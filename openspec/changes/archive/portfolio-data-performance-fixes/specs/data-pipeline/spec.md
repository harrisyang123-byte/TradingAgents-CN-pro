## ADDED Requirements

### Requirement: 并行数据管道
35 个持仓的 get_portfolio_summary 响应时间从 ~100s 降至 ~15s 以内。

#### Scenario: 正常加载
- **GIVEN** 用户有 35 个持仓（含 A 股、港股、基金）
- **WHEN** 用户访问 /portfolio/holdings
- **THEN** 系统在 15 秒内完成所有价格/名称/汇率查询并渲染页面

#### Scenario: 单数据源超时
- **GIVEN** AKShare 接口超时
- **WHEN** 系统查询基金净值
- **THEN** 系统在 10 秒超时后回退到缓存值（如有）或 None
- **AND** 页面正常渲染，缺失数据显示 "--"

#### Edge Case: 全部数据源不可用
- **GIVEN** AKShare + yfinance 都不可用
- **WHEN** 系统查询所有持仓
- **THEN** 每个持仓的 last_price 为 None、name 默认为 code
- **AND** 聚合计算（总资产、盈亏）在缺失值时使用 0 替代
