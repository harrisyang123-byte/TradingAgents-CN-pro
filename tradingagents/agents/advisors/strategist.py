"""策略师 (L3) — 工具型 Agent，组合构建 + 逆向思维"""

from __future__ import annotations
from langchain_core.messages import HumanMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from tradingagents.utils.logging_init import get_logger

logger = get_logger("default")

STRATEGIST_SYSTEM_PROMPT = """你是组合顾问团队的策略师。你的职责是从组合构建角度评估仓位分布的合理性。

## 你的工具
1. `compute_sector_concentration()` — 计算行业集中度
2. `compute_top_holdings_risk(n)` — 前 N 大持仓合计权重和回撤估算
3. `compute_cash_drag()` — 现金拖累和机会成本

## 工作流程
1. 调用 `compute_sector_concentration()` 了解行业分布
2. 调用 `compute_top_holdings_risk(5)` 了解集中度
3. 调用 `compute_cash_drag()` 了解现金效率
4. 综合以上数据，给出组合构建建议

## 评估维度
1. **集中度分析**：是否突破单只/行业红线
2. **逆向思维**：最大仓位下跌 30% 的影响，行业整体下跌 20% 的影响
3. **认知偏差检测**：禀赋效应/近因偏差/锚定效应
4. **组合缺口识别**：缺少哪些方向的配置

用中文回答，保持逆向思维立场。"""


def create_strategist(llm, tools=None, shared_state=None):
    """创建 L3 Strategist 工具型 Agent"""
    if shared_state is None:
        shared_state = {}

    if tools is None:
        from .strategist_tools import create_strategist_tools
        def _sp():
            return shared_state.get("state", {})
        tools = create_strategist_tools(_sp)

    prompt = ChatPromptTemplate.from_messages([
        ("system", "{system_message}"),
        MessagesPlaceholder(variable_name="messages"),
    ])
    prompt = prompt.partial(system_message=STRATEGIST_SYSTEM_PROMPT)
    chain = prompt | llm.bind_tools(tools)

    def strategist_node(state: dict) -> dict:
        shared_state["state"] = state

        portfolio = state.get("portfolio_summary", {})
        positions = portfolio.get("positions", [])
        available_cash = portfolio.get("available_cash", 0)
        total_assets = portfolio.get("total_assets", 1)

        msgs = list(state.get("messages", []))
        cash_ratio = available_cash / max(total_assets, 1) * 100
        init_content = (
            f"请评估当前组合的仓位分布。\n\n"
            f"总资产: ¥{total_assets:,.2f}\n"
            f"可用现金: ¥{available_cash:,.2f} "
            f"(现金占比 {cash_ratio:.1f}%)\n"
            f"持仓数: {len(positions)} 只\n\n"
            f"请先调用 compute_sector_concentration、"
            f"compute_top_holdings_risk、compute_cash_drag "
            f"获取数据后再分析。"
        )
        msgs.append(HumanMessage(content=init_content))

        logger.info("[Strategist] 开始")
        result = chain.invoke(msgs)

        report = (result.content if hasattr(result, "content")
                  else str(result))
        logger.info(f"[Strategist] 完成，输出 {len(report)} 字符")

        has_tool_calls = (hasattr(result, "tool_calls") and
                          result.tool_calls)
        messages_out = [result]
        if not has_tool_calls:
            return {
                "messages": messages_out,
                "strategist_assessment": report,
            }
        return {"messages": messages_out}

    return strategist_node
