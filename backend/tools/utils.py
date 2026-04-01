# backend/tools/utils.py


import os
from dotenv import load_dotenv
load_dotenv()
from langchain_core.tools import tool
import functools


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