# Tasks — v4 AKShare 全量重跑

## 前置
- [ ] 0. stock_source 价格取数走 stock_zh_a_hist(verified 收盘价)

## 阶段 A — 基金方式改造
- [ ] A1. v4_classifier 基金二分逻辑(主题基金→行业标的 / 宽基→大类底仓)
- [ ] A2. 基金持仓 akshare 联网查(fund_portfolio_hold_em)定主题行业
- [ ] A3. collect_v4 + 前端展示(行业内推荐含公司+基金)

## 阶段 B — 行业层重跑 ×8
- [ ] B1. 人工智能算力 / B2. 半导体 / B3. 创新药 / B4. 有色资源
- [ ] B5. 电力公用事业 / B6. 互联网平台 / B7. 消费电子家电 / B8. 新能源车
- 每个: verified 行业ROIC均值+景气+TAM+瓶颈 → go/nogo + 行业内推荐(公司+基金) + critic ACCEPT

## 阶段 C — 大类层重跑 ×8
- [ ] C1-C8: equity/fixed_income/cash/commodity/precious_metal/real_estate/alternative/unclassified

## 阶段 D — 配比重跑
- [ ] D1. alloc:equity_industries(行业间)
- [ ] D2. alloc:industry ×8(行业内,含基金)
- [ ] D3. alloc:portfolio(大类)

## 阶段 E — plan:* ×6
- [ ] E1-E6: fixed_income/cash/commodity/precious_metal/real_estate/alternative

## 阶段 F — 收尾
- [ ] F1. WACC 行业化(stock_source/director)
- [ ] F2. 个股 stance 全面重审(verified ROIC)
- [ ] F3. 辩证横向终审 + 最终 commit + change 归档
