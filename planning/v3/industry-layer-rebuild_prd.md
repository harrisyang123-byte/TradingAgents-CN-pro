---
version: v3.0
requirement: industry-layer-rebuild
status: confirmed
created: 2026-06-04
modules: [tradingagents/graph, tradingagents/agents/advisors, app/routers, app/services]
entities: [IndustryResearcher, IndustryScanPool, IndustryVitalityScore, IndustryDebateCache, StockResearchCache]
---

# PRD：行业层重构（industry-layer-rebuild）

## O — Objective

### Pain
当前行业研究是单线串行、不缓存、用户手动触发的孤立流程：
- 每次分析重复研究相同行业，平均增加 3-5 分钟无效等待
- 个股研究（Tier1）早于行业研究，顺序颠倒，下游无法消费 Tier1 结论
- 行业覆盖矩阵由 `/overview` API 实时拼接，语义割裂，无法支撑 v3 决策层

### Aspiration
行业层成为独立的、可缓存的、自动驱动下游的信息层：
- 自动识别值得研究的行业（景气打分），不依赖用户手动选择
- 行业研究员并行执行，7天缓存复用，大幅缩短分析耗时
- Tier1 被行业层驱动，结果存库，决策层（PM/Portfolio Synthesizer）直接消费

### Metric
- 重复分析同一组行业时，耗时减少 ≥ 70%（缓存命中）
- 并行5个行业的总耗时 ≤ 串行的 40%
- 持仓录入后 `/overview` 接口不再调用 classify_llm（响应时间减少 ≥ 2 秒）

---

## A — Architecture

### 核心实体

**IndustryVitalityScore**（景气打分）
```
industry: str              # 行业名
total_score: float         # 0-100 综合景气分
signal_breakdown: dict     # {资金流向, 北向, PE分位, PMI_PPI, 政策文件} 各维度得分
data_completeness: float   # 0-1，可用信号比例
top3_flag: bool            # 是否进入景气前3名
scored_at: datetime
```

**IndustryScanPool**（行业扫描池）
```
industries: List[IndustryScanItem]

IndustryScanItem:
  industry: str
  source: Literal['holding', 'watchlist', 'vitality']  # 入池来源
  vitality_score: float | None
```

**IndustryDebateCache**（行业辩论缓存，升级 industry_coverage）
```
industry_name: str
user_id: str
go_nogo: Literal['Go', 'NoGo', 'Watch', 'unknown']
vitality_level: Literal['强烈看好', '看好', '中性', '看空']  # 新：定性判断
final_weight: float | None     # 跨行业裁判分配后填入（变更2写入）
lifecycle: str
reasoning: str
debate_history: str            # 新：完整辩论文本
vitality_score: float          # 新：景气打分
expires_at: datetime           # 新：7天后过期
analyzed_at: datetime
```

**StockResearchCache**（Tier1 研究库，新集合）
```
code: str
user_id: str
name: str
industry: str
recommendation: Literal['强烈买入', '买入', '持有', '卖出', '强烈卖出']
target_price: float
entry_price_range: tuple[float, float]
reasoning: str
risk_note: str
trigger_source: Literal['auto', 'manual']  # 自动触发 or 用户手动
expires_at: datetime           # 7天后过期
researched_at: datetime
```

### 状态机

**IndustryDebateCache 状态流转**
```
不存在 / expires_at 已过期
  → [触发研究] → 研究中
  → [辩论完成] → 有效（expires_at = now + 7天）
  → [手动刷新] → 立即过期 → 触发研究
  → [7天到期] → 过期 → 触发研究
```

**行业扫描池构建流程**
```
启动分析
  → 持仓行业聚合（读 paper_positions.industry）
  → watchlist 行业读取
  → 景气打分（全18大行业）→ 取前3名
  → 三层合并去重
  → 检查缓存（未过期 → 跳过，过期 → 进入研究队列）
  → 并行研究员（仅研究队列中的行业）
```

### 数据流

```
[持仓录入] → paper_positions.industry（AKShare分类优先）

[分析启动]
  景气打分引擎（5类信号）
        ↓
  行业扫描池（持仓+watchlist+景气前3）
        ↓
  缓存检查（industry_coverage.expires_at）
        ↓ 未命中
  并行行业研究员×N（asyncio.gather）
    每行业：B+C数据 → Strategist vs Contrarian（2轮）→ 行业裁判
    输出：go_nogo + vitality_level（定性）
        ↓ 所有行业完成
  跨行业权重辩论（1轮）
    输入：total_weight_limit（来自宏观） + 各行业 vitality_level
    输出：各行业 final_weight（加总 = total_weight_limit）
        ↓
  写入 industry_coverage（含 expires_at）
        ↓
  [异步] Tier1 触发（Go行业主要公司 → asyncio.create_task）
    → 写入 stock_research_cache
```

---

## I — Interface

### 新增接口
- `POST /advisor/industry/{name}/refresh` — 手动强制刷新某行业缓存
- `GET /advisor/scan-pool` — 查看当前行业扫描池（含来源标注）
- `GET /watchlist` — 用户 watchlist 查询
- `POST /watchlist` — 添加 watchlist 行业
- `DELETE /watchlist/{industry}` — 删除 watchlist 行业

### 修改接口
- `POST /paper/positions` — 新增：写入 industry 字段
- `PUT /paper/positions/{code}` — 新增：industry 字段不重新分类（除非代码变更）

### 前端无变化
行业层重构对前端透明，`/overview` 接口 schema 不变（变更2再调整）。

---

## S — Scenarios

### 正常路径
- 用户录入茅台（600519）→ 自动写入 industry="食品饮料"，无需手动选择
- 分析启动 → 持仓行业+watchlist+景气前3自动构成扫描池
- 科技行业3天前已研究 → 缓存命中，跳过重新研究，< 1秒返回结论
- 5个行业并行研究 → 总耗时约等于最慢单行业，而非5倍串行

### 异常路径
- AKShare PE分位接口超时 → 降级用其余4类信号打分，标注 data_completeness
- 官网爬虫被反爬 → 降级为 AKShare 新闻接口，记录日志，不中断
- 行业研究员 LLM 超时 → 该行业标记 go_nogo=unknown，其他行业正常完成
- 历史持仓 industry 字段为空 → 视为未分类，扫描池构建时触发一次性补填
- 旧 industry_coverage 无 expires_at → 视为已过期，触发重新研究

### 边界条件
- watchlist 为空 → 正常运行，仅用持仓行业+景气前3
- 所有行业缓存命中 → 跳过所有研究员，直接进入跨行业辩论（读缓存数据）
- 景气打分所有信号不可用 → 景气前3降级为空，扫描池仅含持仓+watchlist
- Tier1 异步触发但 Step2 启动时未完成 → Step2 等待最多60秒，超时降级用 LLM 内生知识
