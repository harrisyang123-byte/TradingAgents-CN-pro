# AGENTS.md — TradingAgents-CN 主 Agent 指南

> 本文件是本项目**唯一权威**的 Agent 指南（single source of truth）。
> 任何 Agent（Claude Code / Cursor / DevGenie 平台 / 其他）动手前先读本文件。
> `CLAUDE.md` 只是指向本文件的指针。
>
> **当前主线 = v4 分层独立深度投研**（§1–§9）。上一代 v3 组合顾问**逐步退役中**，见 §10。

---

## 0. 第一铁律：文档即代码契约

**改了代码就必须同步本文件和 `README.md`。** 本项目反复踩的坑就是「文档和代码两套、互相飘移」——退役的架构还写在文档里骗后来人。所以：

- 改了链路 / 入口 / 开关 / Agent 职责 / 字段 → **同一个 commit 里**更新 `AGENTS.md` + `README.md` + `.kiro/specs/v4/`。
- 发现文档与代码不符 → 以代码为准，**顺手修文档**，不要绕过。
- 不确定哪个是真的 → 去代码里核实（`scripts/run_v4.sh`、`collect_v4.py`、`workflow-v4-advisor.js`、`agents/advisor/v4-*.md`），不要凭印象。

---

## 1. 主线：v4 分层独立深度投研

把投研拆成常驻的「**分析单元（unit）**」：七大类资产 → 行业 → 个股 + 各层配比，每个都是一个有稳定 `unit_id`、独立产物 JSON、独立五色状态、独立 TTL 的单元。触发只跑命中单元，绝不连带重跑其它。独立集合 `v4_units`、独立目录 `data/v4/`、独立编排器 `scripts/workflow-v4-advisor.js`、独立只读路由 `app/routers/portfolio_v4.py`。完整规格见 `.kiro/specs/v4/`。

`unit_id` 形如：`asset:<class>` / `plan:<class>` / `alloc:portfolio` / `alloc:equity_industries` / `industry:<name>` / `stock:<code>` / `alloc:industry:<name>`。七大类 class：`equity / fixed_income / cash / commodity / precious_metal / real_estate / alternative`。

约束链自上而下硬传递：**宏观 → 大类配比 equity_quota → 行业配比(≤quota) → 个股配比(≤行业权重)**；上游变更只置黄软提醒、不强制重跑。

---

## 2. 触发命令（CLI，与 Web 分离）

```bash
./scripts/run_v4.sh analyze <unit-selector> [--user-id <id>] [--portfolio-file <path>] [--full]
./scripts/run_v4.sh refresh <unit-selector> ...   # 强制失效重跑，重绑最新上游指纹
./scripts/run_v4.sh status [--json]               # 列全部单元五色状态
./scripts/run_v4.sh scan   [--json]               # 仅置黄过期单元，绝不自动重跑
```

### 快捷指令 → 真实命令（v4 对话触发）

| 用户说 | 等价命令 |
|--------|----------|
| `分析权益/固收/现金/大宗/贵金属/房地产/另类` | `run_v4.sh analyze asset:<class>` |
| `跑资产配比` / `配比` | `run_v4.sh analyze alloc:portfolio` |
| `分析<行业>行业` / `深辩<行业>` | `run_v4.sh analyze industry:<行业>` |
| `行业配比` | `run_v4.sh analyze alloc:equity_industries` |
| `分析<代码>` | `run_v4.sh analyze stock:<代码>` |
| `行业内配比 <行业>` | `run_v4.sh analyze alloc:industry:<行业>` |
| `<大类>投资方案` | `run_v4.sh analyze plan:<class>` |
| `刷新<单元>` | `run_v4.sh refresh <unit-selector>` |
| `v4 状态/扫描/报告/快照` | `status` / `scan` / `run_report_v4.py` / `build_snapshot_v4.py` |
| `我的持仓是…/加一笔/卖了/看持仓` | AI 读写 `data/v4/_inputs/holdings.json` |

默认带 `--user-id $V4_USER_ID --portfolio-file data/v4/_inputs/holdings.json`。`分析`=有缓存则跳过；`刷新`=强制重跑。未指定行业/个股时 **AI 列选项让用户选，不猜测**。详细意图解析见 Skill `.claude/skills/v4-advisor/SKILL.md`。

---

## 3. 双跑文件总线（本地 ↔ AI 代跑，靠 git 传输）⚠️ 关键

v4 的 git 传输载体 = `data/v4/**/*.json` **单元粒度结构化文件**（diff 友好、可 review，非 dump/二进制，FR-009 AC9.3）。

```
本地: 编辑 data/v4/_inputs/holdings.json ──git push──▶ 私有仓
                                                          │ git pull
                                  AI 代跑: ./run_v4.sh analyze <unit> --portfolio-file data/v4/_inputs/holdings.json
                                                          │ 产出 data/v4/{assets,allocation,industries,stocks,plans}/*.json + _units.json
本地: git pull ◀──git push（AI 提交单元产物）─────────────┘
      python scripts/import_v4.py --user-id <id>   # 幂等 upsert v4_units，前端三层 Tab 即与代跑一致
```

**`.gitignore` 双跑路径约定（已落地，别再改回去）**：`data/` 整体忽略（隐私），但**仅 `data/v4/` 子树解除忽略**（`data/*` + `!data/v4/` + `!data/v4/**`）。其中 `data/v4/_locks/`（运行锁）、`data/v4/inputs/`（collect 中间输入包）、`data/v4/**/*.tmp`（原子写临时）再被排除——**只有单元信封 + `_units.json` + `_inputs/holdings.json` 进 git**。⚠️ `data/v4/` 含真实持仓/处方，**务必私有仓库**。

### 3.1 持仓推送格式（用户本地 → gitlab 的入口）

固定路径 `data/v4/_inputs/holdings.json`（详见 `data/v4/_inputs/README.md` + `holdings.example.json`）：

```json
{"positions": [
  {"code": "600519", "name": "贵州茅台", "weight": 15, "market_value": 150000, "instrument_type": "stock"}
]}
```

字段：`code`（市场代码，现金/房产留空）、`name`（归类主依据）、`weight`(%)、`market_value`、`instrument_type`（`stock/etf/fund/bond/cash/other` 兜底）。名称关键词优先归类，未命中按 `instrument_type` 兜底；仍判不出 → `unclassified`（不丢弃）。

---

## 4. 跑全量分析（拿到 holdings 后，按约束链自上而下）

```bash
H=data/v4/_inputs/holdings.json
for c in equity fixed_income cash commodity precious_metal real_estate alternative; do
  ./scripts/run_v4.sh analyze asset:$c --user-id <id> --portfolio-file $H; done
./scripts/run_v4.sh analyze alloc:portfolio --user-id <id> --portfolio-file $H   # 下传 equity_quota
# 权益深链：industry:<行业> → alloc:equity_industries → stock:<代码> → alloc:industry:<行业>
for c in fixed_income cash commodity precious_metal real_estate alternative; do
  ./scripts/run_v4.sh analyze plan:$c --user-id <id> --portfolio-file $H; done
python scripts/import_v4.py --user-id <id>   # 回传后导入（可选）
python scripts/run_report_v4.py              # 逐单元体检
python scripts/build_snapshot_v4.py          # （可选）前端静态快照 → frontend/public/snapshot/v4/
```

---

## 5. v4 Agent 阵容 + 三套核心方法论

**分层角色**（每层对立角色辩论 + 总监 reflection/反骑墙；全部 `tools:[Read]`，只消费 data-desk 输入包，唯一带联网工具的是 data-desk）：

| 层 | 角色 |
|----|------|
| 通用 | `v4-data-desk`——宏观 `macro_source.py`(AKShare 22 指标) + **A股个股 `stock_source.py`(股价/市值/PE/PB/PE分位/财务/涨幅)** |
| 大类 | `v4-asset-analyst-macro/flow/policy`(3视角) + `v4-asset-bull/bear`(多空3轮) + `v4-asset-director` + `v4-allocation-director`(配比) |
| 行业 | `v4-industry-bull/bear` + **`v4-industry-chokepoint`(产业链瓶颈分析师)** + `v4-industry-director`(整合 chokepoint_map) + `v4-industry-allocator` |
| 个股 | **`v4-stock-analyst-financial/competitive/valuation`(3分析师分队)** + `v4-stock-bull/bear` + `v4-stock-director`(预期差拍板) |

**方法论 1 — Chokepoint 供应链瓶颈**（`planning/v4/chokepoint-framework.md`）：自下而上逆向工程产业链，四维判定（不可替代/供给集中/产能刚性/价值卡位）+ 替代路径 + **市场发现度**，定位"物理卡脖子且市场没发现"的环节。混合分队：瓶颈分析师出骨架→主 agent 对 top 瓶颈派专项调研员深挖→director 核实。

**方法论 2 — 预期差选股**（`planning/v4/stock-selection-theory.md`）：**买卖看预期差（基本面将兑现 − 价格已 price-in），不看涨幅/PE 分位**（A/B 验证：分位法会让你 88 元不敢买中际旭创、错过 11 倍）。三锚：隐含增速缺口/定价充分度/催化。

**方法论 3 — 结果闭环反思 + 反骑墙**：总监开辩前读上一版 verdict → 输出 reflection；证据势均力敌才中性，否则站队，数据盲区降 confidence 而非骑墙。

payload 字段权威定义见 `chokepoint-framework.md §9`（`chokepoint_map`/`top_chokepoints`/`expectation_gap`/`chokepoint_score`/`discovery_level`，向后兼容可选）。

---

## 6. v4 设计铁律（改代码/prompt 前必读）

1. 🚫 **禁止 `llm.invoke()`**：LLM 决策全走 `agents/advisor/v4-*.md` 子 Agent + 编排器 `agent()`。
2. **数据铁律（强制，10 个分析角色已写入）**：分析 Agent **严禁自产价格/PE/市值/目标价数字**——唯一来源 = data-desk 联网核实值（个股走 `stock_source.py`）；无则标 missing，绝不编造（中际旭创"420 vs 真实1000"事故根治）。director 落盘前须剔除/核实 subagent 产出的数字。
3. **数据不静默降级**：环境缺数据源（AKShare 等）时，agent 直跑须用联网（web 搜索/抓取）补齐宏观/行情/估值，`evidence` 标 `verified`+来源；联网也取不到才标 `estimated/missing`。**严禁用 0/中性/示例数字伪装真实读数**（这是 v3 时代的病根）。
4. **MECE**：每一分钱落进恰好一个大类（含 `unclassified` 待穿透桶），不漏不重；Σ 校验含归零类。
5. 状态机 `v4_state.py` **只读、只报警、绝不触发重跑/改数值**（FR-005）；约束链不满足只软提醒。
6. 落盘**覆盖式只动本单元** + `version+1`（原子写 临时文件→rename），不触碰其它单元（AC9.4）。
7. 只读路由不得有「点即跑 LLM」的写接口；重计算只在本地 / AI 代跑触发。
8. **景气度 × 安全边际 × 预期差**：景气定行业、瓶颈定环节、预期差定个股买卖、安全边际把关买点；估值约束只调权重/买点，不做准入否决（避免错过 AI 等成长赛道）。
9. **市场覆盖分层**：A股个股直接（stock_source）、港股直接可投、海外（美股/欧股/台股）物理瓶颈标的通过 QDII/主题基金获取敞口；大类层把海外作为「全球配置」一整块敞口。

---

## 7. 改 v4 后的验证

- 改 Python：`python -m py_compile app/services/v4/*.py scripts/*v4*.py` + `python scripts/test/test_v4_unit_store.py`。
- 改编排器：`node --check scripts/workflow-v4-advisor.js`；改 `run_v4.sh`：`bash -n scripts/run_v4.sh`。
- 改前端：`cd frontend && npx vue-tsc --noEmit`（不要跑 `npm run dev`，阻塞命令）。
- 纯 Python 链路（collect_v4 / build_snapshot_v4 / import_v4 --dry-run / run_report_v4）sandbox 里可用示例持仓真跑验证。**端到端 LLM 真跑不强依赖 MongoDB / claude CLI**——本会话 agent 直跑第 2 阶段（读输入包+联网补数+`v4_unit_cli.py write`），前端走静态快照（`VITE_STATIC_SNAPSHOT=1`，无需 Mongo）。Mongo 与 claude CLI 都是可选增强。

---

## 8. AI 代跑落地步骤（本会话 agent 直跑，模式 A）

把持仓交给 AI、AI 直接跑完整分析 → 存档 `data/v4/` → 用户 `git pull` 后前端解析。**可执行步骤、各单元 payload schema、联网取数与存档/快照细节统一见 `docs/wiki/v4-ai-proxy-run.md`**。要点：
- 第 2 阶段执行体 = 当前对话的 AI（可 spawn subagent ≤3 并发、不嵌套、≤500字摘要），**不需要 `claude` CLI 鉴权**；`run_v4.sh` 无 claude 退出码 2 不是阻塞，改走 agent 直跑。
- **模式 A 角色分工**：主 agent 只做①联网取数（扮演 data-desk）②编排+最终拍板（director，含 reflection+反骑墙）；3 分析师 + 多空辩论交给 subagent（喂角色 prompt + 已核实数据让其扮演）。subagent 无 web 工具，凡需联网的一律主 agent 取后喂给它。
- 缺数据源**联网补齐**而非降级；存档为 `data/v4/**/*.json` 单元信封，前端走**静态快照**即可，**MongoDB 可选**。

---

## 9. 改 v4 要警惕的「孤儿模式」

本项目踩过的病根：**组件造好了但没插电**（函数实现完整却没有调用方）。改动涉及「新增能力」时，确认它真正接进了 `collect_v4.py → run_v4.sh → workflow-v4-advisor.js` 链路，grep 新函数的调用方，别留孤儿。例：行业 `chokepoint_map` 字段——既要瓶颈分析师产出，又要 director 整合透传、`build_industry_detail` 透传到快照、前端渲染，缺一环就「看不见」。

---

## 10. 上一代：v3 组合顾问（退役中）

v3 是已上线的上一代组合顾问，**正逐步被 v4 取代**，保留用于过渡/回溯。改 v3 同守 §0 铁律。

**链路**（单一规范路径，LangGraph 大脑已退役）：
```
前端「组合分析」/对话「分析」/run.sh → v3_advisor_runner.py(两阶段)
  → collect_data.py → workflow-v3-advisor.js(claude -p 跑 v3 子 Agent) → ingest_advice.py
  → portfolio_advice 集合 → 前端 Overview 读
```
编排器阶段：`macro→asset→industry→scout→portfolio→pm→synth`（Step 0-7）。

**触发**：`./scripts/run.sh all --user-id <id>`；两段分离 `collect`（要 Mongo+联网）/ `analyze --data-dir <ts>`（要 claude CLI）；文件总线 `export_inputs.py` → `collect --portfolio-file` → `analyze --snapshot`。行业深辩范围 `--industries scope|all`。

**17 个 v3 子 Agent**（`agents/advisor/v3-*.md`）：宏观 `v3-macro-judge` / 大类 `v3-asset-strategist·defender·judge` / 行业 `v3-industry-researcher·contrarian` + `v3-cross-industry-judge` / 公司 `v3-scout` / 组合 `v3-portfolio-analyst·contrarian` / PM `v3-pm-aggressive·conservative·judge` / 风控 `v3-risk-pessimist·optimist·judge` / 合成 `v3-portfolio-synthesizer`。

**v3 沿用至今的关键铁律（v4 也继承精神）**：
- **数据盲区硬闸**：`collect_data.py` 关键源（宏观PMI/利率、市场广度breadth、北向）缺任一即中止整条链（`exit(1)`），绝不在数据盲区出处方；`--allow-partial-data` 可绕过转告警。采不到写 `null`+`status`，**严禁用 0/中性伪装**。
- **市场覆盖**：v3 行业雷达/个股推荐**仅 A 股**（Tier1 `ak.stock_individual_info_em` 只认 A 股码）；大类层含海外敞口；个股深度分析 `trading_graph.py`（独立链路，保留）支持 A/港/美股。

> v3 与 v4 零侵入并存，写不同集合/目录；v4 成熟后 v3 链路整体下线。详细文档：`docs/wiki/{industry-layer-rebuild,decision-layer-rebuild,portfolio-advisor-engine}.md`。

---

## 技术栈

Python 3.12+ / FastAPI 0.115+ / Vue 3.5+ + Vite + Element Plus / MongoDB + Redis（v4 前端可走静态快照，Mongo 可选）。API 前缀 `/api/`，统一响应 `{code, msg, data}`。
