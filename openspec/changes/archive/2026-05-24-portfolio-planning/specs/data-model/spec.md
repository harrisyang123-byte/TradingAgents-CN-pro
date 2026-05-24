## ADDED Requirements

### Requirement: 行业覆盖数据持久化

系统 SHALL 将每次 L1 市场扫描结果持久化到 `industry_coverage` 集合。

#### Scenario: L1 扫描完成后写入覆盖记录
- **GIVEN** 用户触发 L1 市场扫描
- **WHEN** L1 macro_judge 完成行业方向裁决
- **THEN** 系统将每个行业的 lifecycle、go_nogo、confidence、reasoning 写入 `industry_coverage`，status="planned"

#### Scenario: L2-L4 完成后更新覆盖状态
- **GIVEN** L1 已写入 planned 状态记录
- **WHEN** L4 CIO 终裁完成
- **THEN** 系统将对应行业记录 status 更新为 "completed"，填入 advice_id

#### Scenario: Edge Case — 重复分析同一行业
- **GIVEN** industry_coverage 中已存在该用户+行业的 planned 记录
- **WHEN** 新一次 L1 扫描再次选中该行业
- **THEN** 系统 upsert（更新 lifecycle/go_nogo/analyzed_at），不产生重复文档
