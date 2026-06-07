# v4 全量分析计划 — MECE 单元台账与执行波次

> 配套需求：`planning/v4/layered-deep-research_prd.md`（FR-001~FR-009）
> 权威实现：`scripts/workflow-v4-advisor.js`（单元选择器）、`app/services/v4/*`、`agents/advisor/v4-*.md`
> 执行模式：**本会话 Agent 直跑（模式 A）**——我读输入包 + 角色定义，做多轮辩论 + 总监拍板，缺数据用 web 联网补齐（不降级、不编造），经 `v4_unit_cli.py` 覆盖式写信封到 `data/v4/`，前端走静态快照解析。

---

## 0. 设计铁律（MECE 优先于"少开 agent"）

本计划的唯一组织原则：**完全穷尽（Collectively Exhaustive）+ 相互独立（Mutually Exclusive）+ 职责单一 + 能力打满**。

- **完全穷尽**：每一分钱都落进恰好一个大类；权益里每个值得研究的行业、每只独立个股都各有单元；六个非权益大类各有方案单元。不因"省 agent"而漏掉标的或合并行业。
- **相互独立**：每个单元独立触发、独立缓存、独立有新鲜度、独立可重试；单元失败只染红自己，不污染他人（NFR-004 AC4.2）。
- **职责单一**：一个单元只回答一个问题（"这一类怎么看 / 这个行业景气如何 / 这只票值不值 / 这一层怎么配比"）。配比单元只配比、不做方向研判；研究单元只研判、不拍配比。
- **能力打满**：每个研究/方向单元都配满对立角色（多头 vs 空头 + 专项视角）做**固定 3 轮**辩论，总监拍板；配比单元由配置总监在硬约束下拍板。数据缺失一律联网补齐并记 evidence+来源 URL，严禁静默降级。
- **约束硬传递、软提醒**：宏观 → 大类配比（equity_quota）→ 行业配比（≤equity_quota）→ 行业内个股配比（≤行业权重）。上游变更只把下游置黄（stale 软提醒），不强制重跑、不自动改数（FR-005）。

---

## 1. 持仓快照（穿透归类输入，37 笔 ≈ ¥1,189,621）

按 `v4_classifier` 七大类穿透归类（**Wave 0 已修正**，2026-06-07）：

| 大类 | 笔数 | 权重 | 市值 | 代表持仓 |
|------|------|------|------|----------|
| 权益 equity | 28 | 44.24% | ¥526,245 | 三祥新材/PopMart/恺英/移远/中兴/海康/小米/新和成/三花 + AI/半导体/医疗/家电/新能源/红利 ETF + 沪深300/中证500/A500/创业板宽基 + 纳指/全球QDII |
| 现金及等价物 cash | 1 | 27.93% | ¥332,212 | 活期存款（holding_only） |
| 固定收益 fixed_income | 5 | 12.77% | ¥151,902 | 稳健收益债B/增强回报债A/双债添利/7-10国开债/投资级信用债 |
| **待人工归类 unclassified** | 1 | 12.18% | ¥144,884 | **广发全球多元稳健投顾组合**（多资产，需穿透；暂不丢入权益） |
| 贵金属 precious_metal | 2 | 2.89% | ¥34,377 | 易方达黄金ETF / 广发上海金ETF |
| 大宗商品 commodity | 0 | 0% | ¥0 | 零持仓，仍可分析（AC2.5） |
| 房地产 real_estate | 0 | 0% | ¥0 | 零持仓 |
| 另类投资 alternative | 0 | 0% | ¥0 | 零持仓 |

> ✅ **Wave 0 已完成**（`app/services/v4/v4_classifier.py`）：① 补 FIXED_INCOME 关键词（收益债/回报债/国开债/中债/债A·B·C…）→ 3 只被误归权益的债基（¥117,881）已归位，权益从虚高的 67.84% 修正为真实 44.24%；② 补 PRECIOUS_METAL「上海金/沪金/金ETF」→ `008987 广发上海金ETF` 归贵金属；③ 新增多资产/投顾组合识别 → `广发全球多元稳健投顾组合`（¥144,884）标「待人工归类」而非静默归权益。
>
> ⚠ **待用户决策**：`广发全球多元稳健投顾组合`（12.18%）是多资产投顾组合，需用户提供其底层大致配比（权益/债/现金/黄金占比）才能穿透归类；在此之前它独立占一桶、不参与权益深链。

---

## 2. MECE 单元全景（依赖 DAG）

```
Wave 0  归类校正（纯代码，非 LLM）✅ 已完成
        └─ 修 classifier → 重归类 → 验证 0 漏归类（equity 67.8%→44.2%）
                │
Wave 0.5 数据采集台 档A（v4-data-desk，本会话 Agent 联网取一次）
        └─ 全局公共指标：LPR/逆回购/CPI/PMI/北向/汇率/原油/金价/10Y国债
           → data/v4/inputs/data_macro.json（每项 verified+来源URL，全单元同源共读）
                │（所有下游单元共读这一份宏观）
Wave 1  七大类研究部门 ×7（完全并行，相互独立）
        asset:equity  asset:fixed_income  asset:cash
        asset:commodity  asset:precious_metal  asset:real_estate  asset:alternative
        （各单元触发时 data-desk 档B 再为其深取该类专属数据）
                │（7 个 fingerprint 汇入）
Wave 2  资产配置委员会 ×1
        alloc:portfolio  →  产出七大类目标配比 + equity_quota 下传
                │（equity_quota 约束）
Wave 3  权益深链（gated by equity_quota>0）
        3a 行业研究部门 ×N（并行独立）   industry:<name>
                │
        3b 行业间配比 ×1                 alloc:equity_industries   (Σ权重 ≤ equity_quota)
                │（行业 Go + 行业权重）
        3c 个股研究部门 ×M（并行独立）   stock:<code>
                │
        3d 行业内资金配比 ×K（每 Go 行业一个） alloc:industry:<name>  (Σ ≤ 该行业权重)

Wave 4  非权益方案部门 ×6（与 Wave 3 并行，相互独立）
        plan:fixed_income  plan:cash  plan:commodity
        plan:precious_metal  plan:real_estate  plan:alternative
```

**独立性证明**：Wave 1 七个单元跨不同资产类、零交叉输入；Wave 3a 各行业、Wave 3c 各个股彼此无依赖；Wave 4 六个 plan 彼此无依赖。唯一的串行点是配比单元（2、3b、3d）等待其上游研究单元——但即使上游缺失/stale，配比单元也允许"显式标注 + 带风险继续"（AC3.1 / AC6.3），不硬阻断。

---

## 3. 完整单元台账（逐单元：职责 / 输入 / 角色 / 输出 / 上游 / 验证）

### Wave 1 — 七大类研究部门（7 单元）

每个单元统一范式（FR-002）：输入覆盖宏观（利率/通胀/货币/周期）+ 基本面（该类估值供需）+ 资金面/舆情 + 政策/地缘；角色 = 多头研究员 vs 空头研究员 + 专项视角分析师；**固定 3 轮**辩论 → 大类总监拍板。输出 `verdict{stance, situation, direction, risks, trend_advice, confidence}` + evidence。

| 单元 ID | 职责（单一问题） | 关键输入数据（缺则联网补） | 验证点 |
|---------|------------------|---------------------------|--------|
| `asset:equity` | A股/港股/美股权益大类整体怎么看 | 沪深300/中证500 PE 分位、北向资金、风险溢价、美股估值 | stance/direction 非空，evidence 带来源 |
| `asset:fixed_income` | 利率债/信用债大类怎么看 | 10Y 国债收益率、信用利差、货币政策取向 | 含久期取向 |
| `asset:cash` | 现金及等价物怎么看（持有型） | 货币基金 7 日年化、逆回购利率、流动性 | holding_structure 视角 |
| `asset:commodity` | 大宗商品（能源/工业金属/农产品）怎么看 | 原油/铜价、库存、美元指数 | 零持仓也出研判（AC2.5）|
| `asset:precious_metal` | 黄金/白银怎么看 | 金价、实际利率、央行购金、避险情绪 | — |
| `asset:real_estate` | REITs/房地产怎么看 | REITs 指数、租金回报、地产政策 | 实物房产记敞口口径 |
| `asset:alternative` | 虚拟币等另类怎么看 | BTC/ETH 价格、合规进展 | 高波动/合规风险显著标注 |

### Wave 2 — 资产配置委员会（1 单元）

| 单元 ID | 职责 | 输入 | 输出 | 上游 fingerprint | 验证点 |
|---------|------|------|------|------------------|--------|
| `alloc:portfolio` | 在七大类研判之上拍板目标配比 | 7 个 `asset:*` 的 verdict + 当前持仓配比 | `当前→目标`配比（Σ=100%，允许某类主动归 0）+ **equity_quota** | 记录 7 个 asset 单元 version+fingerprint（AC3.5）| Σ目标=100±0.1；缺/stale 上游显式标注（AC3.1）|

> **职责边界**：配置委员会只做跨大类配比，不重做单类方向研判（那是 Wave 1 的职责）。equity_quota 即权益目标配比，下传为行业层总权重上限；若 =0% 则不触发 Wave 3。

### Wave 3 — 权益深链

**3a 行业研究部门（MECE 覆盖权益持仓所映射行业 + 推荐风口；下表为候选，CLI 对话最终确认）**

| 单元 ID | 对应持仓 | 角色配置 | 验证点 |
|---------|----------|----------|--------|
| `industry:人工智能/算力` | AI ETF(012733/012734/024245)、海康 | 行业多头 vs 空头 + 景气视角 | direction/vitality_level/allocation_advice 非空 |
| `industry:半导体/国产替代` | 芯片ETF(012629)、移远、中兴 | 同上 | — |
| `industry:新能源车/智能驾驶` | 电池ETF(013180)、三花 | 同上 | — |
| `industry:电力/公用事业` | 绿电ETF(019058) | 同上 | — |
| `industry:创新药/生物科技` | 医疗ETF(009881)、新和成 | 同上 | — |
| `industry:消费（可选）` | 家电ETF(005063)、PopMart、小米 | 同上 | — |
| `industry:互联网/平台` | 海外互联网ETF(006327)、恺英 | 同上 | — |
| `industry:有色/资源` | 三祥新材 | 同上 | — |
| `industry:高端制造/机器人` | （推荐风口，三花/三祥部分相关） | 同上 | 零持仓亦可深辩找机会 |
| `industry:军工/国防` | （推荐风口，无持仓） | 同上 | 可选，按 CLI 确认 |

> **宽基底仓 / 海外 QDII 不单独深辩**：沪深300/中证500/A500/创业板宽基与纳指/全球精选 QDII 是被动/跨行业敞口，归到 `alloc:equity_industries` 层作为"被动底仓 + 海外敞口"统一配比，不映射成单一行业（避免破坏 MECE：它们本就不属某一行业）。

**3b 行业间配比（1 单元）**

| 单元 ID | 职责 | 约束 | 上游 fingerprint | 验证点 |
|---------|------|------|------------------|--------|
| `alloc:equity_industries` | 在 equity_quota 内给各 Go 行业 + 被动底仓 + 海外敞口分配目标权重 | Σ行业权重 ≤ equity_quota | `alloc:portfolio` + 各 `industry:*` | over_quota 时 input_warnings 报警不改数 |

**3c 个股研究部门（MECE 覆盖全部独立个股，9 单元，每只独立缓存）**

| 单元 ID | 名称 | 所属行业 | 验证点 |
|---------|------|----------|--------|
| `stock:603663` | 三祥新材 | 有色/资源·高端材料 | 评级+目标价非空 |
| `stock:09992` | 泡泡玛特(港股) | 消费（可选）| — |
| `stock:002517` | 恺英网络 | 互联网/平台·游戏 | — |
| `stock:603236` | 移远通信 | 半导体/物联网 | — |
| `stock:000063` | 中兴通讯 | 半导体/通信 | — |
| `stock:002415` | 海康威视 | 人工智能/安防 | — |
| `stock:01810` | 小米(港股) | 消费（可选）·智能硬件 | — |
| `stock:002001` | 新和成 | 创新药·维生素/化工 | — |
| `stock:002050` | 三花智控 | 新能源车·热管理 | — |

> 个股单元各自独立辩论（多头 vs 空头 + 行业内研究部门视角）→ 个股总监出评级+目标价。仅对落在 Go 行业内的个股触发（节省成本）；非 Go 行业个股标灰待定。

**3d 行业内资金配比（每个 Go 行业一个，K 单元）**

| 单元 ID | 职责 | 约束 | 上游 fingerprint |
|---------|------|------|------------------|
| `alloc:industry:<name>` | 在该行业目标权重内对选定个股配资 + 买入区间 | Σ个股权重 ≤ 该行业权重 | `alloc:equity_industries` + 该行业内各 `stock:*` |

### Wave 4 — 非权益方案部门（6 单元，差异化下钻，FR-007）

| 单元 ID | 输出形态 | 要点 |
|---------|----------|------|
| `plan:fixed_income` | 久期 + 品种结构 | 国债/信用债/可转债/债基配比与久期取向，结合利率环境 |
| `plan:cash` | 持有结构方案 | 活期/货基/短债/逆回购分布建议（持有型，不荐个券）|
| `plan:commodity` | 品种/工具方案 | 能源/工业金属/农产品取向；可交易工具可下钻 |
| `plan:precious_metal` | 品种/工具方案 | 实物/黄金 ETF/金矿股取向 |
| `plan:real_estate` | 工具方案 | REITs 下钻；实物房产仅记敞口 + 宏观持有建议 |
| `plan:alternative` | 品种方案 | 虚拟币品种取向 + 高波动/合规风险显著标注 |

> plan 单元复用 Wave 1 大类研究部门的 3 轮辩论范式（同 `asset:<class>`，planMode=true），但产出落在"类内结构方案"而非跨类配比。

---

## 4. 单元总数（穷尽口径）

| 波次 | 单元数 |
|------|--------|
| Wave 0 归类校正 | 0（纯代码）|
| Wave 1 大类研究 | 7 |
| Wave 2 大类配比 | 1 |
| Wave 3a 行业深辩 | 8（持仓映射）+ 0~2（推荐风口）|
| Wave 3b 行业间配比 | 1 |
| Wave 3c 个股 | 9 |
| Wave 3d 行业内配比 | = Go 行业数（≤8）|
| Wave 4 非权益方案 | 6 |
| **合计** | **约 32~35 个独立单元** |

> 这就是"完全穷尽"的代价与价值：30+ 个独立单元，但每个职责单一、可独立验证、可独立重试。Agent 数量不是约束，MECE 才是目标。

---

## 5. 执行方式（每单元统一动作）

```bash
# ① 采集输入包（纯 Python，不碰 LLM/Mongo）
python scripts/collect_v4.py --selector <unit> \
    --portfolio-file data/v4/_inputs/holdings.json     # → data/v4/inputs/*.json

# ② 本会话 Agent 直跑（模式 A）：读输入包 + agents/advisor/v4-*.md 角色定义
#    → 3 轮辩论 + 总监拍板；缺数据用 web 搜索/抓取补齐，evidence 记 verified + 来源 URL
#    → 经 CLI 覆盖式写信封（version+1，只动本单元）
python scripts/v4_unit_cli.py lock '<unit>'
python scripts/v4_unit_cli.py write '<unit>' --payload <json> --run-mode ai_proxy
python scripts/v4_unit_cli.py unlock '<unit>'

# ③ 体检 + 存档
python scripts/run_report_v4.py                 # 逐单元状态（绿/黄/红/灰）
python scripts/build_snapshot_v4.py             # → frontend/public/snapshot/v4/*.json
```

**存档落点**：单元信封 `data/v4/{assets,allocation,industries,stocks,plans}/<unit>.json`（git 传输载体，diff 友好）；前端静态快照 `frontend/public/snapshot/v4/*.json`。用户 `git pull` 后设 `VITE_STATIC_SNAPSHOT=1` 直接解析展示，无需 Mongo/后端（可选 `import_v4.py` 入库增强）。

**数据获取铁律（取数/辩论分离，本会话 Agent 兼任 data-desk）**：在模式 A 下，**我同时扮演 `v4-data-desk`**——
- **档 A（Wave 0.5，run 级一次）**：开跑前我先联网取十来个全局公共指标（LPR/逆回购/CPI/PMI/北向/汇率/原油/金价/10Y国债）写入 `data_macro.json`，**全部单元共读同一份**（保证约束链一致性）；`fetched_at` 在当个交易日内复用、不重复取。
- **档 B（每单元）**：分析某单元时再为它联网深取专属数据（行业景气/估值、个股财报/资金流、债收益率曲线等）。
- 每个关键数字在 evidence 里记 `verified` + 来源 URL/口径；确实无法获取才标 `missing` 并说明。**严禁静默降级或编造数字**（辩论时引用 data_macro.json 的同源读数，不各自重新解读宏观）。

---

## 6. 验证与修复回路（边跑边验，一举两得）

每跑完一个单元立即验证,既验证系统正确性、又积累配置结论:

1. **结构验证**：`run_report_v4.py` 该单元转绿,payload 非空,fingerprint/version 正确,无意外染红邻居。
2. **内容验证**：verdict/方向/配比/评级字段齐全,evidence 带来源,Σ约束成立（配比和=100 / 行业Σ≤quota / 个股Σ≤行业权重）。
3. **链路验证**：上游 fingerprint 正确绑定;手动改一个上游,确认下游正确置黄(stale 软提醒生效,FR-005)。
4. **前端验证**：`build_snapshot_v4.py` 后三层 Tab 正确解析(Tab1 七大类卡片 / Tab2 行业表 / Tab3 个股表),空态/stale 提示正常。
5. **发现问题 → 当波次修复 → 重跑该单元**(独立性保证不连累其它已绿单元),再进下一波。

---

## 7. 建议执行顺序

`Wave 0`（修归类,10 分钟,立即可验）→ `Wave 1`（7 大类研究,产出方向研判）→ `Wave 2`（大类配比,这步就能给你**第一份可执行的资产配置指导**)→ `Wave 4`（6 非权益方案,可与下并行)→ `Wave 3`（权益深链:行业深辩 → 行业配比 → 个股 → 行业内配比,最细的个股级建议)。

每完成一波我给你一段结论摘要 + run_report 体检,你可随时叫停/调整行业候选范围/调整配比偏好。
