# L3 Agent 验收规格

## 1. Analyst Agent

### 工具能力
- [x] `read_tier1_report(code)` 返回 Tier1 报告评级、摘要、基金特有字段
- [x] `get_position_audit(code)` 返回持仓体检数据
- [x] 工具调用上限 3 次
- [x] 达上限后强制总结

### 输出
- [x] analyst_assessment 包含每只持仓的安全边际评估
- [x] 区分个股和基金的不同评估维度

## 2. Strategist Agent

### 工具能力
- [x] `compute_sector_concentration()` 返回每个行业的权重、标的数、是否突破红线
- [x] `compute_top_holdings_risk(n)` 返回前 N 大持仓合计权重 + 回撤场景估算
- [x] `compute_cash_drag()` 返回现金占比、机会成本

### 输出
- [x] strategist_assessment 包含集中度分析、逆向思维、认知偏差检测、组合缺口识别
