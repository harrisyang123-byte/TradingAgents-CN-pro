# v4-asset-research-dept Specification

## Purpose
对单一大类运行独立「大类研究部门」：多维尽调 + 对立角色固定 3 轮辩论 + 部门总监拍板，产出该大类的形势研判与发展方向报告，逐类独立落盘。对应 FR-002。

## Requirements

### Requirement: 单大类独立多维分析
系统 SHALL 对单个大类独立运行分析部门，输入覆盖该资产相关的多维信息：宏观（利率/通胀/货币政策/经济周期）、微观/基本面（估值与供需）、舆情与资金面、政策与地缘政治；缺失数据源时降级为「LLM 知识 + 可得行情」并在 evidence 标 `missing`。

#### Scenario: 多维输入包拼装
- **GIVEN** 用户触发 `analyze asset:equity`
- **WHEN** 采集阶段拼装输入包
- **THEN** 输入包含宏观/基本面/舆情资金/政策地缘四类数据，缺失维度标注 missing 而非中断

### Requirement: 固定 3 轮对立辩论
系统 SHALL 配置参考真实投研机构的对立角色（多头研究员 vs 空头研究员 + 专项视角分析师），进行固定 3 轮辩论，每轮记录双方论点与反驳到 `debate_rounds[]`。

#### Scenario: 三轮辩论留痕
- **GIVEN** 大类研究部门启动
- **WHEN** 辩论完成
- **THEN** 产物 `debate_rounds[]` 含 3 个回合，每回合记录 bull/bear 论点与反驳

### Requirement: 总监拍板输出研判
3 轮辩论结束后，系统 SHALL 由「大类部门总监」角色拍板，输出该大类的：当前形势研判、发展方向（看多/看空/中性 + 理由）、主要风险、建议趋势。

#### Scenario: director 产出 verdict
- **GIVEN** 3 轮辩论已完成
- **WHEN** 总监角色运行
- **THEN** 产出 `verdict{stance, situation, direction, risks[], trend}`

### Requirement: 逐类独立落盘
系统 SHALL 把每个大类的分析报告独立落盘（`data/v4/assets/<class>.json`），独立标注 version/更新时间/新鲜度，七大类互不覆盖。

#### Scenario: 重跑某类不影响其它类
- **GIVEN** `asset:equity` 与 `asset:cash` 均已落盘
- **WHEN** 重跑 `asset:equity`
- **THEN** 仅 `assets/equity.json` 被覆盖更新（version+1），`assets/cash.json` 不变

### Requirement: 零持仓大类仍可触发
若某大类用户当前零持仓，系统 SHALL 仍允许对其触发分析（用于发现机会/择机配置），不因无持仓而跳过。

#### Scenario: 对零持仓大类深析
- **GIVEN** 用户在 `alternative` 类零持仓
- **WHEN** 触发 `analyze asset:alternative`
- **THEN** 系统产出该类分析报告，`tradable` 候选可空，分析聚焦「是否值得择机配置」
