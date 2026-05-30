# Tasks: Fund → Tier 2 Data Flow Fix

## Slice 1: PE 管道跳过非股票

- [x] 1.1 `pe_percentile.py`: `enrich_price_context` 中跳过 `instrument_type` 为 fund/etf 的持仓
- [x] 1.2 验证：混合持仓调用，基金返回 `non_stock_instrument`，不调 API

## Slice 2: 修复 _prepare_tier1_reports

- [x] 2.1 `portfolio_advisor_service.py`: 主查询切到 `analysis_reports`，提取基金特有字段
- [x] 2.2 保留 `analysis_results` fallback
- [x] 2.3 验证：query 返回正确的 stock/fund 字段

## Slice 3: L3 Agent 基金上下文

- [x] 3.1 `analyst.py`: position_briefs 中提取基金报告摘要，prompt 加基金专项评估
- [x] 3.2 `strategist.py`: 基金仓位汇总，prompt 加基金组合评估
- [x] 3.3 验证：无基金持仓时 prompt 不变（回归）

## Slice 4: CIO 基金决策标准

- [x] 4.1 `cio.py`: 两个 prompt 注入基金决策准则
- [x] 4.2 验证：CIO prompt 包含基金 HOLD/REDEEM/REPLACE 条件

## Verification

- [x] 5.1 Python import + type-check 通过
- [x] 5.2 纯股票回归：prompt 输出与当前一致（fund_section=""，prompt 不变）
- [x] 5.3 基金持仓：fund-specific 字段出现在各 agent prompt 中
