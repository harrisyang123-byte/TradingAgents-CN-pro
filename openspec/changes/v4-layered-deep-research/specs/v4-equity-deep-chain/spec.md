# v4-equity-deep-chain Specification

## Purpose
在权益额度约束内，按「先把行业研究透、再据此配比」的正确顺序展开权益深链：行业逐个独立深辩定方向 → 行业间资金配比 →（独立行业内部门）个股独立分析 → 行业内资金配比。对应 FR-006。

## Requirements

### Requirement: 候选行业内置与对话挑选
系统 SHALL 内置若干候选行业（依据风口与长期投资理论），并在 CLI 对话中询问用户「先深度分析哪些行业」，用户可自选、可采纳系统推荐。

#### Scenario: 推荐并由用户挑选
- **GIVEN** 用户进入权益深链
- **WHEN** AI 询问先分析哪些行业
- **THEN** 给出内置候选 + 景气推荐，用户自选或采纳

### Requirement: 行业深辩先于配比
当用户触发某单一行业的深度分析时，系统 SHALL 以独立「行业研究部门」对该行业做多轮对立辩论，产出行业方向研判（景气、空间、风险、配置建议），此步先于行业间配比。

#### Scenario: 行业深辩产出方向
- **GIVEN** 触发 `analyze industry:AI算力`
- **WHEN** 行业研究部门运行
- **THEN** 产出 verdict（景气/空间/风险/配置建议），且在行业间配比之前完成

### Requirement: 行业间资金配比受权益额度约束
已选行业深度分析就绪后，系统 SHALL 由行业配置团队基于各行业深度结论，在权益额度上限内产出行业间资金配比（各行业目标权重之和 ≤ equity_quota）；某行业深度分析缺失/stale 时显式标注并允许先补跑或带风险继续。

#### Scenario: 行业权重不超额度
- **GIVEN** equity_quota=55%，已深辩 3 个行业
- **WHEN** 产出 `alloc:equity_industries`
- **THEN** Σ行业 target_weight ≤ 55%

### Requirement: 独立行业内部门个股分析
行业方向与行业权重确定后触发个股时，系统 SHALL 由独立「行业内研究部门」对行业内公司/资产做详细分析，找候选标的，并对每只个股独立运行一次分析（个股互相独立、独立缓存），产出评级与目标价。

#### Scenario: 个股独立缓存
- **GIVEN** 某行业内选定 2 只个股
- **WHEN** 分别 `analyze stock:<code>`
- **THEN** 每只个股独立落盘独立缓存，重跑一只不影响另一只

### Requirement: 行业内资金配比
个股分析就绪后，系统 SHALL 在该行业目标权重内对选定个股做行业内资金配比，产出每只个股的目标权重与买入区间。

#### Scenario: 行业内配比产出权重与买点
- **GIVEN** 某行业目标权重 20%，行业内 2 只个股已分析
- **WHEN** 产出 `alloc:industry:<name>`
- **THEN** 每只个股给出 target_weight 与 entry_price_range，Σ ≤ 20%

### Requirement: 行业/个股层遵守独立触发与软提醒
系统 SHALL 使行业层、个股层各自遵守单元独立触发与快照指纹/软提醒机制：行业深辩变 → 行业配比置黄；行业配比变 → 个股配比置黄。

#### Scenario: 行业变更级联置黄
- **GIVEN** `industry:AI算力` 重跑 version+1
- **WHEN** 计算 `alloc:equity_industries` 状态
- **THEN** 该配比单元置 yellow（软提醒，不自动重跑）
