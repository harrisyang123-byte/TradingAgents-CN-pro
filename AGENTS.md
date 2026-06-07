# AGENTS.md — TradingAgents-CN 主 Agent 指南

> 本文件是本项目**唯一权威**的 Agent 指南（single source of truth）。
> 任何 Agent（Claude Code / Cursor / DevGenie 平台 / 其他）动手前先读本文件。
> `CLAUDE.md` 只是指向本文件的指针，不再单独维护内容。

---

## 0. 第一铁律：文档即代码契约

**改了代码就必须同步本文件和 `README.md`。** 本项目反复踩的坑就是「文档和代码两套、互相飘移」——退役的架构还写在文档里骗后来人。所以：

- 改了链路 / 入口 / 开关 / Agent 职责 → **同一个 commit 里**更新 `AGENTS.md` + `README.md`。
- 发现文档与代码不符 → 以代码为准，**顺手修文档**，不要绕过。
- 不确定哪个是真的 → 去代码里核实（`scripts/run.sh`、`collect_data.py`、`workflow-v3-advisor.js`），不要凭印象。

---

## 1. 唯一大脑：v3 pipeline（LangGraph 组合顾问已退役）

历史上系统有两条并行分析路径（LangGraph 的 `AdvisorGraph` 与 v3 子 Agent workflow），都写同一张 `portfolio_advice` 表互相覆盖。**LangGraph 组合顾问大脑已退役**，现在只有一条规范路径。

**设计铁律（防止 Agent 把架构改歪）：**

- 🚫 **禁止 `llm.invoke()`**：所有 LLM 决策逻辑都通过 `agents/advisor/*.md` 子 Agent 定义 + workflow `agent()` 调用，不在 Python 里直接调 LLM。这正是退役 LangGraph、收敛到 v3 单一路径的原因。
- ⚠️ 个股分析的 `tradingagents/graph/trading_graph.py`（LangGraph）**保留**，它独立于组合顾问，不要误删。退役的只有组合顾问那条 LangGraph 路径。

---

## 2. 真实链路图

```
前端「组合分析」 / 对话「分析」 / scripts/run.sh
        ↓
v3_advisor_runner.py（subprocess 驱动 run.sh，两阶段）
        ↓
collect_data.py  →  workflow-v3-advisor.js（claude -p 跑 v3 子 Agent）→ ingest_advice.py
        ↓
portfolio_advice 集合（asset_allocation / industry_matrix / vitality_level / 辩论历程等富字段）
        ↓
前端 Overview 读取
```

编排器是**单一增量编排器** `scripts/workflow-v3-advisor.js`，阶段：
`macro → asset → industry → scout → portfolio → pm → synth`（覆盖 Step 0-7）。按阶段缓存增量跳过，下游随上游失效强制重跑。

---

## 3. 快捷指令 → 真实命令

| 用户说 | 实际执行 | 等价命令 |
|--------|----------|----------|
| `分析` | 全链路 Step 0-7 | `./scripts/run.sh all --user-id <id>` |
| `跑行业层` | 行业研究+反向者 | `./scripts/run.sh analyze --data-dir <path> --only industry` |
| `跑辩论` | PM 辩论 | `./scripts/run.sh analyze --data-dir <path> --only pm` |
| `跑合成` | 风控+合成器 | `./scripts/run.sh analyze --data-dir <path> --only synth` |

阶段名（`--only` / `--from` / `--to` / `--refresh` 通用）：
`macro | asset | industry | scout | portfolio | pm | synth`
单刷一个行业：`--refresh industry:半导体`。`--full` = 忽略缓存全量重跑（不是「全量行业」）。

---

## 4. 接力机制（collect / analyze 两段分离）

整条链路是干净的两段，中间靠 `data/advisor_runs/{ts}/` 这个目录交接：

```
第一段（要 MongoDB + 联网抓 AKShare）          第二段（要 claude CLI 鉴权）
collect_data.py  ──写出──▶ data/advisor_runs/{ts}/ ──读入──▶ workflow-v3-advisor.js
                           ├ data_portfolio.json                  (跑 v3 子 Agent)
                           ├ data_pe / macro / ...                       │
                           ├ data_vitality.json（全18景气榜）            ▼
                           └ industry_list.json ◀── 决定深辩哪些行业  ingest_advice.py
```

- `./scripts/run.sh collect --user-id <id>` = 只跑第一段，产出数据目录。
- `./scripts/run.sh analyze --data-dir <路径>` = 只跑第二段，读目录里的文件。

⚠️ **接力陷阱**：`analyze` 直接吃目录里**已存在的** `industry_list.json`，不会重算。如果一方预生成了子集，另一方 analyze 时不会被覆盖。要换深辩范围，要么重新 `collect`，要么手动改 `industry_list.json` 后再 `analyze`。

### 4.1 文件总线（脱离 MongoDB 异地跑，B 档）

接力机制的延伸：让链路在**没有 MongoDB 的环境**（如远端 Pod）也能跑。所有改动是**叠加式**的——给文件输入开新分支，**绝不动现有 Mongo 全量路径**，两条路都必须跑得通。

```
本地(有Mongo)                          异地(无Mongo)
export_inputs.py ──holdings/watchlist/tier1.json──▶ collect_data.py --portfolio-file
                                                          │ (跳过全部 Mongo 调用)
                                                          ▼
                                    run.sh analyze --snapshot
                                                          │
build_snapshot.py ──overview.json / advice_latest.json──▶ 前端 VITE_STATIC_SNAPSHOT=1 直接 fetch
```

- `collect_data.py --portfolio-file <holdings.json>` 进入文件输入模式：持仓 / 扫描池 / Tier1 改读本地 JSON（`--watchlist-file` / `--tier1-file` 可空），跳过全部 Mongo。`score_all_industries()` 本就不碰 Mongo，照常联网全扫。基金穿透依赖 Mongo 基金库 → 文件模式降级为「仅直接个股敞口」。
- `build_snapshot.py --data-dir <ts> --snapshot` 产出与 API **完全同构**的 `overview.json` / `advice_latest.json`（复用 `ingest_advice.py` 的 `build_doc` + `paper.py` 的矩阵组装逻辑，保证字段契约一致），写到 `frontend/public/snapshot/`。
- **保证看得见**：编排器主循环包了 `try/catch`，无论 done / violations_found / crashed 三条出口，都先写 `run_report.json` + `run_report.md` 再返回。`run_report.py` 也能离线复盘任意历史目录：`python scripts/run_report.py --data-dir data/advisor_runs/<ts>`。它专门标红两个老坑：`Scout 候选全是已持仓 → 0 只新股票`、`industry_matrix 为空 → 前端必降级`。

⚠️ **改文件总线铁律**：任何新增能力都要**同时验证老路（Mongo 全量）和新路（文件模式）都通**，不许只顾一头。`data/` 已在 `.gitignore`；静态快照含持仓/处方，是敏感财务数据，推库务必私有仓库。

---

## 5. 行业深辩范围开关 `--industries`

行业有两层粒度，**决策粒度永远是 18 大投资主题 bucket**（`tradingagents/.../industry_buckets.py` 的 `BUCKETS`），不是数据源的 ~86 个同花顺细分板块。

| 档 | 函数 | 跑多全 | 性质 |
|----|------|--------|------|
| A 廉价雷达 | `score_all_industries()` | 全 18（非 LLM，近零成本）| 排景气榜，写 `data_vitality.json`，给前端全景视图 |
| B 昂贵深辩 | 研究员→反向者→裁判 | 见下方开关 | 真正花 LLM 钱的多 Agent 辩论 |

```bash
./scripts/run.sh all                   # 默认 scope：持仓 + watchlist + 景气 top3
./scripts/run.sh all --industries all  # 全量：全部可投资行业进深辩
./scripts/run.sh collect --industries all   # collect 阶段同样支持
```

- `scope`（默认）：`build_scan_pool()` 产出 = 持仓 + watchlist + 景气 top3 新方向。
- `all`：纳入全部**可投资** bucket（货币类「现金/债券固收/宽基/全球配置」由 `CURRENCY_BUCKETS` 过滤掉，那是大类资产层的活，不进行业深辩）。

**无估值准入闸**：景气 top3 只看景气排名进深辩，**不看估值**。估值约束交给下游每一层（研究员标注 → 跨行业裁判调 `final_weight` → PM 取保守买入区间偏 batch/conditional → cross_validator 警示 → 持仓 PE>90% 提示减仓）。即「景气度高但估值极端时**调权重而非否决**」——AI 这种贵但结构性长期最高的方向永远不会被踢出视野，也永远不会无脑追高满仓。

---

## 6. 设计铁律（改代码前必读，防止改歪）

1. **景气度 × 安全边际双因子**：景气高但估值极端时调权重，不直接否决。
2. **约束从大类层硬传递**：宏观 → 大类资产 → 行业 → PM，每层输出满足上游约束（股票额度 `stock_weight` 下传为行业层 `total_weight_limit`）。Portfolio Synthesizer 只验证链路完整性，不修正。
3. **辩论驱动质量**：每层都有对立角色，避免确认偏误。风控规则是硬约束，Risk Director 是建议，职责分开。
4. **目标是绝对收益**：让用户持久盈利，不跑赢基准、不追板块轮动。全量扫描是廉价雷达，不是决策引擎。
5. **无估值准入闸**：见第 5 节，估值只在下游调权重/买点。
6. **数据盲区 = 举证责任倒置；关键数据「拿不到就不分析」（硬闸）**：
   - `collect_data.py` 对采不到的市场/宏观数据**写 `null` + `data_availability` + 真实 `status`（success/partial/unavailable）**，**严禁**用 `0`/`中性`/`up_ratio=50` 伪装成真实读数（这是历史病根：`fetch_*` 失败时返回 0、collect 又读错 key，导致战略师永远看到「假中性」放心加仓）。
   - **硬闸（最高优先级）**：`collect_data.py` 采完市场温度后做关键数据校验，**关键源缺任一即 `return False` → `exit(1)`，整条链在进入 Agent 分析前中止**，绝不在数据盲区出处方。关键源 = ①宏观指标(PMI/利率) ②市场水温(涨跌广度 breadth) ③北向资金(north)；次要源（融资/Tier1/PE/敞口/景气）缺失仍只告警不阻断。命令行（`run.sh all/collect`）与前端 `/plan` API（`v3_advisor_runner.run_collect`）共用此咽喉点，中止原因会透传到前端。调试/接力可加 `--allow-partial-data` 绕过（缺数据改为告警放行）。
   - 兜底层（万一硬闸被 `--allow-partial-data` 绕过）：宏观裁判 / 战略师 / 大类裁判 / 防御师的 prompt 仍写死铁律：**`status≠success` 或关键字段 null 时进入数据盲区**——「未见看空信号」≠「可以加仓」，不确定性方向默认向下；盲区下 `total_weight_limit ≤50`、`cash_floor ≥20`、禁止压现金到地板/加股票到上限、禁止「承认高位又加满」的认知-行动矛盾。
   - 改这条链路任一环时，**各文件口径必须一致**：硬闸在 `scripts/collect_data.py`（关键源定义）+ `app/services/v3_advisor_runner.py`（原因透传）；盲区兜底在 `v3-macro-judge.md` + `v3-asset-strategist.md` + `v3-asset-defender.md` + `v3-asset-judge.md`。
7. **市场覆盖按链路分层，别假设组合顾问支持美股个票**：
   - 大类资产层：A股/港股 + 海外（纳指/标普/QDII/黄金）作为「全球配置」一整块敞口。
   - 行业景气雷达 + 行业深辩：**仅 A 股**（`score_all_industries()` 全是北向/A股PE分位/中国政策信号，18 bucket 申万口径，不拆美股行业）。
   - 组合顾问个股推荐（Scout/PM）：实跑**仅 A 股**。`market_tools` 技术上能取港股/美股（yfinance），但当前无触发路径，Tier1 自动研究（`trigger_auto_research`）写死 `ak.stock_individual_info_em`，**只认 A 股代码**。
   - 个股深度分析（`trading_graph.py`，独立链路）：支持 A股/港股/美股，结论暂未回流组合顾问 Tier1 库。
   - 想让组合顾问真正推荐美股个票 → 要接通景气雷达的美股档 + 让 Scout 走 us + 把个股分析结论回流 Tier1，这是「中/重档」改动，**别默认它已支持**。

---

## 7. 17 个 v3 子 Agent（`agents/advisor/`）

| 层 | 文件 | 职责 |
|----|------|------|
| 宏观 | `v3-macro-judge.md` | 宏观信号 → total_weight_limit / cash_floor |
| 大类 | `v3-asset-strategist.md` | 战略配置师（进攻）：6 大类偏进攻配比 |
| 大类 | `v3-asset-defender.md` | 防御配置师（避险）：挑战进攻倾向 |
| 大类 | `v3-asset-judge.md` | 大类裁判：综合 → 6 大类目标 + stock_weight 下传 |
| 行业 | `v3-industry-researcher.md` | B+C 三层数据 → 首次判断 |
| 行业 | `v3-industry-contrarian.md` | 挑战研究员，暴露盲点 |
| 跨行业 | `v3-cross-industry-judge.md` | 在 stock_weight 限额内分配 final_weight |
| 公司 | `v3-scout.md` | Go 行业内找候选标的，读 Tier1 横向比较 |
| 组合 | `v3-portfolio-analyst.md` | 持仓分析师：诊断现有持仓与敞口 |
| 组合 | `v3-portfolio-contrarian.md` | 组合反向者：挑战诊断，暴露集中风险 |
| PM | `v3-pm-aggressive.md` | 激进 PM：配额用满，重仓高评级 |
| PM | `v3-pm-conservative.md` | 保守 PM：保留缓冲，偏分批 |
| PM | `v3-pm-judge.md` | PM 裁判：综合两者，取保守买入区间 |
| 风控 | `v3-risk-pessimist.md` | 找最坏情景，挑战集中风险 |
| 风控 | `v3-risk-optimist.md` | 反驳过度保守，指出踏空风险 |
| 风控 | `v3-risk-judge.md` | 综合 → RiskAssessment |
| 合成 | `v3-portfolio-synthesizer.md` | 验证约束链 + 缺口处理 + 汇总 |

---

## 8. 真跑硬前置（`run.sh` 的 `check_prereqs` 会校验）

1. `--user-id` 必须是 24 位 hex（否则报错退出）。
2. Python，优先 `.venv/bin/python`，装好 `requirements.txt`（akshare/motor/pymongo 等）。
3. Claude Code CLI 已鉴权 —— LLM 推理这层靠本地 `claude -p` 驱动 workflow。
4. MongoDB 可达 —— `ingest_advice.py` 写 `portfolio_advice`，前端读这张表。
5. 联网 —— `collect_data.py` 抓 AKShare/Tushare 行情、北向、PE 分位。

> 文件总线（4.1 节）放宽其中两条：`--portfolio-file` 文件模式**不需要 MongoDB**（持仓/扫描池/Tier1 读本地 JSON），`--user-id` 校验也放宽为元信息标签；`--snapshot` 只产前端静态 JSON，不需要 claude CLI。但**真正跑 v3 分析（analyze）仍需 claude CLI 鉴权 + 联网**。

---

## 9. 改代码后的验证

- 改 Python：`.venv/bin/python -c "import <module>"` 做导入级冒烟 + `python -m pytest tests/ -v`。
- 改 JS 编排器：`node --check scripts/workflow-v3-advisor.js`。
- 改前端：`cd frontend && npm run build`（不要跑 `npm run dev`，那是阻塞命令）。
- 改文件总线脚本（`collect_data.py` 文件模式 / `build_snapshot.py` / `export_inputs.py` / `run_report.py`）：`python -m py_compile <file>` 语法检查 + 用合成 fixtures 跑一遍（这些脚本 `build_doc` 等是纯 stdlib，sandbox 里可真跑验证），并离线 `python scripts/run_report.py --data-dir <目录>` 确认报告正确。
- 端到端真跑需 MongoDB + 联网 + claude CLI，sandbox 环境跑不通时明确标注「未端到端验证」。

---

## 10. 要警惕的「孤儿模式」

本项目踩过的典型病根：**组件造好了但没插电**（函数实现完整却没有任何调用方）。例如曾经 `score_all_industries()` / `build_scan_pool()` 实现了全量扫描，但采数链路没人调用、没人写 `industry_list.json`，导致真跑只分析写死的 5 个行业。

改动涉及「新增能力」时，务必确认：**有没有真正接进 `collect_data.py` → `run.sh` → `workflow-v3-advisor.js` 这条链路**，而不是只写了个没人调的函数。grep 一下新函数的调用方，确认不是孤儿。

---

## 11. v4 分层独立深度投研系统（与 v3 并存）

v4 是一条**与 v3 完全并存、零侵入**的新链路：独立集合 `v4_units`、独立目录 `data/v4/`、独立编排器 `scripts/workflow-v4-advisor.js`、独立只读路由 `app/routers/portfolio_v4.py`。v3 链路一行不动，可灰度、可回退。完整规格见 `.kiro/specs/v4/`。

**核心抽象 = 分析单元（unit）**：七大类资产 → 行业 → 个股 + 各层配比，每个都是一个有稳定 `unit_id`、独立产物 JSON、独立五色状态、独立 TTL 的「单元」。触发只跑命中单元，绝不连带重跑其它。`unit_id` 形如 `asset:<class>` / `plan:<class>` / `alloc:portfolio` / `alloc:equity_industries` / `industry:<name>` / `stock:<code>` / `alloc:industry:<name>`。

### 11.1 触发命令（CLI，与 Web 分离）

```bash
./scripts/run_v4.sh analyze <unit-selector> [--user-id <id>] [--portfolio-file <path>] [--full]
./scripts/run_v4.sh refresh <unit-selector> ...   # 强制失效重跑，重绑最新上游指纹
./scripts/run_v4.sh status [--json]               # 列全部单元五色状态
./scripts/run_v4.sh scan   [--json]               # 仅置黄过期单元，绝不自动重跑
```

七大类 class：`equity / fixed_income / cash / commodity / precious_metal / real_estate / alternative`。

#### 快捷指令 → 真实命令（v4 对话触发）

| 用户说 | 实际执行 | 等价命令 |
|--------|----------|----------|
| `分析权益` / `analyze equity` | 权益大类深度分析 | `run_v4.sh analyze asset:equity` |
| `分析固收` / `分析债券` | 固收大类分析 | `run_v4.sh analyze asset:fixed_income` |
| `分析现金` | 现金大类分析 | `run_v4.sh analyze asset:cash` |
| `分析大宗` / `分析商品` | 大宗商品分析 | `run_v4.sh analyze asset:commodity` |
| `分析贵金属` / `分析黄金` | 贵金属分析 | `run_v4.sh analyze asset:precious_metal` |
| `分析房地产` / `分析 REIT` | 房地产分析 | `run_v4.sh analyze asset:real_estate` |
| `分析另类` / `分析虚拟币` | 另类投资分析 | `run_v4.sh analyze asset:alternative` |
| `跑资产配比` / `配比` | 七大类配比决策 | `run_v4.sh analyze alloc:portfolio` |
| `分析<行业>行业` / `深辩<行业>` | 行业深度辩论 | `run_v4.sh analyze industry:<行业>` |
| `行业配比` | 权益行业间配比 | `run_v4.sh analyze alloc:equity_industries` |
| `分析<代码>` | 个股独立分析 | `run_v4.sh analyze stock:<代码>` |
| `行业内配比 <行业>` | 行业内资金分配 | `run_v4.sh analyze alloc:industry:<行业>` |
| `<大类>投资方案` | 非权益差异化方案 | `run_v4.sh analyze plan:<class>` |
| `刷新<单元>` / `refresh <unit>` | 强制失效重跑 | `run_v4.sh refresh <unit-selector>` |
| `v4 状态` | 查看全部单元五色状态 | `run_v4.sh status --json` |
| `v4 扫描` / `扫描过期` | 仅置黄过期单元 | `run_v4.sh scan --json` |
| `跑全量 v4` / `全部分析` | 七大类+配比+非权益方案 | 见 §11.4 全量序列 |
| `导入 v4` | 代跑产物导入 Mongo | `import_v4.py --user-id <id>` |
| `v4 报告` / `体检` | 逐单元体检 | `run_report_v4.py` |
| `v4 快照` | 生成前端静态快照 | `build_snapshot_v4.py` |
| `我的持仓是…` / `更新持仓` / `录入持仓` | 解析口述 → 写入 holdings.json | AI 解析并写 `data/v4/_inputs/holdings.json` |
| `加一笔 XX` / `新买了 XX` | 追加持仓条目 | 读 → 追加 → 写回 |
| `卖了 XX` / `清仓 XX` | 移除持仓条目 | 读 → 删除 → 写回 |
| `看看我的持仓` / `当前持仓` | 展示持仓 | 读取并格式化展示 |

所有命令默认带 `--user-id $V4_USER_ID --portfolio-file data/v4/_inputs/holdings.json`。`分析` = 有缓存则跳过；`刷新` = 强制重跑。未指定行业/个股时 AI 应列出可选项让用户选择，**不猜测**。

详细意图解析规则见 Skill `.claude/skills/v4-advisor/SKILL.md`。

### 11.2 双跑文件总线（本地 ↔ AI 代跑，靠 git 传输）⚠️ 关键

v4 的 git 传输载体 = `data/v4/**/*.json` **单元粒度结构化文件**（diff 友好、可 review，非 dump/二进制，FR-009 AC9.3）。

```
本地: 编辑 data/v4/_inputs/holdings.json ──git push──▶ 私有仓
                                                          │ git pull
                                  AI 代跑: ./run_v4.sh analyze <unit> --portfolio-file data/v4/_inputs/holdings.json
                                                          │ 产出 data/v4/{assets,allocation,industries,stocks,plans}/*.json + _units.json
本地: git pull ◀──git push（AI 提交单元产物）─────────────┘
      python scripts/import_v4.py --user-id <id>   # 幂等 upsert v4_units，前端三层 Tab 即与代跑一致
```

**`.gitignore` 双跑路径约定（已落地，别再改回去）**：`data/` 整体忽略（隐私），但**仅 `data/v4/` 子树解除忽略**（`.gitignore` 末尾 `data/*` + `!data/v4/` + `!data/v4/**`）。其中 `data/v4/_locks/`（运行锁）、`data/v4/inputs/`（collect 中间输入包）、`data/v4/**/*.tmp`（原子写临时）再被排除——**只有单元信封 + `_units.json` + `_inputs/holdings.json` 进 git**。⚠️ `data/v4/` 含真实持仓/处方，**务必私有仓库**。

### 11.3 持仓推送格式（用户本地 → gitlab 的入口）

固定路径 `data/v4/_inputs/holdings.json`，格式（详见 `data/v4/_inputs/README.md` + `holdings.example.json`）：

```json
{"positions": [
  {"code": "600519", "name": "贵州茅台", "weight": 15, "market_value": 150000, "instrument_type": "stock"}
]}
```

字段：`code`（市场代码，现金/房产留空）、`name`（归类主依据）、`weight`(%)、`market_value`、`instrument_type`（`stock/etf/fund/bond/cash/other` 兜底归类）。名称关键词优先归类，未命中按 `instrument_type` 兜底；仍判不出 → `unclassified`（不丢弃）。

### 11.4 跑全量分析（拿到 holdings 后，按约束链自上而下）

```bash
H=data/v4/_inputs/holdings.json
for c in equity fixed_income cash commodity precious_metal real_estate alternative; do
  ./scripts/run_v4.sh analyze asset:$c --user-id <id> --portfolio-file $H; done
./scripts/run_v4.sh analyze alloc:portfolio --user-id <id> --portfolio-file $H   # 下传 equity_quota
# 权益深链：industry:<行业> → alloc:equity_industries → stock:<代码> → alloc:industry:<行业>
for c in fixed_income cash commodity precious_metal real_estate alternative; do
  ./scripts/run_v4.sh analyze plan:$c --user-id <id> --portfolio-file $H; done
python scripts/import_v4.py --user-id <id>   # 回传后导入
python scripts/run_report_v4.py              # 逐单元体检
python scripts/build_snapshot_v4.py          # （可选）前端静态快照 → frontend/public/snapshot/v4/
```

### 11.5 v4 设计铁律（沿用 v3 精神 + 单元化特有）

- 🚫 同 v3：**禁止 `llm.invoke()`**，LLM 决策全走 `agents/advisor/v4-*.md` 子 Agent + 编排器 `agent()`。
- 状态机 `v4_state.py` **只读、只报警、绝不触发重跑/改数值**（FR-005 / AC5.5）；约束链不满足只软提醒。
- 落盘**覆盖式只动本单元** + `version+1`（原子写 临时文件→rename），不触碰其它单元（AC9.4 / NFR4.2）。
- 只读路由不得有「点即跑 LLM」的写接口；重计算只在本地 / AI 代跑触发——**驱动方式有二**：① 本会话 agent 直跑（默认，无需 claude CLI，可 spawn subagent）；② `run_v4.sh` shell 出 `claude -p` 子进程（需 claude 鉴权）。两者产出同构信封，详见 §11.7 与 `docs/wiki/v4-ai-proxy-run.md`。
- **数据不静默降级**：环境缺数据源（AKShare 等）时，agent 直跑须用联网（web 搜索/抓取）补齐宏观/行情/估值，`evidence` 标 `verified`+来源；联网也取不到才标 `estimated/missing`，不得编造或套示例数字。
- 改 v4 同样守第 0 节铁律：改链路/入口/格式 → 同 commit 更新本节 + `README.md` + `.kiro/specs/v4/`。

### 11.6 改 v4 后的验证

- 改 Python：`python -m py_compile app/services/v4/*.py scripts/*v4*.py` + `python scripts/test/test_v4_unit_store.py`。
- 改编排器：`node --check scripts/workflow-v4-advisor.js`；改 `run_v4.sh`：`bash -n scripts/run_v4.sh`。
- 纯 Python 链路（collect_v4 归类 / build_snapshot_v4 / import_v4 --dry-run / run_report_v4）sandbox 里可用示例持仓真跑验证文件总线闭环；**端到端 LLM 真跑不强依赖 MongoDB / claude CLI**——本会话 agent 可直跑第 2 阶段（读输入包+联网补数+`v4_unit_cli.py write`），前端可走静态快照（`VITE_STATIC_SNAPSHOT=1`，无需 Mongo）。Mongo（在线 API）与 claude CLI（`claude -p` 子进程）都是可选增强，非必需。

### 11.7 AI 代跑落地步骤（本会话 agent 直跑）

把持仓交给 AI、AI 直接跑完整分析 → 存档 `data/v4/` → 用户 `git pull` 后前端解析，这条路径的**可执行步骤、各单元 payload schema、联网取数与存档/快照细节**统一见 **`docs/wiki/v4-ai-proxy-run.md`**。要点：
- 第 2 阶段执行体 = 当前对话的 AI（可 spawn subagent ≤3 并发），**不需要 `claude` CLI 鉴权**；`run_v4.sh` 无 claude 退出码 2 不是阻塞，改走 agent 直跑。
- 缺数据源**联网补齐**而非降级；存档为 `data/v4/**/*.json` 单元信封，前端走**静态快照**即可，**MongoDB 可选**。

---

## 技术栈

Python 3.12+ / FastAPI 0.115+ / Vue 3.5+ + Vite + Element Plus / MongoDB + Redis。
API 前缀 `/api/`，统一响应 `{code, msg, data}`。
