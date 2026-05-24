# Retro: portfolio-planning (持仓组合规划)

**复杂度**: complex
**日期**: 2026-05-24
**变更规模**: 27 files, +2218 / -167 lines

## What Went Well

### 规划阶段
- **SSE + Redis PubSub 复用预判准确**：`task_progress_generator` + `RedisProgressTracker` 基础设施已就绪，只需在 `_save_progress()` 加一行 `redis.publish()`。工程代价近乎为零，无需引入 WebSocket 或 astream。
- **两阶段架构（L1 独立 → 用户确认 → L2-L4）决策正确**：解决了"一键黑盒"信任问题，用户可在行业选择环节审查和调整。

### 实现阶段
- **前端状态机设计清晰**：`idle → planning → plan_ready → executing → completed → failed`，每种状态有明确 UI，无状态混叠。
- **双写策略有效**：`portfolio_advice` + `analysis_reports` 同时写入，向后兼容且使报告页可查询组合建议。

### 工具流程
- **openspec artifacts 覆盖完整**：6 个 spec 文件覆盖所有 capability + Edge Case，reviewer 能基于 specs 做结构化审查。

## What Went Wrong

### 实现阶段
- **3 BLOCKER 级别缺陷**（reviewer 发现）：
  1. `executor.submit(_run_l)` — 函数名拼写错误，应为 `_run_l1`（NameError）
  2. status 字段 hardcode `"running"` — 导致 L1 完成后前端轮询永远检测不到完成
  3. `datetime.fromisoformat()` 产生 naive datetime → 与 `datetime.now(timezone.utc)` 比较时 TypeError
- **PaperTrading/index.vue 编辑失误**：移除 advice 逻辑时，一次 Edit 操作意外破坏了 `fmtMoney` 函数（函数体被替换为错误的 `goAnalysis` 体），需回修
- **`current_user["user_id"]` vs `current_user["id"]`**：未确认 auth 模块返回的字段名就使用，初始实现用了错误的 key

### 工具流程
- **reviewer 介入时机偏晚**：3 个 BLOCKER 在实现全部完成后才发现，如果在 Slice 3（后端 API）完成后就触发 reviewer，可更早修复
- **tasks.md 未标记完成**：33/33 tasks 在 archive 时仍显示 incomplete，因未在实现过程中逐条勾选

## Lessons Learned

### 1. datetime 处理是 Python 3 高频陷阱
`datetime.fromisoformat("2026-05-24T10:30:00Z".replace("Z", "+00:00"))` 在 Python 3.11+ 才默认返回 aware datetime，旧版本返回 naive。与 `datetime.now(timezone.utc)` 比较前必须显式 `dt.replace(tzinfo=timezone.utc)`。

**适用条件**：所有涉及 ISO 时间字符串解析的场景。
**边界**：Python 3.11+ `fromisoformat` 已改进，但 3.10 仍有此问题。

### 2. API 响应字段应从真实数据源读取，禁止 hardcode
`status` 被 hardcode 为 `"running"`，但 MongoDB 中实际状态已是 `"L1_COMPLETED"`。前端轮询依赖该字段判断完成，导致死循环。

**适用条件**：所有 `GET /status` 类端点。
**边界**：初始创建时的 status 可以是 hardcode 的 `"running"`，但查询时必须从 DB 读取。

### 3. 大文件 Vue 组件编辑应拆分为多次小编辑
`PaperTrading/index.vue` 移除 advice 逻辑时，一次 Edit 的 `old_string` 匹配到了非预期的位置，导致不相关函数被破坏。

**适用条件**：文件 >300 行且有多个结构相似的代码块时。
**边界**：<100 行的文件单次 Edit 通常安全。

### 4. SSE 端点缺少所有权验证（安全债务）
`/api/stream/portfolio/{task_id}` 未验证当前用户是否为 task 的创建者，任何人可通过 task_id 监听他人分析过程。现有 `/api/stream/task/{task_id}` 也有同样问题。

**适用条件**：所有 SSE 端点。
**边界**：内部工具可降低优先级，但面向多用户时必须修复。

## Architecture Deep Check (zoom-out)

### Deletion Test
| 模块 | 删除后复杂度去哪？ | 判断 |
|------|-------------------|------|
| `portfolio_analysis.py` (464L) | plan/execute/status 端点消失，但 advisor_graph 核心逻辑不受影响 | deep-ish — 薄路由层 |
| `Analysis.vue` (538L) | 用户失去流式 UI，分析仍可 API 调用 | shallow — 展示层，正常 |
| `propagate_l1_plan()` | L1 独立执行能力消失，需在 propagate_advice 内部切分 | deep — 封装了 4 节点子图 |

### 模块边界
- `portfolio_analysis.py` → `PortfolioAdvisorService` → `AdvisorGraph` → `scout_node`，依赖链清晰无循环
- `portfolio_analysis.py` 直接操作 MongoDB（`db["tasks"]`），未通过 service 层 — 轻度架构债务，但现有 batch/stock 分析端点也有相同模式

## Decisions

- [ ] **全局 ThreadPoolExecutor 单例** — 每次 API 请求 `ThreadPoolExecutor(max_workers=1)` 可能在高并发下泄漏，改为应用级单例
- [ ] **SSE 端点统一加 ownership 验证** — `/api/stream/portfolio/{task_id}` 和 `/api/stream/task/{task_id}` 都需验证
- [ ] **datetime 工具函数标准化** — 在 `app/utils/` 加 `parse_iso_datetime()` 统一处理 tzinfo
- [ ] **Slice 级 reviewer 触发** — 复杂变更应在每个后端 Slice 完成后触发 reviewer，而非等全部实现完毕
