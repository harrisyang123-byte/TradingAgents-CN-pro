"""Risk Manager: synthesises the risk-analyst debate into the final decision."""

from __future__ import annotations

import time

from tradingagents.agents.schemas import PortfolioDecision, render_pm_decision
from tradingagents.agents.utils.instrument_utils import build_instrument_context
from tradingagents.agents.utils.structured import (
    bind_structured,
    invoke_structured_or_freetext,
)
from tradingagents.utils.logging_init import get_logger

logger = get_logger("default")


def create_risk_manager(llm, memory):
    structured_llm = bind_structured(llm, PortfolioDecision, "Risk Manager")

    def risk_manager_node(state) -> dict:
        company_name = state["company_of_interest"]
        instrument_context = build_instrument_context(company_name)

        risk_debate_state = state["risk_debate_state"]
        history = risk_debate_state["history"]
        trader_plan = state["investment_plan"]

        curr_situation = (
            f"{state['market_report']}\n\n{state['sentiment_report']}\n\n"
            f"{state['news_report']}\n\n{state['fundamentals_report']}"
        )

        if memory is not None:
            past_memories = memory.get_memories(curr_situation, n_matches=2)
        else:
            logger.warning("memory为None，跳过历史记忆检索")
            past_memories = []

        past_memory_str = ""
        for rec in past_memories:
            past_memory_str += rec["recommendation"] + "\n\n"

        lessons_line = (
            f"\n从过去的错误中学习：\n{past_memory_str}\n"
            if past_memory_str
            else ""
        )

        prompt = f"""作为风险管理委员会主席和辩论主持人，您的目标是评估三位风险分析师——激进、中性和保守——之间的辩论，并确定最佳行动方案。

**评级标准**（必须选择其中一个）：
- **Buy**：强烈看好，建议建仓或加仓
- **Overweight**：看好前景，建议逐步增加敞口
- **Hold**：维持现有仓位，无需操作
- **Underweight**：谨慎看待，建议减少敞口
- **Sell**：强烈看空，建议清仓或避免入场

决策指导原则：
1. 总结每位分析师的最强观点
2. 用辩论中的直接引用和反驳论点支持您的建议
3. 从交易员的原始计划 **{trader_plan}** 开始，根据分析师的见解进行调整
{lessons_line}
标的约束：
{instrument_context}

分析师辩论历史：
{history}

力求清晰和果断。请用中文撰写所有分析内容和建议。"""

        prompt_length = len(prompt)
        estimated_tokens = int(prompt_length / 1.8)
        logger.info(f"[Risk Manager] Prompt 统计: {prompt_length} 字符, ~{estimated_tokens} tokens")

        start_time = time.time()

        final_trade_decision = invoke_structured_or_freetext(
            structured_llm,
            llm,
            prompt,
            render_pm_decision,
            "Risk Manager",
        )

        elapsed_time = time.time() - start_time
        logger.info(f"[Risk Manager] LLM调用耗时: {elapsed_time:.2f}秒, 响应: {len(final_trade_decision)} 字符")

        new_risk_debate_state = {
            "judge_decision": final_trade_decision,
            "history": risk_debate_state["history"],
            "risky_history": risk_debate_state["risky_history"],
            "safe_history": risk_debate_state["safe_history"],
            "neutral_history": risk_debate_state["neutral_history"],
            "latest_speaker": "Judge",
            "current_risky_response": risk_debate_state["current_risky_response"],
            "current_safe_response": risk_debate_state["current_safe_response"],
            "current_neutral_response": risk_debate_state["current_neutral_response"],
            "count": risk_debate_state["count"],
        }

        return {
            "risk_debate_state": new_risk_debate_state,
            "final_trade_decision": final_trade_decision,
        }

    return risk_manager_node
