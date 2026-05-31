## 1. 完善基金后端的辩论节点角色

- [ ] 1.1 在 `tradingagents/agents/researchers/` 下创建特定的 `fund_bull_researcher.py` 节点。
- [ ] 1.2 在 `tradingagents/agents/researchers/` 下创建带有硬约束基金视角的 `fund_bear_researcher.py`（加入最大回撤、经理换手率等 Prompt）。
- [ ] 1.3 在 `tradingagents/agents/managers/` 下创建裁判节点 `fund_research_manager.py` 和 `fund_portfolio_manager.py`（如果不复用股票的话）。
- [ ] 1.4 在 `tradingagents/agents/risk_mgmt/` 下创建 `fund_aggressive/neutral/conservative_debator.py` 或对原有节点进行兼容性改造，以支持基金数据。

## 2. 改造后端图模型与状态机

- [ ] 2.1 在 `fund_graph.py` 中更新 `FundAgentState` 字典，引入 `investment_debate_state` 和 `risk_debate_state` 等控制状态。
- [ ] 2.2 引入股票版的 `ConditionalLogic` 或将条件路由逻辑加入 `fund_graph.py` 以控制对决回环 (Bull <-> Bear) 的轮数。
- [ ] 2.3 在 `fund_graph.py` 的执行流 `run()` 末尾增加落盘 JSON 持久化逻辑，在 `results` 目录下生成 `full_states_log.json` 和对齐的 Markdown 输出。

## 3. 前端支持流式解析对决的重构

- [ ] 3.1 创建 `frontend/src/components/Analysis/DebateTimeline.vue` 组件，内部包含从 `history` 长文本到对话气泡的分发切片正则表达式及样式。
- [ ] 3.2 在 `SingleAnalysis.vue` 的 `reportMappings` 中补充 `investment_debate_state: '⚔️ 投资多空辩论'` 与 `risk_debate_state: '🛡️ 风险控制辩论'` 的定义。
- [ ] 3.3 修改 `SingleAnalysis.vue` 的 `<el-tab-pane>` 渲染区域，在碰到 `history` 对象时渲染新组件 `DebateTimeline`，并实现无解析的兜底优雅降级（stringify + markdown）。