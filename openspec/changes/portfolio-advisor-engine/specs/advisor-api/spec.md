## ADDED Requirements

### Requirement: 触发组合建议
系统 SHALL 提供 API 端点让用户手动触发组合顾问分析。

#### Scenario: 正常触发
- **WHEN** 用户调用 POST /api/portfolio/advice，用户有 5 只持仓
- **THEN** 系统创建 PortfolioAdvice 记录（状态 GENERATING），返回 202 + advice_id，后台异步执行引擎

#### Scenario: 无持仓时触发
- **WHEN** 用户调用 POST /api/portfolio/advice，用户无任何持仓
- **THEN** 系统返回 400 错误 "请先录入持仓后再获取组合建议"

#### Scenario: 重复触发
- **WHEN** 用户调用 POST /api/portfolio/advice，已有一个 GENERATING 状态的请求
- **THEN** 系统返回 409 错误 "组合建议正在生成中，请稍候"

### Requirement: 查看组合建议
系统 SHALL 提供 API 端点查看组合建议结果。

#### Scenario: 查看最新建议
- **WHEN** 用户调用 GET /api/portfolio/advice/latest
- **THEN** 系统返回最新一份 COMPLETED 状态的 PortfolioAdvice，包含处方（AdviceItem 列表）和辩论摘要

#### Scenario: 查看指定建议
- **WHEN** 用户调用 GET /api/portfolio/advice/{advice_id}
- **THEN** 系统返回指定 PortfolioAdvice 的完整内容

#### Scenario: 查看历史建议列表
- **WHEN** 用户调用 GET /api/portfolio/advice?page=1&page_size=10
- **THEN** 系统返回该用户的组合建议历史（按时间倒序），每条包含生成时间、状态、持仓数

#### Scenario: 建议生成中查看
- **WHEN** 用户调用 GET /api/portfolio/advice/{advice_id}，该建议状态为 GENERATING
- **THEN** 系统返回当前状态 GENERATING + 已完成的阶段信息

#### Scenario: 跨用户访问
- **WHEN** 用户 A 调用 GET /api/portfolio/advice/{advice_id}，该 advice 属于用户 B
- **THEN** 系统返回 403 错误

### Requirement: 异步执行与进度通知
系统 SHALL 异步执行组合顾问引擎，并通过现有通知机制推送进度。

#### Scenario: 执行完成通知
- **WHEN** 组合顾问引擎异步执行完成
- **THEN** 系统通过 WebSocket 通知前端，前端自动刷新展示结果

#### Scenario: 执行失败
- **WHEN** 组合顾问引擎执行过程中 LLM 调用失败（重试 1 次仍失败）
- **THEN** PortfolioAdvice 状态更新为 FAILED，通知前端，前端提示"生成失败，请重试"
