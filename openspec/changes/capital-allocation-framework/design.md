# Design: Capital Allocation Framework + Timing Conditions

## 1. CIO Prompt 新增约束章节

### 资金分配框架

在 CIO prompt 中加入：

```
## 资金分配框架

你的处方必须满足全局资金约束：
- 总资产 ¥{total_assets}，可用现金 ¥{available_cash}
- 单票上限 {max_single}%，单行业上限 {max_industry}%

### 资金来源-去向配对
- 每条 ADD/BUY 的资金必须标注来源（来自现金 / 来自卖出某标的）
- 每条 REDUCE/SELL 释放的资金必须标注去向（回到现金 / 买入某标的）
- 若新增仓位的资金来源是现金，必须确保：Σ 新增金额 ≤ 可用现金
- 若减持资金用于加仓，必须确保：卖出金额 ≥ 买入金额（扣除交易成本）

### 处方新增字段
- `timing`: "immediate"（立即执行）/ "conditional"（条件触发）/ "scheduled"（定期执行）
- `capital_source`: 资金来源描述（如"来自现金"、"来自减仓 000063"）
- `trigger_condition`: 若 timing=conditional，填写触发条件（如"回调至 PE 分位 < 20% 或价格 < ¥35"）
```

## 2. Prescription Schema 扩展

`cio.py` `_parse_prescription()` + `advisor_states.py` `AdviceItem`:
- `timing`: str — immediate / conditional / scheduled
- `capital_source`: str — 资金来源描述
- `trigger_condition`: str — 条件触发描述

## 3. 实现策略

单次 CIO prompt 改造：在现有 prompt 末尾追加"资金分配框架"章节，无需新建文件。
