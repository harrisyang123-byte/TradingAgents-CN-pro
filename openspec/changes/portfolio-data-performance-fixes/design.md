# Design: Portfolio Data Performance Fixes

## 1. 并行数据管道

### Module: `app/services/portfolio_service.py`

**`_fetch_position_detail(p: dict) -> dict`**（新增）
- 接收 `paper_positions` 文档，并行查询价格/汇率/名称
- 返回含 `market_value_cny`/`pnl_cny`/`pnl_pct`/`weight` 的详情 dict

```python
async def _fetch_position_detail(self, p: dict) -> dict:
    code, market, currency, instr_type = ...
    # 三个并行子任务
    last_price, exchange_rate, name = await asyncio.gather(
        _safe_price(),   # wait_for 8s
        _safe_rate(),    # wait_for 5s
        _safe_name(),    # wait_for 12s
    )
    # 异常时 name=code, last_price=None, rate=fallback
    return { ... market_value_cny, pnl_cny, pnl_pct, weight: 0.0 ... }
```

**超时策略**：

| 子任务 | 超时 | 回退 |
|--------|------|------|
| price | 8s | None |
| rate  | 5s | 硬编码 fallback (HKD=0.92, USD=7.25) |
| name  | 12s | code 字符串 |

**`get_portfolio_summary()`** — 串行 `for p in positions` → `asyncio.gather`：
```python
position_details = await asyncio.gather(
    *[self._fetch_position_detail(p) for p in positions]
)
total_market_value_cny = sum(p["market_value_cny"] for p in position_details)
```

### AKShare 阻塞兼容
所有 `ak.*()` 调用包装为：
```python
await asyncio.wait_for(asyncio.to_thread(ak.xxx, ...), timeout=10.0)
```

### yfinance 名称回退
```python
clean = str(code).lstrip("0") or "0"
ticker_sym = f"{clean.zfill(4)}.HK"
ticker = await asyncio.to_thread(lambda: yf.Ticker(ticker_sym))
info = await asyncio.to_thread(lambda: ticker.info)
name = info.get("longName") or info.get("shortName")
```

## 2. HK 股数据修复

### Module: `app/services/foreign_stock_service.py`

```python
source_handlers = {
    'yahoo_finance': ('yfinance', self._get_hk_quote_from_yfinance),
    'yfinance': ('yfinance', self._get_hk_quote_from_yfinance),  # 新增别名
    'akshare': ('akshare', self._get_hk_quote_from_akshare),
}
```

`_get_source_priority()` 返回默认 `'yfinance'`，但 handler key 是 `'yahoo_finance'` 导致 yfinance 被过滤。添加 `'yfinance'` 别名解决。

## 3. 行业分类

### Module: `app/routers/paper.py` → `get_portfolio_overview()`

**Step 1: 批量查询 stock_basic_info**
```python
stock_codes = [p["code"] for p in positions if p.get("instrument_type") in ("stock", "etf", None)]
stock_info_map = {}
cursor = db["stock_basic_info"].find({"code": {"$in": stock_codes}})
async for doc in cursor:
    stock_info_map[doc["code"]] = doc
```

**Step 2: 基金名称推断**
```python
kw_map = {
    "纳指|纳斯达克|标普": "海外科技",
    "科创": "科创板",
    "债|债券|信用债": "债券",
    "黄金": "黄金",
    "医药|医疗|生物": "医药健康",
    ...  # 20+ 个关键词映射
}
```

**Step 3: 优先级**
1. `stock_basic_info.industry` / `stock_basic_info.sector`
2. 基金/ETF 名称关键词推断
3. 兜底 "其他"

**新增响应字段**：
```typescript
interface IndustryOverviewRow {
  // ... 已有字段
  position_names: string[]  // 新增
}
```

## 4. 前端 UI 修复

### Module: `frontend/src/views/PaperTrading/index.vue`

**状态**：
```typescript
const showAllPnl = ref(false)
const sortField = ref<string>('weight')
const sortOrder = ref<'asc' | 'desc'>('desc')
```

**计算属性**：
```typescript
const displayPnl = computed(() => {
  if (showAllPnl.value) return sortedByPnl.value  // 全量
  return sortedByPnl.value.slice(0, 10)           // top 10
})

const filteredPositions = computed(() => {
  // market filter + sort
  return [...filtered].sort((a, b) => {
    const aVal = a[sortField.value] ?? 0
    const bVal = b[sortField.value] ?? 0
    return sortOrder.value === 'desc' ? bVal - aVal : aVal - bVal
  })
})
```

**饼图重构**：`topPositions`（top 5）+ `otherWeight`（其余聚合）→ conic-gradient 最多 6 段。

### Module: `frontend/src/views/Portfolio/Overview.vue`

- 持仓标的列：`<span class="pos-name-tag">{{ name }}</span>` + 小字 code
- 弹窗修复：`@click="openAdviceDetail(adv)"` → set `selectedAdvice` + `showDetailDialog = true`

## 5. 验证

- `GET /api/portfolio/summary` 响应 < 15s
- `GET /api/portfolio/overview` 返回 18+ 行业，无"未分类"
- HK 09992 显示名称 + 价格
- Playwright 页面渲染验证
