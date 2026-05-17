# P3 长尾能力 — 任务清单

## Task 1: xAI/Grok Provider + Responses API (#13)
- [ ] `factory.py`: 添加 `"xai"` 到 `_OPENAI_COMPATIBLE`
- [ ] `openai_client.py`: 添加 `"xai"` 到 `_PROVIDER_CONFIG`，base_url `https://api.x.ai/v1`
- [ ] `provider_keys.py`: 添加 `"xai"` 别名 + `XAI_API_KEY` 环境变量映射 + default_backend_url
- [ ] `openai_client.py`: 为原生 OpenAI 添加 `use_responses_api=True`
- [ ] `openai_client.py`: 添加 `"reasoning_effort"` 到 `_PASSTHROUGH_KWARGS`

## Task 2: Vendor-Routing 适配 (#14)
- [ ] `dataflows/interface.py`: 添加 Alpha Vantage fallback 导入 + 路由入口函数
- [ ] `upstream-gap-analysis.md`: 标记 #14 为"已适配（TG-CN 等效架构）"

## Task 3: Benchmark Alpha 显式覆盖 (#15)
- [ ] `default_config.py`: 添加 `benchmark_ticker: None` 配置键
- [ ] `trading_graph.py`: `_resolve_benchmark()` 优先检查 `benchmark_ticker`
- [ ] `upstream-gap-analysis.md`: 标记 #15 完成

## Task 4: Dynamic MessageBuffer (#16)
- [ ] `cli/main.py`: 添加 FIXED_AGENTS, ANALYST_MAPPING, REPORT_SECTIONS 类常量
- [ ] `cli/main.py`: 实现 `init_for_analysis(selected_analysts)`
- [ ] `cli/main.py`: 实现 `get_completed_reports_count()`
- [ ] `cli/main.py`: 添加 `_processed_message_ids` 去重
- [ ] `cli/main.py`: `update_display()` 中 teams dict 改为从 `agent_status` 动态构建
- [ ] `upstream-gap-analysis.md`: 标记 #16 完成
