"""交叉验证引擎 — Python 规则引擎，非 LLM"""

import json
from typing import List, Dict
from pathlib import Path

DATA_DIR = Path("/tmp/claude_advisor")


def detect_tier1_conflicts(tier1: List[Dict]) -> List[Dict]:
    """Tier1 矛盾检测：同标的买入 vs 卖出"""
    conflicts = []
    groups = {}
    for r in tier1:
        code = r.get("code", "")
        if code and not code.startswith("portfolio"):
            groups.setdefault(code, set()).add(str(r.get("recommendation", ""))[:10])

    for code, recs in groups.items():
        has_buy = any("买入" in r or "buy" in r.lower() or "增持" in r for r in recs)
        has_sell = any("卖出" in r or "sell" in r.lower() or "减持" in r for r in recs)
        if has_buy and has_sell:
            conflicts.append({
                "code": code, "type": "tier1_conflict", "severity": "high",
                "detail": f"同一标的Tier1报告方向矛盾: {'/'.join(recs)}",
            })
    return conflicts


def detect_pe_vs_advice(pf: Dict, tier1: List[Dict]) -> List[Dict]:
    """PE 分位 vs 建议方向一致性检查"""
    conflicts = []

    # 读取 PE 数据（如有）
    pe_data = {}
    pe_path = DATA_DIR / "pe.json"
    if pe_path.exists():
        try:
            pe_data = json.load(open(pe_path))
        except (json.JSONDecodeError, FileNotFoundError):
            pass

    for pos in pf.get("positions", []):
        code = pos.get("code", "")
        inst = pos.get("instrument_type", "stock")
        if inst in ("fund", "etf"):
            continue
        # 取 Tier1 建议方向
        t1_recs = [r for r in tier1 if r.get("code") == code]
        latest_rec = str(t1_recs[0].get("recommendation", "")) if t1_recs else ""
        has_buy = "买入" in latest_rec or "buy" in latest_rec.lower()

        # PE 高估且建议买入 → 冲突
        pe = pe_data.get(code, {})
        pe_pct = pe.get("pe_percentile_5y")
        if pe_pct is not None and pe_pct > 85 and has_buy:
            conflicts.append({
                "code": code, "type": "pe_overvalued_buy", "severity": "medium",
                "detail": f"PE {pe_pct}% 分位（历史高位），但 Tier1 建议买入",
            })

    return conflicts


def detect_overlaps(exposure: Dict) -> List[Dict]:
    """敞口重叠识别"""
    conflicts = []
    for o in exposure.get("overlaps", []):
        total = o.get("total", 0)
        sources = o.get("sources", [])
        if total > 0.5 and len(sources) >= 2:
            conflicts.append({
                "code": o.get("name", ""),
                "type": "overlap", "severity": "low" if total < 2 else "medium",
                "detail": f"{o.get('name','')} 合计 {total}%，来自 {', '.join(sources)}",
            })
    return conflicts


def detect_black_swan(market_temp: Dict) -> List[Dict]:
    """黑天鹅预警检测"""
    conflicts = []
    up_ratio = market_temp.get("up_ratio", 50)
    north_days = market_temp.get("north_days", 0)
    north_net = market_temp.get("north_net", 0)

    if up_ratio < 25 and north_days >= 5 and north_net < -50:
        conflicts.append({
            "type": "black_swan", "severity": "high",
            "detail": "涨跌比<25%+北向连续5日净流出+大额流出=黑天鹅预警,建议保持现金≥20%",
        })
    elif up_ratio > 75 and north_net > 50:
        conflicts.append({
            "type": "market_overheat", "severity": "medium",
            "detail": "涨跌比>75%+北向大幅流入=市场亢奋,timing应倾向conditional",
        })
    return conflicts


def detect_sentiment_vs_fundamentals(market_temp: Dict, l2_scout: Dict = None) -> List[Dict]:
    """情绪 vs 基本面冲突（逆向信号）"""
    conflicts = []
    flow_signal = market_temp.get("flow_signal", "中性")

    # 北向大幅流出=恐慌=逆向买入机会（不做空,不做恐慌时卖）
    north_days = market_temp.get("north_days", 0)
    north_net = market_temp.get("north_net", 0)
    if north_days >= 5 and north_net < -50:
        conflicts.append({
            "type": "sentiment_selloff", "severity": "low",
            "detail": "北向连续5日净流出=恐慌型卖出,这是逆向买入窗口,可以关注优质资产",
        })
    return conflicts


def cross_validate_all(
    pf: Dict = None,
    tier1: List[Dict] = None,
    exposure: Dict = None,
    market_temp: Dict = None,
    l2_scout: Dict = None,
) -> List[Dict]:
    """全量交叉验证"""
    all_conflicts = []
    if tier1:
        all_conflicts.extend(detect_tier1_conflicts(tier1))
    if pf and tier1:
        all_conflicts.extend(detect_pe_vs_advice(pf, tier1))
    if exposure:
        all_conflicts.extend(detect_overlaps(exposure))
    if market_temp:
        all_conflicts.extend(detect_black_swan(market_temp))
        all_conflicts.extend(detect_sentiment_vs_fundamentals(market_temp, l2_scout))

    if all_conflicts:
        json.dump(all_conflicts, open(DATA_DIR / "conflicts.json", "w"), ensure_ascii=False)
    else:
        # 空的冲突文件
        json.dump([], open(DATA_DIR / "conflicts.json", "w"))

    return all_conflicts
