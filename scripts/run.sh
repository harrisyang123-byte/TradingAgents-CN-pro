#!/bin/bash
# run.sh — Claude Code Workflow 组合顾问引擎入口
#
# 用法:
#   ./run.sh all [--user-id <id>]
#   ./run.sh collect [--user-id <id>]
#   ./run.sh analyze --data-dir <path> [--from <step>] [--only <step>]
#
# 子命令:
#   all       数据收集 + Agent 推理 + MongoDB 最终保存（全流程）
#   collect   只跑数据收集，产出 data/advisor_runs/{ts}/
#   analyze   只跑 Agent 推理 + 渐进式保存（需已有数据目录）

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
DATA_BASE_DIR="$PROJECT_ROOT/data/advisor_runs"

DEFAULT_USER_ID="6a094caea814b57d3357fa0b"
USER_ID="$DEFAULT_USER_ID"
DATA_DIR=""
FROM_STEP=""
ONLY_STEP=""
COMMAND=""

# ── 参数解析 ──────────────────────────────────────────────

usage() {
    cat <<'EOF'
用法:
  ./run.sh all [--user-id <id>]
  ./run.sh collect [--user-id <id>]
  ./run.sh analyze --data-dir <path> [--from <step>] [--only <step>]

子命令:
  all       数据收集 + Agent 推理 + MongoDB 最终保存
  collect   只跑数据收集
  analyze   只跑 Agent 推理 + 渐进式保存

参数:
  --user-id     用户 ID（默认: 6a094caea814b57d3357fa0b）
  --data-dir    数据目录路径（analyze 必需）
  --from        从指定 Agent step 开始（断点续跑）
  --only        只跑指定 Agent step（单 Agent 调试）
EOF
    exit 1
}

VALID_STEPS=("l1-strategist" "l1-contrarian" "l1-judge" "l2-scout"
             "l3-analyst" "l3-strategist" "l3-analyst-r2" "l3-strategist-r2"
             "l4-cio" "l4-risk" "l4-cio-final")

is_valid_step() {
    for s in "${VALID_STEPS[@]}"; do
        [ "$s" = "$1" ] && return 0
    done
    return 1
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
                echo "错误: Unknown step '$FROM_STEP'"
                echo "Valid: ${VALID_STEPS[*]}"
                exit 1
            fi
            shift 2
            ;;
        --only)
            ONLY_STEP="${2:-}"
            [ -z "$ONLY_STEP" ] && { echo "错误: --only 需要值"; usage; }
            if ! is_valid_step "$ONLY_STEP"; then
                echo "错误: Unknown step '$ONLY_STEP'"
                echo "Valid: ${VALID_STEPS[*]}"
                exit 1
            fi
            shift 2
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
    if ! command -v python &>/dev/null; then
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
    python "$SCRIPT_DIR/collect_data.py" \
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

run_analyze() {
    local RUN_DIR="$1"
    local FROM_FLAG=""
    local ONLY_FLAG=""

    if [ -n "$FROM_STEP" ]; then
        FROM_FLAG="--from $FROM_STEP"
    fi
    if [ -n "$ONLY_STEP" ]; then
        ONLY_FLAG="--only $ONLY_STEP"
    fi

    echo "[2/2] Agent 推理..."
    echo ""

    cd "$PROJECT_ROOT"
    claude workflow run advisor \
        --args "$RUN_DIR" \
        $FROM_FLAG $ONLY_FLAG \
        2>&1 | sed 's/^/  /'

    if [ ${PIPESTATUS[0]} -ne 0 ]; then
        echo ""
        echo "❌ Agent 推理失败。输出文件保留在 $RUN_DIR"
        echo "   修复后可执行: ./run.sh analyze --data-dir $RUN_DIR --from <failed-step>"
        exit 1
    fi

    echo ""
    echo "✅ Agent 推理完成"
}

# ── 最终保存 ──────────────────────────────────────────────

run_save() {
    local RUN_DIR="$1"

    echo ""
    echo "[3/3] 保存到 MongoDB..."

    cd "$PROJECT_ROOT"
    python "$SCRIPT_DIR/save_to_mongodb.py" --dir "$RUN_DIR" 2>&1 | sed 's/^/  /'

    if [ ${PIPESTATUS[0]} -ne 0 ]; then
        echo ""
        echo "❌ MongoDB 保存失败。输出文件保留在 $RUN_DIR"
        echo "   可手动执行: python scripts/save_to_mongodb.py --dir $RUN_DIR"
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
        echo "Claude Code 组合顾问引擎 v1"
        echo "========================================"
        echo "Run ID: $RUN_ID"
        echo "用户:   $USER_ID"
        echo "数据目录: $RUN_DIR"
        echo ""

        # Phase 1: 数据收集
        echo "[1/3] 收集数据..."
        python "$SCRIPT_DIR/collect_data.py" \
            --user-id "$USER_ID" \
            --out-dir "$RUN_DIR" \
            2>&1 | sed 's/^/  /'
        if [ ${PIPESTATUS[0]} -ne 0 ]; then
            echo "❌ 数据收集失败"
            exit 1
        fi
        echo "✅ 数据收集完成"

        # Phase 2: Agent 推理（通过 Claude Code Workflow）
        echo ""
        echo "[2/3] Agent 推理（约 4-5 分钟）..."
        claude workflow run advisor --args "{\"data_dir\": \"$RUN_DIR\", \"user_id\": \"$USER_ID\"}"
        WF_EXIT=$?
        if [ $WF_EXIT -ne 0 ]; then
            echo ""
            echo "❌ Agent 推理失败。"
            echo "   输出文件: $RUN_DIR"
            echo "   断点续跑: ./run.sh analyze --data-dir $RUN_DIR --from <step>"
            exit 1
        fi
        echo "✅ Agent 推理完成"

        # Phase 3: 最终保存
        echo ""
        echo "[3/3] 保存到 MongoDB..."
        python "$SCRIPT_DIR/save_to_mongodb.py" --dir "$RUN_DIR" 2>&1 | sed 's/^/  /'
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
        ARGS_JSON="{\"data_dir\": \"$DATA_DIR\", \"user_id\": \"$USER_ID\""
        if [ -n "$FROM_STEP" ]; then
            ARGS_JSON="$ARGS_JSON, \"from_step\": \"$FROM_STEP\""
        fi
        if [ -n "$ONLY_STEP" ]; then
            ARGS_JSON="$ARGS_JSON, \"only_step\": \"$ONLY_STEP\""
        fi
        ARGS_JSON="$ARGS_JSON}"

        echo "Agent 推理中（约 4-5 分钟）..."
        echo "数据目录: $DATA_DIR"
        [ -n "$FROM_STEP" ] && echo "起始步骤: $FROM_STEP"
        [ -n "$ONLY_STEP" ] && echo "单步调试: $ONLY_STEP"
        echo ""

        claude workflow run advisor --args "$ARGS_JSON"
        if [ $? -ne 0 ]; then
            echo "❌ Agent 推理失败。输出文件: $DATA_DIR"
            [ -z "$ONLY_STEP" ] && echo "断点续跑: ./run.sh analyze --data-dir $DATA_DIR --from <step>"
            exit 1
        fi
        echo "✅ Agent 推理完成"
        ;;
esac
