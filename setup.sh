#!/bin/bash
# setup.sh — 安装 Claude Code 自定义 Agent 文件
# 将 agents/advisor/ 下的 Agent 定义复制到项目 .claude/agents/advisor/

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$SCRIPT_DIR"
SRC_DIR="$PROJECT_ROOT/agents/advisor"
DEST_DIR="$PROJECT_ROOT/.claude/agents/advisor"

if [ ! -d "$SRC_DIR" ]; then
    echo "错误: Agent 源目录不存在: $SRC_DIR"
    exit 1
fi

echo "安装 Claude Code 自定义 Agent..."
echo "  源目录: $SRC_DIR"
echo "  目标目录: $DEST_DIR"

mkdir -p "$DEST_DIR"

AGENT_COUNT=0
for agent_file in "$SRC_DIR"/*.md; do
    if [ -f "$agent_file" ]; then
        basename=$(basename "$agent_file")
        cp "$agent_file" "$DEST_DIR/$basename"
        echo "  ✅ $basename"
        AGENT_COUNT=$((AGENT_COUNT + 1))
    fi
done

echo ""
echo "已安装 $AGENT_COUNT 个 Agent 文件。"
echo "验证: claude /agents 可查看已注册的 Agent。"
