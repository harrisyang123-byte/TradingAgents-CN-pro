# Tasks: p2-extensions

## T1: Azure OpenAI 客户端 (#9)
- 创建 `llm_clients/azure_client.py`
- 注册到 `factory.py`
- 添加 `provider_keys.py` 条目

## T2: 模型目录更新 (#10)
- 更新 `model_catalog.py` — OpenAI/Anthropic/Google/DeepSeek/Qwen/GLM 到最新
- 更新 `capabilities.py` — 补充新模型条目

## T3: CLI token 统计 (#12)
- 创建 `cli/stats_handler.py`（或 `tradingagents/utils/stats_handler.py`）
- 在 `trading_graph.py` 中可选注入 callbacks

## T4: 测试 conftest fixtures (#11)
- 创建/更新 `tests/conftest.py` — dummy API keys + mock_llm_client
- 添加 pytest markers

## T5: Alpha Vantage 数据源 (#8)
- 移植 `dataflows/alpha_vantage*.py` 5 个文件
- 注册到 interface.py 工具列表（可选）
