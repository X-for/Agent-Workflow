import agents
from langgraph.graph import StateGraph, END


# 1. 基础工具路由工厂
def create_check_tool_calls(node_name: str = None):
    def check_tool_calls(state: agents.AgentState) -> str:
        tool_calls = state.get("tool_calls", {}).get(node_name, [])
        
        # 如果没有工具调用，直接走下一步
        if not tool_calls or len(tool_calls) == 0:
            return "next_step"
            
        # --- 物理熔断 ---
        log_key = f"{node_name}_tool_logs"
        tool_logs = state.get("context_data", {}).get(log_key, "")
        # 计算出现过多少次成功或失败的标记
        current_turn_tool_count = tool_logs.count("执行结果") + tool_logs.count("执行失败")

        # 【终极必杀】：针对不同节点，设定不同的物理限流
        if node_name == "recorder":
            max_limit = 1
        elif node_name == "agent":
            # 为代码助手的深度检索放宽限流，允许它在不同文件间穿梭 8 次
            max_limit = 8 
        else:
            max_limit = 3
        
        if current_turn_tool_count >= max_limit:
            print(f"\n🚫 [系统底层拦截] 节点 '{node_name}' 触发限流(已调用{current_turn_tool_count}次)，强制打卡下班！")
            return "next_step"
        
        # -------------------------
            
        return "execute_tools"

    return check_tool_calls


# 2. 纯文本汇聚闸机工厂
def create_fan_in_router(required_keys: list, node_name: str = None):
    def fan_in_router(state: agents.AgentState) -> str:
        context = state.get("context_data", {})
        if all(key in context for key in required_keys):
            return "ready"
        else:
            return "wait"

    return fan_in_router


# 3. 工具+汇聚复合闸机工厂
def create_tool_or_fan_in_router(required_keys: list, node_name: str = None):
    def router(state: agents.AgentState) -> str:
        tool_calls = state.get("tool_calls", {}).get(node_name, [])
        if tool_calls and len(tool_calls) > 0:
            return "execute_tools"

        context = state.get("context_data", {})
        if all(key in context for key in required_keys):
            return "ready"
        else:
            return "wait"

    return router


DYNAMIC_ROUTER_FACTORIES = {
    "check_tool_calls": create_check_tool_calls,
    "fan_in_router": create_fan_in_router,
    "tool_or_fan_in_router": create_tool_or_fan_in_router
}


def build_graph_from_config(config: dict):
    workflow = StateGraph(agents.AgentState)

    # 动态挂载 Agent 节点及其专属工具节点
    for node_info in config.get("nodes", []):
        node_name = node_info["name"]
        agent_instance = agents.BaseAgent()
        node_func = agent_instance.create_dynamic_node(node_info)
        workflow.add_node(node_name, node_func)

        # 如果配了工具，生成专属的 Tool 节点并挂载
        if node_info.get("tools"):
            tool_node_name = f"{node_name}_tools"
            workflow.add_node(tool_node_name, agents.create_tool_node(node_name))

    entry_point = config.get("entry_point")
    if entry_point:
        workflow.set_entry_point(entry_point)

    for edge_info in config.get("edges", []):
        workflow.add_edge(edge_info["from"], edge_info["to"])

    for cond_edge_info in config.get("conditional_edges", []):
        from_node = cond_edge_info["from"]
        router_func_name = cond_edge_info["router"]
        raw_mapping = cond_edge_info["mapping"]

        if router_func_name in DYNAMIC_ROUTER_FACTORIES:
            router_args = cond_edge_info.get("router_args", {})
            # 防污染：复制一份字典并注入当前发件人标识
            current_args = router_args.copy()
            current_args["node_name"] = from_node
            router_func = DYNAMIC_ROUTER_FACTORIES[router_func_name](**current_args)
        elif hasattr(agents, router_func_name):
            router_func = getattr(agents, router_func_name)
        else:
            raise ValueError(f"找不到路由函数: '{router_func_name}'")

        processed_mapping = {}
        for condition, target in raw_mapping.items():
            key = condition
            val = END if target == "END" else target
            processed_mapping[key] = val

        workflow.add_conditional_edges(from_node, router_func, processed_mapping)

    return workflow.compile()