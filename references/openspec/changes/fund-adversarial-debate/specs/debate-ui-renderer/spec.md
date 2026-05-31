## ADDED Requirements

### Requirement: 前端原生流式解析对决对话树
The system SHALL 在面对后端的 JSON 对话对象时（如包含长串 `history`），将文本按发言角色切片，并以气泡框或时间线的友好结构展示，而非生硬 JSON。

#### Scenario: 渲染 `investment_debate_state` 对决节点
- **WHEN** 前端展示组件发现当前报告映射类型为包含对决状态的对象且其具有 `history` 字段
- **THEN** 调用 `DebateTimeline` 解析每行并呈现聊天气泡

#### Scenario: 优雅降级无解析情况
- **WHEN** JSON 对象解析失败，或无 `history`
- **THEN** 兜底渲染为正常的 Markdown stringify 结构，确保页面不报错崩溃

### Requirement: 前端增加基金和风控状态映射
The system SHALL 在 `SingleAnalysis.vue` 中配置正确的名字，如“⚔️ 投资多空辩论” 对应 `investment_debate_state`。

#### Scenario: 正常展示多空辩论页签
- **WHEN** 后端返回的 JSON 对象携带对应 Key
- **THEN** Tab 面板能正确渲染对应名字并承载内部流程