"""Trader: turns the Research Manager's investment plan into a concrete transaction proposal."""

from __future__ import annotations

import functools

from langchain_core.messages import AIMessage

from tradingagents.agents.schemas import TraderProposal, render_trader_proposal
from tradingagents.agents.utils.instrument_utils import build_instrument_context
from tradingagents.agents.utils.structured import (
    bind_structured,
    invoke_structured_or_freetext,
)
from tradingagents.utils.logging_init import get_logger
from tradingagents.utils.stock_utils import StockUtils

logger = get_logger("default")


def create_trader(llm, memory):
    structured_llm = bind_structured(llm, TraderProposal, "Trader")

    def trader_node(state, name):
        company_name = state["company_of_interest"]
        instrument_context = build_instrument_context(company_name)
        investment_plan = state["investment_plan"]

        market_info = StockUtils.get_market_info(company_name)
        currency = market_info['currency_name']
        currency_symbol = market_info['currency_symbol']

        curr_situation = (
            f"{state['market_report']}\n\n{state['sentiment_report']}\n\n"
            f"{state['news_report']}\n\n{state['fundamentals_report']}"
        )

        if memory is not None:
            past_memories = memory.get_memories(curr_situation, n_matches=2)
            past_memory_str = ""
            for rec in past_memories:
                past_memory_str += rec["recommendation"] + "\n\n"
        else:
            logger.warning("memory为None，跳过历史记忆检索")
            past_memory_str = "暂无历史记忆数据可参考。"

        messages = [
            {
                "role": "system",
                "content": f"""您是一位专业的交易员，负责分析市场数据并做出投资决策。

当前分析标的：{company_name}，货币单位：{currency}（{currency_symbol}）
{instrument_context}

请提供具体的买入、卖出或持有建议，包含：
1. 明确的交易方向（Buy / Hold / Sell）
2. 基于分析的入场价格目标（{currency}）
3. 止损价格
4. 仓位管理建议
5. 详细推理

请不要忘记利用过去决策的经验教训来避免重复错误：{past_memory_str}

请用中文撰写分析内容。""",
            },
            {
                "role": "user",
                "content": (
                    f"基于分析师团队的综合分析，以下是为 {company_name} 定制的投资计划。"
                    f"请以此为基础评估下一步交易决策。\n\n"
                    f"投资计划: {investment_plan}\n\n"
                    f"请据此做出明智的战略决策。"
                ),
            },
        ]

        trader_plan = invoke_structured_or_freetext(
            structured_llm,
            llm,
            messages,
            render_trader_proposal,
            "Trader",
        )

        return {
            "messages": [AIMessage(content=trader_plan)],
            "trader_investment_plan": trader_plan,
            "sender": name,
        }

    return functools.partial(trader_node, name="Trader")
