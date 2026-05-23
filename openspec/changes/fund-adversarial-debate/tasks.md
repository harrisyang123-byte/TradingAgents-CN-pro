# Tasks: Fund Adversarial Debate

## 1. 后端验证

- [x] 1.1 确认 `fund_graph.py` 辩论循环正常终止：用真实基金代码（如 270042）触发分析，`investment_debate_state.count` 达到 `max_debate_rounds` 后流转到 `Fund Research Manager`
- [x] 1.2 确认 `risk_debate_state` 三方辩论正常终止：`count` 达到 `max_risk_discuss_rounds` 后流转到 `Fund Trader`
- [x] 1.3 确认返回的 `investment_debate_state.history` 包含角色前缀（如 `Bull Analyst:` / `Bear Analyst:`）可供前端切分
- [x] 1.4 确认 `fund_risk_debators.py` 三方（Aggressive/Neutral/Conservative）的 history 格式一致，包含角色前缀

## 2. 前端验证

- [x] 2.1 在 SingleAnalysis 页面触发基金分析，确认结果 Tab 中出现"⚔️ 投资多空辩论"和"🛡️ 风险控制辩论"两个 Tab（reportMappings 已配置 L1310-1311）
- [x] 2.2 确认 `DebateTimeline.vue` 成功将 history 切分为对话气泡：后端正则兼容性验证通过 — 投资辩论 2 bubbles (Bull/Bear)，风控辩论 3 bubbles (Aggressive/Conservative/Neutral)
- [x] 2.3 确认降级场景：空 history 时 `parsedBubbles.length === 0` → fallback 渲染 markdown，无崩溃

## 3. Bug 修复

- [x] 3.1 修复 Bug 1: `No module named 'tradingagents.dataflows.utils'` — 移除不存在的 import，改为 inline 字符串替换
- [x] 3.2 修复 Bug 2: `unhashable type: 'dict'` in `graph_progress_callback` — 新增 dict 类型消息处理，提取 `step` 字段作为节点名
- [x] 3.3 修复 Bug 3: `state = {}` 硬编码导致基金分析结果全部为空 — 从 `fund_graph.run()` 返回值提取 `state` 和 `decision`
- [x] 3.4 修复 Bug 4: `report_fields` 缺少基金字段 — 追加 `fund_manager_report`, `fund_holdings_report`, `fund_risk_report`, `investment_debate_state`, `risk_debate_state`

## 4. 归档

- [ ] 4.1 更新 `docs/wiki/index.md` 补充基金辩论架构条目
- [ ] 4.2 commit openspec 变更记录
