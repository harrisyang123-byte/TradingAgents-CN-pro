## Context

`PortfolioService._get_last_price` 当前只处理 stock 行情（CN 市场查 market_quotes/stock_basic_info，HK/US 查 ForeignStockService）。`instrument_type` 字段已在全链路贯通（前端→API→DB→PortfolioService→Tier 2），但 `_get_last_price` 尚未根据 `instrument_type` 分支路由——fund 类型持仓仍然走 stock 分支，查不到净值返回 `None`。

AKShare `fund_open_fund_info_em` 已实测可用（测例：270042 广发纳指100ETF联接），返回包含单位净值、累计净值的时间序列。场外基金净值日更，日内不变。

## Goals / Non-Goals

**Goals:**
- fund 类型持仓通过 AKShare 获取最新单位净值作为 `last_price`
- 24h MongoDB 缓存，避免重复调用 AKShare（日级数据，缓存一天合理）
- 降级策略：AKShare 失败时返回缓存旧值（即使过期）→ 无缓存时返回 `None`
- 和现有汇率缓存同模式，代码风格一致

**Non-Goals:**
- 不接入基金基本信息（`fund_individual_basic_info_xq`）— 后续需要时再加
- 不接入基金持仓组合（`fund_portfolio_hold_em`）— 后续需要时再加
- 不新增前端页面或 API 端点
- 不处理 ETF 场内交易（ETF instrument_type 走 stock 分支）

## Decisions

### Decision 1: `_get_last_price` 新增 `instrument_type` 参数而非新建独立方法

**选择**：在现有 `_get_last_price` 签名加 `instrument_type: str = "stock"`，方法体内加 `if instrument_type == "fund"` 分支。

**替代方案**：在 `get_portfolio_summary` 循环中判断 `instrument_type`，分别调用 `_get_last_price` 和 `_get_fund_nav`。

**理由**：`_get_last_price` 的职责是"根据类型获取最新价格"，fund 只是其中一种类型。把分支放在方法内部保持调用方简洁，未来加 bond 类型也只需加一个分支。默认值 `"stock"` 保证向后兼容（存量调用方无需改动）。

### Decision 2: 缓存过期对准北京时间每日 21:00（基金净值发布时间）

**选择**：`now_beijing >= 今天 21:00` 视为过期，而非简单 `cached_at + 24h`。

**替代方案**：和汇率缓存一样的固定 24h TTL。早上 9:00 抓取 → 次日 9:00 过期，但前晚 20:00 净值已发布，用户看到的是 ~13h 前的旧值。

**理由**：场外基金净值每天 20:00-22:00 发布。对齐 21:00 截止线，净值一发布就能在下次请求中抓到。代码逻辑：`now_beijing < 21:00 且 cache 在今日 21:00 前 → 有效`，否则重抓。

### Decision 3: 降级策略两层回退

**选择**：AKShare 失败 → 返回缓存（即使过期）→ 无缓存则返回 `None`。

**理由**：和汇率缓存降级策略一致。场外基金净值日更，过期一两天的旧净值仍有参考价值，好过显示 `null`。

### Decision 4: 净值校验守卫

**选择**：写入缓存前检查 `nav > 0`，AKShare 返回 0 或 NaN 时不写缓存。

**理由**：防止异常值污染缓存。

### Decision 5: 节假日/周末去重

**选择**：AKShare 返回的 `nav_date` 和缓存中的 `nav_date` 相同时，只更新 `cached_at`（延长过期时间），不覆盖 `nav` 值。

**理由**：非交易日 AKShare 返回的仍是上一交易日净值。重写 nav 无意义，只更新 `cached_at` 即可让缓存继续有效到下一个 21:00 截止线，同时避免无效写库。

### Decision 6: 多基金串行调用（已知限制，暂不优化）

**选择**：首次全部 miss 时串行调用 AKShare，不做并行化。

**理由**：日级数据 + 缓存后无感知，10 只基金 × 3~5s ≈ 30~50s 在首次请求可接受。代码中留 TODO 注释标记未来优化点（`asyncio.gather`）。

## Risks / Trade-offs

- [AKShare 3-5s 延迟] → 首次请求有感知，缓存后无影响；try/except 包裹不阻塞 `get_portfolio_summary`
- [基金代码在 AKShare 不存在] → 返回 `None`，不写缓存；下次请求重试
- [单位净值字段名变动] → 取 `单位净值` 列，AKShare 接口稳定；若变动则 fallback 到 `None`
- [多基金串行阻塞] → 极端场景 ~50s，但仅首次触发；留 TODO 标记并行优化
- [节假日重复抓取] → nav_date 去重后只更新 cached_at，无浪费

## Open Questions

<!-- None — PRD 已覆盖所有决策点 -->
