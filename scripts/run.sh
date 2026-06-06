#!/bin/bash
# run.sh — Claude Code Workflow 组合顾问引擎入口（v3 增量编排）
#
# 用法:
#   ./run.sh all [--user-id <id>] [--from <stage>] [--refresh <stage>] [--full]
#   ./run.sh collect [--user-id <id>]
#   ./run.sh analyze --data-dir <path> [--from <stage>] [--only <stage>] [--refresh <stage>] [--full]
#
# 子命令:
#   all       数据收集 + Agent 推理（v3 增量）+ MongoDB 保存（全流程）
#   collect   只跑数据收集，产出 data/advisor_runs/{ts}/
#   analyze   只跑 Agent 推理（v3 增量）+ 保存（需已有数据目录）
#
# v3 阶段(stage): macro | industry | pm | synth
#   默认增量：缓存新鲜的阶段自动跳过；任一阶段跑了，其下游强制重跑。
#   --from <stage>      从某阶段强制重跑到结尾
#   --only <stage>      只跑某阶段（调试）
#   --refresh <stage>   强制失效某阶段并重跑；"industry:<行业名>" 只刷单个行业
#   --full              忽略全部缓存，从头全跑

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
DATA_BASE_DIR="$PROJECT_ROOT/data/advisor_runs"

# 自动检测 Python（优先 venv）
PYTHON="python3"
if [ -x "$PROJECT_ROOT/.venv/bin/python" ]; then
    PYTHON="$PROJECT_ROOT/.venv/bin/python"
elif [ -x "$PROJECT_ROOT/venv/bin/python" ]; then
    PYTHON="$PROJECT_ROOT/venv/bin/python"
elif command -v python &>/dev/null; then
    PYTHON="python"
fi

DEFAULT_USER_ID="6a094caea814b57d3357fa0b"
USER_ID="$DEFAULT_USER_ID"
DATA_DIR=""
FROM_STEP=""
ONLY_STEP=""
REFRESH=""
FULL=""
COMMAND=""

# ── 参数解析 ──────────────────────────────────────────────

usage() {
    cat <<'EOF'
用法:
  ./run.sh all [--user-id <id>] [--from <stage>] [--refresh <stage>] [--full]
  ./run.sh collect [--user-id <id>]
  ./run.sh analyze --data-dir <path> [--from <stage>] [--only <stage>] [--refresh <stage>] [--full]

子命令:
  all       数据收集 + Agent 推理（v3 增量）+ MongoDB 保存
  collect   只跑数据收集
  analyze   只跑 Agent 推理（v3 增量）+ 保存

v3 阶段(stage): macro | industry | pm | synth

参数:
  --user-id     用户 ID（默认: 6a094caea814b57d3357fa0b）
  --data-dir    数据目录路径（analyze 必需）
  --from        从指定阶段开始重跑到结尾（断点续跑）
  --only        只跑指定阶段（单阶段调试）
  --refresh     强制失效某阶段并重跑；"industry:<行业名>" 只刷单个行业
  --full        忽略全部缓存，从头全跑
EOF
    exit 1
}

VALID_STEPS=("macro" "industry" "pm" "synth")

is_valid_step() {
    for s in "${VALID_STEPS[@]}"; do
        [ "$s" = "$1" ] && return 0
    done
    return 1
}

# refresh 允许 "industry:<名>" 形式，取冒号前的 stage 校验
is_valid_refresh() {
    local base="${1%%:*}"
    is_valid_step "$base"
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        all|collect|analyze)
            COMMAND="$1"
            shift
            ;;
        --user-id)
            USER_ID="${2:-}"
            [ -z "$USER_ID" ] && { echo "错误: --user-id 需要值"; usage; }
            shift 2
            ;;
        --data-dir)
            DATA_DIR="${2:-}"
            [ -z "$DATA_DIR" ] && { echo "错误: --data-dir 需要值"; usage; }
            shift 2
            ;;
        --from)
            FROM_STEP="${2:-}"
            [ -z "$FROM_STEP" ] && { echo "错误: --from 需要值"; usage; }
            if ! is_valid_step "$FROM_STEP"; then
                echo "错误: Unknown stage '$FROM_STEP'"
                echo "Valid: ${VALID_STEPS[*]}"
                exit 1
            fi
            shift 2
            ;;
        --only)
            ONLY_STEP="${2:-}"
            [ -z "$ONLY_STEP" ] && { echo "错误: --only 需要值"; usage; }
            if ! is_valid_step "$ONLY_STEP"; then
                echo "错误: Unknown stage '$ONLY_STEP'"
                echo "Valid: ${VALID_STEPS[*]}"
                exit 1
            fi
            shift 2
            ;;
        --refresh)
            REFRESH="${2:-}"
            [ -z "$REFRESH" ] && { echo "错误: --refresh 需要值"; usage; }
            if ! is_valid_refresh "$REFRESH"; then
                echo "错误: Unknown refresh stage '$REFRESH'"
                echo "Valid: ${VALID_STEPS[*]} (或 industry:<行业名>)"
                exit 1
            fi
            shift 2
            ;;
        --full)
            FULL="1"
            shift
            ;;
        -h|--help)
            usage
            ;;
        *)
            echo "错误: 未知参数 '$1'"
            usage
            ;;
    esac
done

[ -z "$COMMAND" ] && usage

# ── 环境检查 ──────────────────────────────────────────────

check_prereqs() {
    local errors=0

    # 检查 user_id 格式
    if ! [[ "$USER_ID" =~ ^[a-f0-9]{24}$ ]]; then
        echo "错误: Invalid user_id format: must be 24-character hex string"
        errors=$((errors + 1))
    fi

    # 检查 Python
    if ! test -x "$PYTHON" &>/dev/null; then
        echo "错误: Python not found"
        errors=$((errors + 1))
    fi

    # 检查 claude CLI 版本
    if ! command -v claude &>/dev/null; then
        echo "错误: Claude Code CLI not found"
        errors=$((errors + 1))
    else
        CLAUDE_VER=$(claude --version 2>/dev/null | grep -oE '[0-9]+\.[0-9]+\.[0-9]+' | head -1)
        if [ -n "$CLAUDE_VER" ]; then
            MAJOR=$(echo "$CLAUDE_VER" | cut -d. -f1)
            MINOR=$(echo "$CLAUDE_VER" | cut -d. -f2)
            PATCH=$(echo "$CLAUDE_VER" | cut -d. -f3)
            # >= v2.1.154
            if [ "$MAJOR" -lt 2 ] || { [ "$MAJOR" -eq 2 ] && [ "$MINOR" -lt 1 ]; } || \
               { [ "$MAJOR" -eq 2 ] && [ "$MINOR" -eq 1 ] && [ "$PATCH" -lt 154 ]; }; then
                echo "错误: Claude Code v2.1.154+ required, current: v$CLAUDE_VER"
                errors=$((errors + 1))
            fi
        fi
    fi

    return $errors
}

check_prereqs || exit 1

# ── 收集数据 ──────────────────────────────────────────────

run_collect() {
    RUN_ID="${1:-$(date +%Y%m%d_%H%M%S)}"
    RUN_DIR="$DATA_BASE_DIR/$RUN_ID"

    echo "========================================"
    echo "Run ID: $RUN_ID"
    echo "用户:   $USER_ID"
    echo "数据目录: $RUN_DIR"
    echo "========================================"
    echo ""

    mkdir -p "$RUN_DIR"

    echo "[1/2] 收集数据..."
    cd "$PROJECT_ROOT"
    $PYTHON "$SCRIPT_DIR/collect_data.py" \
        --user-id "$USER_ID" \
        --out-dir "$RUN_DIR" \
        2>&1 | sed 's/^/  /'

    if [ ${PIPESTATUS[0]} -ne 0 ]; then
        echo ""
        echo "❌ 数据收集失败，退出。"
        exit 1
    fi

    echo ""
    echo "✅ 数据收集完成 → $RUN_DIR"
    echo ""

    # 返回 run_dir 和 run_id
    echo "$RUN_DIR"
}

# ── Agent 推理 ──────────────────────────────────────────────

# 构建 v3 编排器 args 片段（from/only/refresh/full）
wf_extra_args() {
    local extra=""
    [ -n "$FROM_STEP" ] && extra="$extra, from: '$FROM_STEP'"
    [ -n "$ONLY_STEP" ] && extra="$extra, only: '$ONLY_STEP'"
    [ -n "$REFRESH" ]   && extra="$extra, refresh: '$REFRESH'"
    [ -n "$FULL" ]      && extra="$extra, full: true"
    echo "$extra"
}

run_analyze() {
    local RUN_DIR="$1"
    local FROM_MSG=""
    local ONLY_MSG=""

    if [ -n "$FROM_STEP" ]; then
        FROM_MSG="从阶段 $FROM_STEP 开始续跑。"
    fi
    if [ -n "$ONLY_STEP" ]; then
        ONLY_MSG="只运行 $ONLY_STEP 这一个阶段。"
    fi

    echo "[2/2] Agent 推理（v3 增量）..."
    echo ""

    cd "$PROJECT_ROOT"
    claude -p "运行 v3 组合顾问编排器。数据目录: $RUN_DIR, 用户ID: $USER_ID。$FROM_MSG $ONLY_MSG
Workflow 脚本在 scripts/workflow-v3-advisor.js，请用 Workflow 工具调用它，args 传 {dataDir: '$RUN_DIR', user_id: '$USER_ID'$(wf_extra_args)}。
v3 子 Agent 定义在 .claude/agents/advisor/（v3-*.md）。
不要嵌大 JSON 在 prompt 里——Agent 用 Read 工具自己读数据文件。" \
        --permission-mode bypassPermissions \
        --output-format text \
        --max-turns 30 \
        2>&1 | sed 's/^/  /'

    if [ ${PIPESTATUS[0]} -ne 0 ]; then
        echo ""
        echo "❌ Agent 推理失败。输出文件保留在 $RUN_DIR"
        echo "   修复后可执行: ./run.sh analyze --data-dir $RUN_DIR --from <failed-stage>"
        exit 1
    fi

    echo ""
    echo "✅ Agent 推理完成"
}

# ── 最终保存 ──────────────────────────────────────────────

run_save() {
    local RUN_DIR="$1"

    echo ""
    echo "[3/3] 保存到 MongoDB（v3）..."

    cd "$PROJECT_ROOT"
    $PYTHON "$SCRIPT_DIR/save_v3_to_mongodb.py" --dir "$RUN_DIR" 2>&1 | sed 's/^/  /'

    if [ ${PIPESTATUS[0]} -ne 0 ]; then
        echo ""
        echo "❌ MongoDB 保存失败。输出文件保留在 $RUN_DIR"
        echo "   可手动执行: $PYTHON scripts/save_v3_to_mongodb.py --dir $RUN_DIR"
        exit 1
    fi

    echo ""
    echo "✅ 保存完成"
}

# ── 主流程 ──────────────────────────────────────────────

cd "$PROJECT_ROOT"

case "$COMMAND" in
    all)
        RUN_ID=$(date +%Y%m%d_%H%M%S)
        RUN_DIR="$DATA_BASE_DIR/$RUN_ID"
        mkdir -p "$RUN_DIR"

        echo "========================================"
        echo "Claude Code 组合顾问引擎 v3（增量编排）"
        echo "========================================"
        echo "Run ID: $RUN_ID"
        echo "用户:   $USER_ID"
        echo "数据目录: $RUN_DIR"
        [ -n "$FROM_STEP" ] && echo "起始阶段: $FROM_STEP"
        [ -n "$REFRESH" ]   && echo "强制刷新: $REFRESH"
        [ -n "$FULL" ]      && echo "全量模式: 忽略缓存"
        echo ""

        # Phase 1: 数据收集
        echo "[1/3] 收集数据..."
        $PYTHON "$SCRIPT_DIR/collect_data.py" \
            --user-id "$USER_ID" \
            --out-dir "$RUN_DIR" \
            2>&1 | sed 's/^/  /'
        if [ ${PIPESTATUS[0]} -ne 0 ]; then
            echo "❌ 数据收集失败"
            exit 1
        fi
        echo "✅ 数据收集完成"

        # Phase 2: Agent 推理（v3 增量编排，通过 Claude Code）
        echo ""
        echo "[2/3] Agent 推理（v3 增量）..."
        claude -p "运行 v3 组合顾问编排器。数据目录: $RUN_DIR, 用户ID: $USER_ID。
Workflow 脚本在 scripts/workflow-v3-advisor.js，请用 Workflow 工具调用它，args 传 {dataDir: '$RUN_DIR', user_id: '$USER_ID'$(wf_extra_args)}。
v3 子 Agent 定义在 .claude/agents/advisor/（v3-*.md）。
不要嵌大 JSON 在 prompt 里——Agent 用 Read 工具自己读数据文件。" \
            --permission-mode bypassPermissions \
            --output-format text \
            --max-turns 30
        WF_EXIT=$?
        if [ $WF_EXIT -ne 0 ]; then
            echo ""
            echo "❌ Agent 推理失败。"
            echo "   输出文件: $RUN_DIR"
            echo "   断点续跑: ./run.sh analyze --data-dir $RUN_DIR --from <stage>"
            exit 1
        fi
        echo "✅ Agent 推理完成"

        # Phase 3: 最终保存（v3 适配器）
        echo ""
        echo "[3/3] 保存到 MongoDB（v3）..."
        $PYTHON "$SCRIPT_DIR/save_v3_to_mongodb.py" --dir "$RUN_DIR" 2>&1 | sed 's/^/  /'
        if [ ${PIPESTATUS[0]} -ne 0 ]; then
            echo "❌ 保存失败"
            exit 1
        fi
        echo ""
        echo "========================================"
        echo "Done. 处方已保存。"
        echo "Run ID: $RUN_ID"
        echo "========================================"
        ;;

    collect)
        RUN_ID=$(date +%Y%m%d_%H%M%S)
        run_collect "$RUN_ID"
        ;;

    analyze)
        if [ -z "$DATA_DIR" ]; then
            echo "错误: analyze 需要 --data-dir 参数"
            usage
        fi
        if [ ! -d "$DATA_DIR" ]; then
            echo "错误: 数据目录不存在: $DATA_DIR"
            exit 1
        fi
        if [ ! -f "$DATA_DIR/data_portfolio.json" ]; then
            echo "错误: 数据目录缺少 data_portfolio.json"
            echo "请先运行: ./run.sh collect"
            exit 1
        fi

        cd "$PROJECT_ROOT"

        FROM_MSG=""
        ONLY_MSG=""
        if [ -n "$FROM_STEP" ]; then
            FROM_MSG="从阶段 $FROM_STEP 开始续跑。"
        fi
        if [ -n "$ONLY_STEP" ]; then
            ONLY_MSG="只运行 $ONLY_STEP 这一个阶段。"
        fi

        echo "Agent 推理中（v3 增量）..."
        echo "数据目录: $DATA_DIR"
        [ -n "$FROM_STEP" ] && echo "起始阶段: $FROM_STEP"
        [ -n "$ONLY_STEP" ] && echo "单阶段调试: $ONLY_STEP"
        [ -n "$REFRESH" ]   && echo "强制刷新: $REFRESH"
        [ -n "$FULL" ]      && echo "全量模式: 忽略缓存"
        echo ""

        claude -p "运行 v3 组合顾问编排器。数据目录: $DATA_DIR, 用户ID: $USER_ID。$FROM_MSG $ONLY_MSG
Workflow 脚本在 scripts/workflow-v3-advisor.js，请用 Workflow 工具调用它，args 传 {dataDir: '$DATA_DIR', user_id: '$USER_ID'$(wf_extra_args)}。
v3 子 Agent 定义在 .claude/agents/advisor/（v3-*.md）。
不要嵌大 JSON 在 prompt 里——Agent 用 Read 工具自己读数据文件。" \
            --permission-mode bypassPermissions \
            --output-format text \
            --max-turns 30
        if [ $? -ne 0 ]; then
            echo "❌ Agent 推理失败。输出文件: $DATA_DIR"
            [ -z "$ONLY_STEP" ] && echo "断点续跑: ./run.sh analyze --data-dir $DATA_DIR --from <stage>"
            exit 1
        fi
        echo "✅ Agent 推理完成"
        ;;
esac
