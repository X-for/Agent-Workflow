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


# 2. 新增：动态汇聚路由工厂 (多分支纯文本节点使用)
def create_fan_in_router(required_keys: list):
    def fan_in_router(state: agents.AgentState) -> str:
        context = state.get("context_data", {})
        # 检查是否所有需要的分支数据都已经就绪
        if all(key in context for key in required_keys):
            return "ready"
        else:
            return "wait"  # 数据没齐，原地挂起

    return fan_in_router


# 3. 新增：工具+汇聚 复合路由工厂 (多分支带工具节点使用)
def create_tool_or_fan_in_router(required_keys: list):
    def router(state: agents.AgentState) -> str:
        tool_calls = state.get("tool_calls", [])
        if tool_calls and len(tool_calls) > 0:
            return "execute_tools"

        context = state.get("context_data", {})
        if all(key in context for key in required_keys):
            return "ready"
        else:
            return "wait"

    return router


# 将其注册为 graph 引擎的内置路由
BUILTIN_ROUTERS = {
    "check_tool_calls": check_tool_calls
}
# 注册动态路由工厂
DYNAMIC_ROUTER_FACTORIES = {
    "fan_in_router": create_fan_in_router,
    "tool_or_fan_in_router": create_tool_or_fan_in_router
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
        if router_func_name in DYNAMIC_ROUTER_FACTORIES:
            router_args = cond_edge_info.get("router_args", {})
            router_func = DYNAMIC_ROUTER_FACTORIES[router_func_name](**router_args)
        elif router_func_name in BUILTIN_ROUTERS:
            router_func = BUILTIN_ROUTERS[router_func_name]
        elif hasattr(agents, router_func_name):
            router_func = getattr(agents, router_func_name)
        else:
            raise ValueError(f"找不到路由函数: '{router_func_name}'")

        # 将 JSON 中的 "END" 字符串转换为 LangGraph 实际的 END 常量
        processed_mapping = {}
        for condition, target in raw_mapping.items():
            key = condition
            val = END if target == "END" else target
            processed_mapping[key] = val

        workflow.add_conditional_edges(
            from_node,
            router_func,
            processed_mapping
        )

    return workflow.compile()
