"""持仓组合分析 API — 两阶段（L1计划 + L2-L4执行）"""

from fastapi import APIRouter, Depends, HTTPException
from typing import Optional, List
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
    """触发 L1 市场扫描，返回推荐行业计划"""
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
        "current_step": "准备L1市场扫描",
        "user_goal": req.goal,
        "created_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat(),
    })

    # 使用 asyncio.create_task 后台执行（motor MongoDB 绑定主事件循环，不能用线程池）
    asyncio.create_task(_execute_l1(task_id, user_id, req.goal))
    return PlanResponse(task_id=task_id, status="running")


async def _execute_l1(task_id: str, user_id: str, goal: str = ""):
    """后台执行 L1 市场扫描"""
    from app.services.portfolio_service import PortfolioService
    from app.services.industry_classifier import classify_holdings_industries
    from app.services.config_service import ConfigService
    from tradingagents.graph.advisor_graph import AdvisorGraph
    from tradingagents.llm_clients.provider_keys import normalize_provider_key
    from tradingagents.graph.trading_graph import create_llm_by_provider

    try:
        db2 = get_mongo_db()
        portfolio_svc = PortfolioService()
        portfolio_summary = await portfolio_svc.get_portfolio_summary(user_id)

        config_svc = ConfigService()
        llm_config = await config_svc.get_analysis_config(user_id)

        provider = normalize_provider_key(llm_config.get("llm_provider", "qwen"))
        llm = create_llm_by_provider(
            provider=provider,
            model=llm_config.get("deep_think_llm", llm_config.get("quick_think_llm", "qwen-plus")),
            backend_url=llm_config.get("backend_url", ""),
            temperature=0.7,
            max_tokens=4000,
            timeout=180,
            api_key=llm_config.get("deep_api_key") or llm_config.get("quick_api_key"),
        )

        advisor = AdvisorGraph(llm, config=llm_config)

        # 从持仓反推行业分布
        positions = portfolio_summary.get("positions", [])
        industry_map = await classify_holdings_industries(db2, positions)
        portfolio_industries = []
        for ind_name, pos_list in industry_map.items():
            total_weight = sum(p.get("weight", 0) for p in pos_list)
            codes = [p.get("code", "") for p in pos_list]
            portfolio_industries.append({
                "industry": ind_name,
                "weight": round(total_weight, 2),
                "position_count": len(pos_list),
                "codes": codes,
            })
        # 按仓位降序
        portfolio_industries.sort(key=lambda x: x["weight"], reverse=True)

        def progress_cb(label: str, text: str = ""):
            r = get_redis_client()
            if r:
                try:
                    channel = f"task_progress:{task_id}"
                    payload = json.dumps({
                        "type": "node_complete",
                        "task_id": task_id,
                        "node": label,
                        "stage": "1/1",
                        "text": text[:800] if text else "",
                        "progress_pct": 50,
                    }, ensure_ascii=False)
                    r.publish(channel, payload)
                    r.set(f"progress:{task_id}", json.dumps({
                        "status": "running",
                        "current_step": label,
                        "progress_percentage": 50,
                    }))
                    r.expire(f"progress:{task_id}", 3600)
                except Exception:
                    pass

        result = advisor.propagate_l1_plan(
            portfolio_summary=portfolio_summary,
            portfolio_industries=portfolio_industries,
            user_goal=goal,
            progress_callback=progress_cb,
        )

        # 写入 industry_coverage（全量覆盖，status=completed，depth=light/deep）
        completed_at = datetime.utcnow().isoformat()
        industries = result.get("industries", [])
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
                    "depth": ind.get("depth", "light"),
                    "go_nogo": ind.get("recommendation", ind.get("go_nogo", "")),
                    "confidence": ind.get("confidence", ""),
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
                "result": result,
                "industries": industries,
                "macro_judge_verdict": result.get("macro_judge_verdict", ""),
                "market_intel": result.get("market_intel", {}),
                "market_debate_history": result.get("market_debate_history", ""),
                "elapsed_seconds": result.get("elapsed_seconds", 0),
                "completed_at": completed_at,
                "updated_at": completed_at,
            }},
        )

        # 发送完成通知
        try:
            from app.core.ws_manager import manager as ws_manager
            await ws_manager.send_personal_message(
                {"type": "l1_plan_completed", "task_id": task_id, "industries_count": len(industries)},
                user_id,
            )
        except Exception:
            pass

    except Exception as e:
        logger.error(f"L1 计划执行失败: {e}", exc_info=True)
        try:
            db2 = get_mongo_db()
            await db2["portfolio_advice"].update_one(
                {"advice_id": task_id},
                {"$set": {"status": "FAILED", "error": str(e)[:500], "updated_at": datetime.utcnow().isoformat()}},
            )
        except Exception:
            pass


@router.post("/execute")
async def execute_l2_l4(
    req: ExecuteRequest,
    current_user: dict = Depends(get_current_user),
):
    """执行 L2-L4 完整分析（用户确认行业后）"""
    user_id = current_user["id"]
    db = get_mongo_db()

    # 验证 task 存在
    plan = await db["portfolio_advice"].find_one({"advice_id": req.task_id})
    if not plan:
        raise HTTPException(status_code=404, detail="任务不存在")
    if plan.get("status") == "FAILED":
        raise HTTPException(status_code=400, detail="L1 计划已失败，请重新开始")
    if not req.selected_industries:
        raise HTTPException(status_code=400, detail="请至少选择一个行业")

    if plan.get("status") != "L1_COMPLETED":
        await db["portfolio_advice"].update_one(
            {"advice_id": req.task_id},
            {"$set": {"status": "L1_COMPLETED", "updated_at": datetime.utcnow().isoformat()}},
        )

    # 后台执行 L2-L4
    execute_id = f"{req.task_id}_exec"
    asyncio.create_task(_execute_l2_l4(req.task_id, execute_id, user_id, req.selected_industries))
    return PlanResponse(task_id=execute_id, status="running")


async def _execute_l2_l4(task_id: str, execute_id: str, user_id: str, selected_industries: List[str]):
    """后台执行 L2-L4 完整分析"""
    from app.services.portfolio_advisor_service import PortfolioAdvisorService
    from app.services.portfolio_service import PortfolioService
    from app.services.config_service import ConfigService
    from tradingagents.graph.advisor_graph import AdvisorGraph
    from tradingagents.llm_clients.provider_keys import normalize_provider_key
    from tradingagents.graph.trading_graph import create_llm_by_provider

    try:
        db2 = get_mongo_db()
        portfolio_svc = PortfolioService()
        portfolio_summary = await portfolio_svc.get_portfolio_summary(user_id)
        position_codes = [p["code"] for p in portfolio_summary.get("positions", [])]

        # 准备 tier1_reports
        advisor_svc = PortfolioAdvisorService()
        tier1_reports = await advisor_svc._prepare_tier1_reports(position_codes)

        config_svc = ConfigService()
        llm_config = await config_svc.get_analysis_config(user_id)
        provider = normalize_provider_key(llm_config.get("llm_provider", "qwen"))
        llm = create_llm_by_provider(
            provider=provider,
            model=llm_config.get("deep_think_llm", llm_config.get("quick_think_llm", "qwen-plus")),
            backend_url=llm_config.get("backend_url", ""),
            temperature=0.7,
            max_tokens=4000,
            timeout=180,
            api_key=llm_config.get("deep_api_key") or llm_config.get("quick_api_key"),
        )

        advisor = AdvisorGraph(llm, config=llm_config)

        stage_map = {
            "L1": "1/4", "L2": "2/4", "L3": "3/4", "L4": "4/4",
        }

        def progress_cb(label: str, text: str = ""):
            r = get_redis_client()
            if r:
                try:
                    stage = "1/4"
                    for prefix, s in stage_map.items():
                        if label.startswith(prefix):
                            stage = s
                            break
                    channel = f"task_progress:{execute_id}"
                    payload = json.dumps({
                        "type": "node_complete",
                        "task_id": execute_id,
                        "node": label,
                        "stage": stage,
                        "text": text[:800] if text else "",
                    }, ensure_ascii=False)
                    r.publish(channel, payload)
                    r.set(f"progress:{execute_id}", json.dumps({
                        "status": "running",
                        "current_step": label,
                        "progress_percentage": 0,
                    }))
                    r.expire(f"progress:{execute_id}", 3600)
                except Exception:
                    pass

        await db2["portfolio_advice"].update_one(
            {"advice_id": task_id},
            {"$set": {"status": "RUNNING", "current_step": "开始L2-L4分析", "updated_at": datetime.utcnow().isoformat()}},
        )

        result = advisor.propagate_advice(
            portfolio_summary=portfolio_summary,
            tier1_reports=tier1_reports,
            progress_callback=progress_cb,
            selected_industries=selected_industries,
        )

        # 写入 portfolio_advice
        completed_at = datetime.utcnow().isoformat()
        await db2["portfolio_advice"].update_one(
            {"advice_id": task_id},
            {"$set": {
                "status": "COMPLETED",
                "prescription": result.get("prescription", []),
                "cio_verdict": result.get("cio_verdict", ""),
                "analyst_assessment": result.get("analyst_assessment", ""),
                "strategist_assessment": result.get("strategist_assessment", ""),
                "scout_assessment": result.get("scout_assessment", ""),
                "macro_judge_verdict": result.get("macro_judge_verdict", ""),
                "market_intel": result.get("market_intel", {}),
                "stock_candidates": result.get("stock_candidates", []),
                "stock_judge_verdict": result.get("stock_judge_verdict", ""),
                "risk_director_review": result.get("risk_director_review", ""),
                "market_debate_history": result.get("market_debate_history", ""),
                "stock_debate_history": result.get("stock_debate_history", ""),
                "debate_history": result.get("debate_history", ""),
                "selected_industries": selected_industries,
                "elapsed_seconds": result.get("elapsed_seconds", 0),
                "completed_at": completed_at,
                "updated_at": completed_at,
            }},
        )

        # 双写 analysis_reports
        try:
            market_intel = result.get("market_intel", {})
            await db2["analysis_reports"].insert_one({
                "report_type": "portfolio",
                "stock_symbol": f"portfolio_{task_id}",
                "stock_name": f"组合建议 {completed_at[:10]}",
                "summary": (result.get("cio_verdict", "") or "")[:500],
                "recommendation": f"覆盖 {len(selected_industries)} 个行业, {len(result.get('prescription', []))} 条处方",
                "created_at": completed_at,
                "status": "completed",
                "analysts": ["market_strategist", "contrarian", "macro_judge", "scout", "stock_contrarian", "stock_judge", "analyst", "strategist", "cio", "risk_director"],
                "research_depth": 2,
                "market_type": "portfolio",
                "instrument_type": "portfolio",
                "model_info": "Tier2-4Level",
                "reports": {
                    "market_intel": market_intel,
                    "stock_candidates": result.get("stock_candidates", []),
                    "analyst_assessment": result.get("analyst_assessment", ""),
                    "strategist_assessment": result.get("strategist_assessment", ""),
                    "scout_assessment": result.get("scout_assessment", ""),
                    "cio_verdict": result.get("cio_verdict", ""),
                    "risk_director_review": result.get("risk_director_review", ""),
                },
                "advice_id": task_id,
                "user_id": user_id,
            })
        except Exception as e:
            logger.warning(f"双写失败（非致命）: {e}")

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
        logger.error(f"L2-L4 执行失败: {e}", exc_info=True)
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
            "macro_judge_verdict": doc.get("macro_judge_verdict", ""),
        }
    elif status == "completed":
        result_data = {
            "prescription": doc.get("prescription", []),
            "cio_verdict": doc.get("cio_verdict", ""),
            "selected_industries": doc.get("selected_industries", []),
            "elapsed_seconds": doc.get("elapsed_seconds", 0),
            "macro_judge_verdict": doc.get("macro_judge_verdict", ""),
            "stock_judge_verdict": doc.get("stock_judge_verdict", ""),
            "analyst_assessment": doc.get("analyst_assessment", ""),
            "strategist_assessment": doc.get("strategist_assessment", ""),
            "scout_assessment": doc.get("scout_assessment", ""),
            "risk_director_review": doc.get("risk_director_review", ""),
            "market_intel": doc.get("market_intel", {}),
            "stock_candidates": doc.get("stock_candidates", []),
            "market_debate_history": doc.get("market_debate_history", ""),
            "stock_debate_history": doc.get("stock_debate_history", ""),
            "debate_history": doc.get("debate_history", ""),
        }

    return {
        "status": status,
        "current_step": doc.get("current_step", "分析中..."),
        "progress": 30 if status == "l1_completed" else (100 if status == "completed" else 10),
        "result": result_data,
        "error": doc.get("error"),
    }


async def _get_planned_industries(user_id: str, db):
    """获取用户最近一次 L1 分析的行业列表（status=completed，按 analyzed_at 降序取最新一批）"""
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
        "depth": d.get("depth", "light"),
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
    """手动强制刷新某行业的辩论缓存（立即过期，下次分析重新研究）

    将 industry_coverage 中对应记录的 expires_at 设为当前时间，
    下次分析启动时该行业将触发完整的辩论流程。
    """
    db = get_mongo_db()
    now_iso = datetime.utcnow().isoformat()
    result = await db["industry_coverage"].update_one(
        {"user_id": current_user["id"], "industry_name": industry_name},
        {"$set": {"expires_at": now_iso, "updated_at": now_iso}},
    )
    if result.matched_count == 0:
        logger.info(f"[Refresh] 行业 {industry_name} 无缓存记录，跳过")
        return {"success": True, "message": f"行业 {industry_name} 无缓存记录，无需刷新"}

    logger.info(f"[Refresh] 行业 {industry_name} 缓存已刷新")
    return {"success": True, "message": f"行业 {industry_name} 缓存已刷新，下次分析将重新研究"}
