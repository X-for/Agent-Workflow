@echo off
chcp 65001 >nul
echo 正在启动 Agent Workflow...

:: 启动后端 (会弹出一个新的命令行窗口)
echo -^> 启动 FastAPI 后端...
start "Agent Backend" cmd /c "python main.py"

:: 启动前端 (会弹出一个新的命令行窗口)
echo -^> 启动 Vue 前端...
start "Agent Frontend" cmd /c "cd agent-frontend && npm run dev"

echo.
echo 服务均已启动！
echo 关闭弹出的两个黑色窗口即可停止服务。
pause