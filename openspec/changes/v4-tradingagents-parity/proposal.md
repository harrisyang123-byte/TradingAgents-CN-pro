# v4 对齐 TradingAgents 全量改造（v4-tradingagents-parity）

**状态**：approved by user 2026-06-13（"全做，给我狠狠的改"）
**前置**：`v4-five-forces-deep-split`（已合并）+ `v4-completion-validation-five-forces`（已合并）

---

## Why

用户深度反馈系统**对齐 TradingAgents 仅 50-60%**。看 TradingAgents 源码后核实差距：

1. **风险辩论缺失**：TA 在 trader signal 后有 aggressive/safe/neutral 3 方辩论 + risk_manager 裁判；v4 director 一人决断，**没有风险偏好对冲层**
2. **跨次记忆缺失**：TA 每个 agent 有独立 memory，跨次累积经验；v4 只有 reflection（仅对比上一版本股），**学不会跨股经验**
3. **舆情分析缺失**：TA 有 news_analyst + social_media_analyst；v4 没有舆情维度，**信息盲区**
4. **辩论字数限制**：TA 单轮无限制（实测 1500-3000 字深做）；v4 之前 ≤500 字（已取消但未重跑验证）
5. **数据使用追溯**：51 条 evidence 只有 ~17 条真被分析引用，其他堆着装样子
6. **未来推演单维**：path_scenarios 只用 PE 倍数，缺市场风格/流动性/AI 周期/β/对标矩阵/pricing power

加上之前 plan 里没做完的：
- v4_monitor.py 止损监控
- critic 接入编排（让 NEEDS_CHANGES 真拦截落盘）
- 25 只历史拼盘股的真单元跑（这次先跑核心 3 只示范）

---

## What Changes

### 新增 4 类 agent + memory 系统

1. **3 方风险辩论 agent**（破除 director 一人决断）
   - `agents/advisor/v4-stock-risk-aggressive.md`：主张追风险（attack 默认保守）
   - `agents/advisor/v4-stock-risk-safe.md`：主张守底线（attack 默认激进）
   - `agents/advisor/v4-stock-risk-neutral.md`：平衡视角（裁判前置）
   - 编排：director 给初版 verdict → 3 方风险辩论 1 轮 → director 综合最终拍板

2. **memory 长期记忆系统**（破除"单次反思"）
   - `data/v4/_memory/<agent_id>.json` schema：past_decisions / mistakes / patterns
   - bull/bear/director/critic prompt 加"读 memory"指令
   - reflection 后写 memory 入磁盘
   - **跨股、跨行业、跨次累积经验**

3. **新闻/舆情分析师**（破除信息盲区）
   - `agents/advisor/v4-stock-analyst-sentiment.md`
   - data-desk 加新闻热点 + 雪球/股吧情绪取数
   - director 多消费一份 sentiment 输出

4. **辩论字数限制取消**（已在 71bded4 完成 prompt 改动）
   - 但需重跑 002371 验证字数取消是否带来质变

### 加深 director + critic 强制要求

5. **数据使用追溯（Layer 1）**
   - evidence 加 `used_in: ["thesis", "forward_view.bear"]` 字段
   - director prompt 强制在 thesis 文中引用 evidence 关键数字
   - critic 抽查 evidence 是否被实际使用，unused>50% 提改进
   - 前端 Step 1 显示 used/unused 计数

6. **forward_view 多维推演（Layer 3）**
   - 加 6 字段：market_regime / liquidity_environment / industry_cycle_phase / systematic_risk_beta / comparable_matrix / pricing_power_analysis
   - critic 必查这 6 维是否齐全
   - 前端 Step 4 director 拍板下展示

### 工程化收口

7. **critic 接入编排**：v4_unit_cli.py write 拦截 NEEDS_CHANGES，迫使 director 迭代后才能落盘
8. **v4_monitor.py 止损监控**：价格型自动（AKShare 跌破阈值发警）+ 基本面型定期人工核查提示

### 全流程验证

9. **重跑 002371 v3**：含全部新结构（5+1 + 6 轮辩论无字数限制 + 3 方风险 + sentiment + memory + 6 维 forward_view + 数据追溯）
10. **跑恒瑞 600276 v2**：换行业（创新药）测可移植性，验证 sentiment（医保谈判舆情敏感）+ memory（积累医药行业经验）
11. **跑中际旭创 300308 v8**：推翻 v7 拼盘版，CPO 替代威胁敏感性矩阵 + 客户集中度 buyer 风险

---

## Impact

### 新增文件
- 4 个 agent prompt（v4-stock-risk-{aggressive,safe,neutral}.md + v4-stock-analyst-sentiment.md）
- `data/v4/_memory/<agent>.json` 目录
- `scripts/v4_monitor.py`
- `planning/v4/tradingagents-parity-report.md`（最终汇总）

### 修改文件
- `agents/advisor/v4-stock-director.md`（消费 risk 辩论 + sentiment + memory）
- `agents/advisor/v4-stock-bull.md` / `v4-stock-bear.md`（读 memory）
- `agents/advisor/v4-investor-critic.md`（已有深度铁律，再加 risk 辩论是否充分 + memory 是否在用 抽查）
- `agents/advisor/v4-data-desk.md`（加 sentiment 取数协议）
- `app/services/v4/v4_query.py`（透传新字段：sentiment / risk_debate / forward_view 6 维 / evidence used_in）
- `frontend/src/api/portfolioV4.ts` + `StockDetailTab.vue`（展示新字段）
- `scripts/v4_unit_cli.py`（critic 拦截）

### 三只标的真单元
- `data/v4/stocks/002371.json` v3（含全部新结构）
- `data/v4/stocks/600276.json` v2
- `data/v4/stocks/300308.json` v8

### 自动归档
- `data/v4/_archive/stocks/{002371,600276,300308}/v{N}_<日期>.json`

### 用户验证路径
- `git pull` → 看新前端 → 看 3 只股深度跃迁
- `python scripts/archive_v4.py diff stock:002371 --from v2 --to v3` 看变化

---

## Tasks（执行清单，逐项打钩）

详见 `tasks.md`

---

## Spec Deltas（变更点）

详见 `specs/v4-stock-detail/spec.md`（新增字段 schema）

---

## 完成判定

- [ ] 4 个新 agent prompt + memory schema 落地
- [ ] director/critic/bull/bear/data-desk prompt 全部更新
- [ ] 后端 build_stock_detail 透传所有新字段
- [ ] 前端 StockDetailTab 展示新字段（sentiment/risk_debate/forward_view 6 维/used_in）
- [ ] 002371 v3 + 600276 v2 + 300308 v8 全部跑完落盘
- [ ] critic 接入编排（NEEDS_CHANGES 拦截）
- [ ] v4_monitor.py 写好（沙箱无外网，仅写 schema + 待生产环境验证）
- [ ] 全部提交 + 推送 + 写最终汇总报告 `tradingagents-parity-report.md`
