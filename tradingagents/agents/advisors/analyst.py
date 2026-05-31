"""持仓分析师 (L3) — 工具型 Agent，逐只评估安全边际"""

from __future__ import annotations
from langchain_core.messages import HumanMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from tradingagents.utils.logging_init import get_logger

logger = get_logger("default")

ANALYST_SYSTEM_PROMPT = """你是组合顾问团队的持仓分析师。你的职责是逐只评估每个持仓标的的安全边际和投资价值。

## 你的工具
1. `read_tier1_report(code)` — 读取单只标的的 Tier1 深度分析报告
2. `get_position_audit(code)` — 读取持仓体检数据（成本、现价、盈亏、健康分）

## 工作流程
1. 你需要对所有持仓标的逐一调用 `get_position_audit(code)` 获取最新体检数据
2. 对有 Tier1 报告的标的，调用 `read_tier1_report(code)` 获取深度分析
3. 综合两者，对每只标的给出安全边际评估

## 评估维度
- 安全边际：当前价格 vs 报告估值/评级
- 浮盈/浮亏分析：是否应该止盈或止损
- 报告时效：报告是否过期
- 操作建议：持有/加仓/减仓/清仓

## 基金持仓专项评估
- 基金经理质量：从业年限、历史业绩、是否近期变更
- 费率合理性：管理费+托管费 vs 同类
- 业绩持续性：近1/3/5年收益
- 策略一致性：基金名与实际持仓风格是否一致
- 赎回判断：浮亏是市场系统性下跌还是基金本身问题

用中文回答，保持客观。输出要覆盖每只持仓的安全边际评估。"""


def create_portfolio_analyst(llm, tools=None, shared_state=None):
    """创建 L3 Analyst 工具型 Agent

    Args:
        llm: LLM 实例
        tools: 外部创建的工具列表（图层面创建并传入）
        shared_state: 共享状态引用字典，tools 和 agent 共用同一 state 引用
    """
    if shared_state is None:
        shared_state = {}

    if tools is None:
        from .analyst_tools import create_analyst_tools
        def _sp():
            return shared_state.get("state", {})
        tools = create_analyst_tools(_sp)

    prompt = ChatPromptTemplate.from_messages([
        ("system", "{system_message}"),
        MessagesPlaceholder(variable_name="messages"),
    ])
    prompt = prompt.partial(system_message=ANALYST_SYSTEM_PROMPT)
    chain = prompt | llm.bind_tools(tools)

    def portfolio_analyst_node(state: dict) -> dict:
        shared_state["state"] = state

        portfolio = state.get("portfolio_summary", {})
        positions = portfolio.get("positions", [])

        # L1/L2 context for initial message
        market_intel = state.get("market_intel", {})
        stock_candidates = state.get("stock_candidates", [])
        l1_l2_parts = []
        judge_verdict = market_intel.get("judge_verdict", "")
        if isinstance(market_intel, dict) and judge_verdict:
            l1_l2_parts.append(f"## L1 行业方向\n{judge_verdict[:1500]}")
        if stock_candidates:
            cand_lines = [
                f"- {c.get('code', '?')} ({c.get('name', '?')}): "
                f"建议{c.get('action', '?')}"
                for c in stock_candidates[:10]
            ]
            l1_l2_parts.append(
                "## L2 候选标的\n" + "\n".join(cand_lines))

        position_summary = (
            f"总资产: ¥{portfolio.get('total_assets', 0):,.2f}\n"
            f"可用现金: ¥{portfolio.get('available_cash', 0):,.2f}\n"
            f"持仓总数: {len(positions)} 只\n"
        )

        l1_l2_text = "\n\n".join(l1_l2_parts) if l1_l2_parts else "无 L1/L2 数据"

        msgs = list(state.get("messages", []))
        init_content = (
            f"请开始分析所有持仓标的。\n\n"
            f"{position_summary}\n"
            f"{l1_l2_text}\n\n"
            f"提示：请先用 get_position_audit 逐只读取持仓体检数据，"
            f"有 Tier1 报告的再调用 read_tier1_report 获取深度分析。"
        )
        msgs.append(HumanMessage(content=init_content))

        logger.info(
            f"[Portfolio Analyst] 开始，{len(positions)} 只持仓")
        result = chain.invoke(msgs)

        report = (result.content if hasattr(result, "content")
                  else str(result))
        logger.info(
            f"[Portfolio Analyst] 完成，输出 {len(report)} 字符")

        has_tool_calls = (hasattr(result, "tool_calls") and
                          result.tool_calls)
        messages_out = [result]
        if not has_tool_calls:
            return {
                "messages": messages_out,
                "analyst_assessment": report,
            }
        return {"messages": messages_out}

    return portfolio_analyst_node
