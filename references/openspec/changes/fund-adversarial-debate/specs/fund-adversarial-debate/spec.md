## ADDED Requirements

### Requirement: 基金分析包含深度投资辩论
The system SHALL 对单只基金的分析执行多轮对决，引入 `Fund Bull Researcher` 和 `Fund Bear Researcher` 进行 `ConditionalLogic` 回环。

#### Scenario: 成功开启并结束多空辩论
- **WHEN** 基础分析师输出完成，系统进入辩论图流转
- **THEN** 系统交替触发 Bull 与 Bear 对话，直至设定的最大轮数，最终将结果汇聚为 `investment_debate_state` 输出给 Manager 裁判

### Requirement: 基金分析包含三方风控辩论
The system SHALL 在输出初步投资决策后，激活风控体系，使 `Aggressive`、`Neutral`、`Conservative` 三个风险模型进行探讨。

#### Scenario: 风控探讨流转
- **WHEN** 投资决策生成
- **THEN** 执行风控循环直到最大轮数，并将对白写入 `risk_debate_state`

### Requirement: 基金特有指标攻击视角
The system SHALL 在 `Fund Bear Researcher` 的预设系统 Prompt 中强制要求结合基金最大回撤、经理换手率及重仓股集中度进行风险攻击。

#### Scenario: 空头针对基金的逆向思维
- **WHEN** `Fund Bear Researcher` 拿到基金基础分析报告
- **THEN** 其生成的内容必须指向基金特定的流动性隐患或经理人风格漂移等风险，而非通用的话术

## MODIFIED Requirements

### Requirement: 基金后端分析图流程（fund-analysis-pipeline）
系统 SHALL 在 `fund_graph.py` 构建并返回具有辩论状态的完整 `json` 并保存持久化，而不仅仅是线性地输出结果。

#### Scenario: JSON 持久化存储与结果返回
- **WHEN** `fund_graph.py` 的执行流到达 `END` 节点
- **THEN** `results/<fund_code>/<date>/TradingAgentsStrategy_logs/full_states_log.json` 必须被正确记录，且前端 API 获取到的状态对象内包含完整的 `history` 对话日志。