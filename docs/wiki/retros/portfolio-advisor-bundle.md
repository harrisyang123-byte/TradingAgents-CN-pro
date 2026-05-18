# Retro: portfolio-advisor + portfolio-advisor-engine

**复杂度**: 复杂（两个关联变更打包复盘）
**耗时**: 1 天（2026-05-17 设计 → 2026-05-18 实现 + 归档）
**代码量**: 28 文件，+5,429 行，-1,019 行（净增 ~4,400 行）
**commits**: 8 个（1 设计 + 5 实现 + 2 归档）

---

## What Went Well

### 规划阶段

1. **两层分拆决策正确** — 将"持仓管理"和"组合顾问引擎"拆成两个独立变更（portfolio-advisor → portfolio-advisor-engine），使得前者可独立交付验证后再开始后者。事实证明前端 TypeScript 类型对齐、API 格式变更等问题都在第一个变更中暴露和修复，没有污染到引擎层。

2. **信息差架构设计提前验证** — 在 design.md 中明确三角色各看什么数据、不看什么数据，实现时直接照表写 prompt，没有模糊地带。

3. **PRD + 原型驱动** — portfolio_prd.md + portfolio_prototype.html 在实现前就锁定了前端交互。前端改造时没有返工。

### 实现阶段

4. **改造 > 新建** — 复用 `paper.py` 而非新建 `portfolio.py`，节省了路由注册、认证、数据库连接等样板代码。旧格式兼容（dict → float 迁移）只加了 10 行。

5. **分组提交** — 5 个实现 commit 各自包含完整的可验证单元（CRUD API → 汇率服务 → 引擎注入 → 前端 → 验证），每步 git bisect 可用。

6. **Tier 2 图一次通过** — AdvisorGraph 的 LangGraph StateGraph 编译零错误，import 验证即通过。受益于先彻底理解 Tier 1 的 `setup.py` 图拓扑后再写。

### 工具流程

7. **ACE 工作流顺畅** — planner → applier → archiver 三阶段无卡顿。tasks.md 的逐条勾选有效防止了遗漏。

---

## What Went Wrong

### 实现阶段

1. **前端跨文件影响遗漏** — 改造 `paper.ts` API 格式后，`Dashboard/index.vue`、`SingleAnalysis.vue`、`ReportDetail.vue` 三个消费方都需要同步更新（`account.cash` → `account.available_cash`、`accountRes.data.account` → `accountRes.data`）。这些在 tasks.md 中没有列出，是实现中发现的。

2. **Git push 网络问题** — 多次 push 失败（github.com:443 连接超时），需要用户手动切 VPN。这不是代码问题但消耗了交互轮次。

3. **TypeScript 类型精度** — `actionTagType()` 返回 `''` 不在 Element Plus `el-tag` 的 `type` 联合类型中，需要改为 `'primary' | 'success' | ...`。应在写代码时就查 Element Plus 类型定义。

### 流程

4. **无正式 review** — 两个复杂变更都没有跑 ace-reviewer。虽然通过了 Python 语法检查 + vue-tsc + import 验证，但缺少架构/安全维度的审查。

---

## Lessons Learned

### L1: 跨文件消费方影响分析

**经验**: 修改 API 返回格式时，必须先 grep 所有消费方（import 该 API 的文件）并列入 tasks。

**适用条件**: 任何 API response shape 变更、TypedDict 字段改名、接口签名变化。

**边界**: 纯新增字段（向后兼容）不需要，但删除/改名字段必须。

**行动**: 在 ace-planner 的 tasks 生成阶段增加"消费方影响扫描"步骤。

### L2: 信息差 > 人设差

**经验**: 多 Agent 系统中，给同一个 LLM 不同人设（"你是乐观分析师"/"你是悲观分析师"）产生的分歧是表面的。真正的思维多样性来自让每个角色看不同的数据子集。

**适用条件**: 任何 LangGraph 多角色协作场景。

**边界**: 当角色需要全局视角时（如 CIO 裁判），不适用信息差——裁判必须看到所有信息。

### L3: 改造模式的旧格式兼容成本极低

**经验**: 改造现有模块（vs 新建）时，旧数据格式兼容通常只需 5-10 行检测 + 迁移代码（如 `isinstance(cash, dict) → take CNY`），远低于新建模块的连接成本。

**适用条件**: 底层数据模型变更不大的重构。

**边界**: 数据模型彻底重写时（如从关系型改文档型），兼容成本会暴涨。

### L4: LangGraph 图写之前先读

**经验**: 写新的 StateGraph 之前，完整阅读已有图的 `setup.py`（节点注册 + 边定义 + 条件逻辑），直接复用已验证的模式。Tier 2 的辩论轮转就是照搬 Tier 1 的 `should_continue_debate` 模式。

**适用条件**: 项目中已有 LangGraph 图的情况。

---

## Decisions to Make

1. **[ ] 跨文件消费方扫描** — 考虑在 ace-planner tasks 生成时自动 grep API 导入方，列入 tasks
2. **[ ] 复杂变更必须 review** — 当前 ace-reviewer 是可选的，考虑对"复杂"级别变更强制 review 后再归档
3. **[ ] CIO 处方解析鲁棒性** — `_parse_prescription()` 依赖 LLM 输出正确的 JSON 格式，考虑增加 retry + 格式修正逻辑

---

## 架构健康检查

### 新模块引入

| 模块 | Deletion Test | 判定 |
|------|--------------|------|
| `tradingagents/agents/advisors/` | 删掉后组合级分析能力完全消失，复杂度无法转移到其他地方 | **Deep module** — 接口简单（`propagate_advice(summary, reports)`），实现复杂（三角色+辩论+CIO） |
| `app/services/portfolio_advisor_service.py` | 删掉后数据准备逻辑需要分散到 router 和 graph 中 | **Deep module** — 隔离了 MongoDB 查询 + LLM 配置 + 异步执行 |
| `app/services/portfolio_service.py` | 删掉后汇率+总览计算分散到多处 | **Deep module** |

### 接口 vs 实现复杂度

- `AdvisorGraph.propagate_advice(summary, reports, non_held)` → 3 个参数进，1 个 dict 出。内部 10 次 LLM 调用 + 图编排。**接口远比实现简单**。
- `PortfolioAdvisorService.generate_advice(user_id, advice_id)` → 2 个参数。内部 3 次 MongoDB 查询 + LLM 初始化 + 图执行 + 结果存储 + WebSocket 通知。**Deep**。

### 跨层调用

- `portfolio_advisor_service.py` import `trading_graph.create_llm_by_provider` — 跨层引用引擎层的 LLM 工厂。可接受：服务层需要创建 LLM 实例，工厂是正确的入口点。不是循环依赖。
