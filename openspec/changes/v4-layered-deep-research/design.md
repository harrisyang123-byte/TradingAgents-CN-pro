# v4 分层独立深度投研系统 — 技术方案（OpenSpec change 摘要）

> 本文件是 OpenSpec change 内的精炼设计摘要。**完整权威设计**见 `.kiro/specs/v4/design.md`（含 AC→设计逐条追溯、Mermaid 架构/状态机、各 payload schema、文件结构）。需求全文见 `planning/v4/layered-deep-research_prd.md`。
> 设计铁律延续 v3：所有 LLM 决策走 `.md` 子 Agent + Workflow 编排（claude -p 驱动），Python 不直接 `llm.invoke()`；运行态存 MongoDB，git 传输用单元粒度 JSON。技术栈沿用（FastAPI + Vue3 + MongoDB），未新增框架。

## 核心抽象：分析单元（Analysis Unit）

v4 的一切围绕「分析单元」——触发、缓存、落盘、状态、约束链的最小原子。单元类型与稳定 ID：

| 单元类型 | unit_id 格式 | 部门 | 对应 capability |
|----------|-------------|------|-----------------|
| 大类分析 | `asset:<class>` | 大类研究部门 | v4-asset-research-dept |
| 资产配比 | `alloc:portfolio` | 资产配置委员会 | v4-asset-allocation |
| 行业深辩 | `industry:<name>` | 行业研究部门 | v4-equity-deep-chain |
| 行业间配比 | `alloc:equity_industries` | 行业配置团队 | v4-equity-deep-chain |
| 个股分析 | `stock:<code>` | 行业内研究部门 | v4-equity-deep-chain |
| 行业内配比 | `alloc:industry:<name>` | 行业内研究部门 | v4-equity-deep-chain |
| 非权益方案 | `plan:<class>` | 大类研究部门（复用） | v4-non-equity-plans |

七大类 `class` 枚举（固定）：`equity` / `fixed_income` / `cash` / `commodity` / `precious_metal` / `real_estate` / `alternative`。

## 统一单元信封（FR-009 同构核心 + FR-005 指纹）

每单元一个稳定路径 JSON，外壳统一、payload 按类型差异化：`unit_id`（upsert 主键）、`unit_type`、`schema_version`、`version`（每次重跑 +1，下游引用此号判 stale）、`fingerprint`（输入指纹，复用 `stage_cache.py::_fingerprint`）、`upstream[]`（依据的上游 `{unit_id,version,fingerprint}`）、`status`（gray/blue/green/yellow/red，运行态纯函数计算）、`ttl_days`、`generated_at`、`run_mode`（local/ai_proxy，仅元信息）、`error`、`payload`。

## 状态机（FR-004/FR-005）

`v4_state.py` 纯只读函数判定五色：文件无→gray；有锁无产物→blue；`error`→red；`now-generated_at>ttl`→yellow；任一 `upstream[i].version < 上游当前 version`（或指纹不匹配）→yellow + `stale_reason`；否则 green。**只提醒不自动跑**（AC5.3），约束数值（`equity_quota` 等）发现来自过时上游仅报警不修正（AC5.5）。

## 触发链路分离（FR-004）

重计算（LLM 子 Agent 深跑）只在 CLI/本地由 claude 调起：自然语言 → AI 解析 → `scripts/run_v4.sh <verb> <unit-selector>`；前端只读状态与产物，后端 `portfolio_v4.py` 仅提供「读取/状态/导入」，**无任何在线触发 LLM 写接口**。

## v3/v4 关系决策：并存

v4 用独立集合 `v4_units`、独立目录 `data/v4/`、独立编排器 `workflow-v4-advisor.js`、独立路由 `portfolio_v4.py`；v3 链路（`portfolio_advice`、`workflow-v3-advisor.js`、`portfolio_analysis.py`）完全不动。可灰度切换、可回退。S5 全绿后再议是否退役 v3（不在本 change 范围）。

## 分阶段落地（staged）与当前进度

| 阶段 | 范围 | 状态 |
|------|------|------|
| Task 0 | 单元骨架：信封/七大类常量/落盘索引锁/纯函数状态机/CLI 入口/Mongo 集合 | ✅ 已实现 |
| S1 | FR-001 穿透归类 + FR-002 大类研究部门（3 轮辩论） | ✅ 已实现 |
| S2 | FR-003 资产配比 + equity_quota 下传 + 状态机收口 + Tab1 | ⬜ 待开发 |
| S3 | FR-006 权益深链（行业深辩→配比→个股→行业内配比）+ Tab2/3 | ⬜ 待开发 |
| S4 | FR-007 非权益六类差异化方案 + Tab2 方案视图 | ⬜ 待开发 |
| S5 | FR-009 import/快照/run_report + AI 代跑双跑一致 | ⬜ 待开发 |

## 关键设计风险与权衡

- 单元数膨胀调度复杂 → 单元化天然解耦，编排器只跑被选单元 + `_units.json` 索引 + 运行锁。
- 非权益数据源缺失（大宗/另类）→ 降级「LLM 知识 + 可得行情」并 evidence 标 missing。
- 跨单元约束一致性 → upstream 指纹 + version 比对，stale 软提醒，不自动改数值。
- v3/v4 并存维护成本 → 独立集合/目录/路由/编排器，互不干扰。
- CLI 自然语言解析歧义 → 提供等价显式脚本命令兜底（`run_v4.sh` 子命令）。
