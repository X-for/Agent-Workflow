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
    id_to_name = {n["id"]: n["name"] for n in request.nodes}        
    async def event_stream():
        import asyncio
        # 🌟 我们不再使用 async for 直接迭代，而是把它放进一个任务里跑
        # 这样即使前端断开连接，任务也能有很大几率执行完毕并存盘
        
        async with AsyncSqliteSaver.from_conn_string("checkpoints.sqlite") as memory:
            app = build_dynamic_workflow(request.nodes, request.edges, checkpointer=memory)
            
            # 使用 asyncio 取消保护，防止前端断开时后端直接自尽
            try:
                # version="v2" 是支持更频繁存盘的
                async for event in app.astream_events(initial_state, config=config, version="v2"):
                    if event["event"] == "on_chat_model_stream":
                        chunk_content = event["data"]["chunk"].content
                        
                        if chunk_content:
                            real_agent_name = "Agent 网络"
                            for tag in event.get("tags", []):
                                if tag.startswith("AGENT_NAME:"):
                                    real_agent_name = tag.split("AGENT_NAME:", 1)[1]
                                    break
                            payload = {
                                "content": chunk_content, 
                                "agentName": real_agent_name,
                                "run_id": event.get("run_id")
                            }
                            yield f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"
            
            except asyncio.CancelledError:
                # 🌟 关键：当用户刷新页面断开连接时，FastAPI 会抛出 CancelledError
                print(f"\n[后台提醒] 客户端断开连接（如刷新页面），当前对话可能未完全保存！")
                # 我们这里不阻断它，随它去，但注意 LangGraph 走到这基本被取消了
                raise
            except Exception as e:
                print(f"[流式输出异常] {e}")
                error_payload = {
                    "content": "\n\n⚠️ **[系统异常]** 执行过程中断。",
                    "agentName": "系统管家",
                    "run_id": "error"
                }
                yield f"data: {json.dumps(error_payload, ensure_ascii=False)}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")

# 获取历史记录接口
@api.get("/api/history/{thread_id}")
async def get_history(thread_id: str):
    config = {"configurable": {"thread_id": thread_id}}
    async with AsyncSqliteSaver.from_conn_string("checkpoints.sqlite") as memory:
        from langgraph.graph import StateGraph, END
        from backend.state import WorkflowState
        dummy_workflow = StateGraph(WorkflowState)
        dummy_workflow.add_node("dummy", lambda x: x)
        dummy_workflow.set_entry_point("dummy")
        app = dummy_workflow.compile(checkpointer=memory)
        
        try:
            # 🌟 如果最后一次状态坏了，我们就往回找所有成功保存的 checkpoints
            # 取最近一次完整保存的状态
            state = await app.aget_state(config)
            
            if not state.values or "messages" not in state.values:
                # 尝试从所有历史记录里找最后一个完整的
                all_states = [s async for s in app.aget_state_history(config)]
                for past_state in all_states:
                    if past_state.values and "messages" in past_state.values:
                        state = past_state
                        break
            
            if not state.values or "messages" not in state.values:
                return {"messages": []}
                
            history = []
            for msg in state.values["messages"]:
                role = "user" if msg.type == "human" else "agent"
                agent_name = getattr(msg, "name", None) or "Agent 网络"
                history.append({
                    "role": role,
                    "content": msg.content,
                    "agentName": agent_name if role == "agent" else "",
                    "runId": getattr(msg, "id", None) # 把 ID 带上，方便前端对齐
                })
            return {"messages": history}
        except Exception as e:
            print(f"获取历史报错: {e}")
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
    import backend.tools as tools
    category_map = tools.category_map
    available_tools = {}
    for name, obj in inspect.getmembers(tools):
        if hasattr(obj, "name") and hasattr(obj, "description"):
            real_func = getattr(obj, "func", None)
            module_full_name = getattr(real_func, "__module__", "other")
            module_name = module_full_name.split(".")[-1]
            if module_name in category_map:
                cat_id = module_name
            else:
                cat_id = "other_tools"
                if cat_id not in category_map:
                    category_map[cat_id] = {"label": "其他工具", "icon": "🛠️"}
            if cat_id not in available_tools:
                available_tools[cat_id] = {
                    "id": cat_id,
                    "label": category_map[cat_id]["label"],
                    "icon": category_map[cat_id]["icon"],
                    "tools": []
                }
            available_tools[cat_id]["tools"].append({
                "name": obj.name,
                "description": obj.description
            })
    return {"categories": list(available_tools.values())}

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
    """动态读取 models.json 配置，返回给前端"""
    config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "models.json")
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            models = json.load(f)
            # 过滤掉没有在 .env 里配置对应 API KEY 的模型
            available_models = [m for m in models if os.environ.get(m["api_key_env"])]
            return {"models": available_models}
    except Exception as e:
        # 如果文件不存在，给个默认兜底
        return {"models": [{"id": "deepseek-chat", "name": "默认 DeepSeek", "provider": "openai_compatible"}]}



import aiosqlite # 引入 aiosqlite，因为 checkpoint 底层是它

# 清除后端持久化记忆接口
@api.delete("/api/history/{thread_id}")
async def clear_history(thread_id: str):
    """
    清除指定 thread_id 的所有历史记录 (清除 SQLite Checkpoint)。
    注意：这里我们直接用 SQL 删除该 thread_id 对应的检查点数据。
    """
    try:
        # LangGraph 的 Checkpointer 默认在 checkpoints 表里存储记忆
        # 不同的库版本表名可能叫 checkpoints 或者 checkpoint
        # 我们用 aiosqlite 直接连接并执行删除
        async with aiosqlite.connect("checkpoints.sqlite") as db:
            await db.execute("DELETE FROM checkpoints WHERE thread_id = ?", (thread_id,))
            await db.execute("DELETE FROM writes WHERE thread_id = ?", (thread_id,))
            await db.commit()
            
        return {"status": "success", "message": f"任务 {thread_id} 的上下文记忆已彻底清空。"}
    except Exception as e:
        print(f"清空记忆报错: {e}")
        return {"status": "error", "message": "清空上下文失败。"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.api:api", host="0.0.0.0", port=8001, reload=True)