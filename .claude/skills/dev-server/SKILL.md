---
name: dev-server
description: Start and stop the TradingAgents-CN development servers (backend + frontend)
---

# Dev Server — 启动 / 停止开发环境

## 前置条件

- MongoDB 和 Redis 必须已运行（本机或 Docker）
- Python venv 已创建在 `.venv/`
- Node 依赖已安装：`cd frontend && npm install`

## 启动

```bash
# 1. 后端（8000 端口）
cd /Users/yangyanyu/AI-Coding-Engine/domains/tradingagents-cn
source .venv/bin/activate
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 &

# 2. 前端（3000 端口）
cd /Users/yangyanyu/AI-Coding-Engine/domains/tradingagents-cn/frontend
npm run dev &
```

## 停止

```bash
# 后端
pkill -f "uvicorn app.main:app"

# 前端
pkill -f "node.*vite"
```

## 验证

```bash
# 后端健康检查
curl -s http://localhost:8000/api/health | python3 -c "import sys,json; print(json.load(sys.stdin).get('message',''))"

# 前端可达性
curl -s -o /dev/null -w "%{http_code}" http://localhost:3000
```

## 当前运行状态检查

```bash
pgrep -f "uvicorn|vite" && echo "✅ 运行中" || echo "❌ 未运行"
```
