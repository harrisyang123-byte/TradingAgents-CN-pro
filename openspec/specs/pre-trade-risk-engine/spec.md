# pre-trade-risk-engine Specification

## Purpose
TBD - created by archiving change decision-layer-rebuild. Update Purpose after archive.
## Requirements
### Requirement: 事前硬拦截违规方案
系统 SHALL 在PM方案输出后、Risk Director运行前，用规则引擎检查所有约束，违规方案打回对应行业PM重做。

#### Scenario: 单股超限打回重做
- **GIVEN** 科技行业PM方案中中兴通讯 target_weight=35%，超过 max_single_weight=30%
- **WHEN** 风控规则引擎检查
- **THEN** 打回科技行业PM重做，明确标注"中兴通讯超出单股上限30%，需调整"，其他行业PM不受影响

#### Scenario: 打回最多2次后强制截断（Edge Case）
- **GIVEN** 某行业PM连续2次重做后方案仍有小偏差（如单股30.5%，超限0.5%）
- **WHEN** 第3次风控检查
- **THEN** 规则引擎自动截断到边界（30%），不再打回，标注"已自动截断至约束边界"，继续流程

#### Scenario: 多行业独立打回互不影响
- **GIVEN** 科技行业PM违规（单股超限），消费行业PM合规
- **WHEN** 风控检查
- **THEN** 仅科技行业PM被打回重做，消费行业PM结果保留，风控不重跑整个PM层

### Requirement: 四项硬约束规则
系统 SHALL 强制检查四项约束，任一违规即打回。

#### Scenario: 四项约束全部检查
- **WHEN** 风控规则引擎运行
- **THEN** 依次检查：① 单股 target_weight ≤ max_single_weight；② 行业实际权重加总 ≤ final_weight；③ 股票总仓位 ≤ total_weight_limit；④ 现金 ≥ cash_floor

