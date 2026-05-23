# 基金对抗辩论架构

> 基金分析中的多层对抗辩论机制，确保分析结论经过充分的多角度质询。

## 辩论结构

### Tier 1: 分析师团队（独立并行）
- **基金经理分析师** (FundManagerAnalyst) — 经理履历、历史业绩、投资风格
- **持仓分析师** (FundHoldingsAnalyst) — 资产配置、重仓股、行业分布
- **风险分析师** (FundRiskAnalyst) — 回撤、波动率、尾部风险

### Tier 2: 投资多空辩论
- **多方研究员** (BullResearcher) — 论证投资价值
- **空方研究员** (BearResearcher) — 挑战投资逻辑
- **研究总监** (ResearchManager) — 综合双方观点，给出研究结论

### Tier 3: 风控三方辩论
- **激进型** (Aggressive) — 高弹性、高波动容忍
- **保守型** (Conservative) — 安全边际、逆向思维
- **中性型** (Neutral) — 兼顾收益与风险
- **组合经理** (PortfolioManager) — 最终拍板，输出交易决策

## 辩论终止条件

- 投资辩论: `max_debate_rounds` 轮后自动终止
- 风控辩论: `max_risk_discuss_rounds` 轮后自动终止
- 所有辩论 history 保留角色前缀（如 `Bull Analyst:`），供前端 `DebateTimeline` 切分对话气泡

## 前端展示

- **SingleAnalysis.vue** — 三阶段纵向滚动布局（分析结论 → 辩论过程 → 最终决策）
- **DebateTimeline.vue** — 正则切分 history 为对话气泡
- **ReportDetail.vue** — 基金专用模块名映射

## 相关文件

- `tradingagents/agents/fund_*` — 基金各角色 analyst
- `tradingagents/graph/fund_graph.py` — LangGraph 辩论流程编排
- `app/services/simple_analysis_service.py` — 分析服务集成
- `openspec/changes/fund-adversarial-debate/` — 变更记录
