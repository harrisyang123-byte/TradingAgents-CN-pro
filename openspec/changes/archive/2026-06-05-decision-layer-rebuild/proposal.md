## PRD

[planning/v3/decision-layer-rebuild_prd.md](../../../planning/v3/decision-layer-rebuild_prd.md)

## Why

当前 CIO 同时承担选股、定权重、输出处方三个职责，上下文超载导致分析浅薄、大量处方无实质调仓。风控是事后检验而非前置拦截。本变更引入并行行业PM、约束传递链、事前风控和 Portfolio Synthesizer，让每个角色专注一件事，以盈利为目标输出可直接执行的处方。

**依赖**：`industry-layer-rebuild`（变更1）必须先完成，本变更依赖 final_weight、vitality_level、StockResearchCache。

## What Changes

- **新增** 并行行业PM：每个Go行业独立spawn激进PM vs 保守PM辩论，在行业配额内选股配仓
- **新增** PM配仓双因子：Tier1评级（方向）× PE分位安全边际（数量），买入区间取两者保守值
- **新增** 分批建仓计划：PM输出 build_strategy + batch_plan（价格+仓位）
- **新增** 风控规则引擎（事前硬拦截）：替代现有事后检验，违规打回对应行业PM重做
- **新增** Risk Director 双角色辩论：悲观RD vs 乐观RA（2轮）→ 风控裁判，整体组合压测
- **新增** Portfolio Synthesizer：替代现有CIO Final，验证约束传递链完整性，处理缺口，汇总输出
- **新增** 约束传递链：宏观total_weight_limit → 行业final_weight → 个股target_weight，层层硬传递
- **修改** CIO：职责收窄，不再选股定权重，"CIO Final"更名为Portfolio Synthesizer
- **修改** `/paper/overview` API：数据源从实时拼接改为读 advice.industry_matrix
- **修改** portfolio_advice 集合：新增 industry_matrix、pm_results、risk_assessment 字段
- **BREAKING** 现有 CIO prompt 和 advisor_graph L4 节点全面重构

## Capabilities

### New Capabilities

- `parallel-industry-pm`: 并行行业PM——每行业独立辩论，激进vs保守，在行业配额内输出个股target_weight+买入区间+分批计划
- `constraint-chain`: 约束传递链——total_weight_limit从宏观层硬传递到行业层再到PM层，Portfolio Synthesizer验证完整性
- `pre-trade-risk-engine`: 事前风控规则引擎——硬拦截违规方案，违规打回对应行业PM重做（最多2次）
- `dual-role-risk-director`: Risk Director双角色压测——悲观vs乐观整体组合压力测试
- `portfolio-synthesizer`: Portfolio Synthesizer——约束链验证+缺口处理+触发补充侦察+汇总输出industry_matrix和最终处方
- `overview-simplify`: /overview简化——数据源从API实时拼接改为读advice.industry_matrix，新增vitality_level/gap/source列

### Modified Capabilities

（无现有 spec 文件需要 delta 更新）

## Impact

**代码**：
- `tradingagents/agents/advisors/industry_pm.py` — 新建行业PM agent（激进/保守角色）
- `tradingagents/agents/advisors/portfolio_synthesizer.py` — 新建Portfolio Synthesizer（替代cio.py）
- `tradingagents/agents/advisors/risk_director.py` — 重构为双角色辩论
- `tradingagents/agents/advisors/cio.py` — 废弃或大幅简化
- `tradingagents/graph/advisor_graph.py` — L3/L4 节点全面重构
- `tradingagents/agents/advisors/advisor_states.py` — 新增 IndustryPMResult、RiskAssessment、PortfolioSynthesisResult
- `app/routers/paper.py` — `/overview` 数据源切换
- `app/services/portfolio_advisor_service.py` — advice 保存新增字段

**数据**：
- `portfolio_advice` 集合：新增 industry_matrix、pm_results、risk_assessment 字段
- `paper_positions` 集合：读取 industry 字段（变更1写入）

**依赖**：
- 变更1：industry-layer-rebuild（final_weight、vitality_level、StockResearchCache）
- 现有：PE分位数据（pe_percentile.py）、buy_signals（compute_buy_signals节点）

<!-- Dialectical Analysis
## 方案对比

方案A（保守）：只收窄CIO职责，不引入PM层
- 优点：改动小
- 缺点：CIO仍然要处理所有行业的个股，上下文超载问题未解决

方案B（本方案）：引入并行行业PM + Portfolio Synthesizer
- 优点：每个PM上下文聚焦（3-5只标的），质量高；约束传递链消除跨层矛盾
- 缺点：改动范围大，advisor_graph L4 全面重构
- 风险对冲：行业PM用asyncio.gather并行，和L1研究员相同模式，有现成参考

最可能失败的点：
- 约束传递链实现有Bug，导致某层未正确接收约束 → 缓解：Portfolio Synthesizer显式验证，不静默失败
- 风控打回死循环 → 缓解：最多2次打回，第3次强制截断
- 行业PM并行token消耗大 → 缓解：每个PM上下文极小（3-5只标的），实际消耗可控
-->
