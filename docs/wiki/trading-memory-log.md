# TradingMemoryLog 结果反思系统

> 决策级结果追踪 — 记录最终交易决策，下次运行时用实际收益做 LLM 反思

## 核心概念

TradingMemoryLog 与 ChromaDB 反思是两套互补系统：

| 维度 | ChromaDB 反思 | TradingMemoryLog |
|------|--------------|------------------|
| 粒度 | 组件级（bull/bear/trader/judge/risk 各自反思） | 决策级（最终交易决策） |
| 存储 | 向量数据库，按 similarity 召回 | Append-only markdown 日志 |
| 触发 | 每轮运行后各 agent 独立反思 | Phase A 记录 → Phase B 下次解析 |
| 注入 | 各 agent 独立召回历史 | `past_context` 注入 Risk Manager prompt |

## 生命周期

### Phase A — 写入（当轮结束时）
- `memory_log.store_decision(ticker, decision, rationale)` 记录最终决策
- 状态标记为 `pending`（尚无实际收益数据）

### Phase B — 解析（下次同 ticker 运行时）
- `_resolve_pending_entries(ticker)` 获取实际行情收益
- LLM 对比预期 vs 实际，生成反思文本
- 状态更新为 `resolved`

### 注入
- `memory_log.get_past_context(ticker)` 汇总历史决策 + 反思
- 通过 `create_initial_state(past_context=...)` 注入 AgentState

## A 股适配

- `_fetch_returns()` 使用 akshare 替代 yfinance
- Benchmark 映射：
  - `.SH` / `.SZ` / `.SS` 后缀 → 沪深300（`sh000300`）
  - `.HK` 后缀 → 恒生指数

## 评级系统

`rating.py` 提供 5 级评级解析：Buy / Overweight / Hold / Underweight / Sell

## 配置

- `memory_log_path` — 日志文件路径（默认 `memory_log.md`）
- `memory_log_max_entries` — 最大保留条目数

## 文件清单

| 文件 | 说明 |
|------|------|
| `agents/utils/rating.py` | 5 级评级解析器 |
| `agents/utils/trading_memory_log.py` | TradingMemoryLog 类 |
| `graph/reflection.py` | `reflect_on_final_decision()` 方法 |
| `graph/trading_graph.py` | 接线：init / resolve / inject / store |
| `graph/propagation.py` | `create_initial_state()` 接受 past_context |
| `agents/utils/agent_states.py` | AgentState 新增 past_context 字段 |
