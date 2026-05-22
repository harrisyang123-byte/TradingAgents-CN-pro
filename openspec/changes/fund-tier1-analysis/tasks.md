# Tasks: fund-tier1-analysis

> 垂直切片原则：每个 task 端到端可验证，禁止水平分层。

## Slice 1：基金数据工具层
**目标**：能从 AKShare 获取基金分析所需的所有数据

- [x] 1.1 新建 `tradingagents/dataflows/fund_data.py`
  - `get_fund_basic_info(code)` — 基础信息 + 投资策略
  - `get_fund_performance(code)` — 历史业绩 + 同类排名
  - `get_fund_risk_metrics(code)` — 夏普比率、最大回撤、年化波动率
  - `get_fund_holdings_or_index(code, fund_type)` — 重仓股（主动型）或指数信息（QDII/指数型）
  - `get_fund_nav_history(code, period)` — 净值历史（复用 fund_service 逻辑）
- [x] 1.2 验证：对 270042（QDII）和 005827（主动型）各跑一遍，数据正确返回

## Slice 2：基金分析 Graph
**目标**：能跑通完整的基金多 Agent 辩论，输出结构化结果

- [x] 2.1 新建 `tradingagents/graph/fund_graph.py`
  - 3 个分析师节点：`FundManagerAnalyst`、`FundHoldingsAnalyst`、`FundRiskAnalyst`
  - 1 个裁判节点：`FundTrader`
  - 复用 `TradingAgentsGraph` 的 LLM 工厂、checkpointer、progress_callback 机制
- [x] 2.2 新建 `tradingagents/agents/analysts/fund_analysts.py` — 3 个分析师 prompt + 节点函数
- [x] 2.3 新建 `tradingagents/agents/trader/fund_trader.py` — 综合裁判 prompt，输出 `expected_return` 替代 `target_price`
- [ ] 2.4 验证：本地跑 270042，能输出 action + expected_return + 三份报告

## Slice 3：SSE 实时消息流
**目标**：前端能实时看到 Agent 分析文本和工具调用

- [x] 3.1 扩展 `_send_progress_update`：从 chunk 提取 `messages[-1].content`（AIMessage）和 `tool_calls`，加入 callback payload
- [x] 3.2 新建 SSE 端点 `GET /api/analysis/stream/{task_id}`
  - 从 Redis 订阅 task 消息队列
  - 推送 `agent_message`、`tool_call`、`progress`、`complete` 四种事件
- [x] 3.3 验证：curl SSE 端点，能收到实时消息

## Slice 4：后端 API 接入
**目标**：`/api/analysis/submit` 支持基金代码，结果存 `analysis_tasks`

- [x] 4.1 `SingleAnalysisRequest` 加 `instrument_type` 字段（默认 `stock`）
- [x] 4.2 `analysis.py` router：根据 `instrument_type` 路由到 `fund_graph` 或 `trading_graph`
- [x] 4.3 结果存档时加 `instrument_type: "fund"` 字段
- [ ] 4.4 验证：POST `/api/analysis/submit` 传基金代码，任务正常创建和完成

## Slice 5：FundDetail 前端
**目标**：用户在基金详情页能触发分析，看到实时消息流和最终报告

- [ ] 5.1 `FundDetail/index.vue` 加"AI 分析"按钮，点击提交分析任务
- [ ] 5.2 分析进行中：展示 SSE 消息流（Agent 名称 + 内容气泡）
- [ ] 5.3 分析完成：展示最终报告（action/expected_return/confidence + 三份报告折叠展示）
- [ ] 5.4 验证：端到端跑通 270042 分析，前端正确展示

## 完成标准

- [ ] 270042（QDII）和 005827（主动型）都能完成分析
- [ ] 前端实时展示 Agent 消息
- [ ] 结果存入 MongoDB，`instrument_type: "fund"`
- [ ] 股票分析功能不受影响
