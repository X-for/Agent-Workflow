import asyncio
import json
import mimetypes
import os
import re
import tempfile
from pathlib import Path
from uuid import uuid4

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from starlette.exceptions import HTTPException


load_dotenv()

# Windows may map .js to text/plain in the registry. ES modules are rejected by
# browsers unless they are served with a JavaScript MIME type.
mimetypes.add_type("text/javascript", ".js")
mimetypes.add_type("text/javascript", ".mjs")

from Graph import GraphEngine, WorkflowValidationError, validate_workflow_schema
import tools as backend_tools


PROJECT_ROOT = Path(os.environ.get("BASE_DIR", Path(__file__).resolve().parent.parent)).resolve()
FRONTEND_DIR = Path(os.environ.get("FRONTEND_DIR", PROJECT_ROOT / "frontend" / "dist")).resolve()
WORKFLOWS_DIR = Path(os.environ.get("WORKFLOW_DIR", PROJECT_ROOT / "workflows")).resolve()
NODES_DIR = Path(os.environ.get("NODES_DIR", PROJECT_ROOT / "nodes")).resolve()
SESSIONS_DIR = Path(os.environ.get("SESSIONS_DIR", PROJECT_ROOT / "sessions")).resolve()

for directory in (WORKFLOWS_DIR, NODES_DIR, SESSIONS_DIR):
    directory.mkdir(parents=True, exist_ok=True)


app = FastAPI(title="Agent Workflow API")
cors_origins = [
    origin.strip()
    for origin in os.environ.get(
        "CORS_ORIGINS", "http://127.0.0.1:5173,http://localhost:5173"
    ).split(",")
    if origin.strip()
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


INVALID_FILENAME = re.compile(r'[<>:"/\\|?*\x00-\x1f]')
REQUEST_ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]{1,100}$")


def normalize_json_filename(value: str, label: str = "文件名") -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label}不能为空")
    filename = value.strip()
    if INVALID_FILENAME.search(filename) or filename in {".", ".."}:
        raise ValueError(f"{label}包含非法字符")
    if filename.endswith((" ", ".")):
        raise ValueError(f"{label}不能以空格或句点结尾")
    if not filename.lower().endswith(".json"):
        filename += ".json"
    return filename


def safe_json_path(directory: Path, value: str, label: str = "文件名") -> Path:
    filename = normalize_json_filename(value, label)
    target = (directory / filename).resolve()
    try:
        target.relative_to(directory.resolve())
    except ValueError as exc:
        raise ValueError(f"{label}越出允许目录") from exc
    return target


def get_tool_registry():
    registry = {}
    for attr_name in dir(backend_tools):
        attr = getattr(backend_tools, attr_name)
        if hasattr(attr, "name") and hasattr(attr, "description"):
            registry[attr.name] = attr
    return registry


tool_registry = get_tool_registry()
engine_cache: dict[str, tuple[int, int, GraphEngine]] = {}


def get_engine(workflow_id: str) -> GraphEngine:
    filename = normalize_json_filename(workflow_id, "工作流 ID")
    file_path = safe_json_path(WORKFLOWS_DIR, filename, "工作流 ID")
    if not file_path.exists():
        raise FileNotFoundError(f"Workflow {filename} not found")

    stat = file_path.stat()
    signature = (stat.st_mtime_ns, stat.st_size)
    cached = engine_cache.get(filename)
    if cached and cached[:2] == signature:
        return cached[2]

    engine = GraphEngine(str(file_path), tool_registry)
    engine_cache[filename] = (signature[0], signature[1], engine)
    return engine


def normalize_messages(messages: list) -> list[dict]:
    normalized = []
    for message in messages if isinstance(messages, list) else []:
        if not isinstance(message, dict) or message.get("role") not in {"user", "assistant"}:
            continue
        content = message.get("content", "")
        if not isinstance(content, str):
            content = json.dumps(content, ensure_ascii=False)
        normalized.append({
            "id": str(message.get("id") or uuid4().hex),
            "role": message["role"],
            "content": content,
        })
    return normalized


chat_memories: dict[str, list[dict]] = {}
session_locks: dict[str, asyncio.Lock] = {}
active_chat_tasks: dict[str, asyncio.Task] = {}


def get_session_lock(session_id: str) -> asyncio.Lock:
    lock = session_locks.get(session_id)
    if lock is None:
        lock = asyncio.Lock()
        session_locks[session_id] = lock
    return lock


def load_session_memory(session_id: str) -> list[dict]:
    if session_id in chat_memories:
        return [dict(message) for message in chat_memories[session_id]]

    file_path = safe_json_path(SESSIONS_DIR, session_id, "会话 ID")
    if file_path.exists():
        try:
            with file_path.open("r", encoding="utf-8") as file_obj:
                messages = normalize_messages(json.load(file_obj))
                chat_memories[session_id] = messages
                return [dict(message) for message in messages]
        except (OSError, json.JSONDecodeError) as exc:
            print(f"加载 Session {session_id} 失败: {exc}")

    chat_memories[session_id] = []
    return []


def save_session_memory(session_id: str, messages: list[dict]) -> None:
    normalized = normalize_messages(messages)
    file_path = safe_json_path(SESSIONS_DIR, session_id, "会话 ID")
    temporary_path = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=SESSIONS_DIR,
            prefix=f".{file_path.stem}-",
            suffix=".tmp",
            delete=False,
        ) as file_obj:
            temporary_path = Path(file_obj.name)
            json.dump(normalized, file_obj, ensure_ascii=False, indent=2)
        os.replace(temporary_path, file_path)
        chat_memories[session_id] = normalized
    finally:
        if temporary_path and temporary_path.exists():
            temporary_path.unlink(missing_ok=True)


def _resolve_node_config(node: dict) -> dict:
    ref = node.get("ref")
    if not ref:
        return node
    ref_path = safe_json_path(NODES_DIR, ref, "节点模板")
    if not ref_path.exists():
        raise WorkflowValidationError(f"节点模板不存在: {ref}")
    try:
        with ref_path.open("r", encoding="utf-8") as file_obj:
            template = json.load(file_obj)
    except json.JSONDecodeError as exc:
        raise WorkflowValidationError(f"节点模板不是有效 JSON: {ref}") from exc
    return {**template, **node}


def validate_workflow_ports(workflow: dict) -> None:
    resolved_nodes = {node["id"]: _resolve_node_config(node) for node in workflow["nodes"]}
    for connection in workflow["connections"]:
        source = resolved_nodes[connection["source_node"]]
        target = resolved_nodes[connection["target_node"]]
        source_ports = {port.get("id") for port in source.get("output_ports", [])}
        target_ports = {port.get("id") for port in target.get("input_ports", [])}
        if connection["source_port"] not in source_ports:
            raise WorkflowValidationError(
                f"节点 {source['id']} 不存在输出端口 {connection['source_port']}"
            )
        if connection["target_port"] not in target_ports:
            raise WorkflowValidationError(
                f"节点 {target['id']} 不存在输入端口 {connection['target_port']}"
            )


class ChatRequest(BaseModel):
    query: str
    workflow_id: str = "test.json"
    session_id: str = "default"
    request_id: str | None = None


class WorkflowCreateRequest(BaseModel):
    filename: str
    workflow_id: str
    nodes: list
    connections: list


class NodeCreateRequest(BaseModel):
    filename: str
    name: str
    type: str = "AGENT"
    model_name: str = "deepseek-chat"
    base_url: str = "https://api.deepseek.com"
    system_prompt: str = ""
    tools: list = Field(default_factory=list)
    input_ports: list = Field(default_factory=list)
    output_ports: list = Field(default_factory=list)


@app.get("/api/nodes")
async def list_available_nodes():
    nodes = [
        {
            "id": "custom_agent",
            "name": "专用节点 (Custom)",
            "type": "CUSTOM_AGENT",
            "description": "拖拽后可在右侧面板直接编写其私有配置",
            "input_ports": [{"id": "in", "name": "输入"}],
            "output_ports": [{"id": "out", "name": "输出"}],
        },
        {
            "id": "builtin_start",
            "name": "开始节点 (START)",
            "type": "START",
            "description": "工作流入口，接收用户输入",
            "output_ports": [{"id": "out_query", "name": "查询输出"}],
            "input_ports": [],
        },
        {
            "id": "builtin_end",
            "name": "结束节点 (END)",
            "type": "END",
            "description": "工作流出口，返回最终结果",
            "input_ports": [{"id": "in_result", "name": "最终结果"}],
            "output_ports": [],
        },
    ]
    for file_path in sorted(NODES_DIR.glob("*.json")):
        try:
            with file_path.open("r", encoding="utf-8") as file_obj:
                data = json.load(file_obj)
            nodes.append({
                "id": file_path.stem,
                "name": data.get("name", file_path.name),
                "type": "AGENT",
                "ref": file_path.name,
                "description": data.get("system_prompt", "")[:50] + "...",
                "input_ports": data.get("input_ports", []),
                "output_ports": data.get("output_ports", []),
            })
        except (OSError, json.JSONDecodeError) as exc:
            print(f"Error loading node {file_path.name}: {exc}")
    return {"status": "success", "nodes": nodes}


@app.post("/api/nodes")
async def create_node(req: NodeCreateRequest):
    try:
        file_path = safe_json_path(NODES_DIR, req.filename, "节点文件名")
        data = {
            "name": req.name,
            "type": req.type,
            "model_name": req.model_name,
            "base_url": req.base_url,
            "system_prompt": req.system_prompt,
            "tools": req.tools,
            "input_ports": req.input_ports,
            "output_ports": req.output_ports,
        }
        with file_path.open("w", encoding="utf-8") as file_obj:
            json.dump(data, file_obj, ensure_ascii=False, indent=4)
        return {"status": "success", "message": "Node created successfully"}
    except ValueError as exc:
        return JSONResponse(status_code=400, content={"status": "error", "message": str(exc)})


@app.get("/api/tools")
async def list_available_tools():
    return {"status": "success", "tools": list(tool_registry.keys())}


@app.get("/api/workflows")
async def list_workflows():
    workflows = []
    for file_path in sorted(WORKFLOWS_DIR.glob("*.json")):
        try:
            with file_path.open("r", encoding="utf-8") as file_obj:
                data = json.load(file_obj)
            workflows.append({
                "id": file_path.name,
                "name": data.get("workflow_id", file_path.name),
                "nodesCount": len(data.get("nodes", [])),
                "description": f"自定义工作流 {file_path.name}",
            })
        except (OSError, json.JSONDecodeError) as exc:
            print(f"Error loading {file_path.name}: {exc}")
    return {"status": "success", "workflows": workflows}


@app.get("/api/workflows/{workflow_id}")
async def get_workflow(workflow_id: str):
    try:
        file_path = safe_json_path(WORKFLOWS_DIR, workflow_id, "工作流 ID")
        if not file_path.exists():
            return JSONResponse(
                status_code=404,
                content={"status": "error", "message": "Workflow not found"},
            )
        with file_path.open("r", encoding="utf-8") as file_obj:
            return {"status": "success", "workflow": json.load(file_obj)}
    except (ValueError, json.JSONDecodeError) as exc:
        return JSONResponse(status_code=400, content={"status": "error", "message": str(exc)})


@app.delete("/api/workflows/{workflow_id}")
async def delete_workflow(workflow_id: str):
    try:
        filename = normalize_json_filename(workflow_id, "工作流 ID")
        file_path = safe_json_path(WORKFLOWS_DIR, filename, "工作流 ID")
        if not file_path.exists():
            return JSONResponse(
                status_code=404,
                content={"status": "error", "message": "Workflow not found"},
            )
        file_path.unlink()
        engine_cache.pop(filename, None)
        return {"status": "success", "message": "Workflow deleted"}
    except ValueError as exc:
        return JSONResponse(status_code=400, content={"status": "error", "message": str(exc)})


@app.post("/api/workflows")
async def create_workflow(req: WorkflowCreateRequest):
    try:
        filename = normalize_json_filename(req.filename, "工作流文件名")
        file_path = safe_json_path(WORKFLOWS_DIR, filename, "工作流文件名")
        data = {
            "workflow_id": req.workflow_id,
            "nodes": req.nodes,
            "connections": req.connections,
        }
        validate_workflow_schema(data)
        validate_workflow_ports(data)
        with file_path.open("w", encoding="utf-8") as file_obj:
            json.dump(data, file_obj, ensure_ascii=False, indent=2)
        engine_cache.pop(filename, None)
        return {"status": "success", "message": "Workflow created successfully"}
    except (ValueError, WorkflowValidationError) as exc:
        return JSONResponse(status_code=400, content={"status": "error", "message": str(exc)})


@app.get("/api/sessions")
async def list_sessions(workflow_id: str):
    try:
        workflow_filename = normalize_json_filename(workflow_id, "工作流 ID")
    except ValueError as exc:
        return JSONResponse(status_code=400, content={"status": "error", "message": str(exc)})

    sessions = []
    prefix = f"{workflow_filename}_"
    for file_path in sorted(SESSIONS_DIR.glob("*.json"), key=lambda path: path.stat().st_mtime, reverse=True):
        if not file_path.name.startswith(prefix):
            continue
        try:
            with file_path.open("r", encoding="utf-8") as file_obj:
                messages = normalize_messages(json.load(file_obj))
            name = "新对话"
            for message in messages:
                if message["role"] == "user":
                    content = message["content"]
                    name = content[:20] + ("..." if len(content) > 20 else "")
                    break
            sessions.append({"id": file_path.stem, "name": name, "messages": messages})
        except (OSError, json.JSONDecodeError) as exc:
            print(f"Error loading session {file_path.name}: {exc}")

    if not sessions:
        sessions.append({
            "id": f"{workflow_filename}_default",
            "name": "默认对话",
            "messages": [],
        })
    return {"status": "success", "sessions": sessions}


@app.post("/api/chat/{request_id}/cancel")
async def cancel_chat(request_id: str):
    if not REQUEST_ID_PATTERN.fullmatch(request_id):
        return JSONResponse(
            status_code=400,
            content={"status": "error", "message": "无效的 request_id"},
        )
    task = active_chat_tasks.get(request_id)
    if task is None or task.done():
        return {"status": "not_found", "message": "任务已结束或不存在"}
    task.cancel()
    return {"status": "success", "message": "取消信号已发送"}


@app.post("/api/chat")
async def chat_endpoint(request: ChatRequest):
    request_id = request.request_id or uuid4().hex
    if not REQUEST_ID_PATTERN.fullmatch(request_id):
        return JSONResponse(
            status_code=400,
            content={"status": "error", "message": "无效的 request_id"},
        )

    current_task = asyncio.current_task()
    if request_id in active_chat_tasks:
        return JSONResponse(
            status_code=409,
            content={"status": "error", "message": "request_id 已在使用"},
        )
    active_chat_tasks[request_id] = current_task

    try:
        workflow_filename = normalize_json_filename(request.workflow_id, "工作流 ID")
        raw_session_id = request.session_id.strip() or "default"
        prefix = f"{workflow_filename}_"
        full_session_id = (
            raw_session_id if raw_session_id.startswith(prefix) else f"{prefix}{raw_session_id}"
        )
        # 仅用于校验；load/save 时会再次校验并构造路径。
        safe_json_path(SESSIONS_DIR, full_session_id, "会话 ID")

        async with get_session_lock(full_session_id):
            history = load_session_memory(full_session_id)
            engine = get_engine(workflow_filename)
            final_state = await engine.run(
                initial_data=request.query,
                history=history,
                workflow_id=workflow_filename,
                session_id=full_session_id,
            )
            final_result = final_state["_result"]
            if not isinstance(final_result, str):
                final_result = json.dumps(final_result, ensure_ascii=False)

            messages = history + [
                {"id": uuid4().hex, "role": "user", "content": request.query},
                {"id": uuid4().hex, "role": "assistant", "content": final_result},
            ]
            save_session_memory(full_session_id, messages)
            return {
                "status": "success",
                "result": final_result,
                "request_id": request_id,
            }
    except asyncio.CancelledError:
        print(f"请求 {request_id} 已取消")
        raise
    except (ValueError, FileNotFoundError, WorkflowValidationError) as exc:
        return JSONResponse(status_code=400, content={"status": "error", "message": str(exc)})
    except Exception as exc:
        import traceback

        traceback.print_exc()
        return JSONResponse(status_code=500, content={"status": "error", "message": str(exc)})
    finally:
        if active_chat_tasks.get(request_id) is current_task:
            active_chat_tasks.pop(request_id, None)


class SPAStaticFiles(StaticFiles):
    async def get_response(self, path: str, scope):
        try:
            response = await super().get_response(path, scope)
        except HTTPException as exc:
            if exc.status_code == 404:
                return await super().get_response("index.html", scope)
            raise
        if response.status_code == 404:
            return await super().get_response("index.html", scope)
        return response


if FRONTEND_DIR.exists():
    app.mount("/", SPAStaticFiles(directory=FRONTEND_DIR, html=True), name="static")


if __name__ == "__main__":
    import uvicorn

    port = int(os.environ.get("PORT", "8000"))
    print(f"\n前端访问地址: http://127.0.0.1:{port}")
    uvicorn.run("server:app", host="127.0.0.1", port=port, reload=True)
