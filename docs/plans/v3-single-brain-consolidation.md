# Plan — 退役 LangGraph，收敛到 v3 单一大脑

> 状态：进行中
> 关联 openspec change：`retire-langgraph-single-brain`
> 决策人：用户（2026-06-06 拍板「可以退役 langgraph」）

## 1. 诊断：当前有两个并行且会分叉的「大脑」

| | 大脑 A（v3，应为 canonical） | 大脑 B（线上 API 实际在跑） |
|---|---|---|
| 实现 | `scripts/workflow-v3-advisor.js`（Claude Code Workflow，子 agent）| `tradingagents/graph/advisor_graph.py` `AdvisorGraph`（~1200 行 LangGraph）|
| 范式 | `agent()` 子 agent 调用，Step 0-7 | **47 处 `llm.invoke()` 直调**（违反 README「子 Agent 而非 llm.invoke()」原则）|
| agent 定义 | `agents/advisor/v3-*.md`（15 个）| `agents/advisor/l1~l4-*.md`（9 个）|
| 触发 | 对话「分析」/ `scripts/run.sh` | 前端 → `POST /api/portfolio/analysis/plan` + `/execute` |
| 落库 | `ingest_advice.py` 写 `portfolio_advice`（含 industry_matrix/vitality/positions_detail）| `_execute_l1/_execute_l2_l4` 写 `portfolio_advice`（无 v3 富字段）|

**根因**：两个大脑写**同一个** `portfolio_advice` 集合；前端 `paper.py::get_portfolio_overview` 读「最近一条 advice」的 `industry_matrix/synthesis_result`。谁后跑谁覆盖 → 前端富字段（景气/目标%/操作/个股处方/辩论历程）时有时无。用户从前端点分析走的是大脑 B，产出缺 v3 字段，于是景气 `--`、辩论历程空、个股缺失。**这不是前端 bug，是后端两个大脑分叉。**

## 2. 决策

**收敛到 v3 JS workflow 作为唯一大脑，退役 LangGraph `AdvisorGraph` 及 l1~l4 agent。**

理由：
- v3 逻辑更全（大类资产配置 / 行业并行辩论 / 约束传递链 / 事前风控 / Portfolio Synthesizer），且符合 README 子 agent 原则；
- run.sh + ingest 已经是 v3 的成熟落库链路；
- 一套大脑 = 一份事实源，从根上消除「改一处另一处漂移」和「谁后跑谁覆盖」。

## 3. 设计

### 3.1 API 形态（保留两阶段，重接 v3）

保留前端契约不变（`/plan` → `/execute` → `/{taskId}/status`），把后端从 `AdvisorGraph` 换成 v3 pipeline：

- `POST /plan`：新建 run_dir → 跑 v3 数据采集 + `macro`+`asset`+`industry` 阶段（**停在 industry**）→ 读 `industry_allocations.json` 返回推荐行业（go_nogo/stance/vitality/final_weight）。run_dir 持久化到 task 文档。
- `POST /execute`：拿同一 run_dir + `selected_industries` → 跑 `scout`+`portfolio`+`pm`+`synth` → `ingest_advice.py` 写 `portfolio_advice` 富字段 → 状态 COMPLETED。
- 封装在新服务 `app/services/v3_advisor_runner.py`：用 `asyncio.create_subprocess_exec` 调 `scripts/run.sh`（或直接 collect→claude -p→ingest 三步），管理 run_dir 与 task 状态。

需要的最小脚本增强：
- `workflow-v3-advisor.js` + `run.sh` 增加 `--to <stage>` / `to:` arg：跑到某阶段为止（`/plan` 停在 industry 需要）。
- scout/pm 阶段尊重 `selected_industries.json`（用户勾选过滤）。

> **未来可选（不在本次范围）**：v3 本身是自治一次成型（cross-industry judge 已对全行业分配），可进一步收敛为单端点 `/analyze` 一次跑完、去掉 HITL 选行业步骤。本次为降低前端 blast radius 不做。

### 3.2 退役清单

- `app/routers/portfolio_analysis.py`：`_execute_l1` / `_execute_l2_l4` 不再 import/调用 `AdvisorGraph`，改调 `v3_advisor_runner`。
- `app/services/portfolio_advisor_service.py`：移除 `AdvisorGraph` 用法；保留仍有用的 `_prepare_tier1_reports`（Tier1 研究库读取）。
- `tradingagents/graph/advisor_graph.py`：标记废弃 / 删除（确认无其他活引用后）。
- `agents/advisor/l1-*.md l2-*.md l3-*.md l4-*.md`（9 个）：删除（仅大脑 B 消费）。
- 删除归档残留 + 旧入口（用户已授权「可以删除」）：
  - `scripts/archived/`（5 个无引用文件：workflow-v3-{pm-debate,synthesizer,industry-layer}.js、workflow-advisor.js、save_v3_to_mongodb.py）+ `scripts/archived/oneoff/`
  - `.claude/workflows/workflow-advisor.js`（v2 旧编排活副本）
  - `scripts/claude-advisor.js`、`cli/claude_advisor.py`（旧 CLI 入口）

## 4. 验证（含环境约束的诚实说明）

**本沙箱限制**：无 MongoDB 可达、无 akshare、无 motor/pymongo、claude CLI 在但无鉴权。→ **无法 live 端到端跑**（数据采集 + DB 落库 + claude -p 编排都跑不了）。

**能做的真跑**：用平台 subagent 工具充当 LLM，按 `v3-*.md` 提示驱动各 agent 节点，读 fixture dataDir 的 `data_*.json` 产出各阶段 JSON，再 `ingest_advice.py --out-json`（最小依赖、无需 mongo）证明最终 `portfolio_advice` 文档带齐富字段（industry_matrix[vitality_level/delta/go_nogo/stance]、positions_detail、asset_allocation、debate 历程）。

这真跑的是**大脑（推理 + 字段契约）**——正是出 bug 的层；不跑的是 live 数据抓取与 DB 传输（非 bug 所在，且本沙箱无环境）。生产真跑仍走部署机的 `scripts/run.sh`。

验证顺序：
1. **改前 baseline**：subagent 跑 v3 over fixture + ingest --out-json，留证富字段产出（证明 v3 大脑可用，再拆 langgraph 后路）。
2. **改后**：`node --check` / `py_compile` 全量语法检查；再 ingest --out-json 过一遍确认契约未破。

## 5. 风险

- 子进程跑 `claude -p` 需部署机有 claude 鉴权——本沙箱不可验证，只能保证代码正确 + 语法过，runtime 由部署环境承担。已在 summary 对用户明示。
- 删除 advisor_graph 若有隐藏引用 → 删前全仓 grep 确认；先标废弃再删更稳。
- `--to` / `selected_industries` 过滤改动 workflow → 改后用 fixture 跑通对应阶段。
