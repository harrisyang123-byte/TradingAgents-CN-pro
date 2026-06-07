# v4-asset-allocation Specification

## Purpose
在各大类独立分析就绪之上，由资产配置委员会总监产出七大类目标配比报告（Σ=100%、允许主动归零），并将权益额度作为约束向下传递给行业层。对应 FR-003。

## Requirements

### Requirement: 读取各大类最新结论并标注缺失/过时
触发资产配比时，系统 SHALL 读取七大类各自最新的分析结论作为输入；若某大类尚无分析或其分析已 stale，则在配比报告 `input_warnings[]` 中显式标注「该类输入缺失/过时」，并允许用户选择先补跑或带风险继续。

#### Scenario: 某大类输入缺失
- **GIVEN** `asset:commodity` 尚未分析
- **WHEN** 触发 `analyze alloc:portfolio`
- **THEN** 配比报告 `input_warnings[]` 标注 commodity「缺失」，不静默跳过

### Requirement: 当前→目标配比且总和为 100%
系统 SHALL 产出「当前配比 → 目标配比」对照，七大类目标配比之和等于 100%，并给出每类调整方向与理由。

#### Scenario: 配比总和校验
- **GIVEN** 配置委员会总监产出 `assets[]`
- **WHEN** 校验总和
- **THEN** Σ target_weight = 100，否则标记 sum_check 异常

### Requirement: 主动归零为合法决策
若用户/总监判断短期不配置某大类，系统 SHALL 允许该大类目标配比为 0%（`actively_zeroed:true` + 归零理由），视 0% 为合法决策而非缺失，其余大类配比之和仍须等于 100%。

#### Scenario: 主动归零某类
- **GIVEN** 总监决定本期不配 `alternative`
- **WHEN** 产出配比
- **THEN** alternative `target_weight=0, actively_zeroed=true` 含理由，其余六类 Σ=100

### Requirement: 权益额度约束下传
系统 SHALL 将权益目标配比作为约束（`equity_quota`）向下传递，成为权益大类内行业层的总权重上限；若权益目标配比为 0%，则不触发权益深链（行业/个股层）并在前端标注「本期不配置权益」。

#### Scenario: 权益额度下传
- **GIVEN** 配比产出权益 target_weight=55%
- **WHEN** 写入 `alloc:portfolio`
- **THEN** `equity_quota=55` 落盘，供下游 `alloc:equity_industries` 作为权重上限引用

#### Scenario: 权益归零跳过深链
- **GIVEN** 权益 target_weight=0%
- **WHEN** 编排器处理
- **THEN** 不触发行业/个股深链，前端标注「本期不配置权益」

### Requirement: 记录上游分析快照指纹
系统 SHALL 为配比报告记录其依据的「各大类分析快照指纹」（7 个 `asset:*` 的 version+fingerprint）写入信封 `upstream[]`，供下游一致性校验与软提醒使用。

#### Scenario: 配比信封记录上游
- **GIVEN** 配比基于 7 个大类分析
- **WHEN** 落盘 `alloc:portfolio`
- **THEN** `upstream[]` 含 7 个 `asset:*` 的 `{unit_id,version,fingerprint}`
