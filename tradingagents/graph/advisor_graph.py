"""Tier 2 组合顾问 LangGraph — 四层对抗架构

L1: Market Strategist ↔ Contrarian → Macro Judge (行业方向)
L2: Scout ↔ Stock Contrarian → Stock Judge (标的筛选)
L3: Analyst(Agent) → Strategist(Agent) → Scout(LLM) → debate (组合构建)
L4: CIO(Agent) → Risk Director(Agent) → debate → CIO Final(Agent) (最终处方)
"""

from __future__ import annotations
import json
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
from tradingagents.agents.advisors.cio_tools import create_cio_tools
from tradingagents.agents.advisors.analyst_tools import create_analyst_tools
from tradingagents.agents.advisors.strategist_tools import create_strategist_tools
from tradingagents.agents.advisors.risk_tools import create_risk_tools
from tradingagents.dataflows.pe_percentile import enrich_price_context
from tradingagents.utils.logging_init import get_logger
from app.services.portfolio_audit_service import audit_positions
from app.services.buy_signal_engine import get_buy_signal_engine

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


# ── 买入信号计算节点 ───────────────────────────────────

def compute_buy_signals_node(state: dict) -> dict:
    """在 PE 数据就绪后、CIO 之前，为所有持仓 + 候选标的计算买点信号"""
    engine = get_buy_signal_engine()
    positions = state.get("portfolio_summary", {}).get("positions", [])
    candidates = state.get("stock_candidates", [])
    price_ctx = state.get("price_context", {})
    audit_list = state.get("audit_results", [])
    market_intel = state.get("market_intel", {})
    tier1_reports = state.get("tier1_reports", [])

    # 去重：持仓 + 候选（跳过基金/ETF）
    all_targets = {}
    for p in positions:
        if p.get("instrument_type") in ("fund", "etf", "other"):
            continue
        code = p.get("code", "")
        if code:
            all_targets[code] = {
                "code": code, "name": p.get("name", ""),
                "market": p.get("market", p.get("market", "cn")),
                "instrument_type": p.get("instrument_type", "stock"),
            }
    for c in candidates:
        code = c.get("code", "")
        if code and code not in all_targets:
            mkt = c.get("market", "cn")
            if mkt in ("hk", "us"):
                pass
            elif ".HK" in str(code) or ".hk" in str(code):
                mkt = "hk"
            all_targets[code] = {
                "code": code, "name": c.get("name", ""),
                "market": mkt,
                "instrument_type": "stock",
            }

    # 构建 L1 行业索引
    industries = (market_intel.get("industries", []) if isinstance(market_intel, dict) else []) or []
    pos_industry = {}
    for p in positions:
        ind = p.get("industry", "")
        if ind:
            pos_industry[p.get("code", "")] = ind

    # 市场信号：同步计算（不调用异步 API，避免 LangGraph 同步节点中崩溃）
    market_signals = {"source": "sync"}
    # 基于已有数据推算简易市场信号
    market_intel_dict = market_intel if isinstance(market_intel, dict) else {}
    judge_verdict = market_intel_dict.get("judge_verdict", "")
    market_signals["flow_signal"] = "中性"
    market_signals["north_net"] = 0
    market_signals["north_days"] = 0
    market_signals["breadth"] = {"breadth_signal": "中性", "up_ratio": 50}

    # 逐只计算买点信号
    buy_signals = {}
    for code, target in all_targets.items():
        pe = price_ctx.get(code, {})
        audit = next((a for a in audit_list if a.get("code") == code), {})
        scout = next((c for c in candidates if c.get("code") == code), {})

        # L1 行业匹配
        p_ind = pos_industry.get(code, audit.get("industry", ""))
        l1_ind = next((i for i in industries if isinstance(i, dict) and i.get("industry") == p_ind), {})

        # Tier1 rating
        tier1_r = ""
        for r in tier1_reports:
            rc = r.get("stock_code") or r.get("stock_symbol", "")
            if rc == code:
                tier1_r = r.get("rating", r.get("recommendation", ""))
                break

        # 个股情绪（轻量：用 market breadth + 简单启发式）
        stock_sent = {
            "sentiment_score": 50.0,
            "sentiment_label": "中性",
            "em_score": None,
        }

        signal = engine.compute(
            code=code, name=target.get("name", ""),
            market=target.get("market", "cn"),
            pe_ctx=pe, scout_scores=scout,
            audit=audit, l1_industry=l1_ind,
            market_signals=market_signals,
            stock_sentiment=stock_sent,
            tier1_rating=tier1_r,
        )
        buy_signals[code] = {
            "code": signal.code, "name": signal.name,
            "signal": signal.signal, "confidence": signal.confidence,
            "total_score": signal.total_score,
            "quality_score": signal.quality_score,
            "valuation_score": signal.valuation_score,
            "sentiment_score": signal.sentiment_score,
            "fund_flow_score": signal.fund_flow_score,
            "lights": signal.lights,
            "price_range": signal.price_range,
            "timing": signal.timing,
            "trigger_condition": signal.trigger_condition,
            "data_quality": signal.data_quality,
            "signal_details": signal.signal_details,
            "blocked": signal.blocked,
            "block_reason": signal.block_reason,
        }

    logger.info(
        f"[BuySignal] {len(buy_signals)} 只标的完成打分 | "
        f"STRONG_BUY={sum(1 for s in buy_signals.values() if s['signal'] == 'STRONG_BUY')} "
        f"BUY={sum(1 for s in buy_signals.values() if s['signal'] == 'BUY')} "
        f"HOLD={sum(1 for s in buy_signals.values() if s['signal'] == 'HOLD')} "
        f"INSUFFICIENT_DATA={sum(1 for s in buy_signals.values() if s.get('blocked'))}"
    )
    return {"buy_signals": buy_signals, "market_signals": market_signals}


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


# ── 行业缓存检查节点（v3 industry-layer-rebuild） ──────

def _check_industry_cache(state: dict) -> dict:
    """在 L1 运行前标记行业中哪些已有有效缓存。

    对于缓存有效的行业，后续将在 parallel_industry_research 节点（Task 5）中跳过。
    本节点仅做标记，不修改 market_intel。
    """
    scan_pool = state.get("industry_scan_pool", [])
    if not scan_pool:
        logger.info("[CacheCheck] 无行业扫描池，跳过")
        return {}
    logger.info(f"[CacheCheck] 扫描池 {len(scan_pool)} 个行业，等待缓存检查")
    return {}


# ── 辩论节点工厂 ───────────────────────────────────────

def _make_debate_node(llm, role_key: str, label: str, debate_state_key: str):
    """创建红队辩论节点 — 反对前置，批判优先"""

    def debate_node(state: dict) -> dict:
        debate = state.get(debate_state_key, {})
        history = debate.get("history", "")

        # 收集其他成员的初始评估和辩论回复
        other_views = []
        assessment_keys = {
            "analyst_response": "analyst_assessment",
            "strategist_response": "strategist_assessment",
            "scout_response": "scout_assessment",
            "contrarian_response": "contrarian_assessment",
        }
        for k, assess_key in assessment_keys.items():
            if k == role_key:
                continue
            # 优先取辩论回复，次取初始评估
            resp = debate.get(k) or state.get(assess_key, "")
            if resp:
                other_views.append(f"[{k}]: {str(resp)[:1000]}")

        own_assessment = state.get(
            assessment_keys.get(role_key, ""), ""
        )

        prompt = f"""你是组合顾问团队的{label}，正在参与红队辩论。你的首要任务是找出他人推理中的缺陷。

你此前的评估：
{str(own_assessment)[:1500]}

其他成员的观点：
{chr(10).join(other_views) if other_views else '尚无其他成员发言'}

辩论历史：
{history[-2000:] if history else '首轮辩论'}

请以批判性视角审视其他成员的观点：
1. 指出至少 2 个被忽视的风险或推理缺陷（必须具体，不能泛泛而谈）
2. 如果你同意某点，说明为什么它在当前市场环境下仍然可能是错的
3. 补充至少 1 个被遗漏的重要视角
4. 只有在你被说服的情况下，才更新你的建议

保持你的角色视角，用中文回答。不要为了礼貌而同意——真诚的反对比虚假的共识更有价值。"""

        response = llm.invoke([HumanMessage(content=prompt)])
        text = response.content if hasattr(response, "content") else str(response)

        new_debate = dict(debate)
        new_debate[role_key] = text
        new_debate["history"] = history + f"\n\n[{label}]: {text}"
        new_debate["current_speaker"] = role_key

        return {debate_state_key: new_debate}

    return debate_node


def _make_l3_contrarian_node(llm, debate_state_key: str = "advisor_debate_state"):
    """L3 组合构建反向者 — 专门挑刺，找出其他三人推理中的缺陷"""

    def contrarian_node(state: dict) -> dict:
        debate = state.get(debate_state_key, {})
        history = debate.get("history", "")

        analyst = state.get("analyst_assessment", "")
        strategist = state.get("strategist_assessment", "")
        scout = state.get("scout_assessment", "")

        prompt = f"""你是组合顾问团队的反向意见者（Contrarian）。你的唯一职责是质疑和挑战其他成员的推理。

## 持仓分析师的评估
{str(analyst)[:1500] if analyst else '尚未产出'}

## 策略师的评估
{str(strategist)[:1500] if strategist else '尚未产出'}

## 侦察兵的评估
{str(scout)[:1500] if scout else '尚未产出'}

## 辩论历史
{history[-2000:] if history else '首轮'}

请对以上三个评估逐一挑战：
1. **持仓分析师**: 哪些标的的"安全边际"判断可能过于乐观？是否有标的应该减仓却建议持有？
2. **策略师**: 集中度分析的阈值是否合理？组合缺口识别是否遗漏了重要方向？
3. **侦察兵**: 推荐的候选标的是否存在幸存者偏差？是否有更好的冷门标的被忽略？

要求：
- 至少找出 3 个具体的推理缺陷
- 每个批评必须附带数据或逻辑支撑
- 如果你认为某点正确，必须说明"市场可能在什么情况下证明它是错的"
- 提出至少 1 个被所有人忽略的替代方案

用中文回答，保持批判但不刻薄。"""

        response = llm.invoke([HumanMessage(content=prompt)])
        text = response.content if hasattr(response, "content") else str(response)

        new_debate = dict(debate)
        new_debate["contrarian_response"] = text
        new_debate["history"] = history + f"\n\n[反向意见者]: {text}"
        new_debate["current_speaker"] = "contrarian_response"

        return {debate_state_key: new_debate, "contrarian_assessment": text}

    return contrarian_node


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
            if count > max_calls:
                logger.warning(f"[{counter_key}] 工具调用次数超上限 {max_calls}，仍有 tool_calls，强制结束")
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


# ── Tier1 报告摘要格式化 ─────────────────────────────────

def _format_tier1_report_context(tier1_reports: list) -> str:
    """将 Tier1 报告列表格式化为 agent 可用上下文（注入 initial messages）"""
    if not tier1_reports:
        return ""

    stock_items = []
    fund_items = []
    for r in tier1_reports:
        code = r.get("stock_code") or r.get("stock_symbol", "?")
        name = r.get("stock_name", "")
        inst = r.get("instrument_type", "stock")
        rating = r.get("rating", "N/A")
        summary = (r.get("summary", "") or "")[:300]
        label = f"{code} {name}" if name else code

        if inst == "fund":
            parts = [f"- **{label}** (基金) | 评级: {rating}"]
            if summary:
                parts.append(f"  摘要: {summary}")
            action = r.get("fund_action", "")
            conf = r.get("fund_confidence", 0)
            if action:
                parts.append(f"  建议操作: {action} (置信度: {conf})")
            # 基金持仓明细
            holdings = r.get("fund_holdings_report", "")
            if holdings:
                parts.append(f"  重仓股分析: {holdings[:500]}")
            mgr = r.get("fund_manager_report", "")
            if mgr:
                parts.append(f"  基金经理: {mgr[:300]}")
            risk = r.get("fund_risk_report", "")
            if risk:
                parts.append(f"  风险: {risk[:200]}")
            fund_items.append("\n".join(parts))
        else:
            parts = [f"- **{label}** ({inst}) | 评级: {rating}"]
            if summary:
                parts.append(f"  摘要: {summary}")
            stock_items.append("\n".join(parts))

    sections = []
    if stock_items:
        sections.append("### 个股 Tier1 分析\n" + "\n".join(stock_items))
    if fund_items:
        sections.append("### 基金 Tier1 分析（含持仓穿透）\n" + "\n".join(fund_items))

    if not sections:
        return ""

    return (
        "## 持仓 Tier1 分析报告（已完成的深度分析）\n\n"
        + "\n\n".join(sections)
        + "\n\n---\n请基于以上 Tier1 分析数据，结合本次分析进行组合层面的判断。"
    )


# ── 主图构建 ───────────────────────────────────────────

class AdvisorGraph:
    """Tier 2 组合顾问引擎 — 四层对抗架构"""

    def __init__(self, llm, config: Dict[str, Any] = None):
        self.llm = llm
        self.config = config or {}
        self.graph = self._build_graph()

    def _build_graph(self) -> Any:
        # ── L3/L4 共享状态引用（工具通过该引用读取 state） ──
        _shared_state = {}

        # ── L3/L4 工具实例（共享同一 state 引用） ──
        ANALYST_TOOLS = create_analyst_tools(
            lambda: _shared_state.get("state", {}))
        STRATEGIST_TOOLS = create_strategist_tools(
            lambda: _shared_state.get("state", {}))
        CIO_TOOLS = create_cio_tools(
            lambda: _shared_state.get("state", {}))
        RISK_TOOLS = create_risk_tools(
            lambda: _shared_state.get("state", {}))

        # ── Agent 节点 ──
        market_strategist = create_market_strategist(self.llm)
        contrarian = create_contrarian(self.llm)
        macro_judge = create_macro_judge(self.llm)
        scout = create_scout(self.llm)
        stock_contrarian = create_stock_contrarian(self.llm)
        stock_judge = create_stock_judge(self.llm)
        portfolio_analyst = create_portfolio_analyst(
            self.llm, tools=ANALYST_TOOLS, shared_state=_shared_state)
        strategist = create_strategist(
            self.llm, tools=STRATEGIST_TOOLS, shared_state=_shared_state)
        l3_scout = _create_l3_scout(self.llm)
        cio = create_cio(
            self.llm, tools=CIO_TOOLS, shared_state=_shared_state)
        risk_director = create_risk_director(
            self.llm, tools=RISK_TOOLS, shared_state=_shared_state)

        # ── 工具执行节点（L1/L2 维持原状；L3/L4 新加） ──
        tools_l1_market = _make_tool_executor(L1_TOOLS, "market_tool_call_count")
        tools_l1_contrarian = _make_tool_executor(L1_TOOLS, "market_tool_call_count")
        tools_l2_scout = _make_tool_executor(L2_TOOLS, "scout_tool_call_count", max_calls=8)
        tools_l2_scontrarian = _make_tool_executor(L2_TOOLS, "scontrarian_tool_call_count", max_calls=5)
        tools_l3_analyst = _make_tool_executor(ANALYST_TOOLS, "analyst_tool_call_count")
        tools_l3_strategist = _make_tool_executor(STRATEGIST_TOOLS, "strategist_tool_call_count")
        tools_l4_cio = _make_tool_executor(CIO_TOOLS, "cio_tool_call_count")
        tools_l4_risk = _make_tool_executor(RISK_TOOLS, "risk_tool_call_count")
        tools_l4_cio_final = _make_tool_executor(CIO_TOOLS, "cio_final_tool_call_count")

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

        # L3 红队辩论 (Contrarian 首发，批判优先)
        l3_contrarian = _make_l3_contrarian_node(self.llm)
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
        l2_router_scout = _make_tool_router("scout_tool_call_count", "msg_clear_l2a", "scout", max_calls=8)
        l2_router_scontrarian = _make_tool_router("scontrarian_tool_call_count", "msg_clear_l2b", "stock_contrarian", max_calls=5)

        # ── L3/L4 工具路由（新增） ──
        l3_router_analyst = _make_tool_router(
            "analyst_tool_call_count", "msg_clear_l3a", "Analyst")
        l3_router_strategist = _make_tool_router(
            "strategist_tool_call_count", "msg_clear_l3b", "Strategist")
        l4_router_cio = _make_tool_router(
            "cio_tool_call_count", "msg_clear_l4a", "CIO")
        l4_router_risk = _make_tool_router(
            "risk_tool_call_count", "msg_clear_l4b", "Risk_Director")
        l4_router_cio_final = _make_tool_router(
            "cio_final_tool_call_count", "cio_final_end", "CIO_Final")

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

        # === L0: 缓存检查（v3 industry-layer-rebuild） ===
        workflow.add_node("cache_check", _check_industry_cache)
        workflow.add_edge(START, "cache_check")
        workflow.add_edge("cache_check", "market_strategist")

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
        # (routed via cache_check → START)
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

        # === Level 3: 组合构建（工具型 Agent + 红队辩论） ===
        workflow.add_node("Analyst", portfolio_analyst)
        workflow.add_node("Strategist", strategist)
        workflow.add_node("Scout_L3", l3_scout)
        workflow.add_node("tools_l3_analyst", tools_l3_analyst)
        workflow.add_node("tools_l3_strategist", tools_l3_strategist)
        workflow.add_node("msg_clear_l3a", _msg_clear_node)
        workflow.add_node("msg_clear_l3b", _msg_clear_node)
        workflow.add_node("debate_analyst", debate_analyst)
        workflow.add_node("debate_strategist", debate_strategist)
        workflow.add_node("debate_scout_l3", debate_scout_l3)
        workflow.add_node("l3_contrarian", l3_contrarian)
        workflow.add_node("debate_advisor_ctr", debate_advisor_ctr)

        # L3: Analyst tool loop
        workflow.add_edge("msg_clear_final_l2", "Analyst")
        workflow.add_conditional_edges("Analyst", l3_router_analyst, {
            "tools": "tools_l3_analyst",
            "Analyst": "Analyst",
            "msg_clear_l3a": "msg_clear_l3a",
        })
        workflow.add_edge("tools_l3_analyst", "Analyst")
        workflow.add_edge("msg_clear_l3a", "Strategist")

        # L3: Strategist tool loop
        workflow.add_conditional_edges("Strategist", l3_router_strategist, {
            "tools": "tools_l3_strategist",
            "Strategist": "Strategist",
            "msg_clear_l3b": "msg_clear_l3b",
        })
        workflow.add_edge("tools_l3_strategist", "Strategist")
        workflow.add_edge("msg_clear_l3b", "Scout_L3")

        # L3: Scout (纯 prompt) → Contrarian 首发批评 → 红队辩论
        workflow.add_edge("Scout_L3", "l3_contrarian")
        workflow.add_edge("l3_contrarian", "debate_analyst")
        workflow.add_edge("debate_analyst", "debate_strategist")
        workflow.add_edge("debate_strategist", "debate_scout_l3")
        workflow.add_edge("debate_scout_l3", "debate_advisor_ctr")
        workflow.add_conditional_edges("debate_advisor_ctr", advisor_debate_router, {
            "debate_analyst": "debate_analyst",
            "CIO": "enrich_price_data",
        })

        # === Level 4: 最终处方（工具型 Agent） ===
        workflow.add_node("enrich_price_data", enrich_price_data_node)
        workflow.add_node("compute_buy_signals", compute_buy_signals_node)
        workflow.add_node("CIO", cio)
        workflow.add_node("Risk_Director", risk_director)
        workflow.add_node("tools_l4_cio", tools_l4_cio)
        workflow.add_node("tools_l4_risk", tools_l4_risk)
        workflow.add_node("tools_l4_cio_final", tools_l4_cio_final)
        workflow.add_node("msg_clear_l4a", _msg_clear_node)
        workflow.add_node("msg_clear_l4b", _msg_clear_node)
        workflow.add_node("debate_cio_l4", debate_cio_l4)
        workflow.add_node("debate_riskdir_l4", debate_riskdir_l4)
        workflow.add_node("debate_final_ctr", debate_final_ctr)
        workflow.add_node("CIO_Final", cio)

        # L4: enrich → buy_signals → CIO (tool loop)
        workflow.add_edge("enrich_price_data", "compute_buy_signals")
        workflow.add_edge("compute_buy_signals", "CIO")
        workflow.add_conditional_edges("CIO", l4_router_cio, {
            "tools": "tools_l4_cio",
            "CIO": "CIO",
            "msg_clear_l4a": "msg_clear_l4a",
        })
        workflow.add_edge("tools_l4_cio", "CIO")
        workflow.add_edge("msg_clear_l4a", "Risk_Director")

        # L4: Risk Director (tool loop) → debate
        workflow.add_conditional_edges("Risk_Director", l4_router_risk, {
            "tools": "tools_l4_risk",
            "Risk_Director": "Risk_Director",
            "msg_clear_l4b": "msg_clear_l4b",
        })
        workflow.add_edge("tools_l4_risk", "Risk_Director")
        workflow.add_edge("msg_clear_l4b", "debate_cio_l4")

        # L4: debate → CIO Final (tool loop) → END
        workflow.add_edge("debate_cio_l4", "debate_riskdir_l4")
        workflow.add_edge("debate_riskdir_l4", "debate_final_ctr")
        workflow.add_conditional_edges("debate_final_ctr", final_debate_router, {
            "debate_cio": "debate_cio_l4",
            "cio_final": "CIO_Final",
        })

        workflow.add_conditional_edges("CIO_Final", l4_router_cio_final, {
            "tools": "tools_l4_cio_final",
            "CIO_Final": "CIO_Final",
            "cio_final_end": END,
        })
        workflow.add_edge("tools_l4_cio_final", "CIO_Final")

        return workflow.compile()

    def propagate_l1_plan(
        self,
        portfolio_summary: Dict[str, Any],
        portfolio_industries: Optional[List[Dict[str, Any]]] = None,
        user_goal: str = "",
        progress_callback: Optional[Callable] = None,
    ) -> Dict[str, Any]:
        """执行 L1 市场扫描，返回推荐行业计划（不触发 L2-L4）

        Args:
            portfolio_summary: 用户持仓汇总
            portfolio_industries: 从持仓反推的行业分布 [{industry, weight, position_count, codes}, ...]
            user_goal: 用户投资目标（空=默认值博率最高）

        Returns:
            {industries, macro_judge_verdict, market_intel, market_debate_history}
        """
        # 构建 L1-only 子图
        l1_workflow = StateGraph(AdvisorState)

        market_strategist = create_market_strategist(self.llm)
        contrarian = create_contrarian(self.llm)
        macro_judge = create_macro_judge(self.llm)
        tools_l1_market = _make_tool_executor(L1_TOOLS, "market_tool_call_count")
        tools_l1_contrarian = _make_tool_executor(L1_TOOLS, "market_tool_call_count")
        debate_market_strat = _make_two_person_debate_node(
            self.llm, "市场策略师", "strategist_response", "market_debate_state", "contrarian_response"
        )
        debate_contrarian_l1 = _make_two_person_debate_node(
            self.llm, "反向意见者", "contrarian_response", "market_debate_state", "strategist_response"
        )
        debate_market_ctr = _increment_debate_count("market_debate_state")

        l1_router_market = _make_tool_router("market_tool_call_count", "msg_clear_l1a", "market_strategist")
        l1_router_contrarian = _make_tool_router("market_tool_call_count", "msg_clear_l1b", "contrarian")
        market_debate_router = _make_debate_router(
            "market_debate_state",
            self.config.get("market_debate_rounds", 2),
            "macro_judge",
            "debate_market_strat",
        )

        l1_workflow.add_node("market_strategist", market_strategist)
        l1_workflow.add_node("contrarian", contrarian)
        l1_workflow.add_node("tools_l1_market", tools_l1_market)
        l1_workflow.add_node("tools_l1_contrarian", tools_l1_contrarian)
        l1_workflow.add_node("msg_clear_l1a", _msg_clear_node)
        l1_workflow.add_node("msg_clear_l1b", _msg_clear_node)
        l1_workflow.add_node("debate_market_strat", debate_market_strat)
        l1_workflow.add_node("debate_contrarian_l1", debate_contrarian_l1)
        l1_workflow.add_node("debate_market_ctr", debate_market_ctr)
        l1_workflow.add_node("macro_judge", macro_judge)

        l1_workflow.add_edge(START, "market_strategist")
        l1_workflow.add_conditional_edges("market_strategist", l1_router_market, {
            "tools": "tools_l1_market",
            "market_strategist": "market_strategist",
            "msg_clear_l1a": "msg_clear_l1a",
        })
        l1_workflow.add_edge("tools_l1_market", "market_strategist")
        l1_workflow.add_edge("msg_clear_l1a", "contrarian")
        l1_workflow.add_conditional_edges("contrarian", l1_router_contrarian, {
            "tools": "tools_l1_contrarian",
            "contrarian": "contrarian",
            "msg_clear_l1b": "msg_clear_l1b",
        })
        l1_workflow.add_edge("tools_l1_contrarian", "contrarian")
        l1_workflow.add_edge("msg_clear_l1b", "debate_market_strat")
        l1_workflow.add_edge("debate_market_strat", "debate_contrarian_l1")
        l1_workflow.add_edge("debate_contrarian_l1", "debate_market_ctr")
        l1_workflow.add_conditional_edges("debate_market_ctr", market_debate_router, {
            "debate_market_strat": "debate_market_strat",
            "macro_judge": "macro_judge",
        })
        l1_workflow.add_edge("macro_judge", END)

        compiled_l1 = l1_workflow.compile()

        # 构建初始消息：将持仓行业列表 + 用户目标注入市场策略师的上下文
        industries_text = ""
        if portfolio_industries:
            lines = ["以下为用户当前持仓的行业分布："]
            for ind in portfolio_industries:
                codes_str = ", ".join(ind.get("codes", [])[:8])
                lines.append(f"- {ind['industry']}：仓位{ind['weight']:.1f}%，{ind['position_count']}只标的（{codes_str}）")
            if user_goal:
                lines.append(f"\n用户投资目标：{user_goal}")
            else:
                lines.append("\n用户未指定投资目标，请以值博率最高为目标进行判断。")
            lines.append("\n请对以上所有行业执行任务（全覆盖轻量评估 + 自选深度辩论 + 可选机会推荐）。")
            industries_text = "\n".join(lines)

        init_state: AdvisorState = {
            "messages": [HumanMessage(content=f"开始市场扫描\n\n{industries_text}".strip())],
            "portfolio_summary": portfolio_summary,
            "portfolio_industries": portfolio_industries or [],
            "user_goal": user_goal,
            "tier1_reports": [],
            "market_intel": {},
            "market_debate_state": {"history": "", "strategist_response": "", "contrarian_response": "", "count": 0},
            "macro_judge_verdict": "",
            "market_tool_call_count": 0,
        }

        l1_node_mapping = {
            "market_strategist": "L1-市场策略师",
            "contrarian": "L1-反向意见者",
            "tools_l1_market": None,
            "tools_l1_contrarian": None,
            "msg_clear_l1a": None,
            "msg_clear_l1b": None,
            "debate_market_strat": "L1-辩论(策略师)",
            "debate_contrarian_l1": "L1-辩论(反向者)",
            "debate_market_ctr": None,
            "macro_judge": "L1-宏观裁判",
        }

        start_time = time.time()
        final_state = dict(init_state)

        logger.info("[AdvisorGraph:L1] 开始 L1 市场扫描...")
        for chunk in compiled_l1.stream(init_state, stream_mode="updates"):
            for node_name, node_update in chunk.items():
                if node_name.startswith("__"):
                    continue
                if node_update is None:
                    continue
                final_state.update(node_update)

                label = l1_node_mapping.get(node_name)
                if label and progress_callback:
                    try:
                        node_text = ""
                        if isinstance(node_update, dict):
                            mi = node_update.get("market_intel", {})
                            if isinstance(mi, dict) and mi.get("strategist_raw"):
                                node_text = str(mi["strategist_raw"])[:500]
                            elif node_update.get("macro_judge_verdict"):
                                node_text = str(node_update["macro_judge_verdict"])[:500]
                        progress_callback(label, node_text)
                    except Exception:
                        pass

        elapsed = time.time() - start_time
        market_intel = final_state.get("market_intel", {})
        industries = market_intel.get("industries", []) if isinstance(market_intel, dict) else []

        logger.info(f"[AdvisorGraph:L1] 完成，{len(industries)} 个推荐行业，耗时 {elapsed:.1f}s")

        return {
            "industries": industries,
            "macro_judge_verdict": final_state.get("macro_judge_verdict", ""),
            "market_intel": market_intel,
            "market_debate_history": final_state.get("market_debate_state", {}).get("history", ""),
            "elapsed_seconds": round(elapsed, 2),
        }

    def propagate_advice(
        self,
        portfolio_summary: Dict[str, Any],
        tier1_reports: list,
        progress_callback: Optional[Callable] = None,
        selected_industries: Optional[list] = None,
        exposure_context: str = "",
        exposure_matrix: Any = None,
        feedback_context: str = "",
        **config_overrides,
    ) -> Dict[str, Any]:
        """执行组合顾问分析

        Args:
            portfolio_summary: 持仓汇总
            tier1_reports: Tier1 分析报告列表
            progress_callback: 进度回调 fn(node_label, output_text, stage)
            selected_industries: 限定分析的行业列表（None=全量L1扫描）
            exposure_context: 敞口引擎格式化的上下文文本
            exposure_matrix: ExposureMatrix 对象
            **config_overrides: 配置覆盖

        Returns:
            包含 prescription, cio_verdict, 各级分析结果 的字典
        """
        init_msg = "开始市场扫描"
        if selected_industries:
            init_msg = f"开始分析选定行业: {', '.join(selected_industries[:5])}"

        # 将 Tier1 报告 + 敞口矩阵格式化为 agent 可读上下文，注入初始消息
        init_messages = [HumanMessage(content=init_msg)]
        report_ctx = _format_tier1_report_context(tier1_reports)
        if report_ctx:
            init_messages.append(HumanMessage(content=report_ctx))
        if exposure_context:
            init_messages.append(HumanMessage(content=exposure_context))
        if feedback_context:
            init_messages.append(HumanMessage(content=feedback_context))

        # 持仓体检：确定性计算健康分/P&L/成本，注入 CIO/Strategist prompt
        positions = portfolio_summary.get("positions", [])
        audit_results = audit_positions(positions)
        logger.info(f"[AdvisorGraph] 持仓体检完成，{len(audit_results)} 只标的")

        init_state: AdvisorState = {
            "messages": init_messages,
            "portfolio_summary": portfolio_summary,
            "tier1_reports": tier1_reports,
            "exposure_matrix": exposure_matrix,
            "selected_industries": selected_industries or [],
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
            "scout_tool_call_count": 0,
            "scontrarian_tool_call_count": 0,
            # L3
            "analyst_assessment": "",
            "strategist_assessment": "",
            "scout_assessment": "",
            "contrarian_assessment": "",
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
            "buy_signals": {},
            "market_signals": {},
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
            # 持仓体检
            "audit_results": audit_results,
            # 敞口矩阵
            "exposure_context": exposure_context,
            "exposure_matrix": exposure_matrix,
            # 反馈闭环
            "feedback_context": feedback_context,
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
                "max_prescription_items", self.config.get("max_prescription_items", 30)),
            "rebalance_preference": config_overrides.get(
                "rebalance_preference", self.config.get("rebalance_preference", "opportunistic")),
            # L3/L4 计数器
            "analyst_tool_call_count": 0,
            "strategist_tool_call_count": 0,
            "cio_tool_call_count": 0,
            "cio_final_tool_call_count": 0,
            "risk_tool_call_count": 0,
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
            "l3_contrarian": "L3-组合反向者",
            "CIO": "L4-CIO",
            "Risk_Director": "L4-风险总监",
            "debate_cio_l4": "L4-辩论(CIO)",
            "debate_riskdir_l4": "L4-辩论(风险总监)",
            "debate_final_ctr": None,
            "CIO_Final": "L4-CIO终裁",
            "tools_l3_analyst": None,
            "tools_l3_strategist": None,
            "msg_clear_l3a": None,
            "msg_clear_l3b": None,
            "tools_l4_cio": None,
            "tools_l4_risk": None,
            "tools_l4_cio_final": None,
            "msg_clear_l4a": None,
            "msg_clear_l4b": None,
        }

        start_time = time.time()
        final_state = dict(init_state)

        logger.info("[AdvisorGraph] 开始四层对抗分析...")
        for chunk in self.graph.stream(init_state, stream_mode="updates"):
            for node_name, node_update in chunk.items():
                if node_name.startswith("__"):
                    continue
                if node_update is None:
                    continue
                final_state.update(node_update)

                label = node_mapping.get(node_name)
                if label and progress_callback:
                    try:
                        # 提取节点输出的文本摘要
                        node_text = ""
                        if isinstance(node_update, dict):
                            for k in ["macro_judge_verdict", "stock_judge_verdict",
                                       "analyst_assessment", "strategist_assessment",
                                       "scout_assessment", "cio_verdict", "risk_director_review",
                                       "market_intel"]:
                                v = node_update.get(k, "")
                                if isinstance(v, str) and v:
                                    node_text = v[:500]
                                    break
                                elif isinstance(v, dict) and v.get("strategist_raw"):
                                    node_text = str(v["strategist_raw"])[:500]
                                    break
                        progress_callback(label, node_text)
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
            "contrarian_assessment": final_state.get("contrarian_assessment", "")
                or final_state.get("advisor_debate_state", {}).get("contrarian_response", ""),
            "macro_judge_verdict": final_state.get("macro_judge_verdict", ""),
            "market_intel": final_state.get("market_intel", {}),
            "stock_candidates": final_state.get("stock_candidates", []),
            "stock_judge_verdict": final_state.get("stock_judge_verdict", ""),
            "risk_director_review": final_state.get("risk_director_review", ""),
            "debate_history": final_state.get("advisor_debate_state", {}).get("history", ""),
            "market_debate_history": final_state.get("market_debate_state", {}).get("history", ""),
            "stock_debate_history": final_state.get("stock_debate_state", {}).get("history", ""),
            "elapsed_seconds": round(elapsed, 2),
            # ── 新增字段 ──
            "price_context": final_state.get("price_context", {}),
            "risk_debate_final": final_state.get("risk_debate_final", {}),
            "portfolio_summary_snapshot": final_state.get("portfolio_summary", {}),
            "audit_results": final_state.get("audit_results", []),
            "buy_signals": final_state.get("buy_signals", {}),
            "market_signals": final_state.get("market_signals", {}),
        }
