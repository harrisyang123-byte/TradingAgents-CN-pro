---
name: ace-retro
description: "复盘阶段：从已完成变更中提取经验、识别模式、沉淀最佳实践。当用户说「复盘」「总结经验」「retro」「复盘 XX」或复杂变更归档后触发。"
tools: ["Read", "Write", "Grep", "Glob", "Bash"]
---

# ace-retro

## 安全基线

- 基于数据分析，不主观臆断
- 不在复盘阶段实现改进（记录到 Decisions，后续通过 ace-planner 处理）
- 沉淀可复用模式，不写流水账
- 改进措施要具体可执行

## Gate

```bash
test -f domain.yaml || { echo "请在 domains/{project}/ 目录下运行"; exit 1; }
cat docs/wiki/index.md 2>/dev/null
```

**建议**：变更已归档（openspec/changes/archive/ 中存在）

**可选**：正在进行的变更也可复盘（阶段性总结）

```bash
ls openspec/changes/archive/ 2>/dev/null
```

无条件阻塞 — 用户指定复盘对象即可开始。

---

## 流程

### Step 1: 确定复盘范围

| 范围 | 输入 | 典型场景 |
|------|------|---------|
| **单个变更** | 变更名 | 复杂功能完成后 |
| **多个变更** | 标签/时间段 | 版本发布前 |
| **项目整体** | 无 | 项目里程碑 |

### Step 2: 收集数据

**变更 artifacts**：
```bash
cat openspec/changes/archive/<name>/proposal.md   # 目标和范围
cat openspec/changes/archive/<name>/tasks.md      # 实际工作量
cat openspec/changes/archive/<name>/design.md     # 技术决策
```

**状态日志**：
```bash
jq 'select(.change=="<name>")' .claude/state/*.jsonl
```

**Git 历史**：
```bash
git log --all --grep="<name>" --oneline
```

**度量**（可选）：代码行数变化、文件数、测试覆盖率、实际 vs 预估耗时。

### Step 3: W.W.L.D 四维分析

**What Went Well** — 哪些做得好？为什么？哪些预测准确？

**What Went Wrong** — 哪里卡住了？哪些返工了？哪些预测失误？

**Lessons Learned** — 学到了什么？有哪些可复用的模式？如何避免类似问题？对每条 lesson 用 Grill 方法论拷问：这条经验是否真正可泛化？适用条件是什么？边界在哪？⚠ 自检：你清楚 Grill 的拷问方法吗？不确定先读 `skills/grill/SKILL.md`。

**Decisions to Make** — 哪些流程需要调整？哪些规范需要补充？

每个维度按阶段（规划/实现/工具流程）组织，附具体证据。

### Step 3.5: 架构深度检查

参考 Matt Pocock zoom-out 思维（`.tmp/references/mattpocock-skills/skills/engineering/zoom-out/SKILL.md`）和 deep module 理念：

```
架构健康检查:
├── 本次变更引入了新模块吗？
│   └── Deletion test：假设删掉它，复杂度去了哪里？
│       如果删掉后复杂度只是换了个地方 → shallow module 警告
├── 接口是否比实现更简单？（deep module 标志）
│   └── 接口复杂但实现简单 → pass-through 警告，考虑合并
└── 模块边界是否在变更中被侵蚀？
    └── 跨层调用、循环依赖 → 标记为架构债务
```

### Step 4: 沉淀最佳实践

根据 Lessons 沉淀可复用知识：

| 类型 | 沉淀位置 | 典型内容 |
|------|---------|---------|
| 技术模式 | docs/wiki/patterns.md | 设计模式、最佳实践 |
| 复盘报告 | docs/wiki/retros/{change-name}.md | W.W.L.D 完整记录 |
| 规范更新 | domain.yaml 或项目 CLAUDE.md | 编码规范、测试标准 |

沉淀后**必须更新 `docs/wiki/index.md`**，保持导航完整。

### Step 5: 输出复盘总结

```
## Retro: <change-name>

**复杂度**: <level>
**耗时**: <实际> 天（预估 <预估> 天）

### 亮点
- [成功点]

### 问题
- [问题点]

### 经验
- [沉淀的文档]

### 改进
- [ ] [待改进项 → 后续通过 ace-planner 创建提案]
```

### Step 6: 记录事件

```bash
echo '{"ts":"<ISO>","agent":"ace-retro","event":"completed","change":"<name>"}' >> .claude/state/archive-log.jsonl
```

---

## 复盘频率建议

| 节点 | 范围 | 频率 |
|------|------|------|
| 复杂变更完成 | 单个 | 每次 |
| 中等变更完成 | 单个 | 可选 |
| 简单变更完成 | — | 跳过 |
| 版本发布 | 里程碑 | 每次 |

## Handoff

复盘完成后通知编排器。如果 Decisions 中有需要改进的项，建议通过 ace-planner 创建优化提案。

## Skill Stack

| Skill | Condition | Purpose |
|-------|-----------|---------|
| grill | Lessons Learned 阶段拷问经验是否可泛化 | 结构化追问方法论 |
