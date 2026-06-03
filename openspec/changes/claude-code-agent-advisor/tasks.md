## 1. 基础设施准备

- [x] 1.1 创建 `agents/advisor/` 目录结构
- [x] 1.2 创建 `scripts/run.sh` Shell 入口(参数解析 + 校验 + 阶段路由)
- [x] 1.3 创建 `setup.sh`(cp agents/advisor/ → .claude/agents/advisor/)
- [x] 1.4 创建 `data/advisor_runs/` 目录并加入 `.gitignore`
- [x] 1.5 运行 `setup.sh` 验证 Agent 文件可被 Claude Code 发现

## 2. Agent 定义文件(9 个)

- [x] 2.1 创建 `l1-strategist.md` — 市场策略师(看多),输入 data_macro.json + data_portfolio.json,输出行业 Go/NoGo + 方向+数据支撑。model=sonnet, tools=[Read, Bash]
- [x] 2.2 创建 `l1-contrarian.md` — 反向者(看空),输入 step1_strategist.json + data_macro.json,输出质疑+数据反驳。model=sonnet
- [x] 2.3 创建 `l1-judge.md` — 宏观裁判,输入全部 L1 辩论记录,输出最终超配/标配/低配/零配裁定(≥5方向,每个≥200字)。model=sonnet
- [x] 2.4 创建 `l2-scout.md` — Scout(6维评分),输入 step3_judge.json + data_pe.json + data_tier1.json + data_portfolio.json,输出候选池(含financial_data + price_range + top_risks,≥30%中小市值)。model=sonnet, tools=[Read, Bash]
- [x] 2.5 创建 `l3-analyst.md` — 持仓分析师,输入 step3_judge.json + step4_scout.json + data_tier1.json + data_pe.json,输出每只持仓安全边际评估。model=sonnet
- [x] 2.6 创建 `l3-strategist.md` — 组合策略师(诊断报告员),输入 step5_analyst.json + data_exposure.json,输出集中度/一致性风险/隐形暴露汇总。不输出操作建议。model=sonnet
- [x] 2.7 创建 `l4-cio.md` — CIO初稿,输入全部前面产物+conflicts.json,输出敞口诊断+行业配置+资金分配方案。model=opus
- [x] 2.8 创建 `l4-risk.md` — 风险总监,输入 step7_cio.json + conflicts.json + data_exposure.json,输出风险审查(集中度/流动性/Tier1验证/压力测试)。model=opus
- [x] 2.9 创建 `l4-cio-final.md` — CIO终裁,输入 step7_cio.json + step8_risk.json + conflicts.json,输出最终处方+完整cio_verdict。model=opus
- [x] 2.10 为每个 Agent 定义 JSON Schema 输出结构(在 Agent .md 末尾,供 `agent({schema: ...})` 使用)

## 3. Python 脚本

- [ ] 3.1 适配 `scripts/collect_data.py`(或在 cli/ 新建),支持 `--user-id` 和 `--out-dir` 参数,产出 data_portfolio/data_tier1/data_pe/data_exposure/data_macro/data_market_temp 共 6 个 JSON 文件
- [ ] 3.2 创建 `scripts/cross_validate.py` — 读 step3+step4+step5+step6+data_tier1+data_pe+data_exposure → 执行 4 条规则 → 写 conflicts.json
- [ ] 3.3 创建 `scripts/save_step.py` — 读单个 step JSON 文件 → 写 MongoDB agent_steps collection
- [ ] 3.4 创建 `scripts/save_to_mongodb.py` — 读 step9_final.json + conflicts.json → 组装 PortfolioAdvice → 写 MongoDB portfolio_advice collection (source='claude-code-workflow-v1')

## 4. Workflow 编排脚本

- [ ] 4.1 创建 Workflow 脚本(L1 辩论: strategist → contrarian → strategist_r2 → judge)
- [ ] 4.2 实现 L2 Scout 单次调用 + 6维总分映射
- [ ] 4.3 实现 L3 辩论(analyst → strategist → analyst_r2 → strategist_r2)
- [ ] 4.4 实现交叉验证步骤(Bash 调 cross_validate.py)
- [ ] 4.5 实现 L4 辩论(CIO初稿 → 风险总监 → CIO终裁)
- [ ] 4.6 每步 agent() 后加 Bash("python save_step.py --step {name}")
- [ ] 4.7 实现 --from 和 --only 参数逻辑(skip 已完成 Agent / 只跑指定 Agent)

## 5. 集成测试

- [ ] 5.1 E2E: `./run.sh all` 完整跑一次,验证 6 个 data JSON + 12 个 step JSON + conflicts.json + MongoDB 写入成功
- [ ] 5.2 断点续跑: 模拟 L3 步骤失败 → `./run.sh analyze --data-dir ... --from l3-analyst`
- [ ] 5.3 单Agent调试: `./run.sh analyze --data-dir ... --only l2-scout` 验证仅一个 Agent 执行
- [ ] 5.4 空持仓: 创建空持仓用户 → `./run.sh collect` → 预期拒绝
- [ ] 5.5 数据部分失败: 模拟 AKShare 超时 → 验证 continue with partial data + warnings
- [ ] 5.6 MongoDB 失败: 模拟 MongoDB 不可达 → 验证文件保留 + 手动重新保存
- [ ] 5.7 前端展示: 确认 `source='claude-code-workflow-v1'` 处方在前端正常展示

## 6. 文档

- [ ] 6.1 确保 `planning/v2/claude-code-agent-advisor_prd.md` 与最终实现一致
- [ ] 6.2 更新 `docs/wiki/index.md`(如需要)
