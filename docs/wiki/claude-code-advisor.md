---
name: claude-code-agent-advisor-20260603
description: Claude Code Workflow 原生编排 + 9 子 Agent + JSON 文件总线，替代 Python→DeepSeek API 管线
metadata:
  type: project
---

# Claude Code Workflow 组合顾问 — 2026-06-03

## 架构

- Shell 入口 `scripts/run.sh` + Claude Code Workflow `agent()` 原生编排
- 9 个自定义子 Agent（`agents/advisor/*.md`），每个有独立 system prompt + JSON Schema 输出约束
- JSON 文件总线（`data/advisor_runs/{ts}/`）传递上下文——替代 DeepSeek API + msg_clear
- 模型分层：L1-L3 Sonnet（数据驱动分析），L4 Opus（深推理决策）
- 渐进式 MongoDB 保存：每步 Agent 输出即入库，中途崩溃不丢数据

## Agent 清单（9 个 + 交叉验证）

| # | Agent | 层级 | 模型 | 职责 |
|---|-------|------|------|------|
| 1 | l1-strategist | L1 | Sonnet | 行业方向判定（看多） |
| 2 | l1-contrarian | L1 | Sonnet | 挑战策略师（看空） |
| 3 | l1-judge | L1 | Sonnet | 宏观裁判——最终行业裁定 |
| 4 | l2-scout | L2 | Sonnet | 6维评分标的筛选（≥30%中小市值） |
| 5 | l3-analyst | L3 | Sonnet | 逐持仓安全边际评估 |
| 6 | l3-strategist | L3 | Sonnet | 组合诊断报告（集中度/一致性/隐形敞口） |
| 7 | l4-cio | L4 | Opus | CIO 初稿——资金分配方案 |
| 8 | l4-risk | L4 | Opus | 风险总监——攻击 CIO 方案 |
| 9 | l4-cio-final | L4 | Opus | CIO 终裁——最终处方 |
| — | cross_validate.py | — | Python规则引擎 | 确定性矛盾检测（非LLM） |

## 辩论结构

```
L1 (2轮): strategist → contrarian → strategist_r2 → judge
L2 (单次): scout（自带 top_risks + 6维评分映射）
L3 (2轮): analyst → strategist → analyst_r2 → strategist_r2
交叉验证: Python 规则引擎（Tier1矛盾/PE高估vs买入/敞口重叠）
L4 (1轮): CIO初稿 → 风险总监 → CIO终裁
```

## 与上一版（Python+DeepSeek）的关系

| 维度 | 上一版 claude-code-advisor | 当前版 claude-code-agent-advisor |
|------|--------------------------|-------------------------------|
| LLM 调用 | Python `requests.post(DeepSeek)` | Claude Code Workflow `agent()` |
| Agent 能力 | 纯文本补全，无工具 | Read + Bash 工具，独立 context window |
| 上下文传递 | Python for-loop 串行 | JSON 文件总线 + agent() 独立 session |
| 断点恢复 | 不支持 | Workflow resume + `--from` 续跑 |
| 保存 | 最终一次性写 MongoDB | 渐进式 save_step.py 每步入库 |
| source 标识 | `claude-code-v3` | `claude-code-workflow-v1` |

两版通过 `source` 字段共存于同一 MongoDB collection，前端按 `source` 过滤。

## 关键决策

1. **Workflow 替代 Shell `claude -p`**：schema 自动重试 + 断点 resume + `pipeline()` 原生并行语义
2. **文件路径引用模式**：prompt 中只写文件路径，Agent 自己 Read——避开 `[object Object]` 序列化 bug (GitHub #5504)
3. **12 次 agent() 调用非 9 次**：辩论多轮让每轮有独立思考，单次 prompt 内辩论缺少信息不对称
4. **渐进式 MongoDB 保存**：每步 `agent()` 成功后立即 `Bash("python save_step.py")`，失败不阻塞
5. **数据放项目目录非 /tmp**：`data/advisor_runs/{ts}/`，系统重启不丢失分析记录

## CLI 入口

```bash
./run.sh all                      # 全流程
./run.sh collect                  # 只采数据
./run.sh analyze --data-dir ...   # 只跑 Agent
./run.sh analyze --data-dir ... --from l3-analyst   # 断点续跑
./run.sh analyze --data-dir ... --only l2-scout     # 单 Agent 调试
```

## E2E 状态

- 代码实现：完成（28 tasks，4 commits）
- E2E 测试：待运行（需 MongoDB + AKShare + Claude Code Workflow 环境）
