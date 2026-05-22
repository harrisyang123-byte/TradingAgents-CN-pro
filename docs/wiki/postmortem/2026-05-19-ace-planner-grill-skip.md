---
name: ace-planner-failure-postmortem
description: "复盘：为什么 ace-planner 的 Grill 环节被跳过，以及如何防止再犯"
metadata:
  type: reference
tags: [ace, process, postmortem, grill]
---

## 事件

2026-05-19，执行基金详情页规划时，在 Phase 1（探索）结束后直接跳过了 Phase 2 的完整 Grill 流程，让子 agent 代写了 PRD 和原型。

## 根因分析

### 直接原因

用户回答果断（"选 B"、"可以"），AI 误以为方向已明确即可产出方案。没有意识到"方向明确"和"方案敲定"是两回事——Grill 要做的不是确认方向，而是穷举边缘场景。

### 深层原因

1. **行为指令不够醒目**：ace-planner.md 中的规则是段落式的描述，不是 Matt 式的 `<what-to-do>` 行为块，容易被 AI 在长文档中跳过
2. **缺少 "Do NOT" 禁区**：没有明确禁止"子 agent 代写 PRD/原型"的行为
3. **缺少失败模式记录**：如果之前有人犯过同样的错并记录，AI 会更警觉

### 与 Matt Pocock 方案的差距

| 维度 | 我们的 ace-planner | Matt 的 grill-with-docs |
|------|-------------------|----------------------|
| 行为指令 | 段落描述，可忽略 | `<what-to-do>` 块，醒目 |
| 边界声明 | 无 | `.out-of-scope/` 目录 |
| 每步确认 | 写了但AI跳过 | 更轻量，自然语言控制 |
| 子 agent 限制 | 无明确边界 | 隐式依赖纯 prompt |

## 改进方向

对应的 ace-planner 改进参见 openspec 变更记录。
