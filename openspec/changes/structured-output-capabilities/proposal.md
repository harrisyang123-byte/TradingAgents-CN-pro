## Why

TG-CN 的三个决策 agent（risk_manager、research_manager、trader）全部使用原始 `llm.invoke()` + 手动文本解析。`structured.py` 虽存在但零调用。换模型时如果该模型不支持 `tool_choice`（如 DeepSeek V4），结构化输出会直接报错。TG upstream 已有完整的能力感知 + 结构化输出 + 降级链路。

## What Changes

**新增**

- `tradingagents/llm_clients/capabilities.py` — 模型能力查表（从 upstream 移植，增加中文模型条目）

**修改**

- `tradingagents/llm_clients/openai_client.py` — `NormalizedChatOpenAI` 增加 `with_structured_output()` 重写，查能力表自动适配；增加 `DeepSeekChatOpenAI` 子类处理 reasoning_content 回传
- `tradingagents/agents/utils/structured.py` — 对齐 upstream 签名：`bind_structured(llm, schema, agent_name)` 返回 Optional；`invoke_structured_or_freetext(structured_llm, plain_llm, prompt, render, agent_name)`
- `tradingagents/agents/schemas.py` — 对齐 upstream 的 schema 设计：`PortfolioRating` 枚举、`TraderAction` 枚举、render 函数独立于类外
- `tradingagents/agents/managers/risk_manager.py` — 接入结构化管线（bind_structured + invoke_structured_or_freetext），移除手动重试循环
- `tradingagents/agents/managers/research_manager.py` — 接入结构化管线
- `tradingagents/agents/trader/trader.py` — 接入结构化管线

## Impact

- `llm_clients/` — 新增文件 + 修改 1 个文件，不影响现有 provider 配置
- `agents/` — 三个 agent 的输出从自由文本变为结构化 schema + markdown render，降级时仍返回自由文本
- 现有 `llm_adapters/` 不受影响（Web 端适配器层独立于 `llm_clients/`）
- 现有中文 prompt 内容保留，仅包装进结构化调用

**复杂度**: 中等
