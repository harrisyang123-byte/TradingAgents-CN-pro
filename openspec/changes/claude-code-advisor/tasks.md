# Claude Code Advisor — 实现任务

## Slice 1: 数据收集层修复（无 LLM 调用）
<!-- 修复所有数据基底，让后续 Agent 有数据可读 -->

1. [ ] 修复 `_prepare_tier1_reports` — OR 多字段匹配 `stock_symbol` + `stock_code`，排除 `?` 占位符
2. [ ] 实现 `get_portfolio_summary` 中 `position.industry` 字段填充 — 调用 `classify_batch_with_llm`
3. [ ] 实现基金穿透数据采集 — 调用 AKShare 取季报重仓股 → 构建 `fund_holdings_report`
4. [ ] 实现市场温度数据收集 — 北向、涨跌比、融资余额、千股千评 → `market_temperature.json`

## Slice 2: 交叉验证引擎（Python 规则，无 LLM）
<!-- 独立的验证模块，不依赖任何 Agent -->

5. [ ] 实现 `cross_validate()` 函数 — Tier1 矛盾检测
6. [ ] 实现 PE 分位 vs 建议一致性检查
7. [ ] 实现敞口重叠识别
8. [ ] 实现黑天鹅预警检测（3 规则）
9. [ ] 实现情绪 vs 基本面方向冲突检测

## Slice 3: L1 行业哨兵部（3 Agent + 辩论）
<!-- 第一个完整的子 Agent 层 -->

10. [ ] 编写 `PROMPT_L1_STRATEGIST` — 数据驱动判定 + 量化输出 + 情绪修正
11. [ ] 编写 `PROMPT_L1_CONTRARIAN` — 看空立场 + 调工具验证
12. [ ] 编写 `PROMPT_L1_JUDGE` — 综合裁定（超配/标配/低配/零配 + ≥5方向 + 200字/方向）
13. [ ] 在 `cli/claude_advisor.py` 中编排 L1 辩论循环（max 2 轮）
14. [ ] E2E 验证：L1 产出 ≥5 Go 方向 + 每方向 ≥200 字 + 量化引用

## Slice 4: L2 公司侦探部（1 Agent + 交叉验证）
<!-- Scout 能力补全：财务引用 + 中市值 + 价格区间 + L1 连接 -->

15. [ ] 编写 `PROMPT_L2_SCOUT` — 强制财务数据引用 + 中市值覆盖 + 价格区间模板 + L1 行业上下文
16. [ ] 在 `cli/claude_advisor.py` 中注入 L1 裁判输出 + 持仓行业分布数据到 Scout 输入
17. [ ] E2E 验证：候选池 ≥5 只 + ≥30% 中市值 + 每只含 financial_data + pricing_range

## Slice 5: L3 组合诊察部（2 Agent + 辩论）
<!-- 分析师 + 策略师贯通 -->

18. [ ] 编写 `PROMPT_L3_ANALYST` — 逐只安全边际（含 Tier1 引用 + PE + 矛盾标注）
19. [ ] 编写 `PROMPT_L3_STRATEGIST` — 组合诊断报告（集中度 + 一致性风险 + 隐形暴露 + 情绪一致性）
20. [ ] 在 `cli/claude_advisor.py` 中编排 L3 辩论循环（分析师 ↔ 策略师，max 2 轮）
21. [ ] E2E 验证：策略师输出含 ≥1 一致性风险标注 + ≥1 隐形暴露汇总

## Slice 6: L4 CIO 办公室（3 Agent + 辩论）
<!-- CIO + 风控 + CIO终裁 -->

22. [ ] 编写 `PROMPT_L4_CIO` — 敞口诊断 + 行业配置 + 资金分配方案 + 情绪水温参考
23. [ ] 编写 `PROMPT_L4_RISK` — 集中度/流动性/Tier1 验证/黑天鹅触发
24. [ ] 编写 `PROMPT_L4_CIO_FINAL` — 冲突处理 + 最终处方
25. [ ] 在 `cli/claude_advisor.py` 中编排 L4 辩论循环
26. [ ] E2E 验证：处方覆盖全部持仓 + 敞口诊断段落 + 资金分配方案 + 黑天鹅预警

## Slice 7: 主控脚本 + 保存
<!-- 串联全部 + MongoDB 写入 -->

27. [ ] 实现 `cli/claude_advisor.py` 主流程编排（数据收集 → L1 → L2 → 交叉验证 → L3 → L4 → MongoDB）
28. [ ] 实现命令行参数：`--user-id`（必需）、`--verbose`（打印每步输出）、`--skip-data`（复用缓存）
29. [ ] 实现保存逻辑：写入 MongoDB `portfolio_advice`，source='claude-code-v3'
30. [ ] 全链路 E2E 验证：`python cli/claude_advisor.py run --user-id 6a094caea814b57d3357fa0b` → MongoDB + 前端可用
