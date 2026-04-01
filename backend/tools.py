from langchain_core.runnables.config import RunnableConfig
import os
from langchain_core.tools import tool
from dotenv import load_dotenv
from ddgs import DDGS 
import functools
load_dotenv()


WORKSPACE_BASE = os.getenv("WORKSPACE_BASE", os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "custom_workspace")))


def log(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        print(f"\n\033[1;32;40m[Tool Call]\033[0m 正在调用工具: \033[1;32;40m{func.__name__}\033[0m")
        print(f"参数: {args} {kwargs}")
        result = func(*args, **kwargs)
        print(f"结果: {result}\n")
        return result
    return wrapper


@tool
@log
def web_search(query: str) -> str:
    """
    当你不知道某些最新信息、事实，或者需要了解外部互联网上的知识时，必须调用此工具进行搜索。
    输入参数应该是一个简洁明确的搜索关键词。
    """
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
@log
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
@log
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

@tool
@log
def make_dir(dir_name: str, config: RunnableConfig) -> str:
    """当你需要创建一个新的文件夹来组织文件时，调用此工具."""
    thread_id = config["configurable"].get("thread_id")
    # 精准定位到该任务的专属文件夹
    task_dir = os.path.join(WORKSPACE_BASE, thread_id)
    new_dir_path = os.path.join(task_dir, dir_name)
    
    if not os.path.exists(new_dir_path):
        os.makedirs(new_dir_path)
        return f"目录 {dir_name} 已成功创建在 {task_dir} 目录下。"
    else:
        return f"目录 {dir_name} 已经存在于 {task_dir} 目录下。"
    
@tool
@log
def get_content_from_url(url: str) -> str:
    """当你需要获取某个网页的内容时，调用此工具."""
    try:
        import requests
        from bs4 import BeautifulSoup
        
        response = requests.get(url, timeout=10)
        response.raise_for_status()  # 如果请求失败会抛出异常
        
        soup = BeautifulSoup(response.text, 'html.parser')
        # 提取网页的标题和正文（这只是一个简单的示例，实际情况可能需要更复杂的解析）
        title = soup.title.string if soup.title else "无标题"
        paragraphs = soup.find_all('p')
        content = "\n".join(p.get_text() for p in paragraphs[:5])  # 只取前5段
        
        return f"网页标题: {title}\n网页内容:\n{content}"
        
    except Exception as e:
        return f"获取网页内容时发生错误: {str(e)}"
    

@tool
@log
def list_files_in_directory(config: RunnableConfig) -> str:
    """当你需要查看当前工作目录下有哪些文件时，调用此工具."""
    thread_id = config["configurable"].get("thread_id")
    # 精准定位到该任务的专属文件夹
    task_dir = os.path.join(WORKSPACE_BASE, thread_id)
    
    if not os.path.exists(task_dir):
        return f"当前目录 {task_dir} 不存在。"
    
    files = os.listdir(task_dir)
    if not files:
        return f"当前目录 {task_dir} 为空。"
    
    return f"当前目录 {task_dir} 下的文件有:\n" + "\n".join(files)