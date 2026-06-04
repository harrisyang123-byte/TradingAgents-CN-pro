#!/usr/bin/env python3
"""save_to_mongodb.py — Agent 输出 → MongoDB（含 JSON→Markdown 转换 + 处方组装）

用法: python scripts/save_to_mongodb.py --dir <data_dir>

读全部 step JSON + data JSON → 组装完整 PortfolioAdvice → 写 MongoDB
"""

import argparse, asyncio, json, os, re, sys, time, uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


# ═══════════════════════════════════════════════════════════════
# 1. JSON → Markdown 转换器
# ═══════════════════════════════════════════════════════════════

def _maybe_json(v: Any) -> Any:
    """若 v 是 JSON 字符串则解析，否则返回原值"""
    if not isinstance(v, str): return v
    s = v.strip()
    if s.startswith("{") or s.startswith("["):
        try: return json.loads(s)
        except (json.JSONDecodeError, ValueError): pass
    return v


def _jls(path: Path) -> Any:
    """加载 JSON 文件（文件/字符串均处理）"""
    if not path.exists(): return None
    try:
        with open(path) as f: return json.load(f)
    except: return None


# ── L1: macro_judge_verdict ──────────────────────────────────
def _build_l1_verdict(s3: dict) -> str:
    """step3 的 actionable_decisions + debate_adjudication → Markdown"""
    lines: List[str] = []

    # 组合快照摘要
    ps = s3.get("portfolio_snapshot", {})
    if ps:
        lines.append(f"**组合总览**：{ps.get('total_assets_cny', 0):,.0f} 元 · "
                     f"现金 {ps.get('cash_ratio_pct', 0):.1f}% · "
                     f"{ps.get('position_count', 0)} 只持仓 · "
                     f"实际权益敞口 {ps.get('effective_equity_exposure_pct', 0):.1f}%")

    # 宏观背景
    ms = s3.get("macro_snapshot", {})
    if ms:
        lines.append(f"**宏观环境**：{ms.get('summary', '')}")

    # 可执行决策
    decisions = s3.get("actionable_decisions", [])
    if decisions:
        lines.append("## L1 执行决策")
        for d in decisions:
            pid = d.get("id", d.get("priority", "?"))
            action = d.get("action", "")
            detail = d.get("detail", "")
            deadline = d.get("deadline", "")
            rationale = d.get("rationale", "")
            lines.append(f"- **{pid}** [{d.get('type', '')}] {action}")
            if detail: lines.append(f"  {detail}")
            if deadline: lines.append(f"  ⏱ 截止 {deadline}")
            if rationale and len(rationale) < 200: lines.append(f"  {rationale}")

    # 辩论裁决
    debates = s3.get("debate_adjudication", [])
    if debates:
        lines.append("## 争议裁决（策略师 vs 反向者）")
        for d in debates:
            dispute = d.get("dispute", "")
            verdict = d.get("verdict", "")
            ruling = d.get("cio_ruling", d.get("ruling_detail", ""))
            lines.append(f"- **{dispute}** → {verdict}")
            if ruling and len(ruling) < 200: lines.append(f"  CIO: {ruling}")

    # CIO 裁决
    cv = s3.get("cio_verdict", {})
    if isinstance(cv, dict):
        headline = cv.get("headline", "") or cv.get("core_thesis", "")
        if headline: lines.insert(1, f"\n**裁决摘要**：{headline}")

    # 执行序列
    es = s3.get("execution_sequence", {})
    if es:
        lines.append("## 执行序列")
        for phase_key in ("phase_1_immediate", "phase_2_data_recovery", "phase_3_structural_optimization"):
            phase = es.get(phase_key, {})
            if not phase: continue
            label = phase.get("label", phase_key)
            lines.append(f"### {label}")
            tasks = phase.get("tasks", [])
            for i, t in enumerate(tasks):
                if isinstance(t, str): lines.append(f"{i+1}. {t}")
                elif isinstance(t, dict): lines.append(f"{i+1}. {t.get('action', t.get('title', str(t)))}")
            rationale = phase.get("rationale", "")
            if rationale and len(rationale) < 200: lines.append(f"  {rationale}")

    # 风险评估
    fra = s3.get("final_risk_assessment", {})
    if fra:
        lines.append("## 风险评估")
        lines.append(f"**总体风险等级**: {fra.get('overall_risk_level', 'N/A')}")
        for rk, rv in fra.get("risk_factors", {}).items():
            if isinstance(rv, dict):
                lines.append(f"- **{rk}** ({rv.get('level', '?')}): {rv.get('detail', '')}")
        st = fra.get("stop_loss_threshold", {})
        if st:
            lines.append(f"- **止损线**: {st.get('trigger', '')} → {st.get('action', '')}（当前缓冲 {st.get('current_buffer', '')}）")

    return "\n\n".join(lines) if lines else _jls_text(s3)


# ── L2: scout_assessment ─────────────────────────────────────
def _build_l2_scout(s4: dict) -> str:
    lines: List[str] = []

    # 数据完整性
    di = s4.get("data_integrity_report", {})
    if di:
        gaps = di.get("total_data_gaps", 0)
        critical = di.get("critical", [])
        lines.append(f"**数据完整性**：{gaps} 个数据缺口")
        for c in critical:
            lines.append(f"- [CRITICAL] {c.get('item', '')}: {c.get('impact', '')}（影响 {c.get('affected_positions', [])}）")

    # Scout 独立发现
    findings = s4.get("scout_independent_findings", [])
    if findings:
        lines.append("## Scout 独立发现")
        for f in findings:
            sev = f.get("severity", "?").upper()
            title = f.get("title", "")
            detail = f.get("detail", "")
            rec = f.get("recommendation", "")
            lines.append(f"- **[{sev}] {title}**")
            if detail: lines.append(f"  {detail[:300]}")
            if rec: lines.append(f"  建议: {rec}")

    # 执行优先级
    sp = s4.get("scout_execution_priorities", {})
    if sp:
        lines.append("## Scout 执行优先级")
        for cat, cat_label in [("immediate_no_regret", "P0 立即无悔"), ("within_two_weeks", "两周内"), ("within_one_month", "一月内")]:
            items = sp.get(cat, [])
            if items:
                lines.append(f"### {cat_label}")
                for item in items:
                    lines.append(f"- **{item.get('action', '')}** ({item.get('estimated_effort', '')}): {item.get('reason', '')}")

    # CIO 决策验证
    cdv = s4.get("cio_decision_validation", [])
    if cdv:
        lines.append("## 对 CIO 决策的验证")
        for d in cdv:
            lines.append(f"- **{d.get('decision_id', '')}** {d.get('action', '')}: {d.get('scout_validation', '')}")
            addition = d.get("scout_addition", "")
            if addition: lines.append(f"  Scout 补充: {addition}")

    # 风险集中度
    rch = s4.get("risk_concentration_heatmap", {})
    if rch:
        ssr = rch.get("single_stock_risk", {}).get("max_position", {})
        if ssr:
            lines.append(f"**最大单一风险**: {ssr.get('code', '')} {ssr.get('name', '')} 权重 {ssr.get('weight', 0)}%")
        sc = rch.get("sector_concentration", {})
        if sc:
            lines.append(f"**行业集中度**: AI/科技合计 {sc.get('ai_tech_total', '')}")

    return "\n\n".join(lines) if lines else _jls_text(s4)


# ── L3: analyst_assessment ───────────────────────────────────
def _build_l3_analyst(s5: dict) -> str:
    lines: List[str] = []
    holdings = s5.get("holdings_assessment", s5.get("position_assessment", []))
    if holdings:
        lines.append("## 逐只持仓安全边际")
        for h in holdings[:36]:
            code = h.get("code", "?")
            name = h.get("name", "")
            assessment = h.get("assessment", h.get("safety_margin", ""))
            tier1 = h.get("tier1_recommendation", "")
            pe = h.get("pe_percentile_5y", "")
            contradictions = h.get("contradictions", [])
            reasoning = h.get("reasoning", "")
            lines.append(f"- **{code} {name}**: {assessment}")
            if tier1: lines.append(f"  Tier1: {tier1}")
            if pe is not None and pe != "": lines.append(f"  PE 分位: {pe}%")
            if reasoning: lines.append(f"  {reasoning[:200]}")
            for c in contradictions:
                if isinstance(c, dict):
                    lines.append(f"  ⚠ {c.get('description', str(c))}")
        return "\n\n".join(lines)
    return _jls_text(s5)


# ── L3: strategist_assessment ────────────────────────────────
def _build_l3_strategist(s6: dict) -> str:
    lines: List[str] = []
    # 组合诊断
    cpd = s6.get("current_portfolio_diagnosis", {})
    if cpd:
        lines.append(f"**组合评级**: {cpd.get('overall_grade', 'N/A')} · "
                     f"总资产 {cpd.get('total_assets_cny', 0):,.0f} 元 · "
                     f"现金 {cpd.get('cash_ratio_pct', 0):.1f}%")
    ea = s6.get("exposure_analysis", {})
    if ea:
        lines.append(f"**HHI**: {ea.get('hhi', 'N/A')} ({ea.get('hhi_assessment', '')}) · "
                     f"穿透率 {ea.get('penetration_ratio_pct', 'N/A')}%")
    # 最终策略
    fs = s6.get("final_strategy", {})
    if fs:
        lines.append(f"**策略**: {fs.get('headline', '')}")
        ta = fs.get("target_allocation", {})
        if ta:
            for k, v in ta.items():
                lines.append(f"- {k}: {v}")
    # 置信度加权推荐
    cwr = s6.get("conviction_weighted_recommendations", [])
    if cwr:
        lines.append("## 置信度加权推荐")
        for r in cwr:
            lines.append(f"- **{r.get('recommendation', '')}** (置信度 {r.get('conviction', '?')}): {r.get('basis', '')} · 紧迫度 {r.get('urgency', '?')}")
    # 风险
    rmf = s6.get("risk_management_framework", {})
    if rmf:
        lines.append(f"**止损阈值**: {rmf.get('stop_loss_threshold', '')}")
    # 情景分析
    sa = s6.get("scenario_analysis", {})
    if sa:
        lines.append("## 情景分析")
        for case in ("bull_case", "base_case", "bear_case"):
            c = sa.get(case, {})
            if c:
                lines.append(f"- **{case.replace('_case', '')}**: {c.get('scenario', c.get('description', ''))}")
    # closing
    closing = s6.get("closing_statement", "")
    if closing: lines.append(f"\n---\n{closing}")
    return "\n\n".join(lines) if lines else _jls_text(s6)


# ── L4: cio_verdict ──────────────────────────────────────────
def _build_l4_cio(s7: dict, s9: dict, run_dir: Path) -> str:
    lines: List[str] = []

    # step7 definitive_execution_orders
    deo = s7.get("definitive_execution_orders", {})
    if not deo:
        # regex fallback
        all_orders = _extract_orders_regex(run_dir / "step7_cio.json")
        if all_orders:
            lines.append("## Phase 0/1/2 执行指令")
            for o in all_orders[:13]:
                lines.append(f"- **{o.get('order_id', '?')}** [{o.get('type', '')}] {o.get('action', '')}")
                detail = o.get('detail', '')
                if detail: lines.append(f"  💰 {detail}")
                effort = o.get('effort', ''); deadline = o.get('deadline', '')
                if effort or deadline: lines.append(f"  ⏱ {effort} · {deadline}")
        return "\n\n".join(lines) if lines else ""

    for phase_key in ("phase_0_immediate", "phase_1_data_recovery", "phase_2_structural"):
        phase = deo.get(phase_key, {})
        if not phase: continue
        label = phase.get("label", phase_key)
        principle = phase.get("principle", "")
        precondition = phase.get("precondition", "")
        lines.append(f"## {label}")
        if principle: lines.append(f"_{principle}_")
        if precondition: lines.append(f"前提: {precondition}")
        orders = phase.get("orders", [])
        for o in orders:
            oid = o.get("order_id", "?")
            otype = o.get("type", "")
            action = o.get("action", "")
            detail = o.get("detail", "")
            effort = o.get("effort", "")
            deadline = o.get("deadline", "")
            conviction = o.get("conviction", "")
            lines.append(f"**{oid}** [{otype}] {action}")
            if detail: lines.append(f"  💰 {detail}")
            if effort or deadline: lines.append(f"  ⏱ {effort} · 截止 {deadline}")
            if conviction: lines.append(f"  置信度: {conviction}")
        lines.append("")

    # step7 final_adjudication
    fa = s7.get("final_adjudication", {})
    gaps = fa.get("scout_gap_resolution", [])
    if gaps:
        lines.append("## Scout 差距裁决")
        for g in gaps:
            lines.append(f"- **{g.get('gap_id', '?')} {g.get('title', '')}**")
            lines.append(f"  CIO 裁决: {g.get('cio_final_ruling', '')}")
            final_order = g.get("final_order", "")
            if final_order: lines.append(f"  指令: {final_order}")
            lines.append(f"  紧迫度: {g.get('urgency', '')} · 置信度: {g.get('conviction', '')}")

    # step7 analyst_vs_strategist_synthesis
    avs = fa.get("analyst_vs_strategist_synthesis", [])
    if avs:
        lines.append("## 分析师 vs 策略师综合")
        for s in avs:
            lines.append(f"- **{s.get('topic', '')}**: CIO 裁定: {s.get('cio_final_ruling', '')} (置信度 {s.get('conviction', '')})")

    # step7 conviction_weighted_verdicts
    cwv = s7.get("conviction_weighted_verdicts", [])
    if cwv:
        lines.append("## 置信度加权裁决")
        for v in cwv:
            lines.append(f"- **{v.get('verdict', '')}** ({v.get('conviction', '?')})")
            lines.append(f"  依据: {v.get('basis', '')} · 紧迫度: {v.get('urgency', '')}")

    # step7 scenario_response_playbook
    srp = s7.get("scenario_response_playbook", {})
    if srp:
        lines.append("## 情景应对预案")
        for case in ("bull_case", "base_case", "bear_case"):
            c = srp.get(case, {})
            if c:
                lines.append(f"- **{case.replace('_case', '')}**: 触发 {c.get('trigger', '')}")
                lines.append(f"  策略: {c.get('strategy', '')}")

    # step9 critical_alerts
    alerts = s9.get("critical_alerts", [])
    if alerts:
        lines.append("## 致命警报 (step9)")
        for a in alerts:
            lines.append(f"- **[{a.get('severity', '?')}] {a.get('title', '')}**")
            lines.append(f"  行动: {a.get('action', '')} · 截止 {a.get('deadline', '')}")

    # step9 scenario_playbook (user-facing)
    sp9 = s9.get("scenario_playbook", {})
    if sp9 and not srp:
        lines.append("## 情景预案")
        for case in ("bull", "base", "bear"):
            c = sp9.get(case, {})
            if c:
                lines.append(f"- **{case}**: {c.get('trigger', '')} → {c.get('strategy', '')}")

    # step9 risk_summary
    rs9 = s9.get("risk_summary", {})
    if rs9:
        egu = rs9.get("extreme_gains_unprotected", [])
        if egu:
            lines.append("## 极端浮盈无保护")
            for e in egu:
                lines.append(f"  - {e.get('code', '')} {e.get('name', '')}: +{e.get('pnl_pct', 0)}% · {e.get('status', '')}")

    return "\n\n".join(lines) if lines else "（未能解析 CIO 裁决）"


# ── L4: risk_director_review ─────────────────────────────────
def _build_l4_risk(s8: dict) -> str:
    return _jls_text(s8)


# ── 通用 fallback ────────────────────────────────────────────
def _jls_text(v: Any) -> str:
    """任何值 → 字符串"""
    v = _maybe_json(v)
    if v is None: return ""
    if isinstance(v, str): return v
    if isinstance(v, (dict, list)):
        # 尝试提取可读部分
        if isinstance(v, dict):
            for key in ("role", "headline", "summary", "closing_statement", "disclaimer"):
                if isinstance(v.get(key), str):
                    return v[key]
        return json.dumps(v, ensure_ascii=False, indent=2)
    return str(v)


# ═══════════════════════════════════════════════════════════════
# 0. fallback — regex 从损坏 JSON 提取数据
# ═══════════════════════════════════════════════════════════════

def _extract_orders_regex(step_path: Path) -> List[dict]:
    """当 JSON 解析失败时，用 regex 从原始文本提取 orders"""
    try:
        with open(step_path, 'r') as f:
            text = f.read()
    except: return []

    orders = []
    # 匹配: "order_id": "XXX", ... "action": "XXX", ... "detail": "XXX"
    # 用更宽松的方式分段提取
    for block in re.split(r'\},\s*\{', text):
        oid = re.search(r'"order_id"\s*:\s*"([^"]+)"', block)
        action = re.search(r'"action"\s*:\s*"([^"]+)"', block)
        detail = re.search(r'"detail"\s*:\s*"([^"]*?)"(?:\s*[,}])', block)
        otype = re.search(r'"type"\s*:\s*"([^"]+)"', block)
        deadline = re.search(r'"deadline"\s*:\s*"([^"]+)"', block)
        effort = re.search(r'"effort"\s*:\s*"([^"]+)"', block)
        rank = re.search(r'"rank"\s*:\s*(\d+)', block)

        if oid and action:
            orders.append({
                "order_id": oid.group(1),
                "action": action.group(1),
                "detail": detail.group(1) if detail else "",
                "type": otype.group(1) if otype else "",
                "deadline": deadline.group(1) if deadline else "",
                "effort": effort.group(1) if effort else "",
                "rank": int(rank.group(1)) if rank else 99,
            })
    return orders


def _extract_gap_resolutions_regex(step_path: Path) -> List[dict]:
    """从损坏 JSON 中提取 gap resolutions"""
    try:
        with open(step_path, 'r') as f:
            text = f.read()
    except: return []

    gaps = []
    for block in re.split(r'\},\s*\{', text):
        gid = re.search(r'"gap_id"\s*:\s*"([^"]+)"', block)
        if not gid: continue
        title = re.search(r'"title"\s*:\s*"([^"]*?)"(?:\s*[,}])', block)
        ruling = re.search(r'"cio_final_ruling"\s*:\s*"([^"]*?)"(?:\s*[,}])', block)
        final_order = re.search(r'"final_order"\s*:\s*"([^"]*?)"(?:\s*[,}])', block)
        urgency = re.search(r'"urgency"\s*:\s*"([^"]+)"', block)
        gaps.append({
            "gap_id": gid.group(1),
            "title": title.group(1) if title else "",
            "cio_final_ruling": ruling.group(1) if ruling else "",
            "final_order": final_order.group(1) if final_order else "",
            "urgency": urgency.group(1) if urgency else "",
        })
    return gaps

def _build_prescriptions(s3: dict, s4: dict, s7: dict, s9: dict,
                         portfolio: dict, pe_data: dict, run_dir: Path) -> List[dict]:
    """从所有 Agent 输出组装 per-stock 处方"""
    positions = portfolio.get("positions", [])
    pos_map: Dict[str, dict] = {p.get("code", ""): p for p in positions}
    pe = pe_data if isinstance(pe_data, dict) else {}
    prescriptions: List[dict] = []

    # ── 预索引可执行数据 ──
    # 从 step7 definitive_execution_orders 提取所有 orders
    all_orders: List[dict] = []
    deo = s7.get("definitive_execution_orders", {})
    if deo:
        for phase_key, phase_label in [("phase_0_immediate", "P0"), ("phase_1_data_recovery", "P1"), ("phase_2_structural", "P2")]:
            for o in deo.get(phase_key, {}).get("orders", []):
                all_orders.append({**o, "_phase": phase_label})
    if not all_orders:
        all_orders = _extract_orders_regex(run_dir / "step7_cio.json")

    # 从 step7 final_adjudication 提取 gap resolutions
    all_gaps: List[dict] = []
    fa = s7.get("final_adjudication", {})
    for g in fa.get("scout_gap_resolution", []):
        all_gaps.append(g)
    if not all_gaps:
        all_gaps = _extract_gap_resolutions_regex(run_dir / "step7_cio.json")

    # 从 step4 提取 scout findings
    scout_findings: List[dict] = s4.get("scout_independent_findings", [])
    scout_positions: Dict[str, dict] = {}
    for sp in s4.get("position_cross_reference", []):
        code = sp.get("code", "")
        if code: scout_positions[code] = sp

    # 从 step9 提取 alerts
    alerts: List[dict] = s9.get("critical_alerts", [])
    risk_extreme = (s9.get("risk_summary", {}) or {}).get("extreme_gains_unprotected", [])
    egu_map: Dict[str, dict] = {}
    for e in (risk_extreme or []):
        egu_map[e.get("code", "")] = e

    # 从 step7 提取 per-position controls
    pos_controls: Dict[str, dict] = {}
    rmf = s7.get("risk_management_framework", {})
    for pc in rmf.get("individual_position_controls", []):
        pos_str = pc.get("position", "")
        for code in pos_map:
            if code in pos_str:
                pos_controls[code] = pc

    # ── 逐持仓组装 ──
    for code, pos in pos_map.items():
        name = pos.get("name", code)
        weight = pos.get("weight", 0)
        pnl = pos.get("pnl_pct", 0)
        mv = pos.get("market_value_cny", 0)
        pe_info = pe.get(code, {})
        pe_pct = pe_info.get("pe_percentile_5y") if isinstance(pe_info, dict) else None

        action = "hold"
        target_weight = round(weight, 1)
        reasoning_parts: List[str] = []
        priority = "normal"
        timing = "conditional"
        suggested_price = ""
        capital_source = ""

        # ① 查 step7 definitive_execution_orders
        for o in all_orders:
            detail = o.get("detail", "")
            action_text = o.get("action", "")
            if code in detail or code in action_text or name[:6] in detail or name[:6] in action_text:
                otype = o.get("type", "")
                pid = o.get("order_id", "")
                # 优先用 order 的 action 字段判方向——order action 直接表达意图
                # detail 里的关键字可能是其他标的的（如"QDII 止盈释放"写进了黄金 order）
                act_lower = action_text.lower()
                _is_sell = any(w in action_text for w in ("止损", "止盈", "卖出", "减仓", "减持", "清仓", "清理"))
                _is_buy  = any(w in action_text for w in ("定投", "买入", "加仓", "增持", "建仓", "启动"))
                if _is_sell and not _is_buy:
                    action = "reduce"
                elif _is_buy and not _is_sell:
                    action = "add"
                elif any(w in otype for w in ("风险管理", "个股决断")):
                    if any(w in detail for w in ("止损", "止盈", "卖出")):
                        action = "reduce"

                reasoning_parts.append(f"[{pid}] {action_text[:200]}: {detail[:200]}")
                priority = "important"
                timing = "immediate" if o.get("_phase") == "P0" else "conditional"
                deadline = o.get("deadline", "")
                if deadline: reasoning_parts.append(f"  截止: {deadline}")
                # 尝试提取目标价格
                price_match = re.findall(r'(\d+\.?\d*)\s*元', detail)
                if price_match:
                    suggested_price = f"¥{price_match[0]}-{price_match[-1]}" if len(price_match) > 1 else f"¥{price_match[0]}"

        # ② 查 step7 gap_resolution
        if action == "hold":
            for g in all_gaps:
                gap_text = json.dumps(g, ensure_ascii=False)
                if code in gap_text:
                    final_order = g.get("final_order", "")
                    ruling = g.get("cio_final_ruling", "")
                    # gap 的 final_order 直接表达意图——优先用它判方向
                    if any(w in final_order for w in ("止损", "止盈", "卖出", "减仓", "减持", "清仓")):
                        action = "reduce"
                    elif any(w in final_order for w in ("买入", "加仓", "增持", "定投")):
                        action = "add"
                    reasoning_parts.append(f"[{g.get('gap_id', 'GAP')}] {g.get('title', '')}: {ruling[:200]}")
                    priority = "important"

        # ③ 查 step4 scout findings
        for sf in scout_findings:
            sf_text = json.dumps(sf, ensure_ascii=False)
            if code in sf_text or name[:6] in sf_text:
                rec = sf.get("recommendation", "")
                if rec and not reasoning_parts:
                    reasoning_parts.append(f"[Scout: {sf.get('severity', '')}] {sf.get('title', '')}: {rec[:200]}")
                    if any(w in rec for w in ("卖出", "减仓", "止损", "止盈")):
                        action = "reduce" if action == "hold" else action

        # ④ scout position_cross_reference 补充
        sp = scout_positions.get(code, {})
        if sp:
            scout_action = sp.get("scout_assessment", {}).get("action", "")
            if isinstance(scout_action, str) and scout_action and not reasoning_parts:
                reasoning_parts.append(f"[Scout] {scout_action[:200]}")
            tier1_rec = sp.get("tier1", {}).get("recommendation", "")
            if tier1_rec:
                reasoning_parts.append(f"Tier1: {tier1_rec}")
            pe_judgment = sp.get("pe_data", {}).get("valuation_judgment", "")
            if pe_judgment:
                reasoning_parts.append(f"PE 估值: {pe_judgment}")

        # ⑤ step9 alerts + extreme_gains
        for a in alerts:
            if code in json.dumps(a, ensure_ascii=False):
                severity = a.get("severity", "")
                alert_title = a.get("title", "")
                alert_action = a.get("action", "")
                if severity.startswith("P0"):
                    priority = "important"
                    timing = "immediate"
                # 只有 alerts 明确说卖才判 reduce（数据缺失类 P0 不判卖）
                if any(w in alert_title + alert_action for w in ("卖出", "减仓", "止损", "止盈", "减持", "清仓")):
                    if action == "hold": action = "reduce"
                reasoning_parts.append(f"[ALERT {severity}] {alert_title}: {alert_action[:200]}")

        egu = egu_map.get(code, {})
        if egu:
            reasoning_parts.append(f"⚠ 极端浮盈 +{egu.get('pnl_pct', 0)}% 无保护 — {egu.get('status', '')}")

        # ⑥ PE 高估兜底
        if action == "hold" and pe_pct is not None and pe_pct > 90:
            action = "reduce"
            reasoning_parts.append(f"PE {pe_pct}% 分位（交叉验证检出）——建议减仓")
            priority = "important"

        # ⑦ 仍为空时 → hold with default
        if not reasoning_parts:
            pe_status = ""
            if pe_pct is not None:
                pe_status = f"PE {pe_pct}%分位" + ("(偏贵)" if pe_pct > 85 else "(合理)")
            reasoning_parts.append(f"基本面/估值/行业方向均无异常信号{(' · ' + pe_status) if pe_status else ''}")
            priority = "normal"
            timing = "conditional"

        # 计算目标权重——从 order detail 尝试提取目标百分比
        if action == "reduce":
            # 尝试从 reasoning 中提取目标仓位（如 "减仓至 3%"）
            tgt_match = re.search(r'降至?\s*(\d+\.?\d*)\s*%|减(?:仓)?至\s*(\d+\.?\d*)\s*%', " ".join(reasoning_parts))
            if tgt_match:
                tgt = float(tgt_match.group(1) or tgt_match.group(2))
                target_weight = round(tgt, 1)
            else:
                target_weight = round(weight * 0.7, 1) if weight > 1 else weight
        elif action == "add":
            # add 类保持当前权重，不粗暴放大——实际增量由定投等机制决定
            target_weight = round(weight, 1)
        else:
            target_weight = round(weight, 1)

        prescriptions.append({
            "code": code,
            "name": name,
            "action": action,
            "current_weight": round(weight, 1),
            "target_weight": target_weight,
            "capital_source": capital_source,
            "timing": timing,
            "suggested_price": suggested_price,
            "reasoning": " | ".join(reasoning_parts)[:500],
            "priority": priority,
            "pnl_pct": round(pnl, 1) if isinstance(pnl, (int, float)) else pnl,
            "market_value": mv,
        })

    return prescriptions


# ═══════════════════════════════════════════════════════════════
# 3. 行业矩阵
# ═══════════════════════════════════════════════════════════════

def _build_industries(portfolio: dict, prescriptions: List[dict], run_dir: Path):
    """从持仓 + 处方汇总行业视图"""
    positions = portfolio.get("positions", [])
    categories: Dict[str, Dict] = {}

    for p in positions:
        name = p.get("name", "")
        w = p.get("weight", 0)
        code = p.get("code", "")
        itype = p.get("instrument_type", "stock")

        # 个股手写映射
        _stock_map: Dict[str, str] = {
            "603663": "新材料", "002517": "传媒娱乐", "603236": "通信设备",
            "000063": "通信设备", "002415": "安防科技", "09992": "消费",
            "01810": "科技", "002001": "新材料", "002050": "汽车零部件",
        }
        if code in _stock_map:
            cat = _stock_map[code]
        elif itype in ("fund", "etf", "other"):
            # 基金——从名称关键词判断类型
            if any(w in name for w in ("债", "稳健收益", "增强回报", "双债")):
                cat = "债券"
            elif any(w in name for w in ("黄金", "上海金")):
                cat = "黄金"
            elif "纳指" in name or "QDII" in name or "全球精选" in name or "全球多元" in name:
                cat = "QDII/海外"
            elif any(w in name for w in ("500", "300", "A50", "红利", "中证红利", "沪深")):
                cat = "宽基指数"
            elif any(w in name for w in ("科创", "芯片", "半导体", "AI", "人工智能")):
                cat = "科技"
            elif any(w in name for w in ("医疗", "医药")):
                cat = "医药"
            elif any(w in name for w in ("新能源", "绿色电力", "光伏", "电车")):
                cat = "新能源"
            elif "家电" in name:
                cat = "家电"
            elif "ETF" in name or "联接" in name:
                cat = "行业ETF"
            else:
                cat = "基金"
        else:
            # 未映射的个股
            if any(w in name for w in ("新材", "化工", "三祥")):
                cat = "新材料"
            elif any(w in name for w in ("通信", "中兴", "烽火", "移远")):
                cat = "通信设备"
            elif any(w in name for w in ("恺英", "游戏", "传媒", "娱乐")):
                cat = "传媒娱乐"
            elif any(w in name for w in ("海康", "安防")):
                cat = "安防科技"
            elif any(w in name for w in ("三花", "智控", "汽车")):
                cat = "汽车零部件"
            elif "泡泡玛特" in name or "Pop Mart" in name:
                cat = "消费"
            elif "小米" in name or "Xiaomi" in name:
                cat = "科技"
            else:
                cat = name[:6]

        if cat not in categories:
            categories[cat] = {"holdings_weight": 0, "position_count": 0, "codes": [], "names": []}
        categories[cat]["holdings_weight"] += w
        categories[cat]["position_count"] += 1
        categories[cat]["codes"].append(code)
        categories[cat]["names"].append(name)

    # ── 从 order 提取行业级 target 覆盖 ──
    _pos_map = {p.get("code", ""): p for p in positions}
    _ind_target_overrides: Dict[str, float] = {}
    for o in _extract_orders_regex(run_dir / "step7_cio.json"):
        detail = o.get("detail", "")
        action_text = o.get("action", "")
        m = re.search(r'从\s*(\d+\.?\d*)\s*%\s*(?:提升|增至|提高|配置从).*?(\d+\.?\d*)\s*%', detail + action_text)
        if m:
            to_pct = float(m.group(2))
            for code in _pos_map:
                if code in detail or (len(code) >= 4 and code[:4] in detail):
                    for cat, info in categories.items():
                        if code in info["codes"]:
                            _ind_target_overrides[cat] = to_pct
                            break

    # 从处方反推 target_weight 和 go_nogo
    for rx in prescriptions:
        pos = next((p for p in positions if p.get("code") == rx["code"]), None)
        if not pos: continue
        name = pos.get("name", "")
        # 找对应行业
        for cat, info in categories.items():
            if rx["code"] in info["codes"]:
                info.setdefault("target_weight_sum", 0)
                info["target_weight_sum"] += rx.get("target_weight", rx.get("current_weight", 0))
                if rx.get("action") == "reduce":
                    info["go_nogo"] = "NoGo"
                elif rx.get("action") == "add":
                    info.setdefault("go_nogo", "Go")
                break

    industries = []
    for cat, info in categories.items():
        tw = info.get("target_weight_sum", info["holdings_weight"])
        if cat in _ind_target_overrides:
            tw = _ind_target_overrides[cat]
        industries.append({
            "industry": cat,
            "holdings_weight": round(info["holdings_weight"], 1),
            "target_weight": round(tw, 1),
            "position_count": info["position_count"],
            "codes": info["codes"],
            "names": info["names"],
            "go_nogo": info.get("go_nogo", "Watch"),
            "depth": "deep",
            "reasoning": "",
        })

    return industries


# ═══════════════════════════════════════════════════════════════
# 4. 主保存逻辑
# ═══════════════════════════════════════════════════════════════

async def save(data_dir: str) -> bool:
    run_dir = Path(data_dir)
    if not (run_dir / "step9_final.json").exists():
        print(f"错误: 缺少 step9_final.json")
        return False

    # 加载所有文件
    s3 = _jls(run_dir / "step3_judge.json") or {}
    s4 = _jls(run_dir / "step4_scout.json") or {}
    s5 = _jls(run_dir / "step5_analyst.json") or {}
    s6 = _jls(run_dir / "step6_strategist.json") or {}
    s7 = _jls(run_dir / "step7_cio.json") or {}
    s8 = _jls(run_dir / "step8_risk.json") or {}
    s9 = _jls(run_dir / "step9_final.json") or {}
    portfolio = _jls(run_dir / "data_portfolio.json") or {}
    pe_data = _jls(run_dir / "data_pe.json") or {}
    exposure = _jls(run_dir / "data_exposure.json") or {}
    conflicts_raw = _jls(run_dir / "conflicts.json") or {}
    conflicts = conflicts_raw.get("conflicts", [])

    run_id = run_dir.name
    user_id = portfolio.get("user_id", "") or s9.get("user_id", "6a094caea814b57d3357fa0b")

    # 组装
    prescriptions = _build_prescriptions(s3, s4, s7, s9, portfolio, pe_data, run_dir)
    industries = _build_industries(portfolio, prescriptions, run_dir)

    # 市场信号
    mkt_temp = _jls(run_dir / "data_market_temp.json") or {}
    macro = _jls(run_dir / "data_macro.json") or {}
    market_signals = {
        "source": "claude-code-workflow",
        "macro": {"pmi": (macro.get("indicators", {}) or {}).get("pmi", "")},
        "breadth": mkt_temp if isinstance(mkt_temp, dict) else {},
        "north_net": mkt_temp.get("north_net", 0) if isinstance(mkt_temp, dict) else 0,
        "north_days": mkt_temp.get("north_days", 0) if isinstance(mkt_temp, dict) else 0,
        "flow_signal": mkt_temp.get("flow_signal", "中性") if isinstance(mkt_temp, dict) else "中性",
    }

    # PE 价格上下文
    price_context = {}
    for code, info in (pe_data if isinstance(pe_data, dict) else {}).items():
        if isinstance(info, dict):
            price_context[code] = {
                "pe_percentile_5y": info.get("pe_percentile_5y"),
                "pe_ttm": info.get("pe_ttm"),
                "current_price": info.get("current_price"),
                "ma20": info.get("ma20"),
                "judgment": info.get("judgment", ""),
                "pe_percentile_source": info.get("pe_percentile_source", "computed"),
            }

    # 股票候选
    stock_candidates = s4.get("position_cross_reference", s4.get("candidates", []))
    stock_judge_verdict = _jls_text(s4.get("scout_conclusion", s4.get("cio_decision_validation", "")))

    # L1-L4 Markdown
    macro_judge_verdict = _build_l1_verdict(s3)
    market_debate_history = (
        f"## L1 策略师（看多）\n{_jls_text(s3.get('market_intel', {}).get('strategist', s3))}\n\n"
        f"## L1 反向者（看空）\n{_jls_text(s3.get('market_intel', {}).get('contrarian', ''))}"
    )
    scout_assessment = _build_l2_scout(s4)
    analyst_assessment = _build_l3_analyst(s5)
    strategist_assessment = _build_l3_strategist(s6)
    cio_verdict = _build_l4_cio(s7, s9, run_dir)
    risk_director_review = _build_l4_risk(s8)

    # 辩论记录
    debate_history = (
        f"## L3 分析师\n{_jls_text(s5)}\n\n"
        f"## L3 策略师（诊断）\n{_jls_text(s6)}"
    )
    contrarian_assessment = (
        f"## 策略师诊断\n{_jls_text(s6.get('current_portfolio_diagnosis', {}))}\n\n"
        f"## 风险与缓释\n{_jls_text(s6.get('risks_and_mitigants', []))}\n\n"
        f"## 结语\n{s6.get('closing_statement', '')}"
    )

    now = datetime.now(timezone.utc)
    doc = {
        "advice_id": str(uuid.uuid4()),
        "run_id": run_id,
        "source": "claude-code-workflow-v1",
        "user_id": user_id,
        "status": "COMPLETED",
        # L1
        "macro_judge_verdict": macro_judge_verdict,
        "market_intel": {"industries": industries},
        "market_debate_history": market_debate_history,
        # L2
        "scout_assessment": scout_assessment,
        "stock_candidates": stock_candidates,
        "stock_judge_verdict": stock_judge_verdict,
        "stock_debate_history": scout_assessment,
        # L3
        "analyst_assessment": analyst_assessment,
        "strategist_assessment": strategist_assessment,
        "contrarian_assessment": contrarian_assessment,
        "debate_history": debate_history,
        # L4
        "cio_verdict": cio_verdict,
        "risk_director_review": risk_director_review,
        # Data
        "prescription": prescriptions,
        "selected_industries": [i["industry"] for i in industries],
        "market_signals": market_signals,
        "price_context": price_context,
        "conflicts": conflicts,
        "conflict_count": len(conflicts),
        # Meta
        "created_at": now,
        "completed_at": now.isoformat(),
        "analyzed_at": now.isoformat(),
        "elapsed_seconds": 1805,
        "data_dir": str(run_dir),
    }

    from app.core.database import init_database, get_mongo_db
    await init_database()
    db = get_mongo_db()

    for attempt in range(3):
        try:
            await db["portfolio_advice"].update_one(
                {"run_id": run_id, "source": "claude-code-workflow-v1"},
                {"$set": doc}, upsert=True,
            )

            # 写入 industry_coverage，让前端矩阵与处方一致
            cov_written = 0
            for ind in industries:
                await db["industry_coverage"].update_one(
                    {"user_id": user_id, "industry_name": ind["industry"]},
                    {"$set": {
                        "industry_name": ind["industry"],
                        "user_id": user_id,
                        "market": "cn",
                        "go_nogo": ind.get("go_nogo", "Watch"),
                        "lifecycle": "",
                        "depth": ind.get("depth", "deep"),
                        "reasoning": ind.get("reasoning", ""),
                        "confidence": "",
                        "holdings_weight": ind["holdings_weight"],
                        "target_weight": ind["target_weight"],
                        "position_codes": ind["codes"],
                        "position_names": ind["names"],
                        "position_count": ind["position_count"],
                        "analyzed_at": now.isoformat(),
                        "advice_id": doc["advice_id"],
                        "status": "completed",
                    }},
                    upsert=True,
                )
                cov_written += 1

            actions = {}
            for p in prescriptions: actions[p["action"]] = actions.get(p["action"], 0) + 1
            print(f"✅ 处方已保存 (run_id={run_id})")
            print(f"   处方: {len(prescriptions)} 条 · 操作分布 {actions}")
            print(f"   行业覆盖: {cov_written} 个行业已同步")
            print(f"   L1={len(macro_judge_verdict)}B L2={len(scout_assessment)}B L3={len(analyst_assessment)}B L4={len(cio_verdict)}B")
            return True
        except Exception as e:
            if attempt < 2:
                print(f"[WARNING] MongoDB write retry {attempt+1}: {e}")
                time.sleep(2)
            else:
                print(f"❌ MongoDB write failed: {e}")
                return False
    return False


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--dir", required=True)
    args = p.parse_args()
    sys.exit(0 if asyncio.run(save(args.dir)) else 1)


if __name__ == "__main__":
    main()
