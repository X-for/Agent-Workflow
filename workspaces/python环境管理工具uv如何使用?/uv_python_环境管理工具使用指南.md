# uv Python 环境管理工具使用指南

## uv 是什么？

uv 是由 Astral 公司开发的基于 Rust 编写的 Python 包管理器和环境管理器。它旨在提供比现有工具快 10-100 倍的性能，同时保持简单直观的用户体验。uv 可以替代 pip、virtualenv、pip-tools 等工具，提供依赖管理、虚拟环境创建、Python 版本管理等一站式服务。

## 安装 uv

### 推荐安装方式

**macOS/Linux：**
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

**Windows（PowerShell）：**
```powershell
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
```

**使用 Homebrew（macOS）：**
```bash
brew install uv
```

**使用 Scoop（Windows）：**
```bash
scoop install uv
```

**注意：** 不建议使用 pip 或 pipx 安装 uv，这样会与特定的 Python 环境绑定。

## 基本使用

### 1. 创建新项目
```bash
# 创建新项目
uv init my-project
cd my-project
```

这会创建一个包含 `pyproject.toml` 文件的新项目，并自动初始化 Git 仓库。

### 2. 管理 Python 版本
```bash
# 安装特定 Python 版本
uv python install 3.11

# 查看已安装的 Python 版本
uv python list

# 设置项目使用的 Python 版本
uv python pin 3.11
```

### 3. 创建和管理虚拟环境
```bash
# 创建虚拟环境
uv venv

# 激活虚拟环境
# Linux/macOS:
source .venv/bin/activate
# Windows:
.venv\Scripts\activate

# 使用 uv run 直接运行命令（无需激活环境）
uv run python script.py
```

### 4. 依赖管理
```bash
# 添加依赖
uv add requests
uv add numpy==1.24.0
uv add "pandas>=1.5.0"

# 添加开发依赖
uv add --dev pytest black

# 从 requirements.txt 安装
uv pip install -r requirements.txt

# 同步依赖（安装 pyproject.toml 中所有依赖）
uv sync

# 移除依赖
uv remove requests

# 更新依赖
uv update
```

### 5. 锁定依赖
```bash
# 生成锁定文件
uv lock

# 使用锁定文件安装依赖（确保环境一致性）
uv sync --locked
```

### 6. 运行命令
```bash
# 直接运行 Python 脚本
uv run python script.py

# 运行包中的命令
uv run black .
uv run pytest
```

## 高级功能

### 1. 依赖树查看
```bash
# 显示依赖树
uv tree
```

### 2. 导出依赖
```bash
# 导出为 requirements.txt
uv export --format requirements.txt > requirements.txt

# 导出为 conda environment.yml
uv export --format conda > environment.yml
```

### 3. 包构建和发布
```bash
# 构建包
uv build

# 发布包
uv publish
```

### 4. 全局包管理（替代 pipx）
```bash
# 安装全局工具
uv tool install black

# 运行全局工具
uv tool run black --version
```

## 实际工作流程示例

### 典型项目初始化流程：
```bash
# 1. 创建项目
uv init my-project
cd my-project

# 2. 设置 Python 版本
uv python install 3.11
uv python pin 3.11

# 3. 添加依赖
uv add fastapi
uv add --dev pytest

# 4. 同步依赖
uv sync

# 5. 运行代码
uv run python main.py
```

### 从现有项目迁移：
```bash
# 1. 创建虚拟环境
uv venv

# 2. 从 requirements.txt 安装
uv pip install -r requirements.txt

# 3. 生成 pyproject.toml
uv init --existing

# 4. 生成锁定文件
uv lock
```

## 优势总结

1. **极速性能**：比 pip 快 10-100 倍
2. **一站式解决方案**：替代 pip + virtualenv + pip-tools + pyenv + pipx
3. **确定性构建**：通过 `uv.lock` 文件确保环境一致性
4. **简单易用**：统一的命令行接口
5. **跨平台支持**：Windows、macOS、Linux 全支持
6. **向后兼容**：完全兼容 pip 和 requirements.txt

## 注意事项

1. uv 本身不需要 Python 环境，它是独立的二进制工具
2. 建议使用官方安装脚本，避免与特定 Python 环境绑定
3. `uv run` 命令可以直接运行脚本，无需手动激活虚拟环境
4. uv 会自动管理缓存，提高重复安装的速度

## 参考资料

1. 使用 uv 管理 Python 依赖 - oldj's blog
2. uv Python 教學，最佳專案管理工具（上） | ZSL 的文檔庫
3. uv 入门教程 — Python 包与环境管理工具 | 菜鸟教程
4. Python包管理不再头疼：uv工具快速上手 - wang_yb - 博客园
5. 使用 uv 管理 Python 環境 - DEV Community
6. 【Python】使用uv管理python虚拟环境_python uv-CSDN博客