"""侦察兵：读组合缺口 + 非持仓存档报告 + AKShare 行业数据，发现新标的"""

from __future__ import annotations
from tradingagents.utils.logging_init import get_logger

logger = get_logger("default")


def create_scout(llm):
    def scout_node(state: dict) -> dict:
        portfolio = state.get("portfolio_summary", {})
        positions = portfolio.get("positions", [])
        non_held_reports = state.get("non_held_reports", [])

        held_codes = {p.get("code", "") for p in positions}

        buy_candidates = []
        for r in non_held_reports:
            code = r.get("stock_code") or r.get("stock_symbol") or ""
            if code in held_codes:
                continue
            rating = str(r.get("rating", r.get("recommendation", ""))).lower()
            if any(kw in rating for kw in ["buy", "overweight", "买入", "增持", "strong"]):
                summary_text = r.get("summary", r.get("final_decision", ""))
                if isinstance(summary_text, str) and len(summary_text) > 300:
                    summary_text = summary_text[:300] + "..."
                buy_candidates.append(
                    f"- {code}: 评级 {r.get('rating', 'N/A')}, "
                    f"摘要: {summary_text}"
                )

        if len(buy_candidates) > 10:
            buy_candidates = buy_candidates[:10]

        weight_lines = []
        for pos in positions:
            weight_lines.append(
                f"- {pos.get('code', '?')}: 仓位 {pos.get('weight', 0):.1f}%, "
                f"类型 {pos.get('instrument_type', 'stock')}"
            )

        cash_ratio = 0.0
        total_assets = portfolio.get("total_assets", 0)
        available_cash = portfolio.get("available_cash", 0)
        if total_assets > 0:
            cash_ratio = available_cash / total_assets * 100

        prompt = f"""你是组合顾问团队的侦察兵。你的职责是发现当前组合缺少的投资方向，并推荐值得关注的新标的。

你能看到的数据：
- 当前组合的仓位分布概览
- 用户历史分析过但未持有的标的（已有 Tier 1 报告）
- 这些未持仓标的中评级为"买入"或"增持"的候选

你看不到的数据（这些由其他角色负责）：
- 每只持仓的详细分析报告
- 宏观经济环境分析

组合概览：
总资产: ¥{total_assets:,.2f}
可用现金: ¥{available_cash:,.2f} (现金占比 {cash_ratio:.1f}%)
持仓数: {len(positions)} 只

当前仓位分布：
{chr(10).join(weight_lines) if weight_lines else '无持仓'}

已分析但未持有的买入/增持标的（共 {len(buy_candidates)} 只）：
{chr(10).join(buy_candidates) if buy_candidates else '无符合条件的候选标的'}

请从以下维度评估：

1. **组合缺口识别**：
   - 当前组合在行业/风格/市值上是否有明显缺失
   - 现金占比 {cash_ratio:.1f}% 是否合理（是否应配置新标的）

2. **候选标的推荐**（从已分析列表中筛选）：
   - 哪些候选标的能补充组合缺口
   - 推荐理由（与现有持仓的互补性）
   - 每只推荐的建议仓位比例

3. **风险提示**：
   - 推荐标的与现有持仓是否存在相关性风险
   - 加入新标的后组合集中度变化

用中文回答，重点关注组合互补性而非单只标的的投资价值。"""

        from langchain_core.messages import HumanMessage
        response = llm.invoke([HumanMessage(content=prompt)])
        assessment = response.content if hasattr(response, "content") else str(response)

        logger.info(f"[Scout] 评估完成，{len(buy_candidates)} 只候选，输出 {len(assessment)} 字符")
        return {"scout_assessment": assessment}

    return scout_node
