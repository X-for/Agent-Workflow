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
    # base_dir = os.getcwd()
    base_dir = os.path.dirname(os.path.abspath(__file__))

    # 1. 创建所有需要的目录（WORKSPACE_BASE, CHAT_DIR, WORKFLOW_DIR）
    dir_keys = ["WORKFLOW_DIR", "WORKSPACE_BASE", "CHAT_DIR"]
    for key in dir_keys:
        dir_path = os.path.join(base_dir, config_dict.get(key, ""))
        os.makedirs(dir_path, exist_ok=True)
        print(f"[成功] 目录已就绪: {dir_path}/")

    # 2. 专门处理旧 workflow 目录的迁移
    # 假设旧目录固定叫 "workflow"
    old_workflow_path = os.path.join(base_dir, "workflow")
    new_workflow_path = os.path.join(base_dir, config_dict.get("WORKFLOW_DIR"))

    # 如果旧目录存在，且名字确实变了（不是原位操作）
    if os.path.exists(old_workflow_path) and os.path.abspath(old_workflow_path) != os.path.abspath(new_workflow_path):
        print(f"\n✦ 检测到历史目录 [workflow]，正在迁移文件至 [{config_dict.get('WORKFLOW_DIR')}]...")

        for item in os.listdir(old_workflow_path):
            s = os.path.join(old_workflow_path, item)
            d = os.path.join(new_workflow_path, item)

            # 只有当目标位置没有同名文件时才移动，防止覆盖用户的最新配置
            if not os.path.exists(d):
                shutil.move(s, d)

        # 搬空后尝试删除旧目录（如果是空的则删除成功）
        try:
            if not os.listdir(old_workflow_path):
                os.rmdir(old_workflow_path)
                print("[成功] 历史配置文件已全部迁移，旧目录已清理。")
        except Exception:
            print("[提醒] 旧目录尚有非 JSON 文件残留，未删除。")


if __name__ == "__main__":
    project_root = os.path.dirname(os.path.abspath(__file__))
    config = {}
    config["BASE_DIR"] = project_root
    # 1. 收集用户输入（修复默认值丢失问题）
    for key, value in config_need.items():
        value_user = input(f"Please enter value of {key} (default is {value}): ")

        # 如果用户输入为空，则显式填入默认值
        config[key] = value_user if value_user != "" else value

    # 2. 调用独立函数执行初始化
    create_project_directories(config)
    save_config_to_env(config)

    print("\n项目环境初始化完成！")
