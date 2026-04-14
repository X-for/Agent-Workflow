

@echo off
chcp 65001 >nul

REM Windows 第一次设置脚本
echo === Agent Workflow 第一次设置脚本 ===

REM 检查 npm
where npm >nul 2>nul
if %errorlevel% neq 0 (
    echo [警告] 未检测到 npm。请先安装 Node.js 和 npm 后再运行前端。
) else (
    echo 1. 安装前端依赖...
    if exist frontend\ (
        cd frontend
        call npm install
        cd ..
    ) else (
        echo [错误] 未找到 frontend 目录！
    )
)

REM 安装 uv (Python 包管理器)
echo 2. 检查并安装 uv...
where uv >nul 2>nul
if %errorlevel% neq 0 (
    powershell -ExecutionPolicy Bypass -c "irm https://astral.sh/uv/install.ps1 | iex"
    REM 添加到当前会话的 PATH 中
    set "PATH=%USERPROFILE%\.cargo\bin;%PATH%"
) else (
    echo uv 已安装，跳过。
)

REM 同步依赖
echo 3. 同步后端依赖...
call uv sync

REM 运行初始化脚本
echo 4. 初始化项目配置...
call uv run python first.py

echo === 设置完成！ ===
echo 后端启动: cd backend ^&^& uv run uvicorn server:app --reload
echo 前端启动: cd frontend ^&^& npm run dev
pause
