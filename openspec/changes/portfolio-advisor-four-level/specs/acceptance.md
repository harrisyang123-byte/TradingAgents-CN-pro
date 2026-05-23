# Acceptance Specs: Portfolio Advisor Four-Level

## Spec 1: L1 Market Intelligence

- [ ] 1.1 Market Strategist 成功调用 `get_industry_rankings("cn")` / `("hk")` / `("us")` 获取三市场行业排名
- [ ] 1.2 Contrarian 对 Strategist 的行业推荐至少提出一个实质性风险面挑战
- [ ] 1.3 Macro Judge 输出 Go/NoGo 裁定 + 行业生命周期标注
- [ ] 1.4 辩论轮数达到 `market_debate_rounds` (默认2) 后流转到 Macro Judge

## Spec 2: L2 Stock Screening

- [ ] 2.1 Scout 成功调用工具获取行业成分股 + 公司概况 + 财务摘要 + 行情
- [ ] 2.2 Scout 推荐标的附带巴芒四层过滤理由（看懂生意/护城河/管理层/价格合理）
- [ ] 2.3 Stock Contrarian 对每只推荐标的至少提出一个风险挑战
- [ ] 2.4 Stock Judge 最终裁定结果含推荐/观察/淘汰三级分类

## Spec 3: L3 Portfolio Construction (Regression)

- [ ] 3.1 现有功能不受影响：Analyst/Strategist/Scout 独立评估正常输出
- [ ] 3.2 L3 辩论记录在 AdvisorDebateState.history 中正常累计
- [ ] 3.3 L3 Agent 的 prompt 中能看到 L1/L2 数据（行业方向 + 候选标的）

## Spec 4: L4 Final Prescription

- [ ] 4.1 CIO 处方初稿生成正常，prescription 数组可解析
- [ ] 4.2 Risk Director 对处方提出风险审查意见
- [ ] 4.3 CIO 终裁处方 ≤ 8 条（max_prescription_items）
- [ ] 4.4 CIO verdict 中包含 5年视角 + 市场先生标注

## Spec 5: Degradation

- [ ] 5.1 AKShare 行业接口返回空时，L1/L2 标注"无实时数据"但不崩溃
- [ ] 5.2 yfinance 不可用时，港股/美股降级，A股继续正常
- [ ] 5.3 全部数据源不可用时，纯 LLM 常识驱动 + 全局标注

## Spec 6: Frontend

- [ ] 6.1 抽屉中 L1 市场扫描 section 正常渲染
- [ ] 6.2 抽屉中 L2 候选标的 section 正常渲染
- [ ] 6.3 抽屉中 L4 风险审查 section 正常渲染
- [ ] 6.4 现有 section（分析师/策略师/侦察兵/辩论记录）不受影响
- [ ] 6.5 新 section 在无数据时通过 `v-if` 自动隐藏

## Edge Case: Multi-Market Partial Failure

- [ ] E.1 模拟 yfinance 超时 → 港股美股 section 标注 fallback，A股不受影响
- [ ] E.2 模拟 AKShare + yfinance 全挂 → 全局标注"数据不可用"，分析正常完成
