## Why

`cli/claude_advisor.py` 用 Python → HTTP → DeepSeek API 扮演 9 个投资分析角色,Claude Code 本身完全不参与推理,只作为"写代码的工具"。产出质量差(L1 20行业仅1个Go、L2全推大蓝筹、L3报"行业全部为未知")、层间数据断裂(msg_clear)、单次耗时22分钟——用户不敢用。Claude Code v2.1.161 已支持 Dynamic Workflows(Workflow tool),可以原生编排多子 Agent,每个 Agent 在独立 context window 中做深度推理。这是用 Claude Code 能力替代 DeepSeek API 实现组合顾问的正确时机。

## What Changes

- 新增 9 个 Claude Code 子 Agent 定义文件(`agents/advisor/l1-strategist.md` 等),每个有独立 system prompt + JSON Schema 输出约束 + 模型分层(L1-L3 Sonnet, L4 Opus)
- 新增 Workflow 编排脚本,用 `agent()` + `pipeline()` 实现 4 层辩论(L1 2轮 ↔ L2 Scout单次 ↔ L3 2轮 ↔ L4 1轮),共12次子 Agent 调用
- 新增 `run.sh` CLI 入口,支持 `all`/`collect`/`analyze` 子命令 + `--data-dir`/`--from`/`--only` 参数
- 新增交叉验证规则引擎 `cross_validate.py`(Python,非LLM),检测 Tier1矛盾、PE分位vs建议方向、敞口重叠
- 新增渐进式保存管道(`save_step.py` + `save_to_mongodb.py`),每步 Agent 输出即写 MongoDB
- 新增 `setup.sh` 一键复制 Agent 文件到 `.claude/agents/advisor/`
- 输出 `source='claude-code-workflow-v1'` 标识,与 LangGraph 的 `source='langgraph'` 共存于同一 MongoDB collection
- 不改 LangGraph 原代码(留 fix 分支保留),在新分支 `feature/claude-code-agent-advisor` 上构建

## Capabilities

### New Capabilities

- `agent-definitions`: 9 个 Claude Code 子 Agent 定义文件(YAML frontmatter + system prompt),每个角色有独立身份、工具权限、输出 Schema 和模型选择
- `workflow-orchestration`: Workflow 脚本实现 4 层辩论编排,通过 JSON 文件总线传递上下文,每次 `agent()` 调用在独立 session 中运行
- `data-collection-pipeline`: `collect_data.py` 采集持仓/Tier1/PE/敞口/宏观/行业排名/资金流向/市场温度,产出结构化 JSON 到 `data/advisor_runs/{ts}/`
- `cross-validation-engine`: Python 确定性规则引擎检测 Tier1矛盾、PE高估vs买入、敞口重叠,产出 `conflicts.json` 注入 L4 CIO
- `cli-entry-point`: `run.sh` Shell 入口,参数化控制数据收集/Agent推理/保存的阶段化执行
- `progressive-mongodb-save`: 每步 Agent 输出即时持久化到 MongoDB,中途崩溃不丢已完成的推理

### Modified Capabilities

无。本次变更不修改现有 LangGraph Agent 管线的任何 spec 级行为,两套系统通过 `source` 字段共存。

## Impact

- **新增文件**: `agents/advisor/*.md`(9个), `scripts/run.sh`, `scripts/cross_validate.py`, `scripts/save_step.py`, `scripts/save_to_mongodb.py`, `setup.sh`
- **修改文件**: `scripts/collect_data.py`(适配新输出路径)
- **新增依赖**: 无(Python工具复用现有 akshare/tushare/MongoDB 依赖)
- **系统依赖**: Claude Code CLI ≥ v2.1.154(已满足: v2.1.161)
- **MongoDB**: 复用现有 `portfolio_advice` collection,新增 `source='claude-code-workflow-v1'`
- **前端**: 零改动,通过 `source` 字段区分展示
- **Git 分支**: `feature/claude-code-agent-advisor`

## PRD

详见 `planning/v2/claude-code-agent-advisor_prd.md` — O.A.I.S 四层完整需求文档,含 6 实体定义+状态机+Mermaid时序图+SECURE 13场景。

## 原型

跳过——本次变更不涉及新页面、新布局或新交互模式(纯后端基础设施:Agent文件+Workflow脚本+Shell编排+数据管道)。

<!-- Dialectical Analysis -->

### 方案对比

| 维度 | 方案A: Python→DeepSeek API(当前) | 方案B: Claude Code Workflow(本提案) | 方案C: Shell+claude -p one-shot |
|------|--------------------------------|-----------------------------------|-------------------------------|
| Agent 能力 | 纯文本补全,无工具调用 | Read+Bash 工具,独立 context window | 同B,但每次新session |
| 上下文隔离 | N/A(单线程API call) | 每个agent()独立session ✅ | 每个claude -p独立session ✅ |
| 辩论实现 | Python for-loop 串行 | pipeline() 原生并行 ✅ | 需手动管理并行 & wait |
| 断点恢复 | 不支持 ❌ | Workflow resume 原生支持 ✅ | 需自己写断点逻辑 |
| Schema验证 | 手写正则 ❌ | agent({schema: SCHEMA}) 自动重试 ✅ | 同B |
| 维护成本 | Python代码+DeepSeek prompt | JS Workflow脚本+Agent .md文件 | Shell脚本+Agent .md文件 |
| 社区支持 | — | Anthropic主推方向(2026.6发布) | 可行但非推荐路径 |

**推荐方案B**: Workflow 针对多 Agent 辩论场景有原生支持(pipeline/parallel/schema/resume),方案C也能工作但需更多手动管理,方案A已证明产出质量不足。

### 风险对冲

- **最大风险**: `agent()` 的 `[object Object]` 序列化bug(GitHub #5504)。**规避**: prompt中不嵌大JSON,写文件路径让Agent自己Read
- **次要风险**: 12次 Agent 调用总token消耗大(~$5-8)。**控制**: L1-L3用Sonnet降低成本,L4才用Opus深推理
- **退路**: 如果Workflow不稳定,切方案C(`claude -p` one-shot)只需改编排层,Agent文件可复用
