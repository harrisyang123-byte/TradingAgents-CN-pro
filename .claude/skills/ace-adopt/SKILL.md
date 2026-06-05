---
name: ace-adopt
description: "为已有项目接入 ACE 基础设施。自动检测技术栈和服务配置，生成 domain.yaml�"
disable-model-invocation: true
---

# ace-adopt

为已有项目接入 ACE 基础设施。自动检测技术栈和服务配置，生成 domain.yaml，然后调 ace-generate。

## 用法

```
/ace-adopt
```

在 `domains/<project>/` 目录下运行。项目必须已有代码但没有 domain.yaml。

## 与 ace-init 的区别

| | ace-init | ace-adopt |
|---|---------|----------|
| 场景 | 从零创建新项目 | 已有项目接入 ACE |
| 目录结构 | 创建 | 保留现有，补缺失 |
| domain.yaml | 问用户生成 | 自动检测 + 用户确认 |
| 代码 | 无 | 已有 |

## 执行流程

### Step 1: 前置检查

```bash
# 检查 domain.yaml 是否已存在
if [ -f domain.yaml ]; then
  # 展示当前配置摘要，询问用户意图
  echo "domain.yaml 已存在，当前配置："
  grep -E '^(name|description|tech_stack|frontend|backend|database):' domain.yaml | head -10
fi

# 确认有代码
ls package.json */package.json docker-compose.yml 2>/dev/null | head -5
```

**domain.yaml 已存在时的处理**：

询问用户：

1. **重新检测覆盖** — 忽略现有 domain.yaml，重新从代码检测技术栈（适用于 domain.yaml 与实际代码不匹配的情况）
2. **保留现有，只补基础设施** — 跳到 Step 5 补目录 + Step 6 跑 ace-generate（适用于 domain.yaml 正确但缺 CLAUDE.md 等文件）
3. **退出** — 什么也不做

选择 1 → 继续 Step 2（自动检测），检测结果覆盖现有 domain.yaml。
选择 2 → 跳到 Step 5。
选择 3 → 退出。

### Step 2: 自动检测

扫描项目，推断技术栈和服务配置。**检测结果列表展示，用户确认后再写文件。**

#### 2.1 检测项目名

```bash
# 从目录名推断
basename "$(pwd)"
```

#### 2.2 检测技术栈

```bash
# 前端
ls frontend/package.json 2>/dev/null && cat frontend/package.json | grep -E '"react"|"vue"|"angular"|"svelte"' | head -3

# 后端
ls backend/package.json 2>/dev/null && cat backend/package.json | grep -E '"express"|"fastify"|"nestjs"|"koa"' | head -3

# ORM
cat backend/package.json 2>/dev/null | grep -E '"prisma"|"typeorm"|"sequelize"|"drizzle"' | head -3

# 数据库
cat docker-compose.yml 2>/dev/null | grep -E 'postgres|mysql|mongo|redis' | head -3
```

推断规则：
- 有 `@prisma/client` → `node-ts-prisma`
- 有 `react` → `react-ts`（检查 tsconfig 确认 TS）
- docker-compose 有 `postgres` → `postgresql`

#### 2.3 检测服务端口

```bash
# 后端端口：从源码或 .env 读
grep -rn "PORT\|listen" backend/src/ 2>/dev/null | grep -E '\d{4}' | head -5
cat backend/.env 2>/dev/null | grep PORT

# 前端端口：从 vite.config 或 package.json 读
grep -n "port" frontend/vite.config.* 2>/dev/null
grep -n "port" frontend/vue.config.* 2>/dev/null

# 数据库端口：从 docker-compose 读
grep -A2 "ports:" docker-compose.yml 2>/dev/null | grep -E '\d{4}:\d{4}'
```

**端口验证**：如果 vite.config 没有显式端口，标记为"未显式配置，建议设置"。

#### 2.4 检测数据库配置

```bash
# 容器名
grep "container_name:" docker-compose.yml 2>/dev/null

# 凭证
grep -E "POSTGRES_|MYSQL_" docker-compose.yml 2>/dev/null
```

#### 2.5 检测健康检查

```bash
# 后端是否有 /health 端点
grep -rn "health\|/health" backend/src/ 2>/dev/null | head -5
```

### Step 3: 展示检测结果

将检测结果格式化展示，让用户确认或修正：

```
检测结果：

  项目名:    flight-board
  前端:      react-ts (React 19, Vite 8)
  后端:      node-ts-prisma (Express 4.21, Prisma 6.9)
  数据库:    postgresql (Docker)

  服务:
    database:  port 5432, container flight-board-db
    backend:   port 3001, depends [database]
    frontend:  port 5174, depends [backend]
               ⚠ vite.config.ts 未显式设置端口，建议补上

  健康检查:  GET /health ✓

有需要修正的吗？确认后生成 domain.yaml。
```

用户确认 → Step 4。用户修正 → 更新检测结果后再确认。

### Step 4: 生成 domain.yaml

根据确认后的检测结果，按 ace-init Step 4 的模板生成 domain.yaml。

### Step 5: 补缺失目录

```bash
# 只创建不存在的目录
mkdir -p docs/wiki
mkdir -p openspec/changes
mkdir -p openspec/archive
mkdir -p .claude/state
```

### Step 6: 调 ace-generate

运行 `/ace-generate` 生成 CLAUDE.md + 三件套 + .gitignore。

### Step 7: 端口一致性修复

检查源码中的端口是否与 domain.yaml 一致：

```bash
# 如果 vite.config 没有显式端口，提示用户
grep "port" frontend/vite.config.* 2>/dev/null || echo "⚠ 建议在 vite.config 中显式设置 server.port: ${FRONTEND_PORT}"
```

列出不一致项，建议修复（不自动改源码）。

### Step 8: 输出摘要

```
✓ 项目 {name} 已接入 ACE

  生成文件：
  ├── domain.yaml          ← 项目配置（自动检测）
  ├── CLAUDE.md            ← AI 协作指令
  ├── start.sh             ← 一键启动
  ├── stop.sh              ← 一键停止
  ├── status.sh            ← 服务状态
  └── .gitignore           ← Git 忽略规则

  补充目录：
  ├── docs/wiki/index.md   ← 知识库
  ├── openspec/            ← 变更追踪
  └── .claude/state/       ← 状态日志

  ⚠ 建议检查：
  {列出端口不一致等警告}

  下一步：
  ./start.sh 启动服务验证
  告诉我想做什么功能，走 ACE 工作流
```

## 注意事项

- 不修改已有代码（只生成新文件和目录）
- 端口不一致只提示，不自动改源码
- 检测结果必须用户确认后再生成，不自作主张
- 如果项目结构非标准（无 frontend/backend 目录），退化为交互式问答（类似 ace-init）
- domain.yaml 已存在时不直接拒绝，而是展示现有配置并询问用户意图（覆盖/补基础设施/退出）
