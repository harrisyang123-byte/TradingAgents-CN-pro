# Tasks: 退役 LangGraph，收敛到 v3 单一大脑

> 变更：`retire-langgraph-single-brain`
> 状态：**已完成** (2026-06-06)

---

## Task 0 — Baseline 真跑 ✅

用 subagent 当 LLM 驱动 v3 agent 链 over fixture dataDir，产各阶段 JSON → `ingest_advice.py --out-json` 证明 `portfolio_advice` 富字段产出。

产物在 `data/advisor_runs/fixture_baseline/` 和 `.adv_e2e/_ingested_doc.json`。

---

## Task 1 — workflow/run.sh 增加 `--to` + selected_industries 过滤 ✅

**文件**：`scripts/workflow-v3-advisor.js`、`scripts/run.sh`

- workflow 接受 `to` arg：跑到指定 stage 为止（含）后 break
- scout/pm 阶段读 `selected_industries.json`（存在则只处理勾选行业）
- run.sh 暴露 `--to <stage>`

---

## Task 2 — 新建 v3_advisor_runner 服务 ✅

**文件**：`app/services/v3_advisor_runner.py`

- `plan(user_id)`: collect_data + run.sh analyze --to industry → 返回行业列表
- `execute(user_id, run_dir, selected_industries)`: write selected → run.sh analyze → ingest

---

## Task 3 — /plan、/execute 改调 v3 ✅

**文件**：`app/routers/portfolio_analysis.py`

- 完全移除 AdvisorGraph import
- plan 端点调 v3_plan（collect + analyze --to industry）
- execute 端点调 v3_execute（write selected → analyze → ingest）
- /status、/refresh 端点保持前端兼容

---

## Task 4 — 退役 LangGraph + 清理旧入口 ✅

- `portfolio_advisor_service.py` 移除 AdvisorGraph，保留 `_prepare_tier1_reports`
- 删除 `tradingagents/graph/advisor_graph.py`
- 删除 `agents/advisor/l1~l4-*.md`（9个）
- 删除 `scripts/archived/`、`.claude/workflows/workflow-advisor.js` 等旧 workflow
- 删除 `scripts/claude-advisor.js`、`cli/claude_advisor.py`
- README 移除 LangGraph badge 和引用

---

## Task 5 — 验证 ✅

- `node --check scripts/workflow-v3-advisor.js` ✅
- `py_compile` 全部改动 .py ✅
- `ingest_advice.py --out-json` 验证富字段契约 ✅（baseline fixture 产出验证通过）

---

## 执行顺序

```
Task 0 ✅ → Task 1 ✅ → Task 2 ✅ → Task 3 ✅ → Task 4 ✅ → Task 5 ✅
```
