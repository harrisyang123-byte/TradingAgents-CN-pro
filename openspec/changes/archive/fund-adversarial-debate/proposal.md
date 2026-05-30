# Proposal: Fund Adversarial Debate

## Why

当前基金分析引擎（`fund_graph.py`）在 fund-tier1-analysis 实现时已引入辩论图架构，但缺少独立变更记录。同时前端对 `investment_debate_state` / `risk_debate_state` 的渲染质量未经验证——辩论历史是否正确切分为对话气泡、降级逻辑是否生效、两个页面（SingleAnalysis / FundDetail）是否都覆盖，尚不清楚。

<!-- Dialectical Analysis -->
**方案对比**：
- 方案 A（直接归档）：标记所有 task 完成，不做验证 → 风险：代码可运行但前端渲染有 bug 未发现
- 方案 B（补测试再归档）：先跑真实基金做端到端验证，确认辩论渲染正常后归档 → 选择此方案

**最可能失败的点**：`DebateTimeline.vue` 依赖正则切分 history 字符串，若后端 prompt 输出格式不严格（角色前缀不匹配），气泡渲染会静默降级为 JSON 块。

## What

1. 补充 openspec 变更记录（retroactive）
2. 端到端验证辩论流程：后端图 + 前端渲染
3. 修复发现的任何 bug
