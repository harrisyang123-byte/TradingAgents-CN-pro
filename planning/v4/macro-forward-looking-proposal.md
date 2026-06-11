# v4 宏观分析前瞻能力补强方案

> **用户批评（2026-06-10）**：宏观现在只有已知数据，未来情况没有预测。例如美国刚公布的 CPI 4.x，公布前就有很大风声会决定后续市场走势——v4 宏观没体现这层。

## 架构决策：不新增 agent，按维度内化前瞻能力（MECE 优先）

考虑过三个方案：①复用现有 macro 分析师 ②新增 v4-asset-analyst-forward ③只在 director 整合。

**结论：1+3 组合，不新增 agent。**

理由：当前三分析师按**维度** MECE 划分（macro/flow/policy），不是按时间。如果按时间新增 forward agent，必然要在 forward 里再分宏观/资金/政策——**两条划分轴重叠 = 破坏 MECE**。前瞻不是新维度，是同一维度的时间延伸，应内化进现有分析师而非另起一行。

落地：
- **data-desk** → 增加 `forward_calendar` + `consensus` 取数（取数职责天然属于 desk）
- **3 分析师** → 各自维度内增"现状 + 前瞻"任务（职责单一在维度，时间是次维度）
- **director** → verdict 加 `forward_view` 整合路径情景+触发监控（拍板天然职责，不增 analyst）

## 诊断（确实欠缺什么）

当前宏观体系是**回看 nowcasting + 反思**两层，缺**前瞻 forecasting + 预期差**：

| 能力维度 | 当前 v4 | 缺口 |
|---|---|---|
| **现状快照（nowcasting）** | ✓ 22 指标 verified+source | 已有 |
| **历史反思（reflection）** | ✓ 上一版改判原因+self_check | 已有 |
| **前瞻日历** | ✗ | 未来 1-4 周关键发布/会议（FOMC/CPI/非农/社融/PMI/NPC）的**时间表** |
| **市场一致预期** | ✗ | Bloomberg/Reuters consensus 数字（市场已 price-in 什么） |
| **预期差识别** | ✗ | 我们的判断 vs market consensus 的偏差（CPI 风声=预期 vs 实际） |
| **路径情景** | 部分（定性） | 缺概率化情景：base/bull/bear 各对应什么数据 + 大类反应剧本 |
| **触发监控** | 部分（valid_until） | 缺"看到 X 就改判"的明确触发清单 |

## 改造方案：宏观三层叠加

```
Layer 1 nowcasting       已有 → 22 指标当前值
Layer 2 forward calendar 新增 → 未来 4 周关键事件 + 一致预期 + 我方观点
Layer 3 expectation gap  新增 → 与共识的偏差 + 路径情景 + 触发监控
```

### 落地：3 个文件改 + schema 扩展

**A. `agents/advisor/v4-data-desk.md`**：新增取数任务

```yaml
# 22 指标 nowcasting 之外补取
forward_calendar:           # 未来 4 周关键事件
  - date: 2026-06-12
    event: 美国 5 月 CPI
    consensus: 4.1%         # Bloomberg/Reuters 一致预期
    prev: 3.9%
    importance: high
  - date: 2026-06-18
    event: FOMC 会议 + 点阵图
    consensus: 维持 3.50-3.75% 不变, 25bp 加息概率 22%
    importance: high
  - ...（10-12 条）
consensus_snapshot:         # 关键宏观变量市场共识
  fed_2026_eoy: 3.50%       # 市场对 2026 年底联邦利率预期
  cn_gdp_2026_q2: 4.8%
  ...
```

来源：FactSet/Bloomberg Economic Calendar / 路透 / 各大券商月报，标 estimated 容许多源分歧。

**B. `agents/advisor/v4-asset-analyst-macro.md`**：增加前瞻判断任务

宏观分析师除了消费 22 指标，还要：
1. 对每个 high-importance 事件，给出**我方预测 vs consensus**的偏差（hawkish/dovish/inline）
2. 输出 path_scenarios：base / bull / bear 三情景概率 + 各对应的数据特征 + 大类资产反应剧本
3. 输出 trigger_monitor：未来 1 月内"看到 X 就改判"的明确条件

**C. `agents/advisor/v4-asset-director.md`**：verdict 加 forward_view 字段

```json
{
  "verdict": {
    "stance": "...",
    "forward_view": {
      "near_term_calendar": [
        {"date":"2026-06-12","event":"美CPI","consensus":"4.1%","our_view":"≥4.3%偏鹰","gap":"hawkish_surprise_risk","impact":"美10Y突破4.7→A股QDII敞口加压"},
        ...
      ],
      "consensus_vs_view": "市场一致预期Fed 9月降息25bp;我方判断概率<40%(粘性通胀+就业稳),与consensus偏差=hawkish_drift",
      "path_scenarios": [
        {"name":"base","prob":0.55,"trigger":"CPI 4.0-4.2%且非农15-25万","macro":"维持不动","equity_impact":"+0~5%震荡"},
        {"name":"bull","prob":0.25,"trigger":"CPI跌破3.8%+非农<15万","macro":"9月降息预期升至70%","equity_impact":"+8~12%估值修复"},
        {"name":"bear","prob":0.20,"trigger":"CPI 4.3%以上+非农>30万","macro":"加息重启风险","equity_impact":"-10~15%杀估值"}
      ],
      "trigger_monitor": [
        "美CPI 6/12公布>4.3% → 立即降权益至40%",
        "FOMC 6/18点阵图上移>1次 → 减贵金属、加现金",
        "中国社融6/13公布<7.5% → 降权益至42%、加固收"
      ]
    }
  }
}
```

## 这次能解决用户痛点的地方

- ✓ **CPI 风声场景**：data-desk 把 6/12 CPI 列入日历 + 标 consensus 4.1% + 我方观点；analyst 标出"hawkish_surprise_risk"；director 给"看到>4.3% 立即降权益"的硬触发——风声不再被忽视。
- ✓ **会议/政策窗口**：FOMC、Jackson Hole、NPC、政治局会议 提前进入 forward_calendar，不会临时被动反应。
- ✓ **预期差识别**：每个事件都有 consensus 与我方观点对比，**"市场已 price-in 什么"显式可见**——这是宏观真正赚钱的环节（修正预期差）。

## 局限与坑（诚实标注）

1. **联网取数依赖**：consensus 需要 Bloomberg/Reuters 等数据源，免费版可能不全；可用 ForexFactory/Investing.com 补，部分手工采集。
2. **预测必然不准**：path_scenarios 的概率估计带主观性，但"承认不确定 + 列触发监控"比假装精确好——这正是达里奥流。
3. **维护成本**：日历每周需更新；建议 data-desk 每周一刷新一次 forward_calendar。
4. **不是占卜**：本设计不让 agent 预测短期价格，只让它把"市场共识 vs 我方观点 + 路径情景"显式化，目的是**风险预算**而非"押对一次行情"。

## 推荐落地顺序（一次只做一步）

1. **第一步：data-desk 加 forward_calendar 取数任务**（改 prompt + 我手工取一批 6 月日历做样本）
2. **第二步：asset-analyst-macro 加前瞻判断任务**（加 prompt 段）
3. **第三步：asset-director schema 加 forward_view 字段**（改 prompt + 输出 schema）
4. **第四步：实跑一次 asset:equity 验证**（用真实日历数据跑，看效果）
5. **第五步：前端补展示**（AssetDetailTab 加"未来 4 周日历 + 路径情景 + 触发"模块）

工作量评估：1-3 步各 30 分钟（改 prompt+schema），第 4 步 30 分钟实跑，第 5 步 1 小时前端。**总计约 3-4 小时**。

---

## 等你拍板（A/B/C/D）

- **A 全做**（推荐）：5 步全做，宏观真正补上前瞻能力，作为 v4 第二次重大能力升级
- **B 只做骨架（1-3 步）**：先把能力定义出来，第 4-5 步等用户先验证概念
- **C 仅手工示范一次**：先不动 prompt，我直接在最新 asset:equity 重跑里手工写一份完整 forward_view，让你看效果
- **D 不做**，宏观保持现状
