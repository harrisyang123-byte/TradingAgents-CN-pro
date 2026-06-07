# v4 共享数据采集台（取数/辩论分离）— 技术方案（OpenSpec change 摘要）

> 本文件是 OpenSpec change 内的精炼设计摘要。**完整权威设计**见 `.kiro/specs/v4/design.md §5.8`（通用能力层与数据采集台）。**规范架构图**见 `docs/wiki/v4-architecture.md`（§3 通用能力层 + §3.1 两档取数）。
> 设计铁律延续 v3/v4：LLM 决策走 `.md` 子 Agent + Workflow 编排，Python 不直接 `llm.invoke()`；存储/锁/指纹走 `v4_unit_cli.py`。技术栈未新增框架。

## 核心思路：取数与辩论分离（借鉴 TradingAgents Analyst/Researcher 分层）

```
v4-data-desk（唯一带 web 工具，取数）
   ├─ 档A 全局公共指标（run 级取一次，全单元同源共读）→ inputs/data_macro.json
   └─ 档B 单元级深取（按需多次）                     → inputs/<单元>.json 的 desk_* 字段
        ↓ 落盘
14 个辩论/分析 Agent（tools:[Read]，只读输入包，不联网）→ 多空 3 轮辩论 + 总监拍板
```

## 两档取数

| 档 | 范围 | 时机 | 一致性/成本意义 |
|----|------|------|----------------|
| A 全局公共指标 | LPR/逆回购/CPI/PMI/北向/汇率/原油/金价/10Y 国债（约十项） | run 起手取一次；`data_macro.json` 在 `ttl_hours` 内复用 | 全单元同源共读，约束链一致性由构造保证；消除 N 倍重复取数 |
| B 单元级深取 | 行业景气/估值、收益率曲线/信用利差、财报/资金流… | 触发该单元时、单元内可多次 | 重活在此，逐单元深度按需，不一次抓完全宇宙 |

## `data_macro.json` schema 升级（向后兼容）

新增 `fetched_at` / `ttl_hours` / 逐指标 `{value,as_of,status,source_url}` / `evidence[]`；`source` 取值扩展 `v4-data-desk`（兼容旧 `needs_fetch` 占位）。`data_availability ∈ {available, partial, unavailable}`。详见 design §5.8.3。

## 编排器接入点

`workflow-v4-advisor.js` 的 `main()` 在跑部门前插 `ensureDataDesk(sel)`：
- 档 A：`data_macro.json` 缺失/过期 → 调 `v4-data-desk`(tier=global) → 写文件；新鲜则短路复用。
- 档 B：按 `sel.type` 调 `v4-data-desk`(tier=unit) → 合并 `desk_*` 进单元输入包；`alloc:*` 单元只确保档 A 新鲜、不需档 B。
- 这是编排器内唯一调用带 web 工具 Agent 的地方；其余 Read-only 辩论 `agent()` 调用不变。

## collect_v4.py 职责退化

退化为纯 Python「持仓穿透归类 + 拼输入包骨架」（零网络、永远成功）；联网取数（宏观/景气/个股基本面）移交 data-desk。collect 仅写 `data_macro.json` 占位 `source:"pending_data_desk"`。

## 降级策略（不再静默 missing）

data-desk 联网兜底：取到标 `verified`+`source_url`；取不到才 `missing`（`value:null`+note），**严禁编造/套用示例**。无 web 工具环境 → 整体 `unavailable` + run_report 标注「宏观未联网核实」，**不阻断**后续辩论（降级而非崩溃）。

## 兼容与回落

- 叠加在 `v4-layered-deep-research` 之上，不改单元信封/状态机/约束链/三层 Tab/v3。
- data-desk 落地前或无 web 环境：编排器回落「collect best-effort + needs_fetch 占位」旧路径，不阻断。

## 关键风险与权衡

- data-desk 单点（取数失败影响所有下游）→ 逐指标 missing 容错 + 无网降级不阻断。
- 档 A 跨 CLI 进程共享 → `fetched_at`+`ttl_hours` 新鲜度短路实现「同源共读」。
- 联网取不到官方读数 → 来源优先级（官方→主流财经页）+ 宁缺毋假标 missing。
- data-desk 越权研判 → 契约铁律「只取数不研判」+ 输出 schema 无 stance/target_price。
