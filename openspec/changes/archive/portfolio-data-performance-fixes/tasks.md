# Tasks: Portfolio Data Performance Fixes

## Slice 1: 后端数据管道并行化

**已实现。涉及文件**：
- `app/services/portfolio_service.py` — `_fetch_position_detail()` 并行方法 + `_get_position_name` yfinance 回退

**验证**：
- [x] GET /api/portfolio/summary 对 35 个持仓响应 < 15s
- [x] HK 09992 显示 "Pop Mart International Group Limited"，01810 显示 "Xiaomi Corporation"
- [x] 单数据源超时不阻塞页面渲染

## Slice 2: HK 股数据修复

**已实现。涉及文件**：
- `app/services/foreign_stock_service.py` — 添加 `'yfinance'` handler 别名

**验证**：
- [x] HK 09992 last_price = 150.5
- [x] HK 01810 last_price = 30.0

## Slice 3: 行业分类

**已实现。涉及文件**：
- `app/routers/paper.py` — `get_portfolio_overview()` 新增批量行业查询 + 基金名称推断 + position_names
- `app/services/industry_classifier.py` — 提取 `classify_holdings_industries()` 工具函数

**验证**：
- [x] `paper.ts` 新增 `position_names` 接口字段
- [x] GET /api/portfolio/overview 返回 18+ 行业，无"未分类"
- [x] 基金正确分类：债券、AI、医药健康等

## Slice 4: 前端 UI 修复

**已实现。涉及文件**：
- `frontend/src/views/PaperTrading/index.vue` — P&L 切换、排序、饼图 → 柱状图
- `frontend/src/views/Portfolio/Overview.vue` — 名称展示、弹窗修复

**验证**：
- [x] 盈亏贡献默认 top 10 + 展开全部按钮
- [x] 持仓明细表头可排序（市值/仓位/盈亏/盈亏率）
- [x] 饼图替换为横向柱状图（top 5 + 其他聚合）
- [x] 概览页行业矩阵显示中文名称标签
- [x] 历史建议卡片点击打开弹窗

## Slice 5: 持仓标的可读性（Issue 1 追加）

**已实现。涉及文件**：
- `frontend/src/views/PaperTrading/index.vue` — 合并代码+名称+市场为单列"标的"

**验证**：
- [x] 名称为主（可点击链接），代码+市场标签为副（灰色小字）
- [x] 页面 200 正常加载

## Slice 6: CN 股实时价格（Issue 2 追加）

**已实现。涉及文件**：
- `app/services/portfolio_service.py` — `_refresh_cn_market_quotes()` 批量 AKShare 刷新 + `get_portfolio_summary()` 调用

**验证**：
- [x] CN 持仓加载时调一次 `ak.stock_zh_a_spot_em()` 批量刷新
- [x] 603663 三祥新材 last_price 返回实时行情
- [x] 缓存命中时零额外开销
