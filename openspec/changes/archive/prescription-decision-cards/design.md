# Design: Prescription Decision Cards

## Architecture

```
                        ┌─────────────────┐
                        │  L1/L2/L3 执行   │
                        │  (现有四层图)     │
                        └────────┬────────┘
                                 │
                        ┌────────▼────────┐
                        │ enrich_price_data│  ← NEW: PE 分位计算节点
                        │ (price_context)  │
                        └────────┬────────┘
                                 │
                        ┌────────▼────────┐
                        │      CIO        │  ← 增强: 注入 price_context + 6 字段输出
                        │  (初稿/终裁)     │
                        └────────┬────────┘
                                 │
                        ┌────────▼────────┐
                        │  Risk Director  │  (不变)
                        └────────┬────────┘
                                 │
                        ┌────────▼────────┐
                        │   CIO 终裁      │  ← 增强: 同初稿格式
                        └────────┬────────┘
                                 │
                        ┌────────▼────────┐
                        │   前端卡片流     │  ← NEW: DecisionCard 组件
                        └─────────────────┘
```

## Data Pipeline: PE Percentile

### 新增文件

`tradingagents/dataflows/pe_percentile.py`

```python
def compute_pe_context(code: str, market: str) -> dict:
    """统一接口，市场差异下沉到实现层"""
    # 返回:
    {
        "current_price": float,
        "pe_ttm": float | None,
        "pb": float | None,
        "ma20": float | None,
        "pe_percentile_5y": float | None,  # 0-100, 越低越便宜
        "pe_range_5y": str | None,          # "19.2 - 73.3"
        "pe_percentile_source": str,        # "daily" | "annual" | "unavailable"
        "pe_data_points": int,              # 历史数据点数
        "judgment": str,                    # 一句话估值判断
    }
```

### 三市场实现

| 市场 | 数据源 | PE 获取 | 价格历史 | 数据点数(5y) |
|------|--------|---------|----------|-------------|
| A 股 | BaoStock | `query_history_k_data_plus(fields=peTTM)` | 同上 | ~1200 (每日) |
| 港股 | AKShare | `stock_financial_hk_analysis_indicator_em().EPS_TTM` | `stock_hk_daily()` | ~5-9 (年度) |
| 美股 | yfinance | `ticker.financials.Basic EPS` | `ticker.history(period="5y")` | ~5 (年度) |

### 百分位计算

```python
from scipy.stats import percentileofscore
pe_percentile_5y = percentileofscore(historical_pe, current_pe, kind='rank')
# 0% = 历史最低（最便宜），100% = 历史最高（最贵）
```

### Edge Cases
- 上市 < 1 年 → `pe_percentile_5y: null, source: "insufficient_history"`
- PE 为负 → `pe_percentile_5y: null, source: "negative_earnings"`
- 数据源不可用 → `pe_percentile_5y: null, source: "data_unavailable"`，仅返回 MA20 + 当前 PE

## Graph Change: enrich_price_data Node

`advisor_graph.py` 在 L3 辩论完成后、CIO 调用前插入：

```python
def enrich_price_data_node(state: AdvisorState) -> dict:
    codes = set()
    for pos in state.portfolio_summary.get("positions", []):
        codes.add((pos["code"], _infer_market(pos["code"])))
    for c in state.get("stock_candidates", []):
        codes.add((c["code"], c.get("market", "cn")))
    
    price_context = {}
    for code, market in codes:
        price_context[code] = compute_pe_context(code, market)
    
    return {"price_context": price_context}
```

## CIO Prompt Changes

### 新增数据注入

```python
# 在 CIO prompt 中注入：
price_context = state.get("price_context", {})
for code, ctx in price_context.items():
    prompt += f"""
- {code}: 现价 ¥{ctx['current_price']}, PE(TTM) {ctx['pe_ttm']}, 
  PE 近5年分位 {ctx['pe_percentile_5y']}%, PE 区间 {ctx['pe_range_5y']},
  MA20 ¥{ctx['ma20']}, 判断: {ctx['judgment']}"""
```

### 新增输出字段指令

```
每条处方 JSON 必须包含以下决策卡片字段：

- l1_context: 从宏观裁判报告中提取的行业判断（生命周期、Go/NoGo、关键风险）
- l2_context: 从标的裁判报告中提取的护城河评级和过滤结果
- suggested_price: 基于 PE 分位和 MA20 的安全边际判断（价格区间而非点价）
- max_loss_pct: 逆向验证——如果判断错了，最大亏损百分比是多少
- five_year_view: "5年后这个生意会更好吗？" 具体回答（是/否 + 一句话理由）
- bias_check: 认知偏差检测结果（禀赋效应/近因偏差/锚定效应/讲故事陷阱）
```

## CIO 提取 l1/l2_context 策略

不改动 L1/L2 裁判（保持自由文本输出），CIO 从已有文本中提取：

```
### l1_context / l2_context 提取指令

macro_judge_verdict 和 stock_judge_verdict 中已包含行业和标的的裁判信息。对每条处方：
- l1_context: 在 macro_judge_verdict 中找到该标的所属行业的 Go/NoGo 判断和生命周期阶段，提取为一句话
- l2_context: 在 stock_judge_verdict 中找到该标的的护城河评级和过滤结果，提取为一句话
- 若裁判报告未覆盖该标的/行业 → l1_context 标注 "未覆盖"，l2_context 标注 "经由 L2 Scout 筛选"
```

## State Changes

`AdvisorState` 新增:

```python
price_context: dict  # {code: PEContext}, enrich_price_data 节点产出
```

## Frontend

### 新组件: `DecisionCard.vue`

每条卡片结构：

```
┌─────────────────────────────────────────┐
│  🔴 URGENT  │  加仓 · 贵州茅台 600519    │
│             │  当前 12% → 目标 18%        │
├─────────────────────────────────────────┤
│  💡 白酒行业稳步成长期，Go               │  ← l1_context
│  🛡️ 宽护城河，通过四层过滤               │  ← l2_context
├─────────────────────────────────────────┤
│  ¥1,377  │  PE 19.2 (历史0分位)          │  ← suggested_price
│          │  ████░░░░░░ 极低              │  ← PE percentile bar  
│          │  ¥1,300-1,450 具备安全边际     │
├─────────────────────────────────────────┤
│  ⚠️ 最大亏损 -15%   │  5年视角 ✓        │  ← risk row
│  📋 认知偏差: 无显著偏差                  │
├─────────────────────────────────────────┤
│  📝 {reasoning}                         │  ← existing reasoning
└─────────────────────────────────────────┘
```

### 布局

- PaperTrading/index.vue 的 `el-table` 替换为纵向卡片流
- 按 priority (urgent → important → optional) 排序
- 卡片默认收起 L1/L2 context，点击展开
- PE 分位用进度条可视化

### 排序规则

CIO 在每条处方中输出 `priority: "urgent" | "important" | "optional"`：
- **urgent**：需要立即关注（减仓/清仓信号、重大风险暴露）
- **important**：应该执行（加仓好机会、新增优质标的）
- **optional**：可以关注（观察列表、小仓位试探）

## Files Changed

| # | File | Action |
|---|------|--------|
| 1 | `tradingagents/dataflows/pe_percentile.py` | New |
| 2 | `tradingagents/graph/advisor_graph.py` | Modify (add enrich_price_data node) |
| 3 | `tradingagents/agents/advisors/advisor_states.py` | Modify (add price_context) |
| 4 | `tradingagents/agents/advisors/cio.py` | Modify (prompt + parse) |
| 5 | `app/services/portfolio_advisor_service.py` | Modify (save new fields) |
| 6 | `frontend/src/api/paper.ts` | Modify (types) |
| 7 | `frontend/src/components/Analysis/DecisionCard.vue` | New |
| 8 | `frontend/src/views/PaperTrading/index.vue` | Modify (table → cards) |
