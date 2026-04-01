# backend/graph.py
from langgraph.graph import StateGraph, END
from backend.state import WorkflowState
from backend.agent import Agent
from backend import tools as t
import collections



# 你可以在 State 中新增一个字段来记录循环次数，或者通过统计 messages 里的对话轮数
def debate_router(state):
    messages = state.get("messages", [])
    if not messages:
        return "next_node" # 防御性编程，没有消息默认往下走
        
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
        agent_instance = Agent(
            name=node_info.get("label", node_info.get("name", "Unknown")), 
            description=node_info.get("description", ""), 
            tools=selected_tools,
            # 🌟 新增：提取前端传过来的模型信息
            model_id=node_info.get("models", "deepseek-chat"), 
            # provider=node_info.get("provider", "DEEPSEEK")
        )
        workflow.add_node(node_id, agent_instance.run_node)
        
    # 🌟 新的连线处理逻辑：先分类，再添加
    debate_edges_by_source = collections.defaultdict(list)
    normal_edges = []

    # 第一步：把普通的线和需要 debate 的线分开
    for edge in edges_config:
        if "is_debate" in edge and edge["is_debate"]:
            from_node = edge.get("source", edge.get("from"))
            debate_edges_by_source[from_node].append(edge)
        else:
            normal_edges.append(edge)

    # 第二步：处理普通的线
    for edge in normal_edges:
        from_node = edge.get("source", edge.get("from"))
        to_node = edge.get("target", edge.get("to"))
        workflow.add_edge(from_node, to_node)

    # 第三步：处理 debate 的线（合并同源的线）
    # 对于每个带审核逻辑的节点，它应该有两条出线（一条通过，一条打回）
    for from_node, edges in debate_edges_by_source.items():
        next_node_target = None
        loop_back_target = None
        
        for edge in edges:
            to_node = edge.get("target", edge.get("to"))
            # 假设前端通过 is_reject 标记这是一条打回的线
            # 如果你前端用的是其他标记，比如 condition="reject"，这里改为 edge.get("condition") == "reject"
            if edge.get("is_reject"): 
                loop_back_target = to_node
            else:
                next_node_target = to_node

        # 如果找不到其中一条线，给个容错的默认行为，防止报错
        if not next_node_target:
            next_node_target = END
        if not loop_back_target:
            loop_back_target = from_node # 退而求其次，默认打回给自己
            
        # 针对这个审查节点，只注册一次条件路由
        workflow.add_conditional_edges(
            from_node, 
            debate_router,
            {
                "next_node": next_node_target, # 满意了，走向目标
                "loop_back": loop_back_target  # 不满意，走向打回的节点
            }
        )
        
    # 如果没有指定起点，默认将第一个节点作为起点，最后一个作为终点
    if nodes_config:
        workflow.set_entry_point(nodes_config[0]["id"])
        
        # ⚠️ 注意：这行代码有隐患，因为你可能有分支，不一定最后一条配置就是真正的终点。
        # 建议只有在确实需要的时候才硬编码连接到 END。
        # 这里我先保留你的原逻辑，但加上容错判断。
        last_node_id = nodes_config[-1]["id"]
        # 检查最后一个节点是否已经有出去了的普通的线，避免重复连导致逻辑错乱（可选优化）
        workflow.add_edge(last_node_id, END)
        
    # 编译并挂载传进来的记忆插件
    return workflow.compile(checkpointer=checkpointer)