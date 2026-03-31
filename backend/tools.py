from langchain_core.runnables.config import RunnableConfig
import os
from langchain_core.tools import tool

# 独立功能：定义一个搜索工具
@tool
def mock_web_search(query: str) -> str:
    """当你需要了解最新的知识或互联网信息时，调用此工具。"""
    print(f"\n[系统执行] 正在搜索互联网: {query}")
    # 这里未来可以接入真实的搜索 API (如 Tavily 或 SerpAPI)
    return f"关于 {query} 的搜索结果：这是一项非常前沿的技术。"


@tool
def save_document(file_name: str, content: str, config: RunnableConfig) -> str:
    """当你需要保存最终的文档、计划或代码时，调用此工具将其写入本地文件。"""
    thread_id = config["configurable"].get("thread_id")
    # 精准定位到该任务的专属文件夹
    task_dir = os.path.join("workspaces", thread_id)
    file_path = os.path.join(task_dir, file_name)
    
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(content)
        
    return f"文件 {file_name} 已成功保存至 {task_dir} 目录。"


@tool
def read_document(filename: str, config: RunnableConfig) -> str:
    """当你需要从文件读取内容时调用此工具."""
    thread_id = config["configurable"].get("thread_id")
    # 精准定位到该任务的专属文件夹
    task_dir = os.path.join("workspaces", thread_id)
    file_path = os.path.join(task_dir, filename)

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
        return f"{filename} 的内容是:\n{content}"
    except FileNotFoundError:
        return f"错误: 文件 {filename} 不存在。"
