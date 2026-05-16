## Context

CN fork 目前使用自由文本 agent 输出，通过 `Toolkit` 类的 `@tool` 方法提供工具。原版 v0.2.5 引入了 Pydantic 结构化输出模型、SqliteSaver checkpoint、情绪预抓取等能力。本设计将这些增量合并到 CN fork，不动现有 Toolkit 和 create_llm_by_provider 架构。

核心约束：新增功能不能改变已有代码的数据流路径，不能引入新的强制依赖。

## Goals / Non-Goals

**Goals:**
- 新增 `schemas.py` 定义 ResearchPlan/TraderProposal/PortfolioDecision，纯 Pydantic 模型
- 新增 `structured.py` 提供结构化输出绑定和 LLM 不支持时的降级
- 新增 `rating.py` 提供确定性评级解析
- 新增 `checkpointer.py` 提供 SqliteSaver 封装（默认关闭）
- 新增 `sentiment_analyst.py` + `sources/` 注册式情绪预抓取
- `default_config.py` 追加不冲突的配置字段
- `graph/setup.py` wire 情绪预抓取到 graph 入口

**Non-Goals:**
- 不拆分 `agent_utils.py` 的 Toolkit 类
- 不改 `graph/trading_graph.py` 的 create_llm_by_provider 逻辑
- 不改 `graph/signal_processing.py` 的富输出格式
- 不改 `graph/reflection.py` 的 ChromaDB 记忆系统
- 不改现有 agent 的 system prompt（除非需要接入结构化输出）

## Decisions

### 1. 结构化输出：monkey-patch 式接入已有的 agent

**决策**：不在 agent 的 `__init__` 或 system prompt 中强制绑定 schema，而是在 `graph/setup.py` 中按条件注入。

**理由**：
- LLM 可能不支持 structured output（如某些中文模型）
- 不修改现有 agent 的构造函数签名
- 降级路径清晰：supported → bind_structured，unsupported → invoke_structured_or_freetext

**方案**：
```python
# graph/setup.py 中的可选注入
if has_structured_output(llm):
    trader = create_trader_with_structured(llm, toolkit, schemas.TraderProposal)
else:
    trader = create_trader(llm, toolkit)  # 原样
```

### 2. 情绪源注册表：类装饰器 + 基类

**决策**：用类装饰器 `@register` + 抽象基类 `BaseSentimentSource`。

**理由**：
- 新增源只需 `from .xueqiu import XueqiuSource` 传入注册表即可
- 不需要修改 sentiment_analyst.py
- 每个源独立文件，便于维护和测试

**接口**：
```python
class BaseSentimentSource(ABC):
    name: str
    async def fetch(self, tickers: list[str]) -> dict[str, SentimentData]: ...

REGISTRY: dict[str, type[BaseSentimentSource]] = {}

def register(name: str):
    def wrapper(cls):
        REGISTRY[name] = cls
        return cls
    return wrapper
```

### 3. Checkpoint：SqliteSaver 封装，默认关闭

**决策**：SqliteSaver 实例化放在 `graph/setup.py` 的条件分支中，不侵入 graph compile 主路径。

**理由**：
- 现有 CN fork 不依赖 checkpoint
- SqliteSaver 是 langgraph 内置能力，无新增依赖
- 文件存储路径 `./checkpoints/` 已加入 `.gitignore`

### 4. 情绪数据注入：文本格式嵌入 agent state

**决策**：预抓取情绪聚合为纯文本报告，写入 `agent_state.sentiment_context` 字段。

**理由**：
- 不需要修改现有 agent 的 tool-call 逻辑
- 文本格式兼容所有 LLM
- agent 可以在 system prompt 中引用该字段（已存在 context 传递机制）

### 5. 东方财富源：复用 akshare

**决策**：直接使用 CN fork 已有的 `akshare` 获取东方财富新闻数据。

**理由**：
- 已安装，零新增依赖
- 支持 A 股全覆盖
- 港股直接跳过（akshare 不覆盖港股新闻）

### 6. 微信源：HTTP 客户端调用 we-mp-rss

**决策**：使用 httpx 异步 HTTP 请求 we-mp-rss Docker 服务 API。

**理由**：
- 已有 Docker 服务运行在 localhost:8001
- 无需额外 SDK
- `wechat_mp_base_url` 可配置，地址变更不需要改代码

## Risks / Trade-offs

| Risk | Mitigation |
|------|-----------|
| we-mp-rss 服务不稳定 | 5s 超时 + 静默跳过 + warn 日志，不阻塞主线 |
| 东方财富 API 限频 | 每请求间隔 0.5s，akshare 内置重试 |
| 结构化输出导致 LLM 额外 token 消耗 | 仅在 LLM 支持时启用，降级路径不增加消耗 |
| checkpoint 文件积累 | 建议用户定期清理 `.checkpoints/` |
| 新字段污染已有数据流 | 所有新字段都有默认值，不影响现有序列化 |
