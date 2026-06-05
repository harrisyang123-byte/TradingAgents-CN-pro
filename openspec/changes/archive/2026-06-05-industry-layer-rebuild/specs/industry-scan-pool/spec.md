## ADDED Requirements

### Requirement: 三层行业扫描池自动构建
系统 SHALL 在每次组合分析启动时，自动合并三层来源构建行业扫描池：持仓行业（必选）、用户 watchlist（必选）、景气打分前3名（自动补充）。

#### Scenario: 正常合并三层来源
- **GIVEN** 用户有持仓（含行业信息）、有 watchlist、景气打分已完成
- **WHEN** 行业扫描池构建
- **THEN** 系统输出去重后的行业列表，标注每个行业的来源（holding/watchlist/vitality）

#### Scenario: 持仓无行业信息时（Edge Case）
- **GIVEN** paper_positions.industry 字段为空（历史数据未迁移）
- **WHEN** 行业扫描池构建
- **THEN** 系统对无行业信息的持仓触发一次性 LLM 分类补填，写入 paper_positions.industry，再继续构建扫描池

#### Scenario: watchlist 为空
- **GIVEN** 用户未设置 watchlist
- **WHEN** 行业扫描池构建
- **THEN** 系统跳过 watchlist 层，仅用持仓行业 + 景气前3名，不报错

### Requirement: 扫描池来源透明展示
系统 SHALL 在分析结果中标注每个被研究行业的入池原因。

#### Scenario: 用户可查看行业入池原因
- **WHEN** 组合分析完成
- **THEN** 行业矩阵每行包含 source 字段（holding/watchlist/vitality/manual），用户可了解为何研究此行业
