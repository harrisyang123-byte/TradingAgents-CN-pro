# TradingAgents-CN 知识库

> 多智能体 A股/港股 金融交易分析系统

## 系统架构

- **tradingagents/** — 核心多智能体框架（Agent/Graph/LLM 管线）
- **app/** — FastAPI 后端（Web UI 接口）
- **frontend/** — Vue 3 + Element Plus 前端

## 关键依赖

- Python 3.12+, FastAPI, Uvicorn (后端)
- Vue 3, Element Plus, Vite (前端)
- AKShare, Tushare (A股数据)
- MongoDB, Redis (持久化/缓存)

## 页面导航

### 项目起源
- [项目起源与合并思路](project-genesis.md) — TG + TG-CN 合并策略、吸收原则、演进方向
- [TG upstream 差距分析](upstream-gap-analysis.md) — P0-P3 四级 16 项差距 + 吸收计划

### 认证与安全
- [认证引导与首次部署](auth-bootstrap.md) — 初始 admin 创建、鸡蛋问题、ValidationError 分层

### LLM 管线
- [结构化输出管线](structured-output-pipeline.md) — 能力感知 + bind/invoke + 双级降级 + DeepSeek 回传
- [情绪分析师架构](sentiment-analyst-architecture.md) — pre-fetch 模式 + source registry + 中文数据源

### 组合管理
- [持仓管理 (Portfolio CRUD)](portfolio-crud.md) — 单账户单钱包 + 汇率折算 + 持仓上下文注入分析引擎
- [组合顾问引擎 (Tier 2)](portfolio-advisor-engine.md) — 三角色信息差辩论 + CIO 芒格约束 + 结构化处方

### 记忆与反思
- [TradingMemoryLog 结果反思系统](trading-memory-log.md) — 决策级结果追踪 + Phase A/B 生命周期 + A 股适配

### 变更记录
- [P0 核心集成（结构化输出 + Checkpoint + 情绪预抓取）](p0-core-integration.md)
- [P0 核心集成复盘（W.W.L.D）](retro-p0-core-integration.md)
- [情绪数据源设置指南](sentiment-sources-setup.md)
  - eastmoney / eastmoney_comment / wechat_mp / xueqiu / tonghuashun / xiaohongshu
- P1 Batch 2: TradingMemoryLog 结果反思系统 + LLM 工厂清理 (archived)
- P2 Batch 3: Azure OpenAI + 模型目录更新 + Alpha Vantage + CLI 统计 + 测试 fixtures (archived)
- P3 Batch 4: xAI/Grok + Responses API + Benchmark Alpha 覆盖 + CLI 动态分析师选择
- [Portfolio Advisor 复盘 (W.W.L.D)](retros/portfolio-advisor-bundle.md) — 持仓管理 + 组合顾问引擎打包复盘
