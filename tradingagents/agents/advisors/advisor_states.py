"""Tier 2 组合顾问引擎状态定义 — 四层对抗架构"""

from typing import Annotated, List, Dict, Any
from typing_extensions import TypedDict
from langgraph.graph.message import add_messages


class AdviceItem(TypedDict, total=False):
    code: str
    name: str
    instrument_type: str
    action: str  # buy / sell / hold / reduce / add / new_position
    current_weight: float
    target_weight: float
    reasoning: str
    risk_note: str


class MarketDebateState(TypedDict, total=False):
    """L1 行业方向辩论状态"""
    history: str
    strategist_response: str
    contrarian_response: str
    count: int


class StockDebateState(TypedDict, total=False):
    """L2 标的筛选辩论状态"""
    history: str
    scout_response: str
    scontrarian_response: str
    count: int


class AdvisorDebateState(TypedDict, total=False):
    """L3 组合构建辩论状态（现有，保留）"""
    history: str
    current_speaker: str
    analyst_response: str
    strategist_response: str
    scout_response: str
    count: int


class RiskDebateState(TypedDict, total=False):
    """L4 终裁风险辩论状态"""
    history: str
    cio_response: str
    riskdir_response: str
    count: int


class AdvisorState(TypedDict, total=False):
    # === 工具型 agent 必需 ===
    messages: Annotated[list, add_messages]

    # === 输入数据 ===
    portfolio_summary: Dict[str, Any]
    tier1_reports: List[Dict[str, Any]]

    # === 两阶段分析 ===
    selected_industries: List[str]               # 用户选择的行业列表（空=全量扫描）

    # === Level 1: 行业方向 ===
    market_intel: Dict[str, Any]               # {industries: [...], lifecycle_stage: ..., confidence: ...}
    market_debate_state: MarketDebateState
    macro_judge_verdict: str
    market_tool_call_count: int

    # === Level 2: 标的筛选 ===
    stock_candidates: List[Dict[str, Any]]      # [{code, name, market, filter_result, action, reasoning, risk}]
    stock_debate_state: StockDebateState
    stock_judge_verdict: str
    stock_tool_call_count: int

    # === Level 3: 组合构建（现有，保留） ===
    analyst_assessment: str
    strategist_assessment: str
    scout_assessment: str
    advisor_debate_state: AdvisorDebateState

    # === Level 4: 最终处方 ===
    prescription: List[AdviceItem]
    cio_verdict: str
    risk_director_review: str
    risk_debate_final: RiskDebateState

    # === PE 分位数据（L3→L4 enrich_price_data 节点产出） ===
    price_context: Dict[str, Any]

    # === 配置 ===
    report_staleness_days: int
    max_single_weight: float
    max_industry_weight: float
    debate_rounds: int
    market_debate_rounds: int
    stock_debate_rounds: int
    final_debate_rounds: int
    max_prescription_items: int
