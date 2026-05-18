## Why

用户通过 TG-CN 对单只股票跑深度分析（Tier 1），报告存档在 MongoDB。但用户持有多只标的（股票/基金/黄金），系统无法给出"我的持仓整体该怎么操作"的组合级建议。需要 Tier 2 组合顾问引擎——读存档报告 + 持仓数据，通过多角色辩论输出操作方案。

## What Changes

- 新增 Tier 2 组合顾问引擎：3 角色（持仓分析师/策略师/侦察兵）独立分析 → 辩论 → CIO 裁判
- 新增 PortfolioAdvisorService 服务层：数据准备、引擎编排、结果存储
- 新增组合顾问 LangGraph：复用 Tier 1 辩论基础设施（DebateState + 轮转逻辑），新角色 prompt
- 新增 REST API：POST /api/portfolio/advice（触发）、GET /api/portfolio/advice/{id}（查看）
- 前端：持仓页面嵌入"组合建议"按钮 + el-drawer 展示处方和辩论记录
- Tier 1 分析引擎不做任何修改

## Capabilities

### New Capabilities
- `advisor-engine`: 组合顾问引擎核心——3 角色独立分析 + 辩论 + CIO 裁判，输出结构化操作建议
- `advisor-api`: REST API 和服务层——触发/查询/历史，异步执行，进度通知
- `advisor-frontend`: 前端组合建议面板——处方展示 + 辩论记录折叠 + 历史回看

### Modified Capabilities
（无修改现有 spec）

## Impact

- 新建文件：`tradingagents/graph/advisor_graph.py`（Tier 2 图定义）、`tradingagents/agents/advisors/`（3 角色 + CIO agent）、`app/services/portfolio_advisor_service.py`
- 修改文件：`app/routers/paper.py`（新增 2 个 API 端点）、`frontend/src/views/PaperTrading/index.vue`（新增建议面板）
- 依赖：portfolio-advisor 变更（持仓 CRUD + 账户数据），需先交付
- 新增 MongoDB 集合：`portfolio_advice`

## PRD

详见 `planning/v1/portfolio_advisor_engine_prd.md`（O.A.I.S 四层完整 PRD）。

## 原型

本次变更跳过原型——主要是后端引擎，前端仅新增一个 el-drawer 面板展示结构化文本，无复杂交互。
