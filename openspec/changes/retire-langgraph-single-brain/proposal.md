## Why

> **状态：已完成** (2026-06-06)

系统里存在**两个并行且会分叉的大脑**：v3 JS workflow（`scripts/workflow-v3-advisor.js`，子 agent，run.sh/「分析」触发）与 LangGraph `AdvisorGraph`（`tradingagents/graph/advisor_graph.py`，47 处 `llm.invoke()` 直调，线上 API `/api/portfolio/analysis` 实际在跑）。两者写同一 `portfolio_advice` 集合，前端读「最近一条」的 `industry_matrix`——谁后跑谁覆盖，导致前端富字段（景气/目标%/操作/个股处方/辩论历程）时有时无。这是反复修前端却治不好的根因，也违反 README「子 Agent 而非 `llm.invoke()`」第一原则。

## What Changes

- **修改** `/api/portfolio/analysis/plan` 与 `/execute`：后端从 `AdvisorGraph` 切换到 v3 pipeline（保留两阶段 API 契约，前端不变）
- **新增** `app/services/v3_advisor_runner.py`：以 subprocess 驱动 `scripts/run.sh`（collect → claude -p 编排 → ingest），管理 run_dir 与 task 状态
- **新增** `workflow-v3-advisor.js` + `run.sh` 的 `--to <stage>` 能力：`/plan` 跑到 industry 阶段为止；scout/pm 尊重 `selected_industries`
- **移除** `app/routers/portfolio_analysis.py` / `app/services/portfolio_advisor_service.py` 对 `AdvisorGraph` 的 import 与调用（保留 `_prepare_tier1_reports`）
- **BREAKING** 退役 `tradingagents/graph/advisor_graph.py`（LangGraph 大脑）及 `agents/advisor/l1~l4-*.md`（9 个旧 agent 定义）
- **删除** 归档残留与旧入口：`scripts/archived/`、`.claude/workflows/workflow-advisor.js`、`scripts/claude-advisor.js`、`cli/claude_advisor.py`

## Capabilities

### New Capabilities

- `single-brain-consolidation`: 收敛到 v3 单一大脑——所有组合分析（CLI「分析」与前端 API）走同一 v3 workflow + ingest，消除双大脑对同一集合的覆盖竞争
- `api-v3-backed-analysis`: `/api/portfolio/analysis` 两阶段端点改由 v3 pipeline（subprocess）驱动，落库统一带 industry_matrix/positions_detail/debate 富字段

## Impact

**代码**：
- `app/routers/portfolio_analysis.py` — `_execute_l1`/`_execute_l2_l4` 改调 v3_advisor_runner
- `app/services/v3_advisor_runner.py` — 新建（subprocess 封装 + 状态管理）
- `app/services/portfolio_advisor_service.py` — 移除 AdvisorGraph 用法
- `scripts/workflow-v3-advisor.js` / `scripts/run.sh` — 新增 `--to`，scout/pm 过滤 selected_industries
- `tradingagents/graph/advisor_graph.py` — 删除（退役）
- `agents/advisor/l1~l4-*.md` — 删除（9 个）

**清理**：`scripts/archived/`、`.claude/workflows/workflow-advisor.js`、`scripts/claude-advisor.js`、`cli/claude_advisor.py`

**数据**：`portfolio_advice` 集合 schema 不变（仍由 ingest_advice.py 写富字段），但写入者从「两个大脑」收敛为「仅 v3」。

**环境约束（验证）**：本沙箱无 MongoDB/akshare/claude 鉴权，无法 live 端到端跑。真跑用 subagent 当 LLM 驱动 v3 over fixture + `ingest_advice.py --out-json` 证明富字段契约；生产真跑走部署机 run.sh。代码层用 `node --check`/`py_compile` 验证。

<!-- Dialectical Analysis
## 方案对比

方案A（本方案，保留两阶段 API 重接 v3）
- 优点：前端零改动；blast radius 小；retire langgraph 目标达成
- 缺点：需给 workflow 加 --to + selected_industries 过滤；两阶段 HITL 与 v3 自治哲学略有张力

方案B（收敛为单端点 /analyze 一次成型）
- 优点：最契合 v3 自治哲学，最干净
- 缺点：要改前端 UX（去掉选行业步骤）——用户高度关注该屏，blast radius 大
- 结论：本次取 A，B 作为后续 change

最可能失败的点：
- subprocess 跑 claude -p 需部署机鉴权，本沙箱不可验证 → 缓解：代码正确性 + 语法过，runtime 明示由部署环境承担
- 删 advisor_graph 有隐藏引用 → 缓解：删前全仓 grep + 先标废弃
- --to/selected_industries 改 workflow 引入回归 → 缓解：fixture 跑对应阶段验证
-->
