# Tasks: decision-layer-rebuild

**前置条件**：industry-layer-rebuild 所有 Task 完成并验证通过。

每个 Task 是端到端垂直切片，完成后用户可见/可验证。

---

## Task 1: 约束传递链 + AdvisorState 扩展

**目标**：宏观层输出 total_weight_limit/cash_floor，注入所有下游层；新增状态字段支撑后续 Task。

**实现范围**：
- `tradingagents/agents/advisors/advisor_states.py`：新增字段
  - total_weight_limit: float
  - cash_floor: float
  - industry_pm_results: List[IndustryPMResult]
  - risk_assessment: RiskAssessment
  - synthesis_result: PortfolioSynthesisResult
  - pm_retry_count: Dict[str, int]（行业→重试次数）
- `tradingagents/graph/advisor_graph.py`：宏观裁判节点输出写入 total_weight_limit/cash_floor
- 验证：运行分析，确认 state 中有 total_weight_limit 字段

- [ ] 新增 AdvisorState 字段定义
- [ ] 新增 IndustryPMResult / RiskAssessment / PortfolioSynthesisResult 数据类
- [ ] 宏观裁判节点写入 total_weight_limit + cash_floor
- [ ] 跨行业裁判接收 total_weight_limit 做资源分配（替代归一化）
- [ ] 验证约束从宏观传到行业层

---

## Task 2: 并行行业PM

**目标**：每个Go行业独立spawn激进PM vs 保守PM辩论，在行业配额内输出个股配仓方案。

**实现范围**：
- `tradingagents/agents/advisors/industry_pm.py`：新建行业PM agent
  - 激进PM角色：重仓高评级，配额用满，偏immediate建仓
  - 保守PM角色：分散配置，配额保留缓冲，偏batch建仓
  - 买入区间：Tier1区间 ∩ PE30分位区间，取保守值
  - 输出：IndustryPMResult（含 batch_plan）
- `tradingagents/graph/advisor_graph.py`：新增 parallel_pm 节点（asyncio.gather）
- 验证：5个行业并行运行，每个PM输出包含 entry_price_range 和 build_strategy

- [ ] 激进PM角色实现
- [ ] 保守PM角色实现
- [ ] 买入区间双重验证（Tier1 + PE分位，取保守值）
- [ ] 分批建仓计划生成（batch_plan）
- [ ] PM裁判输出 IndustryPMResult
- [ ] asyncio.gather 并行节点
- [ ] advisor_graph 集成
- [ ] 验证端到端

---

## Task 3: 事前风控规则引擎

**目标**：PM方案输出后，规则引擎事前硬拦截违规方案，违规打回对应行业PM重做（最多2次）。

**实现范围**：
- `tradingagents/agents/advisors/risk_rules.py`：新建规则引擎（非LLM）
  - 四项规则：单股上限 / 行业上限 / 总仓位上限 / 现金下限
  - 返回：violations 列表（空=通过）
- `tradingagents/graph/advisor_graph.py`：新增 pre_trade_risk_check 节点
  - conditional_edge：通过→继续，违规→打回对应行业PM
  - 用 pm_retry_count 追踪重试次数，≥2次自动截断
- 验证：构造单股超限方案，确认被打回；第3次自动截断到边界

- [ ] 四项规则引擎实现
- [ ] violations 结构化输出
- [ ] 打回逻辑（conditional_edge + retry_count）
- [ ] 第3次强制截断逻辑
- [ ] advisor_graph 集成
- [ ] 验证端到端（打回场景 + 截断场景）

---

## Task 4: Risk Director 双角色重构

**目标**：Risk Director 改为悲观vs乐观双角色辩论，对整体组合做压力测试。

**实现范围**：
- `tradingagents/agents/advisors/risk_director.py`：重构为双角色
  - 悲观Risk Director：专注找最坏情景，挑战组合集中风险
  - 乐观Risk Analyst：反驳悲观观点，指出组合韧性
  - 2轮辩论 → 风控裁判综合输出 RiskAssessment
- `tradingagents/graph/advisor_graph.py`：更新 Risk Director 节点
- 验证：运行分析，确认输出包含 max_drawdown_20pct、pessimist_view、optimist_view

- [ ] 悲观Risk Director角色实现
- [ ] 乐观Risk Analyst角色实现
- [ ] 2轮辩论逻辑
- [ ] 风控裁判输出 RiskAssessment
- [ ] advisor_graph 集成
- [ ] 验证端到端

---

## Task 5: Portfolio Synthesizer（替代CIO Final）

**目标**：Portfolio Synthesizer 验证约束链完整性、处理缺口、触发补充侦察、汇总输出最终处方和行业矩阵。

**实现范围**：
- `tradingagents/agents/advisors/portfolio_synthesizer.py`：新建（替代 cio.py 的最终裁决逻辑）
  - 验证约束传递链（不修正，只报警）
  - 识别行业缺口（gap > 3% 触发 dispatch_scout）
  - 汇总 industry_matrix（含 vitality_level/gap/source）
  - 汇总最终处方（含 entry_price_range/build_strategy/batch_plan）
  - 输出 PortfolioSynthesisResult
- `tradingagents/agents/advisors/cio.py`：废弃选股和定权重逻辑（保留文件但清空实质内容）
- `tradingagents/graph/advisor_graph.py`：CIO_Final 节点替换为 portfolio_synthesizer
- 验证：运行分析，industry_matrix 包含新字段；有缺口时 dispatch_scout 被触发

- [ ] 约束链验证逻辑
- [ ] 缺口识别 + dispatch_scout 触发
- [ ] industry_matrix 汇总（新字段）
- [ ] 最终处方汇总（新字段）
- [ ] PortfolioSynthesisResult 写入 portfolio_advice 集合
- [ ] cio.py 清理
- [ ] advisor_graph 集成
- [ ] 验证端到端

---

## Task 6: /overview 简化 + 前端新增列

**目标**：/overview API 改为读 advice.industry_matrix，前端新增 vitality_level/gap/source 列和处方执行详情。

**实现范围**：
- `app/routers/paper.py`：`get_portfolio_overview` 函数重构
  - 优先读最近一次 COMPLETED advice 的 industry_matrix
  - 无 industry_matrix 字段时降级到现有拼接逻辑（向后兼容）
  - 删除 classify_llm 调用（不再需要运行时分类）
- `frontend/src/views/Portfolio/Overview.vue`：
  - 行业矩阵表格新增列：景气强度（vitality_level）、配额缺口（gap）、来源（source）
  - 处方详情抽屉新增：entry_price_range、build_strategy、batch_plan、tier1_rating、pe_percentile
- 验证：运行完整分析后查看 /overview，确认数据来自 advice.industry_matrix；处方详情显示买入区间和分批计划

- [ ] /overview API 切换数据源（含向后兼容降级）
- [ ] 删除 classify_llm 运行时调用
- [ ] 前端行业矩阵新增3列
- [ ] 处方详情新增执行信息
- [ ] 验证端到端（新数据源 + 旧降级）

---

## 完成标准

所有 Task 完成后：
1. 处方中有实质调仓建议比例 ≥ 60%（可通过历史advice统计验证）
2. 风控违规方案0漏出（规则引擎拦截，可构造测试用例验证）
3. 每条处方包含买入价格区间和分批建仓计划
4. /overview 响应时间减少≥2秒（不再调用classify_llm）
5. 行业矩阵新增 vitality_level/gap/source 列正确展示
