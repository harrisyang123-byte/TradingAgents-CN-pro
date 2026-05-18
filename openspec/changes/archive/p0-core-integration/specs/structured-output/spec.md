## ADDED Requirements

### Requirement: ResearchManager 输出 ResearchPlan

research_manager agent SHALL 输出 `ResearchPlan` 结构化数据，指导后续分析师工作。

#### Scenario: 正常输出 ResearchPlan
- **WHEN** research_manager 接收到分析请求
- **THEN** 输出包含 plan_type, tickers, focus_areas, timeline 字段
- **AND** plan_type 为 deep_dive / catalyst / earnings / technical 之一

#### Scenario: LLM 不支持结构化输出时降级
- **WHEN** LLM 不支持 tool_use 或 structured output
- **THEN** `invoke_structured_or_freetext` 自动降级为自由文本
- **AND** 下游 agent 仍能正常处理文本格式的计划

### Requirement: Trader 输出 TraderProposal

trader agent SHALL 输出 `TraderProposal` 结构化交易提案。

#### Scenario: 正常输出 TraderProposal
- **WHEN** trader 决定交易方向后
- **THEN** 输出包含 ticker, direction, confidence, reasoning, risk_factors
- **AND** direction 为 long / short / neutral 之一
- **AND** confidence 为 1-100 整数

#### Scenario: 降级为自由文本
- **WHEN** LLM 不支持结构化输出
- **THEN** trader 输出自由文本
- **AND** 不影响 PM 或后处理逻辑

### Requirement: PM 输出 PortfolioDecision

portfolio_manager agent SHALL 输出 `PortfolioDecision` 包含单个决策列表。

#### Scenario: 正常输出 PortfolioDecision
- **WHEN** PM 综合所有 agent 输出后做最终决策
- **THEN** 输出包含 decisions 列表和 allocation_summary
- **AND** 每个 decision 包含 ticker, action, rationale
- **AND** action 为 buy / sell / hold / increase / reduce 之一

### Requirement: 评级解析 rating.py

系统 SHALL 提供确定性评级解析函数，无需 LLM 调用。

#### Scenario: 解析标准评级字符串
- **WHEN** 输入 "Buy" / "Overweight" / "Hold" / "Underweight" / "Sell"
- **THEN** 返回对应枚举值
- **AND** 大小写不敏感

#### Scenario: 解析复合文本中的评级
- **WHEN** 输入包含评级的自然语言句子
- **THEN** 正确提取并返回 5 档中匹配的评级
- **AND** 无匹配时返回 None 而非抛异常
