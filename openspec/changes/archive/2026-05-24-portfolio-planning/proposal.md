# Proposal: 持仓组合规划 (Portfolio Planning)

## Why

当前组合顾问功能只有一个"组合分析"按钮，点击后在抽屉中展示结果。存在三个核心问题：

1. **分析过程不可见**：用户看不到 L1→L2→L3→L4 四层 agent 的实际工作过程，只有一行按钮文字变化。既无法建立信任感，也无法审查 agent 判断是否有问题。
2. **无行业覆盖追踪**：每次分析独立运行，L1 市场策略师每次选 3-5 个行业，28+ 个申万行业没有覆盖状态记录。用户不知道哪些行业已被分析、哪些该分析但还没分析。
3. **结果不持久化**：组合建议存入 `portfolio_advice` 集合，报告页 (`/reports`) 查不到。无历史回溯能力。

需要升级为完整的"持仓组合管理"三页面架构。

## Design Overview

### 页面架构

```
/portfolio (BasicLayout, el-sub-menu)
  ├── /portfolio/holdings   — 我的持仓（现有，去"组合分析"按钮）
  ├── /portfolio/analysis   — 持仓分析（新增，流式分析页）
  └── /portfolio/overview   — 持仓组合总揽（新增，仪表盘）
```

### 两阶段分析

```
Phase 1: L1 市场扫描 → 推荐行业计划 → 用户确认
Phase 2: L2-L4 标的筛选+组合构建+CIO裁决 → 结果展示
```

### 流式技术：SSE + Redis PubSub

复用现有 SSE 端点 (`app/routers/sse.py`) + `RedisProgressTracker`，打通 PubSub 发布通道。

### 结果双写

`portfolio_advice`（保持兼容）+ `analysis_reports`（`report_type: "portfolio"`）。

<!-- Dialectical Analysis -->

### 方案对比

| 维度 | 方案 A (采用): 三页面拆分 | 方案 B: 单页面 SPA |
|------|--------------------------|---------------------|
| 可维护性 | 各页面职责单一 | 一个巨型组件 |
| 导航清晰度 | 子菜单三维度 | 需页面内 tab 切换 |
| 复用度 | holdings 不变，analysis 模仿 SingleAnalysis | 需重写全部 |

### 流式技术对比

| 维度 | SSE + Redis (采用) | WebSocket + astream | 增强轮询 |
|------|-------------------|---------------------|---------| 
| 工程代价 | 低（基础设施已就绪） | 高（需 async 化执行链） | 最低 |
| 实时性 | <100ms | 即时 | 2s |
| 复用度 | 最高（SSE 端点 + RedisProgressTracker 已有） | 低 | 低 |

### 风险对冲

- **最大风险**：Redis PubSub 未在当前 analysis 流中打通，需新增 publish 调用
- **预备方案**：若 Redis 不可用，回退到增强轮询模式（进度数据写 MongoDB，前端 2s 轮询）
