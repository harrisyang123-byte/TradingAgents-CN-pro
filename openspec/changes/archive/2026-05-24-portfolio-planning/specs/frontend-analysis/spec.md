## ADDED Requirements

### Requirement: 流式分析页面

系统 SHALL 提供流式分析页面，分两阶段展示分析过程。

#### Scenario: Phase 1 市场扫描
- **GIVEN** 用户访问 `/portfolio/analysis`
- **WHEN** 用户点击"开始市场扫描"
- **THEN** SSE 流式展示 L1 agent 辩论过程（阶段条 + 流式文本），完成后展示推荐行业计划（表格：行业名、生命周期、Go/NoGo、置信度、推荐理由、勾选框）

#### Scenario: Phase 2 执行分析
- **GIVEN** 用户确认行业选择
- **WHEN** 用户点击"开始分析"
- **THEN** SSE 流式展示 L2-L4 全过程，按 4 阶段滚动（L2 标的筛选 → L3 组合辩论 → PE 估值 → L4 CIO 终裁）

#### Scenario: Edge Case — 分析失败重试
- **GIVEN** Phase 2 执行中 LLM API 超时
- **WHEN** 系统标记任务失败
- **THEN** 前端展示失败信息 + "重试"按钮，用户可重试

### Requirement: 总揽仪表盘

系统 SHALL 提供行业覆盖矩阵仪表盘。

#### Scenario: 查看行业覆盖状态
- **GIVEN** 用户访问 `/portfolio/overview`
- **WHEN** 页面加载完成
- **THEN** 展示行业覆盖矩阵表格，包含持仓权重、覆盖状态、处方建议等列，stale/never 行高亮

#### Scenario: 查看历史组合建议
- **GIVEN** 总揽页已加载
- **WHEN** 用户点击某条历史建议
- **THEN** 展开完整报告（决策卡片 + CIO 全文 + 可折叠详细报告）

#### Scenario: Edge Case — 无持仓时总揽页
- **GIVEN** 用户没有任何持仓
- **WHEN** 访问 `/portfolio/overview`
- **THEN** 展示空态引导"请先添加持仓"，并链接到持仓明细页
