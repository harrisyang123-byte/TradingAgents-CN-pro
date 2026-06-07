# Tasks: v4 共享数据采集台（取数/辩论分离）

> 变更：`v4-shared-data-desk`
> 执行模式：staged（叠加在 `v4-layered-deep-research` 之上；不改单元信封/状态机/三层 Tab/v3）
> 权威设计：`.kiro/specs/v4/design.md §5.8`；规范架构图：`docs/wiki/v4-architecture.md §3`。
> 进度：文档 + Agent 定义已落地；编排器接入与 collect 退化为代码改动，需部署机端到端验证。

---

## Task 1 — 文档与架构定稿 ✅

- [x] `docs/wiki/v4-architecture.md`：抽出通用能力层，§3 列 7 个共享能力，§3.1 两档取数（A 全局共读 / B 单元深取）
- [x] `.kiro/specs/v4/design.md §5.3`：角色表新增 `v4-data-desk` 行 + 「取数/辩论分离」note（14 辩论 Agent Read-only）
- [x] `.kiro/specs/v4/design.md §5.8`：新增详细设计（矛盾/两档/`data_macro.json` schema/编排器 ensureDataDesk 接入/collect 退化/agent 契约）
- [x] `.kiro/specs/v4/design.md §七/§八`：文件结构加 data-desk + collect 退化；降级风险条改为 data-desk 联网兜底

**capability**：v4-data-desk（设计）, v4-asset-research-dept（取数职责修订）

---

## Task 2 — 新增 `v4-data-desk` Agent 定义 ✅

- [x] `agents/advisor/v4-data-desk.md`：frontmatter `tools: [Read, web_search, web_fetch]`（唯一带 web 的 v4 Agent）
- [x] 两档取数说明（档 A 全局公共指标清单 + 来源优先级；档 B 按单元类型深取）
- [x] 档 A 新鲜度短路（读 `data_macro.json` 的 `fetched_at`+`ttl_hours`，新鲜则 `action:"reused"` 不联网）
- [x] 输出严格 JSON schema（档 A `indicators{status,source_url}` + `evidence[]`；档 B `desk_data`）
- [x] 凭据铁律：verified+URL / missing 二选一，严禁编造；只取数不研判；无网整体 unavailable 不阻断

**capability**：v4-data-desk

---

## Task 3 — 编排器接入 `ensureDataDesk` ⬜

- [ ] `scripts/workflow-v4-advisor.js`：新增 `ensureDataDesk(sel)`，在 `main()` 调具体部门前执行
- [ ] 档 A：检查 `inputs/data_macro.json` 新鲜度 → 缺失/过期则 `agent('v4-data-desk', {tier:'global', data_dir})` → 写文件；新鲜则跳过
- [ ] 档 B：按 `sel.type` 调 `agent('v4-data-desk', {tier:'unit', selector, data_dir})` → 合并 `desk_*` 进 `inputs/<单元>.json`；`alloc:*` 单元只确保档 A 新鲜
- [ ] 其余 Read-only 辩论 `agent()` 调用保持不变
- [ ] run_report 接入：无 web/取数失败时标注「宏观未联网核实」，不阻断

**capability**：v4-data-desk（接入）
**验证**：`node --check scripts/workflow-v4-advisor.js`；部署机跑 `analyze asset:equity` 确认 data_macro.json 被 data-desk 填且 evidence 带 URL；二次跑命中新鲜度短路。

---

## Task 4 — collect_v4.py 职责退化 ⬜

- [ ] `scripts/collect_v4.py`：`build_macro_snapshot()` 改为只写占位 `{"source":"pending_data_desk","data_availability":"pending",...}`（保留 `needs_fetch` 回落兼容）
- [ ] `_build_industry_pack` / `_build_stock_pack`：best-effort 联网抓取（景气/基本面）改为只拼骨架字段占位，真实数据交 data-desk 档 B 填
- [ ] 保留 `classify_holdings` 穿透归类不变；确保 stage1 纯 Python、零网络、永远成功

**capability**：v4-asset-research-dept（取数职责修订）
**验证**：`python3 -m py_compile scripts/collect_v4.py`；跑 `collect_v4.py --selector asset:equity --portfolio-file …` 确认无网络调用、输出骨架包 + 占位 macro。

---

## Task 5 — 验证与一致性 ⬜

- [ ] `node --check scripts/workflow-v4-advisor.js`、`py_compile scripts/collect_v4.py` 通过
- [ ] 部署机（具 claude 鉴权 + 联网）端到端：`analyze asset:equity` → data-desk 取数 verified → 辩论 Read 同一份 macro → 信封 evidence 继承 URL
- [ ] 无 web 环境回落：collect 占位 + run_report 标注，辩论不阻断
- [ ] 文档与代码一致性复核（design §5.8 ↔ 编排器 ensureDataDesk ↔ data_macro.json 实际字段）

**capability**：v4-data-desk, v4-asset-research-dept

---

## 执行顺序

```
Task 1 ✅（文档）→ Task 2 ✅（Agent）→ Task 3 ⬜（编排器接入）→ Task 4 ⬜（collect 退化）→ Task 5 ⬜（验证）
```

## 验证策略（沙箱约束）

本沙箱无 claude 鉴权 / web 工具，无法 live 验证联网取数。代码改动用 `node --check` + `py_compile` 静态验证；Agent 契约 + 两档取数 + 新鲜度短路的运行时行为由部署机端到端承担；无网回落路径保证不阻断辩论。
