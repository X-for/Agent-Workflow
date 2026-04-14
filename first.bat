

@echo off

REM Windows 第一次设置脚本
echo === Windows 第一次设置脚本 ===

REM 1. 安装 uv (Python 包管理器)
echo 1. 安装 uv...
powershell -ExecutionPolicy Bypass -c "irm https://astral.sh/uv/install.ps1 | iex"

REM 2. 同步依赖
echo 2. 同步依赖...
uv sync

REM 3. 设置 .env 环境目录
echo 3. 设置 .env 环境目录...

REM 创建 .env 文件
powershell -ExecutionPolicy Bypass -c "New-Item -ItemType File -Path '.env' -Force"

REM 设置环境变量
powershell -ExecutionPolicy Bypass -c "Add-Content -Path '.env' -Value 'USER_NAME=user'"
powershell -ExecutionPolicy Bypass -c "Add-Content -Path '.env' -Value 'BASE_DIR=%cd%'"
powershell -ExecutionPolicy Bypass -c "Add-Content -Path '.env' -Value 'WORKFLOW_DIR=%cd%\workflows'"
powershell -ExecutionPolicy Bypass -c "Add-Content -Path '.env' -Value 'WORKSPACE_DIR=%cd%\workspaces'"
powershell -ExecutionPolicy Bypass -c "Add-Content -Path '.env' -Value 'CHAT_DIR=%cd%\chats'"
powershell -ExecutionPolicy Bypass -c "Add-Content -Path '.env' -Value 'PROJECTS_DIR=%cd%'"
powershell -ExecutionPolicy Bypass -c "Add-Content -Path '.env' -Value 'FRONTEND_DIR=%cd%\frontend'"
powershell -ExecutionPolicy Bypass -c "Add-Content -Path '.env' -Value 'SESSIONS_DIR=%cd%\sessions'"
powershell -ExecutionPolicy Bypass -c "Add-Content -Path '.env' -Value 'NODES_DIR=%cd%\nodes'"
powershell -ExecutionPolicy Bypass -c "Add-Content -Path '.env' -Value 'LOG_LEVEL=INFO'"
powershell -ExecutionPolicy Bypass -c "Add-Content -Path '.env' -Value 'OPENROUTER_API_KEY=your_openrouter_api_key_here'"
powershell -ExecutionPolicy Bypass -c "Add-Content -Path '.env' -Value 'DEEPSEEK_API_KEY=your_deepseek_api_key_here'"

REM 显示 .env 文件内容
echo .env 文件内容：
type .env

echo === 设置完成！ ===
pause