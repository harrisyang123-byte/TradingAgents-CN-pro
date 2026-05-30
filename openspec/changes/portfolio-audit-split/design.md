# Design: Portfolio Audit Split

## 1. Portfolio Audit Service（新增）

### Module: `app/services/portfolio_audit_service.py`

对每只持仓做确定性计算，产出健康诊断：

```python
def audit_position(pos: dict) -> dict:
    """对单只持仓做健康体检"""
    pnl_pct = pos.get("pnl_pct", 0)
    weight = pos.get("weight", 0)
    
    # 健康分
    if pnl_pct <= -20:
        health = "float"       # 深度套牢
    elif pnl_pct < -5:
        health = "pare"        # 需要减仓
    elif pnl_pct < 10:
        health = "ok"          # 正常
    else:
        health = "good"        # 盈利
    
    # 持有天数（如有 buy_date）
    # ...
    
    return {
        "code": pos["code"],
        "name": pos.get("name", ""),
        "health": health,
        "pnl_pct": round(pnl_pct, 1),
        "pnl_cny": round(pos.get("pnl_cny", 0), 0),
        "avg_cost": pos.get("avg_cost", 0),
        "last_price": pos.get("last_price", 0),
        "cost_ratio": round(pnl_pct / 100 * weight, 2) if weight else 0,
        # cost_ratio = 该持仓对组合总收益的贡献：负值意味着拖累组合多少百分点
    }
```

## 2. CIO Prompt 改造

### position 摘要增强（每只 ≤ 80 字）

```
- 000063 中兴通讯 (stock): 仓位 12.5%, 市值 ¥45,000
  成本 ¥38.50 → 现价 ¥36.06, 亏损 -6.3% (¥-2,930), 持有 180 天
  健康分: pare (建议减仓)
```

### 新增 存量 vs 增量 分区

在 system prompt 中加入：

```
## 存量诊断（现有持仓）

对每只持仓，基于成本/盈亏/持有时间，判定：

- **持有 (hold)**: 成本区间合理、权重正常、基本面无恶化
- **加仓 (add)**: 亏损但有基本面支撑、当前仓位低于目标
- **减仓 (reduce/pare)**: 亏损 >10% 且基本面恶化、或盈利 >30% 有止盈需求
- **清仓 (exit)**: 亏损 >20% 且无基本面支撑、或行业逻辑已破

## 增量探索（新机会）

- 候选标的 + 入场条件 + 替代哪只现有持仓
- 如果"卖掉 A 换 B"，必须在 prescription 中配对输出
```

### prescription item 加字段

```json
{
  "code": "...",
  "name": "...",
  "action": "reduce",
  "split_type": "存量体检",        // 新增
  "avg_cost": 38.50,               // 新增
  "pnl_pct": -6.3,                 // 新增
  "cost_context": "成本 ¥38.50, 浮亏 6.3%, 持有 180 天",  // 新增
  ...
}
```

## 3. Strategist Prompt 改造

position 列表从 `weight + market_value` 扩展为 `weight + cost + pnl + market_value`，使策略师在评估集中度风险时感知持仓盈亏状态。

## 4. AdvisorGraph 集成

`propagate_advice()` 调用 audit 服务，将 `audit_results` 注入初始 state：

```python
from app.services.portfolio_audit_service import audit_positions
audit_results = audit_positions(portfolio_summary["positions"])
# ...
init_state["audit_results"] = audit_results
```

## 5. 验证

- CIO prompt 包含 cost/P&L/buy_date
- 处方 JSON 包含 `split_type`、`avg_cost`、`pnl_pct` 字段
- audit 服务计算正确（-20% = float, -6.3% = pare）
