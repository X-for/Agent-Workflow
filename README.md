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
The initialization script installs the locked frontend dependencies, syncs the locked backend environment, creates runtime directories, and generates a default `.env` file without overwriting an existing one. Install Node.js/npm and `uv` before running it.

**Linux / macOS:**
```bash
./first.sh
```

After initialization, add the model API keys you use to `.env`.

#### 3. One-Click Start
Run the backend and frontend in separate terminals:

```bash
cd backend && uv run uvicorn server:app --reload
```

```bash
cd frontend && npm run dev
```

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
File and database tools validate resolved paths against `WORKSPACE_DIR`, and code tools use unique temporary files with `cwd=WORKSPACE_DIR`.

This is **working-directory containment, not an operating-system sandbox**. Executed Python/JavaScript/Bash code still has the permissions of the backend process. Only enable code-execution tools for trusted local users; use a container or dedicated sandbox service before exposing them to untrusted input.

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
初始化脚本会按锁文件安装前端依赖、同步后端环境、创建运行目录，并在不覆盖现有配置的前提下生成默认 `.env`。运行前请先安装 Node.js/npm 和 `uv`。

**Linux / macOS:**
```bash
./first.sh
```

初始化完成后，在 `.env` 中填写实际使用的模型 API Key。

#### 3. 一键启动服务
初始化完成后，在两个终端中分别启动后端和前端：

```bash
cd backend && uv run uvicorn server:app --reload
```

```bash
cd frontend && npm run dev
```

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
文件和数据库工具会校验解析后的路径是否位于 `WORKSPACE_DIR` 内，代码工具使用独立临时文件并绑定 `cwd=WORKSPACE_DIR`。

这属于**工作目录约束，并不是操作系统级沙箱**。执行的 Python/JavaScript/Bash 代码仍继承后端进程权限。代码执行工具只应向可信的本地用户开放；面向不可信输入部署前，应使用容器或专用沙箱服务。

---

### 🤝 贡献
欢迎提交 Issue 和 Pull Request 来帮助完善此项目！

### 📄 许可证
MIT License
