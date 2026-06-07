"""portfolio_v4.py — v4 只读 + 导入路由（FR-004 触发链路分离 / FR-008 / FR-009）

只读接口走 Mongo 缓存（文件回退），秒级响应、绝不触发 LLM（NFR1.2）。
无任何「触发 LLM」写接口——重计算只在 CLI/本地由 claude 调起（AC4.6）。
import 端点幂等 upsert（AC9.5）。鉴权复用 get_current_user。
"""

import logging
from typing import Optional

from fastapi import APIRouter, Depends

from app.core.database import get_mongo_db
from app.core.response import ok
from app.routers.auth_db import get_current_user
from app.services.v4 import asset_classes as ac
from app.services.v4 import v4_query

router = APIRouter(prefix="/portfolio/v4", tags=["portfolio-v4"])
logger = logging.getLogger("webapi")


def _db():
    try:
        return get_mongo_db()
    except Exception:
        return None


@router.get("/overview", response_model=dict)
async def v4_overview(current_user: dict = Depends(get_current_user)):
    """Tab1：七大类卡片 + 资产配比 + equity_quota（AC8.1 / AC8.5）。"""
    units = await v4_query.load_user_units(_db(), current_user["id"])
    data = v4_query.build_overview(units)
    data["has_data"] = bool(units)
    data["asset_classes"] = ac.ASSET_CLASSES  # 前端常量同源
    return ok(data)


@router.get("/units/status", response_model=dict)
async def v4_units_status(current_user: dict = Depends(get_current_user)):
    """全单元状态机视图（五色 + stale + cli_hint，AC8.4 / FR-005）。"""
    units = await v4_query.load_user_units(_db(), current_user["id"])
    return ok({"units": v4_query.build_units_status(units), "has_data": bool(units)})


@router.get("/asset/{asset_class}", response_model=dict)
async def v4_asset_detail(asset_class: str, current_user: dict = Depends(get_current_user)):
    """Tab2：大类详情。权益→行业列表（Task 3 填充）；非权益→方案 payload。"""
    units = await v4_query.load_user_units(_db(), current_user["id"])
    asset_env = units.get(f"asset:{asset_class}")
    plan_env = units.get(f"plan:{asset_class}")
    meta = v4_query.decorate_unit(f"asset:{asset_class}", asset_env, units)
    resp = {
        "asset_class": asset_class,
        "label": ac.label_of(asset_class),
        "is_equity": ac.is_equity(asset_class),
        "max_drill_depth": ac.max_drill_depth(asset_class),
        "asset_unit": meta,
        "verdict": (asset_env or {}).get("payload", {}).get("verdict") if asset_env else None,
        "tradable": (asset_env or {}).get("payload", {}).get("tradable", []) if asset_env else [],
        "holding_only_exposure": (asset_env or {}).get("payload", {}).get("holding_only_exposure", 0) if asset_env else 0,
    }
    if not ac.is_equity(asset_class):
        # 非权益：方案 payload（plan:<class> 优先，回退 asset 的 plan 字段）
        plan_payload = (plan_env or {}).get("payload", {}) if plan_env else {}
        resp["plan_unit"] = v4_query.decorate_unit(f"plan:{asset_class}", plan_env, units)
        resp["plan"] = plan_payload.get("plan") or (asset_env or {}).get("payload", {}).get("plan")
    else:
        # 权益：行业列表（Task 3 由 alloc:equity_industries + industry:* 提供）
        eq_alloc = units.get("alloc:equity_industries")
        resp["equity_industries_unit"] = v4_query.decorate_unit("alloc:equity_industries", eq_alloc, units)
        resp["industries"] = (eq_alloc or {}).get("payload", {}).get("allocations", []) if eq_alloc else []
    return ok(resp)


@router.get("/industry/{name}", response_model=dict)
async def v4_industry_detail(name: str, current_user: dict = Depends(get_current_user)):
    """Tab3：行业深辩报告 + 个股列表 + 行业内配比（Task 3 链路）。"""
    units = await v4_query.load_user_units(_db(), current_user["id"])
    ind_env = units.get(f"industry:{name}")
    alloc_env = units.get(f"alloc:industry:{name}")
    resp = {
        "industry": name,
        "industry_unit": v4_query.decorate_unit(f"industry:{name}", ind_env, units),
        "verdict": (ind_env or {}).get("payload", {}).get("verdict") if ind_env else None,
        "debate_rounds": (ind_env or {}).get("payload", {}).get("debate_rounds", []) if ind_env else [],
        "intra_alloc_unit": v4_query.decorate_unit(f"alloc:industry:{name}", alloc_env, units),
        "stock_weights": (alloc_env or {}).get("payload", {}).get("stock_weights", []) if alloc_env else [],
    }
    # 个股单元（从已落盘的 stock:* 中挑该行业的，前端按 stock_weights 关联）
    stocks = []
    for uid, env in units.items():
        if uid.startswith("stock:"):
            pl = env.get("payload", {})
            if pl.get("industry") == name:
                stocks.append({**v4_query.decorate_unit(uid, env, units),
                               "code": pl.get("code"), "name": pl.get("name"),
                               "rating": pl.get("rating"), "target_price": pl.get("target_price")})
    resp["stocks"] = stocks
    return ok(resp)


@router.post("/import", response_model=dict)
async def v4_import(payload: dict, current_user: dict = Depends(get_current_user)):
    """幂等导入单元信封（按 unit_id upsert，AC9.5）。亦可用 scripts/import_v4.py 脚本直写。"""
    db = _db()
    if db is None:
        return ok({"imported": 0, "message": "Mongo 不可用"})
    envelopes = payload.get("units") or ([payload] if payload.get("unit_id") else [])
    n = 0
    for env in envelopes:
        uid = env.get("unit_id")
        if not uid:
            continue
        doc = dict(env)
        doc["user_id"] = current_user["id"]
        await db["v4_units"].update_one(
            {"user_id": current_user["id"], "unit_id": uid},
            {"$set": doc},
            upsert=True,
        )
        n += 1
    return ok({"imported": n})
