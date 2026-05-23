# Design: Portfolio Advisor Four-Level Adversarial Architecture

## Architecture

```
L1: 行业方向（2轮辩论）
  Market Strategist ↔ Contrarian → Macro Judge (Go/NoGo)
  工具: get_industry_rankings, get_sector_fund_flows, get_macro_indicators

L2: 标的筛选（2轮辩论）
  Scout ↔ Stock Contrarian → Stock Judge
  工具: get_industry_constituents, get_company_profile, get_financial_summary,
        get_stock_quotes, get_fund_rankings

L3: 组合构建（2轮辩论，不改）
  Analyst ↔ Strategist ↔ Scout (3-way)

L4: 最终处方（1轮辩论）
  CIO → Risk Director → debate → CIO 终裁
```

## Data Flow

纯串行 L1 → L2 → L3 → L4。L3 的 Analyst/Strategist 注入 L1/L2 数据用于行业背景评估和集中度分析。

## Key Patterns (复用 Tier 1)

- `prompt | llm.bind_tools(tools)` → `chain.invoke(state["messages"])` — from `market_analyst.py:74`
- `add_conditional_edges` + `hasattr(last, "tool_calls")` + `tool_call_count` 上限 — from `conditional_logic.py:56`
- `should_continue_debate` pattern — from `conditional_logic.py:167`
- `Msg Clear` 节点（RemoveMessage + placeholder）— from `setup.py`

## State Changes

AdvisorState 新增:
- `messages: Annotated[list, add_messages]` — 工具型 Agent 必需
- L1: `market_intel`, `market_debate_state`, `macro_judge_verdict`, `market_tool_call_count`
- L2: `stock_candidates`, `stock_debate_state`, `stock_judge_verdict`, `stock_tool_call_count`
- L4: `risk_director_review`, `risk_debate_final`

移除: `non_held_reports`

## Multi-Market Data Sources

| Market | Data Source | Fallback |
|--------|------------|----------|
| A股 (cn) | AKShare | LLM 常识 |
| 港股 (hk) | yfinance | LLM 常识 |
| 美股 (us) | yfinance | LLM 常识 |

工具层每个 market 独立 try/catch，失败市场返回 `{"fallback": true}` 不影响其他市场。

## LLM Call Budget

| Level | Analysis | Debate | Judge | Total |
|-------|----------|--------|-------|-------|
| L1 | 2 | 4 (2r×2p) | 1 | 7 |
| L2 | 2 | 4 (2r×2p) | 1 | 7 |
| L3 | 3 | 6 (2r×3p) | 0 | 9 |
| L4 | 1 | 2 (1r×2p) | 0 | 3 |
| **Total** | | | | **26** |

工具往返额外 LLM 调用: max +8 (max_tool_call_count=3 per agent × 2 agents, minus initial calls)

## Files

| # | File | Action |
|---|------|--------|
| 1 | `tradingagents/agents/advisors/advisor_states.py` | Modify |
| 2 | `tradingagents/agents/advisors/market_tools.py` | New |
| 3 | `tradingagents/agents/advisors/market_strategist.py` | New |
| 4 | `tradingagents/agents/advisors/contrarian.py` | New |
| 5 | `tradingagents/agents/advisors/macro_judge.py` | New |
| 6 | `tradingagents/agents/advisors/scout.py` | Rewrite |
| 7 | `tradingagents/agents/advisors/stock_contrarian.py` | New |
| 8 | `tradingagents/agents/advisors/stock_judge.py` | New |
| 9 | `tradingagents/agents/advisors/risk_director.py` | New |
| 10 | `tradingagents/agents/advisors/cio.py` | Modify |
| 11 | `tradingagents/agents/advisors/analyst.py` | Modify |
| 12 | `tradingagents/agents/advisors/strategist.py` | Modify |
| 13 | `tradingagents/agents/advisors/__init__.py` | Modify |
| 14 | `tradingagents/graph/advisor_graph.py` | Rewrite |
| 15 | `app/services/portfolio_advisor_service.py` | Modify |
| 16 | `frontend/src/api/paper.ts` | Modify |
| 17 | `frontend/src/views/PaperTrading/index.vue` | Modify |
