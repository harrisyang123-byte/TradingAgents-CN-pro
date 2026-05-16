# P0 核心集成：结构化输出 + Checkpoint + 情绪预抓取

## 概述

将原版 TradingAgents v0.2.5 的三大核心能力增量合入 CN fork（v1.0.1），不动现有 Toolkit 和 create_llm_by_provider 架构。

## 新增文件清单

| 文件 | 用途 |
|------|------|
| `tradingagents/agents/schemas.py` | Pydantic 结构化输出模型 |
| `tradingagents/agents/utils/structured.py` | 结构化输出绑定及降级回退 |
| `tradingagents/agents/utils/rating.py` | 5 档评级确定性解析器 |
| `tradingagents/graph/checkpointer.py` | SqliteSaver 每 ticker 断点恢复 |
| `tradingagents/agents/analysts/sentiment_analyst.py` | 情绪预抓取编排 |
| `tradingagents/agents/analysts/sources/__init__.py` | 注册式情绪源框架 |

## 架构决策

### 结构化输出 — monkey-patch 式接入
不在 agent 构造函数中强制绑定 schema，而是在 `graph/setup.py` 按条件注入。LLM 不支持时自动降级到自由文本。

### 情绪源注册表 — `@register` 装饰器 + `BaseSentimentSource` ABC
新增源只需注册即可，无需修改编排代码。当前内置源：
- `eastmoney` — 基于 akshare，仅 A 股
- `wechat_mp` — 基于 we-mp-rss Docker 服务

### Checkpoint — SqliteSaver，默认关闭
通过 `checkpoint_enabled` 配置控制，不侵入 graph compile 主路径。

### `_run_async()` 跨上下文兼容
`graph/setup.py` 的 `_run_async()` helper 同时支持 sync（CLI）和 async（FastAPI）调用上下文，避免 `asyncio.run()` 在事件循环已运行时崩溃。

## 配置字段

在 `default_config.py` 中追加：

- `checkpoint_enabled: bool` — 默认 False
- `checkpoint_dir: str` — 默认 ".checkpoints"
- `output_language: str` — 默认 "Chinese"
- `sentiment_sources: list[str]` — 默认 ["eastmoney", "wechat_mp"]
- `wechat_mp_base_url: str` — 默认 "http://localhost:8001"

## 相关 spec
- openspec/changes/p0-core-integration/specs/structured-output/spec.md
- openspec/changes/p0-core-integration/specs/checkpoint-resume/spec.md
- openspec/changes/p0-core-integration/specs/sentiment-prefetch/spec.md
