## MODIFIED Requirements

### Requirement: Tier1 查询多字段匹配
`_prepare_tier1_reports` SHALL 同时使用 `stock_symbol` 和 `stock_code` 字段匹配 Tier1 报告。SHALL 排除 `stock_symbol='?'` 的无效记录。匹配成功率 SHALL ≥ 80%。

#### Scenario: 双字段匹配
- **WHEN** 查询 000063 中兴通讯的 Tier1 报告
- **THEN** 系统分别在 `stock_symbol` 和 `stock_code` 两个字段中匹配
- **AND** 返回最新的一份已完成报告（按 created_at 降序）

### Requirement: position.industry 字段填充
`get_portfolio_summary()` 返回的 position dict SHALL 包含非空的 `industry` 字段。填充率 SHALL = 100%。

#### Scenario: LLM 分类填充
- **WHEN** `get_portfolio_summary` 构建 position dict
- **THEN** 系统调用 LLM 分类器（classify_batch_with_llm）填充 `industry` 字段
- **AND** 结果缓存到 MongoDB `industry_classification_cache`（30 天 TTL）

### Requirement: 基金穿透数据采集
`_prepare_tier1_reports` 对基金类型 SHALL 构建 `fund_holdings_report`，包含 Top-10 重仓股及其权重。如 AKShare 采集失败，SHALL 标注"数据不可用"，不阻塞管线。

#### Scenario: 基金穿透成功
- **WHEN** 采集 270042 广发纳指 ETF 的持仓数据
- **THEN** `fund_holdings_report` 包含底层 Top-10 重仓股（Apple, Microsoft, Nvidia, ...）及其权重

#### Scenario: 基金穿透失败不阻塞
- **WHEN** AKShare 连接超时 / SSL 错误
- **THEN** 系统记录警告
- **AND** 继续处理下一个基金
- **AND** 不影响最终处方产出
