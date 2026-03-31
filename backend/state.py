# 1. 独立功能：必须先定义“大纸箱”里装什么标签 (这就是 State 的结构)
from typing import TypedDict


class WorkflowState(TypedDict):
    task: str
    current_draft: str
    # 未来还可以加别的标签