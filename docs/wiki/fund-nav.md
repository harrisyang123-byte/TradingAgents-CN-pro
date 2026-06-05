# 基金净值获取（fund-nav）

**变更**: fund-nav
**日期**: 2026-06-05

## 概述

`PortfolioService._get_last_price` 新增 `instrument_type` 路由，`fund` 类型持仓通过 AKShare `fund_open_fund_info_em` 获取单位净值，MongoDB 缓存对齐北京时间每日 21:00 过期。

## 实现要点

- **`_get_last_price(code, market, instrument_type="stock")`**：新增第三参数，`fund` 时调 `_get_fund_nav(code)` 直接返回，ETF/stock 走原有分支
- **`_get_fund_nav(code)`**：查 `fund_nav_cache` → 有效缓存直接返回 → 过期/无缓存调 AKShare → 写入缓存（upsert）
- **`get_portfolio_summary`**：调用处改为 `_get_last_price(code, market, p.get("instrument_type", "stock"))`

## 关键决策

**缓存过期对准北京时间 21:00**：场外基金净值 20:00-22:00 发布，固定 24h TTL 会导致净值发布后仍用旧值长达数小时。对齐 21:00 截止线，净值一发布下次请求即可抓到。

**两层降级**：AKShare 异常时返回缓存旧值（即使过期），无缓存时返回 `None`。保证服务不中断，旧值比 `None` 更有用。

**分支加在 `_get_last_price` 内**：保持调用方简洁，未来加 bond 等类型只需加一个 `elif` 分支。

## 注意事项

- AKShare `fund_open_fund_info_em` 返回时间序列，取最新行的 `单位净值` 列
- `nav > 0` 校验：0 或 NaN 不写缓存直接返回 `None`
- ETF 场内交易（`instrument_type == "etf"`）不走此分支，仍走 stock 行情
- `nav_date` 去重：节假日/周末 AKShare 返回旧日期时只更新 `cached_at`，不覆盖 nav
