## ADDED Requirements

### Requirement: 独立 @tool 函数架构
系统 SHALL 使用原版 TradingAgents 的独立 @tool 函数架构，每种数据类型一个独立的 tool 函数。

#### Scenario: Market Analyst 使用独立 tool
- **WHEN** Market Analyst 需要获取股价数据和技术指标
- **THEN** 系统调用 `get_stock_data()` 和 `get_indicators()` 两个独立 tool 函数

#### Scenario: Fundamentals Analyst 使用独立 tool
- **WHEN** Fundamentals Analyst 需要获取财务数据
- **THEN** 系统调用 `get_fundamentals()`, `get_balance_sheet()`, `get_cashflow()`, `get_income_statement()` 四个独立 tool 函数

#### Scenario: News Analyst 使用独立 tool
- **WHEN** News Analyst 需要获取新闻
- **THEN** 系统调用 `get_news()` 和 `get_global_news()` 独立 tool 函数

### Requirement: 删除 unified tool 层
系统 SHALL NOT 包含 `tradingagents/tools/` 目录下的 unified tool 函数。

#### Scenario: unified 工具不存在
- **WHEN** 系统启动
- **THEN** 不存在 `unified_news_tool.py`, `get_stock_fundamentals_unified()`, `get_stock_market_data_unified()` 等 unified 函数

### Requirement: 数据源路由保持
独立 tool 函数 SHALL 通过 `dataflows/interface.py` 的 `route_to_vendor()` 路由到正确的数据源（A股→AKShare，港股/美股→yfinance）。

#### Scenario: A股数据走 AKShare
- **WHEN** tool 函数请求 `600519.SH` 的数据
- **THEN** 通过 `route_to_vendor()` 路由到 AKShare 实现

#### Scenario: 港股数据走 yfinance
- **WHEN** tool 函数请求 `0763.HK` 的数据
- **THEN** 通过 `route_to_vendor()` 路由到 yfinance 实现

### Requirement: Tool binding 方式对齐原版
分析师 agent 的 tool binding SHALL 使用原版的 `_create_tool_nodes()` 方式，由 `TradingAgentsGraph` 统一管理。

#### Scenario: Graph 构建时绑定 tool
- **WHEN** TradingAgentsGraph 初始化
- **THEN** 通过 `_create_tool_nodes()` 为每种分析师创建对应的 ToolNode
