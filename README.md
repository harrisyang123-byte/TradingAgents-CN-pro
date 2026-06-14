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
宏观 data-desk（唯一联网取数台：22 宏观指标 + A股/港股个股硬数据 + 价值创造 verified 数据）
   │  价格走新浪源 stock_zh_a_daily(稳定); 财务/ROIC/FCF/EPS/增速 走 stock_financial_abstract
   │（全局共享）
七大类研究部门 ×7（权益/固收/现金/大宗/贵金属/房地产/另类）
   每类：3 视角分析师(macro/flow/policy) → 多空 3 轮 → 总监拍板(reflection+反骑墙)
   │（7 份 verdict）
资产配置委员会  alloc:portfolio
   Σ=100% 目标配比 + 下传 equity_quota（权益额度）
   │（equity_quota 约束）
权益深链（gated by equity_quota>0）
   ├ 行业研究部门 ×N   industry:<canonical_name>     ★行业按"终端驱动+一荣俱荣"归并到 11 大行业
   │    （半导体产业链 / AI算力数据中心 / 互联网平台 / 创新药+CXO / 消费电子+IoT
   │     / 新能源车 EV / AIoT安防 / 有色金属资源 / 化工必需消费 / 可选消费 / 电力公用事业）
   │    景气多空 + 产业链瓶颈分析师(Chokepoint) → 总监整合 chokepoint_map
   ├ 行业间配比         alloc:equity_industries  (Σ ≤ equity_quota)
   ├ 个股研究部门 ×M   stock:<code>
   │    4 分析师(财务/竞争/估值/舆情) → 多空 → 3 方风险辩论 → 总监三维拍板
   │    ★三维选股框架：好公司(ROIC>WACC) × 好价格(PE) × 好未来(PEG/增速可持续)
   │    ★expert_valuation 目标价：TAM×市占率→forward EPS→目标价(标假设)
   └ 行业内配比 ×K      alloc:industry:<name>  (Σ ≤ 行业权重)

非权益方案部门 ×6   plan:<class>（固收/现金/大宗/贵金属/房地产/另类执行方案）

基金穿透说明：基金作整体标的管理(主题基金→对应行业作推荐 / 宽基QDII债基→大类底仓)
```

独立集合 `v4_units`、独立目录 `data/v4/`、独立编排器 `scripts/workflow-v4-advisor.js`、独立只读路由 `app/routers/portfolio_v4.py`、独立前端三层 Tab。完整规格见 `.kiro/specs/v4/`，主 Agent 指南见 [AGENTS.md](AGENTS.md)。

---

## v4 Agent 阵容（分层分队，每层对立角色辩论）

| 层 | 角色 | 职责 |
|----|------|------|
| 通用 | `v4-data-desk` | **唯一带联网工具**的取数台；宏观走 `macro_source.py`(AKShare 22 指标)、A股个股走 `stock_source.py`(AKShare 股价/市值/PE/PB/PE分位/财务/涨幅/**价值创造 verified ROIC·FCF·净利率**) |
| 大类 | `v4-asset-analyst-macro/flow/policy` + `v4-asset-bull/bear` + `v4-asset-director` | 3 视角分析师打底 → 多空 3 轮 → 总监拍板(reflection+反骑墙) |
| 大类 | `v4-allocation-director` | 资产配比委员会，Σ=100% + 下传 equity_quota |
| 行业 | `v4-industry-bull/bear` + **`v4-industry-chokepoint`** + **`v4-industry-future-market-analyst`** + `v4-industry-director` | 景气多空 + **产业链瓶颈分析师**(Chokepoint 四维+逆向工程+替代路径+发现度) + **★未来市场专职分析师**(2026-06-14 拆分独立 agent: TAM 当前/2030E + CAGR + 渗透率阶段 + 行业 forward PEG + 龙头瓜分 + 7 把辩证尺) → 总监整合 chokepoint_map + 引用 industry_future_market(下游个股 expert_valuation 上游锚定) |
| 行业 | `v4-industry-allocator` | 行业间配比(≤equity_quota) |
| 个股 | **`v4-stock-analyst-financial/competitive/valuation`** + **`v4-stock-analyst-sentiment`** + **`v4-stock-valuation-engineer`** + `v4-stock-bull/bear` + **`v4-stock-risk-aggressive/safe/neutral`** + `v4-stock-director` | **4 分析师并列**(财务/竞争/估值/**舆情**) → **估值工程师**(2026-06-14 拆分: forward 2-3年 EPS 推导链 + PE 分位计算 + 可比 PE 锚定 + 对面买家逻辑, 防目标价反复反转) → 多空 → **3 方风险辩论** → 总监预期差拍板 |
| 个股·估值审计 | **`v4-stock-valuation-auditor`**(2026-06-14 拆分, 独立于 critic) | 专职审计 expert_valuation 推导链(6.12 推导链 7 项 + 6.13 成长股 5 项 + **反复反转检查**), 防 director 自我合理化 |
| 进攻·选股 | **`v4-market-scanner`** + **`v4-alpha-hunter`**(2026-06-14 新建) | scanner 全市场硬指标扫描(ROIC>WACC+5pct / PE分位<30% / 增速>20%)出候选池 → hunter 深挖 alpha(预期差≥30% + 可证伪触发器 + 赔率≥3:1)出 3-5 只未识别 alpha |
| 个股·竞争深做 | **`v4-stock-force-entry/substitute/buyer/supplier/rivalry`**（5 力专项分析师，2026-06-13 拆分） | **每力深做+偏基本面**(buyer/supplier 用毛利率/成本数据论证),输出给 competitive 整合 agent 做交叉编织 |
| 个股·风险辩论 | **`v4-stock-risk-aggressive/safe/neutral`**（3 方风险辩论，2026-06-13 加 D0-5）| **TradingAgents `risk_debaters` 对齐**: aggressive 攻保守/safe 攻激进/neutral 协调; 维度=仓位+止损+tail risk 不是方向(与 bull/bear 互补) |
| 个股·舆情 | **`v4-stock-analyst-sentiment`**（新闻舆情分析师，2026-06-13 加 D0-5）| **TradingAgents `news_analyst+social_media_analyst` 对齐**: 5 维度(温度/新闻/一致预期偏差/资金面/情绪vs基本面背离); 是 director 的输入之一(非产物) |
| 跨次记忆 | **memory 系统** `data/v4/_memory/<agent_id>.json` (2026-06-13 加 D0-5)| **TradingAgents `agent.memory` 对齐**: 跨股累积过往判断/错误模式/行为校准; bull/bear/director/critic 开辩前必读, 写 reflection 时追加 |
| 质量闸门 | **`v4-investor-critic`** | 芒格/段永平/Serenity/达里奥 **四视角评审委员会**，拷问 verdict 输出 ACCEPT\|NEEDS_CHANGES; **接入 v4_unit_cli.py write 编排** (NEEDS_CHANGES 直接 exit=4 拦截不让落盘); 必查项: 8 项深度 + 6.9 价值创造四问 + 6.10 PEG五大陷阱 + 6.11 行业未来市场 + 6.11.x 7 把辩证尺 + 6.12 个股推导链 + **6.13 成长股估值方法论(PE 分位/forward 多年/对面买家/错杀vs留意池/静态vs动态)** |
| 元指导 | **`v4-chief-investment-officer`** | **首席投资官+投委会**视角，以"用户持久盈利"为锚审视整个系统方向(五维:可信/能用/连得上/会学/值得)，识别"假专业"与过度工程，给开发明确优先级 |

> 全部分析角色 `tools:[Read]`、**只消费 data-desk 产出的输入包、绝不自己联网取数**；唯一带 `web_search`/`web_fetch` 的是 `v4-data-desk`。

---

## 个股完整分析流程（架构图 — 8 step 真实编排器顺序）

```
┌─────────────────────────────────────────────────────────────────────────┐
│  Step 1 📥 data-desk 数据采集（唯一联网取数台）                            │
│  • 股价/PE/PB/财务大类 via stock_source.py                                │
│  • 5 力深做 schema (CR1/CR3/CR5/产能/上游) ⚠️ 部分待联网升级               │
│  • 新闻+雪球/股吧情绪 + 卖方一致预期 + 北上资金 (sentiment 加取)            │
│  → 输出 inputs/stock_<code>.json (50+ 条 evidence + 21 字段竞争 schema)   │
└──────────────────────────────────┬──────────────────────────────────────┘
                                   │ 输入包 (所有 agent 共享)
                                   ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  Step 2 👔 4 分析师并列分析 (无依赖, 并发跑)                               │
│  ┌────────────┐ ┌────────────────┐ ┌────────────┐ ┌────────────┐        │
│  │ a 财务      │ │ b 竞争 + 五力深做│ │ c 估值     │ │ d 舆情      │       │
│  │ analyst-   │ │ 整合者 +5 力专项 │ │ analyst-   │ │ sentiment  │       │
│  │ financial  │ │ entry/substitute │ │ valuation  │ │ (D0-5 加)  │       │
│  │            │ │ /buyer/supplier  │ │            │ │ 5 维度:温度  │       │
│  │ 毛利率/    │ │ /rivalry         │ │ PE/PB/DCF/ │ │ /新闻/一致预│       │
│  │ ROE/财务   │ │ → competitive    │ │ 预期差三锚 │ │ 期/资金面/   │       │
│  │ 健康度     │ │ 整合者交叉编织   │ │            │ │ 情绪vs基本 │       │
│  └────────────┘ └────────────────┘ └────────────┘ └────────────┘        │
└──────────────────────────────────┬──────────────────────────────────────┘
                                   │ 4 份完整 JSON 产出
                                   ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  Step 3 ⚔️ 多空 N 轮辩论 (消费 4 分析师产出)                              │
│  bull R1 → bear R1 → bull R2 → bear R2 → bull R3 → bear R3              │
│  R3 终局: 双方诚实让步, 形成"方向"维度共识区 (target 区间, 概率分布)        │
│  字数无限制 (D0-5 取消) + 辩论深度铁律 (点名反驳+数据分子+可证伪信号)        │
└──────────────────────────────────┬──────────────────────────────────────┘
                                   │ 多空 R3 共识
                                   ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  Step 4 ⚖️ 3 方风险辩论 (TradingAgents `risk_debaters` 对齐, D0-5 加)      │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐                          │
│  │ aggressive │  │ safe       │  │ neutral    │                          │
│  │ 攻保守     │  │ 攻激进     │  │ 协调双方   │                          │
│  │ 主张追风险 │  │ 主张守底线 │  │ 给修正建议 │                          │
│  └────────────┘  └────────────┘  └────────────┘                          │
│  共识焦点: 仓位 / 止损 / tail risk / 执行节奏 (与 Step 3 维度互补不重复)    │
└──────────────────────────────────┬──────────────────────────────────────┘
                                   │ neutral_proposal_for_director
                                   ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  Step 5 🎩 director 综合拍板 (消费 Step 1-4 全部 + memory)                 │
│  • thesis 融会贯通核心论述                                                  │
│  • 四维质量闸门 (芒格/段永平/Serenity/达里奥)                                │
│  • ★三维选股框架 (好公司ROIC>WACC × 好价格PE × 好未来PEG/增速可持续)         │
│  • ★价值创造四问: TAM 天花板 / ROIC vs WACC / 资本配置 / 正向 DCF 三角验证 │
│  • ★expert_valuation 目标价推导链 (TAM×市占率→forward EPS×目标PE, 标假设)  │
│  • valuation_basis 估值推导链 (forward EPS×PE×对标谁, 禁拍脑袋)             │
│  • forward_view 6 维多维推演 (market_regime/liquidity/cycle/β/comparable/ │
│    pricing_power) — 不只 PE 一维                                           │
│  • 产品分子模型 + 3×3 敏感性矩阵                                           │
│  • reflection 对比上版 + memory_used 引用过往经验                          │
│  • 反骑墙站队 + 采纳/拒绝 neutral_proposal reasoning                       │
└──────────────────────────────────┬──────────────────────────────────────┘
                                   │ director verdict
                                   ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  Step 6 🎓 v4-investor-critic 评审 (4 视角 + 8 必查项)                    │
│  芒格/段永平/Serenity/达里奥 拷问 → ACCEPT (≥85) / NEEDS_CHANGES          │
│  8 必查: 产品分子/敏感性矩阵/可比路径/forward_view 6 维/数据追溯/辩论深度   │
│         + ★价值创造四问 + ★未来维度+PEG五大陷阱(后视镜/低基数/周期伪装/   │
│           增速质量/久期)                                                   │
│  接入 v4_unit_cli.py write 编排: NEEDS_CHANGES 直接 exit=4 拦截不让落盘   │
└──────────────────────────────────┬──────────────────────────────────────┘
                                   │ ACCEPT
                                   ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  落盘 → data/v4/stocks/<code>.json (auto-archive 旧版 + version+1)         │
│  ↓                                                                        │
│  Step 7 📈 v4_replay 回填 historical_alpha (结果闭环)                      │
│  Step 8 ⚠️ v4_monitor.py 止损监控 (价格型自动 + 基本面型季度核查)           │
└─────────────────────────────────────────────────────────────────────────┘
```

**架构特点**：
- **MECE 分工**：4 分析师并列(财务/竞争+5力/估值/舆情)，不重叠不漏
- **5+1 五力深做**（D 阶段）：5 力专项 agent + competitive 整合者交叉编织
- **2 层辩论**（D0-5）：Step 3 多空辩论=方向维度 / Step 4 3 方风险辩论=执行维度，独立不重复
- **跨次 memory**（D0-5）：bull/bear/director/critic 开辩前读 memory，写 reflection 时追加，跨股累积经验
- **critic 接入编排**（D0-5）：NEEDS_CHANGES 强拦截，禁止"主 agent 自评"绕过
- **结果闭环**：reflection（对比上一版）+ historical_alpha（回测准确率）+ critic 评审

---

## 核心方法论

- **Chokepoint 供应链瓶颈框架 + 波特五力**（`planning/v4/chokepoint-framework.md`，借鉴 Serenity）：自下而上逆向工程产业链，**四维判定**（不可替代/供给集中/产能刚性/价值卡位）定位"卡不卡脖子"，**波特五力**（进入者/替代品/买方/供方/同业竞争）判定"利润能否留住"，加 **市场发现度**。A/B 测试验证加五力 85 vs 78。混合分队：瓶颈分析师出骨架 → director 整合 chokepoint_map → **investment_map（瓶颈环节→推荐个股→卡位排序→为什么是它）** 落到"买什么"。
- **预期差选股理论 + 估值推导链**（`planning/v4/stock-selection-theory.md`）：**判断买卖看预期差（基本面将兑现 − 价格已 price-in），不看涨幅/PE 分位**。三锚：隐含增速缺口/定价充分度/催化。**买点/目标价必须有 `valuation_basis` 推导链**（目标价=forward指标×目标倍数(对标谁)，买点=安全边际/PB/DCF），禁止拍脑袋。
- **forward_view 前瞻视野**（A/B 测试 2 次验证 89/82 vs 52）：宏观从"回看"升级到"前瞻"——11 维（事件日历+一致预期+预期差+三情景+仓位/IV+假设证伪+尾部风险+跨市场领先+触发监控），触发监控用**绝对阈值**。三层 director 全部内化（不增 agent，A/B 测试证明）。
- **结果闭环反思 + 回测验证**（借鉴 TradingAgents）：director 开辩前读上一版 verdict → 输出 reflection；**`v4_replay.py` 回测器 + `historical_alpha`（判断价→实际涨跌算 hit/miss）+ `v4_quarterly_review.py` 季度复盘**，让系统对自己判断负责。critic 铁律0：上次判断 miss 必须回答"这次为何对"。
- **四维质量闸门 + 反骑墙**：每层 director 内化芒格/段永平/Serenity/达里奥四视角（生意质量10年/逆向最坏/赔率周期/可执行止损/不确定性诚实）；证据势均力敌才中性，否则必须站队。

**数据铁律**：分析 Agent 严禁自产价格/PE/市值/目标价数字，唯一来源 = data-desk 联网核实值（个股走 `stock_source.py`）；无则标 missing，绝不编造。

**价值创造维度（2026-06-14 补全）**：判断"公司未来值多少钱"必答四问 — TAM 天花板+渗透率阶段 / ROIC vs WACC(创造还是毁灭价值,用 ROIC 不用被杠杆污染的 ROE) / 管理层资本配置 / 正向 DCF 三角验证。ROIC/FCF 等计算密集项用 AKShare verified 精算(A/B 测试证明主 agent 估算=拍脑袋),禁伪精确点值。

**三维选股框架（2026-06-14 用户纠错"漏未来市场"后补全,永久铁律）**：买股票买的是未来,单维度会骗人 → **好公司(ROIC>WACC 价值创造) × 好价格(PE 合理) × 好未来(PEG/增速可持续/TAM 天花板)**,三维缺一不可。只看 ROIC+PE 是回看/当下,漏了未来市场会严重误判(实战中新易盛 ROIC50-66%+PE52.7 单看PE误判"贵",加未来维度 forward PEG<0.6 实为错杀;天孚 PEG2.16 实为透支)。

**行业层 7 把辩证分析尺(2026-06-14 用户拍板"除了网上取数也要有自己分析方法论"后固化,永久铁律)**：光有 verified 数字还不够, director/bull/bear 必须用方法论戳穿水分, verdict.summary 必须显式应用 ≥3 把尺, critic 6.11.x 必查:
- ① **TAM 三角验证**:同一指标 ≥3 独立来源(IDC/marketsandmarkets/Gartner/工信部),差异>30% 标分歧不调和(避免单源偏差)
- ② **TAM 拆解还原**:把 TAM 拆成可验证因子(用户数×ARPU×渗透率/设备×单价×替换周期),反推合理性(如 AI光模块=$700B capex×65%服务器×4%光互连≈$18B 验证 $15.4B)
- ③ **CAGR 久期检验**:用历史可比行业判断高增速持续年数(智能机 2008-2014 渗透 5%→50% 高增 6 年; EV 2018-2025 1%→25% 高增 7 年)
- ④ **渗透率阶段类比**:导入<10% / 爆发 10-50% / 成熟 50-80% / 衰退>80%,用历史可比行业映射(AI 算力当前类比 2010 智能机)
- ⑤ **forward PEG 跨期对比**:当前估值 vs 同类成长股+同期渗透率阶段历史估值(AI 算力 PE 50x vs 2018 新能源车 PE 60x)
- ⑥ **龙头瓜分检验**:top3/top5/top10 集中度判二三线空间(台积电60%+三星15%+联电8%=top3 83%,中芯仅5%空间有限)
- ⑦ **景气先行指标交叉**:库存周期/订单可见度/价格趋势/产能利用率/龙头资本开支,≥3 个先行指标同向才确认景气方向

**计算密集 vs 综合判断铁律(永久,详 `planning/v4/project-master-prompt.md §7-bis`)**:
- **第一类(必须 verified)**:财务比率 ROIC/ROE/FCF/EPS → AKShare; 价格/PE/PB → AKShare; **TAM 当前/2030E/CAGR/渗透率%** → web_search ≥3 独立来源标 URL+status; 宏观 22 指标 → AKShare/官方源
- **第二类(综合判断改 .md 即可)**:多空辩论/风险辩论/chokepoint/forward_view/stance/方向/仓位/渗透率阶段判定/forward PEG 解读 → 让 subagent 用 verified 数据辩论, 禁止编造数据范围内的数字
- **何时新增 subagent**:仅当现有 agent 阵容无法承载的全新视角才新增。已有视角覆盖 → 改 .md(本次未来市场属此类)
- **PEG 五大陷阱（critic 沉淀）**：①后视镜增速(历史≠未来,用 forward 常态增速) ②低基数幻觉(上年塌陷→本年恢复=虚高,如药明102%含创新药寒冬低基数) ③**周期伪装成长**(商品/周期品景气高点利润暴增→PEG极低→实为卖出信号,如紫金61.5%=金铜价高位,内生量增仅8-12%) ④增速质量不分(营收≠利润≠FCF,如工业富联增收不增利毛利3-5%) ⑤增速久期(PEG隐含增速永续,实际高增速仅2-3年,需久期折算)。
- **修正公式**：修正PEG = PE / min(forward_2yr_CAGR, 行业天花板增速) × (3年/高增速持续年数)。周期股禁用 PEG,改用 PB+产能周期。
- **数据源（2026-06-14 根治）**：价格走新浪源 `stock_zh_a_daily`(sh/sz前缀,稳定;东财 push2 实时端点间歇 RemoteDisconnected 反爬),财务/ROIC 走 `stock_financial_abstract`(新浪源稳定),净利/营收增速用财报 verified 算 PEG。

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
│   ├── build_snapshot_v4.py         # v4 单元 → 前端静态快照(大类/行业/个股)
│   ├── v4_replay.py                 # 历史判断回放器(回测算 historical_alpha)
│   ├── v4_quarterly_review.py       # 季度复盘(命中率/胜负case/系统性偏差)
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
| `GET /api/portfolio/v4/industry/{name}` | 行业详情（深辩 + **chokepoint_map 瓶颈地图(四维+五力)** + **investment_map 投资地图** + 个股表）|
| `GET /api/portfolio/v4/stock/{code}` | **个股详情**（四维质量闸门 + forward_view + **valuation_basis 估值推导** + 止损纪律 + **historical_alpha 回测准确率**）|
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
