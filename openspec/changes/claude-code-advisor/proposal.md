## Why

当前 Tier 2 组合顾问系统的 LangGraph 四层 Agent 管线存在三重问题，导致无法支撑用户做 60 万人民币的资金分配决定：

**内容品质不足** — 每层产出与专业投资公司差距巨大。L1 20 行业仅产出 1 个 Go（≈"全卖了"），L2 19 只候选全是大蓝筹，L3 策略师报"行业全部为未知"，L4 是操作清单而非资金分配方案。

**Agent 间数据断链** — msg_clear 清空每层上下文，导致 L3 策略师看不到分析师对 36 只持仓的逐只评估。

**跨层矛盾无检测** — 中兴通讯 3 份 Tier1 报告互相矛盾（1 买入+2 卖出），PE 99% 分位估值偏高但 Tier1 说买入——系统中没有任何 Agent 能发现。

## What Changes

- **新建** `cli/claude_advisor.py` — Python 编排 + 9 个子 Agent 混合架构。每个子 Agent 一次独立 LLM 调用，通过 JSON 文件总线传递完整上下文。原 LangGraph 代码不动（保留在 fix/fund-akshare-api-error 分支）
- **新建** 市场温度计数据收集 — 北向资金、涨跌比、融资余额、千股千评、黑天鹅检测规则
- **新增** 交叉验证层 — Python 规则引擎检测 Tier1 矛盾、PE vs 建议冲突、敞口重叠、情绪 vs 基本面冲突
- **修改** Tier2 每层 Agent 的 prompt 模板 — 强制数据引用、逆向情绪修正、量化输出字段
- **移除** 3 个冗余 Agent — L2 反向者（Scout 自带 top_risks+规则引擎替代）、L2 裁判（6 维评分映射表替代）、L3 侦察兵（分析师+策略师覆盖）
- **数据收集修正** — Tier1 查询 OR 多字段匹配补全覆盖率（当前 9/36 → 目标 ≥ 25/36）
- **无需前端改动** — 输出写入 MongoDB `portfolio_advice`（source='claude-code-v3'），前端零改动

## Capabilities

### New Capabilities

- `claude-advisor-pipeline`: Python 编排的 9 个子 Agent 四层分析管线，通过 JSON 文件总线传递完整上下文，替代 LangGraph 的 msg_clear 链
- `market-thermometer`: 市场温度数据收集（北向资金、涨跌比、融资余额、千股千评），逆向情绪修正注入每个 Agent 决策
- `cross-validation`: Python 规则引擎的矛盾检测——Tier1 方向冲突、PE 分位 vs 建议冲突、敞口重叠、情绪 vs 基本面冲突、黑天鹅预警

### Modified Capabilities

- `l1-industry-direction`: L1 行业哨兵部从 Go/NoGo 标签升级为超配/标配/低配/零配 + 量化指标 + 情绪修正
- `l2-stock-screening`: L2 Scout 从全市场盲扫改为基于 L1 Go 行业 + 强制财务数据引用 + 6 维评分 + 价格区间 + 催化剂
- `l3-portfolio-diagnosis`: L3 策略师从"组合顾问"改为"组合诊断报告员"——不输出操作建议，输出集中度/一致性风险/隐形暴露诊断
- `l4-cio-prescription`: L4 CIO 处方增加敞口诊断、资金分配方案、黑天鹅预警段落、全市场水温 reference
- `data-collection-layer`: 数据收集层增加 Tier1 OR 多字段查询 + position.industry LLM 分类填充 + 基金穿透数据采集

## Impact

**Affected code**:
- 新建 `cli/claude_advisor.py`（主控脚本）+ `cli/prompts.py`（8 个子 Agent prompt）
- 修改 `app/services/portfolio_advisor_service.py`（Tier1 查询修复 + 基金穿透）
- 修改 `app/services/portfolio_service.py`（get_portfolio_summary 填 industry）
- 不影响 `tradingagents/graph/advisor_graph.py`（LangGraph 原代码保持在 fix 分支不变）
- 不影响前端代码（MongoDB 写入格式兼容）

**Affected dependencies**: 无新增

**PRD**: [planning/v2/agent-pipeline-fix_prd.md](../../planning/v2/agent-pipeline-fix_prd.md) v3.0.0

**Architecture**: [planning/v2/architecture_full.md](../../planning/v2/architecture_full.md)

**原型**: 无 UI 变更，跳过原型

<!-- Dialectical Analysis -->

### 方案对比

| 维度 | 方案 A: 修 LangGraph | 方案 B: Claude Code 编排（选） |
|------|-------------------|---------------------------|
| 上下文完整性 | msg_clear → 断裂 | JSON 文件总线 → 完整 |
| 交叉验证 | 无法加上 | 规则引擎 30 行搞定 |
| 修复成本 | 改 6 个文件 | 1 个新文件 |
| 验证耗时 | ~22min/次 | ~5min/次 |
| 子 Agent 独立性 | 结构上独立但上下文断裂 | 真正独立 prompt + 独立上下文 |
| 技术未来性 | 锁定 LangGraph | 框架无关，Claude API 直接调用 |

### 取长补短

- 数据工具层全部复用现有代码（market_tools, pe_percentile, ExposureService 等）
- 辩论结构保留原版（L1 2 轮、L3 2 人 2 轮、L4 CIO↔风控）
- L2 辩论通过目的验证确定为冗余 — 反向者和裁判没有信息不对称

### 风险对冲

- **风险 1: 情绪数据实时采集不可靠** → 已有 market_signals.py 采集、AKShare 回退。采集失败时标"数据不可用"，Agent 回归纯基本面判断
- **风险 2: 9 个子 Agent 的 LLM 调用总耗时超预期** → 子 Agent 并行最大并行度=1（互相依赖）。如超 5min，可把 L2 Scout 的工具调用从 6 个减为 3 个（常规覆盖）
