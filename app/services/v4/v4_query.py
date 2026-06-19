"""v4_query.py — v4 只读查询服务（NFR1.2：走缓存秒级响应，不触发 LLM）

读取单元信封（Mongo v4_units 优先，文件落盘回退），计算实时状态色，
组装三层 Tab 所需结构。绝不触发任何 LLM / 重计算。
"""

from __future__ import annotations

import logging
import json
from typing import Any, Dict, List, Optional

from app.services.v4 import asset_classes as ac
from app.services.v4 import v4_state, v4_unit_store as store

logger = logging.getLogger("webapi")


async def load_user_units(db, user_id: str) -> Dict[str, Dict[str, Any]]:
    """加载某用户全部单元 → {unit_id: envelope}。Mongo 优先，缺失回退文件落盘。"""
    units: Dict[str, Dict[str, Any]] = {}
    # Mongo
    if db is not None:
        try:
            cursor = db["v4_units"].find({"user_id": user_id})
            async for doc in cursor:
                doc.pop("_id", None)
                doc.pop("user_id", None)
                uid = doc.get("unit_id")
                if uid:
                    units[uid] = doc
        except Exception as e:
            logger.warning("v4 load_user_units: Mongo 查询失败，回退文件落盘: %s", e)
    # 文件回退（本地运行未导入 Mongo 时）
    if not units:
        try:
            store.rebuild_index()
            for u in store.list_units():
                env = store.read_unit(u["unit_id"])
                if env:
                    units[env["unit_id"]] = env
        except Exception as e:
            logger.warning("v4 load_user_units: 文件落盘回退失败: %s", e)
    return units


def _resolver(units: Dict[str, Dict[str, Any]]):
    def resolve(uid: str) -> Optional[Dict[str, Any]]:
        e = units.get(uid)
        if e is None:
            return None
        return {"version": e.get("version"), "fingerprint": e.get("fingerprint")}
    return resolve


# D0-8 兼容层 — 把新 schema(verdict.stance/action_plan/critic_evaluation) 翻译成
# 前端 StockDetailTab 期望的旧字段(rating/credibility/risks/...)
# 让 002156/09992 这类按新流程跑出的标的也能在前端正常展示分析详情
def _stance_to_rating(verdict):
    if not isinstance(verdict, dict):
        return None
    s = (verdict.get("stance") or "").strip()
    if not s:
        return None
    # 优先匹配 持有/观望(因为可能含"加仓"上下文如"不主动加仓")
    if any(k in s for k in ("持有", "观望", "HOLD", "维持")):
        return "HOLD"
    if any(k in s for k in ("减仓", "卖", "SELL", "清", "REDUCE")):
        return "REDUCE"
    if any(k in s for k in ("加仓", "买入", "BUY")):
        return "BUY"
    return s[:6]


def _extract_target_price(p):
    vb = p.get("valuation_basis")
    if not isinstance(vb, dict):
        return None
    sc = vb.get("forward_eps_scenarios_with_confidence") or vb.get("forward_eps_scenarios") or vb.get("scenarios") or {}
    if not isinstance(sc, dict):
        return None
    base = sc.get("base")
    if isinstance(base, dict):
        return base.get("fair_price") or base.get("implied_price_hkd") or base.get("price")
    if isinstance(base, str):
        return base
    pwt = vb.get("probability_weighted_target")
    # 截断长字符串避免污染前端 target 显示
    if isinstance(pwt, str) and len(pwt) > 40:
        # 尝试抓出 HK$XXX 或 ¥XXX 数字
        import re
        m = re.search(r"(HK\$\d+\.?\d*|¥\d+\.?\d*|\$\d+\.?\d*)", pwt)
        if m:
            return m.group(1)
    return pwt


def _extract_worst_case(p):
    vb = p.get("valuation_basis")
    if not isinstance(vb, dict):
        return None
    sc = vb.get("forward_eps_scenarios_with_confidence") or vb.get("forward_eps_scenarios") or vb.get("scenarios") or {}
    if not isinstance(sc, dict):
        return None
    bear = sc.get("bear")
    if isinstance(bear, dict):
        return bear.get("fair_price") or bear.get("implied_price_hkd") or str(bear)
    return bear


def _extract_entry_range(p):
    ap = p.get("action_plan")
    if not isinstance(ap, dict):
        return None
    bz = ap.get("buy_back_zones") or []
    if bz:
        first = bz[0]
        if isinstance(first, (str, int, float)):
            return first
        if isinstance(first, dict):
            return first.get("zone") or first.get("range")
        return str(first)[:80]
    return None


def _extract_credibility(p):
    ce = p.get("critic_evaluation") or {}
    if ce:
        return {
            "initial_score": ce.get("v1_score"),
            "critic_score": ce.get("v2_score") or ce.get("v1_score"),
            "final_verdict": ce.get("v2_recommendation") or ce.get("recommendation") or "ACCEPT",
            "reviewers": ["芒格", "段永平", "Serenity", "达里奥"],
            "issues_addressed": ce.get("v1_issues_addressed"),
        }
    # D0-9 兼容(2026-06-15): 本会话个股用 critic_review 字段(verdict/score), 映射到前端读的 credibility
    cr = p.get("critic_review") or {}
    if cr and (cr.get("score") is not None or cr.get("verdict")):
        return {
            "initial_score": None,
            "critic_score": cr.get("score"),
            "final_verdict": cr.get("verdict") or "ACCEPT",
            "reviewers": ["芒格", "段永平", "Serenity", "达里奥"],
            "issues_addressed": cr.get("pending") or cr.get("key_praise"),
        }
    return None


def _fallback_five_forces(p):
    """D0-9: 老 v3 schema 个股没有 five_forces 结构化字段, 从 chokepoint_score/business_quality/risks 等散落字段
    拼出可展示的最小 five_forces, 让前端 Step2 b 不至于整片空白(降级展示)。"""
    cs = p.get("chokepoint_score")
    bq = p.get("business_quality")
    if not (cs or bq):
        return None
    # 从 chokepoint_score 提取护城河等级
    moat = "中"
    cs_str = str(cs or "")
    if any(k in cs_str for k in ["宽", "Very Wide", "极宽", "9.0", "8.5"]): moat = "宽"
    elif any(k in cs_str for k in ["中上", "B+", "7."]): moat = "中上"
    elif any(k in cs_str for k in ["中下", "弱", "中等偏弱"]): moat = "中下"
    elif any(k in cs_str for k in ["窄", "无护城河"]): moat = "窄"
    risks = p.get("risks") or []
    weakest = risks[0] if risks else (p.get("worst_case") or "")
    return {
        "moat_rating": moat,
        "moat_synthesis": cs_str or bq or "(老 schema 落盘, 详见 thesis 与价值创造维度)",
        "cross_force_dynamics": {
            "weakest_link": weakest if isinstance(weakest, str) else str(weakest),
        },
        "key_risk": str(risks[0]) if risks else None,
        "monitoring_signals": [str(r) for r in risks[:5]] if risks else [],
        "_data_status": "fallback_from_chokepoint_score(老 schema 降级展示, 完整五力需重跑)",
    }


def _fallback_analysts(p):
    """D0-9: 老 v3 schema 个股没有结构化 analysts.{financial/competitive/valuation/sentiment},
    从 thesis/value_creation/valuation_basis/forward_view 等拼出降级展示, 让前端 Step2 不至于空白。"""
    if not (p.get("thesis") or p.get("value_creation") or p.get("valuation_basis")):
        return {}
    # 财务: 从 value_creation.actionable_verdict 或 ROIC/ROE 拼
    vc = p.get("value_creation") or {}
    av = vc.get("actionable_verdict") or {}
    fin_parts = []
    if av.get("verified_pe"): fin_parts.append(f"PE {av['verified_pe']}")
    if av.get("roic_pct"): fin_parts.append(f"ROIC/ROE {av['roic_pct']}")
    if av.get("verified_price"): fin_parts.append(f"现价¥{av['verified_price']}")
    if vc.get("roic_vs_wacc"): fin_parts.append(vc["roic_vs_wacc"])
    fin = "; ".join(fin_parts) if fin_parts else None
    # 估值: 从 valuation_basis 或 expert_valuation
    vb = p.get("valuation_basis")
    val = None
    if isinstance(vb, str):
        val = vb[:500]
    elif isinstance(vb, dict):
        val = str(vb.get("derivation") or vb.get("logic") or vb)[:500]
    elif vc.get("expert_valuation"):
        ev = vc["expert_valuation"]
        if isinstance(ev, dict):
            val = str(ev.get("target_verdict") or ev.get("now_judgment") or ev)[:500]
    # 竞争: 从 chokepoint_score 或 business_quality
    comp = p.get("chokepoint_score") or p.get("business_quality")
    # 舆情: 从 thesis 提取(降级)
    senti = (p.get("thesis") or "")[:300] + " (老 schema 无独立舆情段, 取自 thesis 摘要)"
    out = {}
    if fin: out["financial"] = fin
    if comp: out["competitive"] = str(comp)
    if val: out["valuation"] = str(val)
    if senti: out["sentiment"] = senti
    if out: out["_data_status"] = "fallback_from_thesis(老 schema 降级展示, 完整4分析师独立辩论需重跑)"
    return out




def _extract_risk_debate(p):
    rc = p.get("risk_consensus_from_3way") or {}
    if not rc:
        return None
    return {
        "aggressive": rc.get("aggressive"),
        "safe": rc.get("safe"),
        "neutral": rc.get("neutral"),
        "director_decision": rc.get("director_decision"),
    }


def _extract_sell_discipline(p):
    ap = p.get("action_plan") or {}
    out = []
    sl = ap.get("stop_loss") or {}
    if isinstance(sl, dict):
        if sl.get("hard"):
            out.append(f"硬止损 {sl['hard']}")
        if sl.get("trailing"):
            out.append(f"跟踪止损 {sl['trailing']}")
    elif sl:
        out.append(str(sl))
    for tz in (ap.get("trim_zones") or []):
        out.append(f"减仓区 {tz}")
    return out


def _extract_risks(p):
    out = []
    refl = p.get("reflection") or {}
    if refl.get("self_check"):
        out.append(f"诚实自查: {refl['self_check'][:120]}")
    tr = p.get("tail_risk_joint_scenario_modeling") or {}
    for k, v in tr.items():
        if "joint" in k.lower() and isinstance(v, dict) and v.get("implication"):
            out.append(f"尾部联合风险: {v['implication'][:130]}")
    ds = p.get("data_status_overall") or {}
    miss = ds.get("missing") or []
    if miss:
        out.append(f"数据盲区: {', '.join(miss[:3])} 等 {len(miss)} 项 missing")
    return out[:8]


def decorate_unit(unit_id: str, envelope: Optional[Dict[str, Any]],
                  units: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    """为单元附加实时 status/stale_reason/cli_hint（统一前端契约，AC8.4）。"""
    resolver = _resolver(units)
    status, stale = v4_state.compute_status(envelope, unit_id=unit_id, upstream_resolver=resolver)
    base = {
        "unit_id": unit_id,
        "status": status,
        "status_label": v4_state.status_label(status),
        "stale_reason": stale,
        "cli_hint": v4_state.cli_hint(unit_id),
        "version": (envelope or {}).get("version"),
        "generated_at": (envelope or {}).get("generated_at"),
        "ttl_days": (envelope or {}).get("ttl_days"),
        "upstream": (envelope or {}).get("upstream", []),
        "run_mode": (envelope or {}).get("run_mode"),
        "exists": envelope is not None,
    }
    return base


def build_overview(units: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    """Tab1：七大类卡片 + 资产配比 + equity_quota（AC8.1）。"""
    alloc_env = units.get("alloc:portfolio")
    alloc_payload = (alloc_env or {}).get("payload", {}) if alloc_env else {}
    alloc_targets = {a.get("asset_class"): a for a in alloc_payload.get("assets", [])}
    equity_quota = alloc_payload.get("equity_quota")

    cards: List[Dict[str, Any]] = []
    for cfg in ac.ASSET_CLASSES:
        key = cfg["key"]
        unit_id = f"asset:{key}"
        env = units.get(unit_id)
        meta = decorate_unit(unit_id, env, units)
        payload = (env or {}).get("payload", {})
        verdict = payload.get("verdict", {}) if payload else {}
        # 防御：代跑 LLM 产物的 verdict 可能为字符串/缺省结构，强制成 dict，
        # 单个单元 schema 异常只让该卡片字段降级为 None，绝不崩掉整个 Tab1/快照（FR-005 软降级）。
        if not isinstance(verdict, dict):
            verdict = {}
        target = alloc_targets.get(key, {})
        cards.append({
            **meta,
            "asset_class": key,
            "label": cfg["label_zh"],
            "max_drill_depth": cfg["max_drill_depth"],
            "current_weight": target.get("current_weight", payload.get("current_weight", 0)),
            "target_weight": target.get("target_weight"),
            "action": target.get("action"),
            "actively_zeroed": target.get("actively_zeroed", False),
            "stance": verdict.get("stance"),
            "direction": verdict.get("direction"),
            "summary": verdict.get("situation") or verdict.get("trend"),
        })

    # unclassified 桶（AC1.1）：如果存在且有权重，追加到 cards 确保 MECE 可见
    unc_env = units.get("asset:unclassified")
    if unc_env:
        unc_payload = (unc_env or {}).get("payload", {})
        unc_verdict = unc_payload.get("verdict", {}) if unc_payload else {}
        if not isinstance(unc_verdict, dict):
            unc_verdict = {}
        if unc_payload.get("current_weight", 0) > 0:
            unc_target = alloc_targets.get("unclassified", {})
            cards.append({
                **decorate_unit("asset:unclassified", unc_env, units),
                "asset_class": "unclassified",
                "label": unc_payload.get("label", "待人工归类"),
                "max_drill_depth": 0,
                "current_weight": unc_target.get("current_weight", unc_payload.get("current_weight", 0)),
                "target_weight": unc_target.get("target_weight"),
                "action": unc_target.get("action"),
                "actively_zeroed": unc_target.get("actively_zeroed", False),
                "stance": unc_verdict.get("stance"),
                "direction": unc_verdict.get("direction"),
                "summary": unc_verdict.get("situation") or unc_verdict.get("trend"),
            })

    return {
        "allocation": {
            **decorate_unit("alloc:portfolio", alloc_env, units),
            "equity_quota": equity_quota,
            "sum_check": alloc_payload.get("sum_check"),
            "input_warnings": alloc_payload.get("input_warnings", []),
            "summary": alloc_payload.get("summary", ""),
        },
        "asset_cards": cards,
        "equity_quota": equity_quota,
        "equity_disabled": equity_quota == 0,
        # D0-6 (2026-06-13) 基金穿透体检 — Level 2 风格因子 + 重叠分析
        "fund_passthrough": _fund_passthrough_summary_for_overview(units),
    }


def _fund_passthrough_summary_for_overview(units: Dict[str, Dict[str, Any]]) -> Dict[str, Any] | None:
    """组合层基金穿透体检 (用于 V4Overview 卡)"""
    try:
        from pathlib import Path
        holdings_path = Path("data/v4/_inputs/holdings.json")
        if not holdings_path.exists():
            return None
        from app.services.v4.v4_classifier import classify_holdings
        from app.services.v4.v4_aggregator import aggregate_full
        h = json.loads(holdings_path.read_text(encoding="utf-8"))
        classified = classify_holdings(h.get("positions", []) or [])
        stock_inds = {}
        for uid2, env2 in units.items():
            if uid2.startswith("stock:"):
                p2 = env2.get("payload", {}) or {}
                code2 = p2.get("code")
                ind2 = p2.get("industry")
                if code2 and ind2:
                    stock_inds[code2] = ind2
        agg = aggregate_full(classified, stock_inds)
        return {
            "summary": agg.get("summary", {}),
            "style_factors": agg.get("style_factors", {}),
            "overlap_analysis": agg.get("overlap_analysis", {}),
            "industries_top10": list(agg.get("industries", {}).items())[:10],
            "indirect_concentration_top10": agg.get("overlap_analysis", {}).get("summary", {}).get("indirect_concentration_top10", []),
        }
    except Exception:
        return None


def build_units_status(units: Dict[str, Dict[str, Any]]) -> List[Dict[str, Any]]:
    """全单元状态机视图（AC8.4 / FR-005）。"""
    out = []
    for uid in sorted(units.keys()):
        out.append(decorate_unit(uid, units[uid], units))
    return out


def build_asset_detail(units: Dict[str, Dict[str, Any]], asset_class: str) -> Dict[str, Any]:
    """Tab2 大类详情（AC8.2）。权益→行业列表；非权益→方案 payload。

    供 portfolio_v4 路由与 build_snapshot_v4 共用，保证 API/快照同构（NFR4.1）。
    """
    asset_env = units.get(f"asset:{asset_class}")
    plan_env = units.get(f"plan:{asset_class}")
    meta = decorate_unit(f"asset:{asset_class}", asset_env, units)
    asset_payload = (asset_env or {}).get("payload", {}) if asset_env else {}
    # D0-9 兼容(2026-06-15): 大类单元有两种 schema —
    #   老: payload.verdict.{stance,summary,situation,...} 嵌套
    #   新: payload.{stance,summary,situation,direction,risks,forward_view,reflection} 扁平
    # 扁平 schema 的固收/现金/大宗等大类此前 verdict=null 导致前端 Tab2 看不到分析,
    # 这里若无嵌套 verdict 但有扁平 stance, 用扁平字段组装 verdict, 保证 API/快照同构展示。
    _verdict = asset_payload.get("verdict")
    if not _verdict and asset_payload.get("stance"):
        _verdict = {
            "stance": asset_payload.get("stance"),
            "summary": asset_payload.get("summary"),
            "situation": asset_payload.get("situation"),
            "direction": asset_payload.get("direction"),
            "trend": asset_payload.get("trend"),
            "risks": asset_payload.get("risks"),
            "confidence": asset_payload.get("confidence"),
            "forward_view": asset_payload.get("forward_view"),
            "reflection": asset_payload.get("reflection"),
        }
    resp: Dict[str, Any] = {
        "asset_class": asset_class,
        "label": ac.label_of(asset_class),
        "is_equity": ac.is_equity(asset_class),
        "max_drill_depth": ac.max_drill_depth(asset_class),
        "asset_unit": meta,
        "verdict": _verdict,
        "tradable": asset_payload.get("tradable", []),
        "holding_only_exposure": asset_payload.get("holding_only_exposure", 0),
        # §5.9 A：辩论与专项分析早已在信封里，此前被丢弃；所有大类通用（展示缺口非数据缺口）
        "debate_rounds": asset_payload.get("debate_rounds", []),
        "analysts": asset_payload.get("analysts", {}),
    }
    if not ac.is_equity(asset_class):
        plan_payload = (plan_env or {}).get("payload", {}) if plan_env else {}
        resp["plan_unit"] = decorate_unit(f"plan:{asset_class}", plan_env, units)
        # D0-9 兼容(2026-06-15): plan 单元两种 schema —
        #   老: payload.plan.{holding_structure,instrument_mix,...} 嵌套
        #   新: payload.{stance,summary,action_plan,structure_target,valuation_basis,...} 扁平
        # 扁平方案此前 plan=null 导致前端投资方案看不到, 这里无嵌套 plan 但有扁平方案字段时
        # 直接把 plan_payload 整体作为 plan 传给前端(PlanCard 已兼容新旧 schema)。
        _plan = plan_payload.get("plan") or asset_payload.get("plan")
        if not _plan and (plan_payload.get("action_plan") or plan_payload.get("structure_target")
                          or plan_payload.get("stance")):
            _plan = plan_payload
        resp["plan"] = _plan
    else:
        eq_alloc = units.get("alloc:equity_industries")
        resp["equity_industries_unit"] = decorate_unit("alloc:equity_industries", eq_alloc, units)
        resp["industries"] = (eq_alloc or {}).get("payload", {}).get("allocations", []) if eq_alloc else []
    return resp


def _extract_embedded_json(s: str) -> Optional[Dict[str, Any]]:
    """从含思考过程的脏字符串里抽取 ```json ...``` 代码块并解析（行业辩论 subagent 原始输出）。"""
    if not isinstance(s, str):
        return None
    import re
    m = re.search(r"```json\s*(\{.*?\})\s*```", s, re.S)
    if not m:
        # 退而求其次：找第一个 { 到最后一个 } 的片段
        i, j = s.find("{"), s.rfind("}")
        if i == -1 or j == -1 or j <= i:
            return None
        frag = s[i:j + 1]
    else:
        frag = m.group(1)
    try:
        return json.loads(frag)
    except ValueError:
        return None


def _load_industry_debate(name: str) -> List[Dict[str, Any]]:
    """合并独立辩论文件 data/v4/industry_debate_<name>.json（payload.debate_rounds 为空时的来源）。

    原始 bull/bear 是含思考过程的脏字符串，解析内嵌 JSON 提取 thesis/challenge/points，
    解析失败则回退展示截断后的原文，保证「完全展示」不丢内容。
    """
    from pathlib import Path
    safe = str(name).replace("/", "_").replace("\\", "_")
    fp = Path(f"data/v4/industry_debate_{safe}.json")
    if not fp.exists():
        return []
    try:
        raw = json.loads(fp.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    rounds = []
    for r in raw.get("rounds", []) or []:
        bull_obj = _extract_embedded_json(r.get("bull", ""))
        bear_obj = _extract_embedded_json(r.get("bear", ""))
        rounds.append({
            "round": r.get("round"),
            "bull": bull_obj or (r.get("bull", "")[:1500] if isinstance(r.get("bull"), str) else None),
            "bear": bear_obj or (r.get("bear", "")[:1500] if isinstance(r.get("bear"), str) else None),
        })
    return rounds


def _load_industry_drill(name: str) -> List[Dict[str, Any]]:
    """合并独立深挖文件 data/v4/industry_drill_<name>.json（瓶颈上溯链）。

    workflow Step A2 产出 {industry, drills:[{start, depth_reached, chain:[...]}]}。
    转成前端 deep_chokepoint_chains 同构结构（start + chain + deepest_alpha）。
    """
    from pathlib import Path
    safe = str(name).replace("/", "_").replace("\\", "_")
    fp = Path(f"data/v4/industry_drill_{safe}.json")
    if not fp.exists():
        return []
    try:
        raw = json.loads(fp.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    out = []
    for d in raw.get("drills", []) or []:
        chain = d.get("chain", []) or []
        # 最深且标记未发现的一环作为 deepest_alpha 兜底（director 未显式给时）
        deepest = ""
        for node in reversed(chain):
            if isinstance(node, dict) and node.get("node"):
                disc = str(node.get("discovery_level", ""))
                tag = "（🟢未发现）" if "未发现" in disc else ""
                deepest = f"{node.get('node')}{tag}：{node.get('supply_demand_gap', '')}"
                break
        out.append({"start": d.get("start"), "chain": chain, "deepest_alpha": deepest})
    return out


def build_industry_detail(units: Dict[str, Dict[str, Any]], name: str) -> Dict[str, Any]:
    """Tab3 行业详情（AC8.3）：深辩报告 + 个股列表 + 行业内配比。"""
    ind_env = units.get(f"industry:{name}")
    alloc_env = units.get(f"alloc:industry:{name}")
    ind_payload = (ind_env or {}).get("payload", {}) if ind_env else {}

    # D0-2 修复(2026-06-13): investment_map 中的 rating/target_price 实时从 stocks 单元取最新
    # 避免行业 payload 落盘后个股 v2 下修但行业仍显示 v1 旧评级的不一致问题
    raw_inv_map = ind_payload.get("investment_map", []) or []
    fresh_inv_map = []
    for item in raw_inv_map:
        item = dict(item)  # 不改原 payload
        rec = (item.get("recommended") or "").strip()
        # 提取代码: "002371 北方华创" → "002371"
        code_match = rec.split()[0] if rec else ""
        if code_match and code_match.isdigit():
            stock_env = units.get(f"stock:{code_match}")
            if stock_env:
                stock_p = stock_env.get("payload", {})
                live_rating = stock_p.get("rating")
                live_target = stock_p.get("target_price")
                if live_rating:
                    item["rating"] = live_rating  # 用最新个股评级覆盖
                if live_target is not None:
                    item["target_price_live"] = live_target  # 新字段:最新目标价(行业 payload 没这个)
                # 加一致性标记：这条数据来自最新个股单元
                item["rating_source"] = "stock_unit_latest"
        fresh_inv_map.append(item)

    resp: Dict[str, Any] = {
        "industry": name,
        "industry_unit": decorate_unit(f"industry:{name}", ind_env, units),
        "verdict": ind_payload.get("verdict"),
        # debate_rounds：payload 内优先，为空则合并独立辩论文件（解析内嵌 JSON）
        "debate_rounds": ind_payload.get("debate_rounds") or _load_industry_debate(name),
        # Chokepoint 产业链瓶颈地图（行业层增强，透传给前端展示；无则空，不影响旧行业单元）
        "chokepoint_map": ind_payload.get("chokepoint_map", []),
        "top_chokepoints": ind_payload.get("top_chokepoints", []),
        # 瓶颈递归上溯深挖链（2026-06-19）：payload 内优先，缺则合并独立 drill 文件
        "deep_chokepoint_chains": ind_payload.get("deep_chokepoint_chains") or _load_industry_drill(name),
        # D0-2 产业链→个股连接（投资地图：瓶颈环节→推荐个股→卡位排序，实时同步个股最新评级）
        "investment_map": fresh_inv_map,
        "analysts": ind_payload.get("analysts", {}),
        # 2026-06-14 行业层 critic 复核 + 7 把辩证尺 + 未来市场必查模块全透传
        "industry_future_market": ind_payload.get("industry_future_market", {}),
        # 前瞻视野（近端日历 + 中期路径 + 情景推演）+ 证据链 + 数据质量（独立完整报告页需要）
        "forward_view": ind_payload.get("forward_view", {}),
        "evidence": ind_payload.get("evidence", []),
        "data_quality": ind_payload.get("data_quality", ""),
        "value_creation_industry": ind_payload.get("value_creation_industry", {}),
        "fund_recommendation": ind_payload.get("fund_recommendation", {}),
        "credibility": ind_payload.get("credibility", {}),
        "reflection": ind_payload.get("reflection", {}),
        "data_status": ind_payload.get("data_status", ""),
        "intra_alloc_unit": decorate_unit(f"alloc:industry:{name}", alloc_env, units),
        "stock_weights": (alloc_env or {}).get("payload", {}).get("stock_weights", []) if alloc_env else [],
    }
    stocks = []
    for uid, env in units.items():
        if uid.startswith("stock:"):
            pl = env.get("payload", {})
            if pl.get("industry") == name:
                stocks.append({**decorate_unit(uid, env, units),
                               "code": pl.get("code"), "name": pl.get("name"),
                               "rating": pl.get("rating"), "target_price": pl.get("target_price")})
    resp["stocks"] = stocks

    # D0-6 (2026-06-13) 基金穿透 — 间接持仓: 实时算聚合 (不依赖 data/v4/inputs/ 磁盘文件,因其 gitignore)
    # 数据流: holdings.json _fund_passthrough → v4_classifier 透传 → v4_aggregator 聚合
    try:
        from pathlib import Path
        holdings_path = Path("data/v4/_inputs/holdings.json")
        if holdings_path.exists():
            from app.services.v4.v4_classifier import classify_holdings
            from app.services.v4.v4_aggregator import aggregate_to_industry_with_direct_stocks
            h = json.loads(holdings_path.read_text(encoding="utf-8"))
            classified = classify_holdings(h.get("positions", []) or [])
            # 反查 stocks 单元的 industry 映射
            stock_inds = {}
            for uid2, env2 in units.items():
                if uid2.startswith("stock:"):
                    p2 = env2.get("payload", {}) or {}
                    code2 = p2.get("code")
                    ind2 = p2.get("industry")
                    if code2 and ind2:
                        stock_inds[code2] = ind2
            agg = aggregate_to_industry_with_direct_stocks(classified, stock_inds)
            ind_data = (agg.get("industries") or {}).get(name) or {}
            resp["indirect_holdings"] = {
                "direct_yi": ind_data.get("direct_yi", 0),
                "indirect_yi": ind_data.get("indirect_yi", 0),
                "total_yi": ind_data.get("total_yi", 0),
                "contributing_funds": ind_data.get("contributing_funds", []),
                "summary": agg.get("summary", {}),
            }
    except Exception as e:
        # 任何错都不影响主流程,行业页仍正常显示其他内容
        resp["indirect_holdings"] = None

    return resp


def build_stock_detail(units: Dict[str, Dict[str, Any]], code: str) -> Dict[str, Any]:
    """个股详情（D0-3）：四维质量闸门 + forward_view + 估值推导 + 止损纪律 + historical_alpha。

    解决"个股看不到详细分析+不知买点怎么来+回测前端看不到"。透传 stock payload 全字段。
    2026-06-13 加: 反查 industry payload 构造 chain_positioning(产业链卡位 — 服务"全面"目标)。
    """
    env = units.get(f"stock:{code}")
    p = (env or {}).get("payload", {}) if env else {}
    industry = p.get("industry")

    # D0-4 产业链卡位反查(服务"全面"目标 — 让个股页能看到行业层投资地图视角):
    # 从 industry payload.investment_map 找到本股所在条目 + 同环节其他标的 + 卡位排序
    chain_positioning = None
    industry_weight_pct = None  # 服务"可执行": 仓位计算器需要
    if industry:
        ind_env = units.get(f"industry:{industry}")
        ind_p = (ind_env or {}).get("payload", {}) if ind_env else {}
        inv_map = ind_p.get("investment_map") or []

        # 反查行业内配比 alloc:industry:<本股行业> 的 stock_weights
        alloc_ind_env = units.get(f"alloc:industry:{industry}")
        alloc_p = (alloc_ind_env or {}).get("payload", {}) if alloc_ind_env else {}
        for w in alloc_p.get("stock_weights", []) or []:
            if w.get("code") == code:
                industry_weight_pct = w.get("target_weight")
                break

        # 找到本股所在的 chokepoint(瓶颈环节)
        my_entry = None
        for item in inv_map:
            rec = (item.get("recommended") or "").strip()
            entry_code = rec.split()[0] if rec else ""
            if entry_code == code:
                my_entry = item
                break

        if my_entry:
            my_chokepoint = my_entry.get("chokepoint")
            # 找同环节(或邻接环节)的其他标的 — 列出 top 3,本股置顶
            same_or_near = []
            for item in inv_map:
                rec = (item.get("recommended") or "").strip()
                entry_code = rec.split()[0] if rec else ""
                # 同 chokepoint 或同行业 top 3
                same_or_near.append({
                    "rank": item.get("rank"),
                    "recommended": rec,
                    "chokepoint": item.get("chokepoint"),
                    "is_self": entry_code == code,
                    "rating": item.get("rating"),
                    "target_price_live": item.get("target_price_live"),
                    "why": item.get("why"),
                })
            same_or_near.sort(key=lambda x: x.get("rank") or 99)

            chain_positioning = {
                "industry": industry,
                "chokepoint": my_chokepoint,
                "my_rank": my_entry.get("rank"),
                "my_why": my_entry.get("why"),
                "industry_top": same_or_near[:5],  # top 5 让用户看到本股 + 横向比较
                "industry_conclusion": (ind_p.get("verdict") or {}).get("investment_conclusion"),
                "data_source": "industry_unit_investment_map",
            }

    return {
        "code": code,
        "name": p.get("name"),
        "industry": industry,
        "stock_unit": decorate_unit(f"stock:{code}", env, units),
        # 评级与买卖 (兼容新 schema: 从 verdict.stance 推断 rating)
        "rating": p.get("rating") or _stance_to_rating(p.get("verdict", {})),
        "target_price": p.get("target_price") or _extract_target_price(p),
        "entry_price_range": p.get("entry_price_range") or _extract_entry_range(p),
        "price_at_judgment": p.get("price_at_judgment"),
        # D0-4 一句话总结(服务"可信"目标 - 核心判断不绕弯)
        "verdict_oneliner": p.get("verdict_oneliner") or (p.get("verdict") or {}).get("summary"),
        # D0-4 产业链卡位(服务"全面"目标 - 连接行业层)
        "chain_positioning": chain_positioning,
        # D0-4 行业内目标权重(服务"可执行"目标 - 仓位计算器需要)
        "industry_weight_pct": industry_weight_pct,
        # D0-1 估值推导链(买点怎么来)
        "valuation_basis": p.get("valuation_basis"),
        # D0-4 可信度(服务"可信"目标 - critic 评审过程: 从 X 分迭代到 Y 分 ACCEPT)
        "credibility": p.get("credibility") or _extract_credibility(p),
        # 预期差 + 四维质量闸门
        "expectation_gap": p.get("expectation_gap") or ((p.get("valuation_basis") or {}).get("expectation_gap") if isinstance(p.get("valuation_basis"), dict) else None),
        "chokepoint_score": p.get("chokepoint_score"),
        "discovery_level": p.get("discovery_level"),
        "business_quality": p.get("business_quality"),
        "position_nature": p.get("position_nature"),
        # D 阶段 5+1 五力深做(2026-06-13 拆分): 5 力 level + cross_force_dynamics + weakest_link + moat_durability + monitoring_signals
        "five_forces": p.get("five_forces") or p.get("five_forces_summary") or _fallback_five_forces(p),
        # D0-5 TradingAgents 对齐(2026-06-13): 3 方风险辩论 + sentiment + memory + forward_view 6 维 + 数据追溯
        "risk_debate_summary": p.get("risk_debate_summary") or _extract_risk_debate(p),
        "risk_debate_full": p.get("risk_debate_full"),
        "sentiment_view": p.get("sentiment_view"),
        "sentiment_full": p.get("sentiment_full"),
        "memory_used": p.get("memory_used") or (p.get("reflection") or {}).get("memory_used") or [],
        "worst_case": p.get("worst_case") or _extract_worst_case(p),
        "downside": p.get("downside"),
        "sell_discipline": p.get("sell_discipline") or _extract_sell_discipline(p),
        "thesis": p.get("thesis"),
        "risks": p.get("risks") or _extract_risks(p),
        "confidence": p.get("confidence") if p.get("confidence") is not None else (p.get("verdict") or {}).get("confidence"),
        # 前瞻 (D0-5 加 6 维多维推演: market_regime/liquidity/cycle/β/comparable_matrix/pricing_power)
        "forward_view": p.get("forward_view"),
        # 辩论 + 反思
        "debate_rounds": p.get("debate_rounds", []),
        "analysts": p.get("analysts") or _fallback_analysts(p),
        "reflection": p.get("reflection"),
        # C 阶段 回测准确率(前端展示)
        "historical_alpha": p.get("historical_alpha"),
        "evidence": p.get("evidence", []),
        # D0-8 新 schema 透传(action_plan/stance verdict/critic_evaluation 让前端可逐步迁移)
        "verdict_v2": p.get("verdict") if isinstance(p.get("verdict"), dict) else None,
        "action_plan": p.get("action_plan") if isinstance(p.get("action_plan"), dict) else None,
        "anchoring_check": p.get("anchoring_check"),
        "valuation_cross_check": p.get("_valuation_cross_check") or (p.get("valuation_basis") or {}).get("valuation_cross_check") if isinstance(p.get("valuation_basis"), dict) else p.get("_valuation_cross_check"),
        "product_subdivision": p.get("product_subdivision") or p.get("product_subdivision_stress_test"),
        "sensitivity_matrix": (
            (p.get("valuation_basis") or {}).get("sensitivity_matrix_3x3")
            or (p.get("valuation_basis") or {}).get("sensitivity_matrix")
        ) if isinstance(p.get("valuation_basis"), dict) else None,
        "tail_risk": p.get("tail_risk_joint_scenario_modeling"),
        "data_status_overall": p.get("data_status_overall"),
        "critic_evaluation": p.get("critic_evaluation"),
        # 价值创造维度(2026-06-14 用户拍板补全): TAM/渗透率 + ROIC vs WACC + 管理层资本配置 + 正向DCF
        "value_creation": p.get("value_creation"),
        "dcf_intrinsic": p.get("dcf_intrinsic") or (p.get("valuation_basis") or {}).get("dcf_intrinsic") if isinstance(p.get("valuation_basis"), dict) else p.get("dcf_intrinsic"),
        # StockFullReport 精排字段透传(2026-06-19 loop iter10: 前端 iter2 加了展示但后端从未透传, 静态快照下精排 UI 全白板)
        "three_dimension": p.get("three_dimension"),                       # 三维评分(好公司×好价格×好未来)
        "peer_anchor": p.get("peer_anchor"),                               # 同业锚定
        "st_risk_quantified": p.get("st_risk_quantified"),                 # ST/退市风险量化
        "product_decomposition": p.get("product_decomposition"),           # 产品分部利润表
        "product_subdivision_deep": p.get("product_subdivision_deep"),     # 产品业务拆解(深)
        "sensitivity_matrix_3x3": p.get("sensitivity_matrix_3x3"),         # 敏感性矩阵(顶层,区别于 valuation_basis 内的)
        "comparable_path_quantified": p.get("comparable_path_quantified"), # 可比路径量化
        "forward_view_6dim": p.get("forward_view_6dim"),                   # 前瞻6维(顶层)
        "risk_consensus_from_3way": p.get("risk_consensus_from_3way"),     # 3方风险共识
        "bear_data_correction": p.get("bear_data_correction"),             # 空头数据纠错
        "value_creation_verified": p.get("value_creation_verified"),       # 价值创造验证块
        "upstream_drill": p.get("upstream_drill"),                         # 个股上游供应链深挖(iter 个股层新增)
    }
