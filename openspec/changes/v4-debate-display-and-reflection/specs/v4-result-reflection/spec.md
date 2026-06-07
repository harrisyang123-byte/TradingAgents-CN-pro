# v4-result-reflection Specification

## Purpose
为 v4 引入「结果闭环反思」（Layer 1，轻量版）：大类部门总监在每轮研判前先读取自己上一版结论，输出「较上次变了什么、为什么改判、上次判断回看对不对」的 `reflection`，并在前端展示。让系统从「每次重新开始」变为「有记忆、会自省、对过往判断负责」，直接服务用户「用结论差异调整模型」的目标。借鉴 TauricResearch/TradingAgents 的 `get_past_context` 反思注入，但以 v4 的单元归档为载体、零新基建。

## ADDED Requirements

### Requirement: 总监开辩前读取上一版结论
系统 SHALL 让大类部门总监在产出本轮 verdict 前，`Read` 落盘的上一版单元信封（`data/v4/assets/<class>.json`）取得上次 `verdict`。该机制 SHALL 复用「`write_unit` 先归档旧版再写新版、总监运行在 write 之前」的时序——总监运行时落盘文件仍是上一版，无需新建历史文件。

#### Scenario: 重跑时读到上一版结论
- **GIVEN** `asset:equity` 已有 v1 落盘（stance=bullish）
- **WHEN** 重跑 `asset:equity`，总监在 write 前运行
- **THEN** 总监 `Read` 到落盘的 v1 verdict，据其与本轮新数据生成反思

#### Scenario: 首跑无历史
- **GIVEN** `asset:commodity` 从未落盘
- **WHEN** 首次运行总监
- **THEN** 读不到历史，`reflection.self_check="first_run"`，其余字段允许 null，不阻断研判

### Requirement: reflection 字段输出
系统 SHALL 在大类 verdict 中输出可选 `reflection{prev_stance, prev_date, what_changed, why_changed, self_check}`：变化原因 SHALL 引用本轮 data-desk 的新数据/事件；`self_check` SHALL 诚实回看上次判断对错。该字段 SHALL 向后兼容——旧信封无此字段时读取方不报错。

#### Scenario: 改判时给出接地理由
- **GIVEN** 上次 bullish、本轮新数据显示外围 risk-off
- **WHEN** 总监改判为 neutral
- **THEN** `reflection.why_changed` 引用本轮具体新数据（如美 10Y 飙升、纳指下跌），`what_changed` 说明判断差异

### Requirement: 前端展示「较上次」反思条
系统 SHALL 在大类详情页 verdict 区下方展示「较上次 / 自检」小条；当 `reflection` 缺省或 `self_check="first_run"` 时 SHALL NOT 渲染该条（不报错、不空白）。

#### Scenario: 有反思则展示
- **GIVEN** 大类详情含非 first_run 的 reflection
- **WHEN** 前端渲染 Tab2
- **THEN** verdict 下方显示「较上次：上次 X → 这次 Y，因为 Z」+ 自检

#### Scenario: 首跑不展示反思条
- **GIVEN** reflection.self_check="first_run" 或字段缺省
- **WHEN** 前端渲染
- **THEN** 不显示反思条，其余 verdict 正常展示

### Requirement: Layer 2/3 演进登记（本期不实现）
系统 SHALL 将「基准收益回填」（Layer 2：给各大类绑基准、data-desk 快照基准点位、反思引用真实涨跌%）与「个股级 alpha 跟踪」（Layer 3）登记为后续演进方向，本期 SHALL NOT 实现，避免无收益接地的反思被夸大为已验证结论。

#### Scenario: 反思不冒充已验证结果
- **GIVEN** 本期仅 Layer 1（无收益接地）
- **WHEN** 总监输出 reflection
- **THEN** 自省基于「判断与新数据」而非真实收益，不声称已用 alpha 验证
