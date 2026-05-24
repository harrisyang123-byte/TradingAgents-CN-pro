# 持仓组合规划 (Portfolio Planning)

**变更**: portfolio-planning
**日期**: 2026-05-24

## 概述

将原有的单按钮"组合分析"升级为完整的三页面持仓组合管理系统，支持两阶段 SSE 流式分析、行业覆盖追踪、结果双写持久化。

### 三页面架构

```
/portfolio (el-sub-menu)
  ├── /portfolio/holdings   — 持仓明细（现有页面，移除旧组合分析按钮）
  ├── /portfolio/analysis   — 持仓分析（新增，两阶段流式分析）
  └── /portfolio/overview   — 组合总揽（新增，行业覆盖矩阵仪表盘）
```

### 两阶段分析流程

```
Phase 1: L1 市场扫描 → SSE 流式推送 → 推荐行业计划（可勾选）→ 用户确认
Phase 2: L2-L4 标的筛选 + 组合辩论 + CIO 裁决 → SSE 流式推送 → 决策卡片展示
```

## 实现要点

### 数据模型

- **`industry_coverage` 集合** — 行业覆盖状态独立存储，字段：`user_id`, `industry_name`, `market`, `lifecycle`, `go_nogo`, `confidence`, `reasoning`, `priority`, `analyzed_at`, `advice_id`, `status`(planned/completed)。索引：`{user_id, industry_name}` unique, `{user_id, status}`, `{analyated_at: -1}`
- **`analysis_reports` 扩展** — 新增 `report_type` 字段（`"single"` / `"portfolio"`），存量数据默认 `"single"`。组合建议写入时 `stock_symbol = portfolio_{advice_id}`

### 流式技术：SSE + Redis PubSub

- `RedisProgressTracker._save_progress()` 中增加 `redis.publish("task_progress:{task_id}", json.dumps(progress))`
- 复用现有 `task_progress_generator` 和 `/api/stream/portfolio/{task_id}` SSE 端点
- 前端 `EventSource` 消费，3 次重连上限
- 回退方案：Redis 不可用时前端回退到 HTTP 轮询 `GET /api/portfolio/analysis/{task_id}/status`

### Graph 变更

- `AdvisorGraph.propagate_l1_plan()` — 独立执行 L1 节点链（market_strategist → contrarian → debate → macro_judge），返回推荐行业列表
- `AdvisorGraph.propagate_advice(selected_industries=...)` — 接受行业筛选参数，Scout 只扫描指定行业
- `AdvisorState` 新增 `selected_industries: List[str]`

### API

| 端点 | 方法 | 用途 |
|------|------|------|
| `/api/portfolio/analysis/plan` | POST | 触发 L1 市场扫描 |
| `/api/portfolio/analysis/execute` | POST | 用户确认行业后执行 L2-L4 |
| `/api/portfolio/analysis/{task_id}/status` | GET | HTTP 轮询状态（SSE 回退） |
| `/api/stream/portfolio/{task_id}` | GET | SSE 流式推送 |
| `/api/portfolio/overview` | GET | 行业覆盖矩阵聚合数据 |
| `/api/reports/list?report_type=portfolio` | GET | 报告类型筛选 |

### 结果双写

分析完成时同时写入：
- `portfolio_advice` — 保持现有兼容
- `analysis_reports` — `report_type: "portfolio"`, `stock_symbol: "portfolio_{advice_id}"`

## 关键决策

1. **三页面拆分而非单页面 SPA** — 各页面职责单一，holdings 保持不变，analysis 模仿 SingleAnalysis 流式布局，overview 独立仪表盘
2. **SSE + Redis PubSub 而非 WebSocket** — 基础设施已就绪（`task_progress_generator`、RedisProgressTracker），工程代价最低
3. **两阶段而非一键执行** — 用户可在 L1 结果中确认/调整行业选择后再执行 L2-L4，增加透明度和可控性
4. **industry_coverage 独立集合** — 与 portfolio_advice 解耦，支持跨分析会话追踪覆盖状态
5. **ThreadPoolExecutor 异步执行** — 在同步 LangGraph 上下文中通过线程池提交分析任务，避免阻塞 API 响应

## 注意事项

- ThreadPoolExecutor 每次 API 请求创建新实例，高并发下可能泄漏，后续应改为全局单例
- SSE portfolio 端点未实现任务所有权验证（batch/stock SSE 端点同样缺失）
- `datetime.fromisoformat()` 解析 ISO 字符串可能产生 naive datetime，与 `datetime.now(timezone.utc)` 比较前需显式设置 tzinfo
- 前端 `sortedHistoryPrescription` 按 priority 排序（urgent → important → optional），DecisionCard 组件复用
