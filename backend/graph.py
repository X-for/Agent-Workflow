# backend/graph.py
from langgraph.graph import StateGraph, END
from backend.state import WorkflowState
from backend.agent import Agent
from backend import tools as t

# 注意：把 checkpointer 作为参数传进来，而不是在顶部全局定义
def build_dynamic_workflow(nodes_config: list, edges_config: list, checkpointer=None):
    workflow = StateGraph(WorkflowState)
    
    # 动态添加节点
    for node_info in nodes_config:
        node_id = node_info["id"]
        
        selected_tools = []
        for tool_name in node_info.get("tools", []):
            if hasattr(t, tool_name):
                selected_tools.append(getattr(t, tool_name))
        
        # 实例化你写的 Agent 类
        # 如果你前端传的数据里面有些字段没定义，最好用 .get 安全获取，防止 KeyError
        agent_instance = Agent(
            name=node_info.get("label", node_info.get("name", "Unknown")), 
            description=node_info.get("description", ""), 
            tools=selected_tools,
            # 🌟 新增：提取前端传过来的模型信息
            model_id=node_info.get("models", "deepseek-chat"), 
            # provider=node_info.get("provider", "DEEPSEEK")
        )
        workflow.add_node(node_id, agent_instance.run_node)
        
    # 动态添加连线
    for edge in edges_config:
        # 注意：Vue Flow 的连线数据结构通常是 source 和 target
        from_node = edge.get("source", edge.get("from"))
        to_node = edge.get("target", edge.get("to"))
        if from_node and to_node:
            workflow.add_edge(from_node, to_node)
        
    # 如果没有指定起点，默认将第一个节点作为起点，最后一个作为终点
    if nodes_config:
        workflow.set_entry_point(nodes_config[0]["id"])
        workflow.add_edge(nodes_config[-1]["id"], END)
        
    # 编译并挂载传进来的记忆插件
    return workflow.compile(checkpointer=checkpointer)