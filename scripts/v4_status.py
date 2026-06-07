#!/usr/bin/env python3
"""v4_status.py — v4 单元状态机 CLI（status / scan）

status：列出全部单元当前状态色 + 版本 + 生成时间 + stale 提示。
scan  ：扫描过期/过时单元，仅置黄并提示（绝不自动重跑，AC4.2 / AC5.3）。

纯只读：读 data/v4 落盘 + 索引，计算状态，不触发任何 LLM、不改产物数值。
"""

import argparse
import json
import sys
from pathlib import Path

# 让脚本能 import app.services.v4
_REPO = Path(__file__).resolve().parents[1]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from app.services.v4 import v4_state, v4_unit_store as store  # noqa: E402


def _collect() -> list:
    """重建索引并对每个单元计算实时状态。"""
    store.rebuild_index()
    units = store.list_units()
    rows = []
    for u in units:
        uid = u["unit_id"]
        env = store.read_unit(uid)
        status, stale = v4_state.compute_status(env, unit_id=uid)
        rows.append({
            "unit_id": uid,
            "unit_type": u.get("unit_type"),
            "version": u.get("version"),
            "status": status,
            "status_label": v4_state.status_label(status),
            "generated_at": u.get("generated_at"),
            "ttl_days": u.get("ttl_days"),
            "stale_reason": stale,
            "cli_hint": v4_state.cli_hint(uid),
        })
    return rows


_COLOR = {
    "gray": "⚪", "blue": "🔵", "green": "🟢", "yellow": "🟡", "red": "🔴",
}


def main() -> int:
    ap = argparse.ArgumentParser(description="v4 单元状态机 CLI")
    ap.add_argument("--mode", choices=["status", "scan"], default="status")
    ap.add_argument("--user-id", default="")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    rows = _collect()

    if args.mode == "scan":
        # 仅展示需要刷新的（yellow/red），并给出 CLI 提示
        flagged = [r for r in rows if r["status"] in ("yellow", "red")]
        if args.json:
            print(json.dumps({"flagged": flagged}, ensure_ascii=False, indent=2))
            return 0
        if not flagged:
            print("✅ 所有单元新鲜，无需刷新。")
            return 0
        print(f"🟡 发现 {len(flagged)} 个单元待刷新（仅软提醒，不会自动重跑）：\n")
        for r in flagged:
            print(f"{_COLOR.get(r['status'],'')} {r['unit_id']}  v{r['version']}")
            if r["stale_reason"]:
                print(f"    原因: {r['stale_reason']}")
            print(f"    刷新: ./scripts/run_v4.sh refresh {r['unit_id']}")
        return 0

    # status
    if args.json:
        print(json.dumps({"units": rows}, ensure_ascii=False, indent=2))
        return 0
    if not rows:
        print("（暂无任何 v4 单元。用 ./scripts/run_v4.sh analyze asset:equity 触发首个分析）")
        return 0
    print(f"v4 单元状态（共 {len(rows)} 个）：\n")
    for r in rows:
        line = f"{_COLOR.get(r['status'],'')} {r['unit_id']:<32} v{r['version']:<3} {r['status_label']}"
        if r["generated_at"]:
            line += f"  @ {r['generated_at']}"
        print(line)
        if r["stale_reason"]:
            print(f"    ⚠ {r['stale_reason']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
