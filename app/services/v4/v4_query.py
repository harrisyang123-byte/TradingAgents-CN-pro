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
    if not ce:
        return None
    return {
        "initial_score": ce.get("v1_score"),
        "critic_score": ce.get("v2_score") or ce.get("v1_score"),
        "final_verdict": ce.get("v2_recommendation") or ce.get("recommendation") or "ACCEPT",
        "reviewers": ["芒格", "段永平", "Serenity", "达里奥"],
        "issues_addressed": ce.get("v1_issues_addressed"),
    }


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
    resp: Dict[str, Any] = {
        "asset_class": asset_class,
        "label": ac.label_of(asset_class),
        "is_equity": ac.is_equity(asset_class),
        "max_drill_depth": ac.max_drill_depth(asset_class),
        "asset_unit": meta,
        "verdict": asset_payload.get("verdict"),
        "tradable": asset_payload.get("tradable", []),
        "holding_only_exposure": asset_payload.get("holding_only_exposure", 0),
        # §5.9 A：辩论与专项分析早已在信封里，此前被丢弃；所有大类通用（展示缺口非数据缺口）
        "debate_rounds": asset_payload.get("debate_rounds", []),
        "analysts": asset_payload.get("analysts", {}),
    }
    if not ac.is_equity(asset_class):
        plan_payload = (plan_env or {}).get("payload", {}) if plan_env else {}
        resp["plan_unit"] = decorate_unit(f"plan:{asset_class}", plan_env, units)
        resp["plan"] = plan_payload.get("plan") or asset_payload.get("plan")
    else:
        eq_alloc = units.get("alloc:equity_industries")
        resp["equity_industries_unit"] = decorate_unit("alloc:equity_industries", eq_alloc, units)
        resp["industries"] = (eq_alloc or {}).get("payload", {}).get("allocations", []) if eq_alloc else []
    return resp


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
        "debate_rounds": ind_payload.get("debate_rounds", []),
        # Chokepoint 产业链瓶颈地图（行业层增强，透传给前端展示；无则空，不影响旧行业单元）
        "chokepoint_map": ind_payload.get("chokepoint_map", []),
        "top_chokepoints": ind_payload.get("top_chokepoints", []),
        # D0-2 产业链→个股连接（投资地图：瓶颈环节→推荐个股→卡位排序，实时同步个股最新评级）
        "investment_map": fresh_inv_map,
        "analysts": ind_payload.get("analysts", {}),
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
        "five_forces": p.get("five_forces") or p.get("five_forces_summary"),
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
        "analysts": p.get("analysts", {}),
        "reflection": p.get("reflection"),
        # C 阶段 回测准确率(前端展示)
        "historical_alpha": p.get("historical_alpha"),
        "evidence": p.get("evidence", []),
        # D0-8 新 schema 透传(action_plan/stance verdict/critic_evaluation 让前端可逐步迁移)
        "verdict_v2": p.get("verdict") if isinstance(p.get("verdict"), dict) else None,
        "action_plan": p.get("action_plan") if isinstance(p.get("action_plan"), dict) else None,
        "anchoring_check": p.get("anchoring_check"),
        "product_subdivision": p.get("product_subdivision") or p.get("product_subdivision_stress_test"),
        "sensitivity_matrix": (
            (p.get("valuation_basis") or {}).get("sensitivity_matrix_3x3")
            or (p.get("valuation_basis") or {}).get("sensitivity_matrix")
        ) if isinstance(p.get("valuation_basis"), dict) else None,
        "tail_risk": p.get("tail_risk_joint_scenario_modeling"),
        "data_status_overall": p.get("data_status_overall"),
        "critic_evaluation": p.get("critic_evaluation"),
    }
