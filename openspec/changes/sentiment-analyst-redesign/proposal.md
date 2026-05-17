## Why

TG-CN 的情绪分析存在两套互不连通的系统：

1. **pre-fetch 框架** (`sentiment_analyst.py`) — 有真实中文数据源（eastmoney/wechat_mp），但输出写入 `sentiment_context`，下游无人读取
2. **tool-calling 分析师** (`social_media_analyst.py`) — 在图中作为 "Social Analyst" 节点运行，但 `get_stock_sentiment_unified` 对 CN/HK 市场返回占位符模板

结果：A 股/港股分析跑出来的情绪报告要么是占位符，要么是 LLM 编造的内容。此外 tool-calling 模式引入了大量复杂性（死循环修复、Google 模型特殊处理、ToolNode 注册），upstream 已验证 pre-fetch 模式更可靠。

## What Changes

**核心思路**：合并两套系统为一套 pre-fetch 模式的情绪分析师，复用现有中文数据源框架。

**重写**

- `tradingagents/agents/analysts/sentiment_analyst.py` — 从纯数据编排器升级为完整的 pre-fetch + LLM 分析师。pre-fetch 阶段调用已有的 source registry（eastmoney/wechat_mp），将数据注入 prompt，单次 LLM 调用生成报告。不再使用 `bind_tools()`

**修改**

- `tradingagents/graph/setup.py` — "social" 分析师改用新的 `create_sentiment_analyst(llm, source_names)`，移除 ToolNode 注册和独立的 "Sentiment Prefetch" 节点
- `tradingagents/graph/conditional_logic.py` — `should_continue_social` 简化为直接路由到 "Msg Clear Social"（无 tool-calling 循环）
- `tradingagents/graph/trading_graph.py` — 移除 "social" 的 ToolNode 注册
- `tradingagents/agents/utils/agent_states.py` — 移除 `sentiment_tool_call_count`，保留 `sentiment_report`，移除 `sentiment_context`（合并进新流程）

**删除**

- `tradingagents/agents/analysts/social_media_analyst.py` — 被新 `sentiment_analyst.py` 完全取代

**不动**

- `tradingagents/agents/analysts/sources/` — eastmoney.py、wechat_mp.py、registry 框架原封不动复用
- 其他三个 tool-calling 分析师（market、news、fundamentals）不受影响

## Impact

- 图结构简化：social 路径从 analyst → conditional → ToolNode → analyst 循环变为 analyst → Msg Clear 直通
- A 股/港股情绪分析从占位符升级为真实数据驱动
- 移除 ~230 行 social_media_analyst.py（tool-calling + Google 特殊处理 + 死循环修复）
- 移除 conditional_logic.py 中 ~40 行死循环检测代码

**复杂度**: 中等
