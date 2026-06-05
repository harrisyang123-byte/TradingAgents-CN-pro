---
version: v3.0
requirement: decision-layer-rebuild
status: confirmed
created: 2026-06-04
depends-on: industry-layer-rebuild
modules: [tradingagents/graph, tradingagents/agents/advisors, app/routers, app/services]
entities: [PortfolioManager, PortfolioSynthesizer, RiskDirector, IndustryPM]
---

# PRD：决策层重构（decision-layer-rebuild）

## O — Objective

### Pain
当前 CIO 同时承担"选股 + 定权重 + 输出处方"三个职责，上下文超载，导致：
- 分析没有深度，很多标的无建树性判断
- 大量处方显示"hold"，缺乏真正的调仓建议
- 行业配置和个股选择混在一起，职责不清，质量双低
- 风控是事后检验，无法阻止违规方案产生

### Aspiration
决策层职责清晰分离，每个角色专注一件事：
- 行业PM：在行业配额内专注选股配仓，上下文聚焦（3-5只标的）
- Portfolio Synthesizer：验证约束链完整性，不做新决策
- Risk Director：整体组合压力测试，悲观vs乐观双视角
- 风控规则引擎：事前硬拦截，不可绕过

### Metric
- 处方中有实质调仓建议（buy/sell/reduce/add）的比例 ≥ 60%（现在约 20%）
- 用户执行处方后1个月收益率 > 同期沪深300（以盈利为目标）
- 风控违规方案0漏出（规则引擎硬拦截）

---

## A — Architecture

### 核心实体

**IndustryPMResult**（行业PM配仓结果）
```
industry: str
final_weight: float              # 来自行业层，行业总配额
pm_debate_summary: str           # 激进PM vs 保守PM辩论摘要
positions: List[PMPosition]

PMPosition:
  code: str
  name: str
  action: Literal['buy', 'add', 'hold', 'reduce', 'sell', 'new_position']
  target_weight: float           # 在行业final_weight内分配
  entry_price_range: tuple[float, float]  # Tier1区间 + PE分位双重验证，取保守值
  build_strategy: Literal['immediate', 'batch', 'conditional']
  batch_plan: List[dict] | None  # 分批建仓计划（价格+仓位）
  reasoning: str
  risk_note: str
  tier1_rating: str              # 引用 Tier1 评级
  pe_percentile: float           # 当前PE历史分位
```

**RiskAssessment**（风险压测结果）
```
max_drawdown_20pct: float        # 市场下跌20%时组合最大回撤
black_swan_trigger: List[str]    # 黑天鹅触发条件列表
cash_buffer_suggestion: float    # 建议现金缓冲比例
pessimist_view: str              # 悲观视角完整分析
optimist_view: str               # 乐观视角完整分析
verdict: str                     # 风控裁判最终意见
```

**PortfolioSynthesisResult**（Portfolio Synthesizer输出）
```
constraint_chain_valid: bool     # 约束传递链是否完整
violations: List[str]            # 发现的约束违规（报警不修正）
industry_matrix: List[IndustryMatrixRow]
prescription: List[FinalPosition]
gaps: List[IndustryGap]          # 行业配额有但PM未填满的缺口
gap_scout_triggered: bool        # 是否触发缺口侦察

IndustryMatrixRow:
  industry: str
  source: str                    # holding/watchlist/vitality
  go_nogo: str
  vitality_level: str
  final_weight: float            # 行业层分配的配额
  actual_weight: float           # PM实际配仓加总
  gap: float                     # final_weight - actual_weight
  positions: List[str]           # 该行业持仓代码列表

FinalPosition:
  code: str
  name: str
  industry: str
  action: str
  current_weight: float
  target_weight: float
  entry_price_range: tuple
  build_strategy: str
  batch_plan: List[dict] | None
  reasoning: str
  risk_note: str

IndustryGap:
  industry: str
  allocated: float               # 行业配额
  filled: float                  # PM实际填入
  gap: float                     # 缺口
  scout_triggered: bool
```

### 约束传递链（核心设计）

```
Step 0 宏观裁判
  → total_weight_limit: float    # 股票总仓位上限
  → cash_floor: float            # 现金下限
  → 注入所有下游层

Step 1 跨行业裁判（变更1产出）
  → 接收 total_weight_limit
  → 输出各行业 final_weight（加总 = total_weight_limit）
  → 注入各行业PM

行业PM×N（并行）
  → 接收 final_weight（行业配额）
  → 个股 target_weight 加总 ≤ final_weight
  → 输出 IndustryPMResult

风控规则引擎（事前硬拦截）
  → 验证：单股 ≤ max_single_weight
  → 验证：行业实际权重 ≤ final_weight
  → 验证：总仓位 ≤ total_weight_limit
  → 验证：现金 ≥ cash_floor
  → 违规 → 打回对应行业PM重做（不打回全流程）

Risk Director（整体组合压测）
  → 接收所有行业PM汇总方案
  → 悲观RD vs 乐观RA（2轮）→ 风控裁判
  → 输出 RiskAssessment

Portfolio Synthesizer
  → 验证约束传递链完整性
  → 发现违规 → 报警标注，不修正
  → 处理缺口 → 触发 dispatch_scout
  → 汇总 industry_matrix + prescription
  → 输出 PortfolioSynthesisResult
```

### 状态机：风控打回流程

```
行业PM输出方案
  → 风控检查
  → 通过 → 继续
  → 违规 → 标注违规类型 + 打回对应行业PM
  → 行业PM重做（最多2次）
  → 2次后仍违规 → 强制截断到约束边界 + 报警
```

### PM配仓决策逻辑

```
行业配额 final_weight（来自行业层）
候选标的列表（来自Step2 公司层，Tier1评级+PE分位）

激进PM策略：
  重仓高评级标的（强烈买入配额的60%，买入配额的40%）
  行业配额尽量用满（使用率≥90%）
  偏向immediate建仓

保守PM策略：
  分散配置（单标的≤行业配额的40%）
  行业配额保留缓冲（使用率≤80%）
  偏向batch或conditional建仓

买入价格区间：
  取 Tier1目标价区间 与 PE历史30分位区间 的交集
  无交集时取两者中更保守（更低）的区间
  标注：tier1_range vs pe_range 是否一致
```

---

## I — Interface

### 前端变更：/overview 页面

**行业矩阵数据源变更**：
- 现在：API实时拼接（持仓行业+industry_coverage+处方）
- 变更后：直接读最近一次 advice 的 `industry_matrix` 字段
- 新增列：vitality_level（景气强度）、gap（配额缺口）、source（入池来源）

**个股处方展示增强**：
- 新增：entry_price_range（买入价格区间）
- 新增：build_strategy + batch_plan（分批建仓计划）
- 新增：tier1_rating + pe_percentile（决策依据透明）

### 新增接口
- 无新增接口（决策层变更对 API 透明，portfolio_advice 集合字段扩展）

### 修改接口
- `GET /paper/overview` — 数据源从实时拼接改为读 advice.industry_matrix

---

## S — Scenarios

### 正常路径
- 5个Go行业 → 5个行业PM并行运行，每个PM只看本行业3-5只标的
- 科技PM激进vs保守辩论 → 裁判输出科技行业配仓方案
- 所有行业PM完成 → 风控规则引擎逐条验证 → 全部通过
- Risk Director压测 → 悲观视角最坏回撤18%，乐观视角8% → 裁判综合输出
- Portfolio Synthesizer验证约束链 → 发现科技缺口11% → 触发dispatch_scout

### 异常路径
- 某行业PM方案单股超限 → 风控打回该行业PM重做，其他行业不受影响
- 打回2次仍违规 → 强制截断 + 报警标注，用户可见
- Tier1报告未就绪（异步未完成）→ PM降级用LLM内生知识+PE分位配仓，标注"Tier1数据待更新"
- 所有行业配额使用率极低 → Portfolio Synthesizer标注"大量缺口"，建议用户扩大watchlist或等待更好买点

### 边界条件
- total_weight_limit=0（宏观极度risk-off）→ 所有行业final_weight=0，处方全为减仓/清仓
- 行业配额已满但Tier1评级极差 → 保守PM方案：配额使用率压到最低，大量留现金
- 所有候选标的PE分位>80% → 买入价格区间标注"估值偏高，建议等待回调"，build_strategy=conditional
- 风控打回后PM重做方案仍有小偏差（<0.1%）→ 规则引擎自动截断到边界，不再打回（避免无限循环）
