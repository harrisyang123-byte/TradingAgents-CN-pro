from langchain_core.messages import AIMessage
import time
import json

# 导入统一日志系统
from tradingagents.utils.logging_init import get_logger
logger = get_logger("agents")

def create_fund_bear_researcher(llm):
    def fund_bear_node(state) -> dict:
        logger.debug(f"🐻 [DEBUG] ===== 基金空头研究员节点开始 =====")

        investment_debate_state = state.get("investment_debate_state", {})
        history = investment_debate_state.get("history", "")
        bear_history = investment_debate_state.get("bear_history", "")
        current_response = investment_debate_state.get("current_response", "")

        fund_manager_report = state.get("fund_manager_report", "")
        fund_holdings_report = state.get("fund_holdings_report", "")
        fund_risk_report = state.get("fund_risk_report", "")

        fund_code = state.get('company_of_interest', 'Unknown')

        prompt = f"""你是一位极致的【基金空头分析师（Fund Bear Researcher）】，同时也是“芒格逆向思维”的践行者。你的核心目标是全方位寻找不投资该基金（代码：{fund_code}）的硬性理由。

你的任务是透过基金过去可能的平滑业绩，用显微镜找出底层资产的隐患和操盘手可能存在的风险，给予看涨观点最猛烈的反击。

请用中文回答，强制要求你**必须**基于以下几个基金特有维度进行挑刺（如果报告中缺乏某项数据，则必须直接质疑其信息不透明及流动性隐患）：
1. 【最大回撤与波动率】：审视历史最大回撤是否曾达到惊人的幅度？修复周期是否过长？收益是否仅仅是承担了过度风险的补偿？
2. 【重仓股集中度隐患】：深挖持仓报告中的前十大重仓股——行业关联度是否过高（容易同涨同跌）？是否重仓了处于下行周期或存在巨大估值泡沫的股票？
3. 【经理操作与风格】：该经理的换手率是否异常（是否在赌博式炒单）？是否管理了过多基金导致“一拖多”精力分散？是否存在业绩好时吹捧、业绩差时归咎于市场的“风格漂移”？
4. 【针对性反驳】：直接抓住多头（Bull Analyst）在上一轮中刚刚吹捧的点（比如某只重仓股的潜力，或经理的过往业绩）进行精准打击，指出其过度乐观和逻辑漏洞。
5. 【辩论风格】：以极具压迫感和逻辑深度的对话风格呈现，直接质问对方。

可用资源：
基金经理分析报告：{fund_manager_report}
基金持仓分析报告：{fund_holdings_report}
基金风险评估报告：{fund_risk_report}
辩论对话历史：{history}
多头分析师的最新论点：{current_response}

请基于上述信息，输出你极具火药味的看跌论证。请确保语言专业、逻辑严密且完全使用中文。
"""

        response = llm.invoke(prompt)
        argument = f"Bear Analyst: {response.content}"

        new_count = investment_debate_state.get("count", 0) + 1
        logger.info(f"🐻 [基金空头研究员] 发言完成，回合计数: {investment_debate_state.get('count', 0)} -> {new_count}")

        new_investment_debate_state = {
            "history": history + "\n\n" + argument,
            "bear_history": bear_history + "\n\n" + argument,
            "bull_history": investment_debate_state.get("bull_history", ""),
            "current_response": argument,
            "count": new_count,
        }

        return {"investment_debate_state": new_investment_debate_state}

    return fund_bear_node
