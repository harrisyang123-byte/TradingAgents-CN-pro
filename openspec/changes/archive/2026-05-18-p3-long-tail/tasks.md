# P3 长尾能力 — 任务清单

## Task 1: xAI/Grok Provider + Responses API (#13)
- [x] `factory.py`: 添加 `"xai"` 到 `_OPENAI_COMPATIBLE`
- [x] `openai_client.py`: 添加 `"xai"` 到 `_PROVIDER_CONFIG`，base_url `https://api.x.ai/v1`
- [x] `provider_keys.py`: 添加 `"xai"` 别名 + `XAI_API_KEY` 环境变量映射 + default_backend_url
- [x] `openai_client.py`: 为原生 OpenAI 添加 `use_responses_api=True`
- [x] `openai_client.py`: 添加 `"reasoning_effort"` 到 `_PASSTHROUGH_KWARGS`

## Task 2: Vendor-Routing 适配 (#14)
- [x] `dataflows/interface.py`: Alpha Vantage fallback 已有（TG-CN 等效架构 data_source_manager.py）
- [x] `upstream-gap-analysis.md`: 标记 #14 为"已适配（TG-CN 等效架构）"

## Task 3: Benchmark Alpha 显式覆盖 (#15)
- [x] `default_config.py`: 添加 `benchmark_ticker: None` 配置键
- [x] `trading_graph.py`: `_resolve_benchmark()` 优先检查 `benchmark_ticker`
- [x] `upstream-gap-analysis.md`: 标记 #15 完成

## Task 4: Dynamic MessageBuffer (#16)
- [x] `cli/main.py`: 添加 FIXED_AGENTS, ANALYST_MAPPING, REPORT_SECTIONS 类常量
- [x] `cli/main.py`: 实现 `init_for_analysis(selected_analysts)`
- [x] `cli/main.py`: 实现 `get_completed_reports_count()`
- [x] `cli/main.py`: 添加 `_processed_message_ids` 去重
- [x] `cli/main.py`: `update_display()` 中 teams dict 改为从 `agent_status` 动态构建
- [x] `upstream-gap-analysis.md`: 标记 #16 完成
