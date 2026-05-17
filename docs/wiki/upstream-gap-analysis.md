# TG upstream vs TG-CN 差距分析

**日期**: 2026-05-17
**对比版本**: TG v0.2.5 vs TG-CN (main@e6e31a7)

## 背景

以 TG-CN 为底座，增量吸收 TG upstream 核心管线能力。TG-CN 在产品层（Web UI、中文数据源、Docker 部署、配置管理）领先；TG upstream 在 Agent 管线核心设计上更优。

## 差距总表

### P0 — 核心管线（影响分析质量）

| # | 能力 | TG upstream | TG-CN 现状 | 吸收策略 |
|---|------|------------|-----------|---------|
| 1 | ~~结构化输出 + 能力感知~~ | ~~`capabilities.py` 按模型查表~~ | ~~硬编码~~ | **已完成** — capabilities.py + structured.py + 3 个 agent 接入 |
| 2 | ~~情绪分析师重设计~~ | ~~预抓取数据注入 prompt~~ | ~~旧版 tool-calling~~ | **已完成** — pre-fetch 模式 + source registry |
| 3 | ~~情绪数据源补齐~~ | ~~StockTwits + Reddit~~ | ~~占位符~~ | **已完成** — eastmoney 热搜 + eastmoney_comment 千股千评 + wechat_mp |

### P1 — 管线质量

| # | 能力 | TG upstream | TG-CN 现状 | 吸收策略 |
|---|------|------------|-----------|---------|
| 4 | 结果反思系统 | `TradingMemoryLog` 追踪实际收益/alpha | ChromaDB 按组件反思，无结果追踪 | 移植 TradingMemoryLog，与现有 ChromaDB 并存 |
| 5 | LLM 工厂清理 | `create_llm_client` 单路径工厂 | `trading_graph.py` 500+ 行 if/elif | 重构为工厂模式，保留中文 provider |
| 6 | DeepSeek/MiniMax 子类 | `DeepSeekChatOpenAI` 处理 reasoning_content | 全用普通 ChatOpenAI | 移植子类，对接现有 adapter 层 |
| 7 | 模块化工具层 | `core_stock_tools.py` 等独立文件 + `route_to_vendor()` | 全部内联在 1900 行 interface.py | 拆分 interface.py，引入 vendor-routing |

### P2 — 扩展能力

| # | 能力 | TG upstream | TG-CN 现状 | 吸收策略 |
|---|------|------------|-----------|---------|
| 8 | Alpha Vantage 技术指标 | 服务端 API 计算 | 缺失，只有本地 stockstats | 移植，作为可选数据源 |
| 9 | Azure OpenAI | 完整客户端 | 无 | 移植 azure_client.py |
| 10 | 模型目录更新 | GPT-5.x, Claude 4.7, Gemini 3.x, DeepSeek V4 | GPT-4o, Claude 3.x | 更新 model catalog |
| 11 | 测试基础设施 | conftest fixtures + pytest markers | 282 个调试脚本，无 fixtures | 移植 conftest.py + 清理测试目录 |
| 12 | CLI token 统计 | `StatsCallbackHandler` | CLI 无统计 | 移植 |

### P3 — 长尾

| # | 能力 | 说明 |
|---|------|------|
| 13 | xAI/Grok, Responses API | 新 provider 支持 |
| 14 | vendor-routing 架构 | 数据源路由抽象 |
| 15 | benchmark alpha 计算 | 收益归因 |
| 16 | dynamic MessageBuffer.init_for_analysis | CLI 动态分析师选择 |

## TG-CN 独有能力（不可覆盖）

- 中文数据源全套：AKShare / Tushare / BaoStock / 东方财富 / 微信公众号
- Web 全栈：FastAPI + Vue3 + MongoDB/Redis
- Docker 多服务部署 + CI/CD
- MongoDB 配置管理 + Web 端 token 统计
- `llm_adapters/` 适配器层（与 Web 端耦合）
- 中文 LLM 别名、provider_keys.py
- ChromaDB 多 embedding provider 支持（DashScope/DeepSeek/Qianfan/Google）
- 港股数据支持

## 吸收原则

沿用三问决策：
1. 属于"核心能力"还是"本地分叉区"？→ 核心能力才吸收
2. 能否拆成独立小批次？→ 不能拆的暂缓
3. 现有测试能覆盖吗？→ 不能验证的暂缓

**A股情绪源特别说明**：TG upstream 的 StockTwits/Reddit 是美股场景，A 股需要替代源（东方财富股吧、小红书、雪球等）。现有 eastmoney 源可用，wechat_mp 框架已集成但需外部服务。后续应增加更多中文情绪源，通过注册式框架 `@register("源名称")` 接入。

## 计划执行顺序

Batch 1: P0 #1-3 → Batch 2: P1 #4-7 → Batch 3: P2 #8-12 → Batch 4: P3

每个 batch 走 ACE 流程（planner → applier → reviewer → archiver）。
