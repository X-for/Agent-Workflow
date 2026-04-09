import os
import json
from dotenv import load_dotenv

load_dotenv()
path = os.environ.get("WORKFLOW_DIR", "workflow")


def save_workflow_config(workflow_id: str, config_data: dict, overwrite=False):
    name = f"{workflow_id}.json"
    full_path = os.path.join(path, name)
    if not os.path.exists(full_path):
        os.makedirs(path)
    if os.path.exists(full_path):
        overwrite = True  # 文件不存在, 直接覆盖
    if not overwrite:
        return False  # 不覆盖, 二次提醒
    else:
        with open(f"workflow_configs/{workflow_id}.json", "w", encoding="utf-8") as f:
            json.dump(config_data, f, indent=4)
        return True


def load_workflow_config(workflow_id: str):
    name = f"{workflow_id}.json"
    full_path = os.path.join(path, name)
    with open(full_path, "r") as f:
        return json.load(f)


def scan_workflow_configs():
    workflow_configs = os.listdir(path)
    return workflow_configs
