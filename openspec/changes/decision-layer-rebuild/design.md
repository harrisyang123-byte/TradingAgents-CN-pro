## Context

变更1（industry-layer-rebuild）重构了行业信息层，输出 final_weight、vitality_level、StockResearchCache。本变更基于这些产出，重构决策层：引入并行行业PM、约束传递链、事前风控和 Portfolio Synthesizer，让每个角色专注一件事。

现有 CIO（cio.py）同时承担选股+定权重+输出处方，上下文超载，分析质量低。风控是 Risk Director 之后的事后检验，无法前置拦截。

## Goals / Non-Goals

**Goals:**
- 并行行业PM，每个PM上下文聚焦（3-5只标的），提升配仓质量
- 约束传递链，消除跨层矛盾，Portfolio Synthesizer验证完整性
- 风控规则引擎事前硬拦截，替代事后检验
- Risk Director双角色压测，悲观vs乐观双视角
- /overview简化，读 advice.industry_matrix 不再实时拼接

**Non-Goals:**
- 宏观层改造（Step 0）→ 现有 market_strategist/contrarian 保留
- Tier1 研究内部结构改造 → 变更1已完成触发机制
- 前端大幅重构 → 仅在现有表格新增列，不改布局

## Decisions

### D1：行业PM的实现方式

**选择**：每个行业PM是一个独立的 async 函数，在 advisor_graph 的新节点 `parallel_pm` 中用 asyncio.gather 并行调用，和变更1的并行行业研究员相同模式。

**理由**：已有成功先例（变更1），无需引入新的并行机制，复用模式降低风险。

### D2：风控规则引擎的位置

**选择**：在 advisor_graph 中新增 `pre_trade_risk_check` 节点，位于 parallel_pm 之后、Risk Director 之前。违规时通过 conditional_edge 打回对应行业 PM（最多2次），第3次自动截断。

**理由**：独立节点职责清晰，打回逻辑用 state 中的 `pm_retry_count` 字段追踪，不需要修改 PM 本身。

### D3：Portfolio Synthesizer vs CIO

**选择**：`cio.py` 重构为 `portfolio_synthesizer.py`，删除选股和定权重逻辑，只做验证+聚合+输出。

**理由**：CIO 名字误导了实现——让它"做决策"。改名+重构让职责边界清晰，不再有"CIO 应该判断买什么"的冲动。

### D4：/overview 切换时机

**选择**：portfolio_advice 保存时写入 industry_matrix 字段，/overview 读取时优先用 industry_matrix，无则降级到现有拼接逻辑（向后兼容）。

**理由**：渐进切换，不破坏现有用户体验；新分析完成后自动升级到新数据源。

## Risks / Trade-offs

- **并行PM token消耗** → 缓解：每个PM上下文极小（3-5只标的+行业底稿），实际消耗远小于现有CIO
- **风控打回死循环** → 缓解：retry_count硬限2次，第3次强制截断
- **约束传递实现Bug** → 缓解：Portfolio Synthesizer显式验证，violations字段暴露问题
- **advisor_graph重构风险** → 缓解：L1/L2节点不动，只重构L3/L4；分步提交，每步验证

## Migration Plan

1. 变更1完成并验证后启动本变更
2. 新增并行PM和Portfolio Synthesizer节点（不删除旧CIO，并行保留）
3. 在feature flag下启用新流程，对比新旧输出质量
4. 验证通过后删除旧CIO节点，切换/overview数据源
5. 删除旧 classify_holdings_industries 运行时调用

**回滚**：feature flag关闭即回滚到旧CIO流程；/overview降级逻辑保留，无需代码回滚。

## Open Questions

- 行业PM辩论裁判的选股逻辑：当Tier1评级和PE分位指向相反方向时（强烈买入但PE分位90%），裁判如何权衡？→ 初版：PE分位>80%时降级建仓策略为conditional，评级权重降低50%
- dispatch_scout触发后的结果如何回填到industry_matrix？→ 异步更新，前端polling或websocket推送
- 用户对"约束异常，请人工复核"的处理入口？→ 初版仅展示警告，后续迭代提供手动调整界面
