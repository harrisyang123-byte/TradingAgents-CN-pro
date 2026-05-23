from langchain_core.messages import AIMessage
import time
import json

from tradingagents.utils.logging_init import get_logger
logger = get_logger("agents")

def create_fund_research_manager(llm):
    def fund_research_manager_node(state) -> dict:
        logger.debug(f"👔 [DEBUG] ===== 基金研究经理裁判节点开始 =====")

        investment_debate_state = state.get("investment_debate_state", {})
        debate_history = investment_debate_state.get("history", "")

        fund_code = state.get('company_of_interest', 'Unknown')

        prompt = f"""你是一位资深的【基金研究总监（Fund Research Manager）】。
你的下属（多头分析师和空头分析师）刚刚就基金 {fund_code} 进行了一场激烈的辩论。

请你仔细阅读他们的辩论记录，并作为一个绝对中立、理性的高管，给出你的最终裁判和中期决策。

你的输出应包含：
1. 【辩论总结】：客观总结多空双方最核心的交锋点（争论最激烈的地方是什么？）。
2. 【观点判定】：明确指出在这场辩论中，谁的逻辑更严密，谁的论据更站得住脚？为什么？
3. 【中期结论】：给出一个明确的中期投资结论（不考虑组合风控的前提下，这只基金是否值得配置？）。

辩论历史：
{debate_history}

请用专业、客观的高管语气输出（纯中文）。
"""
        response = llm.invoke(prompt)
        decision = f"Research Manager: {response.content}"

        new_investment_debate_state = {
            **investment_debate_state,
            "judge_decision": decision,
            "history": debate_history + "\n\n" + decision
        }

        # 增加日志
        logger.info(f"👔 [基金研究经理] 裁判完成")

        return {"investment_debate_state": new_investment_debate_state}

    return fund_research_manager_node
