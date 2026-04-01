# backend/graph.py
from langgraph.graph import StateGraph, END
from backend.state import WorkflowState
from backend.agent import Agent
from backend import tools as t



# 你可以在 State 中新增一个字段来记录循环次数，或者通过统计 messages 里的对话轮数
def debate_router(state):
    messages = state.get("messages", [])
    last_message = messages[-1].content
    
    # 获取这个节点发过几次话，防止无限循环（比如最多吵 3 个来回）
    # 粗略计算：在这个路由里，如果 messages 已经超过一定长度，强制放行
    if len(messages) > 15: 
        print("\n[系统警告] 达到最大辩论次数，强制跳出循环！")
        return "next_node"
    
    if "<APPROVE>" in last_message:
        return "next_node" # 走向下一个节点
    else:
        return "loop_back" # 打回重做

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
        # 🌟 如果前端标记了这是一条“需要评审的连线”
        # 我们可以用 add_conditional_edges 来代替 add_edge
        if "is_debate" in edge:  
            workflow.add_conditional_edges(
                from_node, 
                debate_router,
                {
                    "next_node": to_node, # 满意了，走向目标
                    "loop_back": from_node # 不满意，死循环打回给 from_node
                }
            )
        else:
            # 普通的直线流转
            workflow.add_edge(from_node, to_node)
        
    # 如果没有指定起点，默认将第一个节点作为起点，最后一个作为终点
    if nodes_config:
        workflow.set_entry_point(nodes_config[0]["id"])
        workflow.add_edge(nodes_config[-1]["id"], END)
        
    # 编译并挂载传进来的记忆插件
    return workflow.compile(checkpointer=checkpointer)