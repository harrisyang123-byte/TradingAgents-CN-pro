## Why

CN fork v1.0.1 基于原版 TradingAgents v0.2.0 开发，原版后续迭代到 v0.2.5 增加了结构化输出、checkpoint 断点恢复、情绪预抓取等核心能力。这些是 agent 系统的关键基础设施，CN fork 缺失导致交易分析质量、稳定性和效率受限。同时，情绪分析功能目前完全空白，需要填补。

## What Changes

- **新增** `agents/schemas.py` — Pydantic 结构化输出模型（ResearchPlan, TraderProposal, PortfolioDecision）
- **新增** `agents/utils/structured.py` — 结构化输出绑定及降级回退（LLM 不支持时自动切换自由文本）
- **新增** `agents/utils/rating.py` — 5 档评级解析器（Buy/Overweight/Hold/Underweight/Sell）
- **新增** `graph/checkpointer.py` — SqliteSaver 每 ticker 断点恢复
- **新增** `analysts/sentiment_analyst.py` — 情绪预抓取框架，在主线 agent 前批量拉取情绪数据
- **新增** `analysts/sources/` — 注册式情绪源目录
- **新增** `analysts/sources/__init__.py` — 情绪源注册表
- **新增** `analysts/sources/eastmoney.py` — 东方财富情绪数据（基于 akshare）
- **新增** `analysts/sources/wechat_mp.py` — 微信公众号情绪数据（基于 we-mp-rss）
- **修改** `default_config.py` — 追加 checkpoint_enabled、output_language、sentiment_sources 字段
- **修改** `graph/setup.py` — 将情绪预抓取接入 graph 管线入口

## Capabilities

### New Capabilities
- `structured-output`: Agent 结构化输出模型、绑定工具及评级解析，提升输出一致性和下游可消费性
- `checkpoint-resume`: SqliteSaver 断点续跑，LLM 超时或中断后从断点恢复
- `sentiment-prefetch`: 情绪预抓取框架及注册式数据源系统，支持多源聚合情绪报告

### Modified Capabilities
（无已有 spec 需要修改）

## Impact

- `tradingagents/agents/schemas.py` — 新增，无副作用
- `tradingagents/agents/utils/structured.py` — 新增，工具函数
- `tradingagents/agents/utils/rating.py` — 新增，纯函数
- `tradingagents/graph/checkpointer.py` — 新增，默认不启用
- `tradingagents/analysts/sentiment_analyst.py` — 新增，不在主线 agent tool-call 路径上
- `tradingagents/analysts/sources/` — 新增目录
- `tradingagents/default_config.py` — 修改，追加字段不影响默认行为
- `tradingagents/graph/setup.py` — 修改，新增情绪注入节点
