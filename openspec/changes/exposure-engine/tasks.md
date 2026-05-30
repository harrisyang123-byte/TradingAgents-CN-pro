# Exposure Engine — 实现任务

## Task 1: ExposureService 核心类
- [ ] 创建 `app/services/exposure_service.py`
- [ ] 实现 `compute(user_id)` 主方法
- [ ] 实现 `_split_positions()` → stock/fund 分流
- [ ] 实现 `_resolve_fund_holdings()` → 调用 FundService.get_top_holdings
- [ ] 实现 `_merge_exposures()` → 同股票权重合并
- [ ] 实现 `_compute_concentration()` → HHI + top-N
- [ ] 实现 `_build_summary()` → 文字摘要
- 验证：import + 基本类型检查

## Task 2: 集成到组合顾问管线
- [ ] 在 `portfolio_advisor_service.py::_execute_advice()` 中调用 ExposureService
- [ ] 将敞口矩阵格式化为 context message 注入 AdvisorGraph
- [ ] 更新 `advisor_graph.py::_format_tier1_report_context` → 也接收 exposure context
- 验证：advisor graph 初始消息包含敞口数据

## Task 3: 数据过期检测
- [ ] 实现 `_check_staleness()` → 检查基金持仓缓存日期
- [ ] 在敞口矩阵 summary 中标注 stale 基金
- [ ] stale 不阻断计算，仅警告
- 验证：模拟过期数据的矩阵输出

## Task 4: P0-1c 架构调整（收尾）
- [ ] 更新 `docs/wiki/portfolio-advisor-architecture.md` → 标注基金分析从 pipeline 降级为数据源
- [ ] 更新记忆：`project-tradingagents-cn.md` + `full-portfolio-advice-blueprint.md`
- [ ] 确认基金 Tier 1 分析仍保留（敞口引擎用它的持仓拆解结果）
- 验证：文档一致性检查
