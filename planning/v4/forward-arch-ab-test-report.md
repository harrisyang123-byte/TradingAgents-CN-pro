# 宏观前瞻能力 — 增 agent vs 不增 agent A/B/C 测试报告

> **测试时间**：2026-06-11
> **方法**：独立 subagent 盲评 + CPI 实际值反演验证

## 测试结论

| 方案 | 独立 critic 盲评 | 关键评语 |
|---|---|---|
| **甲（基线·无前瞻）** | 52 分 | 纯现状后视镜，stance=neutral 回避站队，可执行性弱 |
| **乙（不增 agent·内化前瞻）** | **91 分 ✓ winner** | 唯一具备"诊断当下+预判未来+if-then 行动"三要素 |
| **丙（新增 v4-asset-analyst-forward）** | 84 分 | 前瞻深度最强但**现状层缺失/无独立 stance/可执行性稍弱** |

**反演验证（CPI 实际公布 4.2%）**：
- 乙：明确写"即使 inline 4.2% 市场也会 price 鹰派路径 + 美债冲高 + QDII 承压"——**正是公布后实际反应**（首破 4% 心理关口效应）
- 丙：识别"符合预期→反应温和"但**低估了首破 4% 心理冲击**
- 甲：完全未涉及

## Critic 原文推荐

> **不增 agent**——乙证明单一 director 在输入包中同时拿到现状指标+前瞻日历即可产出完整融合 verdict；**增独立 forward agent 会引入拼接缝隙和 MECE 重叠风险**。
>
> 正确做法：在 data-desk 输入包中固定增加 `forward_calendar` 字段（未来 30 天高影响事件+共识+预期差），director prompt 要求必须消费该字段并输出 `trigger_monitor`，无需新增 agent 角色。

## 决策

**采纳方案乙（不增 agent，按维度内化前瞻）**。这与之前架构思考的判断（MECE 优先于"按时间分"）一致——**且这次有数据证据**：

- 量化差距：91 vs 84，差 7 分（不是分析推断，是独立盲评）
- 反演验证：实际 CPI 公布后，乙的预判最准
- 结构性原因：前瞻不是新维度，是同一维度的时间延伸；新增 agent 会重叠

## 二次验证（11 维完整版）— 结论稳健

按用户要求扩展到 11 维（新增中长期路径/仓位拥挤/IV skew/假设证伪/尾部风险/跨市场领先）后再做一次 A/B/C：

| 测试 | 单 agent (乙) | 拆 agent (丙) | 差距 |
|---|---|---|---|
| 第 1 次 6 维 | 91 | 84 | +7 |
| 第 2 次 11 维 | **89** | 82 | +7 |

**Critic 关键判词**：
- 拆分 agent 的**信息损耗**（时间锚丢失 + 触发阈值模糊化）是主要扣分项
- 乙用**绝对阈值**（CPI>4.3%/VIX>28/OAS>3.8%/北向>300亿）直接映射行动；丙用**相对偏离**需二次计算
- 11 维单 agent 已达 89 分接近上限；边际增强应补 A 股期权数据源（50ETF 隐波/skew），**不是拆 agent**

**反演验证（CPI 公布 4.2%）**：乙基准情景 4.0-4.3% 精确覆盖 → 最从容；丙合格但保守；甲脱窘无预案。

**最终结论稳定**：✓ 不增 agent，按 11 维内化进现有 macro 分析师。

## 落地路径（共识方案）

1. **data-desk** → `agents/advisor/v4-data-desk.md` 加 `forward_calendar` + `consensus_snapshot` 取数任务（未来 4 周高 importance 事件 + Bloomberg/Reuters 共识）
2. **3 分析师** → 各自维度内增"前瞻判断"任务（不增 agent）：消费 forward_calendar 中本维度相关事件，给 my_view vs consensus + gap 标签
3. **director（asset/industry/stock 三层）** → verdict schema 加 `forward_view`{near_term_calendar, consensus_vs_view, path_scenarios, trigger_monitor}
4. **前端** → AssetDetailTab 加"前瞻日历 + 路径情景 + 触发监控"模块
5. **实跑验证** → asset:equity 用真实数据跑一次，看 forward_view 输出质量

工作量：约 3-4 小时；MECE 不破坏；可复用至 industry/stock 三层。
