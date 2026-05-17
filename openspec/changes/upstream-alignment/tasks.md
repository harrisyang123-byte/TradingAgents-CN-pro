## 1. Agent 命名对齐（原子性全局 rename）

- [x] 1.1 `agents/risk_mgmt/aggresive_debator.py`: 函数名 `create_risky_debator` → `create_aggressive_debator`，prompt 中 agent 名 `Risky Analyst` → `Aggressive Analyst`
- [x] 1.2 `agents/risk_mgmt/conservative_debator.py`: 函数名 `create_safe_debator` → `create_conservative_debator`，prompt 中 agent 名 `Safe Analyst` → `Conservative Analyst`
- [x] 1.3 `agents/managers/risk_manager.py` → 重命名为 `portfolio_manager.py`：函数名 `create_risk_judge` → `create_portfolio_manager`，agent 名 `Risk Judge` → `Portfolio Manager`
- [x] 1.4 `agents/utils/agent_states.py`: 字段 `risky_history` → `aggressive_history`, `safe_history` → `conservative_history`, `current_risky_response` → `current_aggressive_response`, `current_safe_response` → `current_conservative_response`
- [x] 1.5 `graph/setup.py`: 所有 agent 名称引用改回原版
- [x] 1.6 `graph/conditional_logic.py`: 路由目标改为 `"Portfolio Manager"`, `"Conservative Analyst"`, `"Aggressive Analyst"`
- [x] 1.7 `graph/propagation.py`: 初始 state 字段名改回原版
- [x] 1.8 `graph/trading_graph.py`: 所有 risky/safe/risk_judge 引用改回原版命名
- [x] 1.9 `agents/__init__.py`: 更新导出名称
- [x] 1.10 验证：grep 确认 codebase 中不再存在 `risky_history`, `safe_history`, `Risk Judge`, `Risky Analyst`, `Safe Analyst`

## 2. 工具架构回到独立 @tool

- [ ] 2.1 从原版移植 `agents/utils/core_stock_tools.py`（`get_stock_data`），底层改为调用 `route_to_vendor()`
- [ ] 2.2 从原版移植 `agents/utils/technical_indicators_tools.py`（`get_indicators`），底层调用 `route_to_vendor()`
- [ ] 2.3 从原版移植 `agents/utils/fundamental_data_tools.py`（`get_fundamentals` 等 4 个函数），底层调用 `route_to_vendor()`
- [ ] 2.4 从原版移植 `agents/utils/news_data_tools.py`（`get_news`, `get_global_news`），底层调用 `route_to_vendor()`；A股跳过 FinnHub/Google News（修复 #18）
- [ ] 2.5 `agents/utils/agent_utils.py`: 删除 unified 函数（`get_stock_fundamentals_unified`, `get_stock_market_data_unified` 等 ~1300 行），回到原版的 import + re-export 模式（~63 行）
- [ ] 2.6 删除 `tradingagents/tools/` 目录（`unified_news_tool.py` 等）
- [ ] 2.7 `graph/trading_graph.py`: 移植原版 `_create_tool_nodes()` 方法，替换当前的 tool binding 逻辑
- [ ] 2.8 分析师 agent（market/fundamentals/news/sentiment）更新 tool import 和 binding
- [ ] 2.9 验证：确认 `from tradingagents.tools` 无任何 import

## 3. 记忆系统对齐

- [ ] 3.1 `agents/utils/memory.py`: 替换为原版 `TradingMemoryLog` 类（flat-file markdown，~300 行），删除 ChromaDB 相关代码
- [ ] 3.2 `graph/trading_graph.py`: 删除 5 个 `FinancialSituationMemory` 实例，改用单个 `TradingMemoryLog`；memory context 仅通过 `past_context` 注入
- [ ] 3.3 `agents/managers/portfolio_manager.py`（原 risk_manager.py）: 确认 `past_context` 字段在 prompt 中正确引用
- [ ] 3.4 删除 `graph/trading_graph.py` 中的 5 个 reflect_xxx 函数（`reflect_bull_researcher` 等）
- [ ] 3.5 从 `requirements.txt` / `pyproject.toml` 移除 `chromadb` 依赖
- [ ] 3.6 验证：grep 确认 codebase 中不再 import chromadb

## 4. Provider 清理

- [ ] 4.1 `llm_adapters/dashscope_openai_adapter.py`: 删除千问 model description hack（保留基础 OpenAI compatible 功能）
- [ ] 4.2 `agents/analysts/fundamentals_analyst.py`: 删除 "通义千问/阿里百炼" 模型检测分支
- [ ] 4.3 所有分析师 agent: 删除 anti-loop、forced tool-call、tool call format fix 等 guardrail 代码
- [ ] 4.4 移植原版 `agents/utils/structured.py` 的 `invoke_structured_or_freetext()` 作为唯一 fallback
- [ ] 4.5 验证：grep 确认无 "通义千问", "anti_loop", "force_tool" 等残留

## 5. Bug 修复

- [ ] 5.1 #14 A股路由：`dataflows/interface.py` 中 `route_to_vendor()` 正确识别纯数字 A股代码
- [ ] 5.2 #15 新闻 NoneType：`dataflows/news/realtime_news.py` 在 `news_df` 为 None 时 guard
- [ ] 5.3 #17 AKShare 断连：`dataflows/` 中 AKShare 调用加指数退避重试（2s/4s/8s, max 3次）
- [ ] 5.4 #16 Embedding fallback：memory.py 已用 TradingMemoryLog 替换，此 bug 自动消除；确认无 embedding 调用残留

## 6. 端到端验证

- [ ] 6.1 类型检查通过：`mypy tradingagents/` 或 `python -c "import tradingagents"` 无 ImportError
- [ ] 6.2 单元测试通过：现有测试全部 pass
- [ ] 6.3 前端 API 兼容性：确认 web API 层无硬编码 risky/safe/risk_judge 字段
- [ ] 6.4 E2E smoke test：用 DeepSeek V4 对 A股（如 600519.SH）运行完整分析，确认无崩溃
