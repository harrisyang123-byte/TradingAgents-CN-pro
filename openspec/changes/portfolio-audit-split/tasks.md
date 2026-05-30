# Tasks: Portfolio Audit Split

## Slice 1: Portfolio Audit Service

- [x] 新建 `app/services/portfolio_audit_service.py`，实现 `audit_position()` + `audit_positions()`
- [x] 健康分：float (<=-20%), pare (-5~-20%), ok (-5~10%), good (>10%)
- [x] 返回 cost_ratio（该持仓对组合总收益的贡献）

## Slice 2: CIO Prompt 改造

- [x] position 摘要加入 `avg_cost`、`last_price`、`pnl_pct`、`pnl_cny`、持有天数
- [x] system prompt 加入 存量诊断 + 增量探索 分区说明
- [x] prescription item 加 `split_type`、`avg_cost`、`pnl_pct`、`cost_context` 字段
- [x] `_parse_prescription()` 容错：新字段缺失不报错

## Slice 3: Strategist Prompt 改造

- [x] position 摘要加入 cost/P&L 数据

## Slice 4: AdvisorGraph 集成

- [x] `propagate_advice()` 调用 `audit_positions()` 
- [x] `audit_results` 注入 init_state

## Slice 5: AdvisorStates + AdviceItem

- [x] `AdviceItem` TypedDict 加 `split_type`、`avg_cost`、`pnl_pct` 字段

## Slice 6: 验证

- [x] Import 验证
- [x] audit_position 单元逻辑验证
