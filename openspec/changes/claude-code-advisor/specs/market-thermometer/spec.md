## ADDED Requirements

### Requirement: 市场温度数据收集
系统 SHALL 在数据收集阶段采集市场情绪数据：北向资金净流入/流出、市场涨跌比(涨家/跌家比例)、涨停/跌停数、融资融券余额变化、个股千股千评评分。

#### Scenario: 正常采集
- **WHEN** 数据收集阶段执行
- **THEN** 系统调用 AKShare 获取北向资金历史流向数据、市场涨跌比数据、融资融券数据
- **AND** 写入 `/tmp/claude_advisor/market_temperature.json`

#### Scenario: 数据采集失败回退
- **WHEN** AKShare API 返回异常或超时
- **THEN** 系统将对应字段标为 "数据不可用"
- **AND** Agent 回归纯基本面判断（不受情绪修正）

### Requirement: 情绪逆向修正
系统 SHALL 将市场温度作为逆向信号修正 Agent 决策：恐慌时置信度加重（immediate），亢奋时置信度降低（conditional/scheduled）。

#### Scenario: 恐慌市场加仓建议
- **WHEN** 某行业基本面 Go + 市场涨跌比 < 25% + 北向连续 5 日净流出
- **THEN** CIO 处方中对该行业标的 timing 倾向 `immediate`
- **AND** reasoning 中标注"逆向：市场恐慌 = 买入窗口"

#### Scenario: 亢奋市场减仓或等待
- **WHEN** 某行业基本面 Go + 市场涨跌比 > 70% + 融资余额环比升高
- **THEN** CIO 处方中对该行业标的 timing 倾向 `conditional` 或 `scheduled`
- **AND** reasoning 中标注"市场亢奋 ≠ 现在该买"
