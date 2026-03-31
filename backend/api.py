# backend/api.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Dict, Any
from langchain_core.messages import AIMessageChunk

# 引入刚刚写的动态组装函数
from graph import build_dynamic_workflow 

api = FastAPI()

# 允许前端跨域访问 (非常重要，否则前端浏览器会报错)
api.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_methods=["*"],
    allow_headers=["*"],
)

# 定义前端必须遵守的数据包格式
class ChatRequest(BaseModel):
    thread_id: str          # 区分不同用户的对话记忆
    user_input: str         # 用户发的话
    nodes: List[Dict[str, Any]] # 前端画的节点
    edges: List[Dict[str, str]] # 前端画的连线

@api.post("/api/chat")
async def chat_endpoint(request: ChatRequest):
    # 1. 拿前端的图纸，动态建图
    app = build_dynamic_workflow(request.nodes, request.edges)
    
    # 2. 组装输入，配置记忆线程
    initial_state = {"task": request.user_input, "current_draft": ""}
    config = {"configurable": {"thread_id": request.thread_id}}
    
    # 3. 异步流式生成推送函数
    async def event_stream():
        # 使用 astream 处理异步数据流
        async for msg, metadata in app.astream(initial_state, config=config, stream_mode="messages"):
            if isinstance(msg, AIMessageChunk) and msg.content:
                # 包装为 SSE 格式，浏览器才能正确解析流式数据
                yield f"data: {msg.content}\n\n"
                
    # 4. 返回流式响应，对接前端的打字机效果
    return StreamingResponse(event_stream(), media_type="text/event-stream")

if __name__ == "__main__":
    import uvicorn
    # 启动 API 服务器
    uvicorn.run(api, host="0.0.0.0", port=8001)