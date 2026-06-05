---
name: ace-learn
description: "在实现过程中即时捕获发现的模式或经验到项目知识库。"
disable-model-invocation: true
---

# ace-learn

在实现过程中即时捕获发现的模式或经验到项目知识库。

## 用法

```
/ace-learn <主题>
```

示例：`/ace-learn npm 进程树停止策略`

## 执行流程

### Step 1: 提取发现

从当前对话上下文中提取与主题相关的关键发现：

- **是什么** — 发现的模式、陷阱或最佳实践
- **为什么重要** — 不知道的话会踩什么坑
- **怎么用** — 具体的代码示例或操作步骤

不写流水账。只记可复用的、下次遇到能直接用的知识。

### Step 2: 写入 wiki

判断写入位置：

- 如果 `docs/wiki/patterns.md` 存在且主题属于通用模式 → 追加到 patterns.md
- 如果主题足够独立（如"bash 脚本陷阱"）→ 新建 `docs/wiki/{topic}.md`
- 更新 `docs/wiki/index.md` 导航

格式：

```markdown
## {主题}

> 来源：{当前变更名或会话上下文}

{是什么}

{为什么重要}

{怎么用——代码示例}
```

### Step 3: 可选 — 同步 Claude memory

如果发现的模式**跨项目通用**（不只适用于当前项目），询问用户是否同步到 Claude memory：

```
这个模式适用于所有项目，要同步到 Claude memory 吗？（跨会话可用）
```

用户确认 → 写入 memory 文件。用户跳过 → 只保留在项目 wiki。

### Step 4: 输出确认

```
✓ 已捕获：{主题}
  位置：docs/wiki/{file}.md
  索引：docs/wiki/index.md 已更新
  Memory：{已同步 / 未同步}
```

## 与 archiver/retro 的区别

| 时机 | 工具 | 特点 |
|------|------|------|
| 实现中发现时 | `/ace-learn` | 上下文最完整，即时捕获 |
| 归档时 | archiver | 从 artifacts 提取，系统化 |
| 复盘时 | retro | W.W.L.D 分析，回顾性 |

三者互补，不冲突。ace-learn 捕获的内容可能在 retro 时被进一步分析。

## 注意事项

- 不写重复知识——先读 `docs/wiki/index.md` 检查是否已有相关页面
- 不写项目特有的临时状态（"当前 PR 在等审批"）——那是 task/memory 的事
- 保持精炼——一个主题一页，不超过 50 行
