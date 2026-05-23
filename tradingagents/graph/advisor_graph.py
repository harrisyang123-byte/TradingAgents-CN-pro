"""Tier 2 组合顾问 LangGraph — 四层对抗架构

L1: Market Strategist ↔ Contrarian → Macro Judge (行业方向)
L2: Scout ↔ Stock Contrarian → Stock Judge (标的筛选)
L3: Analyst ↔ Strategist ↔ Scout (组合构建，现有保留)
L4: CIO → Risk Director → debate → CIO 终裁 (最终处方)
"""

from __future__ import annotations
import time
from typing import Dict, Any, Optional, Callable

from langgraph.graph import END, StateGraph, START
from langgraph.prebuilt import ToolNode
from langchain_core.messages import HumanMessage, RemoveMessage

from tradingagents.agents.advisors import (
    AdvisorState,
    create_portfolio_analyst,
    create_strategist,
    create_scout,
    create_cio,
    create_market_strategist,
    create_contrarian,
    create_macro_judge,
    create_stock_contrarian,
    create_stock_judge,
    create_risk_director,
    L1_TOOLS,
    L2_TOOLS,
)
from tradingagents.dataflows.pe_percentile import enrich_price_context
from tradingagents.utils.logging_init import get_logger

logger = get_logger("default")


# ── PE 数据增强节点 ───────────────────────────────────────

def enrich_price_data_node(state: dict) -> dict:
    """在 L3 辩论之后、CIO 之前收集所有标的价格/PE 分位数据"""
    portfolio = state.get("portfolio_summary", {})
    positions = portfolio.get("positions", [])
    candidates = state.get("stock_candidates", [])

    if not positions and not candidates:
        logger.info("[EnrichPrice] 无持仓和候选标的，跳过")
        return {"price_context": {}}

    price_context = enrich_price_context(positions, candidates)
    success = sum(1 for v in price_context.values() if v.get("pe_percentile_source") not in ("data_unavailable", "unknown_market"))
    logger.info(f"[EnrichPrice] 完成: {success}/{len(price_context)} 标的价格数据可用")
    return {"price_context": price_context}


# ── 工具节点（带计数器） ──────────────────────────────

def _make_tool_executor(tools, counter_key: str, max_calls: int = 3):
    """创建工具执行节点：先执行工具，再递增计数器；达到上限时注入强制总结消息"""
    tool_node = ToolNode(tools)

    def executor(state: dict) -> dict:
        result = tool_node.invoke(state)
        count = state.get(counter_key, 0) + 1
        result[counter_key] = count
        if count >= max_calls:
            from langchain_core.messages import HumanMessage
            msgs = list(result.get("messages", []))
            msgs.append(HumanMessage(
                content="工具调用次数已达上限。请基于已获取的所有数据和你的知识库，"
                        "直接给出最终分析报告。必须输出完整的分析文本和JSON结构化数据块，不要再调用任何工具。"
            ))
            result["messages"] = msgs
        return result

    return executor


# ── Msg Clear 节点 ─────────────────────────────────────

def _msg_clear_node(state: dict) -> dict:
    """清空 messages，放入占位消息"""
    messages = state.get("messages", [])
    if not messages:
        return {}
    removal = [RemoveMessage(id=m.id) for m in messages]
    return {"messages": removal + [HumanMessage(content="Continue")]}


# ── 辩论节点工厂 ───────────────────────────────────────

def _make_debate_node(llm, role_key: str, label: str, debate_state_key: str):
    """创建纯 prompt 辩论节点（用于 L3）"""

    def debate_node(state: dict) -> dict:
        debate = state.get(debate_state_key, {})
        history = debate.get("history", "")

        other_views = []
        for k in ["analyst_response", "strategist_response", "scout_response"]:
            if k != role_key:
                resp = debate.get(k, "")
                if resp:
                    other_views.append(f"[{k}]: {resp[:1000]}")

        own_assessment = state.get(
            {"analyst_response": "analyst_assessment",
             "strategist_response": "strategist_assessment",
             "scout_response": "scout_assessment"}.get(role_key, ""), ""
        )

        prompt = f"""你是组合顾问团队的{label}，正在参与团队辩论。

你此前的评估：
{str(own_assessment)[:1500]}

其他成员的观点：
{chr(10).join(other_views) if other_views else '尚无其他成员发言'}

辩论历史：
{history[-2000:] if history else '首轮辩论'}

请针对其他成员的观点：
1. 指出你同意的部分（及理由）
2. 指出你不同意的部分（及理由）
3. 补充你认为被忽视的重要因素
4. 更新你的操作建议（如有变化）

保持你的角色视角，用中文简洁回答。"""

        response = llm.invoke([HumanMessage(content=prompt)])
        text = response.content if hasattr(response, "content") else str(response)

        new_debate = dict(debate)
        new_debate[role_key] = text
        new_debate["history"] = history + f"\n\n[{label} 辩论]: {text}"
        new_debate["current_speaker"] = role_key

        return {debate_state_key: new_debate}

    return debate_node


# ── L1/L2 辩论节点（两人交替，纯 prompt） ──────────────

def _make_two_person_debate_node(llm, role_label: str, response_key: str, debate_state_key: str, opponent_key: str):
    """创建两人辩论节点"""

    def debate_node(state: dict) -> dict:
        debate = state.get(debate_state_key, {})
        history = debate.get("history", "")
        opponent_response = debate.get(opponent_key, "")

        prompt = f"""你是组合顾问团队的{role_label}，正在与对手辩论。

对手最新观点：
{opponent_response[:2000] if opponent_response else '对手尚未发言'}

辩论历史：
{history[-2000:] if history else '首轮辩论'}

请：
1. 回应对手的质疑（如果对手的观点有道理，请承认）
2. 用数据或逻辑支撑你的立场
3. 如果对手发现了你遗漏的风险，请更新你的建议

用中文简洁回答。"""

        response = llm.invoke([HumanMessage(content=prompt)])
        text = response.content if hasattr(response, "content") else str(response)

        new_debate = dict(debate)
        new_debate[response_key] = text
        new_debate["history"] = history + f"\n\n[{role_label} 辩论]: {text}"

        return {debate_state_key: new_debate}

    return debate_node


# ── L3 Scout（纯 prompt，读 L2 stock_candidates + 组合缺口） ──

def _create_l3_scout(llm):
    def l3_scout_node(state: dict) -> dict:
        portfolio = state.get("portfolio_summary", {})
        positions = portfolio.get("positions", [])
        stock_candidates = state.get("stock_candidates", [])
        stock_judge = state.get("stock_judge_verdict", "")

        weight_lines = []
        for pos in positions:
            weight_lines.append(
                f"- {pos.get('code', '?')}: 仓位 {pos.get('weight', 0):.1f}%, "
                f"类型 {pos.get('instrument_type', 'stock')}"
            )

        cand_lines = []
        for c in stock_candidates[:15]:
            cand_lines.append(
                f"- {c.get('code', '?')} ({c.get('name', '?')}) [{c.get('market', '?')}]: "
                f"建议 {c.get('action', '?')}, 理由: {str(c.get('reasoning', ''))[:100]}"
            )

        cash_ratio = 0.0
        total_assets = portfolio.get("total_assets", 0)
        available_cash = portfolio.get("available_cash", 0)
        if total_assets > 0:
            cash_ratio = available_cash / total_assets * 100

        prompt = f"""你是组合顾问团队的侦察兵（L3）。你的职责是基于 L2 的候选标的发现组合缺口。

## L2 标的裁判结果
{stock_judge[:1500] if stock_judge else '无 L2 数据'}

## L2 候选标的列表
{chr(10).join(cand_lines) if cand_lines else '无候选标的'}

## 当前组合
总资产: ¥{total_assets:,.2f}
可用现金: ¥{available_cash:,.2f} (现金占比 {cash_ratio:.1f}%)
持仓数: {len(positions)} 只

仓位分布：
{chr(10).join(weight_lines) if weight_lines else '无持仓'}

请从以下维度评估：

1. **组合缺口识别**：当前组合在行业/风格/市值/市场（A股/港股/美股）上是否有明显缺失
2. **候选标的适配**：L2 推荐标的中，哪些能最好地补充组合缺口
3. **风险提示**：推荐标的与现有持仓是否存在相关性风险

用中文回答，关注组合互补性。"""

        response = llm.invoke([HumanMessage(content=prompt)])
        assessment = response.content if hasattr(response, "content") else str(response)

        logger.info(f"[Scout L3] 评估完成，{len(stock_candidates)} 只候选")
        return {"scout_assessment": assessment}

    return l3_scout_node


# ── 条件路由函数 ──────────────────────────────────────

def _make_tool_router(counter_key: str, next_node: str, agent_node: str, max_calls: int = 3):
    """创建工具调用条件路由：有 tool_calls → 工具节点，否则 → 下一节点。
    当工具调用次数达上限时，若已注入强制总结消息且 agent 尚未处理，路由回 agent 最后一轮。"""
    def router(state: dict) -> str:
        messages = state.get("messages", [])
        if not messages:
            return next_node
        last = messages[-1]
        count = state.get(counter_key, 0)

        if hasattr(last, "tool_calls") and last.tool_calls:
            if count >= max_calls:
                logger.warning(f"[{counter_key}] 工具调用次数达上限 {max_calls}，强制结束")
                return next_node
            return "tools"

        # count >= max_calls 且最后一条是 HumanMessage（强制总结消息尚未被 agent 处理）
        if count >= max_calls and hasattr(last, "content") and "工具调用次数已达上限" in str(last.content):
            return agent_node

        return next_node
    return router


def _make_debate_router(debate_state_key: str, max_rounds: int, next_node: str, debate_start_node: str):
    """创建辩论轮数条件路由（计数器每轮+1，直接比较 max_rounds）"""
    def router(state: dict) -> str:
        debate = state.get(debate_state_key, {})
        count = debate.get("count", 0)
        if count >= max_rounds:
            return next_node
        return debate_start_node
    return router


def _make_final_debate_router(max_rounds: int = 1):
    """L4 终裁辩论路由"""
    def router(state: dict) -> str:
        debate = state.get("risk_debate_final", {})
        count = debate.get("count", 0)
        if count >= max_rounds:
            return "cio_final"
        return "debate_cio"
    return router


def _increment_debate_count(debate_state_key: str):
    """辩论轮次递增节点"""
    def node(state: dict) -> dict:
        debate = dict(state.get(debate_state_key, {}))
        debate["count"] = debate.get("count", 0) + 1
        return {debate_state_key: debate}
    return node


# ── 主图构建 ───────────────────────────────────────────

class AdvisorGraph:
    """Tier 2 组合顾问引擎 — 四层对抗架构"""

    def __init__(self, llm, config: Dict[str, Any] = None):
        self.llm = llm
        self.config = config or {}
        self.graph = self._build_graph()

    def _build_graph(self) -> Any:
        # ── Agent 节点 ──
        market_strategist = create_market_strategist(self.llm)
        contrarian = create_contrarian(self.llm)
        macro_judge = create_macro_judge(self.llm)
        scout = create_scout(self.llm)
        stock_contrarian = create_stock_contrarian(self.llm)
        stock_judge = create_stock_judge(self.llm)
        portfolio_analyst = create_portfolio_analyst(self.llm)
        strategist = create_strategist(self.llm)
        l3_scout = _create_l3_scout(self.llm)
        cio = create_cio(self.llm)
        risk_director = create_risk_director(self.llm)

        # ── 工具执行节点 ──
        tools_l1_market = _make_tool_executor(L1_TOOLS, "market_tool_call_count")
        tools_l1_contrarian = _make_tool_executor(L1_TOOLS, "market_tool_call_count")
        tools_l2_scout = _make_tool_executor(L2_TOOLS, "stock_tool_call_count")
        tools_l2_scontrarian = _make_tool_executor(L2_TOOLS, "stock_tool_call_count")

        # ── 辩论节点 ──
        # L1 辩论 (2人交替)
        debate_market_strat = _make_two_person_debate_node(
            self.llm, "市场策略师", "strategist_response", "market_debate_state", "contrarian_response"
        )
        debate_contrarian_l1 = _make_two_person_debate_node(
            self.llm, "反向意见者", "contrarian_response", "market_debate_state", "strategist_response"
        )

        # L2 辩论 (2人交替)
        debate_scout_l2 = _make_two_person_debate_node(
            self.llm, "侦察兵", "scout_response", "stock_debate_state", "scontrarian_response"
        )
        debate_scontrarian = _make_two_person_debate_node(
            self.llm, "标的反向者", "scontrarian_response", "stock_debate_state", "scout_response"
        )

        # L3 辩论 (3人轮转，现有模式)
        debate_analyst = _make_debate_node(self.llm, "analyst_response", "持仓分析师", "advisor_debate_state")
        debate_strategist = _make_debate_node(self.llm, "strategist_response", "策略师", "advisor_debate_state")
        debate_scout_l3 = _make_debate_node(self.llm, "scout_response", "侦察兵", "advisor_debate_state")

        # L4 辩论 (CIO ↔ Risk Director)
        debate_cio_l4 = _make_two_person_debate_node(
            self.llm, "CIO", "cio_response", "risk_debate_final", "riskdir_response"
        )
        debate_riskdir_l4 = _make_two_person_debate_node(
            self.llm, "风险总监", "riskdir_response", "risk_debate_final", "cio_response"
        )

        # ── 计数器节点 ──
        debate_market_ctr = _increment_debate_count("market_debate_state")
        debate_stock_ctr = _increment_debate_count("stock_debate_state")
        debate_advisor_ctr = _increment_debate_count("advisor_debate_state")
        debate_final_ctr = _increment_debate_count("risk_debate_final")

        # ── 路由函数 ──
        l1_router_market = _make_tool_router("market_tool_call_count", "msg_clear_l1a", "market_strategist")
        l1_router_contrarian = _make_tool_router("market_tool_call_count", "msg_clear_l1b", "contrarian")
        l2_router_scout = _make_tool_router("stock_tool_call_count", "msg_clear_l2a", "scout")
        l2_router_scontrarian = _make_tool_router("stock_tool_call_count", "msg_clear_l2b", "stock_contrarian")

        market_debate_router = _make_debate_router(
            "market_debate_state",
            self.config.get("market_debate_rounds", 2),
            "macro_judge",
            "debate_market_strat",
        )
        stock_debate_router = _make_debate_router(
            "stock_debate_state",
            self.config.get("stock_debate_rounds", 2),
            "stock_judge",
            "debate_scout_l2",
        )
        advisor_debate_router = _make_debate_router(
            "advisor_debate_state",
            self.config.get("advisor_debate_rounds", 2),
            "CIO",
            "debate_analyst",
        )
        final_debate_router = _make_final_debate_router(
            self.config.get("final_debate_rounds", 1),
        )

        # ── 构建图 ──
        workflow = StateGraph(AdvisorState)

        # === Level 1: 行业方向 ===
        workflow.add_node("market_strategist", market_strategist)
        workflow.add_node("contrarian", contrarian)
        workflow.add_node("tools_l1_market", tools_l1_market)
        workflow.add_node("tools_l1_contrarian", tools_l1_contrarian)
        workflow.add_node("msg_clear_l1a", _msg_clear_node)
        workflow.add_node("msg_clear_l1b", _msg_clear_node)
        workflow.add_node("debate_market_strat", debate_market_strat)
        workflow.add_node("debate_contrarian_l1", debate_contrarian_l1)
        workflow.add_node("debate_market_ctr", debate_market_ctr)
        workflow.add_node("macro_judge", macro_judge)
        workflow.add_node("msg_clear_final_l1", _msg_clear_node)

        # Market Strategist tool loop
        workflow.add_edge(START, "market_strategist")
        workflow.add_conditional_edges("market_strategist", l1_router_market, {
            "tools": "tools_l1_market",
            "market_strategist": "market_strategist",
            "msg_clear_l1a": "msg_clear_l1a",
        })
        workflow.add_edge("tools_l1_market", "market_strategist")
        workflow.add_edge("msg_clear_l1a", "contrarian")

        # Contrarian tool loop
        workflow.add_conditional_edges("contrarian", l1_router_contrarian, {
            "tools": "tools_l1_contrarian",
            "contrarian": "contrarian",
            "msg_clear_l1b": "msg_clear_l1b",
        })
        workflow.add_edge("tools_l1_contrarian", "contrarian")
        workflow.add_edge("msg_clear_l1b", "debate_market_strat")

        # L1 辩论循环
        workflow.add_edge("debate_market_strat", "debate_contrarian_l1")
        workflow.add_edge("debate_contrarian_l1", "debate_market_ctr")
        workflow.add_conditional_edges("debate_market_ctr", market_debate_router, {
            "debate_market_strat": "debate_market_strat",
            "macro_judge": "macro_judge",
        })

        workflow.add_edge("macro_judge", "msg_clear_final_l1")

        # === Level 2: 标的筛选 ===
        workflow.add_node("scout", scout)
        workflow.add_node("stock_contrarian", stock_contrarian)
        workflow.add_node("tools_l2_scout", tools_l2_scout)
        workflow.add_node("tools_l2_scontrarian", tools_l2_scontrarian)
        workflow.add_node("msg_clear_l2a", _msg_clear_node)
        workflow.add_node("msg_clear_l2b", _msg_clear_node)
        workflow.add_node("debate_scout_l2", debate_scout_l2)
        workflow.add_node("debate_scontrarian", debate_scontrarian)
        workflow.add_node("debate_stock_ctr", debate_stock_ctr)
        workflow.add_node("stock_judge", stock_judge)
        workflow.add_node("msg_clear_final_l2", _msg_clear_node)

        workflow.add_edge("msg_clear_final_l1", "scout")

        # Scout tool loop
        workflow.add_conditional_edges("scout", l2_router_scout, {
            "tools": "tools_l2_scout",
            "scout": "scout",
            "msg_clear_l2a": "msg_clear_l2a",
        })
        workflow.add_edge("tools_l2_scout", "scout")
        workflow.add_edge("msg_clear_l2a", "stock_contrarian")

        # Stock Contrarian tool loop
        workflow.add_conditional_edges("stock_contrarian", l2_router_scontrarian, {
            "tools": "tools_l2_scontrarian",
            "stock_contrarian": "stock_contrarian",
            "msg_clear_l2b": "msg_clear_l2b",
        })
        workflow.add_edge("tools_l2_scontrarian", "stock_contrarian")
        workflow.add_edge("msg_clear_l2b", "debate_scout_l2")

        # L2 辩论循环
        workflow.add_edge("debate_scout_l2", "debate_scontrarian")
        workflow.add_edge("debate_scontrarian", "debate_stock_ctr")
        workflow.add_conditional_edges("debate_stock_ctr", stock_debate_router, {
            "debate_scout_l2": "debate_scout_l2",
            "stock_judge": "stock_judge",
        })

        workflow.add_edge("stock_judge", "msg_clear_final_l2")

        # === Level 3: 组合构建（现有逻辑） ===
        workflow.add_node("Analyst", portfolio_analyst)
        workflow.add_node("Strategist", strategist)
        workflow.add_node("Scout_L3", l3_scout)
        workflow.add_node("debate_analyst", debate_analyst)
        workflow.add_node("debate_strategist", debate_strategist)
        workflow.add_node("debate_scout_l3", debate_scout_l3)
        workflow.add_node("debate_advisor_ctr", debate_advisor_ctr)

        workflow.add_edge("msg_clear_final_l2", "Analyst")
        workflow.add_edge("Analyst", "Strategist")
        workflow.add_edge("Strategist", "Scout_L3")
        workflow.add_edge("Scout_L3", "debate_analyst")
        workflow.add_edge("debate_analyst", "debate_strategist")
        workflow.add_edge("debate_strategist", "debate_scout_l3")
        workflow.add_edge("debate_scout_l3", "debate_advisor_ctr")
        workflow.add_conditional_edges("debate_advisor_ctr", advisor_debate_router, {
            "debate_analyst": "debate_analyst",
            "CIO": "enrich_price_data",
        })

        # === Level 4: 最终处方 ===
        workflow.add_node("enrich_price_data", enrich_price_data_node)
        workflow.add_node("CIO", cio)
        workflow.add_node("Risk_Director", risk_director)
        workflow.add_node("debate_cio_l4", debate_cio_l4)
        workflow.add_node("debate_riskdir_l4", debate_riskdir_l4)
        workflow.add_node("debate_final_ctr", debate_final_ctr)
        workflow.add_node("CIO_Final", cio)

        # L4: enrich → CIO → Risk Director → debate → CIO 终裁
        workflow.add_edge("enrich_price_data", "CIO")
        workflow.add_edge("CIO", "Risk_Director")
        workflow.add_edge("Risk_Director", "debate_cio_l4")
        workflow.add_edge("debate_cio_l4", "debate_riskdir_l4")
        workflow.add_edge("debate_riskdir_l4", "debate_final_ctr")
        workflow.add_conditional_edges("debate_final_ctr", final_debate_router, {
            "debate_cio": "debate_cio_l4",
            "cio_final": "CIO_Final",
        })
        workflow.add_edge("CIO_Final", END)

        return workflow.compile()

    def propagate_advice(
        self,
        portfolio_summary: Dict[str, Any],
        tier1_reports: list,
        progress_callback: Optional[Callable] = None,
        **config_overrides,
    ) -> Dict[str, Any]:
        """执行组合顾问分析

        Returns:
            包含 prescription, cio_verdict, 各级分析结果 的字典
        """
        init_state: AdvisorState = {
            "messages": [HumanMessage(content="开始市场扫描")],
            "portfolio_summary": portfolio_summary,
            "tier1_reports": tier1_reports,
            # L1
            "market_intel": {},
            "market_debate_state": {
                "history": "",
                "strategist_response": "",
                "contrarian_response": "",
                "count": 0,
            },
            "macro_judge_verdict": "",
            "market_tool_call_count": 0,
            # L2
            "stock_candidates": [],
            "stock_debate_state": {
                "history": "",
                "scout_response": "",
                "scontrarian_response": "",
                "count": 0,
            },
            "stock_judge_verdict": "",
            "stock_tool_call_count": 0,
            # L3
            "analyst_assessment": "",
            "strategist_assessment": "",
            "scout_assessment": "",
            "advisor_debate_state": {
                "history": "",
                "current_speaker": "",
                "analyst_response": "",
                "strategist_response": "",
                "scout_response": "",
                "count": 0,
            },
            # L4
            "prescription": [],
            "cio_verdict": "",
            "risk_director_review": "",
            "risk_debate_final": {
                "history": "",
                "cio_response": "",
                "riskdir_response": "",
                "count": 0,
            },
            # PE 分位
            "price_context": {},
            # 配置
            "report_staleness_days": config_overrides.get(
                "report_staleness_days", self.config.get("report_staleness_days", 7)),
            "max_single_weight": config_overrides.get(
                "max_single_weight", self.config.get("max_single_weight", 30.0)),
            "max_industry_weight": config_overrides.get(
                "max_industry_weight", self.config.get("max_industry_weight", 50.0)),
            "debate_rounds": config_overrides.get(
                "debate_rounds", self.config.get("advisor_debate_rounds", 2)),
            "market_debate_rounds": config_overrides.get(
                "market_debate_rounds", self.config.get("market_debate_rounds", 2)),
            "stock_debate_rounds": config_overrides.get(
                "stock_debate_rounds", self.config.get("stock_debate_rounds", 2)),
            "final_debate_rounds": config_overrides.get(
                "final_debate_rounds", self.config.get("final_debate_rounds", 1)),
            "max_prescription_items": config_overrides.get(
                "max_prescription_items", self.config.get("max_prescription_items", 8)),
        }

        node_mapping = {
            "market_strategist": "L1-市场策略师",
            "contrarian": "L1-反向意见者",
            "tools_l1_market": None,
            "tools_l1_contrarian": None,
            "msg_clear_l1a": None,
            "msg_clear_l1b": None,
            "msg_clear_final_l1": None,
            "debate_market_strat": "L1-辩论(策略师)",
            "debate_contrarian_l1": "L1-辩论(反向者)",
            "debate_market_ctr": None,
            "macro_judge": "L1-宏观裁判",
            "scout": "L2-侦察兵",
            "stock_contrarian": "L2-标的反向者",
            "tools_l2_scout": None,
            "tools_l2_scontrarian": None,
            "msg_clear_l2a": None,
            "msg_clear_l2b": None,
            "msg_clear_final_l2": None,
            "debate_scout_l2": "L2-辩论(侦察兵)",
            "debate_scontrarian": "L2-辩论(反向者)",
            "debate_stock_ctr": None,
            "stock_judge": "L2-标的裁判",
            "Analyst": "L3-持仓分析师",
            "Strategist": "L3-策略师",
            "Scout_L3": "L3-侦察兵",
            "debate_analyst": "L3-辩论(分析师)",
            "debate_strategist": "L3-辩论(策略师)",
            "debate_scout_l3": "L3-辩论(侦察兵)",
            "debate_advisor_ctr": None,
            "CIO": "L4-CIO",
            "Risk_Director": "L4-风险总监",
            "debate_cio_l4": "L4-辩论(CIO)",
            "debate_riskdir_l4": "L4-辩论(风险总监)",
            "debate_final_ctr": None,
            "CIO_Final": "L4-CIO终裁",
        }

        start_time = time.time()
        final_state = dict(init_state)

        logger.info("[AdvisorGraph] 开始四层对抗分析...")
        for chunk in self.graph.stream(init_state, stream_mode="updates"):
            for node_name, node_update in chunk.items():
                if node_name.startswith("__"):
                    continue
                final_state.update(node_update)

                label = node_mapping.get(node_name)
                if label and progress_callback:
                    try:
                        progress_callback(label)
                    except Exception:
                        pass

        elapsed = time.time() - start_time
        logger.info(f"[AdvisorGraph] 完成，耗时 {elapsed:.1f}s")

        return {
            "prescription": final_state.get("prescription", []),
            "cio_verdict": final_state.get("cio_verdict", ""),
            "analyst_assessment": final_state.get("analyst_assessment", ""),
            "strategist_assessment": final_state.get("strategist_assessment", ""),
            "scout_assessment": final_state.get("scout_assessment", ""),
            "macro_judge_verdict": final_state.get("macro_judge_verdict", ""),
            "market_intel": final_state.get("market_intel", {}),
            "stock_candidates": final_state.get("stock_candidates", []),
            "stock_judge_verdict": final_state.get("stock_judge_verdict", ""),
            "risk_director_review": final_state.get("risk_director_review", ""),
            "debate_history": final_state.get("advisor_debate_state", {}).get("history", ""),
            "market_debate_history": final_state.get("market_debate_state", {}).get("history", ""),
            "stock_debate_history": final_state.get("stock_debate_state", {}).get("history", ""),
            "elapsed_seconds": round(elapsed, 2),
        }
