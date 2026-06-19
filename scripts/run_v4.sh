#!/bin/bash
# run_v4.sh — v4 分层独立深度投研系统 CLI 入口（FR-004）
#
# 触发链路与 Web 分离：重计算只在本地/AI 代跑触发，Web 仅只读。
# 第 2 阶段（Agent 推理）两种驱动：① 本会话 AI agent 直跑（默认，无需 claude CLI，
#   缺数据源联网补齐而非降级，存档 data/v4/ 单元 JSON，前端走静态快照、Mongo 可选）；
#   ② 本脚本 shell 出 claude -p 子进程（需 claude 鉴权）。完整步骤见 docs/wiki/v4-ai-proxy-run.md。
#
# 用法:
#   ./run_v4.sh analyze <unit-selector> [--user-id <id>] [--portfolio-file <path>] [--full]
#   ./run_v4.sh refresh <unit-selector> [--user-id <id>] [--portfolio-file <path>]
#   ./run_v4.sh status  [--user-id <id>] [--json]
#   ./run_v4.sh scan    [--user-id <id>] [--json]
#
# unit-selector（§5.2）:
#   asset:<class>              大类分析（equity/fixed_income/cash/commodity/precious_metal/real_estate/alternative）
#   plan:<class>               非权益方案
#   alloc:portfolio            七大类资产配比
#   industry:<name>            行业深辩
#   alloc:equity_industries    行业间配比
#   stock:<code>               个股分析
#   alloc:industry:<name>      行业内个股配比
#
# 子命令:
#   analyze   触发指定单元深度分析（仅跑命中单元，不连带重跑其它，AC4.4）
#   refresh   强制失效并重跑指定单元（重绑最新上游指纹，AC5.4）
#   recritic  仅重跑 critic 评审闭环（复用已落盘 director 产物，跳过拆解/深挖/辩论，省 token；industry / asset）
#   status    列出全部单元状态（五色 + 版本 + 生成时间）
#   scan      扫描过期/过时单元，仅置黄并提示（绝不自动重跑，AC4.2 / AC5.3）

set -euo pipefail

# 强制 UTF-8 locale（脚本/单元名含中文）
for _loc in C.UTF-8 en_US.UTF-8 zh_CN.UTF-8; do
    if locale -a 2>/dev/null | grep -qix "$_loc"; then
        export LANG="$_loc" LC_ALL="$_loc"
        break
    fi
done
unset _loc

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_ROOT"

# 自动检测 Python（优先 venv）
PYTHON="python3"
if [ -x "$PROJECT_ROOT/.venv/bin/python" ]; then
    PYTHON="$PROJECT_ROOT/.venv/bin/python"
elif [ -x "$PROJECT_ROOT/venv/bin/python" ]; then
    PYTHON="$PROJECT_ROOT/venv/bin/python"
elif command -v python &>/dev/null; then
    PYTHON="python"
fi

ORCHESTRATOR="$SCRIPT_DIR/workflow-v4-advisor.js"

DEFAULT_USER_ID="6a094caea814b57d3357fa0b"
USER_ID="$DEFAULT_USER_ID"
COMMAND="${1:-}"
SELECTOR=""
PORTFOLIO_FILE=""
FULL=""
JSON_OUT=""

usage() {
    cat <<'EOF'
用法:
  ./run_v4.sh analyze  <unit-selector> [--user-id <id>] [--portfolio-file <path>] [--full]
  ./run_v4.sh refresh  <unit-selector> [--user-id <id>] [--portfolio-file <path>]
  ./run_v4.sh recritic <industry:名|asset:类> [--user-id <id>]  # 只重跑 critic 评审闭环(复用已落盘产物,省 token)
  ./run_v4.sh status   [--user-id <id>] [--json]
  ./run_v4.sh scan     [--user-id <id>] [--json]

unit-selector:
  asset:<class> | plan:<class> | alloc:portfolio | industry:<name>
  alloc:equity_industries | stock:<code> | alloc:industry:<name>
EOF
}

if [ -z "$COMMAND" ] || [ "$COMMAND" = "-h" ] || [ "$COMMAND" = "--help" ]; then
    usage
    exit 0
fi
shift || true

# analyze/refresh/recritic 第二个位置参数是 selector
case "$COMMAND" in
    analyze|refresh|recritic)
        if [ $# -gt 0 ] && [[ "${1:-}" != --* ]]; then
            SELECTOR="$1"
            shift
        fi
        ;;
esac

# 解析剩余 flags
while [ $# -gt 0 ]; do
    case "$1" in
        --user-id)         USER_ID="${2:-}"; shift 2 ;;
        --portfolio-file)  PORTFOLIO_FILE="${2:-}"; shift 2 ;;
        --full)            FULL="1"; shift ;;
        --json)            JSON_OUT="1"; shift ;;
        *) echo "未知参数: $1" >&2; usage; exit 1 ;;
    esac
done

run_status() {
    local mode="$1"   # status | scan
    local args=(--user-id "$USER_ID" --mode "$mode")
    [ -n "$JSON_OUT" ] && args+=(--json)
    "$PYTHON" "$SCRIPT_DIR/v4_status.py" "${args[@]}"
}

run_orchestrator() {
    local verb="$1"
    if [ -z "$SELECTOR" ]; then
        echo "❌ $verb 需要 unit-selector（如 asset:equity）" >&2
        usage
        exit 1
    fi
    if [ ! -f "$ORCHESTRATOR" ]; then
        echo "❌ 编排器尚未就绪: $ORCHESTRATOR" >&2
        exit 1
    fi

    # [1/2] 数据采集：为该单元拼装多维输入包（脱 LLM，纯 Python）
    # recritic 复用已落盘产物 + 既有输入包，跳过重新采集（省时省 token，且无需联网）
    if [ "$verb" = "recritic" ]; then
        echo "[1/2] recritic 模式：跳过数据采集，复用已落盘产物与既有输入包"
    else
        local collect_args=(--selector "$SELECTOR" --user-id "$USER_ID" --verb "$verb")
        [ -n "$PORTFOLIO_FILE" ] && collect_args+=(--portfolio-file "$PORTFOLIO_FILE")
        echo "[1/2] 采集 $SELECTOR 输入包..."
        "$PYTHON" "$SCRIPT_DIR/collect_v4.py" "${collect_args[@]}" || {
            echo "❌ 数据采集失败" >&2; exit 1; }
    fi

    # [2/2] Agent 推理：默认本会话 agent 直跑；无 claude 子进程时不阻塞（退出码 2，改走 agent 直跑）
    if ! command -v claude &>/dev/null; then
        echo "ℹ 未找到 claude CLI —— 输入包已就绪（data/v4/inputs/）。" >&2
        echo "  方式①（推荐）：由本会话 AI agent 直跑——读输入包+联网补数+部门辩论，再用" >&2
        echo "    python3 scripts/v4_unit_cli.py write '<unit>' --payload <f> --run-mode ai_proxy 落盘。" >&2
        echo "    完整步骤见 docs/wiki/v4-ai-proxy-run.md。" >&2
        echo "  方式②：在具备 claude 鉴权的环境运行：" >&2
        echo "    claude -p \"运行 v4 编排器，Workflow scripts/workflow-v4-advisor.js，args {verb:'$verb', selector:'$SELECTOR', user_id:'$USER_ID'}\"" >&2
        exit 2
    fi
    local wf_extra=""
    [ -n "$PORTFOLIO_FILE" ] && wf_extra="$wf_extra, portfolio_file: '$PORTFOLIO_FILE'"
    [ -n "$FULL" ] && wf_extra="$wf_extra, full: true"
    echo "[2/2] Agent 推理（v4 单元化部门辩论）..."
    cd "$PROJECT_ROOT"
    claude -p "运行 v4 分层投研编排器。verb=$verb，单元选择器=$SELECTOR，用户ID=$USER_ID。
Workflow 脚本在 scripts/workflow-v4-advisor.js，请用 Workflow 工具调用它，args 传 {verb: '$verb', selector: '$SELECTOR', user_id: '$USER_ID'$wf_extra}。
v4 子 Agent 定义在 .claude/agents/advisor/（v4-*.md）。
不要把大 JSON 嵌进 prompt——Agent 用 Read 工具自己读 data/v4/inputs/ 下的数据文件。" \
        --permission-mode bypassPermissions \
        --output-format text \
        --max-turns 40 \
        2>&1 | sed 's/^/  /'
    if [ ${PIPESTATUS[0]} -ne 0 ]; then
        echo "❌ Agent 推理失败（单元锁与产物保留，可重试）" >&2
        exit 1
    fi
    echo "✅ v4 $verb $SELECTOR 完成"
}

case "$COMMAND" in
    analyze)  run_orchestrator analyze ;;
    refresh)  run_orchestrator refresh ;;
    recritic) run_orchestrator recritic ;;
    status)   run_status status ;;
    scan)     run_status scan ;;
    *)
        echo "未知子命令: $COMMAND" >&2
        usage
        exit 1
        ;;
esac
