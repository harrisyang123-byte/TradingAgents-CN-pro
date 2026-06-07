# TradingAgents-CN — 多智能体 A股/港股 金融投研系统

[![Python](https://img.shields.io/badge/Python-3.12%2B-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115%2B-009688.svg)](https://fastapi.tiangolo.com/)
[![Vue 3](https://img.shields.io/badge/Vue-3.5%2B-4FC08D.svg)](https://vuejs.org/)
[![Claude Code](https://img.shields.io/badge/Claude_Code-Workflow-orange.svg)](https://claude.ai/code)

面向中国 A股/港股 用户的**多智能体分层辩论式投资系统**。以用户持久盈利为目标，从大类资产配置到宏观行业、个股配仓、事前风控全覆盖，所有 LLM 决策环节都有对立角色辩论。

---

## 目标

> **让用户持久盈利，而不是跑赢基准。**

系统以绝对收益为目标而非基准超额收益。景气度高+估值合理=配置，景气度低/高估=不配或减配，不和指数挂钩。

---

## 核心架构

投资决策从**大类资产到个股**分层展开，每层都有多视角辩论，约束从上到下硬传递。

```
【常态化后台，独立运行】
┌────────────────────────────────────────────────────────┐
│ 数据层      市场情绪 / 北向资金 / PE分位 / 宏观指标       │
│ 景气打分    5类信号自动扫描全量18大行业，每日更新         │
│ Tier1库     行业判Go后自动触发主要公司深度研究，7天缓存   │
└────────────────────────────────────────────────────────┘

【每次组合分析主流程】
Step 0  宏观裁判
        输入：PMI/利率/北向/涨跌比
        输出：risk-on/off + total_weight_limit + cash_floor
           ↓ 硬约束

Step 0.5  大类资产配置（战略配置师 vs 防御配置师 → 大类裁判）
        在「现金 / 债券 / 股票 / 黄金 / 海外(QDII) / 其他」6大类间分配
        进攻派 vs 避险派辩论，基金按底层资产穿透归类
        裁判：各类配比之和=100，现金≥cash_floor，股票≤total_weight_limit
        输出：6大类 current→target + stock_weight（股票额度下传行业层）
           ↓ stock_weight 成为行业层 total_weight_limit

Step 1  行业研究员 ×N（并行）
        每行业独立：LLM知识 + AKShare硬数据 + 新闻研报
        研究员首发 → 反向者挑战 → 行业内辩论（2轮）
        → 跨行业裁判：在 stock_weight 限额内做资源分配
        输出：go_nogo + vitality_level + final_weight
        缓存：7天有效期，手动可强制刷新
           ↓ 同时触发 Tier1 研究库异步更新

Step 2  公司层（Tier1 驱动）
        Scout 在 Go 行业找候选标的
        读取 Tier1 研究库报告做横向比较
        输出：每行业候选排序 + 评级 + 目标价

Step 3  组合层（与 Step 2 并行）
        持仓分析师 + Scout_L3 诊断 → 组合反向者挑战
        输出：建议减仓/清仓标的 + 敞口风险

Step 4  行业PM ×N（并行，子 Agent 模式）
        每个 Go 行业独立 spawn 激进PM vs 保守PM
        激进：重仓高评级，配额用满，偏 immediate
        保守：分散配置，保留缓冲，偏 batch/conditional
        裁判：综合两者，买入区间取 Tier1 ∩ PE分位保守值
        输出：target_weight + entry_price_range + batch_plan
           ↓ 行业配额约束

Step 5  风控规则引擎（非LLM，事前硬拦截）
        ① 单股 ≤ max_single_weight
        ② 行业合计 ≤ final_weight
        ③ 总仓位 ≤ total_weight_limit
        ④ 现金 ≥ cash_floor
        违规 → 打回对应行业PM重做（最多2次），第3次自动截断

Step 6  Risk Director（子 Agent 模式）
        悲观风险总监 vs 乐观风险分析师（2轮）
        → 风控裁判
        输出：max_drawdown_20pct + 黑天鹅触发条件（建议性）

Step 7  Portfolio Synthesizer（子 Agent 模式）
        验证约束链完整性（不修正，只报警）
        识别行业缺口（gap > 3% 触发补充侦察）
        汇总 asset_allocation + industry_matrix + 最终处方
        输出：可直接执行的组合调整方案
```

---

## Agent 列表（17 个 v3 子 Agent）

| 层 | Agent 文件 | 职责 |
|----|-----------|------|
| 宏观 | `v3-macro-judge.md` | 宏观信号 → total_weight_limit / cash_floor |
| 大类 | `v3-asset-strategist.md` | 战略配置师（进攻）：6大类偏进攻配比 |
| 大类 | `v3-asset-defender.md` | 防御配置师（避险）：挑战进攻倾向，给避险配比 |
| 大类 | `v3-asset-judge.md` | 大类裁判：综合两者 → 6大类目标 + stock_weight 下传 |
| 行业 | `v3-industry-researcher.md` | B+C三层数据 → 首次判断 |
| 行业 | `v3-industry-contrarian.md` | 挑战研究员，暴露盲点 |
| 跨行业 | `v3-cross-industry-judge.md` | 在 stock_weight 限额内分配 final_weight |
| 公司 | `v3-scout.md` | Go 行业内找候选标的，读 Tier1 横向比较 |
| 组合 | `v3-portfolio-analyst.md` | 持仓分析师：诊断现有持仓与敞口 |
| 组合 | `v3-portfolio-contrarian.md` | 组合反向者：挑战诊断，暴露集中风险 |
| PM | `v3-pm-aggressive.md` | 激进PM：配额用满，重仓高评级 |
| PM | `v3-pm-conservative.md` | 保守PM：保留缓冲，偏分批 |
| PM | `v3-pm-judge.md` | PM裁判：综合两者，取保守买入区间 |
| 风控 | `v3-risk-pessimist.md` | 找最坏情景，挑战集中风险 |
| 风控 | `v3-risk-optimist.md` | 反驳过度保守，指出踏空风险 |
| 风控 | `v3-risk-judge.md` | 综合两者，输出 RiskAssessment |
| 合成 | `v3-portfolio-synthesizer.md` | 验证约束链 + 缺口处理 + 汇总 |

编排脚本（单一增量编排器）：

| Workflow | 阶段（stage） | 覆盖步骤 |
|---------|--------------|---------|
| `workflow-v3-advisor.js` | `macro` → `asset` → `industry` → `scout` → `portfolio` → `pm` → `synth` | Step 0-7 全链路：宏观 → 大类资产辩论 → 行业研究/反向者 → 跨行业裁判 → Scout 标的侦察 → 组合层诊断 → PM 并行辩论 → 风控规则 + Risk Director + Portfolio Synthesizer。按阶段缓存增量跳过，下游随上游失效强制重跑。 |

---

## 单一大脑：v3 pipeline

历史上系统有两条并行的分析路径（LangGraph 的 `AdvisorGraph` 与 v3 子 Agent workflow），两者写同一张 `portfolio_advice` 表互相覆盖，导致前端读到的字段时有时无。**该 LangGraph 大脑已退役**，现在只有一条规范路径：

```
前端「组合分析」 / 对话「分析」 / scripts/run.sh
        ↓
v3_advisor_runner.py（subprocess 驱动，两阶段）
        ↓
collect_data.py  → workflow-v3-advisor.js（claude -p 跑 v3 子 Agent）→ ingest_advice.py
        ↓
portfolio_advice 集合（含 asset_allocation / industry_matrix / vitality_level / 辩论历程等富字段）
        ↓
前端 Overview 读取
```

API 采用**两阶段 + 人工确认**：`/plan`（收集数据 + 跑到行业层，返回推荐行业）→ 用户勾选行业 → `/execute`（续跑 Scout→PM→合成 + 落库）。

---

## 决策设计原则

**景气度 × 安全边际双因子**：景气度高但估值极端时调节权重，不直接否决（避免错过 AI 等成长赛道）。

**约束从大类层硬传递**：宏观 → 大类资产 → 行业 → PM，每层输出满足上游约束（如股票额度 stock_weight 下传为行业层 total_weight_limit），Portfolio Synthesizer 验证链路完整性。

**辩论驱动质量**：每层都有对立角色，避免单一视角的确认偏误。风控规则是硬约束，Risk Director 是建议，两者职责分开。

**子 Agent 而非 `llm.invoke()`**：所有 LLM 决策逻辑都通过 `.md` 文件定义 + Workflow `agent()` 调用，不在 Python 中直接调 LLM——这也是退役 LangGraph 大脑、收敛到 v3 单一路径的原因。

---

## 技术栈

| 组件 | 技术 |
|------|------|
| 后端 | FastAPI 0.115+ + Uvicorn |
| 前端 | Vue 3.5+ + Vite + Element Plus |
| 数据库 | MongoDB + Redis |
| Workflow 子 Agent | v3 全链路编排（Step 0-7），claude -p 驱动 |
| 数据源 | AKShare / Tushare / BaoStock（A股）+ yfinance / Finnhub（港股/美股） |
| 市场覆盖 | 见下方「市场覆盖边界」 |
| 行业体系 | 18大投资主题（消费/科技/金融/医药等） |

> **市场覆盖边界**（按链路分层，别混为一谈）：
> - **大类资产层** —— A股 / 港股 + **海外（纳指/标普/QDII/黄金）作为「全球配置」一整块敞口**参与配比辩论。
> - **行业景气雷达 + 行业深辩** —— **仅 A 股**。景气打分由 A 股信号驱动（北向资金 / A股PE分位 / 中国政策），18 bucket 为申万口径，**不拆解美股行业**。
> - **组合顾问个股推荐（Scout/PM）** —— 实跑**仅 A 股**。底层 `market_tools` 技术上能取港股/美股数据，但当前无触发路径，Tier1 自动研究只认 A 股代码。
> - **个股深度分析（独立链路，非组合顾问）** —— **支持 A股 / 港股 / 美股**（输入 `AAPL` 这类美股可跑完整深度分析，结论暂未回流组合顾问 Tier1 库）。
>
> 一句话：**想配纳指 → 走大类资产层的海外敞口；想深挖某只美股 → 用个股分析。组合顾问目前不会主动推荐美股个票。**

---

## 项目结构

```
tradingagents-cn/
├── agents/advisor/              # 17 个 v3 子 Agent .md 定义（含大类资产层）
├── scripts/
│   ├── workflow-v3-advisor.js   # v3 增量编排器（macro→asset→…→synth），终态守卫强制吐 run_report
│   ├── run.sh                   # 编排入口（all / collect / analyze），支持 --portfolio-file / --snapshot
│   ├── collect_data.py          # 数据采集 → data/advisor_runs/{ts}/（含文件输入模式，脱离 MongoDB）
│   ├── ingest_advice.py         # v3 产物 → portfolio_advice 落库（--out-json 可不连库出 doc）
│   ├── export_inputs.py         # 本地导出文件总线输入（holdings/watchlist/tier1 → data/_inputs/）
│   ├── build_snapshot.py        # 运行产物 → 前端静态快照（frontend/public/snapshot/*.json）
│   ├── run_report.py            # 离线运行报告（逐阶段体检 + 是否降级），保证「看得见」
│   └── migrate_position_industry.py  # 历史持仓行业补填
├── app/
│   ├── routers/
│   │   ├── paper.py                  # 持仓/概览 API
│   │   ├── portfolio_analysis.py     # 组合分析 API（两阶段 plan/execute）
│   │   └── watchlist.py              # 行业关注列表 API
│   └── services/
│       ├── v3_advisor_runner.py      # subprocess 驱动 run.sh 的两阶段 runner
│       ├── portfolio_advisor_service.py  # Tier1 数据准备（LangGraph 已退役）
│       ├── industry_vitality.py      # 景气打分引擎（5类信号）
│       ├── industry_scan_pool.py     # 行业扫描池（持仓+watchlist+景气）
│       ├── industry_classifier.py    # 持仓录入时前置行业分类
│       ├── stock_research_cache.py   # Tier1 研究库（7天缓存）
│       └── market_signals.py         # 市场温度计
├── tradingagents/
│   ├── graph/trading_graph.py        # 个股分析 LangGraph 图（保留，独立于组合顾问）
│   └── agents/advisors/
│       ├── advisor_states.py         # AdvisorState（含v3约束传递字段）
│       └── risk_rules.py             # 事前风控规则引擎（纯Python）
├── frontend/                         # Vue 3 前端
│   └── src/views/Portfolio/
│       └── Overview.vue              # 资产配置 + 行业矩阵 + Drawer + 辩论历程
├── start.sh / stop.sh                # 一键启停脚本
├── docs/wiki/                        # 架构知识库
└── openspec/                         # 变更记录
```

---

## 快速启动

**前置条件**：MongoDB、Redis 已启动；已配 `.env`；已建 `.venv` 并装好依赖。

### 一键启停

```bash
./start.sh    # 起 DB（docker compose）+ 后端(8000) + 前端(3000)
./stop.sh     # 停止
```

`start.sh` 会：起 MongoDB/Redis → 用 `.venv/bin/uvicorn` 起后端（默认 8000，热重载）→ `npm run dev` 起前端（默认 3000）→ 轮询 `/api/health` 等就绪。

### 手动启动（调试）

```bash
docker compose up -d mongodb redis                                # 数据库
.venv/bin/uvicorn app.main:app --reload --host 0.0.0.0 --port 8000  # 后端
cd frontend && npm run dev                                         # 前端
```

访问：前端 `http://localhost:3000`、API 文档 `http://localhost:8000/docs`。

> ⚠️ 起服务前必须先配 `.env`（`cp .env.example .env`），至少填 MongoDB / Redis / `JWT_SECRET` / `CSRF_SECRET`，以及至少一个大模型 API key（DeepSeek / DashScope / AIHubMix 任一）。生产环境务必改掉 `JWT_SECRET`、`CSRF_SECRET` 和数据库默认密码。

### 触发组合分析

| 对话中说 | 实际执行 | 等价命令 |
|----------|----------|----------|
| `分析` | 全链路 Step 0-7 | `./scripts/run.sh all --user-id <id>` |
| `跑行业层` | 行业研究+反向者 | `./scripts/run.sh analyze --data-dir <path> --only industry` |
| `跑辩论` | PM 辩论 | `./scripts/run.sh analyze ... --only pm` |
| `跑合成` | 风控+合成器 | `./scripts/run.sh analyze ... --only synth` |

`run.sh all` 三阶段：`collect_data.py` 采数 → `claude -p` 驱动 `workflow-v3-advisor.js` 跑 v3 子 Agent → `ingest_advice.py` 落库到 `portfolio_advice`，前端 Overview 即读这张表。

#### 行业深辩范围开关 `--industries`

行业层默认只对「持仓 + watchlist + 当下景气 top3 新方向」做昂贵的多 Agent 深度辩论（全 18 行业的廉价景气榜照常全扫，写入 `data_vitality.json` 供前端全景视图）。需要全量深辩时加 `--industries all`：

```bash
./scripts/run.sh all                   # 默认 scope：持仓 + watchlist + 景气 top3
./scripts/run.sh all --industries all  # 全量：全部可投资行业进深辩（货币/固收类不计）
./scripts/run.sh collect --industries all   # collect 阶段同样支持
```

> 景气 top3 只看景气排名进深辩，**不设估值准入闸**——估值约束交给下游各层调权重/买点（「景气×安全边际」「调权重而非否决」）。`--full` 是忽略缓存重跑，不是「全量行业」，别混淆。

#### 接力跑（collect / analyze 分离）

链路天然分两段，靠 `data/advisor_runs/{ts}/` 目录交接，可在不同机器上接力：

```bash
./scripts/run.sh collect --user-id <id>            # 第一段：要 MongoDB + 联网抓 AKShare，产出数据目录
./scripts/run.sh analyze --data-dir <目录> --full  # 第二段：要 claude CLI 鉴权，读目录跑 v3 子 Agent + 落库
```

> ⚠️ `analyze` 直接吃目录里**已存在的** `industry_list.json`，不会重算深辩范围。想换范围要重新 `collect`（带 `--industries`）或手动改该文件后再 `analyze`。

> `run.sh` 硬前置（`check_prereqs` 会校验）：24 位 hex 的 `--user-id`、Python、Claude Code CLI（LLM 推理这层需要 claude CLI 鉴权）。

#### 文件总线（B 档：脱离 MongoDB 在异地跑）

为了让分析能在没有本地 MongoDB 的环境（如远端 Pod）里跑，链路提供一条**叠加式**的文件输入/输出旁路——不改动上面的 Mongo 全量路径，两条路都跑得通：

```bash
# ① 本地（有 Mongo）导出文件总线输入 → data/_inputs/{holdings,watchlist,tier1_reports}.json
python scripts/export_inputs.py --user-id <id> --out-dir data/_inputs

# ② 异地（无 Mongo）：collect 改读文件，跳过所有 Mongo 调用
./scripts/run.sh collect --portfolio-file data/_inputs/holdings.json \
    --watchlist-file data/_inputs/watchlist.json --tier1-file data/_inputs/tier1_reports.json

# ③ 跑分析并生成前端静态快照（frontend/public/snapshot/*.json）
./scripts/run.sh analyze --data-dir data/advisor_runs/<ts> --snapshot
```

- **输入端**：`collect_data.py --portfolio-file` 进入「文件输入模式」，持仓 / 扫描池 / Tier1 全读本地 JSON（`watchlist.json` / `tier1_reports.json` 可空）。景气榜（`score_all_industries`）本就不碰 Mongo，照常联网全扫。基金穿透因依赖 Mongo 基金库而降级为「仅直接个股敞口」。
- **输出端**：`build_snapshot.py` 把运行产物组装成与 API **完全同构**的 `overview.json` / `advice_latest.json`，前端设 `VITE_STATIC_SNAPSHOT=1` 即不连后端、直接 fetch 仓库里的快照展示，效果与走 API 一致。
- **保证看得见**：每次运行（成功 / 风控拦截 / 崩溃）编排器都强制吐 `run_report.json` + `run_report.md`，逐阶段报告「跑没跑 / 产物空不空 / 停在哪为什么 / 前端会不会降级」。可单独离线复盘任意历史目录：

```bash
python scripts/run_report.py --data-dir data/advisor_runs/<ts>
```

> ⚠️ 文件总线产出的 `holdings.json` 等是**敏感财务数据**，`data/` 已在 `.gitignore` 内；若要把静态快照（`frontend/public/snapshot/`）推上库共享，注意它含持仓/处方，务必用私有仓库。

---

## v4 分层独立深度投研系统（与 v3 并存，预览）

v4 是一条**与 v3 完全并存、零侵入**的新链路，把投研拆成常驻的「分析单元」：七大类资产（权益/固收/现金/大宗/贵金属/房地产/另类）→ 行业 → 个股 + 各层配比，每个单元有稳定 `unit_id`、独立产物 JSON、独立五色状态与 TTL，触发只跑命中单元。独立集合 `v4_units`、独立目录 `data/v4/`、独立编排器/路由，v3 一行不动。完整规格见 `.kiro/specs/v4/`，Agent 指南见 [AGENTS.md](AGENTS.md) 第 11 节。

### 触发（CLI 与 Web 分离）

```bash
./scripts/run_v4.sh analyze asset:equity --user-id <id> --portfolio-file data/v4/_inputs/holdings.json
./scripts/run_v4.sh status            # 列全部单元五色状态
```

`unit-selector`：`asset:<class>` / `plan:<class>` / `alloc:portfolio` / `alloc:equity_industries` / `industry:<name>` / `stock:<code>` / `alloc:industry:<name>`。

### 双跑文件总线：本地 ↔ AI 代跑（靠 git 传输）

v4 的 git 传输载体 = `data/v4/**/*.json` **单元粒度结构化文件**（diff 友好、可 review）。**`data/` 整体忽略，但 `data/v4/` 子树显式解除忽略**（运行锁 `_locks/`、collect 中间包 `inputs/`、`.tmp` 仍排除），所以 AI 代跑产出的单元 JSON 能经 git 回传本地。

```
本地: 编辑 data/v4/_inputs/holdings.json ──git push──▶ 私有仓
                                                         │ git pull
                                 AI 代跑: ./run_v4.sh analyze <unit> --portfolio-file data/v4/_inputs/holdings.json
                                                         │ 产出 data/v4/{assets,allocation,industries,stocks,plans}/*.json
本地: git pull ◀──git push（AI 提交单元产物）────────────┘
      python scripts/import_v4.py --user-id <id>   # 幂等导入 v4_units，前端三层 Tab 即与代跑一致
```

> ⚠️ `data/v4/` 含真实持仓/处方财务数据，**只在私有仓库 / 私有分支使用**。仓库其它位置的 `holdings.json` 仍被忽略。

### 本地持仓推送格式

把持仓放到固定路径 `data/v4/_inputs/holdings.json`（模板 `holdings.example.json` + 字段说明见 `data/v4/_inputs/README.md`）：

```json
{"positions": [
  {"code": "600519", "name": "贵州茅台", "weight": 15, "market_value": 150000, "instrument_type": "stock"},
  {"code": "511990", "name": "华宝添益货币ETF", "weight": 12, "market_value": 120000, "instrument_type": "fund"},
  {"code": "", "name": "活期存款", "weight": 7, "market_value": 70000, "instrument_type": "cash"}
]}
```

- `name` 是归类主依据（名称关键词优先），`instrument_type`（`stock/etf/fund/bond/cash/other`）做兜底；判不出归 `unclassified`（不丢弃）。
- 现金、实物房产等无市场代码的敞口 `code` 留空。零持仓的大类也能分析。

### 跑全量分析

```bash
H=data/v4/_inputs/holdings.json
for c in equity fixed_income cash commodity precious_metal real_estate alternative; do
  ./scripts/run_v4.sh analyze asset:$c --user-id <id> --portfolio-file $H; done
./scripts/run_v4.sh analyze alloc:portfolio --user-id <id> --portfolio-file $H
# 权益深链：industry:<行业> → alloc:equity_industries → stock:<代码> → alloc:industry:<行业>
python scripts/import_v4.py --user-id <id>     # 回传后导入
python scripts/run_report_v4.py                # 逐单元体检
python scripts/build_snapshot_v4.py            # （可选）静态快照 → frontend/public/snapshot/v4/
```

> `run_v4.sh` 第 2 阶段（Agent 推理）需 `claude` CLI 鉴权；无 claude 时第 1 阶段（采集输入包）仍完成并打印待手动执行的命令。

---

## API 说明

| 接口 | 说明 |
|------|------|
| `GET /api/portfolio/overview` | 组合总揽（v3 有则读 advice 的 asset_allocation/industry_matrix，否则降级拼接） |
| `POST /api/portfolio/analysis/plan` | 触发 v3 plan 阶段（收集数据+行业分析），返回推荐行业 |
| `POST /api/portfolio/analysis/execute` | 用户确认行业后执行全量（Scout→PM→合成→落库） |
| `GET /api/portfolio/analysis/{task_id}/status` | 轮询任务状态 |
| `POST /api/portfolio/analysis/industry/{name}/refresh` | 强制刷新某行业缓存 |
| `POST /api/portfolio/positions` | 新增持仓（自动分类行业） |
| `GET /api/watchlist` | 行业关注列表 |
| `POST /api/watchlist` | 添加关注行业 |
| `DELETE /api/watchlist/{industry}` | 删除关注行业 |

完整 API 文档：`http://localhost:8000/docs`

---

## 知识库

| 文档 | 内容 |
|------|------|
| [**AGENTS.md**](AGENTS.md) | **主 Agent 指南（唯一真源）**：链路/快捷指令/接力/`--industries`/设计铁律 |
| [行业层重构](docs/wiki/industry-layer-rebuild.md) | 景气打分/并行研究员/7天缓存/Tier1触发 |
| [决策层重构](docs/wiki/decision-layer-rebuild.md) | 并行PM/约束传递链/风控引擎/Portfolio Synthesizer |
| [组合顾问引擎](docs/wiki/portfolio-advisor-engine.md) | v3 子 Agent 辩论架构/结构化处方 |
| [认证与部署](docs/wiki/auth-bootstrap.md) | 初始 admin 创建/首次部署 |

---

## 风险提示

本系统仅用于辅助投资研究，不构成投资建议。AI 判断存在不确定性，投资有风险，决策需谨慎。

---

## License

Apache 2.0
