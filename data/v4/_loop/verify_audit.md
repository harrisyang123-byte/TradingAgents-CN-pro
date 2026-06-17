# RULE-DATA-VERIFIED 红线自动审计报告

生成: 2026-06-17T13:01:55+00:00
扫描: 49 只 stock
- 完全合规: **13** (26.5%)
- 含 fatal 违规: **36**
- 含任意违规: **36**
- fatal 违规计数: 38
- should 违规计数: 5

## 违规明细 (top 15)

### 000063 (1 项)
- [fatal] `evidence`: evidence 空但 verdict 含数字; director schema 要求 evidence min 5 项
  - value: `[] empty`

### 002001 (2 项)
- [fatal] `evidence`: evidence 空但 verdict 含数字; director schema 要求 evidence min 5 项
  - value: `[] empty`
- [should] `valuation_basis.consensus_target`: consensus_target 含数字但无 verified_source(应标卖方报告/共识)
  - value: `卖方均值 ¥28-30 (+25-35% upside)`

### 002050 (1 项)
- [fatal] `evidence`: evidence 空但 verdict 含数字; director schema 要求 evidence min 5 项
  - value: `[] empty`

### 002326 (1 项)
- [fatal] `target_price`: target_price 数字存在但 evidence 数组无对应 verified_source URL/数据源
  - value: `26`

### 002415 (1 项)
- [fatal] `evidence`: evidence 空但 verdict 含数字; director schema 要求 evidence min 5 项
  - value: `[] empty`

### 002517 (1 项)
- [fatal] `evidence`: evidence 空但 verdict 含数字; director schema 要求 evidence min 5 项
  - value: `[] empty`

### 00700 (2 项)
- [fatal] `evidence`: evidence 空但 verdict 含数字; director schema 要求 evidence min 5 项
  - value: `[] empty`
- [should] `valuation_basis.consensus_target`: consensus_target 含数字但无 verified_source(应标卖方报告/共识)
  - value: `HK$711 (+52.53% Strong Buy 46 分析师)`

### 01024 (1 项)
- [fatal] `target_price`: target_price 数字存在但 evidence 数组无对应 verified_source URL/数据源
  - value: `75`

### 01211 (1 项)
- [fatal] `target_price`: target_price 数字存在但 evidence 数组无对应 verified_source URL/数据源
  - value: `115`

### 01810 (1 项)
- [fatal] `evidence`: evidence 空但 verdict 含数字; director schema 要求 evidence min 5 项
  - value: `[] empty`

### 06160 (1 项)
- [fatal] `target_price`: target_price 数字存在但 evidence 数组无对应 verified_source URL/数据源
  - value: `460`

### 06990 (1 项)
- [fatal] `target_price`: target_price 数字存在但 evidence 数组无对应 verified_source URL/数据源
  - value: `520`

### 09988 (2 项)
- [fatal] `evidence`: evidence 空但 verdict 含数字; director schema 要求 evidence min 5 项
  - value: `[] empty`
- [should] `valuation_basis.consensus_target`: consensus_target 含数字但无 verified_source(应标卖方报告/共识)
  - value: `HK$170-200 (大行均值, +30-50%)`

### 300033 (1 项)
- [fatal] `target_price`: target_price 数字存在但 evidence 数组无对应 verified_source URL/数据源
  - value: `255`

### 300308 (2 项)
- [fatal] `evidence`: evidence 空但 verdict 含数字; director schema 要求 evidence min 5 项
  - value: `[] empty`
- [should] `valuation_basis.consensus_target`: consensus_target 含数字但无 verified_source(应标卖方报告/共识)
  - value: `¥1200-1500 (+15-43%, 卖方密集 危险信号)`
