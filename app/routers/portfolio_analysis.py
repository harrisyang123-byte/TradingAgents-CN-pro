"""持仓组合分析 API — 两阶段（plan + execute），由 v3 pipeline 驱动"""

from fastapi import APIRouter, Depends, HTTPException
from typing import List
import uuid
import asyncio
import json
import logging
from datetime import datetime
from pydantic import BaseModel

from app.routers.auth_db import get_current_user
from app.core.database import get_mongo_db, get_redis_client

router = APIRouter(prefix="/api/portfolio/analysis", tags=["portfolio-analysis"])
logger = logging.getLogger("webapi")


class PlanRequest(BaseModel):
    goal: str = ""


class ExecuteRequest(BaseModel):
    task_id: str
    selected_industries: List[str]


class PlanResponse(BaseModel):
    task_id: str
    status: str


@router.post("/plan")
async def start_l1_plan(
    req: PlanRequest = PlanRequest(),
    current_user: dict = Depends(get_current_user),
):
    """触发 v3 plan 阶段（collect + 行业分析），返回推荐行业"""
    user_id = current_user["id"]
    db = get_mongo_db()
    task_id = f"portfolio_l1_{uuid.uuid4().hex[:12]}"

    # 检查是否已有进行中的任务
    existing = await db["portfolio_advice"].find_one(
        {"user_id": user_id, "status": {"$in": ["GENERATING", "RUNNING"]}},
        sort=[("created_at", -1)],
    )
    if existing:
        raise HTTPException(status_code=409, detail="已有正在生成的组合建议，请等待完成")

    await db["portfolio_advice"].insert_one({
        "advice_id": task_id,
        "user_id": user_id,
        "status": "GENERATING",
        "current_step": "准备v3行业分析",
        "user_goal": req.goal,
        "created_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat(),
    })

    asyncio.create_task(_execute_plan(task_id, user_id, req.goal))
    return PlanResponse(task_id=task_id, status="running")


async def _execute_plan(task_id: str, user_id: str, goal: str = ""):
    """后台执行 v3 plan: collect + analyze --to industry"""
    from app.services.v3_advisor_runner import plan as v3_plan

    try:
        db2 = get_mongo_db()
        await db2["portfolio_advice"].update_one(
            {"advice_id": task_id},
            {"$set": {"current_step": "v3数据收集+行业分析", "updated_at": datetime.utcnow().isoformat()}},
        )

        result = await v3_plan(user_id)

        if result["error"]:
            raise RuntimeError(result["error"])

        industries = result["industries"]
        run_dir = result["run_dir"]
        completed_at = datetime.utcnow().isoformat()

        # 写入 industry_coverage
        for ind in industries:
            if not isinstance(ind, dict):
                continue
            ind_name = ind.get("industry", "")
            if not ind_name:
                continue
            await db2["industry_coverage"].update_one(
                {"user_id": user_id, "industry_name": ind_name},
                {"$set": {
                    "market": ind.get("market", "cn"),
                    "lifecycle": ind.get("lifecycle", ""),
                    "depth": "v3",
                    "go_nogo": ind.get("go_nogo", ""),
                    "confidence": ind.get("vitality_level", ""),
                    "reasoning": ind.get("reasoning", ""),
                    "priority": ind.get("priority", 0),
                    "analyzed_at": completed_at,
                    "advice_id": task_id,
                    "status": "completed",
                    "updated_at": completed_at,
                }},
                upsert=True,
            )

        # 更新 portfolio_advice
        await db2["portfolio_advice"].update_one(
            {"advice_id": task_id},
            {"$set": {
                "status": "L1_COMPLETED",
                "industries": industries,
                "run_dir": run_dir,
                "elapsed_seconds": 0,
                "completed_at": completed_at,
                "updated_at": completed_at,
            }},
        )

        # WebSocket 通知
        try:
            from app.core.ws_manager import manager as ws_manager
            await ws_manager.send_personal_message(
                {"type": "l1_plan_completed", "task_id": task_id, "industries_count": len(industries)},
                user_id,
            )
        except Exception:
            pass

    except Exception as e:
        logger.error(f"v3 plan 执行失败: {e}", exc_info=True)
        try:
            db2 = get_mongo_db()
            await db2["portfolio_advice"].update_one(
                {"advice_id": task_id},
                {"$set": {"status": "FAILED", "error": str(e)[:500], "updated_at": datetime.utcnow().isoformat()}},
            )
        except Exception:
            pass


@router.post("/execute")
async def execute_analysis(
    req: ExecuteRequest,
    current_user: dict = Depends(get_current_user),
):
    """执行 v3 完整分析（用户确认行业后）: scout → pm → synth → ingest"""
    user_id = current_user["id"]
    db = get_mongo_db()

    plan = await db["portfolio_advice"].find_one({"advice_id": req.task_id})
    if not plan:
        raise HTTPException(status_code=404, detail="任务不存在")
    if plan.get("status") == "FAILED":
        raise HTTPException(status_code=400, detail="计划已失败，请重新开始")
    if not req.selected_industries:
        raise HTTPException(status_code=400, detail="请至少选择一个行业")

    if plan.get("status") != "L1_COMPLETED":
        await db["portfolio_advice"].update_one(
            {"advice_id": req.task_id},
            {"$set": {"status": "L1_COMPLETED", "updated_at": datetime.utcnow().isoformat()}},
        )

    execute_id = f"{req.task_id}_exec"
    asyncio.create_task(_execute_full(req.task_id, execute_id, user_id, req.selected_industries, plan.get("run_dir", "")))
    return PlanResponse(task_id=execute_id, status="running")


async def _execute_full(task_id: str, execute_id: str, user_id: str, selected_industries: List[str], run_dir: str):
    """后台执行 v3 全量: write selected → analyze from scout → ingest"""
    from app.services.v3_advisor_runner import execute as v3_execute

    try:
        db2 = get_mongo_db()
        await db2["portfolio_advice"].update_one(
            {"advice_id": task_id},
            {"$set": {"status": "RUNNING", "current_step": "v3 Scout+PM+合成", "selected_industries": selected_industries, "updated_at": datetime.utcnow().isoformat()}},
        )

        result = await v3_execute(user_id, run_dir, selected_industries)

        if result["error"]:
            raise RuntimeError(result["error"])

        # ingest 已落库，标记完成（ingest 写了独立的 COMPLETED 文档；这里更新原 task 的状态）
        completed_at = datetime.utcnow().isoformat()
        await db2["portfolio_advice"].update_one(
            {"advice_id": task_id},
            {"$set": {
                "status": "COMPLETED",
                "completed_at": completed_at,
                "updated_at": completed_at,
            }},
        )

        # 更新 industry_coverage
        try:
            for ind_name in selected_industries:
                await db2["industry_coverage"].update_one(
                    {"user_id": user_id, "industry_name": ind_name},
                    {"$set": {
                        "status": "completed",
                        "advice_id": task_id,
                        "analyzed_at": completed_at,
                        "updated_at": completed_at,
                    }},
                )
        except Exception as e:
            logger.warning(f"industry_coverage 更新失败（非致命）: {e}")

    except Exception as e:
        logger.error(f"v3 execute 失败: {e}", exc_info=True)
        try:
            db2 = get_mongo_db()
            await db2["portfolio_advice"].update_one(
                {"advice_id": task_id},
                {"$set": {"status": "FAILED", "error": str(e)[:500], "updated_at": datetime.utcnow().isoformat()}},
            )
        except Exception:
            pass


@router.get("/{task_id}/status")
async def get_analysis_status(task_id: str, current_user: dict = Depends(get_current_user)):
    """轮询任务状态（SSE 回退方案）"""
    db = get_mongo_db()
    doc = await db["portfolio_advice"].find_one({"advice_id": task_id})
    if not doc:
        raise HTTPException(status_code=404, detail="任务不存在")

    status = doc.get("status", "UNKNOWN").lower()

    result_data = None
    if status == "l1_completed":
        industries = await _get_planned_industries(current_user["id"], db)
        result_data = {
            "market_intel": {"industries": industries},
            "industries": industries,
        }
    elif status == "completed":
        result_data = {
            "prescription": doc.get("prescription", []),
            "cio_verdict": doc.get("cio_verdict", ""),
            "selected_industries": doc.get("selected_industries", []),
            "elapsed_seconds": doc.get("elapsed_seconds", 0),
        }

    return {
        "status": status,
        "current_step": doc.get("current_step", "分析中..."),
        "progress": 30 if status == "l1_completed" else (100 if status == "completed" else 10),
        "result": result_data,
        "error": doc.get("error"),
    }


async def _get_planned_industries(user_id: str, db):
    """获取用户最近一次分析的行业列表"""
    latest = await db["industry_coverage"].find_one(
        {"user_id": user_id, "status": "completed"},
        sort=[("analyzed_at", -1)],
    )
    if not latest:
        return []
    latest_at = latest.get("analyzed_at", "")
    docs = await db["industry_coverage"].find(
        {"user_id": user_id, "status": "completed", "analyzed_at": latest_at}
    ).sort("priority", -1).to_list(None)
    return [{
        "industry": d.get("industry_name", ""),
        "market": d.get("market", "cn"),
        "lifecycle": d.get("lifecycle", ""),
        "depth": d.get("depth", "v3"),
        "go_nogo": d.get("go_nogo", ""),
        "confidence": d.get("confidence", ""),
        "reasoning": d.get("reasoning", ""),
        "priority": d.get("priority", 0),
    } for d in docs]


@router.post("/industry/{industry_name}/refresh")
async def refresh_industry_coverage(
    industry_name: str,
    current_user: dict = Depends(get_current_user),
):
    """手动强制刷新某行业的缓存（立即过期，下次分析重新研究）"""
    db = get_mongo_db()
    now_iso = datetime.utcnow().isoformat()
    result = await db["industry_coverage"].update_one(
        {"user_id": current_user["id"], "industry_name": industry_name},
        {"$set": {"expires_at": now_iso, "updated_at": now_iso}},
    )
    if result.matched_count == 0:
        return {"success": True, "message": f"行业 {industry_name} 无缓存记录，无需刷新"}

    return {"success": True, "message": f"行业 {industry_name} 缓存已刷新，下次分析将重新研究"}
