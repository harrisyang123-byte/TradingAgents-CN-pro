# v4-analysis-unit Specification

## Purpose
以「按单元独立触发 + 统一五色新鲜度状态机」驱动 v4 全部分析，放弃一次性全量跑完。触发主入口为 CLI 对话（本地用户或 AI 在本地调起 agent），前端仅只读展示状态与软提醒。对应 FR-004。

## Requirements

### Requirement: CLI 为主触发入口
系统 SHALL 以 CLI 对话为主触发入口：用户用自然语言指定要分析/刷新的单元（大类/资产配比/行业/个股），AI 解析为单元级触发命令并在本地执行；同时保留等价脚本命令 `scripts/run_v4.sh <verb> <unit-selector>` 供本地直接调用。前端 SHALL NOT 提供「点击即跑 LLM」的按钮。

#### Scenario: 自然语言解析为单元命令
- **GIVEN** 用户在 CLI 说「分析权益大类」
- **WHEN** AI 解析
- **THEN** 执行 `run_v4.sh analyze asset:equity` 并覆盖式落盘

#### Scenario: 等价脚本命令兜底
- **GIVEN** 本地用户直接运行 `run_v4.sh analyze industry:AI算力`
- **WHEN** 命令执行
- **THEN** 仅运行该行业深辩单元

### Requirement: 单元独立触发互不连带
触发某单元时，系统 SHALL 仅运行该单元（及其明确选择的范围），不连带强制重跑其它单元；多个单元可分别独立处于不同状态。

#### Scenario: 触发不连带重跑
- **GIVEN** 多个单元处于 green/yellow/gray 混合状态
- **WHEN** 触发其中一个单元
- **THEN** 仅该单元进入 blue→green，其它单元状态不变

### Requirement: 分层独立 TTL
系统 SHALL 为每类分析单元配置独立的时间有效期（TTL），不同层级（大类配置、行业、个股）各自一档且可配置。

#### Scenario: 不同层级不同 TTL
- **GIVEN** TTL 配置表
- **WHEN** 读取大类、行业、个股单元 TTL
- **THEN** 三者可取不同天数，且可在配置中修改

### Requirement: 五色新鲜度状态机
系统 SHALL 以纯只读函数计算单元状态为五色之一——未分析(灰)/分析中(蓝)/新鲜(绿)/建议刷新(黄)/失败(红)；状态计算不触发重跑。

#### Scenario: 五状态判定
- **GIVEN** 单元产物文件不存在
- **WHEN** 计算状态
- **THEN** 返回 gray；有锁无产物→blue；error→red；过期或上游更新→yellow；否则 green

### Requirement: 单元落盘元数据
系统 SHALL 对每个单元落盘记录：状态、最近运行时间、TTL、所依据的上游快照指纹、运行结果产物路径，并在 `_units.json` 索引汇总。

#### Scenario: 信封落盘元数据
- **WHEN** 任一单元运行完成
- **THEN** 其信封含 status/generated_at/ttl_days/upstream/path，`_units.json` 同步更新

### Requirement: 前端 CLI 触发提示
系统 SHALL 在前端为每个单元提供「该如何在 CLI 中触发」的可读指令提示（`cli_hint`：自然语言说法或脚本命令），而非提供直接调起 LLM 的按钮。

#### Scenario: 单元展示 cli_hint
- **GIVEN** 某单元为 gray（未分析）
- **WHEN** 前端渲染该单元
- **THEN** 显示「在 CLI 中说『分析<单元>』」提示，无触发 LLM 按钮

### Requirement: 运行锁去重排队
若一个单元正在分析中（blue），重复触发该单元 SHALL 被去重或排队，不产生并发重复运行。

#### Scenario: 并发重入被拒
- **GIVEN** `asset:equity` 持有运行锁（blue）
- **WHEN** 再次触发 `analyze asset:equity`
- **THEN** 提示「该单元正在运行」并退出，不启动第二次运行
