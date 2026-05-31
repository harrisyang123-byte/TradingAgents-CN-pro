# 组合顾问引擎 (Tier 2)

**变更**: portfolio-advisor-engine → portfolio-advisor-four-level → l3-l4-agent-upgrade
**日期**: 2026-05-18 (初始) → 2026-05-23 (四层升级) → 2026-05-31 (L3/L4 Agent 升级)

## 概述

Tier 2 组合顾问引擎在 Tier 1 单标的分析引擎之上构建组合级别的投资建议系统。通过四层对抗架构（行业→标的→组合→处方），每层独立辩论 + 裁判裁决，输出结构化操作处方。

Tier 1 不做任何修改。两层引擎独立运行：Tier 1 按单只标的跑深度分析，Tier 2 做全市场扫描 + 组合层面决策。

## 四层对抗架构

```
Level 1: 行业方向（2轮辩论）
  Market Strategist ↔ Contrarian → Macro Judge (Go/NoGo)
  工具: get_industry_rankings, get_sector_fund_flows, get_macro_indicators

Level 2: 标的筛选（2轮辩论）
  Scout ↔ Stock Contrarian → Stock Judge
  工具: get_industry_constituents, get_company_profile, get_financial_summary,
        get_stock_quotes, get_fund_rankings

Level 3: 组合构建（工具型 Agent + 辩论）
  Analyst(tool-agent) → Strategist(tool-agent) → Scout(LLM) → 3-way debate

Level 4: 最终处方（工具型 Agent + 辩论）
  CIO(tool-agent) → Risk_Director(tool-agent) → debate → CIO_Final(tool-agent)
```

数据流：纯串行 L1 → L2 → L3 → enrich_price_data → L4。L3 的 Analyst/Strategist 注入 L1/L2 数据，enrich_price_data 在 L3→L4 之间注入 PE 历史分位。

## 角色清单（10 个 + 2 数据节点 + 1 CLI）

| # | 角色 | 层级 | 类型 | 工具 | 说明 |
|---|------|------|------|------|------|
| 1 | Market Strategist | L1 | tool-agent | 3 | 多方向辩手，行业生命周期五阶段模型 |
| 2 | Contrarian | L1 | tool-agent | 3 | 逆向挑战者，风险面辩手 |
| 3 | Macro Judge | L1 | 裁判 | 0 | Go/NoGo 裁定 |
| 4 | Scout | L2 | tool-agent | 5 | 巴芒四层过滤器 |
| 5 | Stock Contrarian | L2 | tool-agent | 5 | 标的挑战者 |
| 6 | Stock Judge | L2 | 裁判 | 0 | 推荐/观察/淘汰裁定 |
| 7 | Analyst | L3 | tool-agent | 2 | 逐只读 Tier1 报告 + 持仓体检 |
| 8 | Strategist | L3 | tool-agent | 3 | 行业集中度 + 前N大风险 + 现金拖累 |
| 9 | Scout L3 | L3 | 纯 LLM | 0 | 组合缺口识别（维持原状） |
| 10 | CIO | L4 | tool-agent | 6 | 分页读持仓 + L1/L2查询 + 派员工搜索 + ETF搜索 + 权重验证 |
| 11 | Risk Director | L4 | tool-agent | 2 | 读处方 + 压力测试 |
| 12 | CIO Final | L4 | tool-agent | 6 | 终裁复用 CIO tools |
| — | enrich_price_data | L3→L4 | 数据节点 | — | PE 历史分位计算 |
| — | cli/run_advisor.py | 入口 | CLI | — | 完整/精简模式执行 |

## LLM 调用量（~30+ 次 + 工具往返）

| 层级 | 分析 | 辩论 | 裁决 | 工具节点 |
|------|------|------|------|----------|
| L1 | 2 | 4 (2轮×2人) | 1 | max=3 call per agent |
| L2 | 2 | 4 (2轮×2人) | 1 | max=3 call per agent |
| L3 | 3 (tool-agent) | 6 (2轮×3人) | 0 | max=3 call per agent × 2 |
| L4 | 3 (tool-agent) | 2 (1轮×2人) | 0 | max=3 call per agent × 3 |
| **总计** | | | | **26 基础 + 工具往返 ~5-15 额外** |

## 多市场数据源

| 市场 | 数据源 | Fallback |
|------|--------|----------|
| A股 (cn) | AKShare | LLM 常识 |
| 港股 (hk) | yfinance | LLM 常识 |
| 美股 (us) | yfinance | LLM 常识 |

工具层每个 market 独立 try/catch，失败市场返回 `{"fallback": true}` 不影响其他市场。

## 图拓扑

```
START → market_strategist ↔ tools_l1_market → msg_clear_l1a → contrarian
  contrarian ↔ tools_l1_contrarian → msg_clear_l1b → debate_market_strat
  → debate_contrarian_l1 → [counter] → (2 rounds) → macro_judge → msg_clear_l1

  → scout ↔ tools_l2_scout → msg_clear_l2a → stock_contrarian
  stock_contrarian ↔ tools_l2_scontrarian → msg_clear_l2b → debate_scout
  → debate_scontrarian → [counter] → (2 rounds) → stock_judge → msg_clear_l2

  → Analyst ↔ tools_l3_analyst → msg_clear_l3a
  → Strategist ↔ tools_l3_strategist → msg_clear_l3b
  → Scout_L3 → debate branches (2 rounds)

  → enrich_price_data
  → CIO ↔ tools_l4_cio → msg_clear_l4a
  → Risk_Director ↔ tools_l4_risk → msg_clear_l4b
  → debate → CIO_Final ↔ tools_l4_cio_final → END
```

### 关键实现模式

- **工具绑定**: `prompt | llm.bind_tools(tools)` → `chain.invoke(state["messages"])`
- **条件边**: `_make_tool_router` 检查 `hasattr(last, "tool_calls")` + `tool_call_count` 上限 (3)
- **辩论循环**: `_make_debate_router` 比较 `count >= max_rounds`
- **死循环保护**: 每层独立 ToolNode + 独立 tool_call_count 计数器
- **Msg Clear**: 层间 `RemoveMessage` + `HumanMessage` 占位，避免 tool-call 消息污染下层

## 文件结构

```
tradingagents/agents/advisors/
├── __init__.py
├── advisor_states.py       # 3 debate TypedDicts + L3/L4 counter fields
├── market_tools.py          # 9 个 AKShare/yfinance 工具函数
├── market_strategist.py     # L1 tool-agent
├── contrarian.py            # L1 tool-agent
├── macro_judge.py           # L1 裁判
├── scout.py                 # L2 tool-agent (重写)
├── stock_contrarian.py      # L2 tool-agent
├── stock_judge.py           # L2 裁判
├── analyst.py               # L3 tool-agent (原纯LLM)
├── analyst_tools.py         # L3 Analyst 工具 (read_tier1_report, get_position_audit)
├── strategist.py            # L3 tool-agent (原纯LLM)
├── strategist_tools.py      # L3 Strategist 工具 (compute_sector_concentration, top_holdings, cash_drag)
├── risk_director.py         # L4 tool-agent (原纯LLM)
├── risk_tools.py            # L4 Risk Director 工具 (get_prescription_draft, check_stress_scenario)
├── cio.py                   # L4 CIO tool-agent + CIO Final tool-agent
└── cio_tools.py             # L4 CIO 工具 (get_position_batch, get_l1_verdict, get_l2_candidates, dispatch_scout, search_industry_etf, validate_allocation)

tradingagents/dataflows/
└── pe_percentile.py         # PE 历史分位计算

tradingagents/graph/
└── advisor_graph.py         # 四层拓扑 + 全部 ToolNode + 条件路由 + Msg Clear

app/services/
└── portfolio_advisor_service.py  # 适配新 graph 结构

cli/
└── run_advisor.py           # 组合顾问 CLI 入口

frontend/src/
├── api/paper.ts             # AdviceItem 类型
├── components/Layout/
│   └── SidebarMenu.vue      # 持仓组合入口
└── views/
    ├── Dashboard/index.vue
    ├── PaperTrading/index.vue
    └── Portfolio/Overview.vue
```

## CIO 芒格心智模型 + 决策卡片

- **20孔卡片**：处方 ≤ 8 条 (max_prescription_items)
- **5年视角**：每条买入必须回答"5年后生意会更好吗？"
- **行业生命周期校准**：期望膨胀期 → 自动降级
- **市场先生**：每条 BUY 标注"在利用恐惧还是顺从狂热？"
- **逆向验证**：每条买入回答"如果判断错了，最大亏损是多少？"
- **认知偏差检测**：禀赋效应、近因偏差、锚定效应

### 决策卡片 7 字段模型

每条处方输出包含信任层 + 执行层共 7 个字段：

| 字段 | 层 | 说明 |
|------|------|------|
| `priority` | 执行 | urgent/important/optional，控制卡片左侧色条 |
| `l1_context` | 信任 | 从宏观裁判报告提取的行业生命周期 + Go/NoGo |
| `l2_context` | 信任 | 从标的裁判报告提取的护城河评级 + 过滤结果 |
| `suggested_price` | 执行 | 基于 PE 分位 + MA20 的价格锚点判断 |
| `max_loss_pct` | 执行 | 逆向验证：判断错了的最大亏损 + 触发场景 |
| `five_year_view` | 执行 | 5年后生意会更好吗？是/否 + 理由 |
| `bias_check` | 执行 | 认知偏差自检，无显著偏差标注"无" |

后端 `_parse_prescription()` 所有新字段按可选处理（向后兼容）。

## PE 历史分位数据管道

`tradingagents/dataflows/pe_percentile.py` — 为决策卡片的 `suggested_price` 提供估值锚点。

### 三市场策略

| 市场 | 数据源 | 数据密度 | 分位精度 |
|------|--------|----------|----------|
| A 股 | BaoStock `query_history_k_data_plus` (peTTM) | ~1200 日数据点 | 精确 |
| 港股 | AKShare `stock_financial_hk_analysis_indicator_em` (EPS_TTM) + 日线 | ~9 年数据点 | 年度 |
| 美股 | yfinance `ticker.financials` (Basic EPS) + 5年价格 | ~5 年数据点 | 年度 |

### 接口

```python
# 单只标的
compute_pe_context("600519", "cn")  # → {current_price, pe_ttm, pe_percentile_5y, ma20, judgment, ...}

# 批量（持仓 + 候选）
enrich_price_context(positions, candidates)  # → {code: pe_context_dict}
```

### 降级路径

- 数据不足 (<10 有效 PE 数据点) → `insufficient_history`
- 亏损企业 (PE ≤ 0) → `negative_earnings`
- 数据源不可用 (网络/接口异常) → `data_unavailable`
- 所有降级场景返回 `judgment="数据不可用"`，前端隐藏 PE 进度条

## 降级策略

| 故障 | 行为 |
|------|------|
| AKShare 行业接口不可用 | L1/L2 用 LLM 常识判断，标注"无实时数据" |
| yfinance 超时/限流 | 港股/美股降级为 LLM 常识，A股继续正常 |
| 全部数据源不可用 | L1/L2 纯 LLM 常识驱动，全局标注"数据不可用" |
| LLM 调用超时 | 该节点重试1次，仍失败则整个 advice 标记 FAILED |

## 前端

持仓页面 "组合建议" 按钮 → el-drawer 展示：
- 决策卡片流（`DecisionCard.vue`，纵向排列，priority 排序）
  - 左侧色条：urgent=红, important=橙, optional=灰
  - 可折叠 l1/l2 上下文（行业方向 + 护城河）
  - PE 分位进度条（绿≤25% / 黄≤75% / 红>75%）
  - 风险行（max_loss + five_year_view + bias_check）
- 5 个可折叠 section：市场扫描(L1)、候选标的(L2)、风险审查(L4)、辩论记录(L1/L2)
- 现有 section（分析师/策略师/侦察兵/辩论记录）不受影响
- 缺失字段显示 "—"，PE 分位不可用时隐藏进度条

## 已知风险

1. ~~**CIO dual-mode 脆弱性**：通过检查 `risk_director_review` 是否为空切换初稿/终裁模式，无显式 mode 字段~~ ✅ L3/L4 升级消除此风险
2. **L1 辩论缺少 self-analysis 上下文**：debate 轮转时只传对手上一轮回应，不传自己的历史发言
3. **RemoveMessage 兼容性**：依赖 langgraph 版本，需验证 `RemoveMessage` 是否可用
4. **多市场降级未测试**：yfinance/AKShare 模拟故障场景待验证
5. **CIO 和 CIO_Final 共用同一套 6 阶段 prompt**：终裁阶段可能重复触发数据收集调用，浪费工具配额
6. **dispatch_scout 单工具失败无降级**：get_industry_constituents 等内部调用无 try/except，异常导致工具整体失败

## 蓝图 v2.0 全维度（2026-05-30 完成）

基于架构蓝图 v2.0，11 个维度全部实现：

| 维度 | 状态 | 实现方式 |
|------|------|---------|
| P0-1 Tier 1 全覆盖 | ✅ | batch 并行分析 33 只持仓 |
| P0-2 敞口引擎 | ✅ | `exposure_service.py` — 基金穿透 + 行业敞口矩阵 |
| P1-3 行业全量覆盖 | ✅ | L1 全行业 Go/NoGo + 深度辩论 |
| P1-4 存量增量拆分 | ✅ | `portfolio_audit_service.py` — 健康分 + CIO prompt 分区 |
| P2-5 资金分配 | ✅ | CIO prompt 资金约束 + 来源-去向配对 |
| P2-6 时机条件 | ✅ | timing (immediate/conditional/scheduled) |
| P3-7 相关性风险 | ✅ | Risk Director 注入敞口矩阵 + HHI + 重叠暴露 |
| P3-8 压力测试 | ✅ | `stress_test.py` — 5 种宏观情景 + 行业冲击估算 |
| P4-9 反馈闭环 | ✅ | `_format_feedback_context()` — 历史处方注入 CIO |
| P4-10 再平衡 | ✅ | `rebalance_preference` + prompt 章节 |
| P4-11 现金管理 | ✅ | 闲置资金配置建议 (货基/逆回购) |

## 关键决策记录

1. **D1: 四层 vs 两层** — 选择四层（行业→标的→组合→处方），每层独立对抗验证
2. **D2: L1/L2 工具型 agent** — 需要实时市场数据，不能依赖训练数据
3. **D3: L3 不改动** — 现有三角色辩论已成熟，改动风险大于收益
4. **D4: 辩论人数** — L1/L2 用 2人+1裁判，L3 保留 3人轮转，L4 用 2人+CIO终裁
5. **D5: 数据流串行** — L1→L2→L3→L4，L3 注入 L1/L2 数据
6. **D6: 多市场数据源** — A股 AKShare，港股美股 yfinance，独立降级
7. **D7: 处方上限 ≤ 8 条** — 芒格 20孔卡片哲学
8. **D8: 行业生命周期五阶段** — 新兴萌芽→期望膨胀→泡沫破裂→稳步成长→成熟稳定
9. **D9: AI 时代不设能力圈** — AI 能看懂大多数行业的生意逻辑
10. **D10: 巴芒四层过滤器** — 嵌入 Scout prompt，是核心筛选逻辑
11. **D11: 决策卡片模型** — 处方输出从纯 JSON 升级为 7 字段卡片（信任层 l1/l2 + 执行层 5 字段），替代 el-table 为纵向卡片流
12. **D12: PE 分位三市场策略** — A 股 BaoStock 日线精确分位，港股 AKShare 年度分位，美股 yfinance 年度分位，各自独立降级
13. **D13: 敞口穿透** — 基金不独立出买卖建议，重仓股拆解后与直接持股合并为敞口矩阵
14. **D14: 存量增量分离** — 已有持仓基于成本/P&L/持有时间判定，新机会需回答"替代谁"
15. **D15: 资金来源-去向配对** — Σ买入 ≤ 可用现金 + Σ卖出，不做"印钞"处方
16. **D16: 三档时机** — immediate（立即）/ conditional（条件）/ scheduled（定期），区分执行紧迫度
17. **D17: 压力测试预设5情景** — 关税/RMB贬值/加息/流动性/衰退，行业级冲击映射
18. **D18: 反馈学习** — 新分析自动加载历史处方，CIO 须对比并说明哪些判断对了/错了
19. **D19: L3/L4 Agent 升级** — 2026-05-31。CIO/分析师/策略师/风险总监从纯 LLM 提升为工具型 Agent。CIO 获 6 工具（含 dispatch_scout 派员工搜索），处方覆盖从 ~8 条提升至 37 条全覆盖
20. **D20: CIO 双节点（CIO + CIO_Final）** — 初稿节点产出行配置 + 处方案，终裁节点复用同一套 tools，图层面区分两个 ToolNode 和计数器

## 注意事项

- Tier 2 可能与 Tier 1 产生矛盾，这是设计特性，不是 bug
- 30+ 只持仓时会截断（前 20 只详细分析，其余合并汇总）
- AKShare 行业接口不稳定时 graceful fallback
- CIO 处方通过 `_parse_prescription()` 从 LLM 输出中提取 JSON，解析失败返回空列表
