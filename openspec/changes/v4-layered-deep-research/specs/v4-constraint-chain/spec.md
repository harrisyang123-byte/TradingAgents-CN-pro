# v4-constraint-chain Specification

## Purpose
通过「上游快照指纹 + version 比对」识别依赖关系，当上游更新时把下游标记为 stale 并软提醒，但不强制重算、不阻断使用旧结论、不静默修正约束数值。对应 FR-005。

## Requirements

### Requirement: 下游记录上游版本指纹
系统 SHALL 在每个下游单元产物中记录其依据的上游单元版本/指纹（`upstream[]`），可人读追溯（如「本行业配比基于资产配比 v3、宏观 v7」）。

#### Scenario: 下游追溯上游
- **GIVEN** `alloc:equity_industries` 基于 `alloc:portfolio` v3
- **WHEN** 读取该单元
- **THEN** `upstream[]` 含 `{unit_id:"alloc:portfolio", version:3, fingerprint:...}`

### Requirement: 上游更新置黄软提醒
当某上游单元产生新版本时，系统 SHALL 将所有引用其旧版本的下游单元置为「建议刷新(黄)」，并提供可读 `stale_reason`（如「行业配比基于 3 天前的资产配置，建议刷新」）。

#### Scenario: 上游 version 递增触发置黄
- **GIVEN** `alloc:portfolio` 从 v3 升到 v4
- **WHEN** 计算下游 `alloc:equity_industries`（仍引用 v3）状态
- **THEN** 该下游状态=yellow 且带 stale_reason

### Requirement: 不强制刷新不阻断
系统 SHALL NOT 在上游变化时自动重跑下游，也 SHALL NOT 阻止用户继续查看/采用 stale 结论（软提醒，非硬阻断）。

#### Scenario: stale 结论仍可读
- **GIVEN** 某下游单元为 yellow
- **WHEN** 用户读取该单元
- **THEN** 系统正常返回旧结论 + 软提醒，不报错不强制重算

### Requirement: 刷新后重绑最新上游
当用户主动刷新某下游单元时，系统 SHALL 使其重新绑定到当前最新上游指纹，并将状态恢复为「新鲜(绿)」。

#### Scenario: 刷新恢复绿
- **GIVEN** `alloc:equity_industries` 为 yellow（上游已升 v4）
- **WHEN** 用户 `refresh alloc:equity_industries`
- **THEN** 重跑后 `upstream[]` 绑定 portfolio v4，状态恢复 green

### Requirement: 约束链校验仅报警不修正
在使用下传约束（如 `equity_quota` 下传行业层）时，系统 SHALL 校验链路完整性；发现下游使用的约束来自已过时上游时，仅报警提示而不修正数值。

#### Scenario: 过时约束仅报警
- **GIVEN** 行业配比使用的 `equity_quota` 来自旧版 `alloc:portfolio`
- **WHEN** 校验约束链
- **THEN** 标注「约束来自过时上游」报警，不自动改写 equity_quota 数值
