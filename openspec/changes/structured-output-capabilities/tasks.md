## 1. 底层能力感知

- [x] 1.1 新增 `tradingagents/llm_clients/capabilities.py` — 从 upstream 移植 `ModelCapabilities` + `get_capabilities()`，增加中文模型条目（qwen、glm、qianfan 系列）
- [x] 1.2 修改 `tradingagents/llm_clients/openai_client.py` — `NormalizedChatOpenAI` 增加 `with_structured_output()` 重写（查能力表选方法、抑制 tool_choice）；增加 `DeepSeekChatOpenAI` 子类（reasoning_content 回传）；`OpenAIClient.get_llm()` 按 provider 选子类

## 2. 结构化输出管线

- [x] 2.1 升级 `tradingagents/agents/utils/structured.py` — 对齐 upstream 签名和降级逻辑
- [x] 2.2 升级 `tradingagents/agents/schemas.py` — 增加 `PortfolioRating`/`TraderAction` 枚举 + render 函数，保留 TG-CN 现有 schema 备用

## 3. Agent 接入

- [ ] 3.1 修改 `tradingagents/agents/managers/research_manager.py` — 使用 `bind_structured` + `invoke_structured_or_freetext`，保留中文 prompt
- [ ] 3.2 修改 `tradingagents/agents/trader/trader.py` — 同上
- [ ] 3.3 修改 `tradingagents/agents/managers/risk_manager.py` — 同上，移除手动 3 次重试（由 structured pipeline 的降级覆盖）

## 4. 验证

- [ ] 4.1 确认 `import` 链路无循环依赖，`python -c "from tradingagents.llm_clients.capabilities import get_capabilities; print('OK')"` 通过
- [ ] 4.2 确认三个 agent 模块可正常 import
