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

- [P0 核心集成（结构化输出 + Checkpoint + 情绪预抓取）](p0-core-integration.md)
- [P0 核心集成复盘（W.W.L.D）](retro-p0-core-integration.md)
  - 结构化输出模型及绑定工具
  - SqliteSaver 断点恢复
  - 注册式情绪数据源框架
