from .utils import *
from langchain_core.runnables.config import RunnableConfig
import os
from dotenv import load_dotenv

load_dotenv()

# 1. 增强环境变量的容错：提供默认路径
WORKSPACE_BASE = os.environ.get("WORKSPACE_BASE", "./workspace")


def get_safe_task_dir(config: RunnableConfig) -> str:
    """内部辅助函数：安全地获取当前任务的工作目录"""
    # 增强 config 解析容错，默认分配一个 "default_task" 文件夹
    configurable = config.get("configurable", {})
    thread_id = configurable.get("thread_id", "default_task")

    task_dir = os.path.abspath(os.path.join(WORKSPACE_BASE, thread_id))
    if not os.path.exists(task_dir):
        os.makedirs(task_dir, exist_ok=True)
    return task_dir


def get_safe_file_path(task_dir: str, file_path: str) -> str:
    """内部辅助函数：防止路径穿越攻击 (Path Traversal)"""
    # 将用户输入的路径转换为绝对路径
    absolute_path = os.path.abspath(os.path.join(task_dir, file_path))
    # 检查最终路径是否仍然以 task_dir 开头，如果不是，说明发生了路径穿越 (如输入了 ../../)
    if not absolute_path.startswith(task_dir):
        raise ValueError(f"安全警告: 拒绝访问工作区外的文件 ({file_path})")
    return absolute_path


@tool
@log
def save_document(file_name: str, content: str, config: RunnableConfig) -> str:
    """当你需要保存最终的文档、计划或代码时，调用此工具将其写入本地文件。注意可以包含相对路径。"""
    try:
        task_dir = get_safe_task_dir(config)
        file_path = get_safe_file_path(task_dir, file_name)

        # 确保文件所在的父目录(可能是子文件夹)存在
        os.makedirs(os.path.dirname(file_path), exist_ok=True)

        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)
        return f"文件 {file_name} 已成功保存至 {task_dir} 目录。"
    except Exception as e:
        return f"保存文件 {file_name} 时发生错误: {str(e)}"


@tool
@log
def read_document(filename: str, config: RunnableConfig) -> str:
    """当你需要从文件读取内容时调用此工具."""
    try:
        task_dir = get_safe_task_dir(config)
        file_path = get_safe_file_path(task_dir, filename)

        if not os.path.exists(file_path):
            return f"错误: 文件 {filename} 不存在。"

        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
        return f"{filename} 的内容是:\n{content}"
    except Exception as e:
        return f"读取文件 {filename} 时发生错误: {str(e)}"


@tool
@log
def make_dir(dir_name: str, config: RunnableConfig) -> str:
    """当你需要创建一个新的文件夹来组织文件时，调用此工具."""
    try:
        task_dir = get_safe_task_dir(config)
        new_dir_path = get_safe_file_path(task_dir, dir_name)

        if not os.path.exists(new_dir_path):
            os.makedirs(new_dir_path)
            return f"目录 {dir_name} 已成功创建。"
        else:
            return f"目录 {dir_name} 已经存在。"
    except Exception as e:
        return f"创建目录 {dir_name} 时发生错误: {str(e)}"


@tool
@log
def list_files_in_directory(config: RunnableConfig) -> str:
    """当你需要查看当前工作目录下有哪些文件时，调用此工具."""
    try:
        task_dir = get_safe_task_dir(config)

        files_info = []
        # 使用 os.walk 以支持列出子目录中的文件，对大模型了解项目结构更有帮助
        for root, dirs, files in os.walk(task_dir):
            for file in files:
                # 获取相对于 task_dir 的相对路径，不要把绝对路径暴露给大模型
                rel_dir = os.path.relpath(root, task_dir)
                rel_file = os.path.join(rel_dir, file) if rel_dir != "." else file
                files_info.append(rel_file)

        if not files_info:
            return f"当前目录为空。"

        return f"当前目录下的文件有:\n" + "\n".join(files_info)
    except Exception as e:
        return f"列出目录时发生错误: {str(e)}"
    

@tool
@log
# 工具 1：精准读取本地文件（支持指定行数）
def read_local_file(file_path: str, start_line: int = 1, end_line: int = None) -> str:
    """读取本地项目文件的内容。可以指定开始和结束行号来查看特定代码块。"""
    try:
        if not os.path.exists(file_path):
            return f"❌ 错误: 找不到文件 {file_path}"
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            
        if end_line is None:
            end_line = len(lines)
            
        # 加上行号以便大模型精准定位
        result = []
        for i in range(start_line - 1, min(end_line, len(lines))):
            result.append(f"{i + 1} | {lines[i].rstrip()}")
        return "\n".join(result)
    except Exception as e:
        return f"❌ 读取失败: {str(e)}"


@tool
@log
# 工具 2：全局搜索函数/类定义
def search_code(keyword: str, directory: str = ".") -> str:
    """在指定目录及其子目录下的代码文件中搜索关键词（如函数名、类名）。"""
    import glob
    results = []
    # 简单实现：搜索所有 .py 文件 (您可以根据需要扩展 .js, .go 等)
    for filepath in glob.glob(os.path.join(directory, "**/*.py"), recursive=True):
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                for line_num, line in enumerate(f, 1):
                    if keyword in line:
                        results.append(f"{filepath} (Line {line_num}): {line.strip()}")
        except Exception:
            pass
    
    if not results:
        return f"未找到包含 '{keyword}' 的代码。"
    # 截断过长的结果防止爆 token
    return "\n".join(results[:50])