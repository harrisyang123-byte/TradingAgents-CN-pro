"""用户行业关注列表（Watchlist）API"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

from app.routers.auth_db import get_current_user
from app.core.database import get_mongo_db
from app.core.response import ok

router = APIRouter(prefix="/watchlist", tags=["watchlist"])
logger = logging.getLogger("webapi")

import logging


class AddWatchlistRequest(BaseModel):
    industry: str
    note: Optional[str] = None


@router.get("", response_model=dict)
async def list_watchlist(current_user: dict = Depends(get_current_user)):
    """获取用户关注的行业列表"""
    db = get_mongo_db()
    items = await db["watchlist"].find(
        {"user_id": current_user["id"]}
    ).sort("created_at", -1).to_list(100)
    result = []
    for item in items:
        result.append({
            "industry": item.get("industry", ""),
            "note": item.get("note", ""),
            "created_at": item.get("created_at", ""),
        })
    return ok({"items": result})


@router.post("", response_model=dict)
async def add_watchlist(
    payload: AddWatchlistRequest,
    current_user: dict = Depends(get_current_user),
):
    """添加关注的行业"""
    db = get_mongo_db()
    existing = await db["watchlist"].find_one({
        "user_id": current_user["id"],
        "industry": payload.industry,
    })
    if existing:
        return ok({"message": "该行业已在关注列表"})

    doc = {
        "user_id": current_user["id"],
        "industry": payload.industry,
        "note": payload.note or "",
        "created_at": datetime.utcnow().isoformat(),
    }
    await db["watchlist"].insert_one(doc)
    return ok({"message": "已添加关注行业", "industry": payload.industry})


@router.delete("/{industry}", response_model=dict)
async def delete_watchlist(
    industry: str,
    current_user: dict = Depends(get_current_user),
):
    """删除关注的行业"""
    db = get_mongo_db()
    result = await db["watchlist"].delete_one({
        "user_id": current_user["id"],
        "industry": industry,
    })
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail=f"未找到关注行业: {industry}")
    return ok({"message": "已取消关注", "industry": industry})
