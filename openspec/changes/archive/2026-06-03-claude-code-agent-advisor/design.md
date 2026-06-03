## Context

当前 `cli/claude_advisor.py` 用 Python for-loop + `requests.post(DeepSeek)` 串行调用 9 个角色。Claude Code 不参与推理。需要把执行层从 DeepSeek API 换成 Claude Code Workflow `agent()`,同时保留现有数据收集工具和 MongoDB schema。

约束:
- Claude Code ≥ v2.1.154 (当前 v2.1.161 ✅)
- Workflow 功能已启用(本次对话中已验证 Workflow tool 可用)
- 现有 Python 数据工具(`market_tools.py`、`pe_percentile.py`、`exposure_service.py`)复用,不改逻辑
- MongoDB `portfolio_advice` collection 复用现有 schema,通过 `source` 字段区分

## Goals / Non-Goals

**Goals:**
- 9 个 Agent 定义文件 + Workflow 编排脚本,实现 planning/v2 设计的完整辩论结构
- 文件路径引用模式避开 `[object Object]` 序列化 bug (GitHub #5504)
- 断点续跑 + 渐进式 MongoDB 保存,中途崩溃不丢数据
- CLI 入口支持全流程/分阶段/单Agent调试三种模式

**Non-Goals:**
- 不修改 LangGraph 原 Agent 管线代码
- 不修改 MongoDB schema(`PortfolioAdvice`/`AdviceItem` 不变)
- 不修改前端(前端通过 `source` 字段区分)
- 不新增 Python 依赖
- 不做组合回测/相关性矩阵/因子暴露(v4)

## Decisions

### D1: Workflow 脚本用 JS DSL (agent/pipeline),不用 Shell+claude -p

**选择**: Workflow `agent()` + `pipeline()` + `Bash()`

**备选**: Shell `for` loop + `claude -p --output-format json`

**理由**: Workflow 提供 schema 自动重试、断点 resume、`pipeline()` 原生并行语义。Shell 方案需要自己管理断点、重试、并行 `wait`。且 `agent()` 的 schema 验证在 tool-call 层自动执行,Shell 方案需要额外写 jq 校验。

**已知风险**: `[object Object]` 序列化 bug (GitHub #5504 #4580)。**规避方式**: prompt 中只写文件路径字符串,不嵌 JSON 对象。Agent 用 Read tool 自己读。

### D2: 文件路径引用模式

**选择**: Prompt 中 `"输入数据在 {data_dir}/data_portfolio.json，请使用 Read 工具读取"`

**备选**: Prompt 中嵌入 JSON 摘要字符串

**理由**: 避开序列化 bug。数据文件可能 50KB+(大量持仓),嵌在 prompt 里浪费 token 且触发 V8 `JSON.stringify` 递归深度问题。Agent 自己 Read 文件,可按需读取部分内容,成本更低。

### D3: 12 次 agent() 调用,非 9 次

**选择**: L1 策略师发言 2 次(初始+回应反方)+ 反向者 1 次 + 裁判 1 次 = 4 次。L2 Scout 1 次。L3 分析师 2 次 + 策略师 2 次 = 4 次。L4 CIO初稿 1 次 + 风险总监 1 次 + CIO终裁 1 次 = 3 次。总计 12 次。

**备选**: 每个角色只调一次,辩论压缩在单次 prompt 内("先给初始判断,再预判可能的挑战并回应")。

**理由**: 单次 prompt 内辩论缺少真正的信息不对称——Agent 不能"不知道对方的挑战"再回应。分次调用让每轮有独立的思考和文件 I/O,辩论才真实。

**代价**: token 消耗约 +30%(多 3 次调用)。L1-L3 Sonnet(~$0.3/次),L4 Opus(~$1/次),总额外成本约 $2-3/次分析。

### D4: 数据目录用 `data/advisor_runs/{ts}/`,不用 `/tmp/`

**选择**: 项目目录下 `data/advisor_runs/YYYYMMDD_HHmmss/`

**理由**: `/tmp` 在 macOS 系统重启时清空,且多用户场景下可能冲突。项目目录保证持久化且和代码一起管理。

### D5: 渐进式 MongoDB 保存(=每步 Agent 输出即入库)

**选择**: Workflow 内每步 `agent()` 成功后 `Bash("python save_step.py")`

**备选**: 全部 Agent 跑完后统一保存

**理由**: 12 次 Agent 调用约 4-5 分钟,中途崩溃如果只在最后保存则全部丢失。渐进式保存确保每一步完成就持久化。`save_step.py` 失败不阻塞流程(只记 warning),避免 MongoDB 问题导致 Workflow 中断。

### D6: agent() 指定 subagent_type 使用自定义 Agent

**选择**: `agent(prompt, {agentType: 'l1-strategist', schema: SCHEMA})` —— 使用 `.claude/agents/advisor/` 下的自定义 Agent 文件

**备选**: `agent(prompt, {schema: SCHEMA})` 不指定 agentType,用 general-purpose 子 Agent,prompt 中包含角色定义

**理由**: 自定义 Agent 文件有独立的 YAML frontmatter(model/tools) 和 system prompt,每个角色有明确的能力边界。`agentType` 直接映射到 Agent 文件名,Workflow 可解析。

## Risks / Trade-offs

- **[R1] `[object Object]` 序列化 bug**: prompt 参数不能嵌 JSON 对象 → 所有数据通过文件路径引用,Agent 自己 Read
- **[R2] 12 次 Agent 调用总 token 消耗 $5-8/次**: L1-L3 用 Sonnet 降低成本,L4 才用 Opus。比 DeepSeek API 的 ~$0.5/次贵很多,但产出质量应该成倍提升
- **[R3] Workflow 运行中途 Claude Code 崩溃**: 渐进式保存 + 项目目录存文件,崩溃后 `--from` 断点续跑
- **[R4] 自定义 AgentType 在 Workflow 中解析失败**: 如果 agentType 指向的文件不存在,回退到 general-purpose + 嵌入角色 prompt。setup.sh 必须在 Workflow 前执行
- **[R5] AKShare 数据源不稳定**: 基金穿透/PE/千股千评可能超时。数据收集时 catch 异常,部分失败继续。Agent prompt 中告知"以下数据可能不完整"
