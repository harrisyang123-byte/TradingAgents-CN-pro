from langchain_core.messages import AIMessage
import time
import json

# 导入统一日志系统
from tradingagents.utils.logging_init import get_logger
logger = get_logger("agents")

def create_fund_bull_researcher(llm):
    def fund_bull_node(state) -> dict:
        logger.debug(f"🐂 [DEBUG] ===== 基金多头研究员节点开始 =====")

        investment_debate_state = state.get("investment_debate_state", {})
        history = investment_debate_state.get("history", "")
        bull_history = investment_debate_state.get("bull_history", "")
        current_response = investment_debate_state.get("current_response", "")

        fund_manager_report = state.get("fund_manager_report", "")
        fund_holdings_report = state.get("fund_holdings_report", "")
        fund_risk_report = state.get("fund_risk_report", "")

        fund_code = state.get('company_of_interest', 'Unknown')

        prompt = f"""你是一位专业的【基金多头分析师（Fund Bull Researcher）】，负责为投资该基金（代码：{fund_code}）建立强有力的看涨论证。

你的任务是构建基于证据的强有力案例，强调该基金的长期增长潜力、基金经理的优秀能力以及其重仓股的良好前景。利用提供的分析报告来解决担忧，并有效反驳空头论点。

请用中文回答，重点关注以下几个特有基金评估维度：
1. 【基金经理能力】：强调基金经理的从业年限、历史业绩、超额收益（Alpha）能力以及稳定的投资风格。
2. 【重仓股前景】：基于持仓报告，论证其前十大重仓股所处行业的高景气度、龙头公司的护城河以及合理的估值水平。
3. 【风控与回撤】：强调该基金在同类中的优秀抗风险能力（如夏普比率、卡玛比率优势）及稳健的持仓集中度。
4. 【针对性反驳】：用具体数据和严谨的投资逻辑，批判性分析空头分析师的担忧（如对特定重仓股的看空、对换手率的质疑等），指出其过度悲观或以偏概全。
5. 【辩论风格】：以对话风格呈现你的论点，直接回应空头分析师的上一轮观点并进行有效交锋，而不仅仅是列举数据。

可用资源：
基金经理分析报告：{fund_manager_report}
基金持仓分析报告：{fund_holdings_report}
基金风险评估报告：{fund_risk_report}
辩论对话历史：{history}
空头分析师的最新反驳：{current_response}

请基于上述信息，输出你强有力的多头论证。请确保语言专业、逻辑连贯且完全使用中文。
"""

        response = llm.invoke(prompt)
        argument = f"Bull Analyst: {response.content}"

        new_count = investment_debate_state.get("count", 0) + 1
        logger.info(f"🐂 [基金多头研究员] 发言完成，回合计数: {investment_debate_state.get('count', 0)} -> {new_count}")

        new_investment_debate_state = {
            "history": history + "\n\n" + argument,
            "bull_history": bull_history + "\n\n" + argument,
            "bear_history": investment_debate_state.get("bear_history", ""),
            "current_response": argument,
            "count": new_count,
        }

        return {"investment_debate_state": new_investment_debate_state}

    return fund_bull_node
