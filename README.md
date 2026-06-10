# TradingAgents-CN — 多智能体 A股/港股/全球 分层深度投研系统

[![Python](https://img.shields.io/badge/Python-3.12%2B-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115%2B-009688.svg)](https://fastapi.tiangolo.com/)
[![Vue 3](https://img.shields.io/badge/Vue-3.5%2B-4FC08D.svg)](https://vuejs.org/)
[![Claude Code](https://img.shields.io/badge/Claude_Code-Workflow-orange.svg)](https://claude.ai/code)

面向中国投资者的**多智能体分层辩论式投研系统**。以用户持久盈利为目标，从大类资产配置 → 行业景气 → 产业链瓶颈 → 个股 → 各层配比 + 事前风控全覆盖，所有 LLM 决策环节都有对立角色辩论、总监拍板。

> **当前主线 = v4 分层独立深度投研**（本文档主体）。上一代 v3 组合顾问已上线但**逐步退役中**，见文末「上一代：v3（退役中）」。

---

## 目标

> **让用户持久盈利，而不是跑赢基准。**

绝对收益导向，不和指数挂钩。判断任何改动都回到一条：它有没有让建议更**全面**（MECE 全覆盖）、更**可信**（证据溯源、不编造）、更**可执行**（敢站队、给方向+仓位+买点+风控线）、更**会学习**（结果闭环反思）。

---

## 核心架构（v4 分层深度投研）

把投研拆成常驻的「**分析单元**」：每个单元有稳定 `unit_id`、独立产物 JSON、独立五色状态与 TTL，触发只跑命中单元，绝不连带重跑。约束从上到下硬传递，上游变更只置黄软提醒、不强制重跑。

```
宏观 data-desk（唯一联网取数台：22 宏观指标 + A股个股硬数据）
   │（全局共享）
七大类研究部门 ×7（权益/固收/现金/大宗/贵金属/房地产/另类）
   每类：3 视角分析师(macro/flow/policy) → 多空 3 轮 → 总监拍板(reflection+反骑墙)
   │（7 份 verdict）
资产配置委员会  alloc:portfolio
   Σ=100% 目标配比 + 下传 equity_quota（权益额度）
   │（equity_quota 约束）
权益深链（gated by equity_quota>0）
   ├ 行业研究部门 ×N   industry:<name>
   │    景气多空 + 产业链瓶颈分析师(Chokepoint) → 总监整合 chokepoint_map
   ├ 行业间配比         alloc:equity_industries  (Σ ≤ equity_quota)
   ├ 个股研究部门 ×M   stock:<code>
   │    3 分析师(财务/竞争/估值) → 多空 → 总监预期差拍板
   └ 行业内配比 ×K      alloc:industry:<name>  (Σ ≤ 行业权重)

非权益方案部门 ×6   plan:<class>（固收/现金/大宗/贵金属/房地产/另类执行方案）
```

独立集合 `v4_units`、独立目录 `data/v4/`、独立编排器 `scripts/workflow-v4-advisor.js`、独立只读路由 `app/routers/portfolio_v4.py`、独立前端三层 Tab。完整规格见 `.kiro/specs/v4/`，主 Agent 指南见 [AGENTS.md](AGENTS.md)。

---

## v4 Agent 阵容（分层分队，每层对立角色辩论）

| 层 | 角色 | 职责 |
|----|------|------|
| 通用 | `v4-data-desk` | **唯一带联网工具**的取数台；宏观走 `macro_source.py`(AKShare 22 指标)、A股个股走 `stock_source.py`(AKShare 股价/市值/PE/PB/PE分位/财务/涨幅) |
| 大类 | `v4-asset-analyst-macro/flow/policy` + `v4-asset-bull/bear` + `v4-asset-director` | 3 视角分析师打底 → 多空 3 轮 → 总监拍板(reflection+反骑墙) |
| 大类 | `v4-allocation-director` | 资产配比委员会，Σ=100% + 下传 equity_quota |
| 行业 | `v4-industry-bull/bear` + **`v4-industry-chokepoint`** + `v4-industry-director` | 景气多空 + **产业链瓶颈分析师**(Chokepoint 四维+逆向工程+替代路径+发现度) → 总监整合 chokepoint_map |
| 行业 | `v4-industry-allocator` | 行业间配比(≤equity_quota) |
| 个股 | **`v4-stock-analyst-financial/competitive/valuation`** + `v4-stock-bull/bear` + `v4-stock-director` | **个股 3 分析师分队**(财务/竞争/估值)打底 → 多空 → 总监预期差拍板 |

> 全部分析角色 `tools:[Read]`、**只消费 data-desk 产出的输入包、绝不自己联网取数**；唯一带 `web_search`/`web_fetch` 的是 `v4-data-desk`。

---

## 三套核心方法论

- **Chokepoint 供应链瓶颈框架**（`planning/v4/chokepoint-framework.md`，借鉴 Serenity）：自下而上逆向工程产业链，四维判定（不可替代/供给集中/产能刚性/价值卡位）+ 替代路径 + **市场发现度**，在景气行业里定位"物理卡脖子且市场还没发现"的环节。混合分队：瓶颈分析师出骨架 → 主 agent 对 top 瓶颈派专项调研员深挖 → 总监核实。
- **预期差选股理论**（`planning/v4/stock-selection-theory.md`）：**判断买卖看预期差（基本面将兑现的 − 价格已 price-in 的），不看涨幅/PE 分位**。三锚：隐含增速缺口 / 定价充分度 / 催化。A/B 验证胜过"估值分位法"——后者会让你 88 元不敢买中际旭创、错过 11 倍。
- **结果闭环反思 + 反骑墙**（借鉴 TradingAgents）：总监开辩前读上一版 verdict → 输出 reflection（变了什么/为何改判/自检）；证据势均力敌才中性，否则必须站队，数据盲区降 confidence 而非默认骑墙。

**数据铁律**：分析 Agent 严禁自产价格/PE/市值/目标价数字，唯一来源 = data-desk 联网核实值（个股走 `stock_source.py`）；无则标 missing，绝不编造。

---

## 决策设计原则

- **景气度 × 安全边际 × 预期差**：景气定行业（go/nogo），瓶颈定环节（钱流向哪个咽喉），预期差定个股买卖（市场还没看到什么），安全边际把关买点。
- **约束硬传递**：宏观 → 大类配比 equity_quota → 行业配比 → 个股配比，每层满足上游约束；上游变更只置黄软提醒。
- **辩论驱动质量**：每层对立角色 + 总监拍板，避免单一视角确认偏误。
- **MECE**：每一分钱落进恰好一个大类（含 unclassified 待穿透桶），不漏不重。
- **子 Agent 而非 `llm.invoke()`**：所有 LLM 决策走 `agents/advisor/v4-*.md` + 编排器 `agent()`。

---

## 技术栈

| 组件 | 技术 |
|------|------|
| 后端 | FastAPI 0.115+ + Uvicorn |
| 前端 | Vue 3.5+ + Vite + Element Plus |
| 数据库 | MongoDB + Redis（v4 前端可走静态快照，MongoDB 可选）|
| v4 Agent | `agents/advisor/v4-*.md` 子 Agent，本会话 AI 直跑 或 `claude -p` 驱动 |
| 数据源 | AKShare（A股宏观+个股，`macro_source.py`/`stock_source.py`）/ Tushare / BaoStock + 联网核实 |
| 市场覆盖 | A股 / 港股 直接；海外（美股/欧股/台股）通过 QDII·主题基金间接 |

> **市场覆盖边界**：A股个股直接（Scout/stock_source），港股直接可投，海外物理瓶颈标的（如 SOI 衬底/MBE 设备）通过 QDII/主题基金获取敞口。大类资产层把海外作为「全球配置」一整块敞口参与配比。

---

## 项目结构

```
tradingagents-cn/
├── agents/advisor/
│   ├── v4-data-desk.md              # 唯一联网取数台
│   ├── v4-asset-*.md                # 大类层(3分析师+多空+director+配比委员会)
│   ├── v4-industry-*.md             # 行业层(多空+瓶颈分析师+director+配比)
│   ├── v4-stock-*.md                # 个股层(3分析师+多空+director)
│   └── v3-*.md                      # 上一代 v3 子 Agent（退役中）
├── scripts/
│   ├── workflow-v4-advisor.js       # v4 单元编排器（unit-selector 驱动）
│   ├── run_v4.sh                    # v4 入口（analyze/refresh/status/scan）
│   ├── collect_v4.py                # v4 输入包采集（穿透归类 + 宏观/个股取数）
│   ├── v4_unit_cli.py               # 单元信封读写（write 自动归档+version+1）
│   ├── build_snapshot_v4.py         # v4 单元 → 前端静态快照
│   ├── import_v4.py / run_report_v4.py / archive_v4.py
│   └── run.sh / collect_data.py …   # 上一代 v3 链路脚本（退役中）
├── app/services/v4/
│   ├── v4_classifier.py             # 七大类穿透归类
│   ├── macro_source.py              # AKShare 22 宏观指标
│   ├── stock_source.py              # AKShare A股个股硬数据（股价/市值/PE/财务/涨幅）
│   ├── v4_unit_store.py / v4_query.py / asset_classes.py
├── app/routers/portfolio_v4.py      # v4 只读路由
├── frontend/src/views/Portfolio/v4/ # v4 三层 Tab（大类/行业/个股 + 瓶颈地图）
├── planning/v4/                     # 设计真源（chokepoint-framework / stock-selection-theory / rerun-memory / backlog）
├── openspec/                        # 变更记录（OpenSpec changes）
├── docs/wiki/                       # 架构知识库
└── start.sh / stop.sh
```

---

## 快速启动

**前置**：已配 `.env`（至少 MongoDB/Redis/`JWT_SECRET`/`CSRF_SECRET` + 一个大模型 key）；已建 `.venv` 装好依赖。

```bash
./start.sh    # 起 DB（docker compose）+ 后端(8000) + 前端(3000)
./stop.sh
```

访问：前端 `http://localhost:3000`、API 文档 `http://localhost:8000/docs`。生产环境务必改掉默认密钥与数据库密码。

> 仅看 v4 结论（无需 Mongo/后端）：跑出 `data/v4/` 单元 + `build_snapshot_v4.py` 后，前端设 `VITE_STATIC_SNAPSHOT=1` 直接 fetch 静态快照展示。

---

## 运行 v4 分析

### 触发（CLI）

```bash
./scripts/run_v4.sh analyze asset:equity --user-id <id> --portfolio-file data/v4/_inputs/holdings.json
./scripts/run_v4.sh refresh <unit-selector> ...   # 强制失效重跑，重绑最新上游指纹
./scripts/run_v4.sh status            # 列全部单元五色状态
./scripts/run_v4.sh scan              # 仅置黄过期单元，绝不自动重跑
```

`unit-selector`：`asset:<class>` / `plan:<class>` / `alloc:portfolio` / `alloc:equity_industries` / `industry:<name>` / `stock:<code>` / `alloc:industry:<name>`。七大类 class：`equity / fixed_income / cash / commodity / precious_metal / real_estate / alternative`。

### 本地持仓格式

放到固定路径 `data/v4/_inputs/holdings.json`（模板见 `data/v4/_inputs/README.md`）：

```json
{"positions": [
  {"code": "600519", "name": "贵州茅台", "weight": 15, "market_value": 150000, "instrument_type": "stock"},
  {"code": "511990", "name": "华宝添益货币ETF", "weight": 12, "market_value": 120000, "instrument_type": "fund"},
  {"code": "", "name": "活期存款", "weight": 7, "market_value": 70000, "instrument_type": "cash"}
]}
```

- `name` 是归类主依据，`instrument_type`（`stock/etf/fund/bond/cash/other`）兜底；判不出归 `unclassified`（不丢弃）。
- 现金/实物房产等无市场代码的敞口 `code` 留空；零持仓的大类也能分析。

### 跑全量分析

```bash
H=data/v4/_inputs/holdings.json
for c in equity fixed_income cash commodity precious_metal real_estate alternative; do
  ./scripts/run_v4.sh analyze asset:$c --user-id <id> --portfolio-file $H; done
./scripts/run_v4.sh analyze alloc:portfolio --user-id <id> --portfolio-file $H
# 权益深链：industry:<行业> → alloc:equity_industries → stock:<代码> → alloc:industry:<行业>
python scripts/import_v4.py --user-id <id>     # 回传后导入 Mongo（可选）
python scripts/run_report_v4.py                # 逐单元体检
python scripts/build_snapshot_v4.py            # 静态快照 → frontend/public/snapshot/v4/
```

### 双跑文件总线：本地 ↔ AI 代跑（靠 git 传输）

v4 的 git 传输载体 = `data/v4/**/*.json` **单元粒度结构化文件**（diff 友好、可 review）。`data/` 整体忽略，但 `data/v4/` 子树显式解除忽略（运行锁 `_locks/`、collect 中间包 `inputs/`、`.tmp` 仍排除）。

```
本地: 编辑 data/v4/_inputs/holdings.json ──git push──▶ 私有仓
                                                         │ git pull
                                 AI 代跑: run_v4.sh analyze <unit> --portfolio-file …
                                                         │ 产出 data/v4/{assets,allocation,industries,stocks,plans}/*.json
本地: git pull ◀──git push（AI 提交单元产物）────────────┘
      python scripts/import_v4.py --user-id <id>   # 幂等导入，前端三层 Tab 即与代跑一致
```

> `run_v4.sh` 第 2 阶段（Agent 推理）两种驱动：**① 本会话 AI agent 直跑（默认，无需 `claude` CLI，缺数据源联网补齐而非降级，存档 `data/v4/` 单元 JSON，前端走静态快照、MongoDB 可选）；② `claude -p` 子进程（需 claude 鉴权）。** 完整步骤见 [`docs/wiki/v4-ai-proxy-run.md`](docs/wiki/v4-ai-proxy-run.md)。

> ⚠️ `data/v4/` 含真实持仓/处方财务数据，**只在私有仓库/私有分支使用**。

---

## API 说明（v4 只读路由）

| 接口 | 说明 |
|------|------|
| `GET /api/portfolio/v4/overview` | 三层概览：七大类卡片 + 资产配比 + equity_quota |
| `GET /api/portfolio/v4/asset/{class}` | 大类详情（多空辩论 + reflection + 方案/行业列表）|
| `GET /api/portfolio/v4/industry/{name}` | 行业详情（深辩 + **chokepoint_map 瓶颈地图** + 个股表）|
| `GET /api/portfolio/v4/units/status` | 全单元五色状态 |

完整 API 文档：`http://localhost:8000/docs`

---

## 知识库

| 文档 | 内容 |
|------|------|
| [**AGENTS.md**](AGENTS.md) | **主 Agent 指南（唯一真源）**：v4 链路/触发/角色/方法论/铁律 |
| [chokepoint-framework](planning/v4/chokepoint-framework.md) | Chokepoint 瓶颈框架（四维/逆向工程/混合分队/A-B实测）|
| [stock-selection-theory](planning/v4/stock-selection-theory.md) | 预期差选股理论（三锚/A-B验证/数据铁律）|
| [v4 AI 代跑](docs/wiki/v4-ai-proxy-run.md) | AI 直跑落地步骤 / 各单元 payload schema |
| [implementation-backlog](planning/v4/implementation-backlog.md) | 应改造未改造台账 |

---

## 上一代：v3 组合顾问（退役中）

v3 是已上线的上一代组合顾问，**正逐步被 v4 取代**，保留用于过渡与回溯。链路概要：

```
宏观裁判 → 大类资产配置(战略 vs 防御 → 裁判) → 行业研究员×N(研究员 vs 反向者 → 跨行业裁判)
→ Scout 标的侦察 → 组合诊断 → 行业PM×N(激进 vs 保守 → 裁判) → 风控规则引擎 + Risk Director → Portfolio Synthesizer
```

- 17 个 v3 子 Agent（`agents/advisor/v3-*.md`）：宏观/大类/行业/公司/组合/PM/风控/合成各层对立角色，编排器 `workflow-v3-advisor.js`（macro→asset→industry→scout→portfolio→pm→synth）。LangGraph 大脑已退役，全部 LLM 决策走 v3 子 Agent。
- 触发：`./scripts/run.sh all --user-id <id>`（采数 → `claude -p` 跑 v3 子 Agent → 落 `portfolio_advice` 表，前端 Overview 读）。两阶段 API：`/plan`（行业层，返回推荐行业）→ 用户勾选 → `/execute`（Scout→PM→合成+落库）。
- 文件总线（脱离 Mongo 异地跑）：`export_inputs.py` 导出 → `run.sh collect --portfolio-file …` → `analyze --snapshot`。
- 设计沿用「景气度 × 安全边际」「约束硬传递」「辩论驱动」原则，v4 在此基础上增加了产业链瓶颈、预期差选股、单元化独立缓存。
- 详细文档：[行业层重构](docs/wiki/industry-layer-rebuild.md) / [决策层重构](docs/wiki/decision-layer-rebuild.md) / [组合顾问引擎](docs/wiki/portfolio-advisor-engine.md)。

> v3 与 v4 零侵入并存，写不同的集合/目录；v4 成熟后 v3 链路将整体下线。

---

## 风险提示

本系统仅用于辅助投资研究，不构成投资建议。AI 判断存在不确定性，投资有风险，决策需谨慎。

## License

Apache 2.0
