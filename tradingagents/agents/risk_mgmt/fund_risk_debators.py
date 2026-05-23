from langchain_core.messages import AIMessage
import time
import json

from tradingagents.utils.logging_init import get_logger
logger = get_logger("agents")

def create_fund_aggressive_debator(llm):
    def node(state) -> dict:
        risk_state = state.get("risk_debate_state", {"count": 0, "history": "", "aggressive_history": ""})
        fund_code = state.get('company_of_interest', 'Unknown')

        prompt = f"""你是一位【激进型风控分析师（Aggressive Risk Analyst）】。
你们正在评估基金 {fund_code} 的风险暴露。
作为激进派，你认为高波动意味着高收益。只要基金经理的超额获取能力（Alpha）足够强，或者其重仓赛道具有极高的爆发性，那么高回撤和集中度就是可以容忍的。

请在风控辩论中，提出为什么对于这只基金，我们应该承担更多风险，或者反驳保守派过度畏首畏尾的观点。
如果这是第一轮发言，请直接表明激进的风险观点；如果是后续轮次，请针对上一位发言者进行反驳。

对话历史：
{risk_state.get('history', '')}

请用激进、追求收益的专业口吻发言（纯中文）。"""

        response = llm.invoke(prompt)
        argument = f"Aggressive Analyst: {response.content}"

        new_state = {
            **risk_state,
            "history": risk_state.get("history", "") + "\n\n" + argument,
            "aggressive_history": risk_state.get("aggressive_history", "") + "\n\n" + argument,
            "latest_speaker": "Aggressive",
            "count": risk_state.get("count", 0) + 1
        }
        logger.info(f"⚡ [激进风控分析师] 发言完成")
        return {"risk_debate_state": new_state}
    return node

def create_fund_neutral_debator(llm):
    def node(state) -> dict:
        risk_state = state.get("risk_debate_state", {"count": 0, "history": "", "neutral_history": ""})
        fund_code = state.get('company_of_interest', 'Unknown')

        prompt = f"""你是一位【中性型风控分析师（Neutral Risk Analyst）】。
你们正在评估基金 {fund_code} 的风险暴露。
作为中性派，你关注的是“性价比（Risk-Adjusted Return）”。你会在激进派（追求高弹性和回撤）和保守派（追求绝对安全）之间寻找平衡，强调夏普比率、卡玛比率等指标。

请在风控辩论中，客观指出激进派可能忽视的下行风险，同时指出保守派可能错失的配置机会，力求给出最理性的风险收益比评估。

对话历史：
{risk_state.get('history', '')}

请用理性、平衡的专业口吻发言（纯中文）。"""

        response = llm.invoke(prompt)
        argument = f"Neutral Analyst: {response.content}"

        new_state = {
            **risk_state,
            "history": risk_state.get("history", "") + "\n\n" + argument,
            "neutral_history": risk_state.get("neutral_history", "") + "\n\n" + argument,
            "latest_speaker": "Neutral",
            "count": risk_state.get("count", 0) + 1
        }
        logger.info(f"⚖️ [中性风控分析师] 发言完成")
        return {"risk_debate_state": new_state}
    return node

def create_fund_conservative_debator(llm):
    def node(state) -> dict:
        risk_state = state.get("risk_debate_state", {"count": 0, "history": "", "conservative_history": ""})
        fund_code = state.get('company_of_interest', 'Unknown')

        prompt = f"""你是一位【保守型风控分析师（Conservative Risk Analyst）】。
你们正在评估基金 {fund_code} 的风险暴露。
作为保守派，你的第一法则是“永远不要亏钱（本金安全）”。你极度厌恶高换手、高回撤、单一赛道高集中度。你宁可错过暴涨，也绝不容忍大幅度回撤破坏复利。

请在风控辩论中，给激进派泼冷水，指出这只基金在极端行情下的脆弱性，警告任何可能导致永久性本金损失的隐患。

对话历史：
{risk_state.get('history', '')}

请用谨慎、风险厌恶的专业口吻发言（纯中文）。"""

        response = llm.invoke(prompt)
        argument = f"Conservative Analyst: {response.content}"

        new_state = {
            **risk_state,
            "history": risk_state.get("history", "") + "\n\n" + argument,
            "conservative_history": risk_state.get("conservative_history", "") + "\n\n" + argument,
            "latest_speaker": "Conservative",
            "count": risk_state.get("count", 0) + 1
        }
        logger.info(f"🛡️ [保守风控分析师] 发言完成")
        return {"risk_debate_state": new_state}
    return node
