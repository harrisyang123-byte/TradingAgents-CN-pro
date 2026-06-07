"""v4_query.py — v4 只读查询服务（NFR1.2：走缓存秒级响应，不触发 LLM）

读取单元信封（Mongo v4_units 优先，文件落盘回退），计算实时状态色，
组装三层 Tab 所需结构。绝不触发任何 LLM / 重计算。
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from app.services.v4 import asset_classes as ac
from app.services.v4 import v4_state, v4_unit_store as store


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
        except Exception:
            pass
    # 文件回退（本地运行未导入 Mongo 时）
    if not units:
        try:
            store.rebuild_index()
            for u in store.list_units():
                env = store.read_unit(u["unit_id"])
                if env:
                    units[env["unit_id"]] = env
        except Exception:
            pass
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
