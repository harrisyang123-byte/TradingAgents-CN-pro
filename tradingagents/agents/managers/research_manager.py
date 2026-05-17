"""Research Manager: turns the bull/bear debate into a structured investment plan."""

from __future__ import annotations

import time

from tradingagents.agents.schemas import ResearchPlan, render_research_plan
from tradingagents.agents.utils.instrument_utils import build_instrument_context
from tradingagents.agents.utils.structured import (
    bind_structured,
    invoke_structured_or_freetext,
)
from tradingagents.utils.logging_init import get_logger

logger = get_logger("default")


def create_research_manager(llm, memory):
    structured_llm = bind_structured(llm, ResearchPlan, "Research Manager")

    def research_manager_node(state) -> dict:
        ticker = state["company_of_interest"]
        instrument_context = build_instrument_context(ticker)
        history = state["investment_debate_state"].get("history", "")
        market_research_report = state["market_report"]
        sentiment_report = state["sentiment_report"]
        news_report = state["news_report"]
        fundamentals_report = state["fundamentals_report"]

        investment_debate_state = state["investment_debate_state"]

        curr_situation = f"{market_research_report}\n\n{sentiment_report}\n\n{news_report}\n\n{fundamentals_report}"

        if memory is not None:
            past_memories = memory.get_memories(curr_situation, n_matches=2)
        else:
            logger.warning("memory为None，跳过历史记忆检索")
            past_memories = []

        past_memory_str = ""
        for rec in past_memories:
            past_memory_str += rec["recommendation"] + "\n\n"

        lessons_line = (
            f"\n以下是您对过去决策的反思：\n\"{past_memory_str}\"\n"
            if past_memory_str
            else ""
        )

        prompt = f"""作为投资组合经理和辩论主持人，您的职责是批判性地评估这轮辩论并做出明确决策：支持看跌分析师、看涨分析师，或者仅在基于所提出论点有强有力理由时选择持有。

**评级标准**（必须选择其中一个）：
- **Buy**：强烈看好，建议建仓或加仓
- **Overweight**：看好前景，建议逐步增加敞口
- **Hold**：维持现有仓位，无需操作
- **Underweight**：谨慎看待，建议减少敞口
- **Sell**：强烈看空，建议清仓或避免入场

简洁地总结双方的关键观点，重点关注最有说服力的证据或推理。您的建议必须明确且可操作。避免仅仅因为双方都有有效观点就默认选择持有。
{lessons_line}
标的约束：
{instrument_context}

以下是辩论历史：
{history}

请用中文撰写所有分析内容和建议。"""

        prompt_length = len(prompt)
        estimated_tokens = int(prompt_length / 1.8)

        logger.info(f"[Research Manager] Prompt 统计: {prompt_length} 字符, ~{estimated_tokens} tokens")

        start_time = time.time()

        investment_plan = invoke_structured_or_freetext(
            structured_llm,
            llm,
            prompt,
            render_research_plan,
            "Research Manager",
        )

        elapsed_time = time.time() - start_time
        logger.info(f"[Research Manager] LLM调用耗时: {elapsed_time:.2f}秒, 响应: {len(investment_plan)} 字符")

        new_investment_debate_state = {
            "judge_decision": investment_plan,
            "history": investment_debate_state.get("history", ""),
            "bear_history": investment_debate_state.get("bear_history", ""),
            "bull_history": investment_debate_state.get("bull_history", ""),
            "current_response": investment_plan,
            "count": investment_debate_state["count"],
        }

        return {
            "investment_debate_state": new_investment_debate_state,
            "investment_plan": investment_plan,
        }

    return research_manager_node
