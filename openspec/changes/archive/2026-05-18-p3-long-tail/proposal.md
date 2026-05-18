# P3 长尾能力吸收 (#13-16)

**日期**: 2026-05-17
**批次**: Batch 4

## 目标

吸收 TG upstream 剩余 4 项长尾能力，完成 upstream 差距分析全部 16 项。

## 变更范围

### #13 xAI/Grok Provider + Responses API
- 将 xAI 从"仅目录"提升为完整可用 provider
- 为原生 OpenAI 启用 Responses API (`use_responses_api=True`)
- 添加 `reasoning_effort` 透传参数

### #14 Vendor-Routing 架构（适配方案）
- TG-CN 已有 DB 驱动的 `data_source_manager.py`，不照搬 upstream 的 `route_to_vendor()`
- 在现有 interface.py 中添加 Alpha Vantage fallback 路由入口
- 标记此项为"架构等效，已适配"

### #15 Benchmark Alpha 显式覆盖
- 添加 `benchmark_ticker` 配置键（显式覆盖优先于后缀匹配）
- 添加 `TRADINGAGENTS_BENCHMARK_TICKER` 环境变量支持

### #16 Dynamic MessageBuffer.init_for_analysis
- 添加类级映射常量 (FIXED_AGENTS, ANALYST_MAPPING, REPORT_SECTIONS)
- 实现 `init_for_analysis(selected_analysts)` 动态初始化
- 实现 `get_completed_reports_count()` 双条件完成检测
- 添加消息去重 (`_processed_message_ids`)

## 影响分析

- **无破坏性变更**：所有改动都是增量添加或向后兼容的重构
- **CLI 行为变化**：MessageBuffer 从静态变为动态，但未选 `init_for_analysis` 时行为不变
