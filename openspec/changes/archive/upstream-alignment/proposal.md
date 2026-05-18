## Why

TG-CN 本应是"原版 TradingAgents 分析引擎 + 中文数据源 + 中文前端"，但实际偏离严重：Agent 命名被改、工具架构重写为 unified 模式、记忆系统从 flat-file 换成 ChromaDB、加入大量千问(Qwen)专属 workaround 和反幻觉 guardrail。端到端对比显示 TG-CN 的 `agent_utils.py` 膨胀到 1379 行（原版 63 行），`trading_graph.py` 膨胀到 1078 行（原版 427 行）。用户使用 DeepSeek，千问 workaround 完全无用。

## What Changes

- **BREAKING** 删除 `tradingagents/tools/` 目录（unified 工具），回到原版 `agents/utils/` 下的独立 `@tool` 函数
- **BREAKING** Agent 命名回到原版：Risky→Aggressive、Safe→Conservative、Risk Judge→Portfolio Manager；相关 state 字段同步改回（`risky_history`→`aggressive_history` 等）
- **BREAKING** 记忆系统从 ChromaDB 5-agent 注入回到 flat-file `TradingMemoryLog` + PM-only 注入
- 删除 `llm_adapters/dashscope_openai_adapter.py` 中的千问专属 workaround
- 删除分析师中的反幻觉/反循环 guardrail，改用原版 `invoke_structured_or_freetext()` fallback
- 修复 5 个已知 bug（#14 A股路由、#15 新闻 NoneType、#16 embedding fallback、#17 AKShare 断连、#18 A股调用外国源）
- 保留中文情绪源（东方财富、微信公众号）和 AKShare 数据层
- 保留前端不动

## Capabilities

### New Capabilities

- `tool-architecture-alignment`: 回到原版独立 @tool 函数架构，删除 unified tool 层
- `agent-naming-alignment`: Agent/State 命名回到原版（Aggressive/Conservative/Portfolio Manager）
- `memory-system-alignment`: 记忆系统回到原版 flat-file TradingMemoryLog + PM-only 注入
- `provider-cleanup`: 删除千问 workaround 和反幻觉 guardrail，所有 provider 走统一路径
- `data-bugfixes`: 修复 A股路由、新闻 NoneType、embedding fallback、AKShare 断连、外国源调用

### Modified Capabilities

(无已有 spec)

## Impact

- **代码**: `tradingagents/` 下 ~20 文件受影响，`tools/` 目录删除
- **依赖**: 移除 ChromaDB（`chromadb` 包），回到 flat-file
- **API**: 前端调用的 `propagate()` 接口不变，但内部 state 字段名变化
- **数据**: AKShare 数据流保留，yfinance 仅用于港股/美股
- **前端**: 不受影响（通过 API 层隔离）
