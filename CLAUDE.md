# TradingAgents-CN — 多智能体 A 股/港股 投资分析系统

## 快捷指令

用户说以下任意一句即可触发：

| 用户说 | 执行 |
|--------|------|
| `分析` | `.venv/bin/python cli/claude_advisor.py`（自动取持仓最多用户） |
| `跑行业层` | 运行 workflow `v3-industry-layer` |
| `跑辩论` | 运行 workflow `v3-pm-debate` |
| `跑合成` | 运行 workflow `v3-synthesizer` |
| `加个功能：XXX` | 走 ACE 工作流 planner → applier → reviewer → archiver |

## 开发环境

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000   # 后端
cd frontend && npm run dev                                   # 前端
python -m pytest tests/ -v                                   # 测试
```

## 架构速览

```
用户请求 → FastAPI → LangGraph L0-L4 管线
                   ↘ Claude Code Workflow（9 子 Agent 编排）

L0: 数据 Agent（行情/财务/情绪）
L1: 策略师 ↔ 反向者 → 裁判 → 行业方向
L2: Scout 标的筛选
L3: 分析师 ↔ 策略师 → 组合诊断
L4: CIO 初稿 → 风险总监 → CIO 终裁 → 处方
```

详见 README.md 和 `planning/v3/architecture_v3.md`。

## ACE 工作流

所有业务变更走：`planner → applier → reviewer → archiver`

- `/ace-planner` — 需求探询 + 提案
- `/ace-applier` — 按 tasks.md 逐条实现
- `/ace-reviewer` — 多维度审查
- `/ace-archiver` — 归档 + 知识沉淀

## 知识库

先读 `docs/wiki/index.md` 了解项目已有知识，再动手。

## 可用 Workflows

| Workflow | 用途 |
|----------|------|
| `advisor` | 9 Agent L1-L4 全链路组合顾问 |
| `v3-industry-layer` | 行业研究员并行 + 反向者 + 跨行业裁判 |
| `v3-pm-debate` | 行业 PM 并行辩论 |
| `v3-synthesizer` | 风控规则 + Risk Director + Portfolio Synthesizer |

## 关键约束

- Python 3.12+ / FastAPI / Vue 3 / MongoDB / Redis
- API 前缀 `/api/`，统一响应 `{code, msg, data}`
- 变更走 openspec，不直接写代码
- 一个 task 一个 commit
