## PRD

[planning/v3/industry-layer-rebuild_prd.md](../../../planning/v3/industry-layer-rebuild_prd.md)

## Why

当前行业研究是单线串行、用户手动触发、结论不缓存的孤立流程，导致每次组合分析都重复研究相同行业、个股研究早于行业研究（顺序颠倒）、行业覆盖矩阵由 API 层拼接语义割裂。v3 架构要求行业层成为独立的、可缓存的、自动驱动下游的信息层，为决策层重构（变更2）奠定基础。

## What Changes

- **新增** 景气打分引擎：5类信号（资金流向/北向/PE分位/PMI-PPI/政策文件）自动扫描全18大行业，输出景气排行榜
- **新增** 行业扫描池自动构建：持仓行业（必选）+ watchlist（必选）+ 景气前3名（自动补充）
- **新增** 行业研究员并行架构：每行业独立 spawn，B+C 三层数据源，行业内2轮辩论 + 跨行业1轮辩论
- **新增** 行业辩论结论缓存：7天有效期，industry_coverage 集合升级存储完整结论 + 过期时间，支持手动强制刷新
- **新增** suggested_weight 双因子输出：景气度 × 安全边际，成长期行业不因 PE 高被否决
- **修改** Tier1 触发机制：从用户手动触发改为被行业层 Go 结果驱动，结果存库供下游消费
- **修改** 持仓录入：录入/更新时同步写入 `paper_positions.industry`，消除运行时 LLM 分类
- **修改` advisor_graph.py`**：L1 节点重构为并行行业研究员架构
- **BREAKING** `industry_coverage` 集合 schema 升级：新增 `suggested_weight`、`expires_at`、`debate_history` 字段

## Capabilities

### New Capabilities

- `industry-vitality-scorer`: 景气打分引擎——5类信号加权打分，全18大行业排序，输出前3名景气行业
- `industry-scan-pool`: 行业扫描池自动构建——持仓行业 + watchlist + 景气前3名合并去重
- `parallel-industry-researcher`: 并行行业研究员——每行业独立 spawn，B+C数据源，行业内辩论 → 跨行业辩论 → 输出 go_nogo + suggested_weight
- `industry-debate-cache`: 行业辩论结论缓存——7天有效期，复用判断，手动强制刷新
- `position-industry-classifier`: 持仓录入前置行业分类——录入/更新持仓时同步写入 industry 字段
- `tier1-auto-trigger`: Tier1 研究库自动触发——行业判 Go 后自动启动该行业主要公司研究，结果存库

### Modified Capabilities

（无现有 spec 文件需要 delta 更新）

## Impact

**代码**：
- `tradingagents/graph/advisor_graph.py` — L1 节点重构（market_strategist/contrarian → 并行行业研究员）
- `tradingagents/agents/advisors/` — 新增行业研究员 agent、景气打分工具
- `tradingagents/agents/advisors/advisor_states.py` — 新增 industry_scan_pool、vitality_scores 等字段
- `app/routers/paper.py` — 持仓录入/更新接口新增行业分类写入
- `app/services/portfolio_advisor_service.py` — industry_coverage 读写逻辑升级
- `app/services/industry_vitality.py` — 新增景气打分服务

**数据**：
- `industry_coverage` 集合：schema 升级（BREAKING）
- `paper_positions` 集合：新增 `industry` 字段

**依赖**：
- AKShare：`stock_sector_fund_flow_rank`、`stock_hsgt_hist_em`、`stock_board_industry_pe_em`、`macro_china_pmi`、`macro_china_ppi`（均已有）
- 新增：官网爬虫（国务院/发改委/证监会公告页面，固定 URL 列表维护）

**参考**：
- `planning/v3/architecture_v3.md` — v3 完整架构
- `advisor-industry-matrix-refine`（空变更，本次一并实现其意图）

<!-- Dialectical Analysis
## 方案对比

方案A（保守）：只改缓存，不改并行架构
- 优点：改动小，风险低
- 缺点：行业串行慢，suggested_weight 没有，下游决策层无法依赖
- 结论：不够，决策层重构需要 suggested_weight 作为输入

方案B（本方案）：并行架构 + 缓存 + 双因子输出
- 优点：完整实现 v3 行业层语义，为变更2解锁
- 缺点：改动范围大，advisor_graph 重构有风险
- 风险对冲：行业研究员并行用 asyncio.gather 而非修改 LangGraph 图结构，降低图重构风险

参考亮点：
- TradingAgents 论文：多 agent 并行提升覆盖广度
- Bridgewater：原则编码 + 系统化执行，景气打分是原则编码的体现

最可能失败的点：
- 并行行业研究员的 token 消耗超出预期 → 预备方案：缓存命中率优先，7天内不重跑
- 官网爬虫被反爬 → 预备方案：降级为纯 AKShare 新闻接口
- industry_coverage schema 升级导致旧数据不兼容 → 预备方案：migration 脚本，旧记录标记 expires_at=now()
-->
