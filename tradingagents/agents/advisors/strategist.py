"""策略师：读组合仓位分布 + 行业集中度，逆向思维 + 认知偏差检测"""

from __future__ import annotations
from tradingagents.utils.logging_init import get_logger
from app.services.portfolio_audit_service import HEALTH_EMOJI_MAP

logger = get_logger("default")


def create_strategist(llm):
    def strategist_node(state: dict) -> dict:
        portfolio = state.get("portfolio_summary", {})
        positions = portfolio.get("positions", [])
        max_single = state.get("max_single_weight", 30.0)
        max_industry = state.get("max_industry_weight", 50.0)

        # L1/L2 数据注入
        market_intel = state.get("market_intel", {})
        stock_candidates = state.get("stock_candidates", [])
        l1_l2_context = ""
        judge_verdict = market_intel.get("judge_verdict", "")
        if judge_verdict:
            l1_l2_context += f"\n\n## L1 行业方向（宏观裁判裁决）\n{judge_verdict[:1500]}"
        if stock_candidates:
            cand_lines = []
            for c in stock_candidates[:10]:
                cand_lines.append(f"- {c.get('code', '?')} ({c.get('name', '?')}): 建议{c.get('action', '?')}")
            l1_l2_context += f"\n\n## L2 候选标的\n{chr(10).join(cand_lines)}"

        # 构建持仓体检数据映射
        audit_results = state.get("audit_results", [])
        audit_map = {}
        if isinstance(audit_results, list):
            for a in audit_results:
                audit_map[a.get("code", "")] = a

        weight_lines = []
        for pos in positions:
            code = pos.get("code", "?")
            inst_type = pos.get("instrument_type", "stock")
            weight = pos.get("weight", 0)
            mv = pos.get("market_value_cny", 0)

            aud = audit_map.get(code, {})
            avg_cost = aud.get("avg_cost", pos.get("avg_cost", 0))
            last_price = aud.get("last_price", pos.get("last_price", 0))
            pnl_pct = aud.get("pnl_pct", pos.get("pnl_pct", 0))
            pnl_cny = aud.get("pnl_cny", pos.get("pnl_cny", 0))
            health = aud.get("health", "ok")
            buy_date = aud.get("buy_date", pos.get("buy_date", ""))

            health_emoji = HEALTH_EMOJI_MAP.get(health, "⚪")

            cost_str = f"，成本 ¥{avg_cost} → 现价 ¥{last_price}" if avg_cost and last_price else ""
            pnl_str = f"，浮{'%.2f' if pnl_pct >= 0 else ''}{pnl_pct:.1f}% (¥{pnl_cny:+,.0f})" if pnl_pct else ""
            buy_str = f"，买入 {buy_date}" if buy_date else ""

            weight_lines.append(
                f"- {code} ({inst_type}): 仓位 {weight:.1f}%, 市值 ¥{mv:,.2f}{cost_str}{pnl_str}{buy_str}"
                f" | {health_emoji} {health}"
            )

        # 检测基金持仓，有则追加基金组合评估
        has_funds = any(p.get("instrument_type") == "fund" for p in positions)
        fund_section = ""
        if has_funds:
            fund_weight_lines = []
            for pos in positions:
                if pos.get("instrument_type") == "fund":
                    fund_weight_lines.append(
                        f"- {pos.get('code', '?')}: 仓位 {pos.get('weight', 0):.1f}%, "
                        f"类型基金"
                    )
            fund_section = f"""
## 基金组合专项评估
基金仓位分布：
{chr(10).join(fund_weight_lines)}

请额外评估：
1. **基金-股票重叠风险**：基金的重仓股是否与你直接持有的个股重叠？同一标的通过基金+直接持股双重暴露
2. **基金管理人集中度**：是否多只基金由同一基金经理或同一公司管理？单一管理人风险
3. **费用拖累**：基金总费率（管理费+托管费+申购赎回费）对长期收益的侵蚀
4. **流动性差异**：场外基金赎回 T+1~T+7 到账 vs 股票 T+1，影响调仓灵活性
"""

        prompt = f"""你是组合顾问团队的策略师。你的职责是从组合构建角度评估仓位分布的合理性。

你能看到的数据：
- 组合仓位分布（每只标的的占比）
- 行业集中度
- 持仓间的潜在相关性
- L1 行业方向判断（用于集中度分析和行业背景评估）
- L2 候选标的列表（用于组合缺口识别）

你看不到的数据（这些由其他角色负责）：
- 个股的分析报告细节（分析师负责）
- 新标的的详细基本面（侦察兵负责）

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

用中文回答，保持逆向思维立场。{l1_l2_context}{fund_section}"""

        from langchain_core.messages import HumanMessage
        response = llm.invoke([HumanMessage(content=prompt)])
        assessment = response.content if hasattr(response, "content") else str(response)

        logger.info(f"[Strategist] 评估完成，输出 {len(assessment)} 字符")
        return {"strategist_assessment": assessment}

    return strategist_node
