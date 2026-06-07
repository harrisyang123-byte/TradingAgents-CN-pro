# v4-asset-research-dept Specification

## Purpose
本 change 修订大类研究部门的**研判范式与数据接地措辞**，借鉴 TauricResearch/TradingAgents 的果断评级与源冲突接地经验：总监不再被「数据盲区→默认中性」诱导骑墙；多源数据冲突时标记分歧而非私自调和。提升辩论质量与结论可执行性。对应 design §5.9.3（与 §5.8 data-desk 凭据契约一致）。

## MODIFIED Requirements

### Requirement: 总监拍板输出研判
3 轮辩论结束后，系统 SHALL 由「大类部门总监」角色拍板，输出该大类的：当前形势研判、发展方向（看多/看空/中性 + 理由）、主要风险、建议趋势。**总监 SHALL 遵循反骑墙果断条款：仅当多空证据真正势均力敌时才给 `neutral`/`hold`；否则必须站队并明确说明采信哪方、压低哪方。数据盲区 SHALL 表达为「降低 confidence + 缩小建议幅度」，而非默认中性。** verdict SHALL NOT 因数据不足而无脑收敛到 neutral/hold。

#### Scenario: director 产出 verdict
- **GIVEN** 3 轮辩论已完成
- **WHEN** 总监角色运行
- **THEN** 产出 `verdict{stance, situation, direction, risks[], trend, confidence}`

#### Scenario: 证据不平衡时必须站队
- **GIVEN** 多头证据明显强于空头
- **WHEN** 总监拍板
- **THEN** stance 取 bullish 并说明采信多头、压低空头的理由，不取中性

#### Scenario: 数据盲区降信心而非中性
- **GIVEN** 关键维度数据缺失但现有证据偏向某方
- **WHEN** 总监拍板
- **THEN** 保留方向性 stance、调低 confidence、缩小建议幅度，并在 situation 注明盲区

## ADDED Requirements

### Requirement: 多源冲突标记分歧
系统 SHALL 要求数据采集与分析角色在遇到多源数据冲突（同一指标不同来源取值不一致）时，标记分歧——列出各来源值、最终采用值与采用理由——SHALL NOT 私自调和出一个未标注的数。该规则适用于 `v4-data-desk` 与三专项分析师（macro/flow/policy）。

#### Scenario: 利率多源冲突标记
- **GIVEN** 中国 10Y 国债收益率在两个来源分别为 2.7% 与 1.71%
- **WHEN** data-desk/分析师记录该指标
- **THEN** evidence 标出两源值 + 采用值（1.71%）+ 采用理由（更近日期/更权威源），不悄悄填一个数
