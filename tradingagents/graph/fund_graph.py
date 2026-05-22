"""基金分析 Graph：复用 LangGraph 框架，独立数据层"""

from __future__ import annotations

import time
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
from tradingagents.agents.trader.fund_trader import create_fund_trader
from tradingagents.default_config import DEFAULT_CONFIG
from tradingagents.graph.trading_graph import create_llm_by_provider
from tradingagents.llm_clients.provider_keys import normalize_provider_key
from tradingagents.utils.logging_init import get_logger

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


# ── Graph ──────────────────────────────────────────────────────────────────

class FundAnalysisGraph:
    """基金分析多 Agent Graph"""

    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or DEFAULT_CONFIG
        self._build_llm()
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
        """构建 4 节点 Graph：3 分析师 + 1 裁判"""
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
        fund_trader = create_fund_trader(self.deep_llm)

        def should_use_tools(state):
            last = state["messages"][-1]
            if hasattr(last, "tool_calls") and last.tool_calls:
                return "tools"
            return END

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
            return "Fund Trader"

        graph = StateGraph(FundAgentState)

        graph.add_node("Fund Manager Analyst", manager_analyst)
        graph.add_node("Fund Holdings Analyst", holdings_analyst)
        graph.add_node("Fund Risk Analyst", risk_analyst)
        graph.add_node("Fund Trader", fund_trader)
        graph.add_node("tools_manager", tool_node)
        graph.add_node("tools_holdings", tool_node)
        graph.add_node("tools_risk", tool_node)

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
            "Fund Trader": "Fund Trader",
        })
        graph.add_edge("tools_risk", "Fund Risk Analyst")
        graph.add_edge("Fund Trader", END)

        return graph.compile()

    def run(
        self,
        fund_code: str,
        trade_date: str,
        fund_type: str = "",
        progress_callback=None,
    ) -> Dict[str, Any]:
        """运行基金分析"""
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
        )

        node_mapping = {
            "Fund Manager Analyst": "📊 基金经理分析师",
            "Fund Holdings Analyst": "📦 持仓分析师",
            "Fund Risk Analyst": "⚠️ 风险分析师",
            "Fund Trader": "💼 综合裁判",
        }

        cumulative_state = {}
        for chunk in self.graph.stream(init_state, stream_mode="updates"):
            for _k, _v in chunk.items():
                if isinstance(_v, dict):
                    cumulative_state.update(_v)

            if progress_callback:
                for node_name in chunk.keys():
                    if not node_name.startswith("__") and node_name in node_mapping:
                        step_label = node_mapping[node_name]
                        # 提取消息内容
                        node_data = chunk[node_name]
                        msgs = node_data.get("messages", [])
                        content = ""
                        tool_calls = []
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
        logger.info(f"基金分析完成 {fund_code}，耗时 {elapsed:.1f}s")

        # 从累积状态提取结果（updates 模式每次只返回节点 delta，需汇总）
        if cumulative_state:
            return {
                "fund_code": fund_code,
                "trade_date": trade_date,
                "fund_manager_report": cumulative_state.get("fund_manager_report", ""),
                "fund_holdings_report": cumulative_state.get("fund_holdings_report", ""),
                "fund_risk_report": cumulative_state.get("fund_risk_report", ""),
                "fund_trader_proposal": cumulative_state.get("fund_trader_proposal", {}),
                "final_trade_decision": cumulative_state.get("final_trade_decision", ""),
                "elapsed_seconds": elapsed,
            }
        return {"fund_code": fund_code, "error": "分析未产生结果"}
