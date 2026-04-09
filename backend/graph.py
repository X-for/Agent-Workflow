import agents  # 直接导入整个模块，而不是导入单个函数
from langgraph.graph import StateGraph, END

# 1. 新增通用的工具路由函数
def check_tool_calls(state: agents.AgentState) -> str:
    """通用路由：判断状态中是否包含需要执行的工具"""
    tool_calls = state.get("tool_calls", [])
    if tool_calls and len(tool_calls) > 0:
        return "execute_tools"
    else:
        return "next_step"

# 将其注册为 graph 引擎的内置路由
BUILTIN_ROUTERS = {
    "check_tool_calls": check_tool_calls
}

# 核心构建工厂
def build_graph_from_config(config: dict):
    """根据传入的 JSON 配置字典，动态构建并编译图结构"""
    # 假设 AgentState 定义在 agents 模块中
    workflow = StateGraph(agents.AgentState)

    # 3.1 动态挂载节点
    for node_info in config.get("nodes", []):
        node_name = node_info["name"]
        agent_instance = agents.BaseAgent()
        node_func = agent_instance.create_dynamic_node(node_info)
        workflow.add_node(node_name, node_func)

    workflow.add_node("tool_executor", agents.tool_executor_node)

    # 3.2 设置入口点
    entry_point = config.get("entry_point")
    if entry_point:
        workflow.set_entry_point(entry_point)

    # 3.3 挂载普通边
    for edge_info in config.get("edges", []):
        workflow.add_edge(edge_info["from"], edge_info["to"])

    # 3.4 动态挂载条件边
    for cond_edge_info in config.get("conditional_edges", []):
        from_node = cond_edge_info["from"]
        router_func_name = cond_edge_info["router"]
        raw_mapping = cond_edge_info["mapping"]

        # 动态获取路由函数：先找引擎内置的，再去找 agents 模块里用户自定义的
        if router_func_name in BUILTIN_ROUTERS:
            router_func = BUILTIN_ROUTERS[router_func_name]
        elif hasattr(agents, router_func_name):
            router_func = getattr(agents, router_func_name)
        else:
            raise ValueError(f"找不到路由函数: '{router_func_name}'")

        # 将 JSON 中的 "END" 字符串转换为 LangGraph 实际的 END 常量
        processed_mapping = {}
        for condition, target in raw_mapping.items():
            key = END if condition == "END" else condition
            val = END if target == "END" else target
            processed_mapping[key] = val

        workflow.add_conditional_edges(
            from_node,
            router_func,
            processed_mapping
        )

    return workflow.compile()