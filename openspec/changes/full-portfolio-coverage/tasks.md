# Tasks: Full Portfolio Coverage

## Slice 1: 行业分类工具函数提取

- [x] 新建 `app/services/industry_classifier.py`，从 `paper.py` 提取 `classify_holdings_industries()`
- [x] 修改 `paper.py` 调用新函数，保持概览页行为不变
- [x] 验证：GET /api/portfolio/overview 返回行业分类结果不变

## Slice 2: L1 接口改造 + industry_coverage 写入

- [x] `PlanRequest` 加 `goal` 字段
- [x] `_execute_l1()` 调用 `classify_holdings_industries()` 生成持仓行业列表
- [x] 持仓行业列表 + goal 注入 `propagate_l1_plan()`
- [x] L1 完成后全量写入 `industry_coverage`（status=completed, depth=light/deep）
- [x] 移除 `planned` 状态写入逻辑
- [x] 验证：curl POST /api/portfolio/analysis/plan 返回全量持仓行业

## Slice 3: Agent Prompt 重写

- [x] `market_strategist.py`：Prompt 改为持仓行业列表驱动 + depth 输出
- [x] `contrarian.py`：只对 depth=deep 行业质疑
- [x] `macro_judge.py`：分层裁决（light 采信 / deep 完整裁决）
- [x] 保留 `_parse_industries()` 容错逻辑

## Slice 4: AdvisorGraph + States

- [x] `advisor_states.py`：加 `portfolio_industries` + `user_goal` 字段
- [x] `advisor_graph.py`：`propagate_l1_plan()` 接收新参数，注入 init_state

## Slice 5: 前端 Analysis.vue

- [x] idle 状态加 goal 输入框
- [x] `startL1Plan()` 传 goal → API
- [x] plan_ready 状态区分持仓行业（必选） vs AI 推荐（可选）
- [x] 视觉区分：不同边框色/标签

## Slice 6: E2E 验证

- [x] 触发分析（带 goal）→ 确认 L1 覆盖所有持仓行业
- [x] 确认 industry_coverage 一次全量写入
- [x] 确认概览页覆盖率 = 100%（无 "never" 状态）
- [x] 确认深辩行业有详细推理，轻量行业有 go/nogo
