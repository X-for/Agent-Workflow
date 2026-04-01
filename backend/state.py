# backend/state.py
from typing import TypedDict, Annotated
import operator
from langgraph.graph import MessagesState
from langchain_core.messages import AnyMessage

# 定义一个简单的 reducer，如果遇到冲突，后写的值覆盖前写的值
def overwrite_draft(left: str, right: str) -> str:
    return right if right is not None else left

class WorkflowState(MessagesState):
    task: str
    # 🌟 使用 Annotated 来告诉 LangGraph，如果遇到多次写入，应该怎么处理
    # 这样就不会报 "Can receive only one value per step" 的错误了
    current_draft: Annotated[str, overwrite_draft]