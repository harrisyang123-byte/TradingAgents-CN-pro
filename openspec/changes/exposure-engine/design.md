# Exposure Engine — 技术设计

## 数据流

```
PortfolioService.get_portfolio_summary()
        │
        ├── positions (stock/fund)
        │       │
        │       ├── stock → 直接纳入敞口矩阵
        │       └── fund  → FundService.get_top_holdings(code)
        │                        │
        │                        └── 拆解为底层股票 × weight
        │
        ▼
ExposureService.compute(user_id)
        │
        ├── 合并：direct_weight + fund_derived_weight = total_exposure
        ├── 行业分类：get_industry(cn_stock_code)
        ├── 集中度计算：top-5 / top-10 / HHI
        └── 标注：stale flag（基金持仓数据 > 45 天）
        │
        ▼
ExposureMatrix {
    stock_exposures: [{code, name, sector, direct_w, fund_w, total_w}]
    sector_concentration: {sector → total_weight}
    top_overlaps: [{stock, holders: [fund_a, fund_b], combined_w}]
    stale_funds: [code, last_update_date]
    summary: "top-5占比 62%, HHI 0.18, 3只标的有双重暴露"
}
```

## 模块设计

### `app/services/exposure_service.py`（新增）

```python
class ExposureService:
    async def compute(user_id: str) -> ExposureMatrix
```

**输入**：
- `portfolio_summary`（已有）
- `fund_top_holdings`（按需获取，带 30 天缓存）

**计算逻辑**：
1. 遍历 positions，按 instrument_type 分流
2. stock → `direct_weight` = position.weight
3. fund → `fund_weight` = position.weight，拆解 top_holdings → `fund_derived_weight` = fund_weight × holding.ratio / 100
4. 同股票合并：total_weight = sum(direct_weight + all fund_derived_weights)
5. 行业分类：调用现有 `get_industry_for_code()` 
6. 集中度：HHI = Σ(weight²)，> 0.15 标记为集中风险

### 集成点

`portfolio_advisor_service.py::_execute_advice()`：
```python
# Before propagate_advice()
exposure = await ExposureService().compute(user_id)
# Format as context → inject into tier1_reports or separate message
```

## 缓存策略

- 基金持仓数据：`fund_data_cache[code]` → 30 天（已有）
- 敞口矩阵结果：`exposure_cache[user_id]` → 1 小时（实时性要求低）
- stale 检测：基金持仓数据超过 45 天 → 矩阵中标记

## 前端展示（后续 PR）

- 敞口矩阵表格（行业 × 权重）
- 重叠检测高亮（同一标的被多只基金持有）
- pending...
