# Agent Workflow

[English](#english) | [简体中文](#chinese)

<a id="english"></a>
## English Version

Agent Workflow is a powerful, node-based **drag-and-drop visual orchestration system for Multi-Agent systems**. It allows users to combine multiple Large Language Models (LLMs) into complex processing flows via a visual canvas, enabling task routing, concurrent execution, tool calling, and result aggregation.

### 🌟 Core Features

- **🎨 Visual Drag-and-Drop Orchestration**: Built on React Flow, supporting free drag-and-drop node generation and connection.
- **🧠 Multi-Agent Collaboration**: Mix and match models from different providers (e.g., DeepSeek, Claude, GPT-4) in a single workflow to leverage their respective strengths.
- **⚡ Native Asynchronous Concurrency Engine**: The backend Graph Engine supports "Level-by-level Parallelism", where multiple Agents at the same level are triggered simultaneously and executed asynchronously, greatly improving execution efficiency.
- **🛠️ Rich Tool Integration**:
  - **Code Sandbox**: Supports isolated environment execution for Python, Node.js (JS/TS), and Bash.
  - **Web Search**: Supports global web search and intelligent cleaning/extraction of web page content.
  - **Data Analysis**: Supports database Schema extraction, SQL queries, and local file reading.
- **🔄 Session Memory & Interruption**: Supports context memory (Session) for multi-turn dialogues, and allows safe interruption (Abort) of large inference tasks at any time.
- **🌗 Global Dark Mode**: Beautiful UI perfectly adapted for dark/light mode switching.

---

### 🚀 Quick Start

#### 1. Prerequisites
- Ensure [Node.js](https://nodejs.org/) is installed (for frontend).
- System supports Bash or PowerShell.

#### 2. One-Click Initialization
We provide automated initialization scripts to download frontend dependencies, install `uv` (modern Python package manager), sync the backend environment, and generate the default `.env` configuration file.

**Linux / macOS:**
```bash
./first.sh
```

**Windows:**
Double-click `first.bat`, or run in the command line:
```cmd
first.bat
```
*(During initialization, follow the prompts to enter your model keys like `DEEPSEEK_API_KEY`, or press Enter to use the default configuration)*

#### 3. One-Click Start
After initialization, simply run the start script for daily development and usage:

**Linux / macOS:**
```bash
./start.sh
```

**Windows:**
Double-click `start.bat`.

Once the service is started, open your browser and visit the local link prompted in the console (usually `http://localhost:5173` by default) to enter the workflow management system.

---

### 🧩 System Architecture

#### Frontend
- **Tech Stack**: React, TypeScript, Vite, Tailwind CSS
- **Core Libraries**: 
  - `@xyflow/react` (for drag-and-drop workflow canvas)
  - `lucide-react` (icon library)
  - `react-markdown` (for rendering rich text output of Multi-Agents)
- **Main Pages**:
  - `/` (Selection): Workflow library to manage, run, edit, and delete workflows.
  - `/create`: Drag-and-drop builder, supporting dynamic loading of existing workflows, modifying general node templates, and configuring Agent parameters.
  - `/chat/:id`: Immersive chat interface, supporting multi-session switching, generation interruption, and Markdown rendering.

#### Backend
- **Tech Stack**: Python, FastAPI, LangChain, Uvicorn
- **Core Architecture**:
  - `server.py`: Native asynchronous FastAPI routing layer managing HTTP APIs.
  - `Graph.py`: Core graph execution engine. Based on a BFS batching algorithm, it implements topological sorting and **concurrent node execution**.
  - `Agent.py`: Agent instance class. Built-in micro Agent Loop supporting automatic tool calling, intelligent routing of `base_url` and corresponding API Keys (compatible with OpenRouter, OpenAI, DeepSeek, etc.).
  - `tools/`: A collection of capabilities mounted on Agents (sandbox, search, file system, etc.).

---

### 💡 Built-in Example Workflows

The project includes two highly representative workflows that demonstrate the system's powerful capabilities:

1. **`general_multi_agent.json` (General Multi-Agent System)**
   - **Architecture**: Dispatcher $\rightarrow$ Three Experts (Code, Search, Analysis) $\rightarrow$ Summarizer
   - **Usage**: Throw in a complex request, and the Dispatcher will automatically break it down and distribute it to three Agents (coding, searching, and analysis) for parallel processing. Finally, the results are aggregated into a perfect report by the Summarizer.

2. **`model_discussion_group.json` (Multi-Model Discussion Group)**
   - **Architecture**: Moderator $\rightarrow$ [Tech Expert, Biz Expert, Security Expert] $\rightarrow$ Secretary
   - **Usage**: Send the same proposal to three Agents with different system prompts (or even different underlying model providers) to let them offer insights from their respective strengths. Finally, the Secretary compiles a "Multi-dimensional Review Report".

---

### 🔒 Directory Permissions & Security
The system features strict built-in directory isolation:
- The `WORKSPACE_DIR` in `.env` is the **only legal operation sandbox** for all Agents to execute code (Python/JS/Bash) and read/write files.
- Underlying tools like `code_tools.py` forcefully bind `cwd=WORKSPACE_DIR` when executing `subprocess`, completely preventing temporary files generated by models from polluting the project source code.

---

### 🤝 Contributing
Issues and Pull Requests are welcome to help improve this project!

### 📄 License
MIT License

---

<a id="chinese"></a>
## 简体中文版

Agent Workflow 是一个强大的、基于节点的**多智能体（Multi-Agent）拖拽式可视化编排系统**。它允许用户通过可视化的画布，将多个大语言模型（LLMs）组合成复杂的处理流，实现任务路由、并发执行、工具调用与结果汇总。

### 🌟 核心特性

- **🎨 可视化拖拽编排**：基于 React Flow 构建，支持自由拖拽生成节点、连线。
- **🧠 多智能体协作**：支持在一个工作流中混用来自不同厂商的大模型（如 DeepSeek, Claude, GPT-4），发挥各自的特长。
- **⚡ 原生异步并发引擎**：后端的 Graph Engine 支持“层级并行（Level-by-level Parallelism）”，位于同一层级的多个 Agent 会被同时触发并异步执行，极大提升执行效率。
- **🛠️ 丰富的工具挂载**：
  - **代码沙盒**：支持 Python, Node.js (JS/TS), Bash 的隔离环境执行。
  - **网络搜索**：支持全网搜索及网页正文智能清洗与抓取。
  - **数据分析**：支持数据库 Schema 提取、SQL 查询、本地文件读取。
- **🔄 会话记忆与中断**：支持多轮对话的上下文记忆（Session），且随时支持安全中断（Abort）正在执行的大型推理任务。
- **🌗 全局深色模式**：优美的 UI 界面，完美适配深色/浅色模式切换。

---

### 🚀 快速开始

#### 1. 环境准备
- 确保已安装 [Node.js](https://nodejs.org/) (用于前端)
- 系统支持 Bash 或 PowerShell

#### 2. 一键初始化
我们提供了自动化的初始化脚本，它会自动下载前端依赖、安装 `uv` (Python 现代包管理器)、同步后端环境并生成默认的 `.env` 配置文件。

**Linux / macOS:**
```bash
./first.sh
```

**Windows:**
双击运行 `first.bat`，或在命令行中执行：
```cmd
first.bat
```
*(在初始化过程中，按提示输入你的 `DEEPSEEK_API_KEY` 等模型密钥，或直接回车使用默认配置)*

#### 3. 一键启动服务
初始化完成后，日常开发和使用只需运行一键启动脚本：

**Linux / macOS:**
```bash
./start.sh
```

**Windows:**
双击运行 `start.bat`。

服务启动后，打开浏览器访问控制台提示的本地链接（默认通常为 `http://localhost:5173`）即可进入工作流管理系统。

---

### 🧩 系统架构

#### 前端 (Frontend)
- **技术栈**: React, TypeScript, Vite, Tailwind CSS
- **核心库**: 
  - `@xyflow/react` (用于拖拽式工作流画布)
  - `lucide-react` (图标库)
  - `react-markdown` (渲染多智能体的富文本输出)
- **主要页面**:
  - `/` (Selection): 工作流库，管理、运行、编辑、删除工作流。
  - `/create`: 拖拽式构建器，支持动态加载已有工作流、修改通用节点模板、配置 Agent 参数。
  - `/chat/:id`: 沉浸式聊天界面，支持多会话切换、打断生成、Markdown 渲染。

#### 后端 (Backend)
- **技术栈**: Python, FastAPI, LangChain, Uvicorn
- **核心架构**:
  - `server.py`: 原生异步的 FastAPI 路由层，管理 HTTP API。
  - `Graph.py`: 核心图执行引擎。基于 BFS 批处理算法，实现拓扑排序与**并发节点执行**。
  - `Agent.py`: Agent 实例类。内置微型 Agent Loop，支持自动工具调用，并能智能匹配 `base_url` 与对应的 API Key（兼容 OpenRouter, OpenAI, DeepSeek 等）。
  - `tools/`: 挂载给 Agent 的能力集合（沙盒、搜索、文件系统等）。

---

### 💡 内置示例工作流

项目内置了两个极具代表性的工作流，展示了系统的强大能力：

1. **`general_multi_agent.json` (通用多智能体系统)**
   - **架构**: 路由中枢 (Dispatcher) $\rightarrow$ 三大专员 (Code, Search, Analysis) $\rightarrow$ 总结员 (Summarizer)
   - **用途**: 丢入一个复杂需求，Dispatcher 会自动将其拆解并分发给懂代码、懂搜索、懂分析的三个 Agent 并行处理，最后汇总成一份完美的报告。

2. **`model_discussion_group.json` (多模型方案讨论组)**
   - **架构**: 主持人 $\rightarrow$ [技术专家, 商业专家, 安全专家] $\rightarrow$ 书记员
   - **用途**: 将同一个方案发给具有不同系统提示词（甚至不同底层模型厂商）的三个 Agent，让它们从各自的特长角度提出见解，最后由书记员整理出一份《多维评审报告》。

---

### 🔒 目录权限与安全性
系统内置了严格的目录隔离：
- `.env` 中的 `WORKSPACE_DIR` 是所有 Agent 执行代码（Python/JS/Bash）、读写文件的**唯一合法操作沙盒**。
- `code_tools.py` 等底层工具在执行 `subprocess` 时强制绑定了 `cwd=WORKSPACE_DIR`，彻底杜绝了模型产生的临时文件污染项目源码。

---

### 🤝 贡献
欢迎提交 Issue 和 Pull Request 来帮助完善此项目！

### 📄 许可证
MIT License