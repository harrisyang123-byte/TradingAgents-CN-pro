## 1. Tier 2 图定义 + Agent 角色

- [ ] 1.1 `tradingagents/agents/advisors/advisor_states.py`: 定义 `AdvisorState`（TypedDict）— analyst_assessment, strategist_assessment, scout_assessment, advisor_debate_state, prescription, cio_verdict
- [ ] 1.2 `tradingagents/agents/advisors/analyst.py`: 持仓分析师 agent — 读取每只持仓的 Tier 1 报告摘要 + 当前价格 + 持仓成本，逐只评估安全边际，输出 analyst_assessment
- [ ] 1.3 `tradingagents/agents/advisors/strategist.py`: 策略师 agent — 读取组合仓位分布 + 行业集中度，逆向思维 + 认知偏差检测，输出 strategist_assessment
- [ ] 1.4 `tradingagents/agents/advisors/scout.py`: 侦察兵 agent — 读取策略师的组合缺口 + 非持仓存档报告 + AKShare 行业数据，输出 scout_assessment
- [ ] 1.5 `tradingagents/agents/advisors/cio.py`: CIO 裁判 agent — 读取三角色评估 + 辩论记录，芒格思维约束（逆向验证 + 偏差检查 + 集中度红线），输出结构化 prescription（AdviceItem 列表）+ cio_verdict
- [ ] 1.6 `tradingagents/graph/advisor_graph.py`: AdvisorGraph 类 — LangGraph StateGraph 定义，节点注册（分析师/策略师/侦察兵/辩论/CIO），条件边（辩论轮数控制），compile()
- [ ] 1.7 `tradingagents/graph/advisor_graph.py`: propagate_advice() 方法 — 构造初始状态，执行图，返回 PortfolioAdvice 结构

## 2. 数据准备层

- [ ] 2.1 `app/services/portfolio_advisor_service.py`: PortfolioAdvisorService 类框架 — 初始化 MongoDB 集合引用（portfolio_advice, positions, analysis_results）
- [ ] 2.2 `app/services/portfolio_advisor_service.py`: `_prepare_analyst_context()` — 读持仓列表 + 每只持仓的最近 Tier 1 报告 + 最新行情，标记报告过期状态（7 天阈值）
- [ ] 2.3 `app/services/portfolio_advisor_service.py`: `_prepare_strategist_context()` — 计算仓位分布、行业集中度、持仓间相关性
- [ ] 2.4 `app/services/portfolio_advisor_service.py`: `_prepare_scout_context()` — 查询非持仓存档报告（评级 Buy/Overweight）+ AKShare 行业板块数据
- [ ] 2.5 `app/services/portfolio_advisor_service.py`: `generate_advice()` — 编排完整流程：准备数据 → 构建 AdvisorGraph → 执行 → 存储结果 → 通知前端

## 3. REST API + 异步执行

- [ ] 3.1 `app/routers/paper.py`: POST /portfolio/advice 端点 — 校验持仓非空 + 无 GENERATING 请求，创建 PortfolioAdvice（GENERATING），异步执行 generate_advice()
- [ ] 3.2 `app/routers/paper.py`: GET /portfolio/advice/latest 端点 — 返回最新 COMPLETED 状态的建议
- [ ] 3.3 `app/routers/paper.py`: GET /portfolio/advice/{advice_id} 端点 — 返回指定建议，校验 user_id 权限
- [ ] 3.4 `app/routers/paper.py`: GET /portfolio/advice 端点（分页）— 返回历史建议列表
- [ ] 3.5 异步执行集成：复用 Tier 1 的 ThreadPoolExecutor 模式，完成后通过 WebSocket 通知前端

## 4. 前端组合建议面板

- [ ] 4.1 `frontend/src/api/paper.ts`: 新增 `generateAdvice()`, `getLatestAdvice()`, `getAdvice()`, `getAdviceHistory()` API 方法
- [ ] 4.2 `frontend/src/views/PaperTrading/index.vue`: 新增"组合建议"按钮 + 加载状态 + 生成中禁用
- [ ] 4.3 `frontend/src/views/PaperTrading/index.vue`: el-drawer 组合建议面板 — 处方表格（操作颜色标记：红=买入/加仓，绿=卖出/减仓，灰=观望）+ 过期报告 ⚠️ 标注
- [ ] 4.4 `frontend/src/views/PaperTrading/index.vue`: 辩论记录折叠面板（el-collapse）— 分角色 Tab 展示
- [ ] 4.5 `frontend/src/views/PaperTrading/index.vue`: 历史建议下拉选择 + WebSocket 监听生成完成事件

## 5. 验证

- [ ] 5.1 API 测试：通过 curl 触发组合建议，验证异步执行 + 结果存储 + 权限校验
- [ ] 5.2 引擎测试：mock LLM，验证三角色数据隔离 + 辩论轮转 + CIO 结构化输出
- [ ] 5.3 边界测试：无持仓触发、全部报告过期、30+ 只持仓截断、混合品种（股票+ETF）
- [ ] 5.4 前端测试：启动 dev server，验证按钮→加载→抽屉→处方→辩论记录→历史
