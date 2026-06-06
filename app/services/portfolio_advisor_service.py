"""组合顾问服务：数据准备工具（Tier1 报告、历史反馈等）

注: AdvisorGraph（LangGraph 大脑）已退役。
    组合分析由 v3 pipeline（v3_advisor_runner → run.sh → workflow-v3-advisor.js）驱动。
    本服务保留 _prepare_tier1_reports 等数据准备方法供其他模块复用。
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List

from app.core.database import get_mongo_db

logger = logging.getLogger("webapi")


class PortfolioAdvisorService:
    def __init__(self):
        self._db = None

    @property
    def db(self):
        if self._db is None:
            self._db = get_mongo_db()
        return self._db

    async def _prepare_tier1_reports(self, position_codes: List[str]) -> List[Dict[str, Any]]:
        """获取持仓标的的 Tier 1 分析报告（股票 + 基金）"""
        if not position_codes:
            return []

        reports = []
        for code in position_codes:
            doc = await self.db["analysis_reports"].find_one(
                {"stock_symbol": code, "status": "completed"},
                sort=[("created_at", -1)],
            )
            if not doc:
                doc = await self.db["analysis_results"].find_one(
                    {"$or": [
                        {"stock_code": code},
                        {"stock_symbol": code},
                        {"stock_code": {"$regex": f"^{code}"}},
                    ]},
                    sort=[("created_at", -1)],
                )

            if doc:
                inst_type = doc.get("instrument_type", "stock")
                entry = {
                    "stock_code": doc.get("stock_symbol") or doc.get("stock_code", code),
                    "stock_symbol": doc.get("stock_symbol") or doc.get("stock_code", code),
                    "stock_name": doc.get("stock_name", ""),
                    "instrument_type": inst_type,
                    "rating": doc.get("recommendation") or doc.get("rating", "N/A"),
                    "summary": doc.get("summary", ""),
                    "created_at": doc.get("created_at", ""),
                }

                if inst_type == "fund":
                    sub_reports = doc.get("reports", {})
                    if isinstance(sub_reports, dict):
                        entry["fund_manager_report"] = sub_reports.get("fund_manager_report", "")
                        entry["fund_holdings_report"] = sub_reports.get("fund_holdings_report", "")
                        entry["fund_risk_report"] = sub_reports.get("fund_risk_report", "")
                    decision = doc.get("decision", {})
                    if isinstance(decision, dict):
                        entry["fund_action"] = decision.get("action", "N/A")
                        entry["fund_confidence"] = decision.get("confidence", 0)
                    else:
                        entry["fund_action"] = "N/A"
                        entry["fund_confidence"] = 0

                reports.append(entry)

        return reports

    async def format_feedback_context(self, user_id: str, current_advice_id: str) -> str:
        """获取最近的已完成处方，格式化为反馈上下文"""
        try:
            self._db = None
            cursor = self.db["portfolio_advice"].find(
                {
                    "user_id": user_id,
                    "advice_id": {"$ne": current_advice_id},
                    "status": "COMPLETED",
                }
            ).sort("created_at", -1).limit(2)

            previous = await cursor.to_list(length=2)
            if not previous:
                return ""

            parts = ["## 历史处方反馈", ""]
            for i, doc in enumerate(previous):
                ts = doc.get("created_at", "")[:10]
                presc = doc.get("prescription", [])
                if not presc:
                    continue

                parts.append(f"### 第{i + 1}次回顾 ({ts})")
                parts.append("| 标的 | 操作 | 目标权重 | 理由 |")
                parts.append("|------|------|----------|------|")
                for p in presc[:8]:
                    parts.append(
                        f"| {p.get('code','?')} {p.get('name','')} | "
                        f"{p.get('action','?')} | {p.get('target_weight',0):.1f}% | "
                        f"{str(p.get('reasoning',''))[:80]} |"
                    )
                parts.append("")

            parts.append("**反馈要求**：对比本次处方与历史处方，说明哪些建议被延续、哪些已过时、哪些需要纠正。")
            return "\n".join(parts)
        except Exception as e:
            logger.warning(f"获取历史处方失败: {e}")
            return ""
