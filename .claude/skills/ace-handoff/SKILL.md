---
name: ace-handoff
description: "会话即将中断时，生成交接文档供下次会话快速接续。"
disable-model-invocation: true
---

# ace-handoff

会话即将中断时，生成交接文档供下次会话快速接续。

## 执行流程

### Step 1: 检测当前状态

```bash
# 确认在项目目录
test -f domain.yaml || { echo "请在 domains/{project}/ 目录下运行"; exit 1; }

# 检查活跃变更
openspec list 2>/dev/null

# 检查未提交变更
git status --short

# 最近 commit
git log --oneline -5
```

### Step 2: 识别当前阶段

根据收集到的信息判断用户当前处于 ACE workflow 的哪个阶段：

```
阶段判断:
├── 有活跃 change 且 tasks.md 有 [ ] → applier 阶段
├── 有活跃 change 但无 tasks.md → planner 阶段
├── 有未提交代码但无活跃 change → 自由编码（非 ACE 流程）
└── 全部 clean → 空闲
```

如果在 applier 阶段，读取 tasks.md 统计进度：

```bash
DONE=$(grep -c '\[x\]' openspec/changes/{change}/tasks.md 2>/dev/null || echo 0)
TODO=$(grep -c '\[ \]' openspec/changes/{change}/tasks.md 2>/dev/null || echo 0)
echo "进度: $DONE/$(($DONE+$TODO)) tasks"
```

### Step 3: 生成交接文档

输出格式（直接在对话中输出，不写文件）：

```markdown
## 会话交接

**项目**: {project-name}
**日期**: {YYYY-MM-DD}
**当前阶段**: {planner / applier / reviewer / archiver / 空闲}

### 进度
- 活跃变更: {change-name}（{N/M} tasks 完成）
- 当前 task: {当前正在做的 task 描述}
- 未提交变更: {N files}

### 未完成的决策
- {列出对话中讨论过但未决定的问题}

### 开放问题
- {列出遇到的阻塞或需要用户后续输入的问题}

### 下次入口
建议用以下方式开始下次会话：
1. `cd domains/{project}`
2. 告诉 AI: "继续 {change-name} 的实现"（或对应阶段的触发词）

### 关键 Artifacts
- 提案: openspec/changes/{change}/proposal.md
- 设计: openspec/changes/{change}/design.md
- 任务: openspec/changes/{change}/tasks.md
- 知识库: docs/wiki/index.md
```

**原则**：引用 artifacts 路径，不复制内容。交接文档是指针，不是快照。
