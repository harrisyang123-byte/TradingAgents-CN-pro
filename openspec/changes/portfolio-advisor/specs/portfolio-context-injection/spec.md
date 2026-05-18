## ADDED Requirements

### Requirement: 分析引擎注入持仓上下文
系统 SHALL 在执行股票分析时，将用户当前持仓信息注入到 Portfolio Manager 的决策 prompt 中。

#### Scenario: 分析持仓中的股票
- **WHEN** 用户对持仓中的 600519 发起分析，且用户持有 1000 股、仓位占比 60%
- **THEN** Portfolio Manager 的 prompt 中包含用户持仓上下文（总投入、可用现金、所有持仓明细、仓位占比、盈亏情况），最终决策考虑仓位因素

#### Scenario: 分析非持仓股票
- **WHEN** 用户分析一只不在持仓中的股票
- **THEN** Portfolio Manager 的 prompt 中仍包含用户整体持仓概况（帮助判断是否有资金/仓位空间买入），但标注"用户未持有该标的"

#### Scenario: 用户无持仓时分析
- **WHEN** 用户未录入任何持仓，发起股票分析
- **THEN** portfolio_context 为空字符串，分析引擎行为与改造前一致

#### Scenario: 持仓上下文长度限制
- **WHEN** 用户持有超过 20 只股票
- **THEN** 系统按市值排序，只展示前 20 只持仓的详情，尾部标注"还有 N 只持仓未展示"
