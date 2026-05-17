## 1. 情绪分析师重写

- [x] 1.1 重写 `tradingagents/agents/analysts/sentiment_analyst.py` — 合并 pre-fetch 数据编排 + LLM 分析为一体。`create_sentiment_analyst(llm, source_names, source_config)` 返回 graph 节点函数。节点内部：调用 source registry fetch → 格式化为 XML 分隔块注入 prompt → `prompt | llm`（无 bind_tools）→ 返回 `sentiment_report`
- [x] 1.2 删除 `tradingagents/agents/analysts/social_media_analyst.py`

## 2. 图接线更新

- [x] 2.1 修改 `tradingagents/graph/setup.py` — "social" 分析师改用 `create_sentiment_analyst(llm, source_names, source_config)`；移除独立的 "Sentiment Prefetch" 节点；移除 social 的 ToolNode 注册
- [x] 2.2 修改 `tradingagents/graph/trading_graph.py` — 移除 "social" 的 ToolNode 条目
- [x] 2.3 修改 `tradingagents/graph/conditional_logic.py` — `should_continue_social` 简化为直接返回 "Msg Clear Social"

## 3. 状态清理

- [x] 3.1 修改 `tradingagents/agents/utils/agent_states.py` — 移除 `sentiment_tool_call_count` 和 `sentiment_context` 字段
- [x] 3.2 确认无其他代码引用被移除的字段（修复了 `__init__.py` 导出）

## 4. 验证

- [x] 4.1 确认 import 链路无循环依赖，所有模块可正常 import
- [x] 4.2 确认 source registry（eastmoney/wechat_mp）未被破坏（修复了 auto-discover）
