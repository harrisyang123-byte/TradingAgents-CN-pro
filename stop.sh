#!/bin/bash
# tradingagents-cn - 停止脚本

set +e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PID_DIR="$SCRIPT_DIR/.pids"
LOG_DIR="$SCRIPT_DIR/.logs"

mkdir -p "$PID_DIR" "$LOG_DIR"

stop_service() {
  local name="$1"
  local port="$2"
  local pid_file="$PID_DIR/${name}.pid"
  local had_something=false

  # Port cleanup
  if [ -n "$port" ]; then
    local port_pids
    port_pids=$(lsof -ti :"$port" 2>/dev/null || true)
    if [ -n "$port_pids" ]; then
      echo "$port_pids" | xargs kill 2>/dev/null || true
      sleep 1
      port_pids=$(lsof -ti :"$port" 2>/dev/null || true)
      if [ -n "$port_pids" ]; then
        echo "$port_pids" | xargs kill -9 2>/dev/null || true
      fi
      had_something=true
    fi
  fi

  # PID file cleanup
  if [ -f "$pid_file" ]; then
    local pid
    pid=$(cat "$pid_file")
    if kill -0 "$pid" 2>/dev/null; then
      kill -9 "$pid" 2>/dev/null || true
      had_something=true
    fi
    rm -f "$pid_file"
    [ "$had_something" = false ] && had_something=true
  fi

  if [ "$had_something" = true ]; then
    echo "  Stopped ${name}"
  else
    echo "  ${name} not running"
  fi
}

echo "Stopping TradingAgents-CN..."

echo "Frontend..."
stop_service "frontend" "$(grep -A2 "^  frontend:" "$SCRIPT_DIR/domain.yaml" 2>/dev/null | grep "port:" | sed 's/.*port:\s*//' | tr -d ' ')"

echo "Backend..."
stop_service "backend" "$(grep -A2 "^  backend:" "$SCRIPT_DIR/domain.yaml" 2>/dev/null | grep "port:" | sed 's/.*port:\s*//' | tr -d ' ')"

echo "Docker services..."
cd "$SCRIPT_DIR"
docker compose down 2>/dev/null && echo "  Docker services stopped" || echo "  No Docker services to stop"

echo "All services stopped."
