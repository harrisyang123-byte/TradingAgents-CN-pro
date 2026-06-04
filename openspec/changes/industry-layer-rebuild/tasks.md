# Tasks: industry-layer-rebuild

每个 Task 是端到端垂直切片，完成后用户可见/可验证。

---

## Task 1: 持仓录入前置行业分类

**目标**：用户录入或更新持仓时，`paper_positions.industry` 自动写入，消除运行时 LLM 分类开销。

**实现范围**：
- `app/routers/paper.py`：`create_position` / `update_position` 接口写入前调用行业分类
- `app/services/industry_classifier.py`：新增 `classify_by_akshare(code)` 方法（AKShare 股票基本信息优先，fallback LLM）
- `scripts/migrate_position_industry.py`：历史持仓行业字段批量补填脚本
- 验证：录入茅台（600519），确认 industry 字段写入"食品饮料"

- [x] 实现 AKShare 行业分类（`stock_individual_info_em`）
- [x] 实现 LLM fallback 分类
- [x] 持仓录入接口集成
- [x] 持仓更新接口集成
- [x] 历史数据迁移脚本
- [ ] 验证端到端

---

## Task 2: 景气打分引擎

**目标**：全量18大行业按5类信号打分，自动输出景气排行榜（前3名）。

**实现范围**：
- `app/services/industry_vitality.py`：新建景气打分服务
  - `score_all_industries()` → `List[IndustryVitalityScore]`
  - 5类信号：资金流向 / 北向资金 / PE分位 / PMI-PPI / 政策文件
  - 政策文件：AKShare 新闻接口 + 官网爬虫（国务院/发改委/证监会，固定 URL 列表）
  - 降级：信号不可用时跳过，标注 data_completeness
- 验证：运行打分，确认输出18行记录，前3名标注 top3_flag=True

- [x] 资金流向信号（AKShare `stock_sector_fund_flow_rank`）
- [x] 北向资金信号（AKShare `stock_hsgt_hist_em`）
- [x] PE分位信号（AKShare `stock_board_industry_pe_em`）
- [x] PMI/PPI 信号（AKShare `macro_china_pmi` / `macro_china_ppi`）
- [x] 政策文件信号（AKShare 新闻 + 官网爬虫，含反爬降级）
- [x] 加权打分 + 排序 + top3 标注
- [ ] 验证端到端

---

## Task 3: 行业扫描池自动构建

**目标**：每次分析启动时，自动合并持仓行业 + watchlist + 景气前3名，输出带来源标注的行业列表。

**实现范围**：
- `app/services/industry_scan_pool.py`：新建扫描池构建服务
- `app/models/watchlist.py`（若不存在）：用户 watchlist 数据模型
- `app/routers/watchlist.py`（若不存在）：watchlist 增删查接口
- `app/services/portfolio_advisor_service.py`：启动前调用 scan_pool 构建
- 验证：用户持仓含科技+消费，watchlist 含医药，景气前3含新能源，最终池包含4个行业

- [ ] 确认 watchlist 是否已有（若无则新建 model + router）
- [ ] 持仓行业聚合逻辑（读 paper_positions.industry）
- [ ] 景气打分集成（Task 2 依赖）
- [ ] 三层合并去重 + 来源标注
- [ ] 注入 AdvisorState.industry_scan_pool
- [ ] 验证端到端

---

## Task 4: 行业辩论结论缓存

**目标**：industry_coverage 集合升级，支持7天有效期复用和手动强制刷新。

**实现范围**：
- `app/services/portfolio_advisor_service.py`：industry_coverage 读写逻辑升级
  - 读取时检查 expires_at，过期视为无效
  - 写入时设置 expires_at = now + 7天
  - 旧记录兼容：缺少 expires_at 视为过期
- `app/routers/advisor.py`：新增 `POST /advisor/industry/{name}/refresh` 接口（手动强制刷新）
- `advisor_graph.py`：L1 节点前插入缓存检查，命中则跳过研究
- 验证：首次运行写入缓存，再次运行确认命中缓存，调用 refresh 接口后下次重新运行

- [ ] industry_coverage schema 升级（新增字段，向后兼容）
- [ ] 缓存读取逻辑（含旧记录兼容）
- [ ] 缓存写入逻辑（expires_at 自动设置）
- [ ] advisor_graph 缓存检查节点
- [ ] 手动刷新接口
- [ ] 验证端到端

---

## Task 5: 并行行业研究员

**目标**：扫描池内每个行业独立并行研究，行业内2轮辩论 + 跨行业1轮辩论，输出 go_nogo + suggested_weight。

**实现范围**：
- `tradingagents/agents/advisors/industry_researcher.py`：新建行业研究员 agent
  - 接收行业名 + B+C 三层数据
  - 内置 Strategist/Contrarian 辩论（2轮）
  - 输出 go_nogo / suggested_weight / reasoning / debate_history
- `tradingagents/agents/advisors/cross_industry_judge.py`：跨行业权重辩论裁判
- `tradingagents/graph/advisor_graph.py`：新增 `parallel_industry_research` 节点
  - asyncio.gather 并行执行各行业研究员（缓存未命中的）
  - 完成后触发跨行业辩论
  - 结果写入 industry_coverage（Task 4 依赖）
- 验证：5个行业并行运行，总耗时 < 最慢单行业 × 1.5，suggested_weight 不超 max_industry_weight

- [ ] 行业研究员 agent（B+C 数据注入）
- [ ] Strategist/Contrarian 辩论逻辑（2轮）
- [ ] 行业研究员输出景气强度定性判断（强烈看好/看好/中性/看空），不直接输出数字权重
- [ ] 跨行业权重辩论（1轮）：接收 total_weight_limit + 各行业景气强度，做资源分配输出 final_weight（加总 = total_weight_limit）
- [ ] asyncio.gather 并行节点
- [ ] advisor_graph 集成
- [ ] 验证端到端

---

## Task 6: Tier1 研究库自动触发

**目标**：行业判 Go 后，自动触发该行业主要公司的 Tier1 研究，结果存库供下游消费。

**实现范围**：
- `app/services/stock_research_cache.py`：新建研究库服务（CRUD + 过期检查）
  - 集合：`stock_research_cache`（code / user_id / report / expires_at / trigger_source）
- `tradingagents/graph/advisor_graph.py`：行业层完成后 asyncio.create_task 触发 Tier1
  - 行业主要公司：AKShare `stock_board_industry_cons_em` 按市值前10
  - 检查缓存，未过期跳过，过期或新增则触发
- `tradingagents/agents/researchers/`：Tier1 研究结果写入 stock_research_cache
- `app/routers/portfolio_analysis.py`：手动触发 Tier1 时同样写入 stock_research_cache
- 验证：科技行业判 Go 后，自动触发前10家公司研究；再次分析时命中缓存；手动分析茅台后组合分析可复用

- [ ] stock_research_cache 集合设计 + 服务
- [ ] 行业主要公司获取（AKShare 成分股按市值）
- [ ] 异步触发逻辑（asyncio.create_task）
- [ ] Tier1 结果写入研究库
- [ ] 手动触发兼容写入
- [ ] Step2 公司层读取研究库接口
- [ ] 验证端到端

---

## 完成标准

所有 Task 完成后：
1. 持仓录入自动带行业，/overview 不再调用 classify_llm
2. 每次分析自动识别景气行业，扫描池来源透明
3. 行业辩论7天内复用，首次运行后再次运行明显更快
4. 行业研究员并行，5个行业总耗时 < 串行的 50%
5. Tier1 研究结果存库，组合分析可消费（为变更2解锁）
