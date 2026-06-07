## Why

v3 是「一次 `run.sh all` 跑完 Step 0-7 的单链路全量分析」：每次都从宏观一路烧到合成，成本高、等待长，且只覆盖「权益行业 → 个股」一条线，大类资产（固收/现金/大宗/贵金属/房地产/另类）没有独立深研，结论「浅尝辄止、不敢据以调仓」。同时全量串跑意味着任何一处想刷新都要重跑整条链，无法按需深挖单个大类/行业/个股。

v4 把 v3 的「单链路阶段（stage）」升维成「**可独立调度的分析单元（unit）**」：以「最大化用户长期复利、不错失机会」为总目标，按「七大类资产 → 大类内行业 → 行业内个股」三层逐级深入，每层是一个独立「分析部门」（对立角色多轮辩论 + 部门总监拍板）。每个单元独立可触发、独立缓存、独立有新鲜度；层间靠「上游快照指纹 + stale 软提醒」保持约束链一致性而**不强制刷新**。重计算只在 CLI/本地由 claude 调起（延续 v3「子 Agent 而非 `llm.invoke()`」铁律），前端只读状态；本地运行与 AI 代跑产出同构信封、覆盖式落盘、幂等导入。

> 现状：v4 设计与任务分解已固化于 `planning/v4/layered-deep-research_prd.md` 与 `.kiro/specs/v4/{design,tasks}.md`。**Task 0（单元骨架）与 S1（资产层）已实现并落地**（`app/services/v4/*`、`scripts/{run_v4.sh,collect_v4.py,v4_unit_cli.py,workflow-v4-advisor.js,init_v4_db.py,v4_status.py}`、`agents/advisor/v4-asset-*.md` + `v4-allocation-director.md`）。本 change 把 v4 纳入 OpenSpec 治理，并驱动 **S2-S5** 余下开发。

## What Changes

- **新增（已落地，S1 + 骨架）** v4 单元化地基：`app/services/v4/{asset_classes,v4_classifier,v4_state,v4_unit_store,v4_query}.py`、CLI 入口 `scripts/run_v4.sh`（analyze/refresh/status/scan + 单元选择器）、编排器 `scripts/workflow-v4-advisor.js`、采集 `scripts/collect_v4.py`、辅助 `scripts/v4_unit_cli.py`、DB 初始化 `scripts/init_v4_db.py`、大类研究部门 6 角色 + 配置委员会总监 `agents/advisor/v4-*.md`、MongoDB `v4_units`/`v4_run_log` 集合。
- **新增（S2 待开发）** 资产配比单元 `alloc:portfolio`（Σtarget=100、允许主动归零、`equity_quota` 下传）、状态机收口（上游 version 递增 → 下游置黄 + `stale_reason`，`scan` 仅置黄不自动跑）、v4 只读路由 `app/routers/portfolio_v4.py`、前端 Tab1 七大类卡片 + 公共状态组件。
- **新增（S3 待开发）** 权益深链：行业深辩 `industry:<name>` → 行业间配比 `alloc:equity_industries`（Σ≤equity_quota）→ 独立行业内部门个股 `stock:<code>` → 行业内配比 `alloc:industry:<name>`；前端 Tab2/Tab3 表格。
- **新增（S4 待开发）** 非权益六类差异化方案 `plan:<class>`（复用大类部门范式，按类注入方案模板）。
- **新增（S5 待开发）** 双跑同构 + 幂等导入 `scripts/import_v4.py`、静态快照 `scripts/build_snapshot_v4.py`、单元级运行报告 `scripts/run_report_v4.py`。
- **不改动** v3 全链路：`scripts/workflow-v3-advisor.js`/`run.sh`、`app/services/v3_advisor_runner.py`、`app/routers/portfolio_analysis.py`、Mongo `portfolio_advice`。**v3/v4 并存**，独立集合/目录/路由/编排器，可灰度可回退。

## Capabilities

### New Capabilities

- `v4-asset-classification`: 七大类资产体系定义 + 持仓穿透归类（可交易标的 vs 持有型敞口 + 最深下钻深度）— FR-001
- `v4-asset-research-dept`: 大类逐类深度分析部门（多角色固定 3 轮辩论 + 总监拍板，逐类独立落盘）— FR-002
- `v4-asset-allocation`: 资产配比决策（Σ=100%、主动归零合法、`equity_quota` 约束下传）— FR-003
- `v4-analysis-unit`: 分层独立分析的触发机制与五色新鲜度状态机（CLI 主入口、单元独立触发、TTL、运行锁）— FR-004
- `v4-constraint-chain`: 约束链一致性校验与 stale 软提醒（上游快照指纹 + version 比对，不强制刷新、不静默修正）— FR-005
- `v4-equity-deep-chain`: 权益深链（行业深辩 → 行业间配比 → 独立部门个股分析 → 行业内资金配比）— FR-006
- `v4-non-equity-plans`: 非权益六大类差异化投资方案（按资产本质匹配下钻深度）— FR-007
- `v4-three-tab-overview`: 三层 Tab 前端（资产配置 → 大类详情 → 行业/个股，卡片 vs 表格 + 五色状态 + 软提醒）— FR-008
- `v4-dual-run-ingest`: 双跑模式与产物覆盖式落盘解析（同构信封 + 单元粒度 git JSON + 幂等 upsert）— FR-009

## Impact

**代码（新增，已落地 S1/骨架）**：
- `app/services/v4/{asset_classes,v4_classifier,v4_state,v4_unit_store,v4_query}.py`
- `scripts/{run_v4.sh,collect_v4.py,v4_unit_cli.py,workflow-v4-advisor.js,init_v4_db.py,v4_status.py}`
- `agents/advisor/v4-asset-{bull,bear,analyst-macro,analyst-flow,analyst-policy,director}.md`、`v4-allocation-director.md`

**代码（新增，S2-S5 待开发）**：
- `app/routers/portfolio_v4.py`（只读 + 导入，无任何在线触发 LLM 写接口）
- `agents/advisor/v4-{industry-bull,industry-bear,industry-director,industry-allocator,stock-bull,stock-bear,stock-director}.md`
- `app/services/v4/industry_candidates.py`
- `scripts/{import_v4.py,build_snapshot_v4.py,run_report_v4.py}`
- `frontend/src/views/Portfolio/Overview.vue`（重构为三层 Tab）+ `frontend/src/views/Portfolio/v4/{AssetAllocationTab,AssetDetailTab,IndustryDetailTab,AssetCard,IndustryTable,StockTable,PlanCard,UnitStatusBadge,EmptyUnitState}.vue`、`useV4Units.ts`

**数据**：新增 Mongo 集合 `v4_units`（`(user_id, unit_id)` 唯一索引，幂等 upsert）、`v4_run_log`；落盘 `data/v4/**/*.json` 单元信封（git 传输载体，已在 `.gitignore`）。`portfolio_advice`（v3）不动。

**不影响**：v3 全链路、`portfolio_advice` 写入者与 schema、现有 `/api/portfolio/*` 路由。

**环境约束（验证）**：本沙箱无 MongoDB/akshare/claude 鉴权，无法 live 端到端跑。代码层用 `node --check`/`py_compile`/前端 `tsc` 验证；状态机/归类/信封读写用纯函数单测验证；真跑（claude -p 驱动 v4 子 Agent + import_v4）走部署机或具 claude 鉴权环境。

<!-- Dialectical Analysis
## 方案对比

方案A（本方案：单元化 + v3/v4 并存独立集合/目录/路由）
- 优点：按需深跑省成本；单元天然解耦可独立缓存/触发；v3 零风险可回退灰度；约束链用指纹+软提醒，一致性与灵活性兼得
- 缺点：单元数膨胀（7大类+N行业+M个股）调度与状态机复杂；v3/v4 并存有维护成本

方案B（直接在 v3 链路上加缓存分段，不做单元化）
- 优点：改动小、不新建集合
- 缺点：阶段缓存仍是「线性链」，无法独立深挖单个大类/行业/个股；大类资产层（固收/大宗等）无处安放；治不了「不敢据以调仓」根因
- 结论：取 A。单元化是「分层独立深研」的本质要求，B 只是 v3 的局部优化。

方案C（v4 直接替换退役 v3）
- 优点：最干净，无并存成本
- 缺点：v4 是 staged 大重构，S2-S5 未完成期间替换会使线上组合分析失能；blast radius 极大
- 结论：否。并存 + 灰度，S5 全绿后再议是否退役 v3。

最可能失败的点：
- claude -p 驱动 v4 子 Agent 需部署机鉴权，本沙箱不可 live 验证 → 缓解：纯函数单测 + 语法过 + fixture 信封；runtime 由部署环境承担
- 非权益大类（大宗/另类）数据源缺失 → 缓解：降级「LLM 知识 + 可得行情」并 evidence 标 missing（技术约束已允许）
- 单元数膨胀导致状态机/索引性能 → 缓解：`_units.json` 索引 + 运行锁 + 只读纯函数状态计算，不连带重跑
- v3/v4 双前端入口混淆用户 → 缓解：v4 独立 Tab 视图与独立路由，灰度开关控制可见性
-->
