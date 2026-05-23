from langchain_core.messages import AIMessage
import time
import json

from tradingagents.utils.logging_init import get_logger
logger = get_logger("agents")

def create_fund_portfolio_manager(llm):
    def fund_portfolio_manager_node(state) -> dict:
        logger.debug(f"👔 [DEBUG] ===== 基金投资组合经理节点开始 =====")

        risk_debate_state = state.get("risk_debate_state", {})
        debate_history = risk_debate_state.get("history", "")

        investment_debate_state = state.get("investment_debate_state", {})
        manager_decision = investment_debate_state.get("judge_decision", "")

        fund_code = state.get('company_of_interest', 'Unknown')

        prompt = f"""你是一位首席【基金投资组合经理（Fund Portfolio Manager）】。
在研究部得出中期结论后，你的风控团队（激进、中立、保守三位分析师）就基金 {fund_code} 的风险暴露进行了辩论。

请你综合研究部的判定以及风控团队的辩论，拍板最终的投资和风险建议。

你的输出应包含：
1. 【风控决断】：点评激进、中立、保守三方谁的风险容忍度最匹配当前该基金的实际情况。
2. 【最终仓位与策略建议】：这只基金在投资组合中应该扮演什么角色？（如：底仓防守、卫星进攻等），建议的配置比例或操作（如分批建仓、持有观望、果断赎回）。
3. 【监控指标】：如果买入或持有，未来需要死盯的 1-2 个风险指标是什么？

研究经理的中期结论：
{manager_decision}

风控辩论历史：
{debate_history}

请用专业、果断的基金经理语气输出（纯中文）。
"""
        response = llm.invoke(prompt)
        decision = f"Portfolio Manager: {response.content}"

        new_risk_debate_state = {
            **risk_debate_state,
            "judge_decision": decision,
            "history": debate_history + "\n\n" + decision
        }

        # 增加日志
        logger.info(f"👔 [基金投资组合经理] 最终决断完成")

        # 这个节点是最后一个，我们顺便将其设置为最终的交易决策，方便兼容原本的获取字段
        return {
            "risk_debate_state": new_risk_debate_state,
            "final_trade_decision": decision
        }

    return fund_portfolio_manager_node
