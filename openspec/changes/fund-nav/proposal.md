## Why

`PortfolioService._get_last_price` 只查股票行情（market_quotes / stock_basic_info / ForeignStockService），用户添加基金持仓后无法获取净值，导致 `last_price=null`，市值和盈亏无法计算。`instrument_type` 字段已贯通，但 fund 分支缺失数据源。

## What Changes

- `_get_last_price` 签名新增 `instrument_type` 参数（默认 `"stock"`，向后兼容）
- 新增 `_get_fund_nav(code)` 方法：调 AKShare `fund_open_fund_info_em` 取最新单位净值
- 新 MongoDB collection `fund_nav_cache`，24h TTL 缓存（和汇率缓存同模式）
- `get_portfolio_summary` 调用 `_get_last_price` 时传入 `instrument_type`

## Capabilities

### New Capabilities

- `fund-nav`: 从 AKShare 获取场外基金单位净值作为 last_price，带 24h MongoDB 缓存，降级策略保可用

### Modified Capabilities

<!-- No existing specs to modify -->

## Impact

- `app/services/portfolio_service.py` — 唯一改动文件
- 前端：无改动（`last_price` 自动从 null 变为净值）
- API：无改动（`get_portfolio_summary` 返回格式不变）
- 依赖：AKShare `fund_open_fund_info_em`（已在 PRD 中验证可用）
