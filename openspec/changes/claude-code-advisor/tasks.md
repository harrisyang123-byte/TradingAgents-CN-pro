# Claude Code Advisor — 实现任务

## Slice 1: 数据收集层修复（无 LLM 调用）
<!-- 修复所有数据基底，让后续 Agent 有数据可读 -->

1. [x] 修复 `_prepare_tier1_reports` — OR 多字段匹配 `stock_symbol` + `stock_code`，排除 `?` 占位符
2. [x] 实现 `get_portfolio_summary` 中 `position.industry` 字段填充 → `industry_buckets.classify`
3. [x] 实现基金穿透数据采集 — ExposureService.compute() 已有覆盖基金穿透
4. [x] 实现市场温度数据收集 — `cli/advisor/data_collector.py` → `collect_market_temp()`

## Slice 2: 交叉验证引擎

5. [x] 实现 `cross_validate()` 函数 — `cli/advisor/cross_validator.py` → `cross_validate_all()`
6. [x] 实现 PE 分位 vs 建议一致性检查 — `detect_pe_vs_advice()`
7. [x] 实现敞口重叠识别 — `detect_overlaps()`
8. [x] 实现黑天鹅预警检测 — `detect_black_swan()`
9. [x] 实现情绪 vs 基本面方向冲突检测 — `detect_sentiment_vs_fundamentals()`

## Slice 3: L1 行业哨兵部

10. [x] 编写 `PROMPT_L1_STRATEGIST` — `cli/advisor/prompts.py`
11. [x] 编写 `PROMPT_L1_CONTRARIAN` — `cli/advisor/prompts.py`
12. [x] 编写 `PROMPT_L1_JUDGE` — `cli/advisor/prompts.py`
13. [x] 在 `cli/claude_advisor.py` 中编排 L1 辩论循环
14. [ ] E2E 验证：L1 产出 ≥5 Go 方向 + 每方向 ≥200 字 + 量化引用

## Slice 4: L2 公司侦探部

15. [x] 编写 `PROMPT_L2_SCOUT` — `cli/advisor/prompts.py`
16. [x] 在 `cli/claude_advisor.py` 中注入 L1 裁判输出 + 持仓行业分布数据到 Scout 输入
17. [ ] E2E 验证：候选池 ≥5 只 + ≥30% 中市值 + 每只含 financial_data + pricing_range

## Slice 5: L3 组合诊察部

18. [x] 编写 `PROMPT_L3_ANALYST` — `cli/advisor/prompts.py`
19. [x] 编写 `PROMPT_L3_STRATEGIST` — `cli/advisor/prompts.py`
20. [x] 在 `cli/claude_advisor.py` 中编排 L3 辩论循环
21. [ ] E2E 验证：策略师输出含 ≥1 一致性风险标注 + ≥1 隐形暴露汇总

## Slice 6: L4 CIO 办公室

22. [x] 编写 `PROMPT_L4_CIO` — `cli/advisor/prompts.py`
23. [x] 编写 `PROMPT_L4_RISK` — `cli/advisor/prompts.py`
24. [x] 编写 `PROMPT_L4_CIO_FINAL` — `cli/advisor/prompts.py`
25. [x] 在 `cli/claude_advisor.py` 中编排 L4 辩论循环
26. [ ] E2E 验证：处方覆盖全部持仓 + 敞口诊断段落 + 资金分配方案 + 黑天鹅预警

## Slice 7: 主控脚本 + 保存

27. [x] 实现 `cli/claude_advisor.py` 主流程编排
28. [x] 实现命令行参数：`--user-id`、`--verbose`、`--skip-data`
29. [x] 实现保存逻辑：MongoDB `portfolio_advice`，source='claude-code-v3'
30. [ ] 全链路 E2E 验证
