## ADDED Requirements

### Requirement: 行业分类
行业覆盖矩阵中每个持仓正确归类到对应行业，而非全部"未分类"。

#### Scenario: Stock/ETF 从 stock_basic_info 获取行业
- **GIVEN** 持仓中有 A 股 stock 和 ETF
- **WHEN** 系统计算行业覆盖矩阵
- **THEN** 从 stock_basic_info 批量查询 industry 字段
- **AND** 正确分组到对应行业（如"半导体"、"医药健康"）

#### Scenario: 基金从名称推断行业
- **GIVEN** 持仓中有基金（instrument_type == "fund"）
- **WHEN** 系统无法从 stock_basic_info 获取行业
- **THEN** 从基金名称关键词推断行业
- **AND** "易方达稳健收益债B" → "债券"、"广发创业板ETF联接A" → "创业板"

#### Edge Case: 无法分类的持仓
- **GIVEN** 持仓名称不含任何已知行业关键词且非 stock/etf
- **WHEN** 系统计算行业覆盖矩阵
- **THEN** 归入"其他"分类

#### Scenario: 覆盖矩阵显示中文名称
- **GIVEN** 行业覆盖矩阵展示
- **WHEN** 用户查看"持仓标的"列
- **THEN** 显示中文名称标签（最多前 3 个）+ 代码小字
