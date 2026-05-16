from typing import Literal
from pydantic import BaseModel, Field


class ResearchPlan(BaseModel):
    """Research plan output by research_manager to guide analyst work."""
    plan_type: Literal["deep_dive", "catalyst", "earnings", "technical"] = Field(
        description="Type of research plan"
    )
    tickers: list[str] = Field(description="Tickers to research")
    focus_areas: list[str] = Field(description="Key areas to investigate")
    timeline: str = Field(description="Expected timeline for the research")

    def render(self) -> str:
        """Render plan as formatted text for agent consumption."""
        lines = [
            f"## Research Plan ({self.plan_type})",
            f"Tickers: {', '.join(self.tickers)}",
            f"Focus Areas: {', '.join(self.focus_areas)}",
            f"Timeline: {self.timeline}",
        ]
        return "\n".join(lines)


class SingleDecision(BaseModel):
    """Single trade decision within a portfolio decision."""
    ticker: str = Field(description="Stock ticker")
    action: Literal["buy", "sell", "hold", "increase", "reduce"] = Field(
        description="Recommended action"
    )
    rationale: str = Field(description="Reasoning behind the decision")


class PortfolioDecision(BaseModel):
    """Portfolio-level decision output by the portfolio manager."""
    decisions: list[SingleDecision] = Field(description="List of per-ticker decisions")
    allocation_summary: str = Field(description="Overall portfolio allocation reasoning")

    def render(self) -> str:
        """Render decision as formatted text."""
        lines = ["## Portfolio Decision", ""]
        for d in self.decisions:
            lines.append(f"- **{d.ticker}**: {d.action.upper()} — {d.rationale}")
        lines.append("")
        lines.append(f"**Summary**: {self.allocation_summary}")
        return "\n".join(lines)


class TraderProposal(BaseModel):
    """Trading proposal output by the trader agent."""
    ticker: str = Field(description="Stock ticker")
    direction: Literal["long", "short", "neutral"] = Field(
        description="Trading direction"
    )
    confidence: int = Field(ge=1, le=100, description="Confidence score 1-100")
    reasoning: str = Field(description="Detailed reasoning")
    risk_factors: list[str] = Field(description="Key risk factors")

    def render(self) -> str:
        """Render proposal as formatted text."""
        lines = [
            f"## Trader Proposal: {self.ticker}",
            f"Direction: {self.direction.upper()}",
            f"Confidence: {self.confidence}/100",
            f"Reasoning: {self.reasoning}",
            "Risk Factors:",
        ]
        for r in self.risk_factors:
            lines.append(f"- {r}")
        return "\n".join(lines)
