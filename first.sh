#!/bin/bash

# Linux/macOS 第一次设置脚本
echo "=== Agent Workflow 第一次设置脚本 ==="

# 检查 npm 是否安装，因为前端需要
if ! command -v npm &> /dev/null; then
    echo "[警告] 未检测到 npm。请先安装 Node.js 和 npm 后再运行前端。"
else
    echo "1. 安装前端依赖..."
    if [ -d "frontend" ]; then
        cd frontend
        npm install
        cd ..
    else
        echo "[错误] 未找到 frontend 目录！"
    fi
fi

# 安装 uv (Python 包管理器)
echo "2. 检查并安装 uv..."
if ! command -v uv &> /dev/null; then
    curl -LsSf https://astral.sh/uv/install.sh | sh
    source $HOME/.cargo/env || true
    export PATH="$HOME/.cargo/bin:$PATH"
else
    echo "uv 已安装，跳过。"
fi

# 同步依赖
echo "3. 同步后端依赖..."
uv sync

# 运行初始化脚本
echo "4. 初始化项目配置..."
uv run python first.py

echo "=== 设置完成！ ==="
echo "后端启动: cd backend && uv run uvicorn server:app --reload"
echo "前端启动: cd frontend && npm run dev"
