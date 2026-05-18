# 变更提案：结果反思系统 (TradingMemoryLog)

**变更 ID**: trading-memory-log
**优先级**: P1 #4
**状态**: 待实现

## 背景

TG-CN 现有 ChromaDB 按组件反思（bull/bear/trader/judge/risk），但无法追踪最终决策的实际收益。
TG upstream 的 `TradingMemoryLog` 补充了这一缺失：

- **Phase A**（写入）：管线结束时记录最终决策，标记 pending
- **Phase B**（解析）：下次同 ticker 运行时，获取实际行情收益，LLM 反思，更新为 resolved
- **注入**：`get_past_context(ticker)` 生成历史决策+反思文本，注入 Risk Manager prompt

两套系统互补：ChromaDB 做组件级反思（vector similarity 召回），TradingMemoryLog 做决策级结果追踪（append-only markdown log）。

## 变更范围

### 新增文件
1. `tradingagents/agents/utils/rating.py` — 5 级评级解析器（移植 upstream）
2. `tradingagents/agents/utils/trading_memory_log.py` — TradingMemoryLog 类（移植 upstream，无修改）

### 修改文件
3. `tradingagents/graph/reflection.py` — 添加 `reflect_on_final_decision()` 方法
4. `tradingagents/graph/trading_graph.py` — 接线：init memory_log、resolve pending、inject past_context、store decision
5. `tradingagents/graph/propagation.py` — `create_initial_state()` 接受 `past_context` 参数
6. `tradingagents/agents/utils/agent_states.py` — `AgentState` 添加 `past_context` 字段
7. `tradingagents/default_config.py` — 添加 `memory_log_path`、`memory_log_max_entries` 配置

### A 股适配
- `_fetch_returns()` 使用 akshare 替代 yfinance
- benchmark 映射：`.SH/.SZ/.SS` → 沪深300（`sh000300`），港股 `.HK` → 恒生指数

## 不变更
- 现有 ChromaDB 5 实例 + reflect_and_remember() 完全保留
- 现有 Reflector 的 5 个 per-agent reflect 方法保留
