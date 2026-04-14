#!/bin/bash

# Linux 第一次设置脚本
echo "=== Linux 第一次设置脚本 ==="

# 更新系统包
echo "1. 更新系统包..."
sudo apt update && sudo apt upgrade -y

# 安装必要的工具
echo "2. 安装必要的工具..."
sudo apt install -y curl wget git build-essential

# 安装 uv (Python 包管理器)
echo "3. 安装 uv..."
curl -LsSf https://astral.sh/uv/install.sh | sh

# 同步依赖
echo "4. 同步依赖..."
uv sync

echo "=== 设置完成！ ==="
