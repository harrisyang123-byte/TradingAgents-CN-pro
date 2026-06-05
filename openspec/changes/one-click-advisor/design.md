# 一键组合顾问 — 技术方案

## 变更范围

| 文件 | 改动 |
|------|------|
| `cli/claude_advisor.py` | --user-id 改为可选；新增 `_auto_detect_user()`；`python3` 适配 |
| `CLAUDE.md` | 快捷指令表：分析 → `python3 cli/claude_advisor.py` |
| `README.md` | 快速启动重新编排：一键分析 > 手动启动 > Workflow 表 |

## 关键决策

**自动探测算法**：aggregate + sort by count desc + limit 1，取持仓最多的用户。确定性返回，不随机。

**零配置优先**：不强制 .env，让用户打开项目说"分析"就能跑。
