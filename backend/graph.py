# backend/graph.py
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from backend.state import WorkflowState
from backend.agent import Agent
from backend import tools as t
import sqlite3
from langgraph.checkpoint.sqlite import SqliteSaver

# 1. 独立功能：连接到本地数据库文件 (如果没有会自动创建)
# 将所有的记忆统一存放在项目根目录的 checkpoints.sqlite 中
db_connection = sqlite3.connect("checkpoints.sqlite", check_same_thread=False)

# 2. 独立功能：使用 SQLite 替换原本的 MemorySaver
memory = SqliteSaver(db_connection)

# 2. 独立功能：根据前端传来的配置，动态组装工作流
def build_dynamic_workflow(nodes_config: list, edges_config: list):
    workflow = StateGraph(WorkflowState)
    
    # 动态添加节点
    for node_info in nodes_config:
        node_id = node_info["id"]
        # 根据前端传来的工具名，映射到真实的 python 函数
        # 这里为了演示，简单判断如果前端传了 'search' 就挂载工具
        # 【修改这里】：根据前端传来的工具名，动态去 tools.py 里拿真实的函数
        selected_tools = []
        for tool_name in node_info.get("tools", []):
            if hasattr(t, tool_name):
                selected_tools.append(getattr(t, tool_name))
        
        # 实例化你写的 Agent 类
        agent_instance = Agent(
            name=node_info["name"], 
            description=node_info["description"], 
            tools=selected_tools
        )
        workflow.add_node(node_id, agent_instance.run_node)
        
    # 动态添加连线
    for edge in edges_config:
        workflow.add_edge(edge["from"], edge["to"])
        
    # 如果没有指定起点，默认将第一个节点作为起点，最后一个作为终点
    if nodes_config:
        workflow.set_entry_point(nodes_config[0]["id"])
        workflow.add_edge(nodes_config[-1]["id"], END)
        
    # 编译并挂载全局记忆插件
    return workflow.compile(checkpointer=memory)