import os
from dotenv import load_dotenv

# 尝试加载现有环境变量作为默认值
load_dotenv()

def get_default(key, default_val):
    return os.environ.get(key, default_val)

def save_config_to_env(config_dict: dict, env_path: str = ".env"):
    """
    将配置字典持久化写入到 .env 文件中
    """
    with open(env_path, "w", encoding="utf-8") as f:
        for k, v in config_dict.items():
            f.write(f"{k}={v}\n")
    print(f"\n[成功] 环境变量已保存至 {env_path}")

def create_project_directories(config_dict: dict):
    """
    负责物理创建目录
    """
    # 需要创建的目录列表
    dir_keys = ["WORKFLOW_DIR", "WORKSPACE_DIR", "CHAT_DIR", "SESSIONS_DIR", "NODES_DIR"]
    
    for key in dir_keys:
        dir_path = config_dict.get(key)
        if dir_path:
            os.makedirs(dir_path, exist_ok=True)
            print(f"[成功] 目录已就绪: {dir_path}")

if __name__ == "__main__":
    project_root = os.path.dirname(os.path.abspath(__file__))
    
    # 定义需要的配置项及其默认值生成逻辑
    config_schema = {
        "USER_NAME": "user",
        "BASE_DIR": project_root,
        "WORKFLOW_DIR": os.path.join(project_root, "workflows"),
        "WORKSPACE_DIR": os.path.join(project_root, "workspaces"),
        "CHAT_DIR": os.path.join(project_root, "chats"),
        "SESSIONS_DIR": os.path.join(project_root, "sessions"),
        "NODES_DIR": os.path.join(project_root, "nodes"),
        "FRONTEND_DIR": os.path.join(project_root, "frontend"),
        "PROJECTS_DIR": os.path.dirname(project_root),
        "LOG_LEVEL": "INFO",
        "DEEPSEEK_API_KEY": "",
        "OPENROUTER_API_KEY": ""
    }

    print("=== Agent Workflow 项目初始化工具 ===")
    
    use_default = input("是否直接使用默认路径和基础配置？(Y/n): ").strip().lower()
    auto_mode = use_default in ["", "y", "yes"]

    final_config = {}
    for key, default_value in config_schema.items():
        current_val = get_default(key, default_value)
        
        # 自动模式下跳过非关键路径配置
        if auto_mode and key not in ["DEEPSEEK_API_KEY", "OPENROUTER_API_KEY"]:
            final_config[key] = current_val
            continue
            
        # 自动模式下，如果 API KEY 已经有值，直接跳过
        if auto_mode and key in ["DEEPSEEK_API_KEY", "OPENROUTER_API_KEY"] and current_val:
            final_config[key] = current_val
            continue

        user_input = input(f"请输入 {key} (当前值: {current_val}): ").strip()
        
        # 如果用户输入为空，则保留当前值
        final_config[key] = user_input if user_input else current_val

    # 执行初始化
    create_project_directories(final_config)
    save_config_to_env(final_config)

    print("\n[完成] 项目环境初始化成功！")
    print("提示: 您可以分别启动前端 (npm run dev) 和后端 (cd backend && uv run uvicorn server:app --reload) 服务。")
