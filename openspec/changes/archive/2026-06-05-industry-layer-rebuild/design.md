## Context

当前 L1 行业研究是单线串行的，market_strategist 处理所有行业，结论不缓存，每次分析重复研究相同行业。持仓行业分类在运行时由 LLM 实时计算（`/overview` 接口每次调用一个 `classify_llm`），开销隐藏且不稳定。Tier1 个股研究由用户手动触发，和组合管理流程完全割裂，下游（L2/L3/PM）无法消费其结论。

本变更将行业层重构为"独立的、可缓存的、自动驱动下游的信息层"，为变更2（decision-layer-rebuild）解锁 suggested_weight 输入。

## Goals / Non-Goals

**Goals:**
- 行业研究员并行化，缩短总耗时
- 行业辩论结论7天缓存，避免重复研究
- 景气打分引擎自动识别值得研究的行业
- 持仓行业分类前置到录入时，消除运行时开销
- Tier1 结果存库，下游可消费

**Non-Goals:**
- 决策层重构（PM/CIO 职责变更）→ 变更2
- 风控前置（规则引擎事前拦截）→ 变更2
- industry_matrix 前端展示重构 → 变更2
- 行业缺口自动侦察 → 变更2

## Decisions

### D1：并行行业研究员的实现方式

**选择**：`asyncio.gather` 在 advisor_graph 的 L1 预处理节点并行执行，而非修改 LangGraph 图结构。

**理由**：LangGraph 图结构修改风险高，影响面广；asyncio.gather 在单个节点内并行调用多个 LLM，对图结构无侵入，可在现有 `market_strategist` 节点前插入一个 `parallel_industry_research` 节点实现。

**替代方案**：为每个行业创建独立 LangGraph 子图（rejected：复杂度高，图管理困难）。

### D2：景气打分引擎的位置

**选择**：新建 `app/services/industry_vitality.py`，在 advisor_graph 启动前调用（advisor_service 层），打分结果注入 AdvisorState。

**理由**：景气打分是确定性计算（规则 + 数据），不需要 LLM，放在 service 层比放在 agent 内更清晰，也更易测试。

### D3：industry_coverage 缓存的过期检查时机

**选择**：在 `parallel_industry_research` 节点启动前，批量检查扫描池内所有行业的缓存状态，未过期的直接跳过，过期的进入并行研究队列。

**理由**：批量检查比逐行业检查更高效，且可以在运行前就知道本次需要研究几个行业（用于日志和用户提示）。

### D4：Tier1 触发的异步机制

**选择**：行业层 Go 结论产出后，用 `asyncio.create_task` 异步触发 Tier1 研究，主流程不等待。Tier1 结果写入 `stock_research_cache` 集合（新集合）。

**理由**：Tier1 研究耗时较长（每家公司需要四维分析师辩论），同步等待会大幅拖慢 Step1→Step2 的衔接。Step2 公司层启动时，部分 Tier1 结果可能已完成，未完成的等待即可。

**风险**：Step2 启动时 Tier1 可能尚未完成 → 缓解：Step2 公司层对未完成的 Tier1 等待最多 60 秒，超时后使用 LLM 内生知识降级分析。

### D5：持仓行业分类的实现

**选择**：在 `paper.py` 的 `create_position` 和 `update_position` 接口中，写入前调用轻量级行业分类（优先用 AKShare 股票基本信息 `stock_individual_info_em`，fallback 到 LLM 分类）。

**理由**：AKShare 股票基本信息包含申万行业分类，对 A 股准确率高且无需 LLM，成本极低；港股/美股 fallback 到 LLM。

## Risks / Trade-offs

- **并行 token 消耗增加** → 缓解：7天缓存保证大部分行业复用，实际每次重新研究的行业数量有限
- **官网爬虫被反爬** → 降级为 AKShare 新闻接口，已在 spec 中定义
- **industry_coverage schema 升级破坏旧数据** → 迁移策略：旧记录缺少 expires_at 视为过期，触发重新研究
- **Tier1 异步触发但 Step2 等待超时** → 60秒超时后降级，不阻断主流程

## Migration Plan

1. 执行持仓行业补填脚本（为历史持仓写入 industry 字段）
2. 部署新代码（industry_coverage schema 向后兼容，旧记录视为过期）
3. 首次运行后 industry_coverage 全量刷新（因旧记录全部过期）
4. 后续运行享受缓存收益

**回滚**：industry_coverage 旧记录未删除，回滚代码后旧逻辑仍可读取（字段增量，不破坏读取）。

## Open Questions

- 景气打分各维度的权重比例（资金流向 vs PE分位 vs 政策文件）→ 初版等权，后续根据回测调整
- Tier1 自动触发的"行业主要公司"如何定义 → 初版：AKShare 行业成分股按市值排序前10
- watchlist 功能是否已有 → 需确认，若无则本变更一并新增用户 watchlist 设置
