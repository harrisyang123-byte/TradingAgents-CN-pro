# parallel-industry-pm Specification

## Purpose
TBD - created by archiving change decision-layer-rebuild. Update Purpose after archive.
## Requirements
### Requirement: 每行业独立并行PM辩论
系统 SHALL 为每个 Go 行业独立 spawn 一个 PM 辩论（激进PM vs 保守PM），所有行业并行执行。

#### Scenario: 多行业并行PM运行
- **GIVEN** 行业层输出5个Go行业，各有 final_weight
- **WHEN** PM层启动
- **THEN** 5个行业PM同时运行，每个PM只接收本行业的候选标的（3-5只），总耗时约等于最慢单行业

#### Scenario: 单行业PM失败不影响其他行业（Edge Case）
- **GIVEN** 科技行业PM因LLM超时失败
- **WHEN** 并行执行
- **THEN** 其他行业PM正常完成，科技行业标记为配仓失败，对应配额全部留现金，不阻断整体流程

### Requirement: 激进vs保守三维辩论
系统 SHALL 让激进PM和保守PM在三个维度辩论：仓位集中度、行业配额使用率、建仓时机。

#### Scenario: 三维辩论输出完整配仓方案
- **WHEN** 行业PM辩论完成
- **THEN** 输出包含：每只标的 target_weight、entry_price_range、build_strategy（immediate/batch/conditional）、batch_plan（分批建仓价格+仓位）

#### Scenario: 配仓双因子约束
- **GIVEN** 中兴通讯 Tier1评级=买入，PE分位=25%（历史低位）
- **WHEN** PM分配 target_weight
- **THEN** 评级决定配置方向（配），PE分位低决定多配，target_weight 在同行业中相对较高

#### Scenario: 买入区间取保守值（Edge Case）
- **GIVEN** Tier1目标价区间 42-48元，PE历史30分位对应区间 40-44元
- **WHEN** PM计算 entry_price_range
- **THEN** 取交集 42-44元；若无交集，取两者中更低的区间，并标注"Tier1与PE分位区间有分歧，取保守值"

