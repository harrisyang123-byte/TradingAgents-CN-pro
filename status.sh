#!/bin/bash
# tradingagents-cn - 服务状态检查

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PID_DIR="$SCRIPT_DIR/.pids"

BACKEND_PORT=$(grep -A2 "^  backend:" "$SCRIPT_DIR/domain.yaml" 2>/dev/null | grep "port:" | sed 's/.*port:\s*//' | tr -d ' ')
FRONTEND_PORT=$(grep -A2 "^  frontend:" "$SCRIPT_DIR/domain.yaml" 2>/dev/null | grep "port:" | sed 's/.*port:\s*//' | tr -d ' ')

: "${BACKEND_PORT:=8000}"
: "${FRONTEND_PORT:=3000}"

check_service() {
  local name="$1"
  local port="$2"
  local pid_file="$PID_DIR/${name}.pid"
  local status="DOWN"
  local pid_info=""

  if curl -s "http://localhost:${port}" > /dev/null 2>&1; then
    status="UP"
  fi

  if [ -f "$pid_file" ]; then
    local saved_pid
    saved_pid=$(cat "$pid_file")
    if kill -0 "$saved_pid" 2>/dev/null; then
      pid_info="PID:${saved_pid}"
    else
      pid_info="PID:stale"
    fi
  fi

  printf "| %-12s | %6s | %-6s | %-10s |\n" "$name" "$port" "$status" "$pid_info"
}

echo "TradingAgents-CN Service Status"
echo "================================"
printf "| %-12s | %6s | %-6s | %-10s |\n" "Service" "Port" "Status" "PID"
printf "|%-14s|%-8s|%-8s|%-12s|\n" "--------------" "--------" "--------" "------------"

check_service "backend" "$BACKEND_PORT"
check_service "frontend" "$FRONTEND_PORT"

echo ""
echo "Docker:"
docker compose ps --format "table {{.Name}}\t{{.Status}}\t{{.Ports}}" 2>/dev/null || echo "  Docker not available"

echo ""
echo "Logs: $SCRIPT_DIR/.logs/"
echo "Start: ./start.sh"
echo "Stop:  ./stop.sh"
