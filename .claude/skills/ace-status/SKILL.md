---
name: ace-status
description: "读取当前项目的 `domain.yaml`，检测各服务运行状态，输出状态面板。"
disable-model-invocation: true
---

# ace-status

读取当前项目的 `domain.yaml`，检测各服务运行状态，输出状态面板。

## 执行流程

### Step 1: 读取 domain.yaml

```bash
test -f domain.yaml || { echo "请在 domains/{project}/ 目录下运行"; exit 1; }
```

读取 `domain.yaml` 的 `services` 段，提取每个服务的名称和端口。

如果 `domain.yaml` 不包含 `services` 段，输出提示：

```
domain.yaml 中未定义 services，请先配置。
```

### Step 2: 检测端口状态

对每个服务，用 `lsof` 检测端口是否有进程监听：

```bash
lsof -i :{port} -sTCP:LISTEN -t >/dev/null 2>&1 && echo "UP" || echo "DOWN"
```

### Step 3: 输出状态表格

```
┌──────────┬──────┬────────┐
│ Service  │ Port │ Status │
├──────────┼──────┼────────┤
│ database │ 5432 │ ✓ UP   │
│ backend  │ 3000 │ ✗ DOWN │
│ frontend │ 5173 │ ✗ DOWN │
└──────────┴──────┴────────┘
```

如果有 DOWN 的服务，附带启动建议：

```
启动建议：
  database: docker compose up -d（或检查 PostgreSQL 服务）
  backend:  cd backend && npm run dev
  frontend: cd frontend && npm run dev
```

启动命令从 `domain.yaml` 的 `scripts.dev:*` 段读取。
