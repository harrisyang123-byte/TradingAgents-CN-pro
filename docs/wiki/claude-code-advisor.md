---
name: claude-code-advisor-20260603
description: Claude Code 编排 + 9 子 Agent 混合架构，替代 LangGraph 成为 Tier 2 主力
metadata:
  type: project
---

## claude-code-advisor — 2026-06-03

### 架构
- Python 编排 `cli/claude_advisor.py` + 9 子 Agent
- JSON 文件总线（`/tmp/claude_advisor/`）替代 LangGraph msg_clear
- 子 Agent: L1(3) → 交叉验证 → L2(1) → L3(2) → L4(3)
- 交叉验证规则引擎: Tier1矛盾 / PE冲突 / 敞口重叠 / 黑天鹅 / 情绪冲突

### 与 LangGraph 的关系
- LangGraph 代码原位不动（fix/fund-akshare-api-error 分支）
- 新分支 feature/claude-code-advisor
- MongoDB 写入同一 collection，source='claude-code-v3' 区分

### 关键决策
- L2 反向者 + 裁判移除：被 Scout 自带 top_risks + 规则引擎替代
- L3 侦察兵移除：被"分析师+策略师"覆盖
- 情绪是每个 Agent 的输入参数，不是独立 Agent
- 逆向修正：恐慌→immediate（别人恐惧时买入），亢奋→conditional

### E2E 结果
- 速度: 486s (目标 <5min)
- 处方: 40 条 (36 持仓全覆盖 + 4 新增)
- 检出: PE 98.7% 分位矛盾、海康威视 1.7% 重叠
