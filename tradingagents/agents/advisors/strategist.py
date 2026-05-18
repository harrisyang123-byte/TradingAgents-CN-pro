"""策略师：读组合仓位分布 + 行业集中度，逆向思维 + 认知偏差检测"""

from __future__ import annotations
from tradingagents.utils.logging_init import get_logger

logger = get_logger("default")


def create_strategist(llm):
    def strategist_node(state: dict) -> dict:
        portfolio = state.get("portfolio_summary", {})
        positions = portfolio.get("positions", [])
        max_single = state.get("max_single_weight", 30.0)
        max_industry = state.get("max_industry_weight", 50.0)

        weight_lines = []
        for pos in positions:
            weight_lines.append(
                f"- {pos.get('code', '?')}: 仓位 {pos.get('weight', 0):.1f}%, "
                f"市值 ¥{pos.get('market_value_cny', 0):,.2f}"
            )

        prompt = f"""你是组合顾问团队的策略师。你的职责是从组合构建角度评估仓位分布的合理性。

你能看到的数据：
- 组合仓位分布（每只标的的占比）
- 行业集中度
- 持仓间的潜在相关性

你看不到的数据（这些由其他角色负责）：
- 个股的分析报告细节
- 非持仓标的的推荐

组合概览：
总资产: ¥{portfolio.get('total_assets', 0):,.2f}
可用现金: ¥{portfolio.get('available_cash', 0):,.2f} (现金占比 {portfolio.get('available_cash', 0) / max(portfolio.get('total_assets', 1), 1) * 100:.1f}%)
持仓数: {len(positions)} 只

仓位分布：
{chr(10).join(weight_lines) if weight_lines else '无持仓'}

定量红线：
- 单只标的仓位上限: {max_single}%
- 单一行业仓位上限: {max_industry}%

请从以下维度评估：

1. **集中度分析**：
   - 是否有标的突破 {max_single}% 单只红线？
   - 是否有行业突破 {max_industry}% 行业红线？
   - 前3大持仓的合计占比

2. **逆向思维**（结构性约束，必须回答）：
   - 如果当前最大仓位标的下跌 30%，对组合的影响
   - 如果最集中的行业整体下跌 20%，对组合的影响
   - 当前组合最大的单点风险是什么

3. **认知偏差检测**：
   - 禀赋效应：是否因为已持有而高估某只标的
   - 近因偏差：是否过度重视最近的涨跌
   - 锚定效应：是否被成本价锚定了决策

4. **组合缺口识别**：
   - 当前组合缺少哪些方向的配置
   - 现金占比是否合理

用中文回答，保持逆向思维立场。"""

        from langchain_core.messages import HumanMessage
        response = llm.invoke([HumanMessage(content=prompt)])
        assessment = response.content if hasattr(response, "content") else str(response)

        logger.info(f"[Strategist] 评估完成，输出 {len(assessment)} 字符")
        return {"strategist_assessment": assessment}

    return strategist_node
