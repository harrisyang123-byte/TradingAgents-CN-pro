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
- [持仓品种分类 (instrument_type)](instrument-type.md) — stock/etf/fund/bond/other + 前端自动识别 A 股 ETF
- [基金净值获取 (fund-nav)](fund-nav.md) — AKShare 场外基金净值 + 北京时间 21:00 缓存过期 + 两层降级
- [基金详情 (FundDetail)](fund-detail.md) — AKShare 穿透数据 + 30 天缓存 + CSS 饼图
- [组合顾问引擎 (Tier 2)](portfolio-advisor-engine.md) — 三角色信息差辩论 + CIO 芒格约束 + 结构化处方
- [Claude Code 组合顾问](claude-code-advisor.md) — 2026-06-03 新架构：Python编排+9子Agent+交叉验证，替代LangGraph管线

### 数据与情报
- [AI 产业链情报管线](ai-industry-intel.md) — 22 个 X(Twitter) 信源每日抓取，半导体/AI 供应链一手信息流

### 记忆与反思
- [TradingMemoryLog 结果反思系统](trading-memory-log.md) — 决策级结果追踪 + Phase A/B 生命周期 + A 股适配

### v4 分层独立深度投研
- [v4 产品架构图（规范真源）](v4-architecture.md) — 6 横层×3 纵深 + 通用能力层（data-desk 取数/辩论分离）+ 五级存储 + 双跑闭环
- [v4 全量分析执行计划（P0–P5）](v4-full-analysis-plan.md) — 活文档：归类修复 + Agent 补强决策 + 5 阶段验证闸 + 执行记录
- [v4 AI 代跑指南](v4-ai-proxy-run.md) — 本会话 AI 直跑 / claude -p 双驱动 + 文件总线回传

### 变更记录
- [P0 核心集成（结构化输出 + Checkpoint + 情绪预抓取）](p0-core-integration.md)
- [P0 核心集成复盘（W.W.L.D）](retro-p0-core-integration.md)
- [行业层重构（industry-layer-rebuild）](industry-layer-rebuild.md) — 并行行业研究员+景气打分+7天缓存+Tier1自动触发
- [决策层重构（decision-layer-rebuild）](decision-layer-rebuild.md) — 并行行业PM+子Agent风控+Risk Director双角色+Portfolio Synthesizer
- [情绪数据源设置指南](sentiment-sources-setup.md)
  - eastmoney / eastmoney_comment / wechat_mp / xueqiu / tonghuashun / xiaohongshu
- P1 Batch 2: TradingMemoryLog 结果反思系统 + LLM 工厂清理 (archived)
- P2 Batch 3: Azure OpenAI + 模型目录更新 + Alpha Vantage + CLI 统计 + 测试 fixtures (archived)
- P3 Batch 4: xAI/Grok + Responses API + Benchmark Alpha 覆盖 + CLI 动态分析师选择
- [Portfolio Advisor 复盘 (W.W.L.D)](retros/portfolio-advisor-bundle.md) — 持仓管理 + 组合顾问引擎打包复盘
