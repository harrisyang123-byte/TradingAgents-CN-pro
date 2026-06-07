# v4-dual-run-ingest Specification

## Purpose
使本地运行与 AI 代跑两种模式产出结构一致的单元信封并覆盖式落盘；AI 代跑产物以单元粒度 git 友好 JSON 随仓库传输，用户本地拉取后通过幂等导入写入数据库，前端读数据库（或静态快照）正确解析展示，无需区分产物来源。对应 FR-009。

## Requirements

### Requirement: 两种运行入口
系统 SHALL 支持两种运行入口：① 本地运行（连本地数据/数据库）；② AI 代跑（仅接收用户提供的持仓文件，不依赖用户本地数据库）。

#### Scenario: AI 代跑脱库运行
- **GIVEN** 运行环境无用户 MongoDB
- **WHEN** `run_v4.sh analyze <selector> --portfolio-file holdings.json`
- **THEN** 全程不依赖用户数据库，产出单元信封文件

### Requirement: 双跑产物结构同构
系统 SHALL 使两种模式产出结构同构的落盘产物（同一套信封 schema：分析报告/配比/状态/快照指纹），前端解析逻辑对两者一致；`run_mode` 仅为元信息。

#### Scenario: 同构 schema
- **GIVEN** 同一份持仓分别走本地与代跑
- **WHEN** 比对两边产物
- **THEN** 信封 schema 一致，前端解析与展示结构对齐

### Requirement: 单元粒度 git JSON 传输载体
系统 SHALL 以单元粒度的结构化 JSON 文件（每单元一个稳定路径文件，diff 友好、可人读）作为 git 传输载体，避免传输数据库 dump 或二进制。

#### Scenario: 单元文件可 review
- **WHEN** AI 代跑完成并 commit
- **THEN** 提交的是 `data/v4/**/*.json` 单元文件，可 diff、可 code review

### Requirement: 覆盖式更新单元粒度
当某单元被重新分析时，系统 SHALL 以覆盖式更新该单元的 JSON 文件（保留单元粒度，不整体重写其它单元），并更新其状态与时间戳。

#### Scenario: 重跑只覆盖本单元
- **GIVEN** 多个单元文件已存在
- **WHEN** 重跑其中一个
- **THEN** 仅该单元文件被覆盖更新（version+1），其它单元文件与状态不变

### Requirement: 幂等导入入库
当用户本地拉取产物时，系统 SHALL 提供幂等的解析/导入机制（按单元唯一键 `(user_id, unit_id)` upsert 入 MongoDB `v4_units`，重复导入不产生重复或脏数据），导入后前端按三层 Tab 正确展示，效果与本地运行一致。

#### Scenario: 重复导入幂等
- **GIVEN** 同一批单元 JSON
- **WHEN** 连续运行 `import_v4.py` 两次
- **THEN** `v4_units` 无重复/脏数据，单元仍为最新信封

### Requirement: 敏感数据隐私约定
系统 SHALL 确保落盘产物中的敏感财务数据（持仓/处方）遵循现有 `.gitignore` 与隐私约定；若产物文件含敏感数据需共享，须走私有仓库。

#### Scenario: 敏感产物不入公库
- **GIVEN** `data/v4/` 含持仓/处方
- **WHEN** 提交
- **THEN** 受 `.gitignore` 保护；如需共享静态快照则走私有仓库
