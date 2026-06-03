## ADDED Requirements

### Requirement: CLI 支持全流程执行
`./run.sh all` SHALL 依次执行数据收集 → Workflow Agent 推理 → MongoDB 最终保存,任意阶段失败时停止并报告错误。

#### Scenario: 全流程正常完成
- **WHEN** 用户执行 `./run.sh all`
- **THEN** 系统依次完成 collect → analyze → save,最终输出 "Done. 处方已保存。 Run ID: {run_id}"

#### Scenario: 数据收集失败时停止
- **WHEN** `collect_data.py` 返回非零退出码
- **THEN** `run.sh` 停止,输出 "数据收集失败: {error}",不进入 analyze 阶段

### Requirement: CLI 支持分阶段执行
`./run.sh collect` SHALL 只执行数据收集。`./run.sh analyze --data-dir <path>` SHALL 只执行 Agent 推理 + 渐进式保存。

#### Scenario: 先收集后分析
- **WHEN** 用户先执行 `./run.sh collect`,数据收集成功后,再执行 `./run.sh analyze --data-dir data/advisor_runs/{ts}/`
- **THEN** 第二次执行跳过数据收集,直接启动 Workflow

#### Scenario: analyze 缺少 data-dir 参数
- **WHEN** 用户执行 `./run.sh analyze` 但未提供 `--data-dir`
- **THEN** `run.sh` 输出错误提示: "analyze 需要 --data-dir 参数,指向数据收集产出的目录"

### Requirement: CLI 支持断点续跑
`./run.sh analyze --data-dir <path> --from <step>` SHALL 从指定 Agent step 开始执行,复用已有数据文件和已完成 Agent 的输出。

#### Scenario: 从 L3 分析师续跑
- **WHEN** 用户执行 `./run.sh analyze --data-dir ... --from l3-analyst`
- **THEN** Workflow 跳过 L1/L2 所有 Agent,直接从 L3-分析师开始,复用前面已有的 step1-strategist 到 step4-scout 文件

#### Scenario: --from 指定的 step 不存在
- **WHEN** 用户执行 `./run.sh analyze --data-dir ... --from invalid-step`
- **THEN** `run.sh` 输出 "Unknown step: invalid-step. Valid: l1-strategist, l1-contrarian, l1-judge, l2-scout, l3-analyst, l3-strategist, l3-analyst-r2, l4-cio, l4-risk, l4-cio-final"

### Requirement: CLI 支持单 Agent 调试
`./run.sh analyze --data-dir <path> --only <step>` SHALL 只执行指定的单个 Agent 调用。

#### Scenario: 只验证 L2 Scout 的 prompt 修改
- **WHEN** 用户执行 `./run.sh analyze --data-dir ... --only l2-scout`
- **THEN** Workflow 只调用 L2-Scout 一次,输出到 step4_scout.json

### Requirement: CLI 校验输入参数
`run.sh` SHALL 在启动前校验 user_id 格式(24字符hex)、data_dir 存在性、Python/claude 环境可用性。

#### Scenario: user_id 格式非法
- **WHEN** 用户执行 `./run.sh all --user-id "invalid"`
- **THEN** `run.sh` 输出 "Invalid user_id format: must be 24-character hex string" 并退出

#### Scenario: Claude Code 版本不足
- **WHEN** `claude --version` 返回版本 < v2.1.154
- **THEN** `run.sh` 输出 "Claude Code v2.1.154+ required for Workflow, current: {version}" 并退出

### Requirement: setup.sh 一键安装 Agent 文件
`setup.sh` SHALL 将 `agents/advisor/` 下所有 `.md` 文件复制到 `.claude/agents/advisor/`,覆盖同名文件。

#### Scenario: 首次安装
- **WHEN** `.claude/agents/advisor/` 目录不存在
- **THEN** `setup.sh` 创建目录并复制所有 Agent 文件

#### Scenario: 更新已有 Agent
- **WHEN** `agents/advisor/l2-scout.md` 已修改,执行 `setup.sh`
- **THEN** `.claude/agents/advisor/l2-scout.md` 被覆盖为新版本
