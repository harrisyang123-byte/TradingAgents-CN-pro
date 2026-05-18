## 1. Tier 2 图定义 + Agent 角色

- [x] 1.1 `tradingagents/agents/advisors/advisor_states.py`: 定义 `AdvisorState`（TypedDict）— analyst_assessment, strategist_assessment, scout_assessment, advisor_debate_state, prescription, cio_verdict
- [x] 1.2 `tradingagents/agents/advisors/analyst.py`: 持仓分析师 agent — 读取每只持仓的 Tier 1 报告摘要 + 当前价格 + 持仓成本，逐只评估安全边际，输出 analyst_assessment
- [x] 1.3 `tradingagents/agents/advisors/strategist.py`: 策略师 agent — 读取组合仓位分布 + 行业集中度，逆向思维 + 认知偏差检测，输出 strategist_assessment
- [x] 1.4 `tradingagents/agents/advisors/scout.py`: 侦察兵 agent — 读取策略师的组合缺口 + 非持仓存档报告 + AKShare 行业数据，输出 scout_assessment
- [x] 1.5 `tradingagents/agents/advisors/cio.py`: CIO 裁判 agent — 读取三角色评估 + 辩论记录，芒格思维约束（逆向验证 + 偏差检查 + 集中度红线），输出结构化 prescription（AdviceItem 列表）+ cio_verdict
- [x] 1.6 `tradingagents/graph/advisor_graph.py`: AdvisorGraph 类 — LangGraph StateGraph 定义，节点注册（分析师/策略师/侦察兵/辩论/CIO），条件边（辩论轮数控制），compile()
- [x] 1.7 `tradingagents/graph/advisor_graph.py`: propagate_advice() 方法 — 构造初始状态，执行图，返回 PortfolioAdvice 结构

## 2. 数据准备层

- [x] 2.1 `app/services/portfolio_advisor_service.py`: PortfolioAdvisorService 类框架 — 初始化 MongoDB 集合引用（portfolio_advice, positions, analysis_results）
- [x] 2.2 `app/services/portfolio_advisor_service.py`: `_prepare_tier1_reports()` — 读持仓列表 + 每只持仓的最近 Tier 1 报告
- [x] 2.3 `app/services/portfolio_advisor_service.py`: `_prepare_non_held_reports()` — 查询非持仓存档报告
- [x] 2.4 `app/services/portfolio_advisor_service.py`: `_prepare_scout_context()` — 已合并到 _prepare_non_held_reports（评级筛选在 scout agent 内部完成）
- [x] 2.5 `app/services/portfolio_advisor_service.py`: `generate_advice()` — 编排完整流程：准备数据 → 构建 AdvisorGraph → 执行 → 存储结果 → 通知前端

## 3. REST API + 异步执行

- [x] 3.1 `app/routers/paper.py`: POST /portfolio/advice 端点 — 校验持仓非空 + 无 GENERATING 请求，创建 PortfolioAdvice（GENERATING），异步执行 generate_advice()
- [x] 3.2 `app/routers/paper.py`: GET /portfolio/advice/latest 端点 — 返回最新建议
- [x] 3.3 `app/routers/paper.py`: GET /portfolio/advice/{advice_id} 端点 — 返回指定建议，校验 user_id 权限
- [x] 3.4 `app/routers/paper.py`: GET /portfolio/advice 端点（分页）— 返回历史建议列表
- [x] 3.5 异步执行集成：ThreadPoolExecutor + WebSocket 通知

## 4. 前端组合建议面板

- [x] 4.1 `frontend/src/api/paper.ts`: 新增 `generateAdvice()`, `getLatestAdvice()`, `getAdvice()`, `getAdviceHistory()` API 方法 + AdviceItem/PortfolioAdvice 类型
- [x] 4.2 `frontend/src/views/PaperTrading/index.vue`: 新增"组合建议"按钮 + 加载状态 + 生成中禁用
- [x] 4.3 `frontend/src/views/PaperTrading/index.vue`: el-drawer 组合建议面板 — 处方表格（操作颜色标记）+ 过期报告标注
- [x] 4.4 `frontend/src/views/PaperTrading/index.vue`: 辩论记录折叠面板（el-collapse）— 分角色展示
- [x] 4.5 `frontend/src/views/PaperTrading/index.vue`: 历史建议下拉选择 + 轮询生成状态

## 5. 验证

- [x] 5.1 Python 语法检查：9 个文件全部通过
- [x] 5.2 引擎验证：AdvisorState 13 个字段，AdvisorGraph import 正常，LangGraph 图编译成功
- [x] 5.3 Router 验证：14 个端点注册，4 个 advice 端点
- [x] 5.4 前端验证：vue-tsc --noEmit 零错误
