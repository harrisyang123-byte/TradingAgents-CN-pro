## ADDED Requirements

### Requirement: 每步 Agent 输出即写 MongoDB
`sava_step.py` SHALL 在每步 Agent 成功输出后,将该步结果写入 MongoDB `agent_steps` collection,包含 run_id、step_name、output_json、model、created_at 字段。

#### Scenario: L1-策略师完成后写 MongoDB
- **WHEN** L1-策略师 agent() 返回且 schema 验证通过,step1_strategist.json 写入成功
- **THEN** `save_step.py --step l1-strategist --dir ...` 将 step1_strategist.json 的内容写入 MongoDB agent_steps collection

#### Scenario: save_step.py 因连接问题失败
- **WHEN** MongoDB 不可达(save_step.py 连接超时)
- **THEN** `save_step.py` 输出 warning 到 stderr,返回非零退出码。Workflow 记录 warning 但继续执行下一个 Agent

### Requirement: 最终处方保存到 portfolio_advice
`sava_to_mongodb.py` SHALL 读取 step9_final.json(CIO 终裁)和 conflicts.json,组装为 PortfolioAdvice 实体写入 MongoDB `portfolio_advice` collection,source 字段设为 `'claude-code-workflow-v1'`。

#### Scenario: 完整处方保存成功
- **WHEN** `save_to_mongodb.py` 执行,step9_final.json 存在且格式正确
- **THEN** MongoDB `portfolio_advice` collection 中新增一条文档,`source = 'claude-code-workflow-v1'`,含完整的 prescription 数组和 cio_verdict 文本

#### Scenario: MongoDB 写入重试
- **WHEN** 第一次 write 操作失败(连接超时)
- **THEN** `save_to_mongodb.py` 间隔 2 秒重试,最多 3 次。3 次全失败后输出错误信息并返回非零退出码

#### Scenario: MongoDB 写入全部失败
- **WHEN** 3 次重试全部失败
- **THEN** `save_to_mongodb.py` 返回非零退出码,`run.sh` 输出 "保存失败: {error}。输出文件保留在 {data_dir},可手动重新保存。"

### Requirement: 与 LangGraph 处方共存
两套系统的处方 SHALL 通过 `source` 字段区分:`source='langgraph'`(旧)和 `source='claude-code-workflow-v1'`(新),前端通过 `source` 过滤展示。

#### Scenario: 前端默认展示最新版处方
- **WHEN** MongoDB 中同时存在 `source='langgraph'` 和 `source='claude-code-workflow-v1'` 两条记录
- **THEN** 前端 `/portfolio/overview` 按 `created_at` 降序取第一条展示,用户可切换到历史版本

#### Scenario: LangGraph 不受影响
- **WHEN** `claude-code-workflow-v1` 处方写入
- **THEN** LangGraph 的现有 API `/api/analysis/batch` 完全不受影响,写入 `source='langgraph'`

### Requirement: 输出文件持久化到项目目录
所有中间 Agent 输出文件 SHALL 写入 `data/advisor_runs/{run_id}/`(项目目录下),不写入 `/tmp/`。系统重启或清理不丢失分析记录。

#### Scenario: 分析完成后文件可追溯
- **WHEN** 一次完整分析完成 7 天后
- **THEN** `data/advisor_runs/{run_id}/` 目录及其全部文件仍然存在,可复查每个 Agent 的完整输出

#### Scenario: 多次分析互不覆盖
- **WHEN** 连续执行两次 `./run.sh all`
- **THEN** 两次分析在 `data/advisor_runs/` 下有各自独立的时间戳子目录
