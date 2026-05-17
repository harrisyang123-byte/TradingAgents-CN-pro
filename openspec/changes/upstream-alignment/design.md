## Context

TG-CN fork 了 TradingAgents v0.2.5 后大幅重写：unified tool 架构、Agent 重命名、ChromaDB 记忆、千问 workaround。现在用户要收敛回"原版引擎 + 中文数据/前端"。

原版代码参考：`/private/tmp/TradingAgents-upstream/tradingagents/`
TG-CN 代码：`/Users/yangyanyu/AI-Coding-Engine/domains/tradingagents-cn/tradingagents/`

关键数据对比：
| 文件 | 原版行数 | TG-CN 行数 | 膨胀比 |
|------|---------|-----------|--------|
| agent_utils.py | 63 | 1379 | 22x |
| trading_graph.py | 427 | 1078 | 2.5x |
| setup.py | 186 | 290 | 1.6x |
| memory.py | 300 | 701 | 2.3x |

## Goals / Non-Goals

**Goals:**
- TG-CN 的分析引擎与原版 v0.2.5 架构一致
- 保留中文数据源（AKShare、东方财富情绪）和中文前端
- 修复 5 个已知 bug
- DeepSeek/OpenAI 等 provider 走统一路径，无专属 workaround

**Non-Goals:**
- 不改前端（Vue/Streamlit）
- 不改 `llm_clients/` 工厂层（已经是干净架构）
- 不迁移到原版的 yfinance 数据流（A股数据需要 AKShare）
- 不删除 `dataflows/` 目录（中文数据层是 TG-CN 核心价值）

## Decisions

### D1: 工具架构 — 回到独立 @tool 函数

**选择**: 删除 `tradingagents/tools/` 目录和 `agent_utils.py` 中的 unified 函数，从原版移植独立 tool 函数。

**替代方案**: 保留 unified 架构但简化 → 拒绝，因为 unified 架构是千问 workaround 的主要载体，且增加了 1300+ 行不必要代码。

**实施**:
- 移植原版 `agents/utils/core_stock_tools.py` — `get_stock_data`
- 移植原版 `agents/utils/technical_indicators_tools.py` — `get_indicators`
- 移植原版 `agents/utils/fundamental_data_tools.py` — `get_fundamentals` 等 4 个函数
- 移植原版 `agents/utils/news_data_tools.py` — `get_news`, `get_global_news` 等
- 但底层数据源保留 AKShare/东方财富（通过 `dataflows/interface.py` 路由）
- 分析师 agent 回到原版的 tool binding 方式（`TradingAgentsGraph._create_tool_nodes()`）

### D2: Agent 命名 — 全局 rename 回原版

**选择**: 原子性全局 rename，一次改完所有文件。

| TG-CN | 原版 | 涉及文件 |
|-------|------|---------|
| Risky Analyst | Aggressive Analyst | aggresive_debator.py, agent_states.py, setup.py, conditional_logic.py, propagation.py |
| Safe Analyst | Conservative Analyst | conservative_debator.py, agent_states.py, setup.py, conditional_logic.py, propagation.py |
| Risk Judge | Portfolio Manager | risk_manager.py→portfolio_manager.py, agent_states.py, setup.py, conditional_logic.py, propagation.py |
| risky_history | aggressive_history | agent_states.py, propagation.py, trading_graph.py |
| safe_history | conservative_history | 同上 |
| current_risky_response | current_aggressive_response | 同上 |
| current_safe_response | current_conservative_response | 同上 |

### D3: 记忆系统 — 回到 flat-file + PM-only

**选择**: 移植原版 `TradingMemoryLog`（flat-file markdown），仅注入 Portfolio Manager。

**替代方案**: 保留 ChromaDB 但缩小到 PM-only → 拒绝，ChromaDB 是不必要的重依赖，原版的 flat-file 方案足够。

**实施**:
- `memory.py` 替换为原版的 `TradingMemoryLog` 类（append-only markdown log）
- `trading_graph.py` 中删除 5 个 `FinancialSituationMemory` 实例，改用单个 `TradingMemoryLog`
- `setup.py` 中 Portfolio Manager 通过 `past_context` state 字段获取历史
- 从 `requirements.txt` / `pyproject.toml` 移除 `chromadb` 依赖

### D4: Provider 清理 — 删除千问 workaround

**选择**: 删除所有千问专属代码。

**实施**:
- 删除 `llm_adapters/dashscope_openai_adapter.py` 中的千问 model description hack
- 删除 `fundamentals_analyst.py` 中 "通义千问" 模型检测分支
- 删除分析师中的 anti-loop / forced tool-call fallback
- 保留原版的 `invoke_structured_or_freetext()` 作为唯一 fallback 策略

### D5: Bug 修复 — 集成到相关切片

| Bug | 修复位置 | 集成到 |
|-----|---------|--------|
| #14 A股路由错误 | `dataflows/interface.py` | 工具架构切片 |
| #15 新闻 NoneType | `dataflows/news/realtime_news.py` | 工具架构切片 |
| #16 Embedding fallback | `agents/utils/memory.py` | 记忆系统切片 |
| #17 AKShare 断连 | `dataflows/` | 工具架构切片 |
| #18 A股调外国源 | `tools/unified_news_tool.py` → 删除 | 工具架构切片 |

## Risks / Trade-offs

- **[风险] 中文数据源兼容性** → 原版 tool 函数调用 yfinance；TG-CN 需要走 AKShare。通过 `dataflows/interface.py` 的 `route_to_vendor()` 路由解决，tool 函数内部调用 `route_to_vendor` 而非直接调 yfinance。
- **[风险] State 字段改名影响前端** → 前端通过 API 层访问，不直接读 state 字段。但需验证 API 层是否有硬编码字段名。
- **[风险] ChromaDB 移除后记忆质量下降** → 原版只在 PM 注入记忆且运行良好。5-agent 记忆注入是 TG-CN 的过度工程。
- **[风险] 删除 guardrail 后 LLM 行为不稳定** → DeepSeek V4 的 tool-calling 质量与 OpenAI 同级，不需要反幻觉 guardrail。原版的 `invoke_structured_or_freetext()` fallback 已足够。
