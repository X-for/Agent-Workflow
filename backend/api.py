# backend/api.py
import os
import json # 新增
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Dict, Any
import inspect
from backend import tools
from langchain_core.messages import AIMessageChunk
from backend.graph import build_dynamic_workflow 
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from dotenv import load_dotenv # 新增
from langchain_core.messages import HumanMessage
from fastapi import FastAPI, UploadFile, File, Form
import shutil # 用于保存文件

# 加载 .env 环境变量
load_dotenv()
# 获取自定义路径，如果没有配置，默认在项目根目录创建一个 custom_workspace
WORKSPACE_BASE = os.getenv("WORKSPACE_BASE", os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "custom_workspace")))

api = FastAPI()

api.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_methods=["*"],
    allow_headers=["*"],
)

class ChatRequest(BaseModel):
    thread_id: str          
    user_input: str         
    nodes: List[Dict[str, Any]] 
    edges: List[Dict[str, Any]] 

@api.post("/api/chat")
async def chat_endpoint(request: ChatRequest):
    # 使用自定义的根目录
    task_dir = os.path.join(WORKSPACE_BASE, request.thread_id)
    if not os.path.exists(task_dir):
        os.makedirs(task_dir)
        
    initial_state = {
        "task": request.user_input, 
        "current_draft": "",
        "messages": [HumanMessage(content=request.user_input)] 
    }
    config = {"configurable": {"thread_id": request.thread_id}}
    
    async def event_stream():
        async with AsyncSqliteSaver.from_conn_string("checkpoints.sqlite") as memory:
            app = build_dynamic_workflow(request.nodes, request.edges, checkpointer=memory)
            async for event in app.astream_events(initial_state, config=config, version="v2"):
                if event["event"] == "on_chat_model_stream":
                    chunk_content = event["data"]["chunk"].content
                    node_name = event.get("metadata", {}).get("langgraph_node", "Agent 网络")
                    if chunk_content:
                        # 🌟 把 agentName 也一起打包进 JSON 发给前端
                        payload = {
                            "content": chunk_content, 
                            "agentName": node_name
                        }
                        yield f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"

                        
    return StreamingResponse(event_stream(), media_type="text/event-stream")

# ✨ 新增：获取历史记录接口
@api.get("/api/history/{thread_id}")
async def get_history(thread_id: str):
    config = {"configurable": {"thread_id": thread_id}}
    async with AsyncSqliteSaver.from_conn_string("checkpoints.sqlite") as memory:
        # 创建一个空图只是为了安全地读取数据库里的 state
        from langgraph.graph import StateGraph, END
        from backend.state import WorkflowState
        dummy_workflow = StateGraph(WorkflowState)
        dummy_workflow.add_node("dummy", lambda x: x)
        dummy_workflow.set_entry_point("dummy")
        app = dummy_workflow.compile(checkpointer=memory)
        
        try:
            state = await app.aget_state(config)
            if not state.values or "messages" not in state.values:
                return {"messages": []}
                
            history = []
            for msg in state.values["messages"]:
                # 区分是用户发的话，还是大模型回的话
                role = "user" if msg.type == "human" else "agent"
                history.append({
                    "role": role,
                    "content": msg.content,
                    "agentName": "Agent 网络" if role == "agent" else ""
                })
            return {"messages": history}
        except Exception as e:
            return {"messages": []}

@api.get("/api/tasks")
async def get_tasks():
    # 改为扫描自定义路径
    if not os.path.exists(WORKSPACE_BASE):
        return {"tasks": []}
    tasks = [d for d in os.listdir(WORKSPACE_BASE) if os.path.isdir(os.path.join(WORKSPACE_BASE, d))]
    return {"tasks": tasks}

@api.get("/api/tools")
async def get_tools():
    # ...保持原样...
    available_tools = []
    for name, obj in inspect.getmembers(tools):
        if hasattr(obj, "name") and hasattr(obj, "description"):
            available_tools.append({"name": obj.name, "description": obj.description})
    return {"tools": available_tools}

class SaveWorkflowRequest(BaseModel):
    thread_id: str
    nodes: List[Dict[str, Any]]
    edges: List[Dict[str, Any]]

@api.post("/api/save_workflow")
async def save_workflow(request: SaveWorkflowRequest):
    # 改为自定义路径
    task_dir = os.path.join(WORKSPACE_BASE, request.thread_id)
    if not os.path.exists(task_dir):
        os.makedirs(task_dir)
    config_path = os.path.join(task_dir, "workflow_config.json")
    with open(config_path, "w", encoding="utf-8") as f:
        json.dump({"nodes": request.nodes, "edges": request.edges}, f, ensure_ascii=False, indent=2)
    return {"status": "success"}


# 文件上传接口
@api.post("/api/upload/{thread_id}")
async def upload_file(thread_id: str, file: UploadFile = File(...)):
    # 精准定位到当前工作流的目录
    task_dir = os.path.join(WORKSPACE_BASE, thread_id)
    if not os.path.exists(task_dir):
        os.makedirs(task_dir)
        
    # 拼装文件的绝对路径
    file_path = os.path.join(task_dir, file.filename)
    
    # 异步保存文件
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        return {"status": "success", "filename": file.filename, "message": "文件上传成功"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

# 复制工作流接口
@api.post("/api/duplicate_workflow")
async def duplicate_workflow(request: dict):
    # request: {"original_id": "旧名字", "new_id": "新名字"}
    original_id = request.get("original_id")
    new_id = request.get("new_id")
    
    if not original_id or not new_id:
        return {"status": "error", "message": "参数缺失"}
        
    old_dir = os.path.join(WORKSPACE_BASE, original_id)
    new_dir = os.path.join(WORKSPACE_BASE, new_id)
    
    # 检查旧目录是否存在
    if not os.path.exists(old_dir):
        return {"status": "error", "message": "源工作流不存在"}
        
    # 如果新目录已经存在，防止覆盖报错
    if os.path.exists(new_dir):
        return {"status": "error", "message": "同名工作流已存在，请换个名字"}
        
    try:
        # 使用 shutil.copytree 完整复制整个文件夹（包含配置、上传的文件等）
        shutil.copytree(old_dir, new_dir)
        return {"status": "success", "message": f"成功复制为 {new_id}"}
    except Exception as e:
        return {"status": "error", "message": f"复制失败: {str(e)}"}

@api.get("/api/models")
async def get_models():
    """扫描 .env 中的配置，返回可用的模型列表"""
    available_models = []
    env_vars = os.environ
    
    # 检查 DeepSeek
    if env_vars.get("DEEPSEEK_API_KEY"):
        available_models.append({
            "id": "deepseek-chat",
            "name": "DeepSeek V3 (通用)",
            "provider": "DEEPSEEK"
        })
        available_models.append({
            "id": "deepseek-reasoner",
            "name": "DeepSeek R1 (推理)",
            "provider": "DEEPSEEK"
        })
        
    # 检查 OpenAI
    if env_vars.get("OPENAI_API_KEY"):
        available_models.append({
            "id": "gpt-4o",
            "name": "GPT-4o",
            "provider": "OPENAI"
        })
        available_models.append({
            "id": "gpt-4o-mini",
            "name": "GPT-4o Mini",
            "provider": "OPENAI"
        })
        
    # 检查通义千问 / 阿里云
    if env_vars.get("QWEN_API_KEY") or env_vars.get("DASHSCOPE_API_KEY"):
        available_models.append({
            "id": "qwen-max",
            "name": "Qwen Max (通义千问)",
            "provider": "QWEN"
        })

    # 如果没配任何 Key，至少给个默认的占位符防错
    if not available_models:
         available_models.append({
            "id": "deepseek-chat",
            "name": "未配置 API Key (默认 DeepSeek)",
            "provider": "DEEPSEEK"
        })
        
    return {"models": available_models}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.api:api", host="0.0.0.0", port=8001, reload=True)