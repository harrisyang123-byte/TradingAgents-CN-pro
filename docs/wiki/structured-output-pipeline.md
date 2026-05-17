# 结构化输出管线

> 从 TG upstream 移植并扩展的能力感知 + 结构化输出 + 自动降级体系。

## 架构概览

```
capabilities.py          ← 模型能力查表（纯数据，零外部依赖）
    ↓ get_capabilities()
openai_client.py         ← NormalizedChatOpenAI.with_structured_output() 查表选方法
    ↓
structured.py            ← bind_structured() / invoke_structured_or_freetext()
    ↓
schemas.py + agent       ← Pydantic schema + render 函数 → markdown 输出
```

## 能力感知层 (`capabilities.py`)

`ModelCapabilities` dataclass 声明每个模型的 API 级能力：

| 字段 | 含义 |
|------|------|
| `supports_tool_choice` | 是否接受 `tool_choice` 参数（DeepSeek thinking / MiniMax 不支持） |
| `supports_json_mode` | 是否支持 `response_format: json` |
| `supports_json_schema` | 是否支持 JSON Schema 约束 |
| `preferred_structured_method` | 首选结构化方法：`function_calling` / `json_mode` / `json_schema` / `none` |
| `requires_reasoning_content_roundtrip` | 是否需要 reasoning_content 回传（DeepSeek 思考模型） |

查找优先级：精确 model ID → 正则 pattern → 默认（全能力开启）。

新增模型时只需在 `_BY_ID` 或 `_BY_PATTERN` 中添加条目。

## 调用模式

Agent 工厂（creation time）：
```python
structured_llm = bind_structured(llm, MySchema, "Agent Name")
# 返回 Optional — 不支持时返回 None，不报错
```

Agent 节点（call time）：
```python
result = invoke_structured_or_freetext(
    structured_llm, llm, prompt, render_fn, "Agent Name"
)
# 1. 尝试 structured_llm.invoke(prompt) → render_fn(parsed)
# 2. 失败或 structured_llm 为 None → llm.invoke(prompt).content
```

## 降级链路

```
with_structured_output() 不支持
    → bind_structured 返回 None
        → invoke_structured_or_freetext 直接走 plain_llm

with_structured_output() 支持但运行时解析失败
    → invoke_structured_or_freetext catch Exception
        → 退回 plain_llm.invoke().content
```

两级降级确保任何模型都能产出文本结果，不会因结构化失败阻塞管线。

## 当前接入的 Agent

| Agent | Schema | 枚举 |
|-------|--------|------|
| Research Manager | `ResearchPlan` | `PortfolioRating` (Buy/Overweight/Hold/Underweight/Sell) |
| Trader | `TraderProposal` | `TraderAction` (Buy/Hold/Sell) |
| Risk Manager | `PortfolioDecision` | `PortfolioRating` |

## DeepSeek 特殊处理

`DeepSeekChatOpenAI` 子类覆盖 `_get_request_payload` 和 `_create_chat_result`，在请求/响应中回传 `reasoning_content`。仅当 `provider == "deepseek"` 时由 `OpenAIClient.get_llm()` 自动选用。
