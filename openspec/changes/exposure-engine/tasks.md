# Exposure Engine — 实现任务

## Task 1: ExposureService 核心类
- [x] 创建 `app/services/exposure_service.py`
- [x] 实现 `compute(user_id)` 主方法
- [x] 实现 `_split_positions()` → stock/fund 分流
- [x] 实现 `_resolve_fund_holdings()` → 调用 FundService.get_top_holdings
- [x] 实现 `_merge_exposures()` → 同股票权重合并
- [x] 实现 `_compute_concentration()` → HHI + top-N
- [x] 实现 `_build_summary()` → 文字摘要
- 验证：import + 基本类型检查 ✅

## Task 2: 集成到组合顾问管线
- [x] 在 `portfolio_advisor_service.py::_execute_advice()` 中调用 ExposureService
- [x] 将敞口矩阵格式化为 context message 注入 AdvisorGraph
- [x] 更新 `advisor_graph.py` → exposure_context + exposure_matrix 参数
- 验证：advisor graph 初始消息包含敞口数据 ✅

## Task 3: 数据过期检测
- [x] 实现 `_check_staleness()` → 检查基金持仓缓存日期
- [x] 在敞口矩阵 summary 中标注 stale 基金
- [x] stale 不阻断计算，仅警告
- 验证：模拟过期数据的矩阵输出 ✅

## Task 4: P0-1c 架构调整（收尾）
- [x] 基金分析从独立 pipeline 降级为数据源（重仓股拆解 → 敞口引擎）
- [x] 更新记忆：`project-tradingagents-cn.md`（P0 进度已同步）
- [x] 确认基金 Tier 1 分析仍保留（敞口引擎用它的持仓拆解结果）
- 验证：文档一致性检查 ✅
