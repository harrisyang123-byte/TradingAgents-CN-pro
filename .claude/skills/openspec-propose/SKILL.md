---
name: openspec-propose
description: "创建 OpenSpec 变更提案：自动生成 proposal/specs/design/tasks artifacts。"
---

# openspec-propose

被 ace-planner 第三阶段调用，将 PRD + 原型转化为 OpenSpec 标准 artifacts。

## 输入上下文

调用者（ace-planner）会提供：
- 变更名称（kebab-case）
- PRD 内容
- 原型文件路径（如适用）
- Grill 总结（术语决策、功能点）
- 复杂度评估（简单/中等/复杂）

## 输出结构

```
openspec/changes/{name}/
├── proposal.md   — 技术方案（含辩证分析）
├── design.md     — 详细设计
├── specs/        — 验收规格（每 capability 一个文件）
│   └── {capability}/spec.md
└── tasks.md      — 实现任务（vertical slicing）
```

## 流程

### Step 1: 创建变更目录

```bash
openspec new change "{name}"
```

### Step 2: 按依赖顺序生成 artifacts

**顺序**：proposal → specs → design → tasks

每步生成前调用模板和规则：

```bash
openspec instructions
```

输出路径由 openspec 模板决定，默认在 `openspec/changes/{name}/` 下。

### Step 3: proposal.md — 技术方案

包含以下章节：
- **Why** — 为什么做（链接 PRD 中的 P.A.M）
- **PRD** — 链接到 `planning/{version}/{name}_prd.md`，写明版本号和路径
- **原型** — 链接到 `planning/{version}/{name}_prototype.html`；无原型时写明跳过原因且不保留空标题
- **Design Overview** — 技术方案概述
- **Dialectical Analysis**（注释块，不可见）— 多路径对比：方案 A vs 方案 B 的权衡；参考的 upstream/reference 亮点；风险对冲（最可能失败的点 + 预备方案）
- **Scoping and Materialization** — 变更范围界定

### Step 4: specs/ — 验收规格

每 capability 一个 `specs/{capability}/spec.md`：

```markdown
## ADDED Requirements

### Requirement: {标题}
{描述}

#### Scenario: {场景名}
- **GIVEN** {前置条件}
- **WHEN** 用户{操作}
- **THEN** 系统{结果}
```

每 capability 至少包含一个边缘案例（Edge Case）场景。

边缘案例要求（引自 `.claude/rules/coding-ace-dialectical-plugin.md`）：
> 每一个新 Capability 必须至少包含一个"Edge Case"（边缘案例）的 Scenario。

### Step 5: design.md — 详细设计

包含数据结构、API 契约、状态迁移、模块交互等。

### Step 6: tasks.md — 实现任务

**强制规则**（引自 ace-planner 规范）：
- 使用 **vertical slicing**（端到端切片，禁止水平分层）
- 每一切片完成一个完整的用户可见功能
- 示例（正确）："用户注册 → 邮箱验证 → 登录"
- 示例（错误）："建数据库表 → 写 API → 画 UI"

### Step 7: 验证

```bash
openspec validate "{name}"
```

## 规范引用

| 引用 | 来源 | 适用 Artifact |
|------|------|------|
| 辩证分析（方案对比） | `.claude/rules/coding-ace-dialectical-plugin` | proposal.md |
| 边缘案例（Edge Case） | `.claude/rules/coding-ace-dialectical-plugin` | specs/ |
| proposal 链接 PRD + 原型 | ace-planner Phase 3 | proposal.md |
| Vertical Slicing 切片 | ace-planner Phase 3 | tasks.md |
| GIVEN/WHEN/THEN 格式 | ace-planner Phase 3 | specs/ |
