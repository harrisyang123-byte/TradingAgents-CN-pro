"""基金综合裁判：整合三份分析报告，输出交易信号"""

from __future__ import annotations
from typing import Optional
from pydantic import BaseModel, Field
from langchain_core.messages import AIMessage

from tradingagents.agents.schemas import TraderAction
from tradingagents.agents.utils.structured import bind_structured, invoke_structured_or_freetext
from tradingagents.utils.logging_init import get_logger

logger = get_logger("default")


class FundTraderProposal(BaseModel):
    """基金交易建议"""
    action: TraderAction = Field(description="交易方向：Buy / Hold / Sell")
    reasoning: str = Field(description="综合三份报告的决策理由，3-5 句话")
    expected_return: Optional[str] = Field(
        default=None,
        description="预期收益率区间，如 '+8%~+15%（6个月）'",
    )
    position_sizing: Optional[str] = Field(
        default=None,
        description="仓位建议，如 '占组合 10%'",
    )
    confidence: Optional[float] = Field(
        default=None,
        description="置信度 0.0-1.0",
    )


def create_fund_trader(llm):
    """基金综合裁判节点"""
    structured_llm = bind_structured(llm, FundTraderProposal, "FundTrader")

    def fund_trader_node(state):
        code = state["company_of_interest"]
        manager_report = state.get("fund_manager_report", "")
        holdings_report = state.get("fund_holdings_report", "")
        risk_report = state.get("fund_risk_report", "")

        messages = [
            {
                "role": "system",
                "content": (
                    "你是一位资深基金投资顾问，负责综合多位分析师的报告，给出最终的投资建议。"
                    "你需要权衡基金经理能力、持仓质量和风险水平，给出 Buy/Hold/Sell 建议，"
                    "并估算未来 6 个月的预期收益率区间。"
                    "请用中文回答。"
                ),
            },
            {
                "role": "user",
                "content": (
                    f"请对基金 {code} 给出综合投资建议。\n\n"
                    f"【基金经理分析报告】\n{manager_report or '暂无'}\n\n"
                    f"【持仓分析报告】\n{holdings_report or '暂无'}\n\n"
                    f"【风险评估报告】\n{risk_report or '暂无'}\n\n"
                    "请综合以上三份报告，给出：\n"
                    "1. 交易建议（Buy/Hold/Sell）\n"
                    "2. 决策理由\n"
                    "3. 预期收益率区间（6个月）\n"
                    "4. 仓位建议\n"
                    "5. 置信度（0-1）"
                ),
            },
        ]

        proposal = invoke_structured_or_freetext(structured_llm, llm, messages, "FundTrader")

        if isinstance(proposal, FundTraderProposal):
            content = (
                f"**基金投资建议**: {proposal.action.value}\n\n"
                f"**理由**: {proposal.reasoning}\n\n"
                f"**预期收益**: {proposal.expected_return or '未估算'}\n\n"
                f"**仓位建议**: {proposal.position_sizing or '未指定'}\n\n"
                f"**置信度**: {f'{proposal.confidence:.0%}' if proposal.confidence else '未评估'}"
            )
            result_msg = AIMessage(content=content)
            return {
                "messages": [result_msg],
                "fund_trader_proposal": proposal.model_dump(),
                "final_trade_decision": content,
            }
        else:
            result_msg = AIMessage(content=str(proposal))
            return {
                "messages": [result_msg],
                "fund_trader_proposal": {},
                "final_trade_decision": str(proposal),
            }

    return fund_trader_node
