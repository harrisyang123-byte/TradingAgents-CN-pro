#!/usr/bin/env python3
"""run_report_v4.py — v4 单元级运行报告（NFR3.2「保证看得见」）

延续 v3 run_report 理念：每次运行后逐单元体检——跑没跑 / 产物空不空 /
停在哪为什么 / 数据是否降级 / 前端会不会降级展示。成功/失败/降级都看得见。

产物：
  data/v4/run_report_v4.json   机器可读
  data/v4/run_report_v4.md     人读

用法:
  python scripts/run_report_v4.py
  python scripts/run_report_v4.py --json   # 仅打印 JSON 到 stdout
"""

import argparse
import json
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from app.services.v4 import v4_state, v4_unit_store as store  # noqa: E402

_COLOR = {"gray": "⚪未分析", "blue": "🔵分析中", "green": "🟢新鲜", "yellow": "🟡待刷新", "red": "🔴失败"}


def _payload_health(env: dict) -> dict:
    """判断单元产物是否「空壳」与是否数据降级。"""
    pl = env.get("payload", {}) or {}
    unit_type = env.get("unit_type", "")
    empty = True
    if unit_type in ("asset", "plan"):
        empty = not (pl.get("verdict") or pl.get("plan"))
    elif unit_type == "industry":
        empty = not pl.get("verdict")
    elif unit_type == "stock":
        empty = not pl.get("rating")
    elif unit_type in ("alloc", "alloc_industry"):
        empty = not (pl.get("assets") or pl.get("allocations") or pl.get("stock_weights"))

    # 降级判定：evidence 里出现 missing/estimated，或显式 input_warnings
    degraded = False
    for ev in pl.get("evidence", []) or []:
        if isinstance(ev, dict) and ev.get("status") in ("missing", "estimated"):
            degraded = True
            break
    if pl.get("input_warnings"):
        degraded = True
    return {"empty": empty, "degraded": degraded}


def build_report() -> dict:
    store.rebuild_index()
    units = store.list_units()
    rows = []
    counts = {"green": 0, "yellow": 0, "red": 0, "gray": 0, "blue": 0}
    empty_units, degraded_units, failed_units = [], [], []

    for u in units:
        uid = u["unit_id"]
        env = store.read_unit(uid)
        status, stale = v4_state.compute_status(env, unit_id=uid)
        counts[status] = counts.get(status, 0) + 1
        health = _payload_health(env) if env else {"empty": True, "degraded": False}
        if status == "red":
            failed_units.append(uid)
        if health["empty"] and status not in ("gray",):
            empty_units.append(uid)
        if health["degraded"]:
            degraded_units.append(uid)
        rows.append({
            "unit_id": uid,
            "status": status,
            "status_label": v4_state.status_label(status),
            "version": u.get("version"),
            "generated_at": u.get("generated_at"),
            "stale_reason": stale,
            "payload_empty": health["empty"],
            "data_degraded": health["degraded"],
            "error": (env or {}).get("error"),
        })

    return {
        "total_units": len(units),
        "counts": counts,
        "failed_units": failed_units,
        "empty_units": empty_units,
        "degraded_units": degraded_units,
        "frontend_will_degrade": len(units) == 0,
        "units": rows,
        "generated_at": store.utc_now_iso(),
    }


def render_md(rep: dict) -> str:
    lines = ["# v4 运行报告", "", f"生成时间：{rep['generated_at']}", ""]
    c = rep["counts"]
    lines.append(f"**单元总数**：{rep['total_units']}　"
                 f"🟢{c.get('green',0)} 🟡{c.get('yellow',0)} 🔴{c.get('red',0)} "
                 f"⚪{c.get('gray',0)} 🔵{c.get('blue',0)}")
    lines.append("")
    if rep["failed_units"]:
        lines.append(f"## ⚠ 失败单元（{len(rep['failed_units'])}）—— 可在 CLI 重试")
        for uid in rep["failed_units"]:
            lines.append(f"- `{uid}`：`./scripts/run_v4.sh refresh {uid}`")
        lines.append("")
    if rep["empty_units"]:
        lines.append(f"## 空壳产物（{len(rep['empty_units'])}）—— 跑了但无有效结论")
        for uid in rep["empty_units"]:
            lines.append(f"- `{uid}`")
        lines.append("")
    if rep["degraded_units"]:
        lines.append(f"## 数据降级（{len(rep['degraded_units'])}）—— 含 estimated/missing 证据或缺失上游")
        for uid in rep["degraded_units"]:
            lines.append(f"- `{uid}`")
        lines.append("")
    lines.append("## 全单元清单")
    for r in rep["units"]:
        mark = _COLOR.get(r["status"], r["status"])
        extra = ""
        if r["data_degraded"]:
            extra += " 〔降级〕"
        if r["payload_empty"] and r["status"] != "gray":
            extra += " 〔空壳〕"
        lines.append(f"- {mark} `{r['unit_id']}` v{r['version']}{extra}")
        if r["stale_reason"]:
            lines.append(f"    - {r['stale_reason']}")
        if r["error"]:
            lines.append(f"    - 错误：{r['error']}")
    if rep["frontend_will_degrade"]:
        lines.append("")
        lines.append("> ⚠ 当前无任何单元产物，前端将显示空态引导（提示在 CLI 触发分析）。")
    return "\n".join(lines) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser(description="v4 单元级运行报告")
    ap.add_argument("--json", action="store_true", help="仅打印 JSON")
    args = ap.parse_args()

    rep = build_report()
    if args.json:
        print(json.dumps(rep, ensure_ascii=False, indent=2))
        return 0

    root = store.data_root()
    root.mkdir(parents=True, exist_ok=True)
    (root / "run_report_v4.json").write_text(
        json.dumps(rep, ensure_ascii=False, indent=2), encoding="utf-8")
    md = render_md(rep)
    (root / "run_report_v4.md").write_text(md, encoding="utf-8")
    print(md)
    print(f"✅ 运行报告已写入 {root}/run_report_v4.{{json,md}}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
