"""基金分析 Graph：复用 LangGraph 框架，独立数据层，引入深度辩论流程"""

from __future__ import annotations

import time
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from langchain_core.messages import HumanMessage
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode
from typing_extensions import Annotated, TypedDict

from tradingagents.agents.analysts.fund_analysts import (
    create_fund_manager_analyst,
    create_fund_holdings_analyst,
    create_fund_risk_analyst,
    tool_get_fund_basic_info,
    tool_get_fund_performance,
    tool_get_fund_risk_metrics,
    tool_get_fund_holdings,
    tool_get_fund_nav_summary,
)
from tradingagents.agents.researchers.fund_bull_researcher import create_fund_bull_researcher
from tradingagents.agents.researchers.fund_bear_researcher import create_fund_bear_researcher
from tradingagents.agents.managers.fund_research_manager import create_fund_research_manager
from tradingagents.agents.risk_mgmt.fund_risk_debators import (
    create_fund_aggressive_debator,
    create_fund_neutral_debator,
    create_fund_conservative_debator
)
from tradingagents.agents.managers.fund_portfolio_manager import create_fund_portfolio_manager

from tradingagents.default_config import DEFAULT_CONFIG
from tradingagents.graph.trading_graph import create_llm_by_provider
from tradingagents.llm_clients.provider_keys import normalize_provider_key
from tradingagents.utils.logging_init import get_logger
from tradingagents.graph.conditional_logic import ConditionalLogic

logger = get_logger("agents")


# ── State ──────────────────────────────────────────────────────────────────

class FundAgentState(TypedDict):
    messages: Annotated[List, add_messages]
    company_of_interest: str
    trade_date: str
    fund_type: str
    fund_manager_report: str
    fund_holdings_report: str
    fund_risk_report: str
    fund_trader_proposal: Dict[str, Any]
    final_trade_decision: str
    investment_debate_state: Dict[str, Any]
    risk_debate_state: Dict[str, Any]


# ── Graph ──────────────────────────────────────────────────────────────────

class FundAnalysisGraph:
    """基金分析多 Agent Graph"""

    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or DEFAULT_CONFIG
        self._build_llm()
        self.conditional_logic = ConditionalLogic(
            max_debate_rounds=self.config.get("max_debate_rounds", 1),
            max_risk_discuss_rounds=self.config.get("max_risk_discuss_rounds", 1),
        )
        self.graph = self._build_graph()

    def _build_llm(self):
        """复用 trading_graph 的 LLM 初始化逻辑"""
        quick_config = self.config.get("quick_model_config", {})
        deep_config = self.config.get("deep_model_config", {})

        quick_provider = self.config.get("quick_provider")
        deep_provider = self.config.get("deep_provider")
        normalized_quick = normalize_provider_key(quick_provider) if quick_provider else None
        normalized_deep = normalize_provider_key(deep_provider) if deep_provider else None
        normalized_provider = normalize_provider_key(self.config["llm_provider"])

        if normalized_quick and normalized_deep and normalized_quick != normalized_deep:
            self.quick_llm = create_llm_by_provider(
                provider=normalized_quick,
                model=self.config["quick_think_llm"],
                backend_url=self.config.get("quick_backend_url", ""),
                temperature=quick_config.get("temperature", 0.7),
                max_tokens=quick_config.get("max_tokens", 4000),
                timeout=quick_config.get("timeout", 180),
                api_key=self.config.get("quick_api_key"),
            )
            self.deep_llm = create_llm_by_provider(
                provider=normalized_deep,
                model=self.config["deep_think_llm"],
                backend_url=self.config.get("deep_backend_url", ""),
                temperature=deep_config.get("temperature", 0.7),
                max_tokens=deep_config.get("max_tokens", 4000),
                timeout=deep_config.get("timeout", 180),
                api_key=self.config.get("deep_api_key"),
            )
        else:
            llm = create_llm_by_provider(
                provider=normalized_provider,
                model=self.config["deep_think_llm"],
                backend_url=self.config.get("backend_url", ""),
                temperature=deep_config.get("temperature", 0.7),
                max_tokens=deep_config.get("max_tokens", 4000),
                timeout=deep_config.get("timeout", 180),
            )
            self.quick_llm = llm
            self.deep_llm = llm

    def _build_graph(self) -> StateGraph:
        """构建复杂图：基础分析师 -> 对决 -> 风险探讨 -> 最终决策"""
        all_tools = [
            tool_get_fund_basic_info,
            tool_get_fund_performance,
            tool_get_fund_risk_metrics,
            tool_get_fund_holdings,
            tool_get_fund_nav_summary,
        ]
        tool_node = ToolNode(all_tools)

        manager_analyst = create_fund_manager_analyst(self.quick_llm)
        holdings_analyst = create_fund_holdings_analyst(self.quick_llm)
        risk_analyst = create_fund_risk_analyst(self.quick_llm)

        fund_bull = create_fund_bull_researcher(self.quick_llm)
        fund_bear = create_fund_bear_researcher(self.quick_llm)
        fund_research_manager = create_fund_research_manager(self.deep_llm)

        aggressive_analyst = create_fund_aggressive_debator(self.quick_llm)
        neutral_analyst = create_fund_neutral_debator(self.quick_llm)
        conservative_analyst = create_fund_conservative_debator(self.quick_llm)
        fund_trader = create_fund_portfolio_manager(self.deep_llm)

        def after_manager(state):
            last = state["messages"][-1]
            if hasattr(last, "tool_calls") and last.tool_calls:
                return "tools_manager"
            return "Holdings Analyst"

        def after_holdings(state):
            last = state["messages"][-1]
            if hasattr(last, "tool_calls") and last.tool_calls:
                return "tools_holdings"
            return "Risk Analyst"

        def after_risk(state):
            last = state["messages"][-1]
            if hasattr(last, "tool_calls") and last.tool_calls:
                return "tools_risk"
            return "Fund Bull Researcher"

        graph = StateGraph(FundAgentState)

        graph.add_node("Fund Manager Analyst", manager_analyst)
        graph.add_node("Fund Holdings Analyst", holdings_analyst)
        graph.add_node("Fund Risk Analyst", risk_analyst)
        graph.add_node("tools_manager", tool_node)
        graph.add_node("tools_holdings", tool_node)
        graph.add_node("tools_risk", tool_node)

        graph.add_node("Fund Bull Researcher", fund_bull)
        graph.add_node("Fund Bear Researcher", fund_bear)
        graph.add_node("Fund Research Manager", fund_research_manager)

        graph.add_node("Fund Aggressive Analyst", aggressive_analyst)
        graph.add_node("Fund Conservative Analyst", conservative_analyst)
        graph.add_node("Fund Neutral Analyst", neutral_analyst)
        graph.add_node("Fund Trader", fund_trader)

        graph.add_edge(START, "Fund Manager Analyst")

        graph.add_conditional_edges("Fund Manager Analyst", after_manager, {
            "tools_manager": "tools_manager",
            "Holdings Analyst": "Fund Holdings Analyst",
        })
        graph.add_edge("tools_manager", "Fund Manager Analyst")

        graph.add_conditional_edges("Fund Holdings Analyst", after_holdings, {
            "tools_holdings": "tools_holdings",
            "Risk Analyst": "Fund Risk Analyst",
        })
        graph.add_edge("tools_holdings", "Fund Holdings Analyst")

        graph.add_conditional_edges("Fund Risk Analyst", after_risk, {
            "tools_risk": "tools_risk",
            "Fund Bull Researcher": "Fund Bull Researcher",
        })
        graph.add_edge("tools_risk", "Fund Risk Analyst")

        # Debate Loop
        graph.add_conditional_edges(
            "Fund Bull Researcher",
            self.conditional_logic.should_continue_debate,
            {
                "Bear Researcher": "Fund Bear Researcher",
                "Research Manager": "Fund Research Manager",
            },
        )
        graph.add_conditional_edges(
            "Fund Bear Researcher",
            self.conditional_logic.should_continue_debate,
            {
                "Bull Researcher": "Fund Bull Researcher",
                "Research Manager": "Fund Research Manager",
            },
        )

        graph.add_edge("Fund Research Manager", "Fund Aggressive Analyst")

        # Risk Discuss Loop
        graph.add_conditional_edges(
            "Fund Aggressive Analyst",
            self.conditional_logic.should_continue_risk_analysis,
            {
                "Conservative Analyst": "Fund Conservative Analyst",
                "Portfolio Manager": "Fund Trader",
            },
        )
        graph.add_conditional_edges(
            "Fund Conservative Analyst",
            self.conditional_logic.should_continue_risk_analysis,
            {
                "Neutral Analyst": "Fund Neutral Analyst",
                "Portfolio Manager": "Fund Trader",
            },
        )
        graph.add_conditional_edges(
            "Fund Neutral Analyst",
            self.conditional_logic.should_continue_risk_analysis,
            {
                "Aggressive Analyst": "Fund Aggressive Analyst",
                "Portfolio Manager": "Fund Trader",
            },
        )

        graph.add_edge("Fund Trader", END)

        return graph.compile()

    def run(
        self,
        fund_code: str,
        trade_date: str,
        fund_type: str = "",
        progress_callback=None,
    ) -> Dict[str, Any]:
        """运行基金深度分析"""
        start_time = time.time()

        init_state = FundAgentState(
            messages=[HumanMessage(content=f"请对基金 {fund_code} 进行全面分析，分析日期：{trade_date}")],
            company_of_interest=fund_code,
            trade_date=trade_date,
            fund_type=fund_type,
            fund_manager_report="",
            fund_holdings_report="",
            fund_risk_report="",
            fund_trader_proposal={},
            final_trade_decision="",
            investment_debate_state={
                "count": 0,
                "history": "",
                "bull_history": "",
                "bear_history": "",
                "current_response": "",
            },
            risk_debate_state={
                "count": 0,
                "history": "",
                "aggressive_history": "",
                "neutral_history": "",
                "conservative_history": "",
                "latest_speaker": "",
            }
        )

        node_mapping = {
            "Fund Manager Analyst": "📊 基金经理分析师",
            "Fund Holdings Analyst": "📦 持仓分析师",
            "Fund Risk Analyst": "⚠️ 风险分析师",
            "Fund Bull Researcher": "🐂 多头研究员",
            "Fund Bear Researcher": "🐻 空头研究员",
            "Fund Research Manager": "🔬 研究总监",
            "Fund Aggressive Analyst": "⚡ 激进风控",
            "Fund Neutral Analyst": "⚖️ 中性风控",
            "Fund Conservative Analyst": "🛡️ 保守风控",
            "Fund Trader": "💼 投资组合经理",
        }

        cumulative_state = init_state.copy()

        for chunk in self.graph.stream(init_state, stream_mode="updates"):
            for _k, _v in chunk.items():
                if isinstance(_v, dict):
                    cumulative_state.update(_v)

            if progress_callback:
                for node_name in chunk.keys():
                    if not node_name.startswith("__") and node_name in node_mapping:
                        step_label = node_mapping[node_name]
                        # 对于辩论节点，提取具体的最新一段辩论文本作为展示
                        content = ""
                        tool_calls = []
                        if node_name in ["Fund Bull Researcher", "Fund Bear Researcher", "Fund Research Manager"]:
                            state_dict = chunk[node_name].get("investment_debate_state", {})
                            content = state_dict.get("current_response", "") or state_dict.get("judge_decision", "")
                        elif node_name in ["Fund Aggressive Analyst", "Fund Neutral Analyst", "Fund Conservative Analyst", "Fund Trader"]:
                            state_dict = chunk[node_name].get("risk_debate_state", {})
                            content = state_dict.get("judge_decision", "")
                            if not content:
                                # Retrieve latest speaker's message simply by slicing the history (for simplicity here, since we don't save per-message exactly except in history)
                                hist = state_dict.get("history", "")
                                content = hist.split("\n\n")[-1] if hist else ""
                        else:
                            node_data = chunk[node_name]
                            msgs = node_data.get("messages", [])
                            if msgs:
                                last_msg = msgs[-1]
                                if hasattr(last_msg, "content") and last_msg.content:
                                    content = str(last_msg.content)[:500]
                                if hasattr(last_msg, "tool_calls") and last_msg.tool_calls:
                                    tool_calls = [tc.get("name", "") if isinstance(tc, dict) else tc.name for tc in last_msg.tool_calls]

                        progress_callback({
                            "type": "agent_step",
                            "step": step_label,
                            "content": content,
                            "tool_calls": tool_calls,
                        })

        elapsed = time.time() - start_time
        logger.info(f"基金深度分析完成 {fund_code}，耗时 {elapsed:.1f}s")

        self._log_state(trade_date, fund_code, cumulative_state)

        # 整理返回给前端的数据结构
        return {
            "fund_code": fund_code,
            "trade_date": trade_date,
            "state": {
                "fund_manager_report": cumulative_state.get("fund_manager_report", ""),
                "fund_holdings_report": cumulative_state.get("fund_holdings_report", ""),
                "fund_risk_report": cumulative_state.get("fund_risk_report", ""),
                "investment_debate_state": cumulative_state.get("investment_debate_state", {}),
                "risk_debate_state": cumulative_state.get("risk_debate_state", {}),
            },
            "final_trade_decision": cumulative_state.get("final_trade_decision", ""),
            "elapsed_seconds": elapsed,
        }

    def _log_state(self, trade_date: str, fund_code: str, final_state: dict):
        """持久化对决状态到本地日志"""
        log_data = {
            "company_of_interest": fund_code,
            "trade_date": trade_date,
            "fund_manager_report": final_state.get("fund_manager_report", ""),
            "fund_holdings_report": final_state.get("fund_holdings_report", ""),
            "fund_risk_report": final_state.get("fund_risk_report", ""),
            "investment_debate_state": final_state.get("investment_debate_state", {}),
            "risk_debate_state": final_state.get("risk_debate_state", {}),
            "final_trade_decision": final_state.get("final_trade_decision", ""),
        }

        safe_ticker = fund_code.replace("/", "_").replace("\\", "_")
        directory = Path(self.config["results_dir"]) / safe_ticker / trade_date / "TradingAgentsStrategy_logs"
        directory.mkdir(parents=True, exist_ok=True)

        log_path = directory / f"full_states_log_{trade_date}.json"
        with open(log_path, "w", encoding="utf-8") as f:
            json.dump(log_data, f, indent=4, ensure_ascii=False)

        logger.info(f"💾 [基金分析] 已持久化状态至 {log_path}")
