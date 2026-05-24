# Proposal: Full Portfolio Coverage — 持仓分析全行业覆盖

## Why

当前 L1 行业扫描由 AI 市场策略师自主决定推荐哪些行业，**不感知用户实际持仓组合**。导致：
- 用户持有 4 个行业，AI 可能只分析其中 2 个
- 覆盖靠多次分析"碰运气"积累，不是一次全覆盖
- `industry_coverage` 的 `planned`/`completed` 两阶段状态模型增加了复杂度但未解决根本问题

用户核心诉求：**以终为始，对持仓涉及的每一个行业都给出 go/nogo 判断。同时保留 AI 推荐机会行业的能力。**

## Design Overview

### 核心变更

```
Before: AI 市场扫描 → 挑 3~5 个行业 → 用户选 → 分析
After:  持仓行业列表 + 用户目标 → AI 判断全量（轻）+ 自选深度辩论（deep） → 一次性全量覆盖
```

### 1. L1 接口新增 `goal`

用户可在触发分析时输入一句话目标（如"年化收益10%"），不填则默认"值博率最大化"。

### 2. 行业分类工具函数提取

`paper.py:get_portfolio_overview()` 中的行业分类逻辑提取到独立函数 `classify_holdings_industries()`，供 `portfolio_analysis.py` 复用。

### 3. Market Strategist Prompt 重写

从"自主扫描市场找机会"改为"基于给定持仓行业列表 + 用户目标，逐行业判 go/nogo"：
- 轻量评估（light）：全部持仓行业，go/nogo + 一句话理由
- 深度辩论（deep）：策略师自选 ≤5 个有分歧/风险/机会的行业
- 机会推荐：≤2 个用户未持有行业的额外推荐

### 4. Contrarian + Macro Judge 适配

- Contrarian：只对策略师标记为 deep 的行业做风险挑战
- Macro Judge：light 行业采信策略师，deep 行业做完整裁决

### 5. Industry Coverage 简化

- 一次 L1 全量写入所有持仓行业（status=completed）
- 新增 `depth` 字段区分 light/deep
- 移除 `planned` 状态

### 6. 前端

- 分析触发页加 goal 输入框
- 行业选择页区分：持仓行业（必选，默认全选） vs AI 推荐（可选）

## Scoping

- **涉及**：`portfolio_analysis.py`、`paper.py`、`market_strategist.py`、`contrarian.py`、`macro_judge.py`、`advisor_graph.py`、`advisor_states.py`、`Analysis.vue`、MongoDB `industry_coverage`
- **不涉及**：L2-L4 分析逻辑、SSE 流式、CIO 裁决、DecisionCard 展示

<!-- Dialectical Analysis -->
**方案对比**：

- 方案 A（迭代积累式）：保持当前 AI 自主选题，多次分析逐步覆盖。优点：零改动。缺点：覆盖靠运气，用户无法得知何时所有行业都被分析过。
- 方案 B（全量覆盖式）：L1 输入从"市场"变为"持仓行业列表 + 用户目标"，AI 对全量行业做轻量判断 + 自选深辩。优点：一次全覆盖，用户可控。缺点：Prompt/Graph/Router 三层穿透，改动较大。

选择方案 B，理由：
1. "持仓分析"的语义是分析持仓——覆盖全部持仓行业是最低要求
2. AI 自选 deep vs light 的机制比纯仓位排序更智能（0.5% 仓位但面临政策风险的行业值得深度辩论）
3. 轻量评估的 token 成本可控（N 个行业 × 一句话 ≈ 少量 tokens）

**风险对冲**：
- Prompt 改动可能导致 L1 输出格式不稳定：保留 `_parse_industries()` 的容错逻辑，解析失败时回退到旧行为
- 大量行业（20+）时轻量评估可能超出 context：按仓位排序，超大组合时只保留 top 15 + 其余合并为"其他行业组"
