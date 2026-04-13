# backend/tools/utils.py

import os
from dotenv import load_dotenv

load_dotenv()
from langchain_core.tools import tool
import functools

WORKSPACE_DIR = os.getenv("WORKSPACE_DIR",
                           os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "custom_workspace")))


def log(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        print(f"\n\033[1;32;40m[Tool Call]\033[0m 正在调用工具: \033[1;32;40m{func.__name__}\033[0m")

        # 1. 清理入参打印：剔除掉长篇大论的底层 config 对象，只看大模型传了什么参数
        clean_kwargs = {k: v for k, v in kwargs.items() if k != 'config'}

        result = func(*args, **kwargs)

        # 2. 截断结果打印：设定终端最多显示前 300 个字符
        res_str = str(result)
        max_display_length = 300

        if len(res_str) > max_display_length:
            display_res = res_str[
                              :max_display_length] + f"\n\033[1;33m... [内容过长已截断，真实总长度: {len(res_str)} 字符]\033[0m"
        else:
            display_res = res_str
        if args or clean_kwargs:
            print(f"参数: {args if args else ''} {clean_kwargs}")
        else:
            print("参数: 无")
        print(f"结果: {display_res}\n")

        # 真实返回给大模型的一定要是完整的结果！
        return result

    return wrapper