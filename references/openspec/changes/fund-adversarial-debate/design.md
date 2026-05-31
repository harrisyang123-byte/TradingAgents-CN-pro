## Context

目前基金的分析流程位于 `tradingagents/graph/fund_graph.py` 中，采用基于 LangGraph 的单向直线执行（经理分析 -> 持仓分析 -> 风险评估 -> 裁判）。在股票分析流程 (`trading_graph.py`) 中，存在由 `ConditionalLogic` 主导的回环流 (Bull vs Bear) 和多方探讨 (Aggressive vs Neutral vs Conservative)。
本次需要将股票的这种高阶状态图设计完全复制并适配到基金分析上，并解决前端 (`SingleAnalysis.vue`) 渲染 `investment_debate_state` 及 `risk_debate_state` 等含有多轮对话 JSON 时导致的展示问题。

## Goals / Non-Goals

**Goals:**
- 将 `fund_graph.py` 的路由逻辑重构为回环图模型。
- 创建特定于基金的多空对决角色的 LLM Prompt（关注持仓集中度、回撤、换手率）。
- 前端添加支持流式解析对决对话并渲染气泡时间的 `DebateTimeline.vue` 组件，并将其集成到 `SingleAnalysis.vue`。
- 存档时序列化基金的完整 Debate 状态数据。

**Non-Goals:**
- 不重构 Tier 2（全部资产）维度的投资组合配置引擎（留待下一个 openspec）。
- 不修改原有的基本信息接口（AKShare获取基金数据的 ToolNode）。

## Decisions

**Decision 1: 复用 ConditionalLogic 类并保持基金独立引擎**
直接引入并适配 `tradingagents/graph/conditional_logic.py`。与其为了合并股票和基金的流转而去把两个巨大的文件合并增加风险，不如维持独立的 `fund_graph.py`，但在其中使用与股票一致的路由条件，保证了业务隔离性同时快速落地。

**Decision 2: 独立出 `DebateTimeline.vue` 组件进行渲染**
原本在 `SingleAnalysis.vue` 中 `formatReportContent` 是通过 `JSON.stringify` 强行解析对象。现决定将 `investment_debate_state` 拦截到 `<DebateTimeline :history="report.content.history"/>`，将内部长字符串按角色正则解析分块。这样可复用现有的渲染框架并兼顾 Markdown。

**Decision 3: 专门定制的 Prompt**
因为基金是对股票的一揽子包装，所以 `Fund Bear Researcher` 必须硬编码基金特有维度（例如最大回撤、经理变更、持仓雷同）。而并非通用的一句“你是空头”。

## Risks / Trade-offs

- **Risk: 基金可能不包含具体的重仓股数据，导致空头分析师“失焦”**
  - *Mitigation*: 在 Prompt 层面设置 fallback 指令：“若未能获取前十大重仓明细，请直接质疑其信息不透明及流动性隐患。”
- **Risk: 大模型可能在长对话后返回错误 JSON 或中断**
  - *Mitigation*: 前端增加对 `history` 中断的不完美处理容忍度，后端在状态转流时捕获解析异常流转到最终裁判即可。