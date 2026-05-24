## ADDED Requirements

### Requirement: L1 独立执行

系统 SHALL 支持独立执行 L1 市场扫描（不触发 L2-L4），返回推荐行业计划。

#### Scenario: 用户触发 L1 计划
- **GIVEN** 用户访问 `/portfolio/analysis` 并点击"开始市场扫描"
- **WHEN** 系统调用 `propagate_l1_plan()`
- **THEN** 只运行 L1 节点链（market_strategist → contrarian → debate → macro_judge），SSE 流式推送每个节点输出，最终返回 3-5 个推荐行业及其生命周期、Go/NoGo、优先级

#### Scenario: 用户确认行业选择后执行完整分析
- **GIVEN** L1 返回推荐计划
- **WHEN** 用户勾选行业并点击"开始分析"
- **THEN** 系统调用 `propagate_advice(selected_industries=[...])`，L2 Scout 只扫描用户确认的行业

#### Scenario: Edge Case — L1 未返回任何 Go 行业
- **GIVEN** 市场环境极端（所有行业 NoGo）
- **WHEN** L1 扫描完成
- **THEN** 前端展示"当前无明确投资方向"提示，仍列出行业以供查看，允许用户手动选择行业强制分析
