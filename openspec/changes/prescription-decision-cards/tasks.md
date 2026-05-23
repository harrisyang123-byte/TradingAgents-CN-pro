# Tasks: Prescription Decision Cards

## Slice 1: PE Percentile Data Pipeline (后端数据管道)

- [x] 1.1 创建 `tradingagents/dataflows/pe_percentile.py`：`compute_pe_context()` 统一接口
- [x] 1.2 A 股实现：扩展 BaoStock `query_history_k_data_plus` 日期范围，计算每日 PE 分位
- [x] 1.3 港股实现：利用 AKShare 年度 EPS_TTM + 每日股价计算 PE 分位
- [x] 1.4 美股实现：利用 yfinance 年度 EPS + 5 年价格历史计算 PE 分位
- [x] 1.5 在 `advisor_graph.py` 中创建 `enrich_price_data_node`，插入 L3→L4 之间
- [x] 1.6 `advisor_states.py` 新增 `price_context` 字段
- [x] 1.7 Edge case 处理：新股/亏损/数据源不可用的降级逻辑

**验证**: 跑一次组合顾问分析，检查日志中 `price_context` 输出包含正确的 PE 分位数据

## Slice 2: CIO Prompt Enhancement (处方字段扩展)

- [x] 2.1 CIO prompt 新增 `price_context` 数据注入段落
- [x] 2.2 CIO prompt 新增 7 字段输出指令（l1/l2_context, suggested_price, max_loss_pct, five_year_view, bias_check, priority）
- [x] 2.3 `_parse_prescription()` 扩展解析，新字段作为可选附加（向后兼容）
- [x] 2.4 CIO prompt 新增 l1/l2_context 提取策略（从裁判报告文本中提取）
- [x] 2.5 `portfolio_advisor_service.py` 保存新字段到数据库（无需改动，自动流转）

**验证**: 跑一次组合顾问分析，检查返回的 prescription JSON 包含全部 7 个新字段

## Slice 3: Frontend Decision Cards (前端卡片流)

- [x] 3.1 `paper.ts` 类型扩展：`AdviceItem` 新增 7 个可选字段
- [x] 3.2 创建 `DecisionCard.vue` 组件：header + l1/l2 collapsible + PE bar + risk row
- [x] 3.3 实现 PE 分位进度条（绿/黄/红三色）
- [x] 3.4 实现 priority 排序 + 颜色编码（urgent=红, important=橙, optional=灰）
- [x] 3.5 `PaperTrading/index.vue`：`el-table` → 纵向卡片流
- [x] 3.6 边缘 case 处理：缺失字段显示 "—"，PE 分位不可用时隐藏进度条

**验证**: 打开 PaperTrading 抽屉，确认卡片流正确渲染，PE 分位进度条显示正确，卡片可展开/收起

## Verification

- [x] 4.1 回归测试：Python import + 向后兼容验证通过，109 个测试收集错误为预存环境问题
- [ ] 4.2 端到端：组合顾问完整流程跑通，卡片流在抽屉中正确展示
