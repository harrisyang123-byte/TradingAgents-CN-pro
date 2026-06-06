# v3 大类资产配置层 落地计划

> 状态：**待确认**（方向已拍板，等 HTML 原型确认后开工）
> 最近更新：2026-06-06
> 配套原型：`docs/mockups/overview-asset-allocation-mockup.html`

本文件固化本轮讨论结论与分期方案，防止上下文遗忘。

---

## 1. 背景与已确认的事实（均有代码/数据佐证）

### 1.1 现在没有真正的「大类资产层」

`data/advisor_runs/*/capital_plan.json` 实锤：只有 `invested_weight`(73%) vs `cash_weight`(27%) 一个二分，
`allocations[]` 把 **债券 / 黄金 / QDII海外 / 宽基 / 行业ETF** 和 **科技 / 医药 / 消费** 平铺成同级「行业」。
→ 概念混淆：把大类资产塞进「行业」这个筐凑数，没有战略层的大类目标配比。

### 1.2 辩论历程几乎不展示（两个断点）

- **前端用错组件**：`frontend/src/views/Portfolio/Overview.vue` 的「分析师辩论历程」把
  `market_debate_history` 等三段纯文本直接塞进 `<pre>`，而项目里**已有做好的气泡组件**
  `frontend/src/components/Analysis/DebateTimeline.vue`（🐂多头/🐻空头/⚖️裁判 左右气泡 + Markdown），**Overview 没用它**。
- **落库链路断**：用户库里 advice 文档无 `debate_history` 字段（截图「暂无市场研判记录」）。
  `scripts/ingest_advice.py::_assemble_debates`（169 行）能把 研究员/反向者 + PM激进/保守 + 风控悲观/乐观
  拼成文本，`build_doc`(385 行) 也合并了——但旧文档是更早版本跑的，或 stage 文件没落全。
- **结论**：12-agent 辩论数据在 workflow 里真实产生（`all_researchers.json` / `pm_results.json` /
  `portfolio_contrarian.json` / 风控 verdict 都在 `data/advisor_runs/` 里），只是落库 + 渲染两端断了。

---

## 2. 已拍板的方向（用户确认）

1. **基金按底层穿透**：基金归类时穿透到底层资产（黄金ETF→黄金大类；纳指QDII→海外大类；蓝筹基金→股票→行业）。穿透在分类层做一次，上层只消费结果。
2. **大类配比由 agent 真实产出**：要有数据、有方法论的多方辩论（战略配置师 vs 防御配置师 vs 大类裁判），不是凑数值。
3. **行业矩阵收口**：剔除现金/债券/黄金/海外，只留真行业，并标注「股票大类内部细分（合计=股票目标%）」。
4. **下钻体验一致**：大类行与行业行统一右滑 Drawer——黄金→黄金ETF处方、债券→债基处方、股票→行业分布、行业→个股处方。买入价位/批次复用现有 `positions_detail` 结构，不另造交互。

### 大类口径（6 类）

`现金 / 债券 / 股票 / 黄金 / 海外(QDII) / 其他`。`股票` 目标% = `total_weight_limit`，硬约束下传行业层。

---

## 3. 分期方案（推荐 1 → 2 → 3，每期独立可用）

### 阶段 1：修辩论展示（零风险、最快见效，不动 agent 链路）

**目标**：让现有 12-agent 辩论在页面看得见。

| 改动 | 文件 |
|---|---|
| `Overview.vue` 辩论区从 `<pre>` 换成 `<DebateTimeline :history-data="..."/>` | `frontend/src/views/Portfolio/Overview.vue` |
| 校验 `_assemble_debates` 落库链路，确认三段 `*_debate_history` 真写入文档 | `scripts/ingest_advice.py` |
| 必要时让 `DebateTimeline` 角色正则覆盖中文角色名（研究员/反向者/PM/裁判/风控） | `frontend/src/components/Analysis/DebateTimeline.vue` |

**验证**：`npx vue-tsc --noEmit`（前端）；用 `data/advisor_runs/` 现成产物跑 `ingest_advice.py --out-json` 看三段非空。

### 阶段 2：大类配置辩论 agent（核心，agent 链路）

**目标**：`capital_plan.json` 产出真正的大类目标配比（含辩论历程）。

| 改动 | 文件 |
|---|---|
| 新增大类配置辩论 agent 定义：战略配置师 / 防御配置师 / 大类裁判 | `agents/advisor/v3-asset-strategist.md` / `v3-asset-defender.md` / `v3-asset-judge.md` |
| 编排器新增 `asset` 阶段：在 macro 之后、industry 之前，产出 `asset_allocation.json`（6 大类现状→目标 + 理由 + 辩论文本） | `scripts/workflow-v3-advisor.js`（+ `.claude/workflows/` 副本同步） |
| 股票额度下传：`股票目标%` → `total_weight_limit`，行业层只在该额度内分配 | `scripts/workflow-v3-advisor.js` / 跨行业裁判输入 |
| 基金底层穿透分类（黄金/债券/海外/股票归类） | `app/services/industry_classifier.py`（复用/扩展） |
| ingest 把 `asset_allocation.json` 映射进 advice 文档（新增 `asset_allocation` 字段 + `asset_debate_history`） | `scripts/ingest_advice.py` |
| `AdvisorState` 增加大类约束字段（如需） | `tradingagents/agents/advisors/advisor_states.py` |

**方法论（写进 agent prompt）**：输入 PMI/利率/北向/PE分位/股债利差（`market_signals` / `data_macro` 已有）；
战略师偏进攻（加股票/黄金对冲），防御师偏避险（保现金/债券压舱）；裁判取折中并满足 `现金 ≥ cash_floor`、`股票 = total_weight_limit`。

**验证**：`node --check`、`python -m py_compile`；跑一遍真数据确认 `asset_allocation.json` 6 类 target 之和=100。

### 阶段 3：前端总揽卡片 + 行业收口（依赖阶段 2 产物）

| 改动 | 文件 |
|---|---|
| 新增「资产配比总揽」卡片：现状/目标堆叠条 + 大类表 + 下钻 | `frontend/src/views/Portfolio/Overview.vue`（+ 可拆 `AssetAllocationCard.vue`） |
| 行业矩阵 `filteredMatrix` 增加剔除规则：排除 现金/债券/黄金/海外/QDII | `frontend/src/views/Portfolio/Overview.vue` |
| 行业矩阵头部加提示「股票大类内部细分」 | 同上 |
| Drawer 统一支持「大类下钻」：黄金/债券/海外→标的处方，股票→行业分布 | 同上 |
| `api/paper.ts` / 后端 overview 契约增加 `asset_allocation` 返回 | `frontend/src/api/paper.ts` / `app/routers/portfolio_analysis.py` 或 `paper.py` |

**验证**：`npx vue-tsc --noEmit`；对照 `overview-asset-allocation-mockup.html` 核对交互。

---

## 4. 风险与边界

- 阶段 2 动 agent 链路与编排器，是本特性最重的部分；阶段 1/3 主要是前端 + 落库，风险低。
- `total_weight_limit` 现由宏观裁判产出，阶段 2 后改为「大类裁判」产出，需确认两者不冲突（建议宏观给区间、大类裁判定值）。
- 行业矩阵收口后，旧 advice 文档（无 `asset_allocation`）要能降级显示，不能白屏。
- `.claude/workflows/` 与 `scripts/` 双副本必须同步（见编排器计划 §4）。

---

## 5. 待确认项（开工前）

1. HTML 原型 `overview-asset-allocation-mockup.html` 的布局/交互是否 OK？
2. 先做哪一期？（推荐 1 → 2 → 3）
3. 大类口径是否就用 6 类（现金/债券/股票/黄金/海外/其他），还是要再拆（如把「商品」从黄金独立）？
