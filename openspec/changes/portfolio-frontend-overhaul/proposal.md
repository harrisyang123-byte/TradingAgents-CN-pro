# Proposal: Portfolio Frontend Overhaul

## Why

组合总揽页（`Portfolio/Overview.vue`）当前有三个明显短板：

1. **行业矩阵信息密度不足** — `market_intel.industries[]` 里有 `go_nogo`、`target_weight`、`holdings_weight`、`reasoning` 等字段，但"研究员推理"只在后端降级路径里有，主路径（直接读 `market_intel.industries`）没有把 `reasoning` 和处方明细注入进来。点击行业行后的 Drawer 经常空白。

2. **辩论过程不可见** — `debate_history`、`market_debate_history`、`stock_debate_history` 三个字段存了 L1/L3 完整辩论，但前端完全没有入口，用户无法了解 CIO 裁决的依据。

3. **后端 `/overview` 主路径缺少处方注入** — 走 `market_intel.industries` 分支时，未把 `prescription[]` 按行业 bucket 归并写入 `positions_detail`，导致 Drawer 里"处方明细"永远为空。

<!-- Dialectical Analysis -->

### 方案对比

**方案 A（保守）**：只修前端，`positions_detail` 用 `advice_id` 二次请求 `/advice/{id}` 拿数据。
- 优点：不改后端
- 缺点：多一次网络请求，前端耦合 advice id，Overview 页刷新时序复杂

**方案 B（推荐）**：后端 `/overview` 主路径补注处方，前端直接消费，同时前端拆三个新区块。
- 优点：数据一次性取齐，前端逻辑简单，可扩展
- 缺点：改动后端一个函数（低风险）

选方案 B。

### 风险对冲

- 最可能失败点：`market_intel.industries[].industry` 名称和 `prescription[].code` 之间没有直接关联，必须通过 `portfolio_advice.market_intel.industries[].codes` 做 code 集合交叉匹配
- 预备方案：前端兜底，Drawer 无 `positions_detail` 时直接按代码从 `price_context` 展示基础行情

## What

### 变更 1：后端 `/overview` 处方注入（Task 1）

在 `paper.py` `/overview` 端点的 **主路径**（`market_intel.industries` 分支）补充逻辑：
- 从 `latest_advice.prescription[]` 按 `code` 与 `industry.codes[]` 交叉匹配，注入 `positions_detail`
- 同时注入 `total_assets` 到 response（用于前端计算调仓金额）

### 变更 2：行业矩阵强化（Task 2）

`Overview.vue` 的行业矩阵表格：
- 新增「研究员推理」折叠列（默认折叠，点击行展开），展示 `row.reasoning`
- GoGo/NoGo 改为彩色 Badge 样式，替换现有的文字
- 行业 Drawer 宽度从 420px 扩展到 520px

### 变更 3：行业 Drawer 处方明细修复（Task 3）

Drawer 内"处方明细"区块：
- 接收 Task 1 注入的 `positions_detail`
- 每条处方展示：代码 | 名称 | 操作 | 当前%→目标% | 调仓金额 | 建仓时机 | 盈亏%
- 若 `pe_data` 存在（来自 `stock_candidates`），额外显示 PE 分位标签

### 变更 4：辩论历程区块（Task 4）

在 Overview 页底部新增「分析师辩论历程」折叠卡片：
- 数据来源：最新 advice 的 `debate_history`、`market_debate_history`、`stock_debate_history`
- Tab 结构：市场研判 L1 | 股票辩论 L3 | 综合裁决
- 内容用 Markdown 渲染（已有 `DebateTimeline.vue` 组件可复用）
- 默认折叠，节省页面空间

### 变更 5：历史记录增强（Task 5）

"历史分析记录"卡片：
- 点击某条记录时，加载该次 advice 的 `debate_history` 填入辩论区块
- 摘要行补充显示：行业数 | 耗时 | 总资产估值
