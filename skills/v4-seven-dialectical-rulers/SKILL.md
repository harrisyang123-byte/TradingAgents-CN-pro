---
name: v4-seven-dialectical-rulers
description: >
  Use when analyzing industry future market(行业未来市场), TAM size, CAGR sustainability,
  penetration rate stage, valuation reasonableness, leader concentration, or industry timing.
  Mandatory for: v4-industry-future-market-analyst (must apply ≥5 rulers in verdict),
  v4-investor-critic 6.11/6.11.x (must verify each ruler applied with verified URLs),
  v4-stock-valuation-engineer (uses ruler ④⑤ for forward PEG vs penetration cross-check),
  v4-alpha-hunter (uses ruler ⑦ for momentum confirmation).
  Provides 7-ruler SOP: ①TAM triangulation ②TAM decomposition ③CAGR duration test
  ④Penetration stage ⑤Forward PEG cross-period ⑥Leader share distribution ⑦Leading indicators cross.
  Each ruler has: SOP steps + verified data requirements + counter-examples + falsification triggers.
---

# 七把辩证分析尺 SOP

> **方法论真源**:`planning/v4/project-master-prompt.md §7-bis` + `planning/v4/unknown-bottleneck-framework.md`
> **2026-06-14 用户拍板固化为永久铁律**:"光有 verified 数字还不够,必须有方法论戳穿水分"
> **2026-06-17 v2 更新**:加 RULE-DATA-VERIFIED 取数 vs 推理分工铁律(防 ai_tam_verified 事故再发生)

## 谁必须用这把尺

| Agent | 必须应用尺 |
|---|---|
| `v4-industry-future-market-analyst` | 全部 7 把(verdict 显式体现 ≥5 把) |
| `v4-industry-bull/bear/director` | 至少 ④⑤⑦(渗透/PEG/景气) |
| `v4-stock-valuation-engineer` | ④⑤(渗透阶段+forward PEG 跨期) |
| `v4-alpha-hunter` | ⑦景气先行(确认方向) |
| `v4-investor-critic` 6.11/6.11.x | 全部 7 把必查 + 每尺数据来源 verified URL |

## ⚠️ 数据 verified 铁律(2026-06-17 加,血泪)

**主 agent 取数,subagent 推理。** 七把尺中:
- **必须主 agent web_search ≥3 独立 URL**:①TAM三角 / ②TAM拆解 / ④渗透率 / ⑥龙头瓜分(具体份额数字)
- **subagent 在 verified 数据基础上做推理**:③CAGR 久期(类比) / ⑤forward PEG(对标历史) / ⑦景气先行(指标交叉)
- **绝禁**:让没联网的 subagent(如 ask-agent-v2)自己"报"具体 TAM 数字 → 必凭训练记忆 → 必违反 RULE-DATA-VERIFIED 红线 → critic 直接 NEEDS_CHANGES

## 尺① TAM 三角验证

**目的**:同一指标 ≥3 独立来源交叉,差异>30% 标分歧不调和(避免单源偏差/口径错配)。

**SOP**:
1. 主 agent web_search 拿 ≥3 独立来源:McKinsey / Goldman / Gartner / IDC / SEMI / WSTS / marketsandmarkets / 工信部 / 行业协会
2. 每个数字标 URL + 发布日期 + 口径(如"hyperscaler capex" vs "全球 AI 总支出"含软件)
3. 偏差<15% → 取均值或中值
4. 偏差 15-30% → 取区间(如 $700-1000B)
5. 偏差>30% → **标分歧不调和**,口径核查后再判
6. 绝禁:subagent 凭记忆报"Goldman $400B"——必须有 URL

**反例(2026-06-17 ai_tam_verified 事故)**:
- ❌ subagent 输出"Goldman $400B / McKinsey $370-410B / Gartner $395B 偏差<15%"
- ✅ 主 agent web_search 后:Goldman $527B(2025.12)→ Wall Street 上修 / Mag7 $725B / Top9 CSP $830B / 全球 ~$1T
- 教训:subagent 凭训练记忆 = 2023-2024 旧数据,低估 50-100%

**falsification**:任一来源数字与年报/法说会原始数据不一致 → 整尺重做。

## 尺② TAM 拆解还原

**目的**:把 TAM 拆成可验证因子反推合理性(防纯口径数字注水)。

**SOP**:
1. 公式分解:TAM = ∑(子赛道单价 × 量 × 渗透率)
2. 每个子项独立 verified(用户数×ARPU×渗透 / 设备×单价×替换周期 / 服务器数×capex/服务器)
3. 子项之和 vs 尺①的总数 → 偏差<10% 算验证通过
4. 偏差>10% → 标"口径分歧"

**实例(AI 算力)**:$400B = GPU $190B(NVIDIA FY27 $180B×85%AI+AMD/Google) + HBM $50B(SK海力士产能×$25-30/GB) + 光互连 $20B + 电力 $70B + 封装散热 $57B → 总 $387B,与 web_search 真值 $700-1000B 不符 → **拆解还原暴露口径**(尺①是 hyperscaler 而非 mag5 单口径)

**falsification**:子项加和与总额偏差>20% → 数据不可信。

## 尺③ CAGR 久期检验

**目的**:用历史可比 S 曲线判断高增速持续年数(防永续高增速幻觉)。

**SOP**:
1. 找 ≥2 个历史可比行业(产业级 capex + 巨头持续投入特征)
2. 列出该行业从渗透 5%→50% 的窗口期(年数 + CAGR)
3. 将当前行业映射到对应窗口位置
4. 输出:剩余高增速年数 / post-peak 增速预期

**历史可比库**:
- 智能手机 2008-2014:6 年,渗透 5%→52%,CAGR 45-55%,post-peak 5-10%
- 新能源车 EV 2018-2025:7 年,渗透 1%→25%,CAGR 35-50%,post-peak 15-20%
- AI 基础设施 2023-?:基础设施层更重 → 类比 EV 7 年(2030 后降 12-18%)
- 智能手表 2014-2020:6 年,渗透 0%→25%
- 光伏组件 2015-2022:7 年,装机翻 5 倍

**falsification**:技术/政策外生冲击改变 S 曲线斜率(如智能机被中国手机 2014 后改变格局)。

## 尺④ 渗透率阶段类比

**目的**:用渗透率%定位 S 曲线位置,映射历史可比给未来空间。

**SOP**:
1. 定义渗透率口径(分母:全球 IT 总支出 / 数据中心总投资 / 全球电力消耗 / 汽车销量等)
2. verified 当前渗透率%(主 agent web_search)
3. 阶段判定:
   - **导入期 <10%**:估值溢价高(PE 50-80x),业绩波动大,但赔率最大
   - **爆发期 10-50%**:估值合理(PE 30-50x)+ 业绩高增,股价非线性放大
   - **成熟期 50-80%**:估值压缩(PE 15-25x),量增放缓
   - **衰退期 >80%**:卖出区
4. 历史可比锚定:智能机 2011=20% / EV 2021=10% / AI 2026=22%(数据中心口径)

**关键洞察**:**爆发期 10→50% 业绩增速 > 股价增速**,估值实际在压缩。仅看"涨多少"判退场是后视镜偏差。

**falsification**:渗透率分母口径错(如把"AI软件"含进"AI 基础设施 TAM")。

## 尺⑤ Forward PEG 跨期对比

**目的**:当前估值 vs 同类成长股同期渗透率阶段历史估值,判定贵贱。

**SOP**:
1. 取行业代表 PE 中位数(verified, AKShare/年报)
2. 取 forward 2-3 年常态 CAGR(剔除低基数+周期峰值)
3. 计算 Forward PEG = PE / CAGR
4. 对标历史可比同渗透率阶段:
   - EV 2018(渗透1%):PE 60-80x / CAGR 50%+ / PEG 1.2-1.6
   - EV 2021(渗透10%):PE 45-60x / CAGR 40% / PEG 1.1-1.5
   - 智能机 2011(渗透20%):PE 25-35x / CAGR 35% / PEG 0.7-1.0
5. PEG<1.0 + 渗透<50% = 成长股合理偏低
6. PEG>1.5 + 渗透>50% = 透支警戒

**关键修正(防 PEG 五大陷阱,详见 `skills/v4-peg-five-traps`)**:
- 周期股禁 PEG(用 PB+股息)
- 防御股禁 PEG(用 Gordon 类债)
- 低基数高增速必修正(剔除一次性反弹)

## 尺⑥ 龙头瓜分检验

**目的**:CR3/CR5/CR10 集中度判二三线空间。

**SOP**:
1. 主 agent web_search verified top3-5 当前份额%(年报/SEMI/IDC/Counterpoint)
2. 推算 2030E 份额(看 capex 投入 + 技术领先 + 客户绑定)
3. CR3>80% → 极垄断(二三线无空间, A 股若无龙头标的就放弃)
4. CR3=60-80% → 集中但有空间(主战场)
5. CR3<60% → 分散(多标的可选)

**实例**:
- AI GPU:NVIDIA 80% → 极垄断,A股无标的
- AI 光互连:CR5=65%(中际20%/Coherent15%/新易盛12%) → A 股主战场
- 数据中心电力:CR5<40% → 分散多标的

**falsification**:历史 top 3 名单变化(如台积电 vs 三星代工份额)。

## 尺⑦ 景气先行指标交叉

**目的**:≥3 先行指标同向才确认方向(防单点信号误判)。

**SOP**:
五大先行指标各取 verified 信号:
1. **库存周期**:渠道库存周转/上游晶圆/原料库存 → ↓库存=景气向上
2. **订单可见度**:在手订单/年化营收 → ↑订单=景气强
3. **价格趋势**:产品 ASP 季度环比 → ↑价=供需紧
4. **产能利用率**:晶圆厂/封测/工厂产能利用率 → >90%=供不应求
5. **龙头资本开支**:hyperscaler/龙头 capex YoY → ↑capex=主动投入

**判定**:
- ≥3 指标同向看多 → 景气方向确认
- 仅 1-2 指标 → 信号薄弱,等更多数据
- 出现矛盾(订单↑但价↓) → 警惕量增价跌

**实例(AI 算力 2026-06)**:5/5 同向看多(capex+60-80% / 订单可见度>1年 / 800G ASP 稳/HBM3E +20% / 产能>90% / NVIDIA Rubin 排产满)→ 景气强确认无疑。

## 输出格式(必产字段)

```json
{
  "tam_now_usd_b": "verified ≥3 URL 来源",
  "tam_2030E_usd_b": "verified + 口径明示",
  "cagr_pct": "区间非点值,标久期(剩余年数)",
  "penetration_stage": "导入/爆发/成熟/衰退 + 历史可比 + 渗透% verified",
  "industry_forward_peg": "PE 中位 / CAGR + 对标历史(EV2021/智能机2011)",
  "leaders_share_distribution": "verified top3-5 + 2030E 预期",
  "leading_indicators": "5 维交叉 ≥3 同向",
  "data_sources": "≥3 独立 URL + 发布日期 + 口径",
  "_data_verification_status": "verified_by_main_agent_websearch|inferred_by_subagent",
  "methodology_used": ["每尺逐一应用结果"]
}
```

## 反偷懒铁律

- ❌ subagent 凭训练记忆报具体 TAM/份额数字(必违 RULE-DATA-VERIFIED)
- ❌ 七把尺只提 1-2 把(浅尝即止)
- ❌ 无 URL/无口径标注(数字真假无法验证)
- ✅ 主 agent web_search 取 verified → subagent 用这些数字应用 7 把尺方法论推理
- ✅ verdict 显式体现 ≥5 把尺的应用结果
- ✅ 每个数字标 verified URL 或 estimated 状态

## critic 6.11/6.11.x 必查清单

1. ✓ 7 把尺 verdict 是否显式体现 ≥5 把
2. ✓ TAM/份额/渗透率每个数字是否有 verified URL
3. ✓ 是否标注"取数主体"(主 agent 还是 subagent 凭推理)
4. ✓ 历史可比类比是否合理(类比对象的 S 曲线特征匹配)
5. ✓ Forward PEG 是否考虑了周期/低基数/久期修正
6. ✓ 景气先行指标 ≥3 同向才算确认
7. ✓ 多源冲突是否标分歧不调和(>30% 偏差禁调和)
