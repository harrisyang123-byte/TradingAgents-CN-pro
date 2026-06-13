# v4 五力深做架构调整（用户拍板：5 力专项 agent + 整合 agent）

> 决策时间：2026-06-13 | 决策依据：用户判断 + A/B 测试反思

## Why（为什么改）

之前 A/B 测试（半导体设备样本）显示"1 个深 agent 82 vs 5 力拼合 64"，但**测试设计不公平**：
- 单 agent 给 600 字深做，5 agent 每个仅 250 字浅做
- 5 agent 方案没有"整合 agent"做交叉编织，只是 5 段拼合
- 这等于让 5 agent 方案"故意输"

**用户的合理判断**（已采纳）：
> "5 力分别分析完成后，把结论给后续的辩论者们" —— 即 5 力是**输入产生器**深做证据，整合 agent 做编织，bull/bear 拷问，director 拍板。
> 这个架构与 v4 已有的"3 分析师 + bull/bear + director"模式一致。

## What Changes

### 新建 5 个力专项分析师
- `v4-stock-force-entry.md` — 潜在进入者威胁
- `v4-stock-force-substitute.md` — 替代品威胁（含物理规律驱动判断）
- `v4-stock-force-buyer.md` — 买方议价力（**偏基本面，必须用毛利率/营收-净利背离论证**）
- `v4-stock-force-supplier.md` — 供方议价力（**偏基本面，必须用成本结构论证**）
- `v4-stock-force-rivalry.md` — 同业竞争烈度（产能利用率+毛利率全行业波动）

每个 prompt 强制要求：
- 单力深做（≤450-500 字 JSON）
- 必须有证据数字（不空话）
- **不评价其他四力**（防扩散）
- 输出 implication_for_stock 落到该股具体含义

### 改造 v4-stock-analyst-competitive
角色从"独立竞争分析师"改为"**五力整合分析师**"：
- 消费 5 个 force agent 的 JSON 产出
- **核心任务=交叉编织**（cross_force_dynamics: 强化/抵消/最弱一环/趋势）
- 必融合财务（买方力 + 毛利率 / 供方力 + 成本同比）
- 必给 investability（买入条件 + 监控指标）
- 输出 moat_synthesis 150字+ 连贯结论

### 编排器改造（待落实）
个股分析流程：
```
data-desk(取数)
  → [5 force agent 并行深做] (并发3+2分批)
  → competitive 整合 agent(交叉编织)
  → financial + valuation analyst (与 competitive 并列)
  → bull/bear 3 轮辩论(消费 competitive.moat_synthesis + investability)
  → director(预期差+四维+forward_view 拍板)
  → critic 评审
```

## 工程成本（诚实标注）

- subagent 调用：原 1 次 → 现 5+1 = 6 次
- token 消耗：约 5x
- 单股个分析时间：原 ~3min → 约 ~10-15min
- 优势：每力深度更够 + 多视角抑制偏见 + 证据更厚（适合后续辩论拷问）

## 验收标准

落地后用恒瑞医药/北方华创/中际旭创**3 个不同行业**做公平 A/B：
- 甲：5 力深做 + 整合 agent（新方案）
- 乙：单 competitive deep agent（原方案）
- 独立 critic 盲评同等条件下哪个产出更好

如果新方案 ≥ 旧方案 +5 分 → 固化；< 5 分 → 退回单 agent（避免徒增工程成本）

## 当前进度

- [x] 5 力 agent prompt 建好（v4-stock-force-{entry,substitute,buyer,supplier,rivalry}.md）
- [x] competitive agent 改造为整合者
- [ ] 编排器整合（workflow-v4-advisor.js / collect_v4.py 串五力调用）
- [ ] 实跑验证（3 标的公平 A/B）
- [ ] 据数据决定固化 or 退回
