# uv Python环境管理工具使用指南

## 一、uv简介

**uv** 是由Astral公司（也是Ruff的开发者）使用Rust编写的Python包管理器和环境管理器。其主要特点包括：

- **极速性能**：比pip快10-100倍
- **功能全面**：集成了包安装、虚拟环境管理、依赖解析、项目构建等能力
- **兼容性好**：兼容pip、pipenv、poetry的生态系统
- **跨平台**：支持macOS、Linux、Windows（PowerShell）

uv可以替代pip、virtualenv、pip-tools等工具，提供依赖管理、虚拟环境创建、Python版本管理等一站式服务。

## 二、安装uv

### 1. 通用安装方式（推荐）
```bash
# 使用官方安装脚本
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### 2. 包管理器安装
```bash
# macOS (Homebrew)
brew install uv

# Windows (PowerShell)
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"

# Linux (apt)
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### 3. 验证安装
```bash
uv --version
```

## 三、核心使用场景

### 1. 基础包安装/卸载
```bash
# 安装包（类似pip install）
uv pip install requests

# 安装特定版本
uv pip install numpy==1.24.0

# 卸载包
uv pip uninstall requests
```

### 2. 虚拟环境管理
```bash
# 创建虚拟环境
uv venv

# 创建指定Python版本的虚拟环境
uv venv --python 3.11

# 激活虚拟环境
# Linux/macOS
source .venv/bin/activate
# Windows
.venv\Scripts\activate

# 在虚拟环境中安装包
uv pip install pandas

# 退出虚拟环境
deactivate
```

### 3. 项目依赖管理
```bash
# 初始化项目（创建pyproject.toml）
uv init

# 添加依赖
uv add requests
uv add numpy --dev  # 开发依赖

# 安装项目所有依赖
uv pip install -e .

# 生成requirements.txt
uv pip freeze > requirements.txt

# 从requirements.txt安装
uv pip install -r requirements.txt
```

### 4. 运行Python代码/脚本
```bash
# 运行Python脚本
uv run script.py

# 运行Python模块
uv run -m module_name

# 运行交互式Python
uv python
```

### 5. 使用uvx运行命令行工具
```bash
# 运行工具（类似pipx）
uvx black  # 格式化代码
uvx ruff   # 代码检查
```

## 四、进阶用法

### 1. 配置镜像源（国内用户）
```bash
# 临时设置镜像源
export UV_INDEX_URL="https://pypi.tuna.tsinghua.edu.cn/simple"

# 永久配置（编辑配置文件）
# 创建或编辑~/.config/uv/config.toml
[install]
index-url = "https://pypi.tuna.tsinghua.edu.cn/simple"
```

### 2. 项目管理
```bash
# 同步依赖（更新lock文件）
uv sync

# 更新所有依赖
uv pip install --upgrade --all

# 查看依赖树
uv pip show --tree
```

### 3. 性能优化
```bash
# 并行安装（默认启用）
uv pip install --parallel

# 缓存管理
uv cache dir    # 查看缓存目录
uv cache clear  # 清理缓存
```

## 五、最佳实践

### 1. 项目结构建议
```
myproject/
├── .venv/           # 虚拟环境（建议.gitignore）
├── pyproject.toml   # 项目配置
├── uv.lock         # 依赖锁文件
├── src/            # 源代码
└── tests/          # 测试代码
```

### 2. 工作流程
```bash
# 1. 创建项目
mkdir myproject && cd myproject
uv init

# 2. 添加依赖
uv add requests pandas
uv add pytest --dev

# 3. 创建虚拟环境
uv venv

# 4. 激活环境并开发
source .venv/bin/activate

# 5. 同步依赖（团队协作）
uv sync
```

### 3. 与现有工具集成
- **替代pip**：`uv pip`命令完全兼容pip
- **替代virtualenv**：`uv venv`创建虚拟环境
- **替代pip-tools**：内置依赖解析和锁定功能
- **兼容poetry/pipenv**：支持`pyproject.toml`

## 六、常见问题解决

### 1. SSL证书错误
```bash
# 跳过SSL验证（不推荐生产环境）
export UV_CERTIFICATES=""
```

### 2. 权限问题
```bash
# 使用用户安装
uv pip install --user package_name
```

### 3. 版本冲突
```bash
# 查看依赖冲突
uv pip check

# 使用uv sync重新解析依赖
uv sync
```

## 总结

uv作为现代Python开发工具，提供了：
1. **极致的性能**：Rust实现带来显著的速度提升
2. **统一的工作流**：一个工具解决包管理、环境管理、依赖解析
3. **良好的兼容性**：无缝对接现有Python生态
4. **简洁的API**：命令直观易记，学习成本低

对于新项目，强烈推荐使用uv作为默认的Python工具链；对于现有项目，可以逐步迁移，先从`uv pip`命令开始替代pip，再逐步使用其他功能。

**注意**：虽然uv功能强大，但在生产环境中建议先在小规模项目上测试，确保与现有工作流程兼容。

---
*资料来源于：菜鸟教程、现代Python开发指南、掘金、GitHub官方文档等*