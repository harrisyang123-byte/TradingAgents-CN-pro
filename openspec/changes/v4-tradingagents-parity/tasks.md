# Tasks — v4-tradingagents-parity

## 阶段 1：核心架构（Agent + Memory）

- [ ] T2.1 创建 `agents/advisor/v4-stock-risk-aggressive.md`（攻击保守立场，主张追风险）
- [ ] T2.2 创建 `agents/advisor/v4-stock-risk-safe.md`（攻击激进立场，主张守底线）
- [ ] T2.3 创建 `agents/advisor/v4-stock-risk-neutral.md`（平衡视角，3 方拍最终板前的协调）
- [ ] T2.4 director prompt 加"消费 3 方风险辩论"指令（risk_debate_summary 字段）
- [ ] T3.1 创建 `data/v4/_memory/` 目录 + 设计 memory schema（past_decisions/mistakes/patterns）
- [ ] T3.2 编写 memory 读写工具函数（`scripts/v4_memory.py`）
- [ ] T3.3 director/bull/bear/critic prompt 加"开辩前读 memory + 结束写 memory"
- [ ] T3.4 更新 v4_unit_cli.py write 时调用 memory 写入
- [ ] T4.1 创建 `agents/advisor/v4-stock-analyst-sentiment.md`（新闻+雪球/股吧舆情）
- [ ] T4.2 v4-data-desk.md 加新闻/舆情取数协议
- [ ] T4.3 director prompt 加"消费 sentiment 输出"

## 阶段 2：数据深度强化

- [ ] T5.1 evidence schema 加 `used_in: string[]` 字段
- [ ] T5.2 director prompt 加"thesis/forward_view/sell_discipline 文中必须引用 evidence 关键数字"
- [ ] T5.3 critic prompt 加"抽查 evidence 是否被实际使用,unused>50% 提改进意见"（已在 71bded4 部分完成 6.5）
- [ ] T5.4 build_stock_detail 透传 used_in 字段
- [ ] T5.5 前端 Step 1 evidence 列表显示"used N 处"标签 + 总览栏显示 unused 比例
- [ ] T6.1 forward_view schema 加 6 字段（market_regime/liquidity/cycle/β/comparable_matrix/pricing_power）
- [ ] T6.2 director prompt 强制输出这 6 字段（已在 71bded4 完成 10.4）
- [ ] T6.3 critic prompt 必查这 6 字段（已在 71bded4 完成 6.4）
- [ ] T6.4 build_stock_detail 透传 + frontend 类型加 ForwardView6 接口
- [ ] T6.5 前端 Step 4 director 卡内展示 6 维卡片
- [ ] T6.6 002371 payload 补 6 维示例数据

## 阶段 3：工程化收口

- [ ] T11.1 改 v4_unit_cli.py write：调用 critic 评审，NEEDS_CHANGES 时返回 status=red 不落盘 + 报错
- [ ] T11.2 加 `--skip-critic` flag（紧急情况绕过）
- [ ] T11.3 写 critic 调用 helper（spawn subagent 评 ACCEPT/NEEDS_CHANGES）
- [ ] T10.1 创建 `scripts/v4_monitor.py`（价格型监控：AKShare 跌破阈值发 markdown 警报）
- [ ] T10.2 加基本面型监控（季度财报关键指标 vs trigger_monitor 阈值核对）
- [ ] T10.3 在 sell_discipline 字段里把"trigger 阈值"结构化成 `monitor_rules: [{type, threshold, action}]`

## 阶段 4：重跑 3 标的（深度验证）

- [ ] T7.1 准备 002371 完整 inputs 包（含 sentiment 数据 + memory 历史）
- [ ] T7.2 spawn 5+1 五力（无字数限制 + 加 memory）
- [ ] T7.3 spawn bull/bear 6 轮辩论（深做版）
- [ ] T7.4 spawn 3 方风险辩论
- [ ] T7.5 spawn sentiment 分析
- [ ] T7.6 director 综合所有 + 输出 6 维 forward_view + 写 memory
- [ ] T7.7 critic 评审（必须 ACCEPT 才能落盘）
- [ ] T7.8 落盘 002371 v3 + 自动归档 v2

- [ ] T8.1-T8.8 同上跑恒瑞 600276 v2

- [ ] T9.1-T9.8 同上跑中际旭创 300308 v8

## 阶段 5：收官

- [ ] T12.1 build_snapshot_v4 重生成快照 44 文件
- [ ] T12.2 vue-tsc 类型检查全过
- [ ] T12.3 写 `planning/v4/tradingagents-parity-report.md` 总结对齐度提升 + 3 标的对比 + 已知局限
- [ ] T12.4 git add + commit + push 最终一次
- [ ] T12.5 更新 `planning/v4/rerun-memory.md` 记录这次大改造
- [ ] T12.6 OpenSpec change 标记 archived 移到 archive 目录
- [ ] T12.7 给用户最终汇报

---

## 风险与应对

| 风险 | 应对 |
|---|---|
| subagent timeout（取消字数限制后单次更慢）| 失败立即主 agent 接管自跑 |
| context window 撑爆（agent 数量多+memory 长输出）| 用 todo 跟踪进度,context 接近满时优先持久化进度到 git markdown |
| 中间 stage 输出不回传 | 拆多次 spawn,每次拿单 stage 结果 |
| 沙箱无外网（数据采集仍手动）| 标 estimated/manual,生产环境再补真值 |

## 完成度量

- 对齐 TradingAgents 从 50-60% 提到 ~95%
- 3 只标的（北方华创/恒瑞/中际旭创）质量跃迁，每只 critic≥85 ACCEPT
- 用户能在前端立刻看到深度跃迁的展示效果
