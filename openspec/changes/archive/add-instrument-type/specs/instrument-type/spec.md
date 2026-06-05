## ADDED Requirements

### Requirement: 持仓标的支持分类字段
系统 SHALL 为每笔持仓记录标的分类（instrument_type），支持 stock / etf / fund / bond / other 五种类型，端到端贯通前端 → API → MongoDB → PortfolioService → Tier 2 引擎。

#### Scenario: 添加持仓时选择分类
- **WHEN** 用户在前端添加持仓，输入代码 "600519"，系统自动识别为 "stock"
- **THEN** 前端展示分类为"股票"，用户可以手动改为其他分类，提交后 MongoDB paper_positions 记录 instrument_type = "stock"

#### Scenario: 添加 ETF 自动识别
- **WHEN** 用户输入代码 "510050"，触发自动识别规则
- **THEN** system 自动设置 instrument_type = "etf"，前端展示"ETF"标签

#### Scenario: 编辑已有持仓修改分类
- **WHEN** 用户编辑一笔旧持仓（无 instrument_type），选择分类为"基金"
- **THEN** MongoDB 更新 instrument_type = "fund"，前端刷新后显示"基金"标签

#### Scenario: PortfolioService 返回分类
- **WHEN** 调用 `get_portfolio_summary(user_id)`
- **THEN** 每笔持仓对象 SHALL 包含 `instrument_type` 字段，其值为 stock/etf/fund/bond/other 之一；旧文档无此字段时返回 "stock"

#### Scenario: Tier 2 引擎读取分类
- **WHEN** AdvisorGraph.propagate_advice() 处理一份 instrument_type = "etf" 的持仓
- **THEN** Analyst/Strategist/Scout/CIO 的 prompt 中该标的显示为 "etf" 而非退化到 "stock"

#### Scenario: 旧数据兼容
- **WHEN** MongoDB 中某 paper_positions 文档未包含 instrument_type 字段
- **THEN** 前端表格显示"未分类"标签，PortfolioService 返回 "stock"，系统行为不变

### Requirement: 自动识别标的分类
系统 SHALL 根据股票代码模式自动推断 instrument_type，用户可覆盖自动结果。

#### Scenario: A 股 ETF 识别
- **WHEN** 用户输入以 159/510/511/512/513/515/516/517/518/588/560/561/562/563 开头的 A 股代码
- **THEN** 系统自动设置 instrument_type = "etf"

#### Scenario: A 股普通股票识别
- **WHEN** 用户输入以 60/00/30/68 开头但不符合 ETF 规则的 A 股代码
- **THEN** 系统自动设置 instrument_type = "stock"

#### Scenario: 港股/美股默认分类
- **WHEN** 用户输入港股或美股代码（市场=HK/US）
- **THEN** 系统自动设置 instrument_type = "stock"，用户可手动修改

#### Scenario: 用户覆盖自动识别
- **WHEN** 自动识别结果为 "stock" 但用户手动改为 "fund"
- **THEN** 系统以用户选择为准，提交后存储 instrument_type = "fund"
