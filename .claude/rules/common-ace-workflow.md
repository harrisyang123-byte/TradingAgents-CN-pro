# ACE 开发工作流

这是一个 ACE（AI Coding Engine）项目。项目中所有业务代码变更必须遵循 ACE 工作流：

## 强制工作流

```
planner → applier → reviewer → archiver
```

### 1. 规划（Planner）
- 新增业务文件、新特性、重构前，必须先运行 ace-planner
- ace-planner 完成 Grill 并获得用户确认后，才能进入实现阶段
- Grill 阶段：一次一问、给推荐答案、沿决策树推进

### 2. 实现（Applier）
- 严格按照 ace-planner 产出的 tasks.md 逐条实现
- 每步即时验证（类型检查、lint、测试）
- 一个 task 一个 commit

### 3. 审查（Reviewer）
- 实现完成后，运行 ace-reviewer 进行多维度代码审查
- Block 级别问题必须修复后再合并

### 4. 归档（Archiver）
- 积累的领域知识沉淀到 docs/wiki/
- 更新 docs/wiki/index.md

## 变更记录

- 所有业务变更必须通过 openspec 记录
- 原则上不允许直接编码，必须先有规划再实现
