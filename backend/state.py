# backend/state.py
from typing import TypedDict
from langgraph.graph import MessagesState
from langchain_core.messages import AnyMessage

# 继承官方的 MessagesState，它自带一个叫做 "messages" 的列表，并且具有自动追加合并(append)的超能力！
class WorkflowState(MessagesState):
    # 你依然可以保留你自己的字段用于特殊用途
    task: str
    current_draft: str