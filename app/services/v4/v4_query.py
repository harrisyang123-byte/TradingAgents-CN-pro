"""v4_query.py — v4 只读查询服务（NFR1.2：走缓存秒级响应，不触发 LLM）

读取单元信封（Mongo v4_units 优先，文件落盘回退），计算实时状态色，
组装三层 Tab 所需结构。绝不触发任何 LLM / 重计算。
"""

from __future__ import annotations

import logging
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
    }


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
    resp: Dict[str, Any] = {
        "industry": name,
        "industry_unit": decorate_unit(f"industry:{name}", ind_env, units),
        "verdict": ind_payload.get("verdict"),
        "debate_rounds": ind_payload.get("debate_rounds", []),
        # Chokepoint 产业链瓶颈地图（行业层增强，透传给前端展示；无则空，不影响旧行业单元）
        "chokepoint_map": ind_payload.get("chokepoint_map", []),
        "top_chokepoints": ind_payload.get("top_chokepoints", []),
        # D0-2 产业链→个股连接（投资地图：瓶颈环节→推荐个股→卡位排序）
        "investment_map": ind_payload.get("investment_map", []),
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
    return resp


def build_stock_detail(units: Dict[str, Dict[str, Any]], code: str) -> Dict[str, Any]:
    """个股详情（D0-3）：四维质量闸门 + forward_view + 估值推导 + 止损纪律 + historical_alpha。

    解决"个股看不到详细分析+不知买点怎么来+回测前端看不到"。透传 stock payload 全字段。
    """
    env = units.get(f"stock:{code}")
    p = (env or {}).get("payload", {}) if env else {}
    return {
        "code": code,
        "name": p.get("name"),
        "industry": p.get("industry"),
        "stock_unit": decorate_unit(f"stock:{code}", env, units),
        # 评级与买卖
        "rating": p.get("rating"),
        "target_price": p.get("target_price"),
        "entry_price_range": p.get("entry_price_range"),
        "price_at_judgment": p.get("price_at_judgment"),
        # D0-1 估值推导链(买点怎么来)
        "valuation_basis": p.get("valuation_basis"),
        # 预期差 + 四维质量闸门
        "expectation_gap": p.get("expectation_gap"),
        "chokepoint_score": p.get("chokepoint_score"),
        "discovery_level": p.get("discovery_level"),
        "business_quality": p.get("business_quality"),
        "position_nature": p.get("position_nature"),
        # D 阶段 5+1 五力深做(2026-06-13 拆分): 5 力 level + cross_force_dynamics + weakest_link + moat_durability + monitoring_signals
        "five_forces": p.get("five_forces"),
        "worst_case": p.get("worst_case"),
        "downside": p.get("downside"),
        "sell_discipline": p.get("sell_discipline", []),
        "thesis": p.get("thesis"),
        "risks": p.get("risks", []),
        "confidence": p.get("confidence"),
        # 前瞻
        "forward_view": p.get("forward_view"),
        # 辩论 + 反思
        "debate_rounds": p.get("debate_rounds", []),
        "analysts": p.get("analysts", {}),
        "reflection": p.get("reflection"),
        # C 阶段 回测准确率(前端展示)
        "historical_alpha": p.get("historical_alpha"),
        "evidence": p.get("evidence", []),
    }
