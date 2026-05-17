# TradingAgents/graph/setup.py

from typing import Dict, Any
from langchain_openai import ChatOpenAI
from langgraph.graph import END, StateGraph, START
from langgraph.prebuilt import ToolNode

from tradingagents.agents import (
    create_bear_researcher,
    create_bull_researcher,
    create_fundamentals_analyst,
    create_market_analyst,
    create_msg_delete,
    create_news_analyst,
    create_neutral_debator,
    create_research_manager,
    create_portfolio_manager,
    create_aggressive_debator,
    create_conservative_debator,
    create_trader,
)
from tradingagents.agents.analysts.sentiment_analyst import (
    create_sentiment_analyst,
)
from tradingagents.agents.utils.agent_states import AgentState
from tradingagents.agents.utils.agent_utils import Toolkit

from .conditional_logic import ConditionalLogic

# 导入统一日志系统
from tradingagents.utils.logging_init import get_logger
logger = get_logger("default")


class GraphSetup:
    """Handles the setup and configuration of the agent graph."""

    def __init__(
        self,
        quick_thinking_llm: ChatOpenAI,
        deep_thinking_llm: ChatOpenAI,
        toolkit: Toolkit,
        tool_nodes: Dict[str, ToolNode],
        bull_memory,
        bear_memory,
        trader_memory,
        invest_judge_memory,
        risk_manager_memory,
        conditional_logic: ConditionalLogic,
        config: Dict[str, Any] = None,
        react_llm = None,
    ):
        """Initialize with required components."""
        self.quick_thinking_llm = quick_thinking_llm
        self.deep_thinking_llm = deep_thinking_llm
        self.toolkit = toolkit
        self.tool_nodes = tool_nodes
        self.bull_memory = bull_memory
        self.bear_memory = bear_memory
        self.trader_memory = trader_memory
        self.invest_judge_memory = invest_judge_memory
        self.risk_manager_memory = risk_manager_memory
        self.conditional_logic = conditional_logic
        self.config = config or {}
        self.react_llm = react_llm

    def _build_sentiment_source_config(self):
        """Build per-source config dict from domain config."""
        source_config = {}
        wechat_url = self.config.get("wechat_mp_base_url")
        if wechat_url:
            source_config["wechat_mp"] = {"base_url": wechat_url}
        xhs_url = self.config.get("xiaohongshu_base_url")
        if xhs_url:
            source_config["xiaohongshu"] = {"base_url": xhs_url}
        return source_config or None

    def setup_graph(
        self,
        selected_analysts=["market", "social", "news", "fundamentals"],
        checkpointer=None,
    ):
        """Set up and compile the agent workflow graph.

        Args:
            selected_analysts (list): List of analyst types to include. Options are:
                - "market": Market analyst
                - "social": Social media analyst
                - "news": News analyst
                - "fundamentals": Fundamentals analyst
        """
        if len(selected_analysts) == 0:
            raise ValueError("Trading Agents Graph Setup Error: no analysts selected!")

        # Create analyst nodes
        analyst_nodes = {}
        delete_nodes = {}
        tool_nodes = {}

        if "market" in selected_analysts:
            # 现在所有LLM都使用标准市场分析师（包括阿里百炼的OpenAI兼容适配器）
            llm_provider = self.config.get("llm_provider", "").lower()

            # 检查是否使用OpenAI兼容的阿里百炼适配器
            using_dashscope_openai = (
                "dashscope" in llm_provider and
                hasattr(self.quick_thinking_llm, '__class__') and
                'OpenAI' in self.quick_thinking_llm.__class__.__name__
            )

            if using_dashscope_openai:
                logger.debug(f"📈 [DEBUG] 使用标准市场分析师（阿里百炼OpenAI兼容模式）")
            elif "dashscope" in llm_provider or "阿里百炼" in self.config.get("llm_provider", ""):
                logger.debug(f"📈 [DEBUG] 使用标准市场分析师（阿里百炼原生模式）")
            elif "deepseek" in llm_provider:
                logger.debug(f"📈 [DEBUG] 使用标准市场分析师（DeepSeek）")
            else:
                logger.debug(f"📈 [DEBUG] 使用标准市场分析师")

            # 所有LLM都使用标准分析师
            analyst_nodes["market"] = create_market_analyst(
                self.quick_thinking_llm, self.toolkit
            )
            delete_nodes["market"] = create_msg_delete()
            tool_nodes["market"] = self.tool_nodes["market"]

        if "social" in selected_analysts:
            source_names = self.config.get("sentiment_sources") or ["eastmoney", "wechat_mp"]
            analyst_nodes["social"] = create_sentiment_analyst(
                self.quick_thinking_llm,
                source_names=source_names,
                source_config=self._build_sentiment_source_config(),
            )
            delete_nodes["social"] = create_msg_delete()

        if "news" in selected_analysts:
            analyst_nodes["news"] = create_news_analyst(
                self.quick_thinking_llm, self.toolkit
            )
            delete_nodes["news"] = create_msg_delete()
            tool_nodes["news"] = self.tool_nodes["news"]

        if "fundamentals" in selected_analysts:
            # 现在所有LLM都使用标准基本面分析师（包括阿里百炼的OpenAI兼容适配器）
            llm_provider = self.config.get("llm_provider", "").lower()

            # 检查是否使用OpenAI兼容的阿里百炼适配器
            using_dashscope_openai = (
                "dashscope" in llm_provider and
                hasattr(self.quick_thinking_llm, '__class__') and
                'OpenAI' in self.quick_thinking_llm.__class__.__name__
            )

            if using_dashscope_openai:
                logger.debug(f"📊 [DEBUG] 使用标准基本面分析师（阿里百炼OpenAI兼容模式）")
            elif "dashscope" in llm_provider or "阿里百炼" in self.config.get("llm_provider", ""):
                logger.debug(f"📊 [DEBUG] 使用标准基本面分析师（阿里百炼原生模式）")
            elif "deepseek" in llm_provider:
                logger.debug(f"📊 [DEBUG] 使用标准基本面分析师（DeepSeek）")
            else:
                logger.debug(f"📊 [DEBUG] 使用标准基本面分析师")

            # 所有LLM都使用标准分析师（包含强制工具调用机制）
            analyst_nodes["fundamentals"] = create_fundamentals_analyst(
                self.quick_thinking_llm, self.toolkit
            )
            delete_nodes["fundamentals"] = create_msg_delete()
            tool_nodes["fundamentals"] = self.tool_nodes["fundamentals"]

        # Create researcher and manager nodes
        bull_researcher_node = create_bull_researcher(
            self.quick_thinking_llm, self.bull_memory
        )
        bear_researcher_node = create_bear_researcher(
            self.quick_thinking_llm, self.bear_memory
        )
        research_manager_node = create_research_manager(
            self.deep_thinking_llm, self.invest_judge_memory
        )
        trader_node = create_trader(self.quick_thinking_llm, self.trader_memory)

        # Create risk analysis nodes
        aggressive_analyst = create_aggressive_debator(self.quick_thinking_llm)
        neutral_analyst = create_neutral_debator(self.quick_thinking_llm)
        conservative_analyst = create_conservative_debator(self.quick_thinking_llm)
        portfolio_manager_node = create_portfolio_manager(
            self.deep_thinking_llm, self.risk_manager_memory
        )

        # Create workflow
        workflow = StateGraph(AgentState)

        # Add analyst nodes to the graph
        for analyst_type, node in analyst_nodes.items():
            workflow.add_node(f"{analyst_type.capitalize()} Analyst", node)
            workflow.add_node(
                f"Msg Clear {analyst_type.capitalize()}", delete_nodes[analyst_type]
            )
            if analyst_type in tool_nodes:
                workflow.add_node(f"tools_{analyst_type}", tool_nodes[analyst_type])

        # Add other nodes
        workflow.add_node("Bull Researcher", bull_researcher_node)
        workflow.add_node("Bear Researcher", bear_researcher_node)
        workflow.add_node("Research Manager", research_manager_node)
        workflow.add_node("Trader", trader_node)
        workflow.add_node("Aggressive Analyst", aggressive_analyst)
        workflow.add_node("Neutral Analyst", neutral_analyst)
        workflow.add_node("Conservative Analyst", conservative_analyst)
        workflow.add_node("Portfolio Manager", portfolio_manager_node)

        # Define edges
        first_analyst = selected_analysts[0]
        first_analyst_node = f"{first_analyst.capitalize()} Analyst"
        workflow.add_edge(START, first_analyst_node)

        # Connect analysts in sequence
        for i, analyst_type in enumerate(selected_analysts):
            current_analyst = f"{analyst_type.capitalize()} Analyst"
            current_clear = f"Msg Clear {analyst_type.capitalize()}"

            if analyst_type in tool_nodes:
                current_tools = f"tools_{analyst_type}"
                workflow.add_conditional_edges(
                    current_analyst,
                    getattr(self.conditional_logic, f"should_continue_{analyst_type}"),
                    [current_tools, current_clear],
                )
                workflow.add_edge(current_tools, current_analyst)
            else:
                workflow.add_edge(current_analyst, current_clear)

            # Connect to next analyst or to Bull Researcher if this is the last analyst
            if i < len(selected_analysts) - 1:
                next_analyst = f"{selected_analysts[i+1].capitalize()} Analyst"
                workflow.add_edge(current_clear, next_analyst)
            else:
                workflow.add_edge(current_clear, "Bull Researcher")

        # Add remaining edges
        workflow.add_conditional_edges(
            "Bull Researcher",
            self.conditional_logic.should_continue_debate,
            {
                "Bear Researcher": "Bear Researcher",
                "Research Manager": "Research Manager",
            },
        )
        workflow.add_conditional_edges(
            "Bear Researcher",
            self.conditional_logic.should_continue_debate,
            {
                "Bull Researcher": "Bull Researcher",
                "Research Manager": "Research Manager",
            },
        )
        workflow.add_edge("Research Manager", "Trader")
        workflow.add_edge("Trader", "Aggressive Analyst")
        workflow.add_conditional_edges(
            "Aggressive Analyst",
            self.conditional_logic.should_continue_risk_analysis,
            {
                "Conservative Analyst": "Conservative Analyst",
                "Portfolio Manager": "Portfolio Manager",
            },
        )
        workflow.add_conditional_edges(
            "Conservative Analyst",
            self.conditional_logic.should_continue_risk_analysis,
            {
                "Neutral Analyst": "Neutral Analyst",
                "Portfolio Manager": "Portfolio Manager",
            },
        )
        workflow.add_conditional_edges(
            "Neutral Analyst",
            self.conditional_logic.should_continue_risk_analysis,
            {
                "Aggressive Analyst": "Aggressive Analyst",
                "Portfolio Manager": "Portfolio Manager",
            },
        )

        workflow.add_edge("Portfolio Manager", END)

        # Compile and return
        compile_kwargs = {}
        if checkpointer is not None:
            compile_kwargs["checkpointer"] = checkpointer
        return workflow.compile(**compile_kwargs)
