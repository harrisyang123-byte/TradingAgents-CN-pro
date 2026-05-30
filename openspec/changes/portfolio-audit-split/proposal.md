# Proposal: Portfolio Audit Split — 存量体检 vs 增量探索

## Why

当前 CIO 把所有持仓混在一起出建议，不区分"现有持仓怎么调"和"要不要买新东西"。
但这是两类本质不同的问题：
- **存量体检**：持有/加仓/减仓/清仓——需与现有成本、盈亏状态挂钩
- **增量探索**：新进入机会——需回答"为什么现在"和"替代谁"

数据已经全部在 `portfolio_summary` 里（avg_cost, pnl_cny, pnl_pct, buy_date），只是 Agent prompt 没暴露。

## Design Overview

### 核心变更

```
Before: CIO 看到 weight + market_value → 统一出建议
After:  CIO 看到 成本 + P&L + 持有时间 + weight → 拆分 存量诊断 + 增量探索
```

### 变更范围

1. **CIO prompt** (`cio.py`)：position 摘要加入 cost/P&L/buy_date，新增 存量/增量 分区
2. **Strategist prompt** (`strategist.py`)：position 摘要加入 cost/P&L
3. **Prescription schema** (`advisor_states.py`)：AdviceItem 加 `avg_cost`、`pnl_pct` 字段
4. **Portfolio Audit Service** (`portfolio_audit_service.py`)：轻量预处理器，为每只持仓打健康分（float/pare/ok/good）

### 不涉及

- 新 Agent 节点（存量/增量只是 CIO prompt 分区，不是独立 Agent）
- 前端改动（prescription 已有 DecisionCard 渲染）
- MongoDB schema 变更

<!-- Dialectical Analysis -->
**方案对比**：
- 方案 A（Prompt only）：只改 prompt，不建新服务。优点：零文件新增。缺点：LLM 可能算错 P&L%。
- 方案 B（Preprocessor + Prompt）：新增轻量 audit 服务，预先计算每只持仓的健康分和诊断，CIO prompt 引用。优点：确定性计算 + LLM 发挥。缺点：多一个文件。

选择方案 B，理由：
1. P&L% 和持有天数等数学计算不适合让 LLM 做
2. 健康分（float/pare/ok/good）作为确定性标签，CIO 只需解读
3. 预处理结果可复用于前端展示

**风险对冲**：
- 健康分标准主观：阈值（亏损 >20% = float）暂时硬编码，后续可配置化
- Prompt 可能过于冗长：控制 position 摘要每只 ≤ 80 字
