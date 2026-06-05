# 行业层重构（industry-layer-rebuild）

**变更**: industry-layer-rebuild
**日期**: 2026-06-05

## 概述

行业层从单线串行、不缓存、用户手动触发，重构为并行可缓存、自动驱动下游的信息层。核心改进：
- 持仓录入时前置行业分类（写入 `paper_positions.industry`），消除运行时 LLM 分类
- 行业研究员并行执行（每行业独立 spawn），7天缓存复用
- 行业扫描池自动构建（持仓行业 + watchlist + 景气前3名）
- 景气打分引擎（5类信号：资金流向 / 北向 / PE分位 / PMI-PPI / 政策文件）
- Tier1 研究库（被行业 Go 结果自动触发，结果存库供下游消费）

## 实现要点

### 行业扫描池（`app/services/industry_scan_pool.py`）
- 三层来源自动合并：持仓行业（必选）+ watchlist（必选）+ 景气前3名（自动补充）
- 每行业标注 `source`（holding/watchlist/vitality）和 `cached`（缓存有效标志）
- 在 service 层预检 `industry_coverage` 的 `expires_at`，标记缓存有效行业

### 景气打分引擎（`app/services/industry_vitality.py`）
- 5类信号加权打分（等权初版）
- 信号不可用时降级跳过，标注 `data_completeness`
- 按总分降序排列，前3名标注 `top3_flag`
- 政策文件信号：AKShare 新闻接口 + 官网爬虫（国务院/发改委/证监会，含反爬降级）

### 行业研究员（`tradingagents/agents/advisors/industry_researcher.py`）
- B+C 三层数据注入：LLM 内生知识 + AKShare 硬数据 + 新闻研报
- 研究员首发 → 反向者挑战 → 研究员回应 → 裁判输出（2轮辩论）
- 输出：定性判断（强烈看好/看好/中性/看空），不直接输出数字权重
- 并行执行：`asyncio.gather` 在 advisor_graph 的单个节点内

### 跨行业裁判（`tradingagents/agents/advisors/cross_industry_judge.py`）
- 接收 `total_weight_limit`（来自宏观层）和各行定性判断
- 做资源分配而非归一化：在限额内基于判断分配最终权重
- 所有行业 `final_weight` 加总 = `total_weight_limit`

### 行业缓存（变更 `industry_coverage` 集合）
- 新增字段：`expires_at`、`debate_history`、`vitality_level`、`vitality_score`
- 写入时 `expires_at = now + 7天`
- 旧记录向后兼容（缺少 `expires_at` 视为过期）

### 持仓行业分类（`app/services/industry_classifier.py`）
- 优先 AKShare `stock_individual_info_em` 的「所属行业」字段
- 映射到18-bucket体系（`industry_buckets._match_bucket`）
- AKShare 失败则关键词回退（`_fallback_classify`）
- 历史数据补填脚本：`scripts/migrate_position_industry.py`

### Tier1 研究库（`app/services/stock_research_cache.py`）
- 集合：`stock_research_cache`（code / user_id / report / expires_at）
- 行业层输出 Go 后 `asyncio.create_task` 异步触发研究
- 各层通过 `get_batch_research` 直接读取

## 关键决策

1. **并行方式**：`asyncio.gather` 在单节点内并行，而非修改 LangGraph 图结构（降低风险）
2. **行业研究员不输出数字权重**：只输出定性判断（强烈看好/看好/中性/看空），跨行业裁判在 `total_weight_limit` 内做资源分配
3. **估值调整**：景气度是主因子，PE历史分位是调节因子（成长行业不因 PE 高被否决）
4. **缓存位置**：缓存检查在 service 层做（`build_scan_pool` 中有 DB 连接），graph 节点只读 state 中的 cached 标志
5. **手动刷新**：`POST /portfolio/analysis/industry/{name}/refresh` 将 `expires_at` 设为当前时间

## 注意事项

- `asyncio.new_event_loop()` + `loop.run_until_complete()` 模式在 LangGraph 同步节点中可用，但演进到 AsyncGraph 时需重构
- 配置文件（官网爬虫）有被反爬风险，降级为 AKShare 新闻接口
- 行业研究员输出格式未严格校验，`_parse_industry_conclusion` 用正则提取 JSON，结构缺失时使用默认值
