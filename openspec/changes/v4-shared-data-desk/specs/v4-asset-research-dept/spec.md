# v4-asset-research-dept Specification (delta)

## Purpose
本 delta 修订 `v4-asset-research-dept` 的**取数职责与降级策略**：把「各 Agent 自行联网 / collect best-effort 缺则静默标 missing」改为「辩论 Agent 维持 Read-only 只消费 `v4-data-desk` 输入包；缺数据由 data-desk 联网兜底，取不到才 missing 且显式提示、不静默降级」。其余（固定 3 轮辩论、总监拍板、逐类独立落盘、零持仓可触发）不变，仍以 `v4-layered-deep-research` 中的本能力规格为准。

## MODIFIED Requirements

### Requirement: 单大类独立多维分析
系统 SHALL 对单个大类独立运行分析部门，输入覆盖该资产相关的多维信息：宏观（利率/通胀/货币政策/经济周期）、微观/基本面（估值与供需）、舆情与资金面、政策与地缘政治。多维数据 SHALL 由 `v4-data-desk` 取回（档 A 全局宏观共读 + 档 B 本大类深取）并落入输入包；辩论/分析 Agent 维持 `tools:[Read]`，只消费输入包、不自行联网。缺失数据 SHALL 先由 data-desk 联网兜底，取不到才在 evidence 标 `missing` 并显式提示，**不静默降级、不编造**。

#### Scenario: 多维输入包由 data-desk 填真实数据
- **GIVEN** 用户触发 `analyze asset:equity`
- **WHEN** 编排器在辩论前执行 ensureDataDesk
- **THEN** `inputs/data_macro.json`（档 A）与 `inputs/asset_equity.json` 的 `desk_*`（档 B）由 data-desk 填入 verified+URL 的真实数据，辩论 Agent 仅 Read 这些包

#### Scenario: 缺数据源联网兜底而非静默标 missing
- **GIVEN** 运行环境缺 akshare/Mongo
- **WHEN** data-desk 取该大类宏观/估值数据
- **THEN** 优先联网取得并标 verified+URL；确实取不到的指标才标 missing 并在 evidence 显式提示，辩论 Agent 据 status 决定是否降级，全程不编造数值
