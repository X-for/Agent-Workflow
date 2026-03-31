# /main.py (项目根目录)
import uvicorn

if __name__ == "__main__":
    # 告诉 uvicorn：去 backend 文件夹下的 api.py 里，找到那个名叫 'api' 的 FastAPI 实例并启动它
    # reload=True 可以在你修改后端代码时自动重启服务，非常方便调试
    uvicorn.run("backend.api:api", host="0.0.0.0", port=8001, reload=True)