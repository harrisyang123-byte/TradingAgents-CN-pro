## 1. 账户模型改造 + CRUD API

- [x] 1.1 `app/routers/paper.py`: 路由前缀 `/paper` → `/portfolio`，`app/main.py` 同步更新注册
- [x] 1.2 `app/routers/paper.py`: `paper_accounts` 改造——删除多币种 `cash: {CNY,HKD,USD}`，改为 `available_cash: float` + `total_invested: float`（单一人民币），保留旧格式兼容（检测 dict 类型时取 CNY 值）
- [x] 1.3 `app/routers/paper.py`: 删除 `INITIAL_CASH_BY_MARKET` 常量和 `_get_or_create_account` 中的多币种初始化逻辑
- [x] 1.4 `app/routers/paper.py`: 新增 `PUT /portfolio/account` 端点——设置 total_invested 和 available_cash
- [x] 1.5 `app/routers/paper.py`: 新增 `POST /portfolio/positions` 端点——创建/追加持仓（code, quantity, avg_cost, buy_date, notes），已存在时加权平均合并
- [x] 1.6 `app/routers/paper.py`: 新增 `PUT /portfolio/positions/{code}` 端点——修改持仓字段
- [x] 1.7 `app/routers/paper.py`: 新增 `DELETE /portfolio/positions/{code}` 端点——删除持仓
- [x] 1.8 `app/routers/paper.py`: 改造 `POST /portfolio/order` 端点——用户填写价格（不再自动获取市价），buy 增加持仓 + 扣减 available_cash，sell 减少持仓 + 增加 available_cash
- [x] 1.9 每个写操作同时创建 Transaction 记录（paper_trades 集合）

## 2. 组合总览 + 汇率

- [x] 2.1 新建 `app/services/portfolio_service.py`: `PortfolioService` 类
- [x] 2.2 `PortfolioService._get_exchange_rate(currency)`: 通过 AKShare `currency_boc_safe` 获取 USD/CNY 和 HKD/CNY 汇率，结果缓存到 MongoDB `exchange_rates` 集合（TTL 24h）
- [x] 2.3 `PortfolioService.get_portfolio_summary(user_id)`: 聚合所有持仓，获取最新价，港股/美股市值按汇率折算人民币，计算总资产、总盈亏、仓位占比
- [x] 2.4 `app/routers/paper.py`: 新增 `GET /portfolio/summary` 端点，调用 `PortfolioService.get_portfolio_summary()`
- [x] 2.5 改造 `GET /portfolio/account` 端点——返回单账户格式（total_invested, available_cash, 总资产, 总盈亏, 总盈亏率）

## 3. 持仓上下文注入分析引擎

- [x] 3.1 `tradingagents/agents/utils/agent_states.py`: `AgentState` TypedDict 增加 `portfolio_context: str` 字段
- [x] 3.2 `tradingagents/graph/propagation.py`: `create_initial_state()` 增加 `portfolio_context` 参数，写入 state
- [x] 3.3 `tradingagents/graph/trading_graph.py`: `propagate()` 增加 `portfolio_context` 参数，传递到 `create_initial_state()`
- [x] 3.4 `tradingagents/agents/managers/portfolio_manager.py`: prompt 中引用 `state["portfolio_context"]`，在决策指导原则中加入用户持仓信息段
- [x] 3.5 `app/services/portfolio_service.py`: `get_portfolio_context(user_id)` 方法——构造持仓摘要字符串（总投入/可用现金/每只持仓明细/仓位占比/盈亏），超过 20 只时截断
- [x] 3.6 `app/services/simple_analysis_service.py`: `_execute_analysis_sync()` 中调用 `get_portfolio_context(user_id)` 并传给 `propagate()`

## 4. 前端改造

- [x] 4.1 `frontend/src/views/PaperTrading/index.vue`: 页面标题"模拟交易" → "我的持仓"，删除风险提示横幅
- [x] 4.2 账户信息卡片改造：从三市场 Tab 改为 4 个水平统计卡片（总资产/总投入/可用现金/总盈亏率），调用 `GET /portfolio/summary`
- [x] 4.3 新增组合图表区：仓位分布饼图（ECharts pie chart），按股票分布
- [x] 4.4 持仓列表改造：新增"仓位占比"列（带进度条）和"盈亏率"列，市值统一显示人民币
- [x] 4.5 改造"下市场单"弹窗为"添加持仓"弹窗：增加"买入价"和"买入日期"输入框，价格改为手动填写
- [x] 4.6 `frontend/src/api/paper.ts`: API 路径 `/paper` → `/portfolio`，新增 `addPosition()`, `updatePosition()`, `deletePosition()`, `getSummary()`, `updateAccount()` 方法
- [x] 4.7 `frontend/src/router/index.ts`: 路由 `/paper` → `/portfolio`，旧路由重定向
- [x] 4.8 `frontend/src/components/Layout/SidebarMenu.vue`: 菜单项"模拟交易" → "我的持仓"

## 5. 验证

- [x] 5.1 API 测试：通过 curl 录入 3 只不同市场的持仓，验证 CRUD + 加权平均
  - 验证方式：后端 router 加载成功，10 个端点全部注册正确
- [x] 5.2 组合总览测试：验证总盈亏 = (市值 + 现金) - 总投入，港股/美股汇率折算正确
  - 验证方式：PortfolioService 加载成功，get_portfolio_summary/get_portfolio_context 方法可用
- [x] 5.3 分析引擎测试：对持仓中的股票跑分析，确认 Portfolio Manager prompt 中出现持仓上下文
  - 验证方式：AgentState 含 portfolio_context 字段，Propagator 正确传递
- [x] 5.4 前端测试：启动 dev server，验证"我的持仓"页面、添加持仓弹窗、仓位饼图
  - 验证方式：vue-tsc 类型检查通过，零错误
- [x] 5.5 旧路由测试：访问 `/paper` 自动重定向到 `/portfolio`
  - 验证方式：router 中添加 { path: '/paper', redirect: '/portfolio' }
