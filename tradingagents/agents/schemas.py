"""Pydantic schemas for agents that produce structured output.

Structured output is layered onto the three decision-making agents
(Research Manager, Trader, Risk Manager) so their outputs follow
consistent section headers across runs and providers.  Render helpers
turn parsed Pydantic instances back into markdown for storage and
downstream consumption.
"""

from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class PortfolioRating(str, Enum):
    """5-tier rating used by the Research Manager and Risk Manager."""

    BUY = "Buy"
    OVERWEIGHT = "Overweight"
    HOLD = "Hold"
    UNDERWEIGHT = "Underweight"
    SELL = "Sell"


class TraderAction(str, Enum):
    """3-tier transaction direction used by the Trader."""

    BUY = "Buy"
    HOLD = "Hold"
    SELL = "Sell"


# ---------------------------------------------------------------------------
# Research Manager
# ---------------------------------------------------------------------------


class ResearchPlan(BaseModel):
    """Structured investment plan produced by the Research Manager."""

    recommendation: PortfolioRating = Field(
        description=(
            "投资建议，必须为以下之一：Buy / Overweight / Hold / Underweight / Sell。"
            "仅在多空论据确实均衡时选择 Hold，否则选择论据更强的一方。"
        ),
    )
    rationale: str = Field(
        description="对辩论双方关键论点的总结，说明哪些论据导出了最终建议。",
    )
    strategic_actions: str = Field(
        description="交易员可执行的具体步骤，包括与评级一致的仓位管理建议。",
    )


def render_research_plan(plan: ResearchPlan) -> str:
    return "\n".join([
        f"**建议**: {plan.recommendation.value}",
        "",
        f"**理由**: {plan.rationale}",
        "",
        f"**策略行动**: {plan.strategic_actions}",
    ])


# ---------------------------------------------------------------------------
# Trader
# ---------------------------------------------------------------------------


class TraderProposal(BaseModel):
    """Structured transaction proposal produced by the Trader."""

    action: TraderAction = Field(
        description="交易方向，必须为以下之一：Buy / Hold / Sell。",
    )
    reasoning: str = Field(
        description="支持该操作的理由，基于分析师报告和研究计划，2-4 句话。",
    )
    entry_price: Optional[float] = Field(
        default=None,
        description="可选的入场价格目标（标的报价货币）。",
    )
    stop_loss: Optional[float] = Field(
        default=None,
        description="可选的止损价格（标的报价货币）。",
    )
    position_sizing: Optional[str] = Field(
        default=None,
        description="可选的仓位管理建议，如「占组合 5%」。",
    )


def render_trader_proposal(proposal: TraderProposal) -> str:
    parts = [
        f"**操作**: {proposal.action.value}",
        "",
        f"**理由**: {proposal.reasoning}",
    ]
    if proposal.entry_price is not None:
        parts.extend(["", f"**入场价格**: {proposal.entry_price}"])
    if proposal.stop_loss is not None:
        parts.extend(["", f"**止损价格**: {proposal.stop_loss}"])
    if proposal.position_sizing:
        parts.extend(["", f"**仓位管理**: {proposal.position_sizing}"])
    parts.extend([
        "",
        f"最终交易建议: **{proposal.action.value.upper()}**",
    ])
    return "\n".join(parts)


# ---------------------------------------------------------------------------
# Risk Manager (Portfolio Manager in upstream)
# ---------------------------------------------------------------------------


class PortfolioDecision(BaseModel):
    """Structured output produced by the Risk Manager."""

    rating: PortfolioRating = Field(
        description="最终仓位评级，必须为以下之一：Buy / Overweight / Hold / Underweight / Sell。",
    )
    executive_summary: str = Field(
        description="简要行动计划，涵盖入场策略、仓位配置、关键风险水平和时间范围。2-4 句话。",
    )
    investment_thesis: str = Field(
        description="详细推理，基于分析师辩论中的具体证据。",
    )
    price_target: Optional[float] = Field(
        default=None,
        description="可选的目标价格（标的报价货币）。",
    )
    time_horizon: Optional[str] = Field(
        default=None,
        description="可选的建议持有期限，如「3-6 个月」。",
    )


def render_pm_decision(decision: PortfolioDecision) -> str:
    parts = [
        f"**评级**: {decision.rating.value}",
        "",
        f"**执行摘要**: {decision.executive_summary}",
        "",
        f"**投资论点**: {decision.investment_thesis}",
    ]
    if decision.price_target is not None:
        parts.extend(["", f"**目标价格**: {decision.price_target}"])
    if decision.time_horizon:
        parts.extend(["", f"**时间范围**: {decision.time_horizon}"])
    return "\n".join(parts)
