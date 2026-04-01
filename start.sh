#!/bin/bash
echo "正在启动 Agent Workflow..."

# 捕获 Ctrl+C 信号，优雅地同时杀掉前后端进程，防止端口占用
trap 'echo -e "\n 正在关闭服务..."; kill 0' SIGINT SIGTERM

# 1. 启动后端并放到后台运行
echo "-> 启动 FastAPI 后端 (端口 8001)..."
python main.py &

# 2. 启动前端并放到后台运行
echo "-> 启动 Vue 前端..."
cd agent-frontend && npm run dev &

# 等待后台进程
wait