"""反向意见者 (L1 辩手)：挑战市场策略师的行业判断，提供风险面和逆向视角"""

from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from .market_tools import L1_TOOLS


def create_contrarian(llm):
    tools = L1_TOOLS

    system_message = """你是反向意见者（Contrarian），职责是挑战市场策略师的行业判断，从风险面和逆向视角审视。

## 你的立场
- 对市场策略师推荐的每个行业方向，必须提出至少一个实质性风险面质疑
- 你不是为了反对而反对——你的质疑必须有数据支撑或逻辑推理
- 你的目标是帮助发现策略师遗漏的盲点和过度乐观的假设

## 逆向思维的维度
1. **市场共识风险**：当所有人看好时，预期可能已被充分定价
2. **行业生命周期误判**：策略师可能把期望膨胀期误判为稳步增长期
3. **政策/监管风险**：行业面临的政策不确定性
4. **周期性风险**：行业当前处于周期哪个位置
5. **外部冲击**：宏观环境变化、国际关系等
6. **资金面陷阱**：资金流入可能是短期炒作而非长期看好

## 工作流程
1. 如果争议点需要数据核实，调用工具获取最新数据
2. 对策略师推荐的行业，重点检查是否处于期望膨胀期
3. 对涨幅过高的行业，检查是否有泡沫特征

## 输出格式
对策略师的每个行业推荐，给出：
- 认可的方面（如果有）
- 风险面挑战
- 数据支撑（如有）
- 修正建议（降级/缩小范围/延后观察）

同时推荐 1-2 个策略师可能忽略的冷门但有价值的行业方向。

用中文回答，保持批判性但建设性的基调。"""

    prompt = ChatPromptTemplate.from_messages([
        ("system", "{system_message}"),
        MessagesPlaceholder(variable_name="messages"),
    ])
    prompt = prompt.partial(system_message=system_message)

    chain = prompt | llm.bind_tools(tools)

    def contrarian_node(state: dict) -> dict:
        result = chain.invoke(state["messages"])
        report = ""
        if not hasattr(result, "tool_calls") or not result.tool_calls:
            report = result.content if hasattr(result, "content") else str(result)

        mb = state.get("market_debate_state", {})
        new_mb = dict(mb)
        new_mb["contrarian_response"] = report
        new_mb["history"] = mb.get("history", "") + f"\n\n[反向意见者 分析]: {report}"

        existing_intel = dict(state.get("market_intel", {}))
        existing_intel["contrarian_raw"] = report

        return {
            "messages": [result],
            "market_debate_state": new_mb,
            "market_intel": existing_intel,
        }

    return contrarian_node
