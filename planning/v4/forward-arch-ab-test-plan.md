# 宏观前瞻能力 — 增 agent vs 不增 agent A/B/C 测试方案

> **用户要求（2026-06-10）**：不能通过分析得结论，要做测试再决定方案。复用之前"四维闸门 A/B 测试"的方法论——独立 subagent 盲评，结构性差距说话。

## 测试目标

**回答一个问题**：实现"宏观前瞻能力"应该用以下三种架构里的哪个？
- **基线**：当前 v4-asset-analyst-macro（无前瞻），现状对照
- **方案 A**：不增 agent，在现有 macro 分析师 prompt 内加前瞻任务
- **方案 B**：新增 v4-asset-analyst-forward 专做前瞻，macro 保持现状

判断标准：哪个产出对投资决策更有用 + 不破坏 MECE。

## 黄金样本：2026-06-09 视角的 CPI 前瞻

**为什么选这个时点**：
- CPI 在 2026-06-10（昨天）已公布 4.2%，是"已知答案"
- 6/9 当天 CNBC 等报道"Wall St consensus 4.2%（首次过 4%）"——风声明确
- 6/18 FOMC 会议未公布（真正前瞻）
- 这是**最理想的回放样本**——能精确验证"前瞻判断准不准"

## 输入（三方一致）

```yaml
当前时点: 2026-06-09  # 假设视角
22指标快照: 复用 asset:equity v4 的 evidence
forward_calendar:
  - date: 2026-06-10  # T+1
    event: 美 5 月 CPI
    consensus: 4.2% (Wall St)
    prev: 3.9%
    importance: high
    note: "首次过 4%, 关税推涨预期"
  - date: 2026-06-13
    event: 中国 5 月社融
    consensus: 7.6-7.8%
    importance: high
  - date: 2026-06-18
    event: FOMC 会议+点阵图
    consensus: 维持 3.50-3.75%, 25bp 加息概率 22%
    importance: high
  - date: 2026-06-27
    event: 中国 5 月规模以上工业利润
    importance: medium
持仓上下文: equity 44.24% 偏高, AI/QDII 拥挤
```

## 三个被测对象

### 基线（baseline_macro）
- **prompt**：当前 v4-asset-analyst-macro.md 不加任何前瞻
- **输入**：仅 22 指标快照（不喂 forward_calendar）
- **任务**：常规宏观分析

### 方案 A（macro_with_forward）
- **prompt**：基线 prompt + "增任务：基于 forward_calendar，对每个 high-importance 事件给出 我方观点 vs consensus + gap 标签 + 触发监控"
- **输入**：22 指标 + forward_calendar + consensus
- **任务**：现状分析 + 前瞻判断（同一 agent）

### 方案 B（separate_forward）
- **macro 子任务**：基线 prompt 不动（只看现状）
- **新增 forward 子任务**：专门 prompt = "你是宏观前瞻分析师,只做前瞻判断:消化日历+共识,输出预期差+路径情景+触发监控,不要重复现状描述"
- **输入**：同方案 A
- **任务**：两个独立子任务串行

## 评测维度（独立 critic 盲评，不知道哪个是哪个）

| 维度 | 评测点 | 权重 |
|---|---|---|
| **前瞻深度** | 是否识别 CPI 4.2% 风声 + 临界点判断 | 25% |
| **预期差识别** | 是否标出 hawkish_surprise_risk + 量化偏差 | 20% |
| **触发监控** | 是否给"看到 X 就改判 Y"的硬触发清单 | 20% |
| **可执行性** | 是否给出 6/10-6/18 期间的具体调仓动作 | 15% |
| **MECE 不重复** | 方案 B 中 forward 是否与 macro 内容重复 | 10% |
| **现状不丢** | 前瞻没让现状分析质量下降 | 10% |

## 反演验证（黄金标准）

CPI 实际值 4.2%，**已知正确判断**：
- ✓ 风声=4.2% 应在 6/9 已 price-in，惊喜程度低
- ✓ 但"首次过 4%"心理关口冲击 → 美 10Y 上行 + 美元走强 → A股 QDII 敞口压力
- ✓ FOMC 6/18 加息重启概率上调（即使没加，鹰派指引）
- ✓ 行动：6/9 应已减 QDII/AI 拥挤区，转红利+内需

**评测**：哪个方案产出最接近这个"事后正确"判断？

## 测试流程

1. **取数**：我（data-desk）联网核实 6/9 视角的 forward_calendar + consensus + 22 指标（约 30 分钟）
2. **三方并行**：subagent 跑 baseline / macro_with_forward / separate_forward 三份产出（约 15 分钟）
3. **独立 critic 盲评**：subagent 评分（不知哪个是哪个，按 6 维度打分）
4. **反演验证**：用 CPI 实际值 4.2% 对比哪份判断更准
5. **最终决策**：得分高 + 反演准 + MECE 健康 = 推荐方案
6. **报告 + 提交**：落 `planning/v4/forward-arch-ab-test.md`

## 工作量与风险

- 工作量：约 2 小时（取数 30min + 跑测 30min + 评分 15min + 写报告 30min + 提交）
- 风险：subagent 不稳定可能超时；铁律是失败则我主 agent 接管
- 局限：单一样本（一个 CPI 公布日），结论需后续多场景复测

---

## 等你拍板

- **A 按这方案做**（推荐）：严谨 A/B/C，结论用数据说话
- **B 调整测试设计**：你觉得哪里要改（评测维度/样本选择/权重）
- **C 简化版**：只做方案 A vs 基线，不测方案 B（如果你觉得"新增 agent 破 MECE"已经足够明显）

我的建议是 **A**——用户上次的教训正是这个：方案 B（新增 agent）虽然分析上"破 MECE"，但实际效果可能更好（专注度高），不测就推荐有偏。
