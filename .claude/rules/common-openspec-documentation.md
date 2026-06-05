# OpenSpec 文档规范

## 强制要求

所有业务变更必须通过 openspec 创建变更记录：

```bash
openspec new change "<change-name>"
```

变更记录必须包含完整的 artifacts：
- proposal.md — 为什么要做
- design.md — 怎么做（技术方案）
- specs/ — 验收规格
- tasks.md — 实现任务（垂直切片）

## 变更命名规范

- 使用 kebab-case（连接符小写）
- 名称应当反映变更内容（如 `fund-detail-page`、`ace-planner-grill-enhancement`）

## 归档

实现完成后，openspec 变更记录不删除，作为项目的决策历史永久保留。
