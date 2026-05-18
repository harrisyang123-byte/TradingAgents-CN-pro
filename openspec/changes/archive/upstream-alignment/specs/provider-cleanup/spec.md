## ADDED Requirements

### Requirement: 统一 Provider 路径
所有 LLM provider SHALL 走统一的工厂路径（`llm_clients/factory.py`），不存在 provider 专属 workaround。

#### Scenario: DeepSeek 走统一路径
- **WHEN** 配置 `llm_provider: deepseek`
- **THEN** 通过 `create_llm_client()` 工厂创建，无专属分支

#### Scenario: 千问走统一路径
- **WHEN** 配置 `llm_provider: qwen`
- **THEN** 通过 `create_llm_client()` 工厂创建，无专属 adapter 或 model description hack

### Requirement: 删除千问 workaround
系统 SHALL NOT 包含千问(Qwen)专属的 workaround 代码。

#### Scenario: 无千问模型检测
- **WHEN** 分析师 agent 初始化
- **THEN** 不存在 "通义千问" 或 "阿里百炼" 模型检测分支

#### Scenario: 无千问 adapter hack
- **WHEN** LLM adapter 初始化
- **THEN** `dashscope_openai_adapter.py` 中不包含千问 model description 特殊处理

### Requirement: 统一 structured output fallback
系统 SHALL 使用原版的 `invoke_structured_or_freetext()` 作为唯一的 structured output fallback 策略。

#### Scenario: Structured output 失败
- **WHEN** LLM 的 structured output 调用失败
- **THEN** 自动降级为 free text 重试，不触发 anti-loop 或 forced tool-call 逻辑

### Requirement: 删除反幻觉 guardrail
分析师 agent SHALL NOT 包含 anti-hallucination、anti-loop、forced tool-call 等 guardrail 代码。

#### Scenario: 分析师无反幻觉代码
- **WHEN** 检查分析师 agent 代码
- **THEN** 不存在 loop 检测、强制 tool call、tool call 格式修补等逻辑
