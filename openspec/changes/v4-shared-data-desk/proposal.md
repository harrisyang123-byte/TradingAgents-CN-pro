## Why

v4 落地后暴露一个结构性矛盾：**14 个辩论/分析 Agent（`v4-asset-*`/`v4-industry-*`/`v4-stock-*`）全部 `tools: [Read]`，却被 prompt 要求「数据缺失时自行联网补齐」——这是空头支票，它们根本没有 web 工具。** 同时，每个大类/行业/个股 Agent 都各自解读宏观（LPR/CPI/北向…），N 个单元重复取同一份公共指标，且各单元读到的数值可能对不齐，直接破坏 v4 最看重的「约束链一致性」。当 `akshare`/Mongo 在运行环境缺失时，现状是 `collect_v4.py` 把宏观标 `needs_fetch`/`missing` 后静默降级，分析「浅尝辄止、不敢据以调仓」。

借鉴 [TauricResearch/TradingAgents](https://github.com/TauricResearch/TradingAgents) 的 **Analyst-toolkit / Researcher-debate 分层**，本 change 把「取数」与「辩论」彻底分离：抽出一个**通用能力层**，新增**唯一带联网工具的 `v4-data-desk` Agent** 集中取数，14 个辩论 Agent 维持 Read-only 只消费输入包。取数分两档——**档 A 全局公共指标 run 级取一次、全单元同源共读**（一致性由构造保证），**档 B 单元级深取按需多次**（重活在此）。这同时解掉了「联网空头支票」「宏观重复且不一致」「缺数据源即静默降级」三个问题。

> 现状：架构优化已固化于 `docs/wiki/v4-architecture.md`（规范架构图）与 `.kiro/specs/v4/design.md §5.8`（详细设计）。本 change 把该重构纳入 OpenSpec 治理并驱动实现。它**叠加在** `v4-layered-deep-research`（FR-001~009 单元化地基）之上，不推翻其单元/信封/状态机设计。

## What Changes

- **新增** 通用能力层数据采集台 `agents/advisor/v4-data-desk.md`——v4 中**唯一**带 `web_search`/`web_fetch` 的 Agent。两档取数：档 A 全局公共指标（LPR/逆回购/CPI/PMI/北向/汇率/原油/金价/10Y 国债，run 级取一次，`data_macro.json` 带 `fetched_at`+`ttl_hours` 在 TTL 内复用）；档 B 单元级深取（行业景气/估值、收益率曲线/信用利差、财报/资金流等，按需多次）。每个数字带 `status`(verified/missing) + `source_url`。
- **改动** 编排器 `scripts/workflow-v4-advisor.js`：`main()` 跑部门前插入 `ensureDataDesk(sel)` 阶段（档 A 新鲜度短路 + 档 B 按单元深取），写 `inputs/data_macro.json` 与 `inputs/<单元>.json` 的 `desk_*` 字段；其余 Read-only 辩论 `agent()` 调用**一行不改**。
- **改动** 采集 `scripts/collect_v4.py`：从「取数 + 拼包」退化为「持仓穿透归类 + 拼输入包骨架」纯 Python（零网络、永远成功）；`build_macro_snapshot()` 及行业/个股 best-effort 联网抓取移交 data-desk，collect 仅写 `data_macro.json` 占位（`source: "pending_data_desk"`，兼容回落 `needs_fetch`）。
- **改动（降级策略）** 缺数据源不再静默标 missing/编造：data-desk 联网兜底，取到标 `verified`+URL；取不到才 `missing` 并显式提示；无 web 工具时整体 `unavailable` 且 run_report 标注「宏观未联网核实」，**不阻断**辩论。
- **不改动** 14 个辩论/分析 Agent 的角色逻辑与 `tools: [Read]`；不改单元信封 schema、五色状态机、约束链指纹、三层 Tab 前端、v3 全链路。

## Capabilities

### New Capabilities

- `v4-data-desk`: 通用能力层数据采集台 —— 唯一带联网工具的共享取数 Agent，两档取数（全局公共指标同源共读 + 单元级深取）、凭据契约（verified+URL / missing，严禁编造）、只取数不研判、新鲜度短路复用、无网降级不阻断。

### Modified Capabilities

- `v4-asset-research-dept`: 取数职责从「各 Agent 自行联网/collect best-effort 降级标 missing」改为「**辩论 Agent 维持 Read-only、只消费 data-desk 输入包；缺数据由 data-desk 联网兜底，取不到才 missing 且不静默降级**」。多维输入包来源由 collect_v4 拼骨架 + data-desk 填真实数据。

## Impact

**代码（新增）**：
- `agents/advisor/v4-data-desk.md`（唯一带 `web_search`/`web_fetch`）

**代码（改动）**：
- `scripts/workflow-v4-advisor.js`（新增 `ensureDataDesk` 阶段 + 档 A 新鲜度短路）
- `scripts/collect_v4.py`（退化为归类 + 拼骨架；`data_macro.json` 占位）

**文档（已更新）**：
- `docs/wiki/v4-architecture.md`（§3 通用能力层 + §3.1 两档取数，规范架构图）
- `.kiro/specs/v4/design.md`（§5.3 角色表加 data-desk + 取数/辩论分离 note；新增 §5.8；§七 文件结构；§八 降级风险）

**数据**：`inputs/data_macro.json` schema 升级（加 `fetched_at`/`ttl_hours`/逐指标 `status`+`source_url`/`evidence`），属 stage1 中间产物（`data/v4/inputs/` 已 gitignore），不影响单元信封 schema 与 Mongo 集合。

**不影响**：v4 单元信封/状态机/约束链/三层 Tab；v3 全链路；`v4_units`/`v4_run_log` 集合结构。

**环境约束（验证）**：本沙箱无 claude 鉴权/web 工具 live 跑。代码层用 `node --check scripts/workflow-v4-advisor.js` + `py_compile scripts/collect_v4.py` 验证；Agent 契约 + 编排器接入逻辑由部署机（具 claude 鉴权 + 联网）端到端验证；无网时回落路径保证不阻断。

<!-- Dialectical Analysis
## 方案对比

方案A（本方案：抽通用能力层 + 唯一带 web 的 v4-data-desk，两档取数）
- 优点：取数集中消除 N 倍重复；档 A 同源共读使约束链一致性由构造保证；解掉「Read-only Agent 被要求联网」的空头支票；联网兜底不再静默降级；14 个辩论 Agent 零改动；契合 TradingAgents 经过验证的 Analyst/Researcher 分层
- 缺点：编排器多一个 ensureDataDesk 阶段；data-desk 取数失败会影响所有下游（单点）→ 缓解：无网降级不阻断 + 逐指标 missing 容错

方案B（给每个辩论 Agent 都开 web 工具，各自取数）
- 优点：改动局部，不需新 Agent
- 缺点：N 个单元重复取同一份宏观、读数对不齐破坏一致性；成本翻 N 倍；14 个 Agent 都要改 tools + prompt；与「取数/辩论分离」背道而驰
- 结论：否。重复与不一致正是要消除的根因。

方案C（维持现状：collect_v4 best-effort + 缺则 missing 降级）
- 优点：零改动
- 缺点：缺数据源即降级，分析「浅尝辄止」；用户明确要求「不许降级、想办法联网」未满足
- 结论：否。这正是本 change 要修的问题。

最可能失败的点：
- data-desk 联网取不到官方读数 → 缓解：来源优先级（官方→主流财经页）+ 取不到标 missing 不编造，下游据 status 降级
- 档 A「run 级一次」在 CLI 单元粒度下跨进程共享 → 缓解：data_macro.json 带 fetched_at+ttl_hours，启动先查新鲜度，新鲜则复用
- 无 web 工具环境（如纯 claude -p 无联网）→ 缓解：整体 unavailable + run_report 标注 + 回落 collect needs_fetch 占位，不阻断辩论
- data-desk 越权做投资研判 → 缓解：agent 契约铁律「只取数不研判」+ 输出 schema 不含 stance/target_price
-->
