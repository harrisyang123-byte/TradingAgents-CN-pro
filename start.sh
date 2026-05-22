#!/bin/bash
# tradingagents-cn - 一键启动脚本
# 读取 domain.yaml 配置启动服务

set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
DOMAIN_YAML="$SCRIPT_DIR/domain.yaml"
PID_DIR="$SCRIPT_DIR/.pids"
LOG_DIR="$SCRIPT_DIR/.logs"

mkdir -p "$PID_DIR" "$LOG_DIR"

parse_port() {
  local service="$1"
  grep -A5 "^  ${service}:" "$DOMAIN_YAML" 2>/dev/null | grep "port:" | head -1 | sed 's/.*port:\s*//' | tr -d ' '
}

parse_health_path() {
  grep -A3 "health_check:" "$DOMAIN_YAML" 2>/dev/null | grep "backend:" | head -1 | sed 's/.*backend:\s*//' | tr -d ' "'
}

parse_health_timeout() {
  grep -A3 "health_check:" "$DOMAIN_YAML" 2>/dev/null | grep "timeout:" | head -1 | sed 's/.*timeout:\s*//' | tr -d ' '
}

parse_db_container() {
  grep "container_name:" "$SCRIPT_DIR/docker-compose.yml" 2>/dev/null | head -1 | sed 's/.*container_name:\s*//' | tr -d ' '
}

wait_for_url() {
  local url="$1"
  local max_wait="$2"
  local label="$3"
  local elapsed=0
  while [ $elapsed -lt "$max_wait" ]; do
    if curl -s "$url" > /dev/null 2>&1; then
      return 0
    fi
    sleep 2
    elapsed=$((elapsed + 2))
  done
  echo "  Backend not ready within ${max_wait}s"
  return 1
}

wait_for_db() {
  local max_wait="$1"
  local elapsed=0
  while [ $elapsed -lt "$max_wait" ]; do
    local status
    status=$(docker inspect --format='{{.State.Health.Status}}' "$DB_CONTAINER" 2>/dev/null || echo "missing")
    if [ "$status" = "healthy" ]; then
      return 0
    fi
    sleep 2
    elapsed=$((elapsed + 2))
  done
  echo "  Database not ready within ${max_wait}s"
  return 1
}

is_running() {
  local port="$1"
  curl -s "http://localhost:${port}" > /dev/null 2>&1
}

BACKEND_PORT=$(parse_port "backend")
FRONTEND_PORT=$(parse_port "frontend")
DB_PORT=$(parse_port "database")
HEALTH_PATH=$(parse_health_path)
HEALTH_TIMEOUT=$(parse_health_timeout)
DB_CONTAINER=$(parse_db_container)

: "${BACKEND_PORT:=8000}"
: "${FRONTEND_PORT:=3000}"
: "${DB_PORT:=27017}"
: "${HEALTH_PATH:=/api/health}"
: "${HEALTH_TIMEOUT:=30}"

echo "Starting TradingAgents-CN..."

echo "1. Starting Docker services (mongodb + redis)..."
cd "$SCRIPT_DIR"

docker compose up -d mongodb redis 2>&1 | sed 's/^/  /'
echo "  Waiting for services..."
sleep 3

echo "2. Starting backend (port: ${BACKEND_PORT})..."
cd "$SCRIPT_DIR"

# Pre-kill stale processes on this port
port_pids=$(lsof -ti :"$BACKEND_PORT" 2>/dev/null || true)
[ -n "$port_pids" ] && echo "$port_pids" | xargs kill -9 2>/dev/null && sleep 1

echo "  Starting FastAPI server with hot-reload..."
"$SCRIPT_DIR/.venv/bin/uvicorn" app.main:app --host 0.0.0.0 --port "$BACKEND_PORT" --reload --reload-dir "$SCRIPT_DIR/app" > "$LOG_DIR/backend.log" 2>&1 &
BACKEND_PID=$!
echo "$BACKEND_PID" > "$PID_DIR/backend.pid"

if wait_for_url "http://localhost:${BACKEND_PORT}${HEALTH_PATH}" "$HEALTH_TIMEOUT" "Backend"; then
  echo "  Backend ready (PID: ${BACKEND_PID})"
else
  echo "  Backend may not be fully started, check logs: $LOG_DIR/backend.log"
fi

echo "3. Starting frontend (port: ${FRONTEND_PORT})..."
if [ -d "$SCRIPT_DIR/frontend" ]; then
  cd "$SCRIPT_DIR/frontend"

  if [ ! -d "node_modules" ]; then
    echo "  Installing frontend dependencies..."
    npm install > /dev/null 2>&1
  fi

  if is_running "$FRONTEND_PORT"; then
    echo "  Frontend already running"
  else
    # Pre-kill stale processes on this port
    port_pids=$(lsof -ti :"$FRONTEND_PORT" 2>/dev/null || true)
    [ -n "$port_pids" ] && echo "$port_pids" | xargs kill -9 2>/dev/null && sleep 1

    npm run dev > "$LOG_DIR/frontend.log" 2>&1 &
    FRONTEND_PID=$!
    echo "$FRONTEND_PID" > "$PID_DIR/frontend.pid"
    echo "  Frontend starting (PID: ${FRONTEND_PID})"
  fi
else
  echo "  No frontend directory found, skipping"
fi

echo ""
echo "Services:"
echo "  Backend:  http://localhost:${BACKEND_PORT}"
echo "  Frontend: http://localhost:${FRONTEND_PORT}"
echo "  Logs:     $LOG_DIR/"
echo "  Stop:     ./stop.sh"
