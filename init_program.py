'''
@Project ：LeetCode_Solution
@File    ：init_program.py.py
@IDE     ：PyCharm
@Author  ：2A9
@Date    ：2026/4/9
'''
import os
import shutil  # 新增：用于移动文件
from dotenv import load_dotenv

load_dotenv()

config_need = {
    "USER_NAME": os.environ.get("USER_NAME", "user"),
    "WORKFLOW_DIR": os.environ.get("WORKFLOW_DIR", "workflows"),
    "WORKSPACE_BASE": os.environ.get("WORKSPACE_BASE", "workspaces"),
    "CHAT_DIR": os.environ.get("CHAT_DIR", "chats"),
    "DEEPSEEK_API_KEY": os.environ.get("DEEPSEEK_API_KEY"),
}


def save_config_to_env(config_dict: dict, env_path: str = ".env"):
    """
    负责将配置字典持久化写入到 .env 文件中
    """
    with open(env_path, "w", encoding="utf-8") as f:
        for k, v in config_dict.items():
            f.write(f"{k}={v}\n")
    print(f"\n[成功] 环境变量已保存至 {env_path}")


def create_project_directories(config_dict: dict):
    """
    负责物理创建目录，并将旧的 workflow 配置自动迁移到新目录
    """
    base_dir = os.path.dirname(os.path.abspath(__file__))

    # 1. 创建所有需要的目录
    dir_keys = ["WORKFLOW_DIR", "WORKSPACE_BASE", "CHAT_DIR"]
    for key in dir_keys:
        old_dir = config_need.get(key, None)
        dir_path = os.path.join(base_dir, config_dict.get(key, ""))
        if dir_path:
            os.makedirs(dir_path, exist_ok=True)
            if old_dir:
                shutil.move(old_dir, dir_path)
            print(f"[成功] 目录已就绪: {dir_path}/")


if __name__ == "__main__":

    config = {}
    # 1. 收集用户输入（修复默认值丢失问题）
    for key, value in config_need.items():
        value_user = input(f"Please enter value of {key} (default is {value}): ")

        # 如果用户输入为空，则显式填入默认值
        config[key] = value_user if value_user != "" else value

    # 2. 调用独立函数执行初始化
    create_project_directories(config)
    save_config_to_env(config)

    print("\n项目环境初始化完成！")
