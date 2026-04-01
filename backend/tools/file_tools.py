from .utils import *
from langchain_core.runnables.config import RunnableConfig
import os


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