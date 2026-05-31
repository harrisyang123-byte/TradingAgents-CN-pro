# L3/L4 Agent 升级

## Why

### 当前问题

当前 `AdvisorGraph` 四层架构中，L1/L2 是真正的 LangGraph Agent（`bind_tools` + `ToolNode` + 条件路由），但 L3/L4 全是单次 `llm.invoke(prompt)` 调用。导致两个核心问题：

1. **CIO 处方覆盖不全**：CIO 只能产出 ~8 条处方，而用户持仓有 36 只标的。原因是单次调用受 context window 限制，无法逐批阅读所有持仓数据
2. **无迭代决策能力**：CIO 无法主动查询信息，所有数据必须提前塞进 prompt。当需要查看某个行业的 L1 评级、或搜索某行业的优质公司时，CIO 没有能力做

### 用户反馈

- "8条处方...不是完整的持仓建议"
- "l3/l4应都用真正的agent才行"
- "如果cio看好了某个行业，是不是还可以调用他的员工去专门搜索这个行业的优秀公司？"

## What

将 L3（Analyst/Strategist/Scout_L3）和 L4（CIO/Risk_Director）全部从单次 `llm.invoke(prompt)` 升级为工具型 LangGraph Agent，复用 L1/L2 已验证的 Agent 模式：

- Agent 节点：`ChatPromptTemplate + bind_tools(tools)` → 多步迭代
- ToolNode：`_make_tool_executor(tools, counter_key)` → 工具执行 + 计数器
- 条件路由：`_make_tool_router(counter_key, next_node, agent_node)` → 有工具调用则循环，否则继续

CIO 获得 6 个新工具，包括派员工搜索行业的 `dispatch_scout` 能力。

### 三种调用路径

1. **前端页面按钮**：用户点击"生成建议" → 后端异步执行 → WebSocket 推进度 → 前端展示
2. **CLI 对话调用**：`python cli/run_advisor.py run --user-id xxx` → 终端打印完整处方 + 行业配置表
3. **Web API**：`POST /api/portfolio/advice/generate` → 返回 advice_id → 前端轮询结果

<!-- Dialectical Analysis -->

### 方案对比

| 方案 | 优点 | 缺点 |
|------|------|------|
| A: 纯 prompt 增强 (当前) | 改动最小 | 无法根本解决覆盖不全，受 context window 硬限制 |
| B: 工具型 Agent (选此方案) | 逐批处理数据，迭代决策，可主动查询 | 实现工作量较大，需要改图结构 |
| C: 多轮 invoke 拼接 | 实现简单 | 状态管理复杂，没有工具调用能力 |

### 风险对冲

- **CIO 工具调用超限**：`_make_tool_executor` 的 max_calls=3 强制总结机制兜底，保证不会无限循环
- **dispatch_scout 数据质量**：依赖 L2 已有工具函数（get_industry_constituents 等），这些函数已有降级/兜底逻辑
- **HK 标的覆盖**：dispatch_scout 在 HK 市场可能拿不到完整财务数据，但行情数据可用
