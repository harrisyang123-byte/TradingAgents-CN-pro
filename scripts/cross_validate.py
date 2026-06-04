#!/usr/bin/env python3
"""cross_validate.py — 交叉验证规则引擎（确定性算法，非 LLM）

用法:
    python scripts/cross_validate.py --dir <data_dir>

输入: step3_judge.json, step4_scout.json, step5_analyst*.json, step6_strategist*.json,
      data_tier1.json, data_pe.json, data_exposure.json
输出: conflicts.json

检测规则:
    1. Tier1 矛盾: 同标的 buy vs sell
    2. PE 高估 vs 买入建议
    3. 敞口重叠: overlap_weight > 15%
"""

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List


def load_json(path: Path) -> Dict[str, Any]:
    """加载 JSON 文件，不存在或损坏返回空对象"""
    if not path.exists():
        return {}
    try:
        with open(path, "r") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return {}


def detect_tier1_conflicts(tier1_data: List[Dict]) -> List[Dict]:
    """规则 1: Tier1 矛盾检测"""
    conflicts = []
    by_code: Dict[str, List[Dict]] = {}
    for r in tier1_data:
        code = r.get("code", "")
        if code:
            by_code.setdefault(code, []).append(r)

    for code, reports in by_code.items():
        if len(reports) < 2:
            continue
        buys = [r for r in reports if any(w in str(r.get("recommendation", "")).lower()
                for w in ["买入", "buy", "增持", "推荐"])]
        sells = [r for r in reports if any(w in str(r.get("recommendation", "")).lower()
                for w in ["卖出", "sell", "减持", "回避"])]
        if buys and sells:
            buy_srcs = [r.get("name", r.get("code", "?")) for r in buys]
            sell_srcs = [r.get("name", r.get("code", "?")) for r in sells]
            conflicts.append({
                "type": "tier1_conflict",
                "code": code,
                "severity": "high",
                "description": f"Tier1 报告矛盾: 买入({', '.join(buy_srcs[:2])}) vs 卖出({', '.join(sell_srcs[:2])})",
            })

    return conflicts


def detect_pe_overvalued(pe_data: Dict, scout_candidates: List[Dict],
                         analyst_outputs: List[Dict]) -> List[Dict]:
    """规则 2: PE 高估 vs 买入建议"""
    conflicts = []

    for candidate in scout_candidates:
        code = candidate.get("code", "")
        pe_info = pe_data.get(code, {})
        if not isinstance(pe_info, dict):
            continue
        percentile = pe_info.get("pe_percentile_5y")
        if percentile is not None and percentile > 85:
            # 放宽阈值——有 position_cross_reference 的标的就报（无 total_score 不阻检）
            score = candidate.get("total_score", candidate.get("weight_pct", 0))
            conflicts.append({
                "type": "pe_overvalued",
                "code": code,
                "severity": "medium",
                "description": f"PE 处于 {percentile}% 分位(偏贵)，仓位 {candidate.get('weight_pct', 'N/A')}%",
            })

    return conflicts


def detect_overlaps(exposure_data: Dict) -> List[Dict]:
    """规则 3: 敞口重叠"""
    conflicts = []
    overlaps = exposure_data.get("overlaps", [])
    for o in overlaps:
        weight = o.get("overlap_weight", o.get("weight", 0))
        if isinstance(weight, str):
            try:
                weight = float(weight.replace("%", ""))
            except ValueError:
                weight = 0
        if weight > 15:
            code = o.get("code", o.get("stock_code", "?"))
            conflicts.append({
                "type": "overlap",
                "code": code,
                "severity": "low",
                "description": f"基金穿透后 {code} 实际敞口 {weight}%，超过 15% 阈值",
            })

    return conflicts


def main():
    parser = argparse.ArgumentParser(description="Cross-validation rule engine")
    parser.add_argument("--dir", required=True, help="Data directory")
    args = parser.parse_args()
    data_dir = Path(args.dir)

    # 加载所有输入
    tier1 = load_json(data_dir / "data_tier1.json")
    pe_data = load_json(data_dir / "data_pe.json")
    exposure = load_json(data_dir / "data_exposure.json")

    scout = load_json(data_dir / "step4_scout.json")
    step5 = load_json(data_dir / "step5_analyst.json")
    step5_r2 = load_json(data_dir / "step5_analyst_r2.json")

    # 执行规则检测
    all_conflicts: List[Dict] = []

    # 规则 1: Tier1 矛盾
    if isinstance(tier1, list):
        all_conflicts.extend(detect_tier1_conflicts(tier1))

    # 规则 2: PE 高估——直接扫描 data_pe.json
    for code, pe_info in pe_data.items():
        if isinstance(pe_info, dict):
            pct = pe_info.get("pe_percentile_5y")
            if pct is not None and pct > 85:
                all_conflicts.append({
                    "type": "pe_overvalued",
                    "code": code,
                    "severity": "medium",
                    "description": f"PE 处于 {pct}% 分位(偏贵)",
                })

    # 规则 3: 敞口重叠
    if isinstance(exposure, dict):
        all_conflicts.extend(detect_overlaps(exposure))

    # 写入冲突报告
    report = {
        "conflicts": all_conflicts,
        "total": len(all_conflicts),
        "generated_at": datetime.now(timezone.utc).isoformat() + "Z",
    }

    output_path = data_dir / "conflicts.json"
    with open(output_path, "w") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    print(f"冲突检测完成: {len(all_conflicts)} 个问题")
    for c in all_conflicts:
        print(f"  [{c['severity'].upper()}] {c['type']}: {c['code']} — {c['description'][:80]}")

    sys.exit(0)


if __name__ == "__main__":
    main()
