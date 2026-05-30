## ADDED Requirements

### Requirement: HK 股名称和价格
港股持仓（09992、01810 等）正确显示中文/英文名称和最新价格。

#### Scenario: HK 股名称查询
- **GIVEN** 用户持有 09992（泡泡玛特）和 01810（小米）
- **WHEN** 系统调用 get_portfolio_summary
- **THEN** 09992 显示 "Pop Mart International Group Limited" 或 "泡泡玛特"
- **AND** 01810 显示 "Xiaomi Corporation" 或 "小米集团"

#### Scenario: HK 股价格来自 yfinance
- **GIVEN** akshare HK 行情接口不可用
- **WHEN** 系统查询港股价格
- **THEN** 降级到 yfinance 查询，返回非空价格

#### Edge Case: HK 股未在 yfinance 数据源注册
- **GIVEN** 港股代码格式特殊（如 09992 需要转为 9992.HK）
- **WHEN** 系统查询价格
- **THEN** 正确转换代码格式（strip 前导零，pad to 4，加 .HK 后缀）
