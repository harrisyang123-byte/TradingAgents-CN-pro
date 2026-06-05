## 1. Fund NAV cache + fetch

- [x] 1.1 新增 `_get_fund_nav(self, code: str)` 方法：查 `fund_nav_cache` → 缓存有效（now_beijing < 今天 21:00 且 cache 是今天 21:00 前所抓）直接返回 → 过期/无缓存则调 AKShare `fund_open_fund_info_em` → 取 `单位净值` 列最新值 → 写入缓存（upsert）→ 返回 nav
- [x] 1.2 净值校验：写入缓存前检查 `nav > 0`，0 或 NaN 不写缓存返回 `None`
- [x] 1.3 nav_date 去重：AKShare 返回的 `nav_date` 和缓存相同时只更新 `cached_at`（节假日/周末场景），不覆盖 nav
- [x] 1.4 实现降级策略：AKShare 异常时返回缓存旧值（即使过期），无缓存返回 `None`，warning 级别日志
- [x] 1.5 留 TODO 注释标记多基金并行优化点（`asyncio.gather`）

## 2. Route fund type in _get_last_price

- [x] 2.1 `_get_last_price` 签名新增 `instrument_type: str = "stock"` 参数
- [x] 2.2 方法体内：`instrument_type == "fund"` 时调用 `_get_fund_nav(code)` 并直接返回（fund 不区分 market）
- [x] 2.3 `get_portfolio_summary` 中 `_get_last_price(code, market)` 调用改为 `_get_last_price(code, market, p.get("instrument_type", "stock"))`

## 3. Verify

- [x] 3.1 用基金代码（如 270042）创建持仓 → 调用 `get_portfolio_summary` → 确认 `last_price` 为净值非 null
- [x] 3.2 确认缓存写入 `fund_nav_cache` collection，二次请求命中缓存
- [x] 3.3 确认 stock/etf 类型持仓 `last_price` 不受影响
