# Tasks: Fund Adversarial Debate

## 1. 后端验证

- [x] 1.1 确认 `fund_graph.py` 辩论循环正常终止：用真实基金代码（如 270042）触发分析，`investment_debate_state.count` 达到 `max_debate_rounds` 后流转到 `Fund Research Manager`
- [x] 1.2 确认 `risk_debate_state` 三方辩论正常终止：`count` 达到 `max_risk_discuss_rounds` 后流转到 `Fund Trader`
- [x] 1.3 确认返回的 `investment_debate_state.history` 包含角色前缀（如 `Bull Analyst:` / `Bear Analyst:`）可供前端切分
- [x] 1.4 确认 `fund_risk_debators.py` 三方（Aggressive/Neutral/Conservative）的 history 格式一致，包含角色前缀

## 2. 前端验证

- [ ] 2.1 在 SingleAnalysis 页面触发基金分析，确认结果 Tab 中出现"⚔️ 投资多空辩论"和"🛡️ 风险控制辩论"两个 Tab
- [ ] 2.2 确认 `DebateTimeline.vue` 成功将 history 切分为对话气泡（非 JSON 降级渲染）
- [ ] 2.3 确认降级场景：空 history 时显示 fallback（无崩溃）

## 3. Bug 修复

- [ ] 3.1 修复 1.3/1.4/2.2 中发现的任何格式不匹配或渲染 bug

## 4. 归档

- [ ] 4.1 更新 `docs/wiki/index.md` 补充基金辩论架构条目
- [ ] 4.2 commit openspec 变更记录
