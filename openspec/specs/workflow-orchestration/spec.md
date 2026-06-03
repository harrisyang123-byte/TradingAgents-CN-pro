# workflow-orchestration Specification

## Purpose
TBD - created by archiving change claude-code-agent-advisor. Update Purpose after archive.
## Requirements
### Requirement: Workflow 脚本实现 4 层辩论编排
Workflow 脚本 SHALL 按 L1→L2→L3→交叉验证→L4 的顺序调用子 Agent,其中 L1 和 L3 各 2 轮辩论,L4 为 CIO初稿→风险审查→CIO终裁的单向流程。

#### Scenario: L1 辩论完整执行
- **WHEN** 数据收集完成且所有 data_*.json 就绪
- **THEN** Workflow 依次调用 L1-策略师 → L1-反向者 → L1-策略师R2(回应挑战) → L1-裁判,R2 的输入包含反向者输出

#### Scenario: L2 Scout 单次执行
- **WHEN** L1 裁判输出已写入 step3_judge.json
- **THEN** Workflow 调用 L2-Scout 一次,输入包含 L1 裁定 + PE数据 + Tier1报告 + 持仓分布

#### Scenario: L3 辩论完整执行
- **WHEN** L2 Scout 输出已写入 step4_scout.json
- **THEN** Workflow 依次调用 L3-分析师 → L3-策略师 → L3-分析师R2 → L3-策略师R2,策略师读分析师输出做诊断,分析师R2回应诊断

#### Scenario: L4 处方流程完整执行
- **WHEN** 交叉验证完成且 conflicts.json 就绪
- **THEN** Workflow 依次调用 L4-CIO初稿 → L4-风险总监 → L4-CIO终裁,CIO终裁读风险总监审查意见后出最终处方

### Requirement: JSON 文件总线通信
每步 Agent 的输出 SHALL 写入 `/data/advisor_runs/{run_id}/step{N}_{role}.json`,下游 Agent 通过文件路径读取上游输出。

#### Scenario: L1 反向者读取策略师输出
- **WHEN** L1-反向者 agent() 启动
- **THEN** 其 prompt 中指定输入文件为 `step1_strategist.json` 的完整路径,反向者通过 Read 工具获取策略师的全部行业判定

#### Scenario: CIO 终裁读取所有上游输出
- **WHEN** L4-CIO终裁 agent() 启动
- **THEN** 其 prompt 中指定输入包含 step3_judge.json + step4_scout.json + step5_analyst_r2.json + step6_strategist_r2.json + conflicts.json + data_exposure.json

### Requirement: 辩论轮次控制
每个辩论层 SHALL 有明确的轮次上限:L1 max 2 rounds, L3 max 2 rounds, L4 max 1 round。

#### Scenario: L1 辩论不超 2 轮
- **WHEN** L1-策略师R2 回应反向者后
- **THEN** 直接进入 L1-裁判,不再进行第 3 轮

#### Scenario: L4 风险总监只发言一次
- **WHEN** L4-风险总监输出 step8_risk.json 后
- **THEN** 直接进入 L4-CIO终裁,CIO终裁读完风险意见后出最终处方

### Requirement: Agent 失败时保留已完成的输出
当某个 agent() 调用失败(重试耗尽/超时)时,Workflow SHALL 保留所有已完成 Agent 的输出文件,用户可通过 `--from` 参数从失败步骤断点续跑。

#### Scenario: L3-分析师R2 失败后断点续跑
- **WHEN** L3-分析师R2 agent() 在 schema 验证失败 2 次重试后仍不符合格式
- **THEN** Workflow 终止,已完成的 step1-strategist 到 step6-strategist 文件保留。用户执行 `./run.sh analyze --data-dir ... --from l3-analyst-r2` 从失败步骤继续

### Requirement: 渐进式 MongoDB 保存
每步 Agent 成功输出后,Workflow SHALL 通过 `Bash("python save_step.py --step {step_name}")` 即时保存该步结果到 MongoDB。

#### Scenario: L1-策略师完成后即刻保存
- **WHEN** L1-策略师 agent() 返回且 schema 验证通过
- **THEN** Workflow 立即执行 `python save_step.py --step l1-strategist --dir ...`,将该步输出写入 MongoDB

#### Scenario: save_step.py 执行失败不中断流程
- **WHEN** save_step.py 因 MongoDB 连接问题失败
- **THEN** Workflow 记录 warning 日志,继续执行下一个 Agent 调用

