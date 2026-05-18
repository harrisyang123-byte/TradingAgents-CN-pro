# 基金数据源接入 — PRD

**日期**: 2026-05-18
**复杂度**: L2 标准

---

## O — 概述

### P.A.M 三段论

- **Problem**: instrument_type 已贯通，但 `PortfolioService._get_last_price` 只查股票行情（market_quotes / stock_basic_info / ForeignStockService）。用户添加基金持仓后无法获取净值，导致 `last_price=null`，市值和盈亏无法计算。
- **Approach**: 在 `_get_last_price` 增加 `fund` 分支，调 AKShare `fund_open_fund_info_em` 取最新单位净值，结果缓存在新 collection `fund_nav_cache`，24h TTL。
- **Metrics**:
  - 基金持仓 `last_price` 从 null → 最新单位净值
  - 缓存命中率 > 95%（日级数据 + 24h TTL）
  - 不改动前端和其他模块

---

## A — 分析

### 数据流

```
get_portfolio_summary()
  └→ for each position:
       └→ _get_last_price(code, market)
            ├→ market=="CN" → 查 market_quotes / stock_basic_info (现有)
            ├→ market in ["HK","US"] → ForeignStockService (现有)
            └→ instrument_type=="fund" → _get_fund_nav(code) ← 新增
                 ├→ 查 fund_nav_cache (TTL 24h) → 命中直接返回
                 └→ miss → AKShare fund_open_fund_info_em(symbol=code)
                         → 取最新 '单位净值' → 写入缓存 → 返回
```

### 缓存设计

```
Collection: fund_nav_cache
Document:
{
  "code": "270042",
  "nav": 8.1939,
  "nav_date": "2026-05-15",
  "cached_at": "2026-05-18T21:00:00Z"
}
Index: { code: 1 } unique
过期策略: 北京时间每日 21:00 为净值截止线
  - now_beijing < 今天 21:00 且 cache 是今天 21:00 前抓的 → 有效
  - now_beijing >= 今天 21:00 → 过期，重新抓取
  - 即：对齐基金净值发布时间（~20:00-22:00），最小化发布-刷新差值
```

### 关键决策

- **基金代码即 AKShare symbol**：`270042` 直接传给 `fund_open_fund_info_em(symbol="270042")`，无需转换
- **不检测 market**：场外基金统一按 CN 市场处理（已由 `_detect_market_and_code` 归类为 CN），但 `_get_last_price` 的参数签名需要新增 `instrument_type` 参数
- **缓存策略**：对齐基金净值发布时间（北京时间 21:00 截止），now >= 21:00 即过期重抓。和汇率缓存的 24h TTL 模式不同——这是事件驱动的过期（净值发布事件），而非固定时长

---

## I — 接口

### 改动范围

| 文件 | 改动 |
|------|------|
| `app/services/portfolio_service.py` | `_get_last_price` 签名新增 `instrument_type` 参数；新增 `_get_fund_nav` 方法 |
| `app/services/portfolio_service.py` | `get_portfolio_summary` 调用 `_get_last_price` 时传入 `instrument_type` |

**不改动**：
- 前端：无需改动
- API：无需改动（`get_portfolio_summary` 返回的 `last_price` 自动从 null 变净值）
- Tier 2 引擎：无需改动（已通过 `pos['last_price']` 读取）

### 函数签名变更

```python
# 旧
async def _get_last_price(self, code: str, market: str) -> Optional[float]:
# 新
async def _get_last_price(self, code: str, market: str, instrument_type: str = "stock") -> Optional[float]:
```

---

## S — 场景

### SECURE 六类场景

#### Success
- 用户添加 `270042`（fund）→ `get_portfolio_summary` → `_get_last_price("270042", "CN", "fund")` → AKShare 返回最新净值 8.1939 → `last_price=8.1939` → 市值 = 8.1939 × 100 = 819.39
- 第二次请求（1 小时内）→ 缓存命中 → 直接返回 8.1939，不调 AKShare

#### Edge
- AKShare 超时或返回空 → 返回 `None`（`last_price=null`），前端显示 `--`
- 基金代码在 AKShare 中不存在 → 返回 `None`，不写缓存
- 缓存已过期（>24h）→ 触发重新抓取，成功则更新缓存

#### Constraint
- `_get_fund_nav` 仅在 `instrument_type == "fund"` 时调用
- 缓存 TTL 严格 24h，和汇率缓存同模式
- AKShare 调用需要 try/except 包裹，失败不阻塞返回

#### Unhappy
- AKShare 网络超时 → 返回缓存中的旧净值（即使已过期），降级策略保可用
- 缓存过期且 AKShare 也失败 → 返回 `None`

#### Risk
- 场外基金净值日更，日内无变化 → 24h TTL 合理，无数据陈旧风险
- AKShare 3-5 秒延迟 → 对 `get_portfolio_summary` 首次调用有影响，缓存后无感

#### Edge-case
- `instrument_type` 为 null（旧兼容）→ 默认走 stock 分支，不触发 fund 逻辑
- ETF 场内交易 → instrument_type="etf"，走现有股票行情分支，不触发 fund 逻辑

---

## 自检矩阵

| 检查项 | 状态 |
|--------|------|
| P 有数据 | ✓ AKShare 实测可获取 |
| M 有数字 | ✓ 缓存 TTL 24h |
| 状态转移无孤立 | ✓ 3 态（无缓存/有效缓存/过期缓存）全覆盖 |
| SECURE 六类各 ≥1 | ✓ 见上方 |
| PRD 引用原型 | N/A — 无新页面 |
