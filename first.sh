#!/usr/bin/env bash

set -euo pipefail

PROJECT_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_ROOT"

echo "=== Agent Workflow 第一次设置脚本 ==="

if ! command -v npm >/dev/null 2>&1; then
    echo "[错误] 未检测到 npm，请先安装 Node.js 和 npm。" >&2
    exit 1
fi
if ! command -v uv >/dev/null 2>&1; then
    echo "[错误] 未检测到 uv，请先安装 uv。" >&2
    exit 1
fi

echo "1. 按锁文件安装前端依赖..."
npm --prefix frontend ci

echo "2. 按锁文件同步后端依赖..."
uv sync --locked

echo "3. 初始化项目目录和配置..."
mkdir -p workflows workspaces chats sessions nodes

if [[ ! -f .env ]]; then
    PROJECTS_DIR="$(dirname "$PROJECT_ROOT")"
    umask 077
    cat >.env <<EOF
USER_NAME=${USER:-user}
BASE_DIR="$PROJECT_ROOT"
WORKFLOW_DIR="$PROJECT_ROOT/workflows"
WORKSPACE_DIR="$PROJECT_ROOT/workspaces"
CHAT_DIR="$PROJECT_ROOT/chats"
SESSIONS_DIR="$PROJECT_ROOT/sessions"
NODES_DIR="$PROJECT_ROOT/nodes"
FRONTEND_DIR="$PROJECT_ROOT/frontend/dist"
PROJECTS_DIR="$PROJECTS_DIR"
LOG_LEVEL=INFO
DEEPSEEK_API_KEY=
OPENROUTER_API_KEY=
OPENAI_API_KEY=
EOF
    echo "已生成 .env，请在启动前填写所需的 API Key。"
else
    echo ".env 已存在，未覆盖现有配置。"
fi

echo "=== 设置完成！ ==="
echo "后端启动: cd backend && uv run uvicorn server:app --reload"
echo "前端启动: cd frontend && npm run dev"
