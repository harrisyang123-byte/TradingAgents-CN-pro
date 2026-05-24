## ADDED Requirements

### Requirement: 组合分析 SSE 流式推送

系统 SHALL 通过 SSE 实时推送分析过程到前端。

#### Scenario: 前端接收节点完成事件
- **GIVEN** 前端建立 SSE 连接到 `/api/sse/portfolio/{task_id}`
- **WHEN** 后端任意 agent 节点完成
- **THEN** 前端收到 `{type: "node_complete", node: "L1-市场策略师", stage: "1/4", text: "agent输出文本..."}` 并实时渲染

#### Scenario: SSE 心跳保活
- **GIVEN** SSE 连接已建立
- **WHEN** 连续 10 秒无节点完成事件
- **THEN** 后端发送心跳事件，前端不渲染心跳但保持连接

#### Scenario: Edge Case — Redis 不可用回退轮询
- **GIVEN** Redis 连接失败
- **WHEN** 后端进度更新
- **THEN** 进度数据写 MongoDB，前端回退到 2s 间隔的 HTTP 轮询 `GET /api/portfolio/analysis/{task_id}/status`

### Requirement: 总揽 API 聚合查询

系统 SHALL 提供聚合 API 返回行业覆盖矩阵数据。

#### Scenario: 总揽页加载
- **GIVEN** 用户有持仓且有历史分析记录
- **WHEN** 前端调用 `GET /api/portfolio/overview`
- **THEN** 返回包含每个行业的持仓权重、覆盖状态、最近分析时间、处方建议的矩阵数据

#### Scenario: Edge Case — 持仓行业无历史分析
- **GIVEN** 用户持仓包含"医药生物"但从未分析
- **WHEN** 前端调用总揽 API
- **THEN** 该行业的 coverage_status="never"，last_analysis_at=null，处方字段为空

### Requirement: 报告类型筛选

系统 SHALL 支持在报告列表页按报告类型筛选。

#### Scenario: 筛选组合建议
- **GIVEN** 用户访问 `/reports` 页面
- **WHEN** 用户在 report_type 下拉中选择"组合建议"
- **THEN** 列表仅显示 `report_type === "portfolio"` 的报告

#### Scenario: Edge Case — 存量报告无 report_type
- **GIVEN** 存量 `analysis_reports` 文档没有 `report_type` 字段
- **WHEN** API 查询时
- **THEN** 默认视为 `"single"` 类型
