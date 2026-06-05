---
name: ace-init
description: "在 `domains/` 下创建新项目，生成标准目录结构和 domain.yaml。"
disable-model-invocation: true
---

# ace-init

在 `domains/` 下创建新项目，生成标准目录结构和 domain.yaml。

## 用法

```
/ace-init <project-name>
```

## 执行流程

### Step 1: 收集项目信息

向用户询问（一次一问，给推荐选项）：

1. **项目描述** — 一句话说明项目做什么
2. **技术栈** — 前端 / 后端 / 数据库各用什么（推荐：react-ts / node-ts-prisma / postgresql）
3. **是否需要 Docker** — 默认 yes

不需要的信息跳过，用默认值。

### Step 2: 环境检测

检测用户机器上的必要工具，输出状态报告。**不自动安装**（避免权限问题），缺失时给安装指引。

```bash
# 检测必要工具
echo "环境检测:"

# Node.js
if command -v node >/dev/null 2>&1; then
  NODE_VER=$(node -v)
  if echo "$NODE_VER" | grep -qE '^v(18|20|22|24)'; then
    echo "  ✓ Node.js $NODE_VER"
  else
    echo "  ⚠ Node.js $NODE_VER（需要 v18+，建议升级：nvm install 20）"
  fi
else
  echo "  ✗ Node.js 未安装（安装：https://nodejs.org 或 brew install node）"
fi

# npm
command -v npm >/dev/null 2>&1 && echo "  ✓ npm $(npm -v)" || echo "  ✗ npm 未安装（随 Node.js 一起安装）"

# Git
command -v git >/dev/null 2>&1 && echo "  ✓ Git $(git --version | cut -d' ' -f3)" || echo "  ✗ Git 未安装（安装：brew install git）"

# Docker（可选）
if command -v docker >/dev/null 2>&1; then
  docker ps >/dev/null 2>&1 && echo "  ✓ Docker $(docker --version | cut -d' ' -f3 | tr -d ',')" || echo "  ⚠ Docker 已安装但未运行（请启动 Docker Desktop）"
else
  echo "  ⚠ Docker 未安装（可选，安装：https://docs.docker.com/get-docker/）"
fi

# tmux（可选，dev server 需要）
command -v tmux >/dev/null 2>&1 && echo "  ✓ tmux $(tmux -V | cut -d' ' -f2)" || echo "  ⚠ tmux 未安装（dev server 建议使用，安装：brew install tmux）"
```

如果有关键工具缺失（Node.js 或 Git），提示用户先安装再继续，但不阻塞流程。

### Step 3: 创建目录结构

```bash
PROJECT_DIR="domains/{project-name}"

mkdir -p "$PROJECT_DIR"
mkdir -p "$PROJECT_DIR/docs/wiki"
mkdir -p "$PROJECT_DIR/planning/v0.1"
mkdir -p "$PROJECT_DIR/openspec/changes"
mkdir -p "$PROJECT_DIR/openspec/archive"
mkdir -p "$PROJECT_DIR/.claude/state"
```

### Step 4: 生成 domain.yaml

根据用户回答填充模板：

```yaml
name: {project-name}
description: {用户输入的描述}
version: 0.1.0

tech_stack:
  frontend: {用户选择}
  backend: {用户选择}
  database: {用户选择}

services:
  # 如果用户选择了 database：
  database:
    type: {tech_stack.database}         # postgresql / mysql 等
    port: 5432                          # postgresql=5432, mysql=3306
    environment:
      POSTGRES_DB: {project-name}
      POSTGRES_USER: {project-name}user
      POSTGRES_PASSWORD: {project-name}pass

  backend:
    port: 3000
    dependencies:
      - database                        # 无 database 时删除此行
    environment:
      DATABASE_URL: "postgresql://{user}:{pass}@localhost:{db_port}/{dbname}"
      PORT: 3000

  # 如果用户选择了 frontend：
  frontend:
    port: 5173                          # Vite 默认
    dependencies:
      - backend
    environment:
      VITE_API_URL: "http://localhost:3000"

lifecycle:
  pid_dir: .pids
  log_dir: .logs
  health_check:
    backend: /health
    timeout: 30

scripts:
  dev: "{根据技术栈生成}"
  test: "{根据技术栈生成}"
  build: "{根据技术栈生成}"

coding_standards:
  backend:
    - "{根据技术栈生成通用规范}"
  frontend:
    - "{根据技术栈生成通用规范}"

testing:
  unit_test_coverage: 80
  e2e_test_required: false
  test_framework: "{根据技术栈选择}"
  test_commands:
    unit: "{根据技术栈生成}"

knowledge:
  always_load:
    - path: docs/wiki/index.md
      desc: 项目知识库导航入口
  on_demand:
    - path: docs/wiki/
      trigger: "涉及项目知识、技术方案、业务规则时"

planning:
  current_version: v0.1
```

### Step 5: 生成知识库骨架

写入 `docs/wiki/index.md`：

```markdown
# {project-name} 知识库

> 由 ACE workflow 自动维护。archiver 归档时写入知识，retro 复盘时沉淀模式。

## 页面导航

（暂无知识页面，完成第一个变更归档后自动生成）

## 模式与最佳实践

- [patterns.md](patterns.md) — 技术模式与最佳实践（待创建）
```

### Step 6: 生成 openspec config

写入 `openspec/config.yaml`：

```yaml
version: "1.0"
change_dir: changes
archive_dir: archive
```

### Step 7: 调用 ace-generate

在项目目录下运行 `/ace-generate` 生成 CLAUDE.md、start.sh、stop.sh、status.sh、.gitignore。

### Step 8: 可选 — 生成 Docker 环境

如果用户选择需要 Docker **且** domain.yaml 中有 database 配置，**必须**生成以下文件：

**docker-compose.yml**（根据 database 类型生成）：

```yaml
# PostgreSQL 示例
services:
  db:
    image: postgres:15-alpine
    container_name: {project-name}-db
    environment:
      POSTGRES_USER: {project-name}user
      POSTGRES_PASSWORD: {project-name}pass
      POSTGRES_DB: {project-name}
    ports:
      - "{domain.yaml services.database.port}:5432"
    volumes:
      - {project-name}-data:/var/lib/postgresql/data

volumes:
  {project-name}-data:
```

**backend/.env**：

```bash
DATABASE_URL="postgresql://{user}:{pass}@localhost:{port}/{dbname}"
PORT={domain.yaml services.backend.port}
NODE_ENV=development
```

此步骤**不可跳过** — 没有 docker-compose.yml，数据库无法启动，后续 Prisma migrate 会失败。

### Step 9: 输出摘要

```
✓ 项目 {project-name} 创建完成

目录结构：
  domains/{project-name}/
  ├── domain.yaml          ← 项目配置
  ├── CLAUDE.md            ← AI 协作指令（已生成）
  ├── start.sh             ← 一键启动（已生成）
  ├── stop.sh              ← 一键停止（已生成）
  ├── status.sh            ← 服务状态（已生成）
  ├── .gitignore           ← Git 忽略规则（已生成）
  ├── openspec/            ← 变更追踪
  ├── docs/wiki/index.md   ← 知识库
  └── planning/v0.1/       ← 版本规划

下一步：
  cd domains/{project-name}
  告诉我你想做什么功能，我会走 ACE 工作流帮你实现。

提示：
  实现过程中技术栈变了？运行 /ace-adopt 重新检测配置。
```
