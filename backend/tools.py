from langchain_core.runnables.config import RunnableConfig
import os
from langchain_core.tools import tool
from dotenv import load_dotenv
from duckduckgo_search import DDGS 
load_dotenv()


WORKSPACE_BASE = os.getenv("WORKSPACE_BASE", os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "custom_workspace")))



# 独立功能：定义一个搜索工具
@tool
def web_search(query: str) -> str:
    """
    当你不知道某些最新信息、事实，或者需要了解外部互联网上的知识时，必须调用此工具进行搜索。
    输入参数应该是一个简洁明确的搜索关键词。
    """
    print(f"\n[系统执行] 正在通过 DuckDuckGo 搜索: {query}")
    try:
        # 初始化搜索引擎
        ddgs = DDGS()
        # 搜索最多前 5 条结果
        results = list(ddgs.text(query, max_results=5))
        
        if not results:
            return f"未能找到关于 '{query}' 的搜索结果。"
            
        # 将结果拼接成让大模型易于阅读的格式
        formatted_results = []
        for i, res in enumerate(results):
            # DuckDuckGo 返回的通常有 title(标题), body(摘要), href(链接)
            title = res.get('title', '无标题')
            body = res.get('body', '无摘要')
            link = res.get('href', '')
            formatted_results.append(f"[{i+1}] {title}\n摘要: {body}\n来源: {link}")
            
        # 把这些拼接好的字符串返回给 Agent
        return "\n\n".join(formatted_results)
        
    except Exception as e:
        return f"搜索过程中发生错误: {str(e)}"


@tool
def save_document(file_name: str, content: str, config: RunnableConfig) -> str:
    """当你需要保存最终的文档、计划或代码时，调用此工具将其写入本地文件。"""
    thread_id = config["configurable"].get("thread_id")
    # 精准定位到该任务的专属文件夹
    task_dir = os.path.join(WORKSPACE_BASE, thread_id)
    file_path = os.path.join(task_dir, file_name)
    if not os.path.exists(task_dir):
        os.makedirs(task_dir)    
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(content)
        
    return f"文件 {file_name} 已成功保存至 {task_dir} 目录。"


@tool
def read_document(filename: str, config: RunnableConfig) -> str:
    """当你需要从文件读取内容时调用此工具."""
    thread_id = config["configurable"].get("thread_id")
    # 精准定位到该任务的专属文件夹
    task_dir = os.path.join(WORKSPACE_BASE, thread_id)
    file_path = os.path.join(task_dir, filename)

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
        return f"{filename} 的内容是:\n{content}"
    except FileNotFoundError:
        return f"错误: 文件 {filename} 不存在。"
