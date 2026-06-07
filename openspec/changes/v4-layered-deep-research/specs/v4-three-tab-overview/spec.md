# v4-three-tab-overview Specification

## Purpose
以三层 Tab 结构呈现「资产配置 → 大类详情 → 行业/个股」，在每个分析单元上展示五色新鲜度状态与 stale 软提醒；卡片用于少量需突出状态的对象，表格用于多项需横向对比的对象。对应 FR-008。

## Requirements

### Requirement: Tab1 七大类卡片
系统 SHALL 在 Tab1（资产配置）以卡片展示七大类，每卡显示该类分析摘要、状态颜色（灰/蓝/绿/黄/红）、最近更新时间，以及「当前→目标」配比。

#### Scenario: 七大类卡片渲染
- **GIVEN** v4 overview 数据就绪
- **WHEN** 用户访问组合总揽
- **THEN** Tab1 渲染 7 张卡片，各含状态色 + 摘要 + current→target

### Requirement: Tab2 大类详情按类型分流
当用户点击某大类时，系统 SHALL 进入 Tab2 大类详情：权益以表格展示行业列表（含行业间配比、状态、关键指标）；非权益展示其差异化投资方案。

#### Scenario: 点击权益进入行业表格
- **GIVEN** 用户在 Tab1
- **WHEN** 点击「权益」卡片
- **THEN** Tab2 以表格展示权益行业列表

#### Scenario: 点击非权益进入方案
- **WHEN** 点击「固定收益」卡片
- **THEN** Tab2 展示固收差异化方案（卡片/小表）

### Requirement: Tab3 行业深辩与个股表格
当用户点击某行业时，系统 SHALL 进入 Tab3：展示行业深辩报告，并以表格展示行业内个股分析列表与行业内资金配比（个股、评级、目标价、目标权重、状态）。

#### Scenario: 行业详情渲染
- **WHEN** 点击某行业
- **THEN** Tab3 展示深辩报告 + 个股表格（评级/目标价/目标权重/状态）

### Requirement: 状态色与软提醒文案
系统 SHALL 在任意单元卡片/表格行上展示状态颜色，并在 stale 时显示可读软提醒文案及对应的 CLI 触发指令提示，SHALL NOT 提供直接调起 LLM 的按钮。

#### Scenario: stale 行展示软提醒
- **GIVEN** 某单元为 yellow
- **WHEN** 前端渲染该行
- **THEN** 显示黄色状态 + 「基于 N 天前的上游配置，建议在 CLI 中刷新」+ cli_hint，无触发 LLM 按钮

### Requirement: 空态引导
当缺少数据（未分析/未触发）时，系统 SHALL 显示空态与引导（提示在 CLI 如何触发），而非报错或空白。

#### Scenario: 未分析单元空态
- **GIVEN** 某单元为 gray
- **WHEN** 前端渲染
- **THEN** 显示空态 + 「在 CLI 中触发分析」引导，不报错不空白
