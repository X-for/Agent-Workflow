from typing import TypedDict
from langgraph.graph import StateGraph, END
from agent import Agent
from state import WorkflowState
import tools

workflow = StateGraph(WorkflowState)

my_planner = Agent(name="规划师", description="写计划", tools=[tools.mock_web_search])

workflow.add_node("planner", my_planner.run_node)
# 假设已经执行了：workflow = StateGraph(WorkflowState) 和 workflow.add_node("planner", my_planner.run_node)

# 1. 明确数据流向：设置图的起点和终点
workflow.set_entry_point("planner")  # 任务开始时，第一个把大纸箱交给 planner
workflow.add_edge("planner", END)    # planner 干完活后，直接结束 (END 需要从 langgraph.graph 导入)

# 2. 编译图：把我们画好的草图变成一个可以执行的程序
app = workflow.compile()

# 3. 触发执行：塞入初始的“大纸箱”状态，启动流水线
if __name__ == "__main__":
    # 定义初始状态（包含用户的任务）
    initial_state = {
        "task": "帮我制定一个学习 Python 的两周计划", 
        "current_draft": ""
    }
    
    # invoke 会让纸箱跑完整个流程，并返回最终装满状态的大纸箱
    final_state = app.invoke(initial_state)
    
    print("\n=== 最终结果 ===")
    print(final_state["current_draft"])