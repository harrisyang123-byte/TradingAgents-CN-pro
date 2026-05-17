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

### 变更记录
- [P0 核心集成（结构化输出 + Checkpoint + 情绪预抓取）](p0-core-integration.md)
- [P0 核心集成复盘（W.W.L.D）](retro-p0-core-integration.md)
- [情绪数据源设置指南](sentiment-sources-setup.md)
  - eastmoney（开箱即用） vs wechat_mp（需外部服务）
