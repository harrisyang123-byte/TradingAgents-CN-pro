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

## 技术栈

Python 3.12+ / FastAPI 0.115+ / Vue 3.5+ + Vite + Element Plus / MongoDB + Redis。
API 前缀 `/api/`，统一响应 `{code, msg, data}`。
