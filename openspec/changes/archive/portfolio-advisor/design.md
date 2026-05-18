## Context

TG-CN 现有 PaperTrading 模块（`app/routers/paper.py`）已有完整的持仓管理基础设施：MongoDB 集合（paper_accounts/paper_positions/paper_orders/paper_trades）、多市场支持（CN/HK/US）、多货币、T+1 限制、手续费计算、行情获取。

分析引擎（`tradingagents/graph/`）通过 `past_context` 字符串注入历史决策记忆到 Portfolio Manager prompt 中，可用同样机制注入 `portfolio_context`。

改造方向：PaperTrading 从"虚拟资金模拟交易"变为"真实持仓管理"，同时保持现有代码结构。

## Goals / Non-Goals

**Goals:**
- 改造 PaperTrading 为真实持仓 CRUD（单账户、统一人民币计价）
- 后端 REST API 支持 CLI 和 Web 两种录入方式
- 持仓上下文注入到 propagate() 的 Portfolio Manager prompt
- 前端"我的持仓"页面（总览 + 持仓列表 + 手动录入弹窗）

**Non-Goals:**
- 不做组合诊断/主动推荐（Phase 2）
- 不做基金支持（Phase 3）
- 不做券商 API 对接
- 不删除现有 paper_orders/paper_trades 集合（保留交易记录功能）

## Decisions

### D1: 改造 vs 新建模块

**选择**：改造 `app/routers/paper.py`，而非新建 `portfolio.py`。

**理由**：PaperTrading 已有 90% 的基础设施（Position CRUD、行情获取、多市场识别、加权平均成本计算）。改造量远小于新建。

**具体改动**：
- 路由前缀 `/paper` → `/portfolio`（`app/main.py` 中改注册）
- 删除 `INITIAL_CASH_BY_MARKET` 固定初始资金
- `paper_accounts` 从多币种现金 `{CNY, HKD, USD}` 简化为单一 `available_cash`（人民币）+ `total_invested`
- 保留 `_detect_market_and_code()`、`_get_last_price()`、`_calculate_commission()` 等工具函数
- 新增 `POST /portfolio/positions`（添加持仓）、`PUT /portfolio/positions/{code}`（修改）、`DELETE /portfolio/positions/{code}`（删除）
- 新增 `GET /portfolio/summary`（组合总览）
- 改造 `POST /portfolio/order`（用户填价格，非自动市价）

### D2: 单账户 vs 多币种账户

**选择**：单账户单钱包，统一人民币。

**理由**：用户实际只有一笔钱，分成三个币种账户是模拟交易的设计，不符合真实场景。

**实现**：`paper_accounts` 的 `cash` 字段从 `{CNY: x, HKD: y, USD: z}` 改为单一 `available_cash: float`。旧数据兼容：检测到 dict 类型时取 CNY 值。

### D3: 汇率来源

**选择**：AKShare `currency_boc_safe`（中国银行外汇牌价），每日缓存。

**替代方案**：实时汇率 API → 过度设计，日频足够。固定汇率 → 偏差大。

**实现**：`PortfolioService` 中增加 `_get_exchange_rate(currency)` 方法，结果缓存到 MongoDB `exchange_rates` 集合，TTL 24 小时。

### D4: 持仓上下文注入点

**选择**：在 `simple_analysis_service.py` 的 `_execute_analysis_sync()` 中构造 portfolio_context，传给 `propagate()`。

**理由**：这是分析请求的入口，有 `user_id` 可以查持仓。不在引擎层（`trading_graph.py`）做数据库查询，保持引擎层纯净。

**数据流**：
```
AnalysisService._execute_analysis_sync(user_id, request)
  → PortfolioService.get_portfolio_context(user_id)  # 构造字符串
  → trading_graph.propagate(ticker, date, portfolio_context=ctx)
  → Propagator.create_initial_state(... portfolio_context=ctx)
  → state["portfolio_context"] = ctx
  → Portfolio Manager prompt 引用 state["portfolio_context"]
```

### D5: Web 手动录入

**选择**：改造现有"下市场单"弹窗为"添加持仓"弹窗。

**区别**：
- 原来：用户选买/卖 + 填代码/数量，价格自动获取（市价单）
- 现在：用户填代码/数量/价格/日期（手动录入真实持仓）

保留 `side` 字段（buy/sell），buy 增加持仓，sell 减少持仓。

## Risks / Trade-offs

**[R1] 旧数据兼容** → paper_accounts 结构变化需要兼容旧格式。Mitigation：检测 `cash` 字段类型（dict vs float），dict 时取 CNY 值迁移。

**[R2] 行情获取失败** → eastmoney IP 封禁导致 A 股行情不可用。Mitigation：最新价返回 null 时前端显示"--"，不阻塞其他功能。已有 `_RetryAKShare` 重试机制。

**[R3] 汇率获取失败** → BOC API 可能不稳定。Mitigation：缓存 + fallback 到上次成功获取的汇率。

**[R4] Portfolio Manager prompt 过长** → 持仓多时上下文字符串很长。Mitigation：限制最多展示 20 只持仓，超出时按市值排序截断。
