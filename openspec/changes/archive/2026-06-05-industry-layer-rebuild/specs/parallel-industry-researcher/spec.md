## ADDED Requirements

### Requirement: 每行业独立并行研究员
系统 SHALL 为扫描池中每个行业独立 spawn 一个研究员 agent，所有行业并行执行，互不阻塞。

#### Scenario: 多行业并行运行
- **GIVEN** 扫描池包含5个行业
- **WHEN** 行业研究员启动
- **THEN** 5个研究员同时运行，总耗时约等于最慢单个行业的耗时，而非5倍串行时间

#### Scenario: 单行业研究员失败不影响其他行业（Edge Case）
- **GIVEN** 科技行业研究员因 LLM 超时失败
- **WHEN** 并行执行
- **THEN** 其他行业正常完成，科技行业标记为研究失败（go_nogo=unknown），不阻断整体流程

### Requirement: B+C 三层数据源注入
每个行业研究员 SHALL 接收三层数据：LLM 内生知识（训练数据）+ AKShare 硬数据（景气/估值）+ 新闻研报（AKShare新闻+官网政策）。

#### Scenario: 三层数据完整注入
- **WHEN** 行业研究员启动
- **THEN** prompt 中包含行业景气数据（资金流向/PE分位/ROE趋势）、近7天相关新闻摘要、近期政策信号

#### Scenario: 硬数据获取失败时（Edge Case）
- **GIVEN** AKShare 行业 PE 接口返回空数据
- **WHEN** 行业研究员运行
- **THEN** 研究员基于 LLM 内生知识 + 新闻继续分析，在 reasoning 中注明"估值数据不可用，基于定性判断"

### Requirement: 两层辩论结构
系统 SHALL 执行行业内辩论（Strategist vs Contrarian，固定2轮）和跨行业权重辩论（固定1轮），输出 go_nogo + suggested_weight。

#### Scenario: 行业内辩论完整执行
- **WHEN** 单行业研究完成
- **THEN** Strategist 先发言，Contrarian 挑战，Strategist 回应，共2轮，行业裁判输出最终 go_nogo

#### Scenario: suggested_weight 双因子约束
- **GIVEN** AI 行业 PE 分位 85%（历史高位）但景气度评分 90/100
- **WHEN** 行业裁判输出 suggested_weight
- **THEN** suggested_weight 不因高 PE 被否决，但在 reasoning 中注明"估值偏高，建议分批建仓"，权重调节幅度 ≤ 30%

#### Scenario: suggested_weight 不超行业上限
- **GIVEN** max_industry_weight = 30%
- **WHEN** 行业裁判输出 suggested_weight
- **THEN** 任何行业的 suggested_weight ≤ 30%，超限时自动截断并在 reasoning 中说明
