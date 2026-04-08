from langgraph.graph import StateGraph, END
from agents import AgentState, parser_node, search_node, generator_node, reviewer_node

def should_continue(state: AgentState):
    """条件路由函数：判断是否审核通过，决定下一步流向"""
    if state.get("is_approved"):
        return END
    else:
        return "generator"

# 初始化状态图
workflow = StateGraph(AgentState)

# 添加所有节点
workflow.add_node("parser", parser_node)
workflow.add_node("search", search_node)
workflow.add_node("generator", generator_node)
workflow.add_node("reviewer", reviewer_node)

# 定义固定流向 (添加普通边)
workflow.set_entry_point("parser")
workflow.add_edge("parser", "search")
workflow.add_edge("search", "generator")
workflow.add_edge("generator", "reviewer")

# 定义条件循环边 (将路由函数绑定到 reviewer 节点)
workflow.add_conditional_edges(
    "reviewer",
    should_continue,
    {
        END: END,
        "generator": "generator"
    }
)

# 编译图供外部调用
app = workflow.compile()