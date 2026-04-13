from .utils import *
import subprocess
import sys
import os

@tool
@log
def execute_python_code(code: str) -> str:
    """
    专供代码专家 Agent 使用的工具。在完全隔离的子进程环境中执行 Python 代码。
    输入必须是合法的 Python 代码字符串。
    
    【极其重要】：如果你的代码需要依赖第三方库（比如 requests, pandas），
    请在代码的最开头使用 PEP 723 标准的注释来声明依赖，例如：
    
    # /// script
    # requires-python = ">=3.11"
    # dependencies = [
    #     "requests",
    #     "pandas",
    # ]
    # ///
    
    这样隔离环境就会自动为你安装它们！
    会返回标准输出 (stdout) 或完整的错误跟踪日志 (stderr)。
    """
    # 我们把代码写入一个临时文件，让 uv run 去执行它
    # 这样 uv 会自动处理 PEP 723 的依赖并在沙盒里运行
    temp_script = "sandbox_temp.py"
    
    try:
        # 将生成的代码写入临时文件
        with open(temp_script, "w", encoding="utf-8") as f:
            f.write(code)
            
        # 使用 uv run 来隔离执行这个脚本
        # 加上 --isolated 可以防止它读取当前项目的全局依赖
        result = subprocess.run(
            ["uv", "run", "--isolated", temp_script],
            capture_output=True,
            text=True,
            timeout=30  # 给安装第三方包留出充足的时间
        )
        
        if result.returncode == 0:
            return f"代码在沙盒环境执行成功。\n标准输出:\n{result.stdout}"
        else:
            return f"代码执行报错 (退出码 {result.returncode})。\n错误日志:\n{result.stderr}"
            
    except subprocess.TimeoutExpired:
        return "错误: 代码执行超时 (超过 30 秒)。请检查是否存在死循环或包下载过慢。"
    except Exception as e:
        return f"沙盒环境发生未知错误: {str(e)}"
    finally:
        # 无论成功失败，清理临时文件
        if os.path.exists(temp_script):
            os.remove(temp_script)


# 引入您之前在 file_tools.py 里定义好的大本营变量
WORKSPACE_BASE = os.environ.get("WORKSPACE_BASE", "/home/zaq/Workspace/")

@tool
@log
def git_safe_modify(absolute_file_path: str, new_content: str, branch_name: str, commit_message: str) -> str:
    """
    【安全操作】：将 AI 生成的代码写入文件。自动进行 Git 沙盒隔离，绝对精准锚定项目根目录。
    """
    file_dir = os.path.dirname(absolute_file_path)

    if not os.path.exists(file_dir):
        return f"❌ 拒绝操作: 父级目录 {file_dir} 不存在，请先确保目录结构正确。"

    if not os.path.exists(absolute_file_path):
        print(f"💡 [系统提示] 文件不存在，准备在路径下新建: {absolute_file_path}")

    # === 【终极路径定位大法】完全摆脱环境变量依赖 ===
    curr_dir = file_dir
    project_root = None
    
    # 1. 优先往上寻找已经存在的 .git 根目录
    while curr_dir and curr_dir != "/":
        if os.path.exists(os.path.join(curr_dir, ".git")):
            project_root = curr_dir
            break
        curr_dir = os.path.dirname(curr_dir)
    
    # 2. 如果没找到 .git（说明还没建仓），就根据路径特征暴力截取
    if not project_root:
        parts = absolute_file_path.split(os.sep)
        # 如果路径里有 Workspace，就取 Workspace 的下一级目录（如 SEPK）作为根
        if "Workspace" in parts:
            ws_idx = parts.index("Workspace")
            if len(parts) > ws_idx + 1:
                project_root = os.sep.join(parts[:ws_idx + 2])
        
        # 兜底保障
        if not project_root:
            project_root = file_dir

    def run_cmd(cmd: str):
        # 统一在精确计算出的 project_root 下执行所有 Git 命令
        result = subprocess.run(cmd, shell=True, cwd=project_root, capture_output=True, text=True)
        return result.returncode, result.stdout, result.stderr

    # 1. 检查是否在 Git 仓库内
    code, _, _ = run_cmd("git rev-parse --is-inside-work-tree")
    if code != 0:
        run_cmd("git init")
        run_cmd("git add .")
        run_cmd('git commit -m "chore: 系统自动初始化的本地代码基线"')
        print(f"💡 [系统提示] 已自动为项目 {os.path.basename(project_root)} 建立 Git 仓库。")

    # 2. 检查工作区是否有未提交修改
    code, out, _ = run_cmd("git status --porcelain")
    if out.strip():
        run_cmd('git add .')
        run_cmd('git commit -m "chore: 自动暂存用户在 AI 动手前的未提交修改"')

    # 3. 记录当前分支
    _, current_branch, _ = run_cmd("git branch --show-current")
    current_branch = current_branch.strip() or "master"

    # 4. 创建并切换新分支
    code, out, err = run_cmd(f"git checkout -b {branch_name}")
    if code != 0:
        run_cmd(f"git checkout {branch_name}")

    # 5. 【执行写入】
    try:
        with open(absolute_file_path, 'w', encoding='utf-8') as f:
            f.write(new_content)
    except Exception as e:
        run_cmd(f"git checkout {current_branch}") 
        return f"❌ 代码写入本地文件失败: {e}"

    # 6. 【核心修复】：不再使用容易出错的绝对路径 add，直接用全局 add 捕捉新文件
    run_cmd("git add .")
    
    # 提前查验是否有改动被识别到，防止空 Commit 报错
    code, status_out, _ = run_cmd("git status --porcelain")
    if not status_out.strip():
        run_cmd(f"git checkout {current_branch}") 
        return f"❌ Commit 失败: 文件 {os.path.basename(absolute_file_path)} 已写入磁盘，但 Git 未检测到任何变化。可能是新代码与原内容完全相同，或文件被 .gitignore 忽略。"

    code, out, err = run_cmd(f'git commit -m "AI Auto-Commit: {commit_message}"')
    if code != 0:
        run_cmd(f"git checkout {current_branch}") 
        return f"❌ Commit 执行失败: {out} {err}"

    # 7. 切回主分支
    run_cmd(f"git checkout {current_branch}")

    return (f"✅ 代码写入并隔离成功！\n"
            f"提示：已将修改存入分支 `{branch_name}`。\n"
            f"您可以输入 `git diff {current_branch} {branch_name}` 查看改动。")