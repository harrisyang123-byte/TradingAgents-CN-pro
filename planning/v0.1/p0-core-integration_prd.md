# P0 核心集成 — PRD

> 将原版 TradingAgents v0.2.5 的核心 agent 特性增量合并到 CN fork v1.0.1

---

## Objective（目标）

**业务目标**：把原版迭代的结构化输出、checkpoint 恢复、情绪预抓取等能力补回 CN fork，同时保持 CN fork 已有的 A 股数据层和中文友好架构不动。

**成功标准**：
1. CLI 能跑通 A 股全流程分析
2. Docker Web 前端正常使用
3. 新增功能不影响已有数据流

**不做的**：
- Toolkit 拆分重构（保持 CN fork 现有结构）
- 美股数据源合并（Alpha Vantage, yfinance 等跳过）
- CN fork 已有功能重写（create_llm_by_provider, 反循环守卫等保留）

---

## Architecture（架构）

### 变更总览

```
tradingagents/
├── agents/
│   ├── schemas.py                    [新增]  Pydantic 结构化输出模型
│   └── utils/
│       ├── structured.py             [新增]  结构化输出绑定/退化回退
│       └── rating.py                 [新增]  5 档评级解析器
├── analysts/
│   ├── sentiment_analyst.py          [新增]  情绪分析预抓取框架
│   └── sources/                      [新增]  情绪数据源注册目录
│       ├── __init__.py               [新增]  注册表
│       ├── eastmoney.py              [新增]  东方财富情绪数据
│       └── wechat_mp.py              [新增]  微信公众号情绪数据
├── graph/
│   ├── checkpointer.py               [新增]  SqliteSaver checkpoint/resume
│   └── setup.py                      [修改]  接入预抓取情绪到 graph 入口
├── default_config.py                 [修改]  追加 checkpoint、output_language 字段
└── llm_clients/
    └── model_catalog.py              [修改]  已加 deepseek-v4 模型（完成）
```

### 状态流

```
用户输入 → pre-fetch 情绪(sentiment_sources) → Research Team → Trader → Risk → PM → 输出
                                                  ↑
                                          结构化输出(schemas + rating)
                                                  ↑
                                          checkpoint 每 ticker 持久化
```

### 依赖关系

| 文件 | 依赖 | 说明 |
|------|------|------|
| schemas.py | 无 | 纯 Pydantic 模型，零依赖 |
| structured.py | schemas.py | 工具函数依赖模型 |
| rating.py | 无 | 纯字符串解析 |
| checkpointer.py | langgraph | SqliteSaver |
| sentiment_analyst.py | sources/*, httpx | 遍历注册表拉取 |
| sources/eastmoney.py | httpx, akshare | 东方财富 API |
| sources/wechat_mp.py | httpx | we-mp-rss Docker API |

---

## Interface（接口）

### 新增配置字段（default_config）

```python
# 原 CN fork 已有字段保留不动，追加以下：
checkpoint_enabled: bool = False       # 关闭不影响现有行为
output_language: str = "Chinese"        # 控制 agent 输出语言
sentiment_sources: list[str] = ["eastmoney", "wechat_mp"]  # 启用的情绪源
wechat_mp_base_url: str = "http://localhost:8001"  # we-mp-rss 服务地址
```

### 结构化输出模型（schemas.py）

```python
class ResearchPlan(BaseModel):
    """研究计划 — research_manager 输出，指导分析师工作"""
    plan_type: Literal["deep_dive", "catalyst", "earnings", "technical"]
    tickers: list[str]
    focus_areas: list[str]
    timeline: str

class TraderProposal(BaseModel):
    """交易提案 — trader 输出"""
    ticker: str
    direction: Literal["long", "short", "neutral"]
    confidence: int  # 1-100
    reasoning: str
    risk_factors: list[str]

class PortfolioDecision(BaseModel):
    """投资组合决策 — PM 最终输出"""
    decisions: list[SingleDecision]
    allocation_summary: str

class SingleDecision(BaseModel):
    ticker: str
    action: Literal["buy", "sell", "hold", "increase", "reduce"]
    rationale: str
```

### 情绪源注册表（sources/__init__.py）

```python
REGISTRY: dict[str, type[BaseSentimentSource]] = {}

def register(name: str):
    """装饰器：注册情绪源"""

def get_enabled_sources(names: list[str]) -> list[BaseSentimentSource]:
    """按名称列表获取已启用的源实例"""
```

每个源实现：
```python
class BaseSentimentSource(ABC):
    name: str
    async def fetch(self, tickers: list[str]) -> dict[str, SentimentData]: ...
```

### Checkpoint

```python
# 调用方式
checkpointer = create_checkpointer()  # SqliteSaver(db_path=".checkpoints/trading.db")
app = graph.compile(checkpointer=checkpointer)
# 恢复方式
thread_config = {"configurable": {"thread_id": ticker}}
state = app.get_state(thread_config)
```

---

## Scenarios（场景）

### 场景 1：CLI 跑通 A 股全流程

```
WHEN  用户运行 python cli/run.py --tickers 000001.SZ,600519.SH
THEN  情绪预抓取先拉东方财富 + 微信公众号数据
THEN  agent 管线正常执行
THEN  输出包含结构化决策结果
AND   不报错，不卡死
```

### 场景 2：Checkpoint 断点续跑

```
GIVEN checkpoint_enabled = True
WHEN  分析过程中 Ctrl+C 中断
THEN  在 .checkpoints/ 目录保存当前进度
WHEN  重新运行相同 ticker
THEN  从断点恢复，而不是从头跑
```

### 场景 3：情绪源注册扩展

```
GIVEN P1 新增自定义源 class XueqiuSource(BaseSentimentSource)
WHEN  在 sources/__init__.py 中注册
THEN  配置 sentiment_sources 追加 "xueqiu" 即可启用
AND   无需修改 sentiment_analyst.py
```

### 场景 4：结构化输出退化（LLM 不支持时）

```
GIVEN LLM 不支持 tool_use 或 structured output
WHEN  trader 尝试输出 TraderProposal
THEN  降级为自由文本（fallback 逻辑在 structured.py）
AND   下游 PM 仍能正常处理
```

### 场景 5：Docker Web 前端不受影响

```
WHEN  后端启动（uvicorn app.main:app）
THEN  新增模型不影响 FastAPI 注册
AND   前端 API 调用不变
AND   所有 /api/ 端点正常响应
```

---

## 边界与异常

| 异常 | 处理 |
|------|------|
| we-mp-rss 服务不可达 | 静默跳过，日志 warn，不影响主线 |
| 东方财富 API 限流 | httpx 超时 (5s) + 重试 1 次 |
| LLM 不支持结构化输出 | `invoke_structured_or_freetext` 自动降级 |
| checkpoint 文件损坏 | 删掉 .checkpoint 文件，从头运行 |
| 情绪源全部不可用 | 返回空报告，主线继续 |

---

## 不做但需注意的

- `graph/trading_graph.py` 不改——CN fork 的 `create_llm_by_provider` 逻辑保留，不合并原版的 `_resolve_benchmark` / `_fetch_returns`（P2 组合管理时再考虑）
- `graph/signal_processing.py` 不改——CN fork 的富输出保留，`rating.py` 作为独立函数存在
- `graph/reflection.py` 不改——CN fork 的 ChromaDB 记忆系统保留
