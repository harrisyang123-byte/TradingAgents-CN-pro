# agent-definitions Specification

## Purpose
TBD - created by archiving change claude-code-agent-advisor. Update Purpose after archive.
## Requirements
### Requirement: Agent 文件必须符合 YAML frontmatter 规范
每个 Agent 定义文件 SHALL 包含 `name`、`description`、`model`、`tools` 四个 YAML frontmatter 字段,其中 `name` 和 `description` 为必填,`model` 和 `tools` 有默认值。

#### Scenario: 有效 Agent 文件被正确解析
- **WHEN** Claude Code 启动并扫描 `.claude/agents/advisor/` 目录
- **THEN** 所有包含合法 YAML frontmatter 的 `.md` 文件被注册为可用子 Agent

#### Scenario: 缺少必填字段的 Agent 文件被跳过
- **WHEN** Agent 文件缺少 `name` 或 `description` 字段
- **THEN** Claude Code 跳过该文件,不注册,记录 warning 日志

### Requirement: Agent 输出必须符合 JSON Schema 定义
每个 Agent SHALL 在 `agent()` 调用时通过 `schema` 参数指定输出 JSON Schema,输出不符合 Schema 时自动重试。

#### Scenario: Schema 验证通过
- **WHEN** Agent 输出符合 Schema 定义的字段类型和必填项
- **THEN** 输出 JSON 写入对应 step 文件,retry_count 保持 0

#### Scenario: Schema 验证失败自动重试
- **WHEN** Agent 输出缺少必填字段或字段类型错误
- **THEN** 系统自动重试 agent() 调用,retry_count +1,prompt 中追加"上次输出格式不对请严格按 Schema 输出"

#### Scenario: 重试 2 次后仍失败
- **WHEN** Agent 在 2 次重试后输出仍不符合 Schema
- **THEN** 该 AgentStep status 设为 FAILED,error_message 记录 Schema 验证错误详情,保留原始输出文件供人工检查

### Requirement: Agent 按层级分配模型
L1-L3 层 Agent SHALL 使用 Sonnet 模型,L4 层 Agent(CIO初稿、风险总监、CIO终裁)SHALL 使用 Opus 模型。

#### Scenario: L1 策略师使用 Sonnet
- **WHEN** Workflow 调用 `agent(l1-strategist)`
- **THEN** 子 Agent 使用 sonnet 模型执行

#### Scenario: L4 CIO 终裁使用 Opus
- **WHEN** Workflow 调用 `agent(l4-cio-final)`
- **THEN** 子 Agent 使用 opus 模型执行

### Requirement: Agent 通过文件路径引用输入数据
每个 Agent 的 prompt SHALL 包含输入数据文件的绝对路径,Agent 使用 Read 工具自行读取,不得在 prompt 字符串中嵌入大型 JSON。

#### Scenario: Agent 读取数据文件
- **WHEN** Agent 收到 prompt 中包含 "输入数据在 /data/advisor_runs/{ts}/data_portfolio.json"
- **THEN** Agent 调用 Read 工具读取该文件,获取完整数据

#### Scenario: 数据文件不存在
- **WHEN** Agent 尝试 Read 不存在的输入文件
- **THEN** Agent 输出错误信息,AgentStep status 设为 FAILED

### Requirement: 每个 Agent 必须有独立的系统提示
每个 Agent 定义文件的 body SHALL 包含角色身份定义、输入数据说明、思考步骤要求、输出格式要求。

#### Scenario: 策略师收到行业方向判定任务
- **WHEN** Workflow 以策略师角色调用 agent()
- **THEN** Agent 以市场策略师身份推理,基于宏观数据和行业排名输出 Go/NoGo 判定

#### Scenario: 反向者收到挑战策略师的任务
- **WHEN** Workflow 以反向者角色调用 agent(),输入包含策略师输出
- **THEN** Agent 以质疑立场审视策略师的每个行业判定,输出数据支撑的反驳

