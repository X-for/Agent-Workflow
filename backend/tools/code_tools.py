from .utils import *
import subprocess
import os
import tempfile
import shutil
import sys
from dotenv import load_dotenv

load_dotenv()

# 从环境变量加载真实的工作区目录，如果没有则使用默认路径
WORKSPACE_BASE = os.path.abspath(os.environ.get(
    "WORKSPACE_DIR",
    os.path.join(os.path.dirname(__file__), "..", "..", "workspaces"),
))

# 确保工作区目录存在
if not os.path.exists(WORKSPACE_BASE):
    os.makedirs(WORKSPACE_BASE, exist_ok=True)


def _create_temp_script(content: str, suffix: str) -> str:
    descriptor, temp_path = tempfile.mkstemp(prefix="agent-", suffix=suffix, dir=WORKSPACE_BASE)
    with os.fdopen(descriptor, "w", encoding="utf-8") as file_obj:
        file_obj.write(content)
    return temp_path

@tool
@log
def execute_python_code(code: str) -> str:
    """
    专供代码专家 Agent 使用的工具。在独立临时文件和受控工作目录中执行 Python 代码。
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
    temp_script = None
    try:
        temp_script = _create_temp_script(code, ".py")
            
        uv_executable = shutil.which("uv")
        command = [uv_executable, "run", "--isolated", temp_script] if uv_executable else [sys.executable, temp_script]
        result = subprocess.run(
            command,
            cwd=WORKSPACE_BASE,
            capture_output=True,
            text=True,
            timeout=30 
        )
        
        if result.returncode == 0:
            runtime_note = "uv 隔离环境" if uv_executable else "当前 Python 环境"
            return f"代码在{runtime_note}执行成功。\n标准输出:\n{result.stdout}"
        else:
            return f"代码执行报错 (退出码 {result.returncode})。\n错误日志:\n{result.stderr}"
            
    except subprocess.TimeoutExpired:
        return "错误: 代码执行超时 (超过 30 秒)。请检查是否存在死循环或包下载过慢。"
    except Exception as e:
        return f"沙盒环境发生未知错误: {str(e)}"
    finally:
        if temp_script and os.path.exists(temp_script):
            os.remove(temp_script)

@tool
@log
def execute_javascript_code(code: str) -> str:
    """
    在子进程环境中执行 JavaScript/Node.js 代码。
    输入必须是合法的 JavaScript 代码字符串。
    返回标准输出 (stdout) 或错误跟踪日志 (stderr)。
    注意：系统需要预先安装好 Node.js 环境。
    """
    temp_script = None
    try:
        temp_script = _create_temp_script(code, ".js")
            
        result = subprocess.run(
            ["node", temp_script],
            cwd=WORKSPACE_BASE,
            capture_output=True,
            text=True,
            timeout=15 
        )
        
        if result.returncode == 0:
            return f"JS代码执行成功。\n标准输出:\n{result.stdout}"
        else:
            return f"JS代码执行报错 (退出码 {result.returncode})。\n错误日志:\n{result.stderr}"
            
    except FileNotFoundError:
        return "错误: 未找到 Node.js 环境。请确保已安装 node 并加入到系统 PATH 中。"
    except subprocess.TimeoutExpired:
        return "错误: JS代码执行超时 (超过 15 秒)。"
    except Exception as e:
        return f"JS执行沙盒发生未知错误: {str(e)}"
    finally:
        if temp_script and os.path.exists(temp_script):
            os.remove(temp_script)

@tool
@log
def execute_bash_script(script: str) -> str:
    """
    在子进程环境中执行 Bash shell 脚本。
    输入必须是合法的 Bash 脚本内容。
    返回标准输出 (stdout) 或错误跟踪日志 (stderr)。
    """
    temp_script = None
    try:
        temp_script = _create_temp_script(script, ".sh")
            
        # 根据系统平台选择执行方式
        cmd = ["bash", temp_script] if os.name != "nt" else ["bash.exe", temp_script]
            
        result = subprocess.run(
            cmd,
            cwd=WORKSPACE_BASE,
            capture_output=True,
            text=True,
            timeout=15 
        )
        
        if result.returncode == 0:
            return f"Bash脚本执行成功。\n标准输出:\n{result.stdout}"
        else:
            return f"Bash脚本执行报错 (退出码 {result.returncode})。\n错误日志:\n{result.stderr}"
            
    except FileNotFoundError:
        return "错误: 当前环境不支持 Bash 或未找到 Bash 解释器。"
    except subprocess.TimeoutExpired:
        return "错误: Bash脚本执行超时 (超过 15 秒)。"
    except Exception as e:
        return f"Bash执行沙盒发生未知错误: {str(e)}"
    finally:
        if temp_script and os.path.exists(temp_script):
            os.remove(temp_script)

@tool
@log
def git_safe_modify(absolute_file_path: str, new_content: str, branch_name: str, commit_message: str) -> str:
    """
    在独立 Git worktree 中写入并提交单个文件，不切换或提交用户当前工作区。
    """
    target_path = os.path.abspath(absolute_file_path)
    allowed_root = os.path.abspath(os.environ.get("PROJECTS_DIR", WORKSPACE_BASE))
    try:
        if os.path.commonpath([allowed_root, target_path]) != allowed_root:
            return "拒绝操作: 目标文件越出允许的项目目录。"
    except ValueError:
        return "拒绝操作: 目标文件越出允许的项目目录。"

    file_dir = os.path.dirname(target_path)
    if not os.path.isdir(file_dir):
        return f"拒绝操作: 父级目录 {file_dir} 不存在。"
    if not branch_name or not commit_message.strip():
        return "分支名和提交说明不能为空。"

    def run_cmd(args: list[str], cwd: str):
        return subprocess.run(args, cwd=cwd, capture_output=True, text=True)

    root_result = run_cmd(["git", "rev-parse", "--show-toplevel"], file_dir)
    if root_result.returncode != 0:
        return "目标文件不在已有的 Git 仓库中；工具不会自动初始化或提交整个目录。"
    project_root = os.path.abspath(root_result.stdout.strip())
    try:
        relative_path = os.path.relpath(target_path, project_root)
        if relative_path == ".." or relative_path.startswith(f"..{os.sep}"):
            return "目标文件不属于检测到的 Git 仓库。"
    except ValueError:
        return "目标文件不属于检测到的 Git 仓库。"

    branch_check = run_cmd(["git", "check-ref-format", "--branch", branch_name], project_root)
    if branch_check.returncode != 0:
        return f"分支名无效: {branch_name}"
    branch_exists = run_cmd(
        ["git", "show-ref", "--verify", "--quiet", f"refs/heads/{branch_name}"],
        project_root,
    )
    if branch_exists.returncode == 0:
        return f"分支已存在: {branch_name}，请使用新的分支名。"

    with tempfile.TemporaryDirectory(prefix="agent-git-") as worktree_dir:
        added = False
        try:
            add_result = run_cmd(
                ["git", "worktree", "add", "-b", branch_name, worktree_dir, "HEAD"],
                project_root,
            )
            if add_result.returncode != 0:
                return f"创建隔离 worktree 失败: {add_result.stderr.strip()}"
            added = True

            worktree_target = os.path.join(worktree_dir, relative_path)
            os.makedirs(os.path.dirname(worktree_target), exist_ok=True)
            with open(worktree_target, "w", encoding="utf-8") as file_obj:
                file_obj.write(new_content)

            add_file = run_cmd(["git", "add", "--", relative_path], worktree_dir)
            if add_file.returncode != 0:
                return f"暂存目标文件失败: {add_file.stderr.strip()}"
            diff_check = run_cmd(["git", "diff", "--cached", "--quiet", "--", relative_path], worktree_dir)
            if diff_check.returncode == 0:
                return "新内容与仓库中的原内容相同，没有可提交的修改。"

            commit = run_cmd(
                ["git", "commit", "-m", f"AI Auto-Commit: {commit_message.strip()}"],
                worktree_dir,
            )
            if commit.returncode != 0:
                return f"Commit 执行失败: {(commit.stdout + commit.stderr).strip()}"
        except Exception as exc:
            return f"隔离写入失败: {exc}"
        finally:
            if added:
                run_cmd(["git", "worktree", "remove", "--force", worktree_dir], project_root)

    return (
        "代码已在隔离 worktree 中提交，当前工作区未被切换或暂存。\n"
        f"分支: `{branch_name}`"
    )
