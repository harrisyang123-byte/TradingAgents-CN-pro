# AGENTS.md — TradingAgents-CN 主 Agent 指南

> 本文件是本项目**唯一权威**的 Agent 指南（single source of truth）。
> 任何 Agent（Claude Code / Cursor / DevGenie 平台 / 其他）动手前先读本文件。
> `CLAUDE.md` 只是指向本文件的指针。
>
> **当前主线 = v4 分层独立深度投研**（§1–§9）。上一代 v3 组合顾问**逐步退役中**，见 §10。

---

## 🚨 RULE-DATA-VERIFIED 永久红线（2026-06-14 用户血泪固化,代码层强制,无法绕过）

**所有数字字段(TAM/CAGR/渗透率/份额/forward营收/EPS/目标价/可比PE)必须有 verified_source URL,严禁主 agent 凭训练记忆产出。违反 = 欺骗用户 = 立即标违规。**

### 强制校验链(代码层 4 层防御)
1. **认知层**(本红线): 任何 agent 看到这条必须先停下确认数据来源
2. **数据契约层**: `app/services/v4/stock_data_contract.py::EXPERT_VALUATION_MUST_VERIFIED` 校验函数,每个数字字段必须含 `verified_sources: [URL列表 ≥3]`
3. **代码强制层**: `scripts/v4_unit_cli.py write` 落盘前调用契约校验,缺 verified_sources → exit=4 拒绝落盘 + 红色错误信息
4. **辩证铁律**: `planning/v4/project-master-prompt.md §7-bis` 详细规则

### 血泪教训(避免重复)
- **通富 future_tam $157B事故**(2026-06-14): 主 agent 凭训练知识填"全球先进封装$157B" → 实际 Yole verified $80B,**虚高 96%**。下游 future_share/forward EPS/target_price 全部错误推导,差点误导用户加仓。
- **新易盛 target 三次反转**(2026-06-14): v1 ¥480-600(凭记忆建仓) → v2 ¥266-416(可比PE选低,说"透支") → critic 修正 v3 ¥500-620(才接近真值)。**没有 critic 自查,我会一直错下去**。

### 当违反此红线时
- 立即停止后续推导链(因为下游全错)
- 标 `data_status: "🚨 RULE_DATA_VERIFIED_VIOLATED"` 并诚实告诉用户
- 重新走 verified 流程: web_search ≥3 独立源 + 标 URL + 派生子赛道
- 严禁修复时再次拍脑袋(典型反模式: 改一个数字推导链不动)

### Trigger 信号(自检)
- 我正在写 TAM/份额/目标价数字 → **是否有 verified_source URL?** 没有 → 立即停下取数
- 我正在引用"$XXB" → **来自哪份报告?年份?状态?** 答不出 → 删除/标 missing
- 我说"派生自行业层" → **行业层这个数字真有吗?是不是凭记忆移植?** 不确定 → 实际打开行业 JSON 核对

---

## 0. 第一铁律：文档即代码契约

**改了代码就必须同步本文件和 `README.md`。** 本项目反复踩的坑就是「文档和代码两套、互相飘移」——退役的架构还写在文档里骗后来人。所以：

- 改了链路 / 入口 / 开关 / Agent 职责 / 字段 → **同一个 commit 里**更新 `AGENTS.md` + `README.md` + `.kiro/specs/v4/`。
- 发现文档与代码不符 → 以代码为准，**顺手修文档**，不要绕过。
- 不确定哪个是真的 → 去代码里核实（`scripts/run_v4.sh`、`collect_v4.py`、`workflow-v4-advisor.js`、`agents/advisor/v4-*.md`），不要凭印象。

---

## 0bis. 严格全流程铁律（2026-06-13 用户拍板,血泪教训）

**禁止"为了快/避免 timeout/省 context"简化跑分析单元**。具体：

- 5+1 五力 + 6 轮辩论 + 3 方风险 + sentiment + critic = **完整 17 个 stage,缺一不算"真单元"**
- subagent failed 时**先重试 1 次**(换更小的 prompt 或拆 stage),第 2 次仍 fail 才主 agent 接管
- **主 agent 接管的 stage 必须在 payload 里标 `data_status: "synthesized_by_main_agent"`** 让用户在前端可见
- critic 评 NEEDS_CHANGES 时**必须真重 spawn critic 复核 v3-final**,不能"主 agent 自评 84 分"绕过 critic
- 所有"简化版"产出必须在 `reflection.self_check` 里诚实标注是简化的(不能号称真全流程)
- v4_unit_cli.py write 已通过 `payload.credibility.final_verdict=ACCEPT` 拦截 NEEDS_CHANGES, **不能用 --skip-critic 绕过**(除非真紧急)

**违反将让所有"质量改造"沦为伪改造,等同欺骗用户。**

---

## 0ter. 信息流转全量铁律（2026-06-13 用户拍板"满血版分析",对齐 TradingAgents 输入全量原则）

**TradingAgents 实际机制**(看源码 `bull_researcher.py` 等): 每个 debater 接收完整 5 份报告 (market/sentiment/news/fundamentals + history) ≈ 15000-20000 字/次。
**v4 之前实际跑**: spawn task 是主 agent 手写 ~800-1500 字精简事实摘要 → 缩水 90%+。

**新铁律**: spawn 时必须把上一阶段产出**完整 JSON 字符串化塞入 task**, 不得精简。具体:
- spawn 5 力 agent 时: 完整 data-desk inputs JSON + 上一阶段已跑的力的完整产出
- spawn integrator 时: 5 力 5 个 agent 完整 JSON 全部
- spawn bull/bear 时: 4 分析师完整 JSON + 5+1 整合者完整 JSON + sentiment 完整 JSON + 历史辩论 history 累积
- spawn 3 方风险辩论时: bull/bear 完整 history + 4 分析师完整 JSON
- spawn critic 时: director verdict 完整 payload (不是字段摘要)

**触底约束**: 单次 spawn 输入字数预期 5000-15000 字 (vs 之前 1500), 输入越长 timeout 风险升高 30-50%, 但**质量优先**——失败时主 agent 接管 (按 §0bis 铁律), 不简化输入。

**为什么必要**: 输入精简意味着 subagent 看不到细节,论点空洞、数据引用流于形式、辩论沦为立场对撞。这是用户反复指出的"建议言之无物"根本原因之一。

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
| 通用 | `v4-data-desk`——宏观 `macro_source.py`(AKShare 22 指标) + **A股个股 `stock_source.py`(股价/市值/PE/PB/PE分位/财务/涨幅/**价值创造 verified ROIC·FCF·净利率**)** |
| 大类 | `v4-asset-analyst-macro/flow/policy`(3视角) + `v4-asset-bull/bear`(多空3轮) + `v4-asset-director` + `v4-allocation-director`(配比) |
| 行业 | `v4-industry-bull/bear` + **`v4-industry-chokepoint`(产业链瓶颈分析师)** + `v4-industry-director`(整合 chokepoint_map) + `v4-industry-allocator` |
| 个股 | **`v4-stock-analyst-financial/competitive/valuation`(3分析师分队)** + `v4-stock-bull/bear` + `v4-stock-director`(预期差拍板) |
| 质量闸门 | **`v4-investor-critic`**(芒格/段永平/Serenity/达里奥四视角评审,ACCEPT\|NEEDS_CHANGES;标准已内化进各层 director) |
| 元指导 | **`v4-chief-investment-officer`**(首席投资官+投委会,以"用户持久盈利"审视系统方向:可信/能用/连得上/会学/值得,识别假专业与过度工程) |

**方法论 1 — Chokepoint 瓶颈 + 波特五力**（`planning/v4/chokepoint-framework.md`）：四维判定（不可替代/供给集中/产能刚性/价值卡位）定"卡不卡脖子" + **波特五力**（进入者/替代品/买方/供方/同业竞争）定"利润能否留住"(A/B验证加五力85 vs 78) + **市场发现度**。瓶颈→`investment_map`(推荐个股+卡位排序+为什么是它)落到"买什么"。

**方法论 2 — 预期差选股 + 估值推导链**（`planning/v4/stock-selection-theory.md`）：**买卖看预期差（基本面将兑现 − 价格已 price-in），不看涨幅/PE 分位**（A/B验证：分位法会让你88元不敢买中际旭创错过11倍）。三锚：隐含增速缺口/定价充分度/催化。**买点/目标价必须有 `valuation_basis` 推导链**（目标价=forward指标×目标倍数(对标谁)，买点=安全边际/PB/DCF），禁拍脑袋。

**方法论 3 — forward_view 前瞻视野**（A/B 测试2次 89/82 vs 52）：宏观从回看升级到前瞻,11维(日历+共识+预期差+三情景+仓位/IV+假设证伪+尾部+跨市场+触发监控),触发用绝对阈值;三层 director 全内化(不增 agent)。

**方法论 4 — 结果闭环 + 回测验证 + 反骑墙**：director 读上一版 verdict 输出 reflection;**`v4_replay.py` 回测 + `historical_alpha`(判断价→实际涨跌算 hit/miss) + `v4_quarterly_review.py` 季度复盘**,critic 铁律0:上次 miss 必须答"这次为何对";证据势均力敌才中性否则站队,数据盲区降 confidence。

payload 字段权威定义见 `chokepoint-framework.md §9`（`chokepoint_map`(含 five_forces)/`top_chokepoints`/`investment_map`/`expectation_gap`/`chokepoint_score`/`discovery_level`/`valuation_basis`/`forward_view`/`price_at_judgment`/`historical_alpha`，向后兼容可选）。

---

## 6. v4 设计铁律（改代码/prompt 前必读）

1. 🚫 **禁止 `llm.invoke()`**：LLM 决策全走 `agents/advisor/v4-*.md` 子 Agent + 编排器 `agent()`。
2. **数据铁律（强制，10 个分析角色已写入）**：分析 Agent **严禁自产价格/PE/市值/目标价数字**——唯一来源 = data-desk 联网核实值（个股走 `stock_source.py`）；无则标 missing，绝不编造（中际旭创"420 vs 真实1000"事故根治）。director 落盘前须剔除/核实 subagent 产出的数字。

3. **价值创造维度铁律（2026-06-14 用户拍板补全，回答"公司未来值多少钱"）**：个股分析必含价值创造四维——①TAM 天花板+渗透率阶段(成长上限) ②ROIC vs WACC(创造/毁灭价值，用 ROIC 不用被杠杆污染的 ROE) ③管理层资本配置(再投资/并购/分红回购质量) ④正向 DCF 与反向 DCF+多派别三角验证。**ROIC/FCF 计算密集项用 AKShare `stock_source` verified 精算**(A/B 测试: 估算法35 vs 计算法85，主 agent 估精确点值=拍脑袋)；取不到才给区间+稳健性检验。数据契约 24 MUST(加价值创造组 6)；critic 6.9 价值创造四问必查。

4. **★计算密集 vs 综合判断铁律（2026-06-14 用户拍板"未来市场分析要经过计算的，原 subagent 计算或者主 agent 计算可能拍脑袋"，永久铁律）**：判定何时该新增 verified 数据源 / 何时只改 .md 提示词,**避免 ROIC A/B 测试式拍脑袋偏差(主 agent 估算 35 vs verified 85,偏差 50)再次发生**:
   - **第一类(必须 verified,主 agent 严禁自产)**: 财务比率(ROIC/ROE/FCF/EPS/净利率) → AKShare `stock_financial_abstract`; 价格/市值/PE/PB → AKShare `stock_zh_a_daily`; **TAM 当前/2030E/CAGR/渗透率%** → web_search ≥3 个独立来源(IDC/marketsandmarkets/Gartner/工信部)+标 URL+status verified; 宏观 22 指标 → AKShare/官方源
   - **第二类(综合判断,改 .md 即可不新增 agent)**: 多空辩论/风险辩论/chokepoint 卡位/forward_view 多维/stance/方向/仓位/渗透率阶段判定/forward PEG 解读 → 让 subagent 用 verified 数据辩论, 禁止编造数据范围内的数字
   - **何时真要新增 subagent**: 仅当现有 agent 阵容(allocator/bear/bull/chokepoint/director + 个股 5 力专项+sentiment+3 方风险) 无法承载的全新分析视角才新增。已有视角覆盖 → 改 .md(本次未来市场属此类: bull/bear/director/critic 分别加必辩/必查项)
   - **正确做法**: ① 优先找 verified 接口/源 ② 取不到则联网 web_search ③ 实在取不到才标 missing 或 estimated+区间(不给伪精确点值) ④ 绝不让主 agent/subagent 凭训练记忆编数字
   - **★7 把辩证分析尺(2026-06-14 用户拍板"除了网上取数也要有自己分析方法论")**: 光有 verified 数字还不够, subagent 必须用方法论戳穿水分。详见 `v4-industry-director.md` 的 `_methodology` 字段:
     - ①TAM三角验证(≥3 独立源, 差异>30% 标分歧不调和) ②TAM拆解还原(用户数×ARPU×渗透率反推合理性) ③CAGR久期(历史可比行业判高增速持续年数) ④渗透率类比(智能机/EV S曲线映射) ⑤forward PEG跨期对比(同类成长股同期估值) ⑥龙头瓜分检验(top3/top5 集中度判二三线空间) ⑦景气先行指标交叉(≥3 同向才确认方向)
     - **应用规则**: verdict.summary 必须显式用 ≥3 把尺, 不能只堆数字。critic 6.11.x 必查
   - 详见 `planning/v4/project-master-prompt.md §7-bis` 完整 cheat sheet

5. **数据不静默降级**：环境缺数据源（AKShare 等）时，agent 直跑须用联网（web 搜索/抓取）补齐宏观/行情/估值，`evidence` 标 `verified`+来源；联网也取不到才标 `estimated/missing`。**严禁用 0/中性/示例数字伪装真实读数**（这是 v3 时代的病根）。
6. **MECE**：每一分钱落进恰好一个大类（含 `unclassified` 待穿透桶），不漏不重；Σ 校验含归零类。

7. **MECE 反偷懒铁律(2026-06-14 用户拍板防止借'少开 agent'偷懒)**: "少开 agent"原则不得作为偷懒借口。当某分析维度在现有 agent 阵容中无对应职责,**必须新建专门 subagent**, 而不是让现有 agent 凑合做(否则=草草敷衍)。
   - 判定**必须新建**: ① 某维度在现有阵容(allocator/bear/bull/chokepoint/director+critic+5力+sentiment+3风险辩论)中无 agent 职责对应; ② 现有 agent 兼做但质量明显不足(如 critic 兼 6.12 自查暴露 NEEDS_CHANGES 反复); ③ 主 agent 想为省时间兼做 → 触发本铁律禁主 agent 接管,必须 spawn
   - 当前应新建(本会话暴露的): `v4-stock-valuation-auditor.md`(expert_valuation 推导链独立审计)/`v4-market-scanner.md`(全市场 ROIC/PE/增速筛选)/`v4-alpha-hunter.md`(未识别 alpha 深挖)
   - 详见 `planning/v4/project-master-prompt.md §3 反偷懒铁律`
7. 状态机 `v4_state.py` **只读、只报警、绝不触发重跑/改数值**（FR-005）；约束链不满足只软提醒。
8. 落盘**覆盖式只动本单元** + `version+1`（原子写 临时文件→rename），不触碰其它单元（AC9.4）。
9. 只读路由不得有「点即跑 LLM」的写接口；重计算只在本地 / AI 代跑触发。
10. **景气度 × 安全边际 × 预期差**：景气定行业、瓶颈定环节、预期差定个股买卖、安全边际把关买点；估值约束只调权重/买点，不做准入否决（避免错过 AI 等成长赛道）。
11. **市场覆盖分层**：A股个股直接（stock_source）、港股直接可投、海外（美股/欧股/台股）物理瓶颈标的通过 QDII/主题基金获取敞口；大类层把海外作为「全球配置」一整块敞口。

---

## 7. 改 v4 后的验证

- 改 Python：`python -m py_compile app/services/v4/*.py scripts/*v4*.py` + `python scripts/test/test_v4_unit_store.py`。
- 改编排器：`node --check scripts/workflow-v4-advisor.js`；改 `run_v4.sh`：`bash -n scripts/run_v4.sh`。
- 改前端：`cd frontend && npx vue-tsc --noEmit`（不要跑 `npm run dev`，阻塞命令）。
- 纯 Python 链路（collect_v4 / build_snapshot_v4 / import_v4 --dry-run / run_report_v4）sandbox 里可用示例持仓真跑验证。**端到端 LLM 真跑不强依赖 MongoDB / claude CLI**——本会话 agent 直跑第 2 阶段（读输入包+联网补数+`v4_unit_cli.py write`），前端走静态快照（`VITE_STATIC_SNAPSHOT=1`，无需 Mongo）。Mongo 与 claude CLI 都是可选增强。

---

## 8. AI 代跑落地步骤（本会话 agent 直跑，模式 A）

把持仓交给 AI、AI 直接跑完整分析 → 存档 `data/v4/` → 用户 `git pull` 后前端解析。**可执行步骤、各单元 payload schema、联网取数与存档/快照细节统一见 `docs/wiki/v4-ai-proxy-run.md`**。要点：
- 第 2 阶段执行体 = 当前对话的 AI（可 spawn subagent ≤3 并发、不嵌套；**字数限制取消 2026-06-13——深度优先于篇幅**），**不需要 `claude` CLI 鉴权**；`run_v4.sh` 无 claude 退出码 2 不是阻塞，改走 agent 直跑。
  - 历史：subagent 之前默认 ≤500 字摘要,实测 TradingAgents 单轮辩论 1500-3000 字才能深做,故取消字数约束(2026-06-13)。timeout 仍是平台级硬约束(估 5-10 分钟),失败时主 agent 接管自跑。
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
