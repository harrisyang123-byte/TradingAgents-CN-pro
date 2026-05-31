## Why

目前基金分析 (`fund_graph.py`) 的引擎为单向串行流水线，完全缺失原版股票系统中的“多空双派（Bull vs Bear）对抗式辩论”与“三方风控辩论（Aggressive/Neutral/Conservative）”机制，导致输出的报告同质化严重。并且前端在面对 JSON 对象格式的报告时直接采用 `JSON.stringify`，体验极差。需要引入深度对决机制挖掘如最大回撤、经理换手率等基金特有风险。

## What Changes

- 在 `fund_graph.py` 引入原版股票的 `ConditionalLogic` 辩论图模型
- 新增 `Fund Bull Researcher`、`Fund Bear Researcher` 角色，进行多轮投资对决
- 新增 `Fund Aggressive Analyst`、`Fund Conservative Analyst`、`Fund Neutral Analyst`，进行风险探讨对决
- 优化前端 `SingleAnalysis.vue` 对长辩论文本的渲染机制，由 `JSON.stringify` 改为流式对话气泡结构 (`DebateTimeline.vue`)
- 实现对对决记录持久化的 JSON / Markdown 日志保存机制（复用内存和文件存取）

## Capabilities

### New Capabilities
- `fund-adversarial-debate`: 实现单只基金 Tier 1 级别的双层深度辩论流程（投资决策对决、风险管理对决）。
- `debate-ui-renderer`: 前端支持对多轮复杂角色对话的渲染解析（时间轴/聊天气泡展示）。

### Modified Capabilities
- `fund-analysis-pipeline`: 从单向串行改造为带回环的 LangGraph 图流程。

## Impact

- `fund_graph.py` 将迎来重大重构，变成包含回环图机制的复杂图
- 需要新增多个专门针对基金角色的 LLM Prompt（位于 `tradingagents/agents/researchers/` 及相关目录）
- 前端 `SingleAnalysis.vue` 与新 `DebateTimeline.vue` 需要深度整合并能够接住后端的 JSON History 对象
- 持久化逻辑需要同步调整以保证 JSON 落盘完整性