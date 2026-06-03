## ADDED Requirements

### Requirement: 交叉验证检测 Tier1 报告矛盾
`cross_validate.py` SHALL 扫描所有 Tier1 报告,对同一标的出现"买入"和"卖出"矛盾建议时生成 high severity 冲突。

#### Scenario: 中兴通讯 3 份报告方向矛盾
- **WHEN** Tier1 报告中有 2 份建议"买入"中兴通讯,1 份建议"卖出"
- **THEN** `conflicts.json` 中生成 `{type: "tier1_conflict", code: "000063", severity: "high", description: "Tier1 报告矛盾: 买入(来源A,来源B) vs 卖出(来源C)"}`

#### Scenario: 无 Tier1 矛盾
- **WHEN** 所有 Tier1 报告对同一标的的建议方向一致或仅 1 份报告
- **THEN** 不生成 tier1_conflict 冲突

### Requirement: 交叉验证检测 PE 高估 vs 买入建议不一致
当标的同时满足 PE 5年分位 >85% 且被建议买入/加仓时,`cross_validate.py` SHALL 生成 medium severity 冲突。

#### Scenario: PE 99% 分位但 Scout 推强烈推荐
- **WHEN** Scout 输出 candidates 中包含某标的且 total_score>=35,同时 data_pe 中该标的 pe_percentile_5y = 99
- **THEN** `conflicts.json` 中生成 `{type: "pe_overvalued", code: "xxx", severity: "medium", description: "PE 处于 99% 分位(偏贵),但 Scout 建议强烈推荐"}`

#### Scenario: PE 低位且建议买入(一致,不触发)
- **WHEN** 标的 pe_percentile_5y = 15 且被建议加仓
- **THEN** 不生成 pe_overvalued 冲突

### Requirement: 交叉验证检测敞口重叠
对 `data_exposure.json` 中 overlaps 数组的每个元素,如果 overlap_weight > 15% SHALL 生成 low severity 冲突。

#### Scenario: 基金穿透后苹果实际敞口 18%
- **WHEN** 持仓中 3 只基金底层都重仓苹果,穿透后 AAPL 总敞口 18%
- **THEN** `conflicts.json` 中生成 `{type: "overlap", code: "AAPL", severity: "low", description: "基金穿透后 AAPL 实际敞口 18%,超过 15% 阈值"}`

#### Scenario: 重叠未超阈值
- **WHEN** overlap_weight = 12%
- **THEN** 不生成 overlap 冲突

### Requirement: 冲突报告注入 CIO 上下文
`conflicts.json` SHALL 作为 L4-CIO初稿和 L4-CIO终裁的强制输入文件,Agent prompt 中要求"必须对每个冲突做出回应:确认/驳回/标注需人工判断"。

#### Scenario: CIO 初稿处理 Tier1 矛盾
- **WHEN** L4-CIO初稿的 prompt 中包含 conflicts.json 且其中有 tier1_conflict
- **THEN** CIO 在处方中对该标的标注"Tier1矛盾,建议重新分析",timing 倾向 conditional

#### Scenario: 无冲突时正常出方案
- **WHEN** conflicts.json 的 conflicts 数组为空
- **THEN** CIO 正常出资金分配方案,不做额外标注

### Requirement: 规则引擎必须是确定性算法
交叉验证 SHALL 使用 Python 硬编码规则实现,不使用 LLM。规则不说谎。

#### Scenario: 确定性输出
- **WHEN** 对同一组输入文件运行 `cross_validate.py` 两次
- **THEN** 两次输出的 conflicts.json 完全一致(字节级)

#### Scenario: 规则引擎执行时间
- **WHEN** `cross_validate.py` 处理 36 只持仓 + 19 只候选 + 11 份 Tier1 报告
- **THEN** 执行时间 < 100ms(纯 Python 字典操作,无网络调用)
