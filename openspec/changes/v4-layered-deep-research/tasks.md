# Tasks: v4 分层独立深度投研系统

> 变更：`v4-layered-deep-research`
> 执行模式：**staged**（Task 0 骨架 + S1~S5 五阶段，每阶段独立可用、可回归，v3 完全不动）
> 权威任务分解与 AC 覆盖矩阵见 `.kiro/specs/v4/tasks.md`；本文件为 OpenSpec change 的实现清单与进度。
> 进度：**Task 0 + S1~S5 全部已落地（编译通过）；端到端真跑待部署环境验证。**

---

## Task 0 — 单元化基础骨架 ✅

搭起 v4「分析单元」原子地基：统一信封 schema、七大类常量、落盘/索引/锁、纯只读状态机、CLI 入口、Mongo 集合。

- [x] `app/services/v4/asset_classes.py`：七大类枚举 + `max_drill_depth` + 分档 TTL（AC1.3/AC4.3）
- [x] `app/services/v4/v4_unit_store.py`：信封读写 + `_units.json` 索引 + 覆盖式只动本单元 + `_locks/` 运行锁（AC4.5/AC4.7/AC9.4 基础/NFR4.2）
- [x] `app/services/v4/v4_state.py`：五色状态机纯函数 + 复用 `stage_cache.py::_fingerprint` 做指纹/version 比对，只读不重跑（AC5.1/AC5.3/AC5.4/NFR2.1）
- [x] `scripts/run_v4.sh`：`analyze/refresh/status/scan` + 单元选择器解析 + `--portfolio-file` 透传（AC4.1/AC4.4）
- [x] `scripts/v4_unit_cli.py`：锁/信封写入/上游版本解析/指纹的辅助 CLI（供编排器 Bash 调用）
- [x] `scripts/init_v4_db.py`：`v4_units`（`(user_id,unit_id)` 唯一）+ `v4_run_log` 集合与索引（§5.6/AC9.5）
- [x] `data/v4/` 已在 `.gitignore`；信封不硬编码凭据（AC9.6/NFR5.1/NFR5.2）

**capability**：v4-analysis-unit, v4-constraint-chain（机制底座）, v4-dual-run-ingest（信封同构底座）

---

## Task 1 — S1 资产层：七大类穿透归类 + 大类研究部门（3 轮辩论）✅

- [x] `app/services/v4/v4_classifier.py`：七大类穿透归类，无法归类入 `unclassified` 不丢弃；`tradable` vs `holding_only_exposure` 分离；支持 Mongo 持仓与 `--portfolio-file`（AC1.1/1.2/1.4）
- [x] 大类研究部门 6 角色 `agents/advisor/v4-asset-{bull,bear,analyst-macro,analyst-flow,analyst-policy,director}.md`（AC2.1/2.2）
- [x] `scripts/collect_v4.py`：单大类多维输入包拼装，缺数据源降级标 missing（AC2.1）
- [x] `scripts/workflow-v4-advisor.js`：`asset:<class>` 单元路径，固定 3 轮辩论 + director 出 verdict（AC2.2/2.3）
- [x] 落盘 `data/v4/assets/<class>.json` 独立单元，覆盖式只动本单元；零持仓大类仍可触发（AC2.4/2.5/9.4）

**capability**：v4-asset-classification, v4-asset-research-dept

---

## Task 2 — S2 配比机制：资产配比 + 约束下传 + 状态机收口 + Tab1 ✅

- [x] `agents/advisor/v4-allocation-director.md`（已存在角色定义，需接入配比单元流程）：读 7 个 `asset:*` verdict → `assets[]`（current→target+action+reasoning），校验 Σtarget=100；缺失/stale 入 `input_warnings[]`；支持 `actively_zeroed`（AC3.1/3.2/3.3）
- [x] 编排器加 `alloc:portfolio` 单元：写 `equity_quota`，==0 跳过权益深链并标注；`upstream[]` 记 7 个 `asset:*`（AC3.4/3.5）
- [x] 状态机收口：上游 version 递增→下游置黄 + `stale_reason`；`run_v4.sh scan` 仅置黄不自动跑；约束传递校验仅报警不修正（AC4.2/5.2/5.5/NFR2.2）
- [x] `app/routers/portfolio_v4.py`：`GET /overview`、`GET /units/status`，响应带 status/version/upstream/stale_reason/cli_hint，走 Mongo 缓存秒级、不触发 LLM（AC4.6/NFR1.2）
- [x] 前端 `AssetAllocationTab.vue` + `AssetCard.vue`（7 卡）+ `UnitStatusBadge.vue`（五色+stale+cli_hint）+ `EmptyUnitState.vue` + `useV4Units.ts`（AC8.1/8.4/8.5/NFR3.1）

**capability**：v4-asset-allocation, v4-constraint-chain（收口）, v4-three-tab-overview（Tab1）, v4-analysis-unit（scan/状态展示）
**验证**：`analyze alloc:portfolio` Σ=100% 校验；主动归零合法；权益=0% 前端标注；改 `asset:*` 重跑后 `scan` 使配比置黄显示 stale_reason；Tab1 渲染 7 卡 + 五色 + 空态。

---

## Task 3 — S3 权益深链：行业深辩 → 行业配比 → 个股 → 行业内配比 + Tab2/3 ✅

- [x] `app/services/v4/industry_candidates.py`：内置候选行业（风口+长期主题），复用 `industry_vitality.py` 推荐；CLI 询问先分析哪些（AC6.1）
- [x] `agents/advisor/v4-industry-{bull,bear,director}.md` + 编排器 `industry:<name>` 单元：多轮辩论 + director 定方向，早于配比（AC6.2）
- [x] `agents/advisor/v4-industry-allocator.md` + `alloc:equity_industries` 单元：Σ行业权重 ≤ equity_quota，缺/stale 标注（AC6.3）
- [x] `agents/advisor/v4-stock-{bull,bear,director}.md` + `stock:<code>` 单元：每股独立分析独立缓存，产评级/目标价（AC6.4）；`alloc:industry:<name>` 单元产目标权重+买入区间（AC6.5）
- [x] upstream 链路：`industry:*` 变→`alloc:equity_industries` 黄；`alloc:equity_industries` 变→`alloc:industry:*` 黄（AC6.6）
- [x] 前端 `AssetDetailTab.vue`（权益分支）+ `IndustryTable.vue`；`IndustryDetailTab.vue` + `StockTable.vue`（AC8.2 权益/AC8.3）

**capability**：v4-equity-deep-chain, v4-three-tab-overview（Tab2/3）
**验证**：`analyze industry:<name>` 产深辩+verdict；`alloc:equity_industries` Σ≤equity_quota；`stock:<code>` 独立缓存；行业配比变→行业内配比置黄；前端 Tab2/3 表格渲染。

---

## Task 4 — S4 非权益六类：差异化投资方案 ✅

- [x] 编排器加 `plan:<class>` 单元路径：复用 `v4-asset-{bull,bear,director}`，director 按 class 注入方案模板；`upstream` = `asset:<class>` + macro（AC7.1/7.7）
- [x] 各类 payload：cash→`holding_structure[]`（AC7.2）；fixed_income→`duration_view`+`instrument_mix[]`（AC7.3）；commodity/precious_metal→`instrument_mix[]` 可交易下钻/持有型记敞口（AC7.4）；real_estate→REITs 下钻/实物记敞口+宏观建议（AC7.5）；alternative→`instrument_mix[]`+`risk_flags[]`（AC7.6）
- [x] 前端 `PlanCard.vue`：Tab2 非权益分支渲染（AC8.2 非权益）

**capability**：v4-non-equity-plans, v4-three-tab-overview（Tab2 方案视图）
**验证**：6 类各 `analyze plan:<class>` 跑通并校验各自 payload 字段；前端 Tab2 非权益方案卡片；非权益单元遵守状态机软提醒。

---

## Task 5 — S5 双跑 / 导入 / 快照 / 运行报告：本地与代跑一致 ✅

- [x] 两入口统一编排：本地（连 Mongo）/ AI 代跑（`--portfolio-file`），均产同构信封（AC9.1/NFR4.1）
- [x] `scripts/import_v4.py`：按 `(user_id,unit_id)` 幂等 upsert `$set` 整信封入 `v4_units`，重复导入不脏（AC9.5）；可选 `POST /api/portfolio/v4/import`
- [x] `scripts/build_snapshot_v4.py`：v4 单元 → `frontend/public/snapshot/v4/*.json` 同构；`useV4Units.ts` 在 `VITE_STATIC_SNAPSHOT=1` 时 fetch 快照、否则走 API（NFR4.1）
- [x] `scripts/run_report_v4.py`：单元级运行报告（停在哪/产物空否/降级与否/前端是否降级），延续 v3「保证看得见」（NFR3.2）

**capability**：v4-dual-run-ingest
**验证**：同份 holdings.json 走本地+代跑比对信封 schema 一致；`import_v4.py` 重复导入幂等；`VITE_STATIC_SNAPSHOT=1` 下前端与 API 一致；`run_report_v4.py` 对成功/失败/降级目录均产可读报告。

---

## 执行顺序

```
Task 0 ✅ → S1 ✅ → S2 ✅ → S3 ✅ → S4 ✅ → S5 ✅
（S4 依赖 S1 部门范式 + S2 的 Tab2 框架；S5 建议在 S3/S4 单元齐备后做端到端一致性验证）
```

## 验证策略（沙箱约束）

本沙箱无 MongoDB/akshare/claude 鉴权，无法 live 端到端跑。各阶段验证：
- Python 改动：`py_compile` + `v4_state`/`v4_classifier`/信封读写纯函数单测
- 编排器：`node --check scripts/workflow-v4-advisor.js`
- 前端：`tsc` / 组件渲染检查
- 真跑（claude -p 驱动 v4 子 Agent + `import_v4`）：走部署机或具 claude 鉴权环境
