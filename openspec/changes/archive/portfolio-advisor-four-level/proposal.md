# Proposal: Portfolio Advisor Four-Level Adversarial Architecture

## Why

当前 Tier 2 组合顾问只能分析现有持仓 + 推荐历史分析过的标的。Scout 是纯 prompt agent，没有实时市场扫描能力——它只能翻 `non_held_reports`（历史 Tier 1 分析报告中评级为买入/增持的标的），不能主动发现新的投资机会。

用户需求明确：
1. 扫描全市场（A股+港股+美股）发现好生意，不限于已分析过的标的
2. 在合适时机推荐买入好公司
3. 每个关键决策环节必须经过对抗验证（不能单人拍板）
4. 偏好巴菲特/芒格投资哲学（四层过滤器、安全边际、能力圈、逆向思维、20孔卡片、市场先生）
5. 偏好桥水流程结构（多 Agent 独立分析 → 辩论碰撞 → 裁判裁决）

核心洞察：AI 时代"能力圈"不再是瓶颈——AI 能看懂几乎所有行业的生意逻辑。瓶颈在深度分析（Tier 1）的 LLM 成本。需要在全市场扫描（便宜）和深度分析（贵）之间建立漏斗。

<!-- Dialectical Analysis -->
**方案对比**：
- 方案 A（前置数据预取）：在 Service 层预取行业数据/行情，注入 Agent prompt → 优点：LLM 无需工具调用，快且便宜。缺点：预取范围固定，Agent 无法根据分析需要动态获取数据。
- 方案 B（工具型 Agent）：Agent 自主调用工具获取实时数据 → 优点：灵活，Agent 可按需深入。缺点：LLM 调用次数增加（工具往返），可能出现死循环。

选择方案 B，理由：
1. Tier 1 已验证 `bind_tools + ToolNode + 条件边` 模式成熟可用
2. 市场数据变化快，预取数据到 Agent 分析时可能已过时
3. 死循环风险通过 `max_tool_call_count` 保护

**风险对冲**：
- 最可能失败的点：L1/L2 工具型 Agent 的 tool→LLM 往返循环在 AdviserState（无 `add_messages` reducer 历史）中可能出现消息累积问题 → 通过 Msg Clear 节点层间清理
- 预备方案：若工具调用不稳定，L1/L2 降级为纯 prompt（用 LLM 训练数据常识 + 标注"无实时数据"）

**Edge Case**：
- 多市场部分失败：A股 AKShare 正常但 yfinance（港股/美股）超时 → 需保证港股美股降级但不阻塞 A股分析
- 全部数据源不可用 → 纯 LLM 常识驱动，全局标注"数据不可用"

## What

1. 四层对抗架构（行业→标的→组合→处方），10 个角色，每层独立辩论+裁判
2. Scout 重写：纯 prompt → 工具型 Agent，支持 A股+港股+美股全市场扫描
3. 巴芒四层过滤器嵌入 Scout prompt（看懂生意→护城河→管理层→价格合理）
4. 芒格心智模型嵌入 CIO prompt（20孔卡片、5年视角、市场先生、逆向验证、认知偏差检测）
5. 多市场数据源：A股 AKShare + 港股美股 yfinance，降级策略完整
6. 前端抽屉新增市场扫描、候选标的、风险审查可折叠 section
