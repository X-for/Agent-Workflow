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


@tool
@log
def git_safe_modify(absolute_file_path: str, new_content: str, branch_name: str, commit_message: str) -> str:
    """
    【高危但在沙盒中安全的操作】：将 AI 生成的新代码写入文件，通过 Git 创建新分支隔离风险。
    """

    # 获取文件所在的目录
    working_dir = os.path.dirname(absolute_file_path)

    # 【核心修复】：如果父目录不存在，说明路径非法，直接拒绝
    if not os.path.exists(working_dir):
        return f"❌ 拒绝操作: 父级目录 {working_dir} 不存在，请先确保目录结构正确。"

    # 如果父目录存在，但文件本身不存在，这里我们打印一个提示，然后允许继续
    if not os.path.exists(absolute_file_path):
        print(f"💡 [系统提示] 文件不存在，准备在路径下新建: {absolute_file_path}")

    def run_cmd(cmd: str):
        result = subprocess.run(cmd, shell=True, cwd=working_dir, capture_output=True, text=True)
        return result.returncode, result.stdout, result.stderr

    # 1. 检查是否在 Git 仓库内
    code, _, _ = run_cmd("git rev-parse --is-inside-work-tree")
    if code != 0:
        # 如果不是 Git 仓库，自动在本地为您初始化，并做一次初始提交作为安全基线！
        run_cmd("git init")
        run_cmd("git add .")
        code, out, err = run_cmd('git commit -m "chore: 系统自动初始化的本地代码基线"')
        if code != 0:
            return f"❌ 自动初始化本地 Git 仓库失败: {err}"
        print("💡 [系统提示] 已自动为您将该目录初始化为本地 Git 仓库。")

    # 2. 检查当前工作区是否干净
    code, out, _ = run_cmd("git status --porcelain")
    if out.strip():
        # 如果工作区有未提交的改动，我们也可以霸道一点，自动帮您暂存起来，防止冲突
        run_cmd('git add .')
        run_cmd('git commit -m "chore: 自动暂存用户在 AI 动手前的未提交修改"')

    # 3. 记录当前所在的老分支
    _, current_branch, _ = run_cmd("git branch --show-current")
    current_branch = current_branch.strip() or "master" # 兼容刚初始化的仓库没有 default branch name 的情况

    # 4. 创建并切换到 AI 专属的新分支
    code, out, err = run_cmd(f"git checkout -b {branch_name}")
    if code != 0:
        code, out, err = run_cmd(f"git checkout {branch_name}")
        if code != 0:
            return f"❌ 切换/创建分支失败: {err}"

    # 5. 【执行写入】：将 AI 的代码覆盖写入文件
    try:
        with open(absolute_file_path, 'w', encoding='utf-8') as f:
            f.write(new_content)
    except Exception as e:
        run_cmd(f"git checkout {current_branch}") 
        return f"❌ 代码写入本地文件失败: {e}"

    # 6. Git Add & Commit
    run_cmd(f"git add {absolute_file_path}")
    code, out, err = run_cmd(f'git commit -m "AI Auto-Commit: {commit_message}"')
    if code != 0:
        run_cmd(f"git checkout {current_branch}") 
        return f"❌ Commit 失败 (代码可能没有变化): {out}"

    # 7. 打扫战场：安全切回人类原来的主分支
    run_cmd(f"git checkout {current_branch}")

    return (f"✅ 代码写入并隔离成功！\n"
            f"操作日志：已将修改存入并行分支 `{branch_name}`，并产生了一次 Commit。\n"
            f"提示人类：您可以立刻在终端输入 `git diff {current_branch} {branch_name}` 查看改动。")