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
from app.services.v4 import v4_unit_store as store

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
    """Tab2：大类详情。权益→行业列表；非权益→方案 payload。"""
    units = await v4_query.load_user_units(_db(), current_user["id"])
    return ok(v4_query.build_asset_detail(units, asset_class))


@router.get("/industry/{name}", response_model=dict)
async def v4_industry_detail(name: str, current_user: dict = Depends(get_current_user)):
    """Tab3：行业深辩报告 + 个股列表 + 行业内配比。"""
    units = await v4_query.load_user_units(_db(), current_user["id"])
    return ok(v4_query.build_industry_detail(units, name))


@router.get("/stock/{code}", response_model=dict)
async def v4_stock_detail(code: str, current_user: dict = Depends(get_current_user)):
    """个股详情（D0-3）：四维 + forward_view + 估值推导 + 止损 + historical_alpha。"""
    units = await v4_query.load_user_units(_db(), current_user["id"])
    return ok(v4_query.build_stock_detail(units, code))


@router.post("/import", response_model=dict)
async def v4_import(payload: dict, current_user: dict = Depends(get_current_user)):
    """幂等导入单元信封（按 unit_id upsert，AC9.5）。亦可用 scripts/import_v4.py 脚本直写。"""
    db = _db()
    if db is None:
        return ok({"imported": 0, "message": "Mongo 不可用"})
    envelopes = payload.get("units") or ([payload] if payload.get("unit_id") else [])
    n = 0
    rejected: list[str] = []
    for env in envelopes:
        uid = env.get("unit_id")
        if not uid:
            rejected.append("(缺少 unit_id)")
            continue
        # 校验 unit_id 格式合法（防脏数据入库）：非法前缀/格式直接拒绝
        try:
            store.parse_unit_id(uid)
        except ValueError as e:
            logger.warning("v4 import 拒绝非法 unit_id=%r: %s", uid, e)
            rejected.append(str(uid))
            continue
        doc = dict(env)
        doc["user_id"] = current_user["id"]
        await db["v4_units"].update_one(
            {"user_id": current_user["id"], "unit_id": uid},
            {"$set": doc},
            upsert=True,
        )
        n += 1
    return ok({"imported": n, "rejected": rejected})
