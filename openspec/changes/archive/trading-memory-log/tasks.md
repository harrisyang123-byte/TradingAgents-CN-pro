# Tasks: trading-memory-log

## T1: 移植 rating.py
- 从 upstream 复制 `agents/utils/rating.py`
- 内容不变：`RATINGS_5_TIER` + `parse_rating()`
- 验证：import 成功

## T2: 移植 TradingMemoryLog
- 创建 `agents/utils/trading_memory_log.py`
- 从 upstream `agents/utils/memory.py` 复制 `TradingMemoryLog` 类
- import 路径调整：`from tradingagents.agents.utils.rating import parse_rating`
- 验证：import 成功，单元测试 store/load/get_past_context

## T3: 扩展 Reflector
- 在 `graph/reflection.py` 添加 `reflect_on_final_decision()` 方法
- 中文 prompt（与现有 prompt 风格一致）
- 验证：import 成功

## T4: AgentState + propagation 扩展
- `agent_states.py`：AgentState 添加 `past_context: Annotated[str, ...]`
- `propagation.py`：`create_initial_state()` 接受 `past_context=""` 参数，注入 state
- 验证：类型检查通过

## T5: 配置扩展
- `default_config.py` 添加 `memory_log_path`、`memory_log_max_entries`
- 添加 A 股 benchmark 映射配置

## T6: trading_graph.py 接线
- `__init__`: 创建 `self.memory_log = TradingMemoryLog(config)`
- 添加 `_resolve_benchmark()` + `_fetch_returns()`（akshare 版本）
- 添加 `_resolve_pending_entries()`
- `propagate()` 开头调用 `_resolve_pending_entries(ticker)`
- 图运行前调用 `memory_log.get_past_context(ticker)` 注入 state
- 图运行后调用 `memory_log.store_decision()`
- 验证：import 成功，类型检查通过
