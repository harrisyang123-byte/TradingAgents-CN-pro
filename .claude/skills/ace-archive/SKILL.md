---
name: ace-archive
description: 归档方法论参考 — 复杂度感知归档、知识沉淀规则。被 ace-archiver agent 引用。
---

# ace-archive 方法论

归档变更时的方法论参考。完整流程见 `agents/ace-archiver.md`。

## 复杂度感知归档

| 复杂度 | 前置要求 | 跳过策略 |
|--------|---------|---------|
| 简单 | apply 完成 | 直接归档 |
| 中等 | review 或 verify 至少一个 | 警告后允许 |
| 复杂 | review + verify 都通过 | 阻止，强制归档需记录风险 |

## 知识沉淀规则

**识别类型**：从 proposal.md/design.md 关键词自动分类（API/业务/架构/数据库/其他）。

**提取优先级**：specs/ > design.md > proposal.md > review-log。

**原则**：
- 惰性创建：目录不存在时询问用户
- 无法识别类型时跳过，不强制
- 不重复 openspec 官方归档逻辑

## 检查清单

- [ ] 复杂度已识别
- [ ] 前置步骤已验证（或用户确认跳过）
- [ ] 知识已沉淀（或确认跳过）
- [ ] 变更目录已移至 archive/
- [ ] 摘要已生成
- [ ] 事件已写入 archive-log.jsonl
