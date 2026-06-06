# v3 大类资产配置层 落地计划

> 状态：**已确认开工**（v3.2 原型已确认，按 阶段1 → 2 → 3 实施）
> 最近更新：2026-06-06
> 配套原型：`docs/mockups/overview-asset-allocation-mockup.html`（v3.2）

本文件固化本轮讨论结论与分期方案，防止上下文遗忘。

---

## 0. v3.2 原型已锁定的决策（用户确认，开工基线）

以下决策已通过 mockup v3.2 与用户对齐，作为实施基线，不再回头讨论：

1. **大类口径 = 6 类**：`现金 / 债券 / 股票 / 黄金 / 海外(QDII) / 其他`。`股票` 目标% = `total_weight_limit`，硬约束下传行业层。
2. **顶部统计卡**：总资产 / 股票仓位(现→目标) / 现金(现→目标，标注 ≥floor) / 数据质量。
3. **股票大类点击 = 滚动 + 高亮下方完整行业矩阵**（不再开「偷工减料」的精简抽屉）；
   黄金/债券/海外(QDII) 才开 Drawer 看标的处方；现金/其他 不可下钻。**消除「下钻 vs 矩阵」信息不一致。**
4. **个股处方表「每行可展开」= Tier1 选股依据卡**：核心逻辑(多头) / 主要风险(空头) / 评级 / 目标价 / 分批计划 / 建仓策略 / PE分位 / 取数时间。
   主行 = 怎么买（第一眼清晰），展开 = 为什么买（要深入能深入）。
5. **辩论历程加「数据凭据条」**：每个 agent 气泡标注取到了哪些数据（✓ 已取）、哪些没取到（✗ 缺失，**标红不掩盖**），点「查看依据」展开具体数值。
6. **Drawer 统一宽度 60%**（原 520px 偏窄），大类下钻与行业下钻共用同一 Drawer 组件。
7. **诚实原则（贯穿全程）**：UI 每个值都要能追溯到真实分析判断；agent 没产出的格子显示「未分析/数据不足」，**绝不靠默认值/补算凑数**。

### 数据现状盘点（真实可用 vs 需新增）

| 展示项 | 字段 | 现状 |
|---|---|---|
| 个股 操作/仓位/调仓金额 | `action/current_weight/target_weight/amount` | ✅ ingest 已映射 |
| 个股 买入区间/建仓策略/分批计划 | `entry_price_range/build_strategy(timing)/batch_plan` | ✅ ingest 已映射 |
| 个股 PE分位 | `pe_data.pe_percentile_5y` | ✅ ingest 已映射（agent 有输出才有） |
| 个股 核心逻辑/风险 | `reasoning` / `risk_note` | ✅ 已落库（映射为 Tier1 卡 多头/空头） |
| 个股 **评级** | `tier1_rating` | ⚠️ 类型已有，**ingest 未映射** → 阶段3 ingest 补 |
| 个股 **目标价** | `target_price` | ❌ **全链路缺字段** → 阶段3 agent/ingest 新增（缺则显示「未给目标价」） |
| 行业 景气/操作/变动 | `vitality_level/go_nogo/delta` | ✅ ingest 三级回退已映射 |
| **大类 6 类配比** | `asset_allocation` | ❌ **不存在**（现仅 invested/cash 二分）→ 阶段2 新增 |
| **辩论气泡** | `*_debate_history` | ⚠️ 有文本但 `【角色】` 标记 DebateTimeline 正则解析不出气泡 → 阶段1 改前缀格式 |
| **辩论数据凭据 prov** | （无） | ❌ agent 未结构化输出取数情况 → 阶段2 随大类辩论一并补，旧数据降级隐藏凭据条 |

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

**目标**：让现有 12-agent 辩论在页面看得见（用户问题①）。

| 改动 | 文件 |
|---|---|
| `Overview.vue` 辩论区从 `<pre>` 换成 `<DebateTimeline :history-data="..."/>` | `frontend/src/views/Portfolio/Overview.vue` |
| `_assemble_debates` 输出改为 **`角色名：内容`** 行前缀格式（DebateTimeline 正则按 `名[:：]` 切气泡），原 `【角色】` 标记解析不出气泡只会落到 fallback | `scripts/ingest_advice.py` |
| `DebateTimeline` 角色正则补充中文角色：宏观裁判/行业研究员/反向者/跨行业裁判/激进PM/保守PM/PM裁判/悲观风险/乐观风险/风控裁判/Synthesizer/战略配置师/防御配置师/大类裁判，并归到 多头(左)/空头(右)/裁判(中) 三类对齐 | `frontend/src/components/Analysis/DebateTimeline.vue` |

> **数据凭据条（prov ✓/✗）属阶段2**：现有 agent 未结构化输出取数情况，阶段1 先不做，避免凭空造「✓」。旧文档无 prov 时凭据条整体隐藏（降级），不显示假凭据。

**验证**：`npx vue-tsc --noEmit`（前端）；用 `data/advisor_runs/` 现成产物跑 `ingest_advice.py --out-json` 看三段非空且角色前缀可被正则命中。

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

## 5. 已敲定（开工基线，不再回头）

1. ✅ 原型 `overview-asset-allocation-mockup.html`（v3.2）布局/交互 OK。
2. ✅ 实施顺序：阶段 1 → 2 → 3（每期独立可用、可验证）。
3. ✅ 大类口径 = 6 类（现金/债券/股票/黄金/海外/其他），不再细拆。

## 6. 阶段2/3 新增字段的数据缺口处理（诚实原则落地）

- **`asset_allocation`（6 大类现状→目标）**：阶段2 由大类裁判 agent 真实产出；ingest 写入 advice 文档。
  旧文档无此字段时，前端「资产配比总揽」卡降级为「由持仓聚合的现状条（无 agent 目标）」或显示「未生成大类配置」，不编造目标值。
- **`target_price`（个股目标价）**：阶段3 agent 输出 + ingest 映射；agent 未给则前端显示「未给目标价」，不补算。
- **`tier1_rating`（评级）**：类型已存在，阶段3 ingest 从 `tier1_rating` 映射；缺失显示「--」。
- **`prov`（数据凭据）**：阶段2 随大类/各层 agent 输出结构化 `{label, ok, value}`；缺失则气泡不渲染凭据条。
- **基金底层穿透**：阶段2 在分类层做一次（黄金ETF→黄金、QDII→海外、债基→债券、其余→股票→行业），上层只消费 `asset_class` 结果。
