# Proposal: fund-tier1-analysis

## Why

用户持有基金（如 QDII、主动股票型），但系统只能分析股票，无法对基金给出交易信号。用户需要在 FundDetail 页面触发基金分析，获得与股票分析一致的 buy/sell/hold 信号，并存档供 Tier 2 组合分析使用。

## What

1. **基金分析管线**：新建 `fund_graph.py`，复用 LangGraph 辩论框架，替换数据工具层（净值历史、业绩排名、风险指标）
2. **SSE 实时消息流**：扩展 `progress_callback`，把 Agent 分析文本 + 工具调用名称通过 SSE 推送给前端
3. **FundDetail 触发入口**：加"AI 分析"按钮，触发分析，展示实时消息流和最终报告
4. **结果存档**：存入 `analysis_tasks` 集合，加 `instrument_type: "fund"` 字段

## 方案对比

| 方案 | 描述 | 风险 | 工作量 |
|------|------|------|--------|
| A：改现有 trading_graph.py | 加 instrument_type 分支 | 高（破坏股票分析） | 中 |
| **B：新建 fund_graph.py（选定）** | 复用框架，独立数据层 | 低 | 中 |
| C：单次 LLM 调用 | 不用 LangGraph | 低 | 小 |

选 B：零风险，股票分析完全不受影响，可复用辩论框架。

## 分析师角色设计

```
基金经理分析师（FundManagerAnalyst）
  数据：基础信息、历史业绩、同类排名、夏普比率
  输出：基金经理评价报告

持仓/指数分析师（FundHoldingsAnalyst）
  数据：重仓股（主动型）/ 指数成分+净值走势（QDII/指数型）
  输出：持仓质量报告

风险分析师（FundRiskAnalyst）
  数据：最大回撤、年化波动率、同类排名走势
  输出：风险评估报告

综合裁判（FundTrader）
  输入：三份报告
  输出：action(buy/sell/hold) + confidence + expected_return + reasoning
```

## 输出格式

```json
{
  "action": "buy",
  "confidence": 0.78,
  "expected_return": "+8%~+15%（6个月）",
  "reasoning": "...",
  "fund_manager_report": "...",
  "holdings_report": "...",
  "risk_report": "..."
}
```

## SSE 消息格式

```json
{"type": "agent_message", "agent": "基金经理分析师", "content": "..."}
{"type": "tool_call", "agent": "持仓分析师", "tool": "get_fund_holdings"}
{"type": "progress", "step": "风险分析师", "percent": 60}
{"type": "complete", "result": {...}}
```

## 风险

- AKShare 数据质量：QDII 基金无重仓股，用净值+指数信息替代，LLM 可能分析质量较低
- LLM 对基金的训练数据少于股票，输出质量待验证

## PRD

见 `planning/v1/fund-detail_prd.md`（阶段一 PRD，本变更在其基础上扩展）

## 原型

见 `planning/v1/fund-detail_prototype.html`（阶段一原型，本变更新增分析触发区域）
