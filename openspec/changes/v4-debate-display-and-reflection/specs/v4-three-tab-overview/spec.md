# v4-three-tab-overview Specification

## Purpose
本 change 在三层 Tab 既有能力上**修订 Tab2 大类详情**，使其与 Tab3 行业详情一致地展示多轮辩论过程与三专项分析师视角，并承载结果反思条。数据已存在于 `asset:<class>` 信封（`payload.debate_rounds`/`analysts`），仅为展示管线补全，零 LLM 重跑。对应 design §5.9.1。

## MODIFIED Requirements

### Requirement: Tab2 大类详情按类型分流
当用户点击某大类时，系统 SHALL 进入 Tab2 大类详情：权益以表格展示行业列表（含行业间配比、状态、关键指标）；非权益展示其差异化投资方案。**此外，无论权益或非权益，Tab2 SHALL 展示该大类的多轮多空辩论历程（`debate_rounds`）与三专项分析师（macro/flow/policy）视角**——数据取自 `build_asset_detail` 补吐的 `debate_rounds`/`analysts` 字段，渲染方式与 Tab3 行业深辩折叠块一致。辩论数据缺省（`[]`）时 SHALL 不渲染辩论块、不报错。

#### Scenario: 点击权益进入行业表格
- **GIVEN** 用户在 Tab1
- **WHEN** 点击「权益」卡片
- **THEN** Tab2 以表格展示权益行业列表

#### Scenario: 点击非权益进入方案
- **WHEN** 点击「固定收益」卡片
- **THEN** Tab2 展示固收差异化方案（卡片/小表）

#### Scenario: 大类详情展示多轮辩论
- **GIVEN** `asset:equity` 信封含 `debate_rounds`（3 轮）
- **WHEN** 用户进入权益大类详情
- **THEN** Tab2 在 verdict 头与行业表之间展示「大类深辩历程（3 轮）」折叠块，每轮含多头/空头对栏

#### Scenario: 无辩论数据不报错
- **GIVEN** 某大类信封 `debate_rounds` 为空
- **WHEN** 渲染 Tab2
- **THEN** 不显示辩论块，verdict 与行业/方案区正常渲染

## ADDED Requirements

### Requirement: build_asset_detail 补吐辩论与分析师
系统 SHALL 在 `build_asset_detail` 响应中加入 `debate_rounds`（取 `payload.debate_rounds`，默认 `[]`）与 `analysts`（取 `payload.analysts`，默认 `{}`）。因该函数被 `portfolio_v4` 路由与 `build_snapshot_v4` 共用，改动 SHALL 同时对 API 与静态快照生效（同构），SHALL NOT 触发任何 LLM 重计算。

#### Scenario: API 与快照同构带辩论
- **GIVEN** `build_asset_detail` 已补吐字段
- **WHEN** 分别经 API 与重生成的静态快照读取 `asset:equity`
- **THEN** 两者返回结构一致、均含 `debate_rounds`/`analysts`，无 LLM 重跑
