from .utils import *
import subprocess

@tool
@log
def execute_python_code(code: str) -> str:
    """
    专供代码专家 Agent 使用的工具。在隔离的子进程中执行 Python 代码。
    输入必须是合法的 Python 代码字符串。
    会返回标准输出 (stdout) 或完整的错误跟踪日志 (stderr)。
    """
    try:
        # 使用 subprocess 运行代码，限制最大执行时间为 10 秒防死循环
        result = subprocess.run(
            ["python", "-c", code],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode == 0:
            return f"代码执行成功。\n标准输出:\n{result.stdout}"
        else:
            return f"代码执行报错 (退出码 {result.returncode})。\n错误日志:\n{result.stderr}"
            
    except subprocess.TimeoutExpired:
        return "错误: 代码执行超时 (超过 10 秒)。请检查是否存在死循环。"
    except Exception as e:
        return f"沙盒环境发生未知错误: {str(e)}"