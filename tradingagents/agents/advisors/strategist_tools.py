"""L3 策略师工具 — 行业集中度、前几大持仓风险、现金拖累"""

from langchain_core.tools import tool
import json


def create_strategist_tools(state_provider):
    """创建 L3 Strategist 工具列表。"""

    @tool
    def compute_sector_concentration() -> str:
        """计算行业集中度。返回每个行业的权重、标的数，标注是否突破 50% 红线。"""
        state = state_provider()
        positions = state.get("portfolio_summary", {}).get("positions", [])
        max_industry = state.get("max_industry_weight", 50.0)
        sectors = {}
        for p in positions:
            ind = p.get("industry", "未知")
            if ind not in sectors:
                sectors[ind] = {"weight": 0, "codes": [], "total_value": 0}
            sectors[ind]["weight"] += p.get("weight", 0)
            sectors[ind]["codes"].append(p.get("code", ""))
            sectors[ind]["total_value"] += p.get("market_value_cny", 0)
        items = []
        for ind, data in sorted(
                sectors.items(), key=lambda x: -x[1]["weight"]):
            items.append({
                "industry": ind,
                "weight": round(data["weight"], 1),
                "position_count": len(data["codes"]),
                "over_limit": data["weight"] > max_industry,
                "top_codes": data["codes"][:5],
            })
        return json.dumps(
            {"sectors": items, "max_industry_limit": max_industry},
            ensure_ascii=False, indent=2)

    @tool
    def compute_top_holdings_risk(n: int = 5) -> str:
        """计算前 N 大持仓合计权重，估算最大回撤影响。"""
        state = state_provider()
        positions = state.get("portfolio_summary", {}).get("positions", [])
        sorted_pos = sorted(
            positions, key=lambda p: p.get("weight", 0), reverse=True)
        top_n = sorted_pos[:n]
        total_weight = sum(p.get("weight", 0) for p in top_n)
        scenario = ""
        if top_n:
            scenario = (
                f"若最大仓位下跌 30%，组合损失约 "
                f"{top_n[0].get('weight', 0) * 0.3:.1f}%")
        return json.dumps({
            "top_n": n,
            "total_weight": round(total_weight, 1),
            "holdings": [
                {"code": p.get("code"), "name": p.get("name"),
                 "weight": round(p.get("weight", 0), 1)}
                for p in top_n],
            "scenario_30pct_drawdown": scenario,
        }, ensure_ascii=False, indent=2)

    @tool
    def compute_cash_drag() -> str:
        """计算现金拖累：闲置资金占比和机会成本。"""
        state = state_provider()
        portfolio = state.get("portfolio_summary", {})
        total = portfolio.get("total_assets", 1)
        cash = portfolio.get("available_cash", 0)
        cash_ratio = cash / max(total, 1) * 100
        assessment = "偏高" if cash_ratio > 25 else (
            "偏高(略)" if cash_ratio > 15 else (
                "合理" if cash_ratio > 8 else "偏低"))
        return json.dumps({
            "total_assets": round(total, 0),
            "cash": round(cash, 0),
            "cash_ratio": round(cash_ratio, 1),
            "annual_opportunity_cost_2pct": round(cash * 0.02, 0),
            "assessment": assessment,
        }, ensure_ascii=False, indent=2)

    return [compute_sector_concentration, compute_top_holdings_risk, compute_cash_drag]
