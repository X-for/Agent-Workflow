import os
import json
from datetime import datetime
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

from Graph import GraphEngine
import tools as backend_tools

# 基础路径配置
BASE_DIR = os.environ.get("BASE_DIR")
FRONTEND_DIR = os.environ.get("FRONTEND_DIR")
WORKFLOWS_DIR = os.environ.get("WORKFLOW_DIR")
NODES_DIR =os.environ.get("NODES_DIR")
SESSIONS_DIR = os.environ.get("SESSIONS_DIR")

os.makedirs(WORKFLOWS_DIR, exist_ok=True)
os.makedirs(NODES_DIR, exist_ok=True)
os.makedirs(SESSIONS_DIR, exist_ok=True)

# 初始化 FastAPI
app = FastAPI(title="Agent Workflow API")

# 允许跨域请求
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册大模型可用工具
def get_tool_registry():
    """
    动态从 backend/tools 目录获取所有被 @tool 装饰的工具
    """
    registry = {}
    # 遍历 backend_tools 模块中的所有属性
    for attr_name in dir(backend_tools):
        attr = getattr(backend_tools, attr_name)
        # 检查是否是 LangChain 的 BaseTool 实例 (由 @tool 装饰器生成)
        if hasattr(attr, "name") and hasattr(attr, "description"):
            registry[attr.name] = attr
    return registry

tool_registry = get_tool_registry()

# 缓存引擎
engine_cache = {}

def get_engine(workflow_id: str):
    if workflow_id in engine_cache:
        return engine_cache[workflow_id]
        
    file_path = os.path.join(WORKFLOWS_DIR, f"{workflow_id}")
    if not file_path.endswith('.json'):
        file_path += '.json'
        
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Workflow {workflow_id} not found")
        
    engine = GraphEngine(file_path, tool_registry)
    engine_cache[workflow_id] = engine
    return engine

# 请求体模型
class ChatRequest(BaseModel):
    query: str
    workflow_id: str = "test.json"
    session_id: str = "default"

# 内存存储对话历史 (后续可持久化到数据库)
# 结构: { session_id: [ {role: "user", content: "..."}, ... ] }
chat_memories = {}

def load_session_memory(session_id: str):
    """从文件加载 Session 记忆"""
    if session_id in chat_memories:
        return chat_memories[session_id]
    
    file_path = os.path.join(SESSIONS_DIR, f"{session_id}.json")
    if os.path.exists(file_path):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                chat_memories[session_id] = json.load(f)
                return chat_memories[session_id]
        except Exception as e:
            print(f"加载 Session {session_id} 失败: {e}")
    
    chat_memories[session_id] = []
    return []

def save_session_memory(session_id: str, messages: list):
    """保存 Session 记忆到文件"""
    chat_memories[session_id] = messages
    file_path = os.path.join(SESSIONS_DIR, f"{session_id}.json")
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(messages, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"保存 Session {session_id} 失败: {e}")

class WorkflowCreateRequest(BaseModel):
    filename: str
    workflow_id: str
    nodes: list
    connections: list

@app.get("/api/nodes")
async def list_available_nodes():
    """获取所有可用的通用节点（从 nodes 目录）"""
    nodes = []
    
    # 增加一个专用的“空白节点”以支持画布上直接配置
    nodes.append({
        "id": "custom_agent",
        "name": "专用节点 (Custom)",
        "type": "CUSTOM_AGENT",
        "description": "拖拽后可在右侧面板直接编写其私有配置",
        "input_ports": [{"id": "in", "name": "输入"}],
        "output_ports": [{"id": "out", "name": "输出"}]
    })
    
    # 内置基础节点
    nodes.extend([
        {
            "id": "builtin_start",
            "name": "开始节点 (START)",
            "type": "START",
            "description": "工作流入口，接收用户输入",
            "output_ports": [{"id": "out_query", "name": "查询输出"}],
            "input_ports": []
        },
        {
            "id": "builtin_end",
            "name": "结束节点 (END)",
            "type": "END",
            "description": "工作流出口，返回最终结果",
            "input_ports": [{"id": "in_result", "name": "最终结果"}],
            "output_ports": []
        }
    ])
    
    # 扫描 nodes 目录下的专用节点
    if os.path.exists(NODES_DIR):
        for file in os.listdir(NODES_DIR):
            if file.endswith('.json'):
                path = os.path.join(NODES_DIR, file)
                try:
                    with open(path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        nodes.append({
                            "id": file.replace('.json', ''),
                            "name": data.get("name", file),
                            "type": "AGENT",
                            "ref": file,
                            "description": data.get("system_prompt", "")[:50] + "...",
                            "input_ports": data.get("input_ports", []),
                            "output_ports": data.get("output_ports", [])
                        })
                except Exception as e:
                    print(f"Error loading node {file}: {e}")
                    
    return {"status": "success", "nodes": nodes}

class NodeCreateRequest(BaseModel):
    filename: str
    name: str
    type: str = "AGENT"
    model_name: str = "deepseek-chat"
    base_url: str = "https://api.deepseek.com"
    system_prompt: str = ""
    tools: list = []
    input_ports: list = []
    output_ports: list = []

@app.post("/api/nodes")
async def create_node(req: NodeCreateRequest):
    """保存一个新的通用节点配置到 nodes 目录"""
    file_path = os.path.join(NODES_DIR, req.filename)
    if not file_path.endswith('.json'):
        file_path += '.json'
        
    data = {
        "name": req.name,
        "type": req.type,
        "model_name": req.model_name,
        "base_url": req.base_url,
        "system_prompt": req.system_prompt,
        "tools": req.tools,
        "input_ports": req.input_ports,
        "output_ports": req.output_ports
    }
    
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
        
    return {"status": "success", "message": "Node created successfully"}

@app.get("/api/tools")
async def list_available_tools():
    """获取所有已注册的工具列表"""
    return {"status": "success", "tools": list(tool_registry.keys())}

@app.get("/api/workflows")
async def list_workflows():
    workflows = []
    for file in os.listdir(WORKFLOWS_DIR):
        if file.endswith('.json'):
            path = os.path.join(WORKFLOWS_DIR, file)
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    workflows.append({
                        "id": file,
                        "name": data.get("workflow_id", file),
                        "nodesCount": len(data.get("nodes", [])),
                        "description": f"自定义工作流 {file}"
                    })
            except Exception as e:
                print(f"Error loading {file}: {e}")
    return {"status": "success", "workflows": workflows}

@app.get("/api/workflows/{workflow_id}")
async def get_workflow(workflow_id: str):
    """获取单个工作流的详细配置"""
    # 移除可能存在的 .json 后缀，统一处理
    clean_id = workflow_id
    if clean_id.endswith('.json'):
        clean_id = clean_id[:-5]
        
    file_path = os.path.join(WORKFLOWS_DIR, f"{clean_id}.json")
    
    print(f"DEBUG: Loading workflow from {file_path}")
        
    if not os.path.exists(file_path):
        return JSONResponse(status_code=404, content={"status": "error", "message": f"Workflow {clean_id} not found at {file_path}"})
        
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return {"status": "success", "workflow": data}
    except Exception as e:
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})

@app.delete("/api/workflows/{workflow_id}")
async def delete_workflow(workflow_id: str):
    """删除工作流"""
    clean_id = workflow_id
    if clean_id.endswith('.json'):
        clean_id = clean_id[:-5]
    file_path = os.path.join(WORKFLOWS_DIR, f"{clean_id}.json")
    if os.path.exists(file_path):
        os.remove(file_path)
        if f"{clean_id}.json" in engine_cache:
            del engine_cache[f"{clean_id}.json"]
        return {"status": "success", "message": "Workflow deleted"}
    return JSONResponse(status_code=404, content={"status": "error", "message": "Workflow not found"})

@app.post("/api/workflows")
async def create_workflow(req: WorkflowCreateRequest):
    file_path = os.path.join(WORKFLOWS_DIR, req.filename)
    if not file_path.endswith('.json'):
        file_path += '.json'
        
    data = {
        "workflow_id": req.workflow_id,
        "nodes": req.nodes,
        "connections": req.connections
    }
    
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        
    # Invalidate cache if exists
    if req.filename in engine_cache:
        del engine_cache[req.filename]
        
    return {"status": "success", "message": "Workflow created successfully"}

@app.get("/api/sessions")
async def list_sessions(workflow_id: str):
    """获取指定工作流的所有会话列表"""
    sessions = []
    if os.path.exists(SESSIONS_DIR):
        for file in os.listdir(SESSIONS_DIR):
            # 兼容旧格式：session_xxx.json 或 default.json
            # 新格式：workflowId_sessionId.json
            is_new_format = file.startswith(f"{workflow_id}_")
            is_old_format = file.startswith("session_") or file == "default.json"
            
            if file.endswith('.json') and (is_new_format or is_old_format):
                session_id = file.replace('.json', '')
                path = os.path.join(SESSIONS_DIR, file)
                try:
                    with open(path, 'r', encoding='utf-8') as f:
                        messages = json.load(f)
                        # 取第一条用户消息作为会话名称
                        name = "新对话"
                        for msg in messages:
                            if msg['role'] == 'user':
                                name = msg['content'][:20] + ("..." if len(msg['content']) > 20 else "")
                                break
                        
                        # 如果是旧格式且没有 workflow 前缀，我们暂时允许它显示在当前工作流下
                        # 或者你可以选择只显示匹配当前 workflow_id 的文件
                        sessions.append({
                            "id": session_id,
                            "name": name,
                            "messages": messages
                        })
                except Exception as e:
                    print(f"Error loading session {file}: {e}")
    
    # 如果没有找到任何会话，返回一个默认的
    if not sessions:
        default_id = f"{workflow_id}_default"
        sessions.append({
            "id": default_id,
            "name": "默认对话",
            "messages": []
        })
        
    return {"status": "success", "sessions": sessions}

@app.post("/api/chat")
async def chat_endpoint(request: ChatRequest):
    """
    处理前端的聊天请求，调用工作流引擎并返回结果
    """
    try:
        # 确保 session_id 包含 workflow_id 前缀以区分不同工作流的会话
        full_session_id = request.session_id
        if not full_session_id.startswith(f"{request.workflow_id}_"):
            full_session_id = f"{request.workflow_id}_{request.session_id}"

        print(f"\n🔄 接收到前端请求: {request.query}, Workflow: {request.workflow_id}, Session: {full_session_id}")
        
        # 1. 获取或初始化该 Session 的记忆
        messages = load_session_memory(full_session_id)
        
        # 2. 将当前用户输入加入记忆
        messages.append({"role": "user", "content": request.query})
        
        engine = get_engine(request.workflow_id)
        
        # 3. 传入记忆上下文启动工作流
        final_global_state = engine.run(
            start_node_id="start_node",
            start_port_id="out_query",
            initial_data=request.query,
            history=messages
        )
        
        # 获取结果
        final_result = final_global_state.get("end_node:text_output", "未找到结果")
        
        # 4. 将助手回答加入记忆并保存
        messages.append({"role": "assistant", "content": final_result})
        save_session_memory(full_session_id, messages)
        
        print(f"✅ 工作流处理完毕，返回结果长度: {len(str(final_result))}")
        return {"status": "success", "result": final_result}
        
    except Exception as e:
        print(f"❌ API 执行过程中出现错误: {str(e)}")
        import traceback
        traceback.print_exc()
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})

# Serve static files (put this last to avoid overriding API routes)
if os.path.exists(FRONTEND_DIR):
    app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="static")

if __name__ == "__main__":
    import uvicorn
    print("\n🚀 ========================================================")
    print("🚀 启动 FastAPI 服务中...")
    print("🚀 前端访问地址: http://127.0.0.1:8000")
    print("🚀 ========================================================\n")
    uvicorn.run("server:app", host="127.0.0.1", port=8000, reload=True)