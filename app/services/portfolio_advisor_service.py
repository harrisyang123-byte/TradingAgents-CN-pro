"""组合顾问服务：数据准备 + 引擎编排 + 结果存储"""

import logging
import uuid
from datetime import datetime
from typing import Dict, Any, Optional, List
from concurrent.futures import ThreadPoolExecutor

from app.core.database import get_mongo_db

logger = logging.getLogger("webapi")

_executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="advisor")


class PortfolioAdvisorService:
    def __init__(self):
        self._db = None

    @property
    def db(self):
        if self._db is None:
            self._db = get_mongo_db()
        return self._db

    async def _prepare_tier1_reports(self, position_codes: List[str]) -> List[Dict[str, Any]]:
        """获取持仓标的的 Tier 1 分析报告"""
        if not position_codes:
            return []

        reports = []
        for code in position_codes:
            doc = await self.db["analysis_results"].find_one(
                {"$or": [
                    {"stock_code": code},
                    {"stock_symbol": code},
                    {"stock_code": {"$regex": f"^{code}"}},
                ]},
                sort=[("created_at", -1)],
            )
            if doc:
                reports.append({
                    "stock_code": doc.get("stock_code", code),
                    "stock_symbol": doc.get("stock_symbol", code),
                    "rating": doc.get("rating") or doc.get("recommendation", "N/A"),
                    "summary": doc.get("summary") or doc.get("final_decision", ""),
                    "created_at": doc.get("created_at", ""),
                })
        return reports

    async def generate_advice(
        self,
        user_id: str,
        advice_id: str,
        config_overrides: Optional[Dict[str, Any]] = None,
    ) -> None:
        """异步执行组合顾问分析（在线程池中运行）"""
        _executor.submit(
            self._run_advice_sync,
            user_id,
            advice_id,
            config_overrides or {},
        )

    def _run_advice_sync(
        self,
        user_id: str,
        advice_id: str,
        config_overrides: Dict[str, Any],
    ) -> None:
        """同步执行组合顾问分析（线程池中运行）"""
        import asyncio

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(
                self._execute_advice(user_id, advice_id, config_overrides)
            )
        except Exception as e:
            logger.error(f"组合顾问执行失败: {e}", exc_info=True)
            loop.run_until_complete(self._mark_failed(advice_id, str(e)))
        finally:
            loop.close()

    async def _execute_advice(
        self,
        user_id: str,
        advice_id: str,
        config_overrides: Dict[str, Any],
    ) -> None:
        """实际执行逻辑"""
        from app.services.portfolio_service import PortfolioService
        from app.services.config_service import ConfigService

        self._db = None

        await self.db["portfolio_advice"].update_one(
            {"advice_id": advice_id},
            {"$set": {"status": "RUNNING", "updated_at": datetime.utcnow().isoformat()}},
        )

        portfolio_svc = PortfolioService()
        portfolio_summary = await portfolio_svc.get_portfolio_summary(user_id)

        position_codes = [p["code"] for p in portfolio_summary.get("positions", [])]
        tier1_reports = await self._prepare_tier1_reports(position_codes)

        logger.info(
            f"[Advisor] 数据准备完成: {len(position_codes)} 只持仓, "
            f"{len(tier1_reports)} 份 Tier1 报告"
        )

        config_service = ConfigService()
        llm_config = await config_service.get_analysis_config(user_id)

        from tradingagents.graph.trading_graph import create_llm_by_provider
        from tradingagents.llm_clients.provider_keys import normalize_provider_key

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

        from tradingagents.graph.advisor_graph import AdvisorGraph

        advisor = AdvisorGraph(llm, config=llm_config)

        def progress_cb(label: str):
            try:
                import asyncio
                _l = asyncio.new_event_loop()
                _l.run_until_complete(
                    self._update_progress(advice_id, label)
                )
                _l.close()
            except Exception:
                pass

        result = advisor.propagate_advice(
            portfolio_summary=portfolio_summary,
            tier1_reports=tier1_reports,
            progress_callback=progress_cb,
            **config_overrides,
        )

        await self.db["portfolio_advice"].update_one(
            {"advice_id": advice_id},
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
                "elapsed_seconds": result.get("elapsed_seconds", 0),
                "completed_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat(),
            }},
        )

        await self._send_ws_notification(user_id, advice_id)

        logger.info(f"[Advisor] 完成 advice_id={advice_id}, "
                     f"{len(result.get('prescription', []))} 条处方")

    async def _update_progress(self, advice_id: str, step: str):
        self._db = None
        await self.db["portfolio_advice"].update_one(
            {"advice_id": advice_id},
            {"$set": {"current_step": step, "updated_at": datetime.utcnow().isoformat()}},
        )

    async def _mark_failed(self, advice_id: str, error: str):
        self._db = None
        await self.db["portfolio_advice"].update_one(
            {"advice_id": advice_id},
            {"$set": {
                "status": "FAILED",
                "error": error[:500],
                "updated_at": datetime.utcnow().isoformat(),
            }},
        )

    async def _send_ws_notification(self, user_id: str, advice_id: str):
        try:
            from app.core.ws_manager import manager as ws_manager
            await ws_manager.send_personal_message(
                {"type": "advice_completed", "advice_id": advice_id},
                user_id,
            )
        except Exception as e:
            logger.debug(f"WebSocket 通知失败（非致命）: {e}")
