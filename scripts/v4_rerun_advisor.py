#!/usr/bin/env python3
"""v4_rerun_advisor.py — 精准重跑顾问：扫描产物缺哪些「新规则字段」，给出按优先级排序的重跑清单。

背景（2026-06-19 loop iter11 DISCOVER）：mine 反复报「静态规则 100% / 产物 0%」落差——
不是流程缺失（critic 闭环/sell_discipline/pre_mortem/五力/财务 SOP 等规则层已完备），
而是**旧产物早于这些规则、没跟上**。盲目全量重跑 49 只烧 token；本工具按「缺几项新规则」
排序，指导本地**精准重跑**（缺得多的优先），省 token、有的放矢，服务北极星。

只读扫描，不改任何产物。用法：
  python3 scripts/v4_rerun_advisor.py            # 打印重跑清单(按缺项数降序)
  python3 scripts/v4_rerun_advisor.py --json     # 机器可读
"""

from __future__ import annotations

import glob
import json
import sys
from pathlib import Path

STOCK_DIR = Path("data/v4/stocks")

# 新规则字段 → 检测函数（兼容字段名变体，避免误判）
RULE_CHECKS = {
    "sell_discipline(退出纪律)": lambda p: bool(
        p.get("sell_discipline") or (p.get("action_plan", {}) or {}).get("stop_loss")
    ),
    "pre_mortem(三场景死亡清单)": lambda p: bool(p.get("pre_mortem")),
    "five_forces_synthesis(五力交叉编织)": lambda p: bool(
        (p.get("five_forces", {}) or {}).get("cross_force_dynamics")
    ),
    "financial_analysis(杜邦5年/ROIC vs WACC)": lambda p: bool(p.get("financial_analysis")),
    "value_creation(价值创造四问)": lambda p: bool(
        p.get("value_creation") or p.get("value_creation_verified")
    ),
    "credibility真评审(非主agent自评)": lambda p: (
        str((p.get("credibility", {}) or {}).get("data_status") or "") != "synthesized_by_main_agent"
        and str((p.get("critic_evaluation", {}) or {}).get("data_status") or "") != "synthesized_by_main_agent"
    ),
}


def scan() -> list[dict]:
    rows = []
    for f in sorted(glob.glob(str(STOCK_DIR / "*.json"))):
        code = Path(f).stem
        try:
            p = json.loads(Path(f).read_text(encoding="utf-8")).get("payload", {})
        except (OSError, ValueError):
            continue
        missing = [name for name, fn in RULE_CHECKS.items() if not fn(p)]
        if missing:
            rows.append({"code": code, "name": p.get("name", code),
                         "missing_count": len(missing), "missing": missing})
    rows.sort(key=lambda r: -r["missing_count"])
    return rows


def main() -> int:
    rows = scan()
    if "--json" in sys.argv:
        print(json.dumps({"rerun_candidates": rows, "total": len(rows)}, ensure_ascii=False, indent=2))
        return 0
    total = len(glob.glob(str(STOCK_DIR / "*.json")))
    print(f"=== v4 精准重跑顾问 — {len(rows)}/{total} 只个股缺新规则字段（按缺项数降序）===")
    print("提示：缺项最多的优先重跑；本地 `./run_v4.sh refresh stock:<code>`。流程规则已完备，这是产物跟进，非代码洞。\n")
    for r in rows:
        print(f"  [{r['missing_count']}缺] {r['code']} {r['name']}: "
              + ", ".join(m.split("(")[0] for m in r["missing"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
