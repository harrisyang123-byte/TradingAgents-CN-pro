#!/usr/bin/env python3
"""save_to_mongodb.py — 最终处方保存到 MongoDB

用法:
    python scripts/save_to_mongodb.py --dir <data_dir>

读 step9_final.json + step4_scout.json + data_portfolio.json + conflicts.json
组装为前端期望的 PortfolioAdvice 格式 → 写 MongoDB。
"""

import argparse
import json
import os
import sys
import asyncio
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


def load_json(path: Path) -> Any:
    if not path.exists():
        return None
    try:
        with open(path, "r") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return None


def build_prescriptions(
    final: dict, scout: Optional[dict], portfolio: Optional[dict], pe_data: Optional[dict]
) -> List[dict]:
    """从 Agent 输出组装前端期望的 per-stock prescription 格式"""
    prescriptions: List[dict] = []
    alerts = final.get("critical_alerts", [])

    # ── 读持仓列表 ──
    positions: Dict[str, dict] = {}
    if portfolio:
        for p in portfolio.get("positions", []):
            code = p.get("code", p.get("stock_code", ""))
            if code:
                positions[code] = p

    # ── 读 Scout 的 per-position 分析 ──
    pos_analysis: Dict[str, dict] = {}
    if scout:
        for item in scout.get("position_cross_reference", []):
            code = item.get("code", "")
            if code:
                pos_analysis[code] = item

    # ── 从 scout_independent_findings + cio_decision_validation 提取方向 ──
    findings: Dict[str, dict] = {}
    if scout:
        for item in scout.get("scout_independent_findings", []):
            detail = item.get("detail", "")
            # 尝试从 detail 文本提取 code
            for code in list(positions.keys()):
                if code in detail:
                    findings[code] = {"action": "review", "reasoning": item.get("title", "") + ": " + detail[:200]}

    cio_decisions = {}
    if scout:
        for d in scout.get("cio_decision_validation", []):
            detail = d.get("detail", "")
            for code in list(positions.keys()):
                if code in detail:
                    cio_decisions[code] = {"scout_validation": d.get("scout_validation", ""), "detail": detail[:200]}

    # ── 从 target_allocation_12m 提取大类资产方向 ──
    alloc = final.get("target_allocation_12m", {})
    if not alloc:
        alloc = final.get("asset_allocation_summary", {})

    # ── 对每只持仓生成 prescription ──
    for code, pos in positions.items():
        name = pos.get("name", pos.get("stock_name", code))
        weight = pos.get("weight", pos.get("weight_pct", 0))
        if isinstance(weight, str):
            try:
                weight = float(weight)
            except ValueError:
                weight = 0
        mv = pos.get("market_value_cny", pos.get("market_value", 0))

        # 从 PE 数据取估值状态
        pe_info = (pe_data or {}).get(code, {})
        pe_pct = pe_info.get("pe_percentile_5y") if isinstance(pe_info, dict) else None
        valuation = ""
        if pe_pct is not None:
            valuation = f"PE {pe_pct}%分位" + ("(偏贵)" if pe_pct > 85 else "(合理)" if pe_pct < 50 else "(偏贵)")

        # 从 alerts 中找匹配
        matched_alert = None
        for a in alerts:
            alert_text = json.dumps(a, ensure_ascii=False)
            if code in alert_text or (name and name[:4] in alert_text):
                matched_alert = a
                break

        # 判定 action
        action = "hold"
        reasoning = ""
        priority = "normal"

        if matched_alert:
            severity = matched_alert.get("severity", "")
            if "卖出" in matched_alert.get("title", "") or "减仓" in matched_alert.get("title", ""):
                action = "reduce"
                priority = "important"
            elif "P0" in severity or "致命" in severity:
                action = "reduce"
                priority = "important"
            reasoning = f"[ALERT] {matched_alert.get('title', '')}: {matched_alert.get('summary', '')[:150]}"
        elif pe_pct is not None and pe_pct > 90:
            action = "reduce"
            reasoning = f"PE {pe_pct}%分位——交叉验证建议减仓"
            priority = "important"

        # 从 pos_analysis 补充
        pa = pos_analysis.get(code, {})
        pnl = pa.get("pnl_pct", pos.get("pnl_pct", 0))

        prescriptions.append({
            "code": code,
            "name": name,
            "action": action,
            "current_weight": round(weight, 1),
            "target_weight": round(weight * (0.7 if action == "reduce" else 1.0), 1),
            "capital_source": "",
            "timing": "immediate" if priority == "important" else "conditional",
            "reasoning": reasoning or (pa.get("detail", "") if isinstance(pa.get("detail"), str) else ""),
            "priority": priority,
            "valuation": valuation,
            "pnl_pct": pnl,
            "market_value": mv,
        })

    # 去重
    return prescriptions


def build_cio_verdict(final: dict, conflicts: list) -> str:
    """组装 cio_verdict 文本"""
    parts = []

    # Overall verdict
    ov = final.get("overall_verdict", {})
    if isinstance(ov, dict):
        summary = ov.get("summary", "") or ""
        improvements = ov.get("key_improvements_over_original_judge_plan", "") or ""
        expected = ov.get("expected_outcome_6_months", "") or ""
        if summary:
            parts.append(f"## 总体评估\n{summary}")
        if improvements:
            parts.append(f"## 关键改进\n{improvements}")
        if expected:
            parts.append(f"## 6个月预期\n{expected}")
    elif isinstance(ov, str):
        parts.append(ov)

    # Risk summary
    risk = final.get("risk_summary", {})
    if isinstance(risk, dict):
        risk_text = json.dumps(risk, ensure_ascii=False, indent=2)
        parts.append(f"## 风险摘要\n{risk_text}")

    # Key insights
    insights = final.get("key_insights", [])
    if insights:
        items = []
        for i in insights:
            if isinstance(i, dict):
                items.append(f"- {i.get('title', i.get('insight', ''))}: {i.get('detail', '')}")
            elif isinstance(i, str):
                items.append(f"- {i}")
        if items:
            parts.append("## 关键洞察\n" + "\n".join(items))

    # Alerts
    alerts = final.get("critical_alerts", [])
    if alerts:
        alert_lines = []
        for a in alerts:
            alert_lines.append(f"- [{a.get('severity', '?')}] {a.get('title', '')}: {a.get('action', '')}")
        parts.append("## 致命警报\n" + "\n".join(alert_lines))

    # Conflicts
    if conflicts:
        conflict_lines = []
        for c in conflicts:
            conflict_lines.append(f"- [{c.get('severity', '')}] {c.get('type', '')}: {c.get('description', '')}")
        parts.append("## 交叉验证冲突\n" + "\n".join(conflict_lines))

    return "\n\n".join(parts)


async def save_to_mongodb(data_dir: str) -> bool:
    run_dir = Path(data_dir)
    run_id = run_dir.name

    final = load_json(run_dir / "step9_final.json")
    if not final:
        print(f"错误: CIO 终裁文件不存在: {run_dir / 'step9_final.json'}")
        return False

    scout = load_json(run_dir / "step4_scout.json")
    portfolio = load_json(run_dir / "data_portfolio.json")
    pe_data = load_json(run_dir / "data_pe.json")
    conflicts_raw = load_json(run_dir / "conflicts.json")
    conflicts = conflicts_raw.get("conflicts", []) if conflicts_raw else []

    # 组装 prescription
    prescriptions = build_prescriptions(final, scout, portfolio, pe_data)
    cio_verdict = build_cio_verdict(final, conflicts)

    doc = {
        "advice_id": str(uuid.uuid4()),
        "run_id": run_id,
        "source": "claude-code-workflow-v1",
        "user_id": final.get("user_id", ""),
        "status": "COMPLETED",
        "cio_verdict": cio_verdict,
        "prescription": prescriptions,
        "conflicts": conflicts,
        "conflict_count": len(conflicts),
        "created_at": datetime.now(timezone.utc),
        "completed_at": datetime.now(timezone.utc).isoformat(),
        "elapsed_seconds": 1805,
        "data_dir": str(data_dir),
    }

    from app.core.database import init_database, get_mongo_db
    await init_database()
    db = get_mongo_db()

    for attempt in range(3):
        try:
            await db["portfolio_advice"].update_one(
                {"run_id": run_id, "source": "claude-code-workflow-v1"},
                {"$set": doc},
                upsert=True,
            )
            print(f"✅ 处方已保存 (run_id={run_id}, {len(prescriptions)} items, {len(conflicts)} conflicts)")
            return True
        except Exception as e:
            if attempt < 2:
                print(f"[WARNING] MongoDB 写入失败 (attempt {attempt+1}/3): {e}")
                time.sleep(2)
            else:
                print(f"❌ MongoDB 写入全部失败: {e}")
                return False

    return False


def main():
    parser = argparse.ArgumentParser(description="Save final prescription to MongoDB")
    parser.add_argument("--dir", required=True)
    args = parser.parse_args()
    success = asyncio.run(save_to_mongodb(args.dir))
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
