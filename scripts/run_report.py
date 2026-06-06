#!/usr/bin/env python3
"""run_report.py — v3 编排「保证产出」的运行报告。

设计目的（对齐 README/AGENTS 的「数据缺失需明示、禁止静默降级」铁律）：
无论 v3 编排成功 / 违规中止 / 崩溃，都产出一份**可读的终态报告**，回答三件事：
  1. 每个阶段：跑了没、产物在不在、产物空不空、关键计数是多少；
  2. 本次到底停在哪、为什么停（违规 / 崩溃 / 正常）；
  3. 前端会不会降级成「拿持仓拼凑」？会的话原因是什么、缺哪个产物。

两种用法：
  - 编排器自动调用：workflow-v3-advisor.js 在每次 return 前调用本脚本（读 _run_disposition.json）。
  - 你本地手动复盘：`python3 scripts/run_report.py --data-dir data/advisor_runs/<ts>`
    （纯 stdlib，不需要 Mongo / akshare / claude，离线即可跑，把 run_report.md 贴给我即可定位断点）

产物：
  - <data-dir>/run_report.json   机器可读（前端/我消费）
  - <data-dir>/run_report.md     人类可读（你看 / 贴给我）

只读分析磁盘上已有的产物文件，不发起任何网络/LLM/DB 调用，绝不修改业务产物。
"""
from __future__ import annotations

import argparse
import datetime as _dt
import json
import os
from pathlib import Path
from typing import Any

# 与 workflow-v3-advisor.js 的 CACHE.out 对齐：每个阶段的终态产物文件
STAGE_OUTPUTS = [
    ("macro", "宏观裁判", "macro_verdict.json"),
    ("asset", "大类配置", "asset_allocation.json"),
    ("industry", "行业研究", "industry_allocations.json"),
    ("scout", "Scout标的侦察", "step4_scout.json"),
    ("portfolio", "组合层诊断", "portfolio_diagnosis.json"),
    ("pm", "PM辩论", "pm_results.json"),
    ("synth", "风控合成", "final_prescription.json"),
]

# 现金桶名（与 risk_rules.CASH_INDUSTRY 对齐），统计「真实行业数」时排除
CASH_INDUSTRY = "现金"

# 新建仓动作（用户最关心的「有没有给我推荐新股票」）
NEW_BUY_ACTIONS = {"new_position", "buy", "add"}
# 卖出/减仓动作
SELL_ACTIONS = {"sell", "reduce", "clear"}


def _load(path: Path) -> Any:
    """安全加载 JSON；不存在/解析失败返回 None。"""
    try:
        if not path.exists():
            return None
        txt = path.read_text(encoding="utf-8").strip()
        if not txt:
            return None
        return json.loads(txt)
    except Exception:
        return None


def _as_list(data: Any, key: str | None = None) -> list:
    """把 [...] 或 {key:[...]} 统一成 list。"""
    if data is None:
        return []
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        if key and isinstance(data.get(key), list):
            return data[key]
        # 兜底：取第一个 list 值
        for v in data.values():
            if isinstance(v, list):
                return v
    return []


def _norm(s: Any) -> str:
    return str(s or "").strip()


def analyze(data_dir: Path) -> dict:
    """逐阶段体检，返回结构化报告 dict。"""
    stages: list[dict] = []
    for stage_id, title, out_name in STAGE_OUTPUTS:
        path = data_dir / out_name
        data = _load(path)
        exists = path.exists()
        info: dict[str, Any] = {
            "stage": stage_id,
            "title": title,
            "output": out_name,
            "exists": exists,
            "empty": data is None,
            "metrics": {},
            "notes": [],
        }

        if not exists:
            info["status"] = "missing"
            info["notes"].append("产物文件不存在——该阶段未运行或在写盘前中止")
        elif data is None:
            info["status"] = "empty"
            info["notes"].append("产物文件存在但为空/无法解析")
        else:
            info["status"] = "ok"
            _fill_stage_metrics(stage_id, data, data_dir, info)
        stages.append(info)

    verdict = _verdict(data_dir, stages)
    disposition = _load(data_dir / "_run_disposition.json")

    return {
        "generated_at": _dt.datetime.now().isoformat(timespec="seconds"),
        "data_dir": str(data_dir),
        "disposition": disposition,  # 编排器塞进来的终态（done/violations_found/crashed）
        "stages": stages,
        "verdict": verdict,
    }


def _fill_stage_metrics(stage_id: str, data: Any, data_dir: Path, info: dict) -> None:
    """按阶段抽取关键计数，并标注用户最关心的几类问题。"""
    m = info["metrics"]
    notes = info["notes"]

    if stage_id == "macro":
        if isinstance(data, dict):
            m["total_weight_limit"] = data.get("total_weight_limit")
            m["cash_floor"] = data.get("cash_floor")
            m["risk_environment"] = data.get("risk_environment")

    elif stage_id == "asset":
        assets = _as_list(data, "assets")
        m["asset_classes"] = len(assets)
        m["stock_weight"] = data.get("stock_weight") if isinstance(data, dict) else None
        tsum = sum(float(a.get("target_weight", 0) or 0) for a in assets if isinstance(a, dict))
        m["target_sum"] = round(tsum, 1)
        if assets and abs(tsum - 100) > 1:
            notes.append(f"⚠️ 6大类目标权重之和={tsum:.1f}%（应=100）")

    elif stage_id == "industry":
        rows = _as_list(data, "allocations")
        real = [r for r in rows if isinstance(r, dict) and _norm(r.get("industry")) != CASH_INDUSTRY]
        m["industries"] = len(real)
        go = [r for r in real if _norm(r.get("go_nogo")) == "Go"]
        m["go_industries"] = len(go)
        m["overweight"] = sum(1 for r in real if _norm(r.get("stance")) == "超配")
        if not real:
            notes.append("🔴 行业分配表为空——下游 Scout/PM 无行业可做，矩阵必空、前端必降级")
        elif not go:
            notes.append("🔴 没有任何 Go 行业——Scout/PM 会整段跳过，不会产出任何买入标的")

    elif stage_id == "scout":
        cands = _as_list(data, "candidates")
        m["candidates"] = len(cands)
        new = [c for c in cands if isinstance(c, dict) and not c.get("is_holding")]
        m["new_candidates"] = len(new)
        m["holding_candidates"] = len(cands) - len(new)
        if not cands:
            notes.append("🔴 Scout 未挖到任何候选标的——大概率 AKShare 取不到成分股，或上游无 Go 行业")
        elif not new:
            notes.append("🔴 候选全是已持仓标的，0 只新股票——这正是「绕来绕去就是老股票」的直接来源")

    elif stage_id == "portfolio":
        reduce = []
        if isinstance(data, dict):
            reduce = _as_list(data, "reduce_candidates")
            m["holdings_assessed"] = len(_as_list(data, "holdings_assessment"))
        m["reduce_candidates"] = len(reduce)

    elif stage_id == "pm":
        rows = _as_list(data)
        m["pm_industries"] = len(rows)
        if not rows:
            notes.append("🔴 PM 无产出——无 Go 行业可配仓，最终处方不会有买入条目")

    elif stage_id == "synth":
        # final_prescription.json
        presc = _as_list(data, "prescription")
        m["prescriptions"] = len(presc)
        actions: dict[str, int] = {}
        for p in presc:
            if isinstance(p, dict):
                a = _norm(p.get("action")).lower()
                actions[a] = actions.get(a, 0) + 1
        m["actions"] = actions
        m["new_buys"] = sum(v for k, v in actions.items() if k in NEW_BUY_ACTIONS)
        m["sells"] = sum(v for k, v in actions.items() if k in SELL_ACTIONS)

        # industry_matrix.json（决定前端降级的关键产物，单独读）
        matrix_raw = _load(data_dir / "industry_matrix.json")
        matrix = _as_list(matrix_raw, "matrix")
        real_matrix = [r for r in matrix if isinstance(r, dict) and _norm(r.get("industry")) != CASH_INDUSTRY]
        m["industry_matrix_rows"] = len(real_matrix)
        m["industry_matrix_exists"] = (data_dir / "industry_matrix.json").exists()

        # risk_violations.json
        viol = _as_list(_load(data_dir / "risk_violations.json"))
        m["risk_violations"] = len(viol)
        if viol:
            engine_err = any(_norm(v.get("rule")) == "risk_engine_error" for v in viol if isinstance(v, dict))
            if engine_err:
                notes.append("🔴 风控引擎执行异常（risk_engine_error）——synth 在写矩阵/处方前 fail-closed 中止")
            else:
                notes.append(f"⚠️ {len(viol)} 条风控违规未清除——可能导致 synth 中止")
        if not real_matrix:
            notes.append("🔴 industry_matrix 为空——前端拿不到 v3 矩阵，必然降级成持仓拼凑视图")
        elif m["new_buys"] == 0:
            notes.append("⚠️ 处方里 0 条新建仓（buy/add/new_position）——只在调整已持仓，没给新方向")


def _verdict(data_dir: Path, stages: list[dict]) -> dict:
    """汇总成一句话判断 + 前端是否降级。"""
    by_id = {s["stage"]: s for s in stages}
    synth = by_id.get("synth", {})
    sm = synth.get("metrics", {})

    matrix_ok = sm.get("industry_matrix_rows", 0) > 0
    presc_n = sm.get("prescriptions", 0)
    new_buys = sm.get("new_buys", 0)

    # 找第一个「该有产物却没有/为空」的阶段作为断点
    breakpoint_stage = None
    for s in stages:
        if s["status"] in ("missing", "empty"):
            breakpoint_stage = s
            break

    frontend_degrade = not matrix_ok
    if frontend_degrade:
        if breakpoint_stage:
            reason = (f"链路在「{breakpoint_stage['title']}」断裂"
                      f"（{breakpoint_stage['output']} {'缺失' if breakpoint_stage['status']=='missing' else '为空'}），"
                      f"industry_matrix 未产出")
        else:
            reason = "industry_matrix 为空（synth 未写出矩阵）"
        degrade_note = "前端将降级为「拿你的持仓反向拼一张表」——只可能显示你已持有的行业/股票，不会出现任何新标的"
    else:
        reason = "industry_matrix 非空，前端读 v3 真实矩阵"
        degrade_note = "前端正常显示 v3 分析结果（非降级）"

    if matrix_ok and presc_n > 0 and new_buys > 0:
        headline = f"✅ 本次产出可用：{sm.get('industry_matrix_rows')} 行矩阵、{presc_n} 条处方、其中 {new_buys} 条新建仓"
        grade = "usable"
    elif matrix_ok and presc_n > 0:
        headline = f"⚠️ 矩阵/处方有，但 0 条新建仓——只调整老持仓，没给新股票方向"
        grade = "no_new_picks"
    else:
        headline = f"🔴 本次不可用：{reason}"
        grade = "degraded"

    return {
        "grade": grade,
        "headline": headline,
        "frontend_will_degrade": frontend_degrade,
        "degrade_reason": reason if frontend_degrade else None,
        "degrade_note": degrade_note,
        "breakpoint": breakpoint_stage["stage"] if breakpoint_stage else None,
    }


def to_markdown(report: dict) -> str:
    v = report["verdict"]
    disp = report.get("disposition") or {}
    disp_status = disp.get("status", "unknown") if isinstance(disp, dict) else "unknown"

    lines: list[str] = []
    lines.append("# v3 编排运行报告")
    lines.append("")
    lines.append(f"- 生成时间：{report['generated_at']}")
    lines.append(f"- 数据目录：`{report['data_dir']}`")
    lines.append(f"- 编排终态：`{disp_status}`"
                 + (f"（停在 `{disp.get('stage')}`）" if isinstance(disp, dict) and disp.get("stage") else ""))
    lines.append("")
    lines.append(f"## 结论：{v['headline']}")
    lines.append("")
    lines.append(f"- 前端是否降级：{'🔴 会降级' if v['frontend_will_degrade'] else '✅ 不降级'}")
    lines.append(f"- 说明：{v['degrade_note']}")
    if v.get("degrade_reason"):
        lines.append(f"- 降级原因：{v['degrade_reason']}")
    if v.get("breakpoint"):
        lines.append(f"- 链路断点：`{v['breakpoint']}` 阶段")
    lines.append("")
    lines.append("## 逐阶段体检")
    lines.append("")
    lines.append("| 阶段 | 产物 | 状态 | 关键计数 |")
    lines.append("|------|------|------|----------|")
    for s in report["stages"]:
        icon = {"ok": "✅", "missing": "⛔", "empty": "⚠️"}.get(s["status"], "?")
        metrics = s.get("metrics", {})
        mstr = "、".join(f"{k}={v}" for k, v in metrics.items()) if metrics else "—"
        if len(mstr) > 80:
            mstr = mstr[:77] + "…"
        lines.append(f"| {s['title']} | `{s['output']}` | {icon} {s['status']} | {mstr} |")
    lines.append("")

    # 把所有 notes（问题点）集中列出
    problems = []
    for s in report["stages"]:
        for n in s.get("notes", []):
            problems.append(f"- [{s['title']}] {n}")
    if problems:
        lines.append("## 发现的问题")
        lines.append("")
        lines.extend(problems)
        lines.append("")

    lines.append("---")
    lines.append("> 本报告纯离线分析磁盘产物，不调用网络/LLM/DB。把本文件贴给灵犀即可定位断点。")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser(description="v3 编排运行报告（保证产出，离线可跑）")
    ap.add_argument("--data-dir", required=True, help="data/advisor_runs/<ts> 目录")
    ap.add_argument("--quiet", action="store_true", help="不打印 headline 到 stdout")
    args = ap.parse_args()

    data_dir = Path(args.data_dir)
    if not data_dir.is_dir():
        print(f"错误: 数据目录不存在: {data_dir}")
        return 1

    report = analyze(data_dir)
    (data_dir / "run_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (data_dir / "run_report.md").write_text(to_markdown(report), encoding="utf-8")

    if not args.quiet:
        print(report["verdict"]["headline"])
        print(f"报告已写入: {data_dir / 'run_report.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
