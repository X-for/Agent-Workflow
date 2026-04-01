# UV 用法文档（精炼版）

## 概述
UV 是一个快速的 Python 包管理器和工具链，由 Astral 开发。它结合了 pip、pip-tools、virtualenv 和 pipx 的功能。

## 安装
```bash
# 使用 pip 安装
pip install uv

# 或使用 curl 安装
curl -LsSf https://astral.sh/uv/install.sh | sh
```

## 基本用法

### 1. 包管理
```bash
# 安装包
uv pip install package_name

# 安装特定版本
uv pip install package_name==1.0.0

# 从 requirements.txt 安装
uv pip install -r requirements.txt

# 列出已安装包
uv pip list

# 卸载包
uv pip uninstall package_name
```

### 2. 虚拟环境管理
```bash
# 创建虚拟环境
uv venv

# 激活虚拟环境
# Windows:
.venv\Scripts\activate
# Unix/MacOS:
source .venv/bin/activate

# 在虚拟环境中安装包
uv pip install --python .venv package_name
```

### 3. 项目依赖管理
```bash
# 初始化项目
uv init

# 添加依赖
uv add package_name

# 添加开发依赖
uv add --dev package_name

# 同步依赖
uv sync

# 生成 requirements.txt
uv pip freeze > requirements.txt
```

### 4. 性能优化
```bash
# 使用缓存加速安装
uv pip install --cache-dir ~/.cache/uv package_name

# 并行安装
uv pip install --parallel package_name
```

## 高级功能

### 1. 锁定文件支持
```bash
# 生成 uv.lock 文件
uv lock

# 从锁定文件安装
uv sync --locked
```

### 2. 源管理
```bash
# 添加私有源
uv source add private https://private.pypi.org/simple/

# 设置默认源
uv config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple
```

### 3. 工具链管理
```bash
# 安装 Python 版本
uv python install 3.11

# 列出可用 Python 版本
uv python list

# 设置项目 Python 版本
uv python pin 3.11
```

## 常用命令速查

| 命令 | 描述 |
|------|------|
| `uv pip install <package>` | 安装包 |
| `uv venv` | 创建虚拟环境 |
| `uv add <package>` | 添加项目依赖 |
| `uv sync` | 同步所有依赖 |
| `uv lock` | 生成锁定文件 |
| `uv python install <version>` | 安装 Python 版本 |
| `uv pip list` | 列出已安装包 |
| `uv pip freeze` | 输出依赖列表 |

## 配置选项

### 全局配置
```bash
# 查看配置
uv config list

# 设置镜像源
uv config set global.index-url https://mirrors.aliyun.com/pypi/simple/

# 设置超时时间
uv config set global.timeout 30
```

### 项目配置
在 `pyproject.toml` 中配置：
```toml
[tool.uv]
python = "3.11"
index-url = "https://pypi.org/simple"

[tool.uv.sources]
testpypi = "https://test.pypi.org/simple/"
```

## 最佳实践

1. **使用虚拟环境**：始终为每个项目创建独立的虚拟环境
2. **使用锁定文件**：在生产环境中使用 `uv.lock` 确保依赖一致性
3. **配置镜像源**：在国内使用镜像源加速下载
4. **定期更新**：定期运行 `uv pip list --outdated` 检查更新
5. **清理缓存**：定期清理 `~/.cache/uv` 释放磁盘空间

## 故障排除

### 常见问题
1. **安装速度慢**：配置国内镜像源
2. **权限错误**：使用 `--user` 标志或虚拟环境
3. **依赖冲突**：使用 `uv pip check` 检查依赖关系
4. **网络问题**：设置代理或使用离线模式

### 调试命令
```bash
# 显示详细输出
uv pip install -v package_name

# 检查依赖关系
uv pip check

# 查看缓存信息
uv cache info
```

## 版本信息
```bash
# 查看 uv 版本
uv --version

# 查看帮助
uv --help
```

---

*文档最后更新：2024年*
*更多信息请参考官方文档：https://docs.astral.sh/uv/*