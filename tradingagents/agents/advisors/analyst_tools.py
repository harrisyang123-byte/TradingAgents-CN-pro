"""L3 持仓分析师工具 — 读 Tier1 报告 + 持仓体检"""

from langchain_core.tools import tool
import json


def create_analyst_tools(state_provider):
    """创建 L3 Analyst 工具列表。"""

    @tool
    def read_tier1_report(code: str) -> str:
        """读取单只标的的 Tier1 深度分析报告。返回评级、摘要、基金特有字段。"""
        state = state_provider()
        reports = state.get("tier1_reports", [])
        for r in reports:
            rc = r.get("stock_code") or r.get("stock_symbol", "")
            if rc == code:
                return json.dumps({
                    "code": code,
                    "name": r.get("stock_name", ""),
                    "instrument_type": r.get("instrument_type", "stock"),
                    "rating": r.get("rating", r.get("recommendation", "N/A")),
                    "summary": str(r.get("summary", ""))[:500],
                    "fund_manager_report": str(
                        r.get("fund_manager_report", ""))[:300],
                    "fund_holdings_report": str(
                        r.get("fund_holdings_report", ""))[:300],
                    "fund_action": r.get("fund_action", "N/A"),
                    "fund_confidence": r.get("fund_confidence", 0),
                }, ensure_ascii=False, indent=2)
        return json.dumps(
            {"code": code, "error": "未找到该标的的 Tier1 报告"})

    @tool
    def get_position_audit(code: str) -> str:
        """读取单只标的的持仓体检数据：成本、现价、盈亏、健康分、持有天数。"""
        state = state_provider()
        audit_results = state.get("audit_results", [])
        if not isinstance(audit_results, list):
            audit_results = []
        for a in audit_results:
            if a.get("code") == code:
                return json.dumps({
                    "code": code,
                    "avg_cost": a.get("avg_cost", 0),
                    "last_price": a.get("last_price", 0),
                    "pnl_pct": round(a.get("pnl_pct", 0), 1),
                    "pnl_cny": round(a.get("pnl_cny", 0), 0),
                    "health": a.get("health", "ok"),
                    "buy_date": a.get("buy_date", ""),
                    "current_weight": a.get("weight", 0),
                }, ensure_ascii=False, indent=2)
        return json.dumps(
            {"code": code, "error": "未找到该标的的体检数据"})

    return [read_tier1_report, get_position_audit]
