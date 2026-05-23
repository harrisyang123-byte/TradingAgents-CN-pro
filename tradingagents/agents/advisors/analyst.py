"""持仓分析师：读 Tier 1 报告 + 当前价格 + 持仓成本，逐只评估安全边际"""

from __future__ import annotations
import json
from datetime import datetime, timedelta
from tradingagents.utils.logging_init import get_logger

logger = get_logger("default")


def create_portfolio_analyst(llm):
    def portfolio_analyst_node(state: dict) -> dict:
        portfolio = state.get("portfolio_summary", {})
        tier1_reports = state.get("tier1_reports", [])
        staleness_days = state.get("report_staleness_days", 7)
        positions = portfolio.get("positions", [])

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

        position_briefs = []
        for pos in positions:
            code = pos.get("code", "")
            inst_type = pos.get("instrument_type", "stock")
            report = next((r for r in tier1_reports if r.get("stock_code") == code or r.get("stock_symbol") == code), None)

            report_summary = "无深度分析报告"
            report_age_note = ""
            fund_context = ""
            if report:
                created = report.get("created_at", "")
                try:
                    report_time = datetime.fromisoformat(created.replace("Z", "+00:00")) if created else None
                    if report_time and (datetime.utcnow().replace(tzinfo=report_time.tzinfo) - report_time) > timedelta(days=staleness_days):
                        report_age_note = f" [报告已过期，生成于{created[:10]}，超过{staleness_days}天阈值，建议重新分析]"
                except Exception:
                    pass

                rating = report.get("rating", report.get("recommendation", "N/A"))
                summary_text = report.get("summary", report.get("final_decision", ""))
                if isinstance(summary_text, str) and len(summary_text) > 500:
                    summary_text = summary_text[:500] + "..."
                report_summary = f"评级: {rating}, 摘要: {summary_text}{report_age_note}"

                # 基金特有上下文
                if inst_type == "fund":
                    parts = []
                    mgr = report.get("fund_manager_report", "")
                    hold = report.get("fund_holdings_report", "")
                    risk = report.get("fund_risk_report", "")
                    if mgr:
                        parts.append(f"基金经理: {mgr[:200]}")
                    if hold:
                        parts.append(f"持仓: {hold[:200]}")
                    if risk:
                        parts.append(f"风险: {risk[:200]}")
                    if parts:
                        fund_context = " | ".join(parts)

            pnl_str = f"{pos.get('pnl_pct', 0):.2f}%" if pos.get("pnl_pct") is not None else "N/A"
            line = (
                f"- {code} ({inst_type}): "
                f"持仓{pos.get('quantity', 0)}份, 均价{pos.get('avg_cost', 0):.2f}, "
                f"现价{pos.get('last_price', 'N/A')}, 仓位{pos.get('weight', 0):.1f}%, "
                f"浮盈{pnl_str}\n  报告: {report_summary}"
            )
            if fund_context:
                line += f"\n  基金详情: {fund_context}"
            position_briefs.append(line)

        # 检测是否有基金持仓，有则追加基金专项评估
        has_funds = any(p.get("instrument_type") == "fund" for p in positions)
        fund_section = ""
        if has_funds:
            fund_section = """
## 基金持仓专项评估维度
- **基金经理质量**：分析经理从业年限、历史业绩、管理规模、是否近期变更
- **费率合理性**：管理费+托管费 vs 同类平均水平，高费率是否带来超额收益
- **业绩持续性**：近1年/3年/5年收益是否持续优于基准，还是依赖单一年份
- **策略一致性**：基金名称与实际持仓风格是否一致（如"中小盘"基金重仓大盘股即为漂移）
- **赎回/替换判断**：浮亏较大时，判断是市场系统性下跌还是基金本身问题
"""

        prompt = f"""你是组合顾问团队的持仓分析师。你的职责是逐只评估每个持仓标的的安全边际和投资价值。

你能看到的数据：
- 每只持仓的 Tier 1 分析报告摘要（如果有）
- 当前市场价格
- 持仓成本和浮盈
- L1 行业方向判断（用于评估持仓标的的行业背景）
- L2 候选标的列表（用于判断是否有更好的替代选择）

你看不到的数据（这些由其他角色负责）：
- 组合整体的仓位分布和行业集中度（策略师负责）

组合概览：
总资产: ¥{portfolio.get('total_assets', 0):,.2f}
总投入: ¥{portfolio.get('total_invested', 0):,.2f}
可用现金: ¥{portfolio.get('available_cash', 0):,.2f}
总盈亏: ¥{portfolio.get('total_pnl', 0):,.2f} ({portfolio.get('total_pnl_pct', 0):.2f}%)

持仓明细：
{chr(10).join(position_briefs) if position_briefs else '无持仓'}

请对每只持仓进行以下评估：
1. 安全边际：当前价格 vs 报告估值/评级是否合理
2. 浮盈/浮亏分析：是否应该止盈或止损
3. 报告时效：报告是否过期，是否需要重新分析
4. 操作建议：持有/加仓/减仓/清仓，附理由

用中文回答，保持客观。{l1_l2_context}{fund_section}"""

        from langchain_core.messages import HumanMessage
        response = llm.invoke([HumanMessage(content=prompt)])
        assessment = response.content if hasattr(response, "content") else str(response)

        logger.info(f"[Portfolio Analyst] 评估完成，{len(positions)} 只持仓，输出 {len(assessment)} 字符")
        return {"analyst_assessment": assessment}

    return portfolio_analyst_node
