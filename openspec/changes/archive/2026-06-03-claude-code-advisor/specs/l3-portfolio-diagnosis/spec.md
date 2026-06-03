## MODIFIED Requirements

### Requirement: L3 分析师
分析师 SHALL 逐只评估每只持仓的安全边际。评估 SHALL 引用 Tier1 报告评级 + PE 分位数据。如果 Tier1 报告不可用，SHALL 标注"无深度分析报告"。如果同一标的有多份 Tier1 报告且方向矛盾，SHALL 标注矛盾。

#### Scenario: 有 Tier1 报告的安全边际评估
- **WHEN** 分析师评估有 Tier1 报告的持仓标的
- **THEN** 输出 SHALL 包含 Tier1 评级引用、PE 分位值、对该标的的操作建议方向
- **AND** 如果 PE 分位 > 85% 且 Tier1 建议买入，SHALL 标注此矛盾

#### Scenario: 无 Tier1 报告的安全边际评估
- **WHEN** 分析师评估无 Tier1 报告的持仓标的
- **THEN** 输出 SHALL 标注"无深度分析报告"
- **AND** 仍基于 PE 分位和基本面数据给出建议方向

### Requirement: L3 策略师诊断
策略师 SHALL 输出组合健康度诊断报告，不输出操作建议。诊断 SHALL 包含：行业集中度（含超标预警）、分析师推荐的一致性风险、基金穿透后隐形暴露汇总、共性的数据质量担忧。策略师 SHALL 读取分析师的输出后再发言。

#### Scenario: 一致性风险检测
- **WHEN** 分析师建议 ≥3 只持仓的加仓方向属于同一行业
- **THEN** 策略师 SHALL 标注"集中度风险：X 只加仓全在 XX 行业，合计目标仓位将达到 XX%"
- **AND** 标注是否接近或超过单行业红线

#### Scenario: 隐形暴露汇总
- **WHEN** 敞口矩阵显示基金穿透后的底层标的合计 > 5% 但 direct_weight = 0%
- **THEN** 策略师 SHALL 标注 "你通过基金间接持有 XX 超过 5%，但直接持仓显示为 0%"
