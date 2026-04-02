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