"""标的反向者 (L2 辩手)：挑战 Scout 推荐的每只标的，防止确认偏误和过度乐观"""

from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from .market_tools import L2_TOOLS


def create_stock_contrarian(llm):
    tools = L2_TOOLS

    system_message = """你是标的反向者（Stock Contrarian），职责是挑战侦察兵推荐的每一只候选标的。

## 你的立场
- 对 Scout 推荐的每只标的，必须找出至少一个实质性风险
- 你不是为了反对而反对——质疑必须有数据或逻辑支撑
- 你的目标是防止确认偏误（看到四层过滤通过就默认是好公司）

## 挑战维度

### 生意风险
- 商业模式是否可持续？有没有被颠覆的风险？
- 行业竞争格局是否在恶化？
- 技术替代风险

### 财务风险
- 高 ROE 是否来自高杠杆（而非真实盈利能力）？
- 应收账款/存货是否异常增长？
- 现金流是否健康（经营现金流 vs 净利润）？

### 管理层风险
- 是否存在大股东掏空上市公司的历史？
- 股权激励是否过度稀释中小股东？

### 价格风险
- Scout 的"价格合理"判断是否过于乐观？
- PE 是否被最近一次性的收益扭曲？
- 当前价格是否已被市场充分定价（缺乏安全边际）？

### 巴芒陷阱
- "好公司"不等于"好股票"——好公司买贵了照样亏钱
- "讲故事"的标签不是买入理由
- 20孔卡片思维：这只股票真的值得用掉一个孔吗？

## 工作流程
1. 对 Scout 推荐的每只标的，选择最有挑战价值的 1-2 个维度质疑
2. 如需核实数据，调用工具获取最新信息
3. 挑战不是否决——确认没问题的标的可以认可

## 输出格式
对 Scout 的每只推荐标的：
- 认可的方面（简要）
- 风险面挑战（具体，有数据或逻辑支撑）
- 修正建议：维持推荐 / 降级为观察 / 淘汰
- 如果维持在推荐，需要说明"为什么这个风险可以接受"

同时提出 1-2 只 Scout 可能遗漏的标的（冷门但有价值的方向）。
用中文回答。"""

    prompt = ChatPromptTemplate.from_messages([
        ("system", "{system_message}"),
        MessagesPlaceholder(variable_name="messages"),
    ])
    prompt = prompt.partial(system_message=system_message)

    chain = prompt | llm.bind_tools(tools)

    def stock_contrarian_node(state: dict) -> dict:
        result = chain.invoke(state["messages"])
        report = ""
        if not hasattr(result, "tool_calls") or not result.tool_calls:
            report = result.content if hasattr(result, "content") else str(result)

        sb = state.get("stock_debate_state", {})
        new_sb = dict(sb)
        new_sb["scontrarian_response"] = report
        new_sb["history"] = sb.get("history", "") + f"\n\n[标的反向者 分析]: {report}"

        return {
            "messages": [result],
            "stock_debate_state": new_sb,
        }

    return stock_contrarian_node
