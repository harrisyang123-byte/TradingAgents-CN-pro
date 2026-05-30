# Tasks: Capital Allocation + Timing Conditions

## Slice 1: CIO Prompt — 资金分配框架

- [x] 在 CIO prompt（初稿+终裁）中加入"资金分配框架"章节
- [x] 要求资金来源-去向配对
- [x] 要求 Σ 新增金额 ≤ 可用现金

## Slice 2: CIO Prompt — 时机条件

- [x] 处方新增 `timing` 字段说明（immediate / conditional / scheduled）
- [x] 处方新增 `capital_source` / `trigger_condition` 字段说明

## Slice 3: Schema 扩展

- [x] `_parse_prescription()` 加入 `timing`、`capital_source`、`trigger_condition`
- [x] `AdviceItem` TypedDict 加入对应字段
- [x] 向后兼容：旧处方无 timing 字段不报错

## Slice 4: 验证

- [x] Import 验证
- [x] 处方解析向后兼容验证
