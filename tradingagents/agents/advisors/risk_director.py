"""风险总监 (L4 辩手) — 工具型 Agent，审查 CIO 处方"""

from __future__ import annotations
from langchain_core.messages import HumanMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from tradingagents.utils.logging_init import get_logger

logger = get_logger("default")

RISK_SYSTEM_PROMPT = """你是风险总监（Risk Director），职责是在 CIO 终裁前对处方进行独立的终端风险审查。

## 你的立场
- 你不对标的基本面做判断（那是 L1/L2 的职责）
- 你的职责是审查 CIO 处方的 **组合层面风险**：集中度、流动性、尾部风险、黑天鹅
- 你对每一句 CIO 的判断都要问一句"万一错了呢？"

## 你的工具
1. `get_prescription_draft()` — 读取 CIO 初稿处方
2. `check_stress_scenario(scenario)` — 获取场景压力测试结果

## 审查维度
- **集中度风险**：处方是否导致过度集中？
- **流动性风险**：建议买入标的中是否有流动性差的？
- **尾部风险**：什么情况下会同时亏损？
- **操作风险**：卖出理由是否充分？
- **处方纪律**：是否有冗余操作？

## 输出格式
对每条操作：
- 风险审查意见：通过 / 有风险 / 否决
- 风险说明
- 修正建议

最后给出总体风险评级：低风险 / 中等风险 / 高风险。用中文回答。"""


def create_risk_director(llm, tools=None, shared_state=None):
    """创建 Risk Director 工具型 Agent"""
    if shared_state is None:
        shared_state = {}

    if tools is None:
        from .risk_tools import create_risk_tools
        def _sp():
            return shared_state.get("state", {})
        tools = create_risk_tools(_sp)

    prompt = ChatPromptTemplate.from_messages([
        ("system", "{system_message}"),
        MessagesPlaceholder(variable_name="messages"),
    ])
    prompt = prompt.partial(system_message=RISK_SYSTEM_PROMPT)
    chain = prompt | llm.bind_tools(tools)

    def risk_director_node(state: dict) -> dict:
        shared_state["state"] = state

        portfolio = state.get("portfolio_summary", {})
        audit_results = state.get("audit_results", [])

        # 集中度摘要
        concentration_summary = "无持仓数据"
        if isinstance(audit_results, list) and audit_results:
            top3 = sorted(
                audit_results,
                key=lambda x: abs(x.get("weight", 0)),
                reverse=True,
            )[:3]
            top3_str = ", ".join(
                f"{a.get('code', '?')} {a.get('weight', 0):.1f}%"
                for a in top3
            )
            concentration_summary = f"Top-3 持仓: {top3_str}"

        msgs = list(state.get("messages", []))
        init_content = (
            f"请审查 CIO 的处方草案。\n\n"
            f"### 持仓集中度\n{concentration_summary}\n\n"
            f"请先调用 get_prescription_draft() 查看 CIO 处方，"
            f"再调用 check_stress_scenario 检查压力测试结果。"
        )
        msgs.append(HumanMessage(content=init_content))

        logger.info("[Risk Director] 开始")
        result = chain.invoke(msgs)

        review = (result.content if hasattr(result, "content")
                  else str(result))
        logger.info(
            f"[Risk Director] 完成，输出 {len(review)} 字符")

        has_tool_calls = (hasattr(result, "tool_calls") and
                          result.tool_calls)
        messages_out = [result]
        if not has_tool_calls:
            return {
                "messages": messages_out,
                "risk_director_review": review,
            }
        return {"messages": messages_out}

    return risk_director_node
