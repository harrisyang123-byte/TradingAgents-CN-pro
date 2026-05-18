# 组合顾问引擎 (Tier 2)

**变更**: portfolio-advisor-engine
**日期**: 2026-05-18

## 概述

Tier 2 组合顾问引擎在 Tier 1 单标的分析引擎之上构建组合级别的投资建议系统。读取 Tier 1 存档报告 + 用户持仓数据，通过三角色辩论 + CIO 裁决，输出结构化操作处方。

Tier 1 不做任何修改。两层引擎独立运行：Tier 1 按单只标的跑深度分析，Tier 2 读 Tier 1 报告做组合层面决策。

## 架构

### 三角色信息差设计

核心原则：**同一个 LLM 用不同 prompt 不会产生真正的思维多样性。信息差是多 Agent 系统中创造有效分歧的核心机制。**

| 角色 | 读取数据 | 不读数据 | 输出 |
|------|---------|---------|------|
| 持仓分析师 | Tier 1 报告摘要 + 当前价格 + 持仓成本 | 宏观环境、行业趋势 | analyst_assessment |
| 策略师 | 组合仓位分布 + 行业集中度 + 相关性 | 个股报告细节 | strategist_assessment |
| 侦察兵 | 组合缺口 + 非持仓存档报告(Buy/Overweight) | 个股持仓细节 | scout_assessment |

### 图拓扑

```
START → Analyst → Strategist → Scout
  → debate_analyst → debate_strategist → debate_scout → counter
  → [count < N ? 回到 debate_analyst : CIO] → END
```

默认 2 轮辩论（`advisor_debate_rounds` 可配置），总计 ~10 次 LLM 调用。

### CIO 芒格思维约束

- **逆向验证**：每条加仓/建仓建议必须回答"如果错了最大亏损多少"
- **认知偏差检测**：禀赋效应、近因偏差、锚定效应
- **定量红线**：单只标的 ≤ 30%，单一行业 ≤ 50%（可配置）

## 实现要点

### 文件结构

```
tradingagents/agents/advisors/
├── __init__.py
├── advisor_states.py    # AdvisorState, AdviceItem, AdvisorDebateState
├── analyst.py           # create_portfolio_analyst(llm)
├── strategist.py        # create_strategist(llm)
├── scout.py             # create_scout(llm)
└── cio.py               # create_cio(llm) + _parse_prescription()

tradingagents/graph/
└── advisor_graph.py     # AdvisorGraph + propagate_advice()

app/services/
└── portfolio_advisor_service.py  # PortfolioAdvisorService
```

### 数据流

1. `PortfolioAdvisorService` 调用 `PortfolioService.get_portfolio_summary()` 获取持仓
2. 从 `analysis_results` 集合读取 Tier 1 报告（持仓标的 + 非持仓标的）
3. 构建 `AdvisorState` 初始状态，传入 `AdvisorGraph.propagate_advice()`
4. LangGraph 图执行三角色独立分析 → 辩论 → CIO 裁决
5. CIO 输出 JSON 处方（`_parse_prescription()` 从 Markdown 中提取 JSON 数组）
6. 结果存储到 `portfolio_advice` 集合

### 异步执行

复用 Tier 1 模式：`ThreadPoolExecutor` 在后台线程中运行，完成后 WebSocket 通知前端。

### API 端点

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | /api/portfolio/advice | 触发生成（校验持仓非空 + 无进行中请求） |
| GET | /api/portfolio/advice/latest | 最新一份建议 |
| GET | /api/portfolio/advice/{advice_id} | 指定建议（含权限校验） |
| GET | /api/portfolio/advice | 分页历史列表 |

### 前端

持仓页面 "组合建议" 按钮 → 轮询状态（3s 间隔） → el-drawer 展示：
- 处方表格（el-table，操作颜色标记：红=买入/加仓，绿=卖出/减仓，灰=持有）
- CIO 裁决文本
- 折叠面板（el-collapse）分角色展示独立评估 + 辩论记录
- 历史建议 el-select 切换

## 关键决策

1. **D1: 独立图 vs 复用 Tier 1 图** — 选择新建独立 `AdvisorGraph`，但复用辩论模式（DebateState 结构 + 轮转逻辑）。Tier 1/2 图拓扑完全不同，强行复用导致大量条件分支。
2. **D2: 三角色数据隔离** — 各角色在独立分析阶段只看分配给自己的数据子集。
3. **D3: 侦察兵数据源优先级** — 历史报告(成本零) > AKShare 行业 > 雪球热门。
4. **D4: CIO 思维约束** — 硬编码芒格逆向 + 偏差检测 + 定量红线，是结构性约束而非装饰性 persona。
5. **D5: 报告过期阈值** — 默认 7 天，可配置。过期不等于不可用，标注提醒即可。

## 注意事项

- Tier 2 可能与 Tier 1 产生矛盾（如组合集中度原因建议减仓一只 Tier 1 评级 Buy 的股票），这是设计特性，不是 bug
- 30+ 只持仓时会截断（前 20 只详细分析，其余合并汇总）
- AKShare 行业接口不稳定时侦察兵 graceful fallback 到历史报告
- CIO 处方通过 `_parse_prescription()` 从 LLM 输出中提取 JSON，解析失败返回空列表
