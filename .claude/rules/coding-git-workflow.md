# Git 工作流规范

ACE Engine 的 Git 工作流规范，确保代码管理清晰、可追溯。

---

## 核心原则

1. **小步提交**: 每次提交只做一件事
2. **清晰描述**: 提交信息要说明"为什么"，不只是"是什么"
3. **保持主干清洁**: main/master 分支始终可部署
4. **基于特性分支**: 所有开发在独立分支进行

---

## 分支策略

### 主干分支

**main** (或 master):
- 受保护，不允许直接推送
- 始终保持可部署状态
- 所有代码通过 Pull Request 合并

### 开发分支

**命名格式**: `<type>/<short-description>`

```bash
# ✅ 正确
feature/add-user-authentication
fix/login-token-expiration
docs/update-readme
refactor/simplify-api-error-handling

# ❌ 错误
my-branch                    # 不语义化
feature_add_authentication   # 不是连字符
fix-bug                      # 太模糊
```

**类型（type）**:
- `feature/`: 新功能
- `fix/`: 修复 bug
- `docs/`: 文档变更
- `refactor/`: 重构
- `test/`: 测试相关
- `chore/`: 构建/工具变更
- `hotfix/`: 紧急修复（直接从 main 拉取）

---

## 提交信息规范

### 格式

```
<type>(<scope>): <subject>

<body>

<footer>
```

### 必需部分：Header

**格式**: `<type>(<scope>): <subject>`

```bash
# ✅ 正确
feat(todo): add create todo API
fix(auth): resolve login token expiration issue
docs(readme): add installation instructions
refactor(api): simplify error handling logic
test(todo): add unit tests for CRUD operations

# ❌ 错误
Added new feature              # 没有类型
Fix bug                        # 太模糊，首字母大写
update                         # 没有 scope，太简单
feat: add todo                 # 没有 scope
```

**type（类型）**:
- `feat`: 新功能
- `fix`: 修复 bug
- `docs`: 文档
- `style`: 代码格式（不影响功能）
- `refactor`: 重构
- `perf`: 性能优化
- `test`: 测试
- `build`: 构建系统
- `ci`: CI/CD 配置
- `chore`: 其他（不修改 src 或 test）

**scope（范围）**:
- 受影响的模块/组件名称
- 小写，kebab-case
- 示例: `todo`, `auth`, `api`, `database`, `frontend`

**subject（主题）**:
- 简短描述（50 字符以内）
- 动词开头，现在时（"add" 不是 "added"）
- 首字母小写
- 结尾不加句号

### 可选部分：Body

详细说明**为什么**做这个改动，不是**什么**改动（代码已经说明了"是什么"）

```
feat(todo): add priority field to todo items

Users requested the ability to prioritize tasks. This commit adds
a priority field (high/medium/low) to the Todo model and updates
the API to support filtering by priority.

The frontend UI changes will be in a separate commit.
```

### 可选部分：Footer

**Breaking Changes**:
```
feat(api): change todo API response format

BREAKING CHANGE: The API response now returns `data` instead of `todos`.
Clients need to update from `response.todos` to `response.data`.
```

**关联 Issue**:
```
fix(auth): resolve token expiration bug

Closes #123
Fixes #456
```

---

## 提交频率

### 何时提交

✅ **应该提交**:
- 完成一个小功能（可运行）
- 修复一个 bug（可验证）
- 重构一个模块（测试通过）
- 添加文档或注释

❌ **不应该提交**:
- 代码无法运行
- 测试不通过
- 包含调试代码（console.log）
- 混合多个不相关的改动

### 提交粒度

**原则**: 每次提交只做一件事

```bash
# ✅ 正确：分开提交
git commit -m "feat(todo): add Todo model and schema"
git commit -m "feat(todo): add create todo API endpoint"
git commit -m "test(todo): add unit tests for create todo"

# ❌ 错误：一次提交太多
git commit -m "feat(todo): add complete todo feature with tests and docs"
```

---

## Pull Request 规范

### PR 标题

与提交信息相同格式：

```
feat(todo): add priority filtering
fix(auth): resolve token expiration
docs(api): update REST API documentation
```

### PR 描述模板

```markdown
## 改动内容

简要描述这个 PR 做了什么。

## 改动原因

为什么需要这个改动？解决了什么问题？

## 改动类型

- [ ] 新功能 (feature)
- [ ] Bug 修复 (fix)
- [ ] 文档更新 (docs)
- [ ] 重构 (refactor)
- [ ] 测试 (test)
- [ ] 其他 (chore)

## 测试

如何测试这个改动？

- [ ] 单元测试通过
- [ ] 手动测试通过
- [ ] 新增测试覆盖

## 截图（如有 UI 改动）

[可选：添加截图]

## 关联 Issue

Closes #123
```

### PR 审查检查清单

审查者应检查：

- [ ] 代码符合命名规范
- [ ] 提交信息清晰
- [ ] 测试充分
- [ ] 文档已更新（如需要）
- [ ] 没有调试代码（console.log, debugger）
- [ ] 没有硬编码的密钥或敏感信息

---

## 常见工作流

### 开发新功能

```bash
# 1. 从 main 拉取最新代码
git checkout main
git pull origin main

# 2. 创建特性分支
git checkout -b feature/add-priority-field

# 3. 开发 + 提交（小步提交）
# ... 编码 ...
git add src/models/todo.ts
git commit -m "feat(todo): add priority field to Todo model"

# ... 编码 ...
git add src/api/todos.ts
git commit -m "feat(todo): add priority filter to API"

# 4. 推送到远程
git push origin feature/add-priority-field

# 5. 创建 Pull Request（在 GitHub/GitLab 上）

# 6. 合并后删除本地分支
git checkout main
git pull origin main
git branch -d feature/add-priority-field
```

### 修复 Bug

```bash
# 1. 创建修复分支
git checkout -b fix/login-token-expiration

# 2. 修复 + 测试 + 提交
git add src/auth/token.ts
git commit -m "fix(auth): extend token expiration to 7 days"

git add tests/auth.test.ts
git commit -m "test(auth): add test for token expiration"

# 3. 推送并创建 PR
git push origin fix/login-token-expiration
```

### 同步 main 分支的更新

```bash
# 在特性分支上
git checkout feature/my-feature

# 拉取 main 的最新代码
git fetch origin main

# 选项 A: Rebase（推荐，保持线性历史）
git rebase origin/main

# 选项 B: Merge（如果已经推送到远程）
git merge origin/main

# 解决冲突后推送
git push origin feature/my-feature --force-with-lease  # 如果用了 rebase
```

---

## 冲突解决

### 合并冲突

```bash
# 1. 拉取最新 main
git fetch origin main
git rebase origin/main

# 2. 如果有冲突，Git 会暂停
# <<<<<<< HEAD
# 你的代码
# =======
# main 分支的代码
# >>>>>>> origin/main

# 3. 手动解决冲突后
git add <解决冲突的文件>
git rebase --continue

# 4. 如果想放弃 rebase
git rebase --abort
```

---

## 禁止事项

❌ **永远不要**:

1. **直接推送到 main**
   ```bash
   git push origin main  # ❌ 禁止
   ```

2. **强制推送到 main**
   ```bash
   git push origin main --force  # ❌❌❌ 极度危险
   ```

3. **提交敏感信息**
   ```bash
   # .env
   DATABASE_PASSWORD=secret123  # ❌ 不要提交到 Git
   
   # 使用 .gitignore
   .env
   .env.local
   *.key
   *.pem
   ```

4. **修改已推送的提交历史**（除非在自己的分支）
   ```bash
   git rebase -i HEAD~3          # ⚠️ 只在本地分支安全
   git push origin feature --force  # ⚠️ 如果别人已基于此分支，会出问题
   ```

5. **提交 node_modules 或构建产物**
   ```bash
   # .gitignore 应包含：
   node_modules/
   dist/
   build/
   .DS_Store
   *.log
   ```

---

## Git 配置建议

### 全局配置

```bash
# 设置用户信息
git config --global user.name "Your Name"
git config --global user.email "your.email@example.com"

# 默认分支名为 main
git config --global init.defaultBranch main

# 启用颜色输出
git config --global color.ui auto

# 设置默认编辑器
git config --global core.editor "code --wait"  # VSCode

# 启用自动换行转换（Windows）
git config --global core.autocrlf true

# 启用自动换行转换（Mac/Linux）
git config --global core.autocrlf input
```

### 项目级 .gitignore

```gitignore
# Dependencies
node_modules/
.pnp
.pnp.js

# Testing
coverage/

# Production
dist/
build/

# Environment
.env
.env.local
.env.*.local

# IDE
.vscode/
.idea/
*.swp
*.swo

# OS
.DS_Store
Thumbs.db

# Logs
*.log
npm-debug.log*

# Database
*.sqlite
*.db
```

---

## Git Hooks（可选）

使用 Husky 自动化检查：

```json
// package.json
{
  "husky": {
    "hooks": {
      "pre-commit": "npm run lint",
      "commit-msg": "commitlint -E HUSKY_GIT_PARAMS"
    }
  }
}
```

**pre-commit**: 提交前自动运行 lint  
**commit-msg**: 检查提交信息格式

---

## 常用 Git 命令参考

```bash
# 查看状态
git status

# 查看差异
git diff
git diff --staged          # 查看暂存区差异

# 查看提交历史
git log
git log --oneline          # 简洁模式
git log --graph --all      # 图形化所有分支

# 撤销操作
git reset HEAD <file>      # 取消暂存
git checkout -- <file>     # 丢弃工作区改动
git revert <commit>        # 撤销某次提交（创建新提交）

# 分支操作
git branch                 # 列出本地分支
git branch -a              # 列出所有分支（包括远程）
git branch -d <branch>     # 删除已合并分支
git branch -D <branch>     # 强制删除分支

# 暂存工作区
git stash                  # 暂存当前改动
git stash pop              # 恢复最近的暂存
git stash list             # 查看所有暂存
```

---

**更新时间**: 2026-05-11  
**维护者**: ACE Engine Team
