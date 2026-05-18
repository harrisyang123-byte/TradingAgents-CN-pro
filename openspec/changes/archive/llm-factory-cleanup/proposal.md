# 变更提案：LLM 工厂清理 (P1 #5)

**变更 ID**: llm-factory-cleanup
**优先级**: P1 #5
**状态**: 待实现

## 背景

`trading_graph.py` 的 `__init__` 包含 ~310 行 if/elif 分支来初始化 LLM。
每个分支做几乎相同的事：解析 API key → 解析 backend_url → 调用 `_create_provider_pair`。
差异仅在 API key 来源和少量 provider-specific 参数。

## 变更范围

将 ~310 行 if/elif 压缩为 ~40 行：

1. 提取 `_resolve_api_key(provider)` — config `quick_api_key/deep_api_key` → `env_key_for_provider()`
2. 提取 `_resolve_backend_url(provider)` — config `backend_url` → `default_backend_url()`
3. 保留三个分支：mixed-mode / anthropic / 统一路径
4. 删除所有 per-provider 日志（统一为一行初始化日志）

## 不变更
- `create_llm_by_provider()` 和 `_create_provider_pair()` 保持不变
- 所有 provider 功能保持不变
- Web UI 的 config 传入方式不变
