# Tasks: llm-factory-cleanup

## T1: 添加 _resolve_api_key 和 _resolve_backend_url 方法
- 在 TradingAgentsGraph 类中添加两个私有方法
- `_resolve_api_key`: config → env_key_for_provider
- `_resolve_backend_url`: config → default_backend_url (with deepseek special case)

## T2: 替换 __init__ LLM 初始化块
- 删除 lines 244-531 的 if/elif 链
- 替换为三分支结构：mixed-mode / anthropic / 统一路径
- 统一路径使用 _resolve_api_key + _resolve_backend_url + _create_provider_pair
- 保留 google 的 transport=rest extra kwarg

## T3: 验证
- import 成功
- 所有 provider 路径可用
