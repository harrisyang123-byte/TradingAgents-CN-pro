---
name: v4-debate-discipline
description: >
  Use when running v4 bull/bear/aggressive/safe/neutral 辩手 agent (任一三层: asset/industry/stock).
  Mandatory for: v4-asset-bull/bear, v4-industry-bull/bear, v4-stock-bull/bear,
  v4-stock-risk-aggressive/safe/neutral. Provides:
  ①辩论 3 铁律(点名反驳/数据分子/可证伪信号) ②bull 派别切入(段永平好生意+费雪 scuttlebutt+马克斯紫苏叶)
  ③bear 派别切入(芒格逆向+达里奥风险+死亡清单 LTCM/Archegos/Woodford)
  ④三层辩论焦点差异 ⑤反 Goodhart 输出契约。
  这是把"立场对撞辩论沦为口号"治成"超级投资人方法论对抗"的核心 skill。
---

# v4 辩论纪律 skill (debate discipline)

> **用途**: 9 个 bull/bear 辩手 agent 开辩前必读, 输出 history 必证可见 cite。
> **核心信念**: 辩论质量 = director verdict 上限。辩手浅尝 = 下游再多方法论也补救不及 (上游污染, 下游补丁徒劳)。

## §1 辩论 3 铁律 (内化自 AGENTS.md §11 + critic 6.6)

每轮 history 必须做到 3 件事, 缺一即被 critic NEEDS_CHANGES:

### 铁律 1: 点名反驳 (rebut by name, not by stance)
- ❌ 浅: "我看多/我看空" (立场对撞, 平行喊口号)
- ✅ 深: "对方第 N 轮说 X, 但忽略了 Y 数据分子 → 该论点不成立"
- 实操: history 每轮**首句**必须引用对方上轮**具体论点编号或关键词** (前置承认对方说了什么, 再反驳)

### 铁律 2: 数据分子 (numerator data, not adjective)
- ❌ 浅: "增长很强/估值偏贵/护城河深" (定性形容词, 换个股也成立)
- ✅ 深: "Q3 客户 A 收入 占比 32% 同比 +18%, 但毛利率从 42% → 38% (-4pct), 净利贡献 = 32% × 38% = 12.2亿"
- 实操: 每个论点 ≥1 个 KPI 数字 + 单位 + 出处 (data-desk 输入包字段编号或 evidence 索引)

### 铁律 3: 可证伪信号 (falsifiable signal, not eternal truth)
- ❌ 浅: "AI 算力会持续增长 / 利润必将兑现" (无时间窗无量化阈值, 永远对永远不可证伪)
- ✅ 深: "看到 X (绝对阈值) → 我承认错": 如 "若 2026Q3 客户 A 出货量 < 50 万 (verified Q2=80万), 我承认看多逻辑破产"
- 实操: 本方每个核心论点配 ≥1 个反向阈值 + 时间窗 (绝对阈值禁相对偏离词, 对齐 critic 6.16②)

## §2 派别切入 (Bull 必引用 ≥1 派, Bear 必引用 ≥1 派)

### Bull 三派切入 (用对应派的方法论锚住看多论点)

**段永平派 — 好生意(business quality first)**:
- 切入点: "这是不是一门好生意?" → 复购/定价权/现金流质量/ROIC > WACC
- 反例(浅): "公司业绩好" / 切入(深): "段永平: 好生意要看 (1) 复购率 X% (2) 提价不丢客户 (3) FCF 转化率 Y% — 本股 (1)(2)(3) 数字..."
- 适用: stock-bull / industry-bull (商业模式角度)

**费雪派 — scuttlebutt 闲聊法**:
- 切入点: 客户名单/产能地图/上游矿源/专利碎片**一手演绎** (禁卖方研报二手结论)
- 反例(浅): "据某券商研报" / 切入(深): "费雪 scuttlebutt: 招标公告 X 显示客户 A 出货 Y 万 / 海关数据 X 显示进口 Y 吨 / 专利 N 件覆盖核心环节 — 一手演绎"
- 适用: stock-bull (alpha 挖掘) / industry-bull (景气先行指标)

**马克斯派 — 紫苏叶/错杀龙头(未被充分定价)**:
- 切入点: 二阶思维 — 市场 price-in 了什么 / 预期差在哪 / 是低关注度紫苏叶还是被错杀的卡位龙头(中际旭创¥88案)
- 反例(浅): "PE 低就是便宜" / 切入(深): "马克斯二阶: 市场已 price-in X 共识但漏了 Y, forward PE/PEG 历史分位 Z% 显示错杀, 中际旭创案前例"
- 适用: stock-bull (预期差) / industry-bull (景气拐点)

### Bear 三派切入 (用对应派的方法论锚住看空论点)

**芒格派 — 逆向思考(invert)**:
- 切入点: "什么情况下亏光本金?" → 死亡清单具体场景 (基本面双杀/估值杀/政策黑天鹅)
- 反例(浅): "估值贵" / 切入(深): "芒格逆向: 若 X 触发 (具体业务路径), 本股下行至 ¥Y (-Z%), 同型于 [乐视/康美/价值陷阱]"
- 适用: stock-bear / industry-bear / risk-safe

**达里奥派 — 风险优先(risk first)**:
- 切入点: 先算亏再算赚 / 不确定性诚实 / What am I missing? / 周期位置
- 反例(浅): "估值贵风险大" / 切入(深): "达里奥风险: 周期位置 = 资本开支顶 / 历史回撤中位 X% / 尾部双杀 = -Y%, 押单一情景下行赔率 1: Z"
- 适用: stock-bear / risk-aggressive (反向警告) / risk-neutral

**死亡清单派 — Part 2.7 失败案例反向锚**:
- 切入点: 引用 LTCM / Archegos / Woodford / 乐视/康美 / 抱团瓦解 / 价值陷阱 等具体案例做同型论证
- 反例(浅): "历史上有类似教训" / 切入(深): "Archegos 2021: 集中度 + 杠杆 + 衍生品隐藏敞口 三道闸破任一即强减; 本股集中度 X% / 杠杆 Y / 隐性敞口 Z, 任一破则同型路径"
- 适用: stock-bear (永久损失) / risk-safe (尾部) / asset-bear (周期顶)

## §3 三层辩论焦点差异 (避免不同层用同套话, GATE attempt#1 duan 视角深化)

| 层 | 焦点 | bull 应引 ≥1 派 | bull 禁引 (生硬错位) | bear 应引 ≥1 派 | bear 禁引 |
|---|---|---|---|---|---|
| **asset (大类)** | 周期定位 + equity_quota / 流动性 / 政策 | 马克斯-周期定位(渗透率S曲线/估值分位) / 达里奥-原则化(逆向用) | 段永平-好生意 (大类无具体公司, 无复购/定价权可谈) / 费雪-scuttlebutt (无个股客户名单) | 达里奥-风险优先 / 死亡清单-LTCM(相关性崩溃) / 死亡清单-Archegos(杠杆+集中) / 死亡清单-抱团瓦解(2021核心资产) | 段永平-好生意 / 费雪 (同上) / 死亡清单-乐视康美(无具体公司财务) |
| **industry (行业)** | chokepoint 卡位 + 五力 + 景气 | 费雪-scuttlebutt(招标公告/海关数据/产能地图/专利碎片) / 马克斯-紫苏叶(低关注度产业链) / 段永平-好生意(行业商业模式) | 死亡清单-LTCM(相关性是大类层议题) | 芒格-逆向(行业基本面双杀路径) / 达里奥-周期(资本开支顶/产能过剩) / 死亡清单-价值陷阱(持续低 PE 行业基本面恶化) / 死亡清单-抱团瓦解 | 死亡清单-Archegos(杠杆是大类/个股层) |
| **stock (个股)** | 预期差三锚(隐含增速/定价充分度/催化) | **三派全适用主战场**: 段永平-好生意(复购+定价权+FCF) / 费雪-scuttlebutt(客户名单+专利) / 马克斯-紫苏叶/错杀龙头(中际旭创¥88案) | (本层是 §2 主战场, 无禁引) | **三派全适用**: 芒格-逆向(死亡清单具体场景) / 达里奥-风险优先(尾部赔率) / 死亡清单 8 案例任选 | (本层无禁引) |
| **risk (个股风险三方)** | 仓位/集中度/赔率 / 隐性敞口 | aggressive 应引 马克斯-紫苏叶(边际加仓机会) / 段永平-好生意(确定性窗口加仓) | 死亡清单(是 safe 的弹药) | safe 应引 死亡清单全套 / 达里奥-永久损失 / 芒格-逆向(下行测算) | 段永平好生意/费雪 (是 aggressive 加仓弹药) |

**应用原则**:
- **bull/bear 至少引 ≥1 应引派**, 缺 = critic 6.6 ④ NEEDS_CHANGES
- **引了"禁引派"** = 错位形式 cite, 即使 narrative 写得再像也算 fatal_flaw (例: asset-bull 谈"段永平复购率"= 大类层无具体公司, 错位)
- **risk-neutral** 是协调派, 同时引 bull+bear 派各 ≥1, 但应聚焦"哪些 aggressive 论点 safe 没驳倒/哪些 safe 论点 aggressive 没驳倒", 不是再开新派
- **跨层 cross-reference**: stock-bull 可引行业层 chokepoint 论据(费雪 scuttlebutt 上溯产业链), 但不应引 asset 层周期论据(粒度错位)

**长期演化协议**: 当 v4 加新分类(如 commodity 大类细分 / 新增 momentum 派) 时, 必须在 §2 加新派别 + §3 表加新层/新行 + USER_CORRECTION 区记录, 不允许"先上线后补 skill"导致 9 agent 引用悬空。

## §4 反 Goodhart 输出契约 (协议 Part 7 #10)

辩手 history 输出**禁止形式 cite**:
- ❌ 形式 cite: "本轮应用了 [段永平-好生意]" 但下文无对应 narrative
- ✅ narrative cite: "段永平好生意三问: (1) 复购率 X% — 数据见 input #5 (2) 提价能否过 — Q2 提价 Y% 客户未流失 (3) FCF 转化 Z% — 5年均值 — 三问全过, 看多核心"

每轮输出末尾必填 `methodology_used`:
```json
{
  "methodology_used": [
    {"派别": "段永平-好生意", "本轮如何用的": "narrative 1-2 句, 必须能在 history 上文找到对应段落"},
    {"派别": "费雪-scuttlebutt", "本轮如何用的": "..."}
  ]
}
```

critic 6.6 必查: 随机抽 ≥2 项 `本轮如何用的` narrative, 必须能在 history 找到具体段落, 否则形式 cite = fatal_flaw。

## §5 输入消化铁律 (AGENTS.md §0ter 配套)

辩手输入 5000-15000 字 (data-desk 完整 JSON + 上一阶段产出 + 历史 history 累积) 必须配本 skill 消化:
- 不应"立场角色 + 满血输入" → 浅薄输出
- 应"立场角色 + 满血输入 + 本 skill 派别切入" → 方法论对抗

输入字数高 = 信息密度高 = 必须用 skill 派别切入压缩为可辩论的核心论点 (而非堆砌摘抄)。

<!-- USER_CORRECTION_START — 用户纠错沉淀的硬铁律, 禁日常编辑改写, 只有循环 CONSOLIDATE 经 GATE 能更新 -->
- 2026-06-17 自进化循环 iteration 3 落地: 9 个 bull/bear 辩手 zero skill cite zero ruler narrative 是用户'每个 agent 浅尝即止'诉求的最痛切片。本 skill 一个覆盖 9 agent 单点聚焦不违反 Part 7 #3 批量浅做铁律。配 critic 6.6 升级 + mine scan_debate_discipline 形成三层联动。
<!-- USER_CORRECTION_END -->

---

## §6 与协议的关系

本 skill 是 `planning/v4/self-evolving-optimization-loop.md` Part 2.6 IPS-多PM委员会 + critic 6.6 辩论深度铁律 的可执行落地。每轮辩论都应让 critic 看到 (a) 3 铁律真做到 (b) 派别切入 narrative 真出现 (c) methodology_used 不是形式 cite。**目标**: 让辩论从"立场对撞口号"变成"超级投资人方法论对抗"。
