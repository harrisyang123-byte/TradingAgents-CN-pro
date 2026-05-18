"""Tier 2 组合顾问引擎状态定义"""

from typing import Annotated, List, Dict, Any, Optional
from typing_extensions import TypedDict


class AdviceItem(TypedDict, total=False):
    code: str
    name: str
    instrument_type: str
    action: str  # buy / sell / hold / reduce / add / new_position
    current_weight: float
    target_weight: float
    reasoning: str
    risk_note: str


class AdvisorDebateState(TypedDict, total=False):
    history: str
    current_speaker: str
    analyst_response: str
    strategist_response: str
    scout_response: str
    count: int


class AdvisorState(TypedDict, total=False):
    # 输入数据
    portfolio_summary: Dict[str, Any]
    tier1_reports: List[Dict[str, Any]]
    non_held_reports: List[Dict[str, Any]]

    # 独立分析输出
    analyst_assessment: str
    strategist_assessment: str
    scout_assessment: str

    # 辩论
    advisor_debate_state: AdvisorDebateState

    # CIO 裁判输出
    prescription: List[AdviceItem]
    cio_verdict: str

    # 配置
    report_staleness_days: int
    max_single_weight: float
    max_industry_weight: float
    debate_rounds: int
