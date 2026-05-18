## ADDED Requirements

### Requirement: 风险辩论者命名对齐原版
系统 SHALL 使用原版命名：`Aggressive Analyst`（激进派）、`Conservative Analyst`（保守派）、`Portfolio Manager`（组合经理/最终裁决）。

#### Scenario: 激进分析师命名
- **WHEN** 风险辩论阶段创建激进派 agent
- **THEN** agent 名称为 `Aggressive Analyst`，创建函数为 `create_aggressive_debator()`

#### Scenario: 保守分析师命名
- **WHEN** 风险辩论阶段创建保守派 agent
- **THEN** agent 名称为 `Conservative Analyst`，创建函数为 `create_conservative_debator()`

#### Scenario: 组合经理命名
- **WHEN** 风险裁决阶段创建裁决 agent
- **THEN** agent 名称为 `Portfolio Manager`，创建函数为 `create_portfolio_manager()`

### Requirement: State 字段命名对齐原版
AgentState 中的字段 SHALL 使用原版命名。

#### Scenario: 辩论历史字段
- **WHEN** AgentState 定义辩论历史
- **THEN** 字段名为 `aggressive_history` 和 `conservative_history`（非 risky_history / safe_history）

#### Scenario: 当前回复字段
- **WHEN** AgentState 定义当前辩论回复
- **THEN** 字段名为 `current_aggressive_response` 和 `current_conservative_response`

### Requirement: 条件路由使用原版名称
Graph 的条件路由 SHALL 使用原版 agent 名称进行节点跳转。

#### Scenario: 辩论结束路由
- **WHEN** 辩论轮次结束需要路由
- **THEN** 路由目标为 `"Portfolio Manager"`, `"Conservative Analyst"`, `"Aggressive Analyst"`
