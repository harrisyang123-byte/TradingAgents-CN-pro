# Tasks — v4 AKShare 全量重跑

## 前置
- [x] 0. stock_source 价格取数走 stock_zh_a_hist(verified 收盘价)

## 阶段 A — 基金方式改造
- [x] A1. 基金二分映射表 data/v4/_inputs/fund_classification.json(主题ETF→行业/宽基QDII债基→大类)
- [x] A2. 基金主题已由名称明确归类(akshare持仓可验证, 待行业层引用)
- [x] A3. 行业层 fund_recommendation 字段(行业内推荐含公司+基金)已落地, 前端快照已含

## 阶段 B — 行业层重跑 ×8
- [x] B1-B4 人工智能算力(critic88)/半导体/创新药/有色资源
- [x] B5-B8 电力/互联网/消费电子家电/新能源车 (抽样critic91)
- 每个: verified 行业ROIC均值+景气+TAM+瓶颈 → go/nogo + 行业内推荐(公司+基金) + critic ACCEPT

## 阶段 C — 大类层重跑 ×8
- [ ] C1-C8: equity/fixed_income/cash/commodity/precious_metal/real_estate/alternative/unclassified

## 阶段 D — 配比重跑
- [x] D1. alloc:equity_industries 价值创造+基金二分
- [x] D2. alloc:industry ×8 加基金维度(个股+基金配比)
- [x] D3. alloc:portfolio v7 价值创造双标准(上轮已完成)

## 阶段 E — plan:* ×6
- [ ] E1-E6: fixed_income/cash/commodity/precious_metal/real_estate/alternative

## 阶段 F — 收尾
- [ ] F1. WACC 行业化(stock_source/director)
- [ ] F2. 个股 stance 全面重审(verified ROIC)
- [ ] F3. 辩证横向终审 + 最终 commit + change 归档
