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
    
# 假设当前文件在 backend/tools/ 目录下，那么它的上两级 "../../" 就是项目根目录
PROJECT_ROOT = os.environ.get("PROJECTS_DIR", WORKSPACE_BASE)


@tool
@log
def search_project() -> str:
    """
    当用户要求查看某个项目时，调用此工具获取工作区下的所有项目列表。
    """
    try:
        # 获取所有文件夹名
        projects = next(os.walk(PROJECT_ROOT))[1]
        # 【修复1】：明确告诉大模型根目录地址，让它自己去拼接绝对路径
        return (f"✅ 当前工作区绝对路径为: {PROJECT_ROOT}\n"
                f"包含以下项目目录: {projects}\n"
                f"⚠️ 提示：调用后续工具时，请务必将工作区路径与项目名拼接成完整的绝对路径传入！")
    except StopIteration:
        return f"❌ 无法读取目录: {PROJECT_ROOT}"


@tool
@log
def get_project_structure(absolute_path: str, max_depth: int = 3, special_files: list = None) -> str:
    """
    获取指定项目目录的树状文件结构。自动过滤掉缓存、虚拟环境等无关文件。
    不要轻易选择特定的.git, .vscode目录作为 special_files 作为参数传入 !!!
    不要轻易选择特定的.git, .vscode目录作为 special_files 作为参数传入 !!!
    不要轻易选择特定的.git, .vscode目录作为 special_files 作为参数传入 !!!
    参数:
    - absolute_path: 项目的绝对路径
    - max_depth: 最大向下遍历的层级深度（默认 3 层）
    - special_files: 可选的特殊文件列表，如果提供了这个参数，函数就会将这些已经被排除的文件/目录重新包含在结果中
    """
    if not special_files:
        special_files = []
    if not os.path.exists(absolute_path):
        return f"❌ 找不到目录: {absolute_path}"

    # 定义要无情排除的垃圾目录和文件后缀
    EXCLUDE_DIRS = {'.git', '__pycache__', 'node_modules', 'venv', '.venv', 'env', '.idea', '.vscode'}
    EXCLUDE_EXTS = {'.pyc', '.pyo', '.pyd', '.so', '.dll', '.class', '.lock', '.log'}

    tree_str = []
    base_level = absolute_path.rstrip(os.sep).count(os.sep)

    for root, dirs, files in os.walk(absolute_path):
        # 1. 过滤掉黑名单目录和所有以 . 开头的隐藏目录
        dirs[:] = [d for d in dirs if (d not in EXCLUDE_DIRS and not d.startswith('.')) or (d in special_files)]
        
        # 2. 计算当前深度，超过 max_depth 就停止往下遍历
        level = root.rstrip(os.sep).count(os.sep) - base_level
        if level >= max_depth:
            del dirs[:]  # 清空 dirs 列表，阻止 os.walk 继续向下
            
        indent = '  ' * level
        basename = os.path.basename(root)
        
        # 记录目录
        if level == 0:
            tree_str.append(f"📁 {basename}/")
        else:
            tree_str.append(f"{indent}📂 {basename}/")
            
        # 记录文件（过滤掉隐藏文件和黑名单后缀，除非它在特权名单中）
        sub_indent = '  ' * (level + 1)
        for f in files:
            # 1. 如果该文件在特权白名单中，直接无条件放行
            if f in special_files:
                tree_str.append(f"{sub_indent}📄 {f}")
                continue
                
            # 2. 否则，执行常规的黑名单拦截（拦截隐藏文件和垃圾后缀）
            if f.startswith('.') or any(f.endswith(ext) for ext in EXCLUDE_EXTS):
                continue
                
            tree_str.append(f"{sub_indent}📄 {f}")
            
    result = "\n".join(tree_str)
    # 加一个字数保险，防止超大项目搞崩模型
    return result if len(result) < 15000 else result[:15000] + "\n... (内容过长，已截断)"

@tool
@log
def read_local_file(absolute_file_path: str, start_line: int = 1, end_line: int = None) -> str:
    """读取文件的具体内容。必须传入完整的 absolute_file_path。"""
    try:
        if not os.path.exists(absolute_file_path):
            return f"❌ 找不到文件 {absolute_file_path}"
        with open(absolute_file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        end_line = len(lines) if end_line is None else end_line
        result = [f"{i + 1} | {lines[i].rstrip()}" for i in range(start_line - 1, min(end_line, len(lines)))]
        return "\n".join(result)
    except Exception as e:
        return f"❌ 读取失败: {e}"


@tool
@log
def search_code(keyword: str, absolute_directory: str, special_files: list=None) -> str:
    """在指定的项目绝对路径下搜索代码关键词。支持全文件类型搜索，自动过滤无用目录。"""
    if not os.path.exists(absolute_directory):
        return f"❌ 找不到目录 {absolute_directory}"
    
    if not special_files:
        special_files = []
        
    # 同步黑名单，防止陷入虚拟环境和缓存的泥潭
    EXCLUDE_DIRS = {'.git', '__pycache__', 'node_modules', 'venv', '.venv', 'env', '.idea', '.vscode'}
    # 增加二进制和日志文件后缀，防止尝试用 utf-8 读取它们导致报错
    EXCLUDE_EXTS = {'.pyc', '.pyo', '.pyd', '.so', '.dll', '.class', '.lock', '.log', '.zip', '.tar', '.pdf', '.png', '.jpg'}

    results = []
    
    for root, dirs, files in os.walk(absolute_directory):
        # 1. 目录修剪：将黑名单和隐藏目录直接砍掉，极大提升搜索速度
        dirs[:] = [d for d in dirs if (d not in EXCLUDE_DIRS and not d.startswith('.')) or (d in special_files)]
        
        for f in files:
            # 2. 文件修剪：跳过隐藏文件和二进制/日志文件
            if f not in special_files and (f.startswith('.') or any(f.endswith(ext) for ext in EXCLUDE_EXTS)):
                continue
                
            filepath = os.path.join(root, f)
            try:
                # 尝试读取文件，只找文本内容
                with open(filepath, 'r', encoding='utf-8') as file_obj:
                    for line_num, line in enumerate(file_obj, 1):
                        if keyword in line:
                            # 使用 os.path.relpath 更加安全和优雅
                            rel_path = os.path.relpath(filepath, absolute_directory)
                            results.append(f"{rel_path} (Line {line_num}): {line.strip()}")
                            
                            # 3. 性能优化：一旦搜满 50 条立刻刹车，停止整个搜索过程
                            if len(results) >= 50:
                                return "\n".join(results) + f"\n... (匹配结果过多，仅显示前 50 条)"
            except UnicodeDecodeError:
                # 遇到非 UTF-8 的二进制文件直接跳过
                pass
            except Exception:
                pass
                
    return "\n".join(results) if results else f"未找到包含 '{keyword}' 的代码。"