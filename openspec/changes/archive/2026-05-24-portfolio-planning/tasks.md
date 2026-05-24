# Tasks: 持仓组合规划

## Slice 1: 数据模型 & 基础设施

- [ ] 1.1 创建 `industry_coverage` 集合索引（MongoDB migration）
- [ ] 1.2 `app/services/portfolio_advisor_service.py`: 双写 `analysis_reports`
- [ ] 1.3 `app/services/progress/tracker.py`: Redis PubSub publish 打通
- [ ] 1.4 验证: Python import + MongoDB 索引确认

## Slice 2: 两阶段 Advisor Graph

- [ ] 2.1 `tradingagents/graph/advisor_graph.py`: 新增 `propagate_l1_plan()` 方法
- [ ] 2.2 `tradingagents/graph/advisor_graph.py`: `propagate_advice()` 接受 `selected_industries`
- [ ] 2.3 `tradingagents/graph/advisor_graph.py`: progress_callback 集成 + Redis publish
- [ ] 2.4 验证: L1 独立执行返回正确 industries 结构

## Slice 3: 后端 API

- [ ] 3.1 新建 `app/routers/portfolio_analysis.py`: plan/execute/status 端点
- [ ] 3.2 扩展 `app/routers/sse.py`: `/api/sse/portfolio/{task_id}` 端点
- [ ] 3.3 扩展 `app/routers/paper.py`: `GET /api/portfolio/overview` 聚合端点
- [ ] 3.4 扩展 `app/routers/reports.py`: report_type 筛选
- [ ] 3.5 注册路由到 `app/main.py`
- [ ] 3.6 验证: curl 各端点返回正确数据

## Slice 4: 前端 — 路由 + 导航

- [ ] 4.1 `frontend/src/router/index.ts`: `/portfolio` 改为嵌套路由（holdings/analysis/overview）
- [ ] 4.2 `frontend/src/components/layout/SidebarMenu.vue`: "我的持仓" 改为 el-sub-menu
- [ ] 4.3 `frontend/src/views/PaperTrading/index.vue`: 删除"组合分析"按钮
- [ ] 4.4 验证: npm type-check + 页面路由跳转正常

## Slice 5: 前端 — 分析页

- [ ] 5.1 新建 `frontend/src/views/Portfolio/Analysis.vue`: 页面框架 + 状态机
- [ ] 5.2 Phase 1: SSE 流式展示 + 推荐行业计划表格
- [ ] 5.3 Phase 2: 行业确认 + L2-L4 流式执行 + 结果展示
- [ ] 5.4 新建/扩展 `frontend/src/api/portfolio.ts`: API 调用封装
- [ ] 5.5 验证: npm type-check + 页面渲染

## Slice 6: 前端 — 总揽页

- [ ] 6.1 新建 `frontend/src/views/Portfolio/Overview.vue`: 行业覆盖矩阵
- [ ] 6.2 历史建议列表 + 展开详情
- [ ] 6.3 验证: npm type-check + 矩阵数据正确

## Slice 7: 前端 — 报告页集成

- [ ] 7.1 `frontend/src/views/Reports/index.vue`: report_type 筛选下拉
- [ ] 7.2 `frontend/src/views/Reports/ReportDetail.vue`: portfolio 类型适配
- [ ] 7.3 验证: npm type-check + 筛选功能

## Slice 8: 验证

- [ ] 8.1 Python import + type-check 通过
- [ ] 8.2 纯股票回归：prompt 输出不变
- [ ] 8.3 基金持仓：fund-specific 字段正常
- [ ] 8.4 E2E: 完整分析流程 → 总揽矩阵 → 报告筛选
