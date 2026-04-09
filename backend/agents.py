from langchain_openai import ChatOpenAI
from typing import TypedDict, Optional
import os
from dotenv import load_dotenv

load_dotenv()
import tools

# 1. 定义共享状态 (State)
class AgentState(TypedDict):
    user_input: str
    parsed_query: Optional[str]
    search_results: Optional[str]
    draft: Optional[str]
    feedback: Optional[str]
    is_approved: bool
    tool_calls: Optional[list]


def tool_executor_node(state: AgentState) -> dict:
    """专职工具节点：读取 tool_calls 并执行，将结果回写"""
    tool_calls = state.get("tool_calls", [])
    if not tool_calls:
        return {}

    results = []
    # 遍历并执行清单上的所有工具
    for tc in tool_calls:
        tool_name = tc["name"]
        tool_args = tc["args"]

        # 从 tools 包中动态抓取真实工具并调用
        if hasattr(tools, tool_name):
            tool_obj = getattr(tools, tool_name)
            res = tool_obj.invoke(tool_args)
            results.append(f"【{tool_name} 执行结果】: {res}")
        else:
            results.append(f"【{tool_name} 执行失败】: 找不到该工具")

    return {
        "tool_results": "\n".join(results),
        "tool_calls": []  # 执行完毕，清空队列
    }




class BaseAgent:
    def __init__(self):
        self.tools_names = ""
        self.model = ""
        self.name = ""
        self.base_prompt = ""
        self.prompt = ""
        self.tools = []
        self.temperature = 0.0
        self.api = ""
        self.base_url = "https://openrouter.ai/api/v1"

    def create_dynamic_node(self, config: dict):
        self.model = config["model"]
        self.name = config["name"]
        self.base_prompt = config["system_prompt"]
        self.tools_names = config["tools"]
        self.temperature = config["temperature"]
        self.api = config.get("api", "")
        self.base_url = config.get("base_url", self.base_url)

        actual_tools = []
        for t_name in self.tools_names:
            if hasattr(tools, t_name):
                actual_tools.append(getattr(tools, t_name))
            else:
                raise AttributeError(f"tool {t_name} not available")

        llm = ChatOpenAI(
            model=self.model,
            temperature=self.temperature,
            api_key=os.environ.get(self.api, ""),
            base_url=self.base_url,
        )

        if actual_tools:
            llm = llm.bind_tools(actual_tools)

        def node_func(state: AgentState) -> dict:
            prompt = f"{self.base_prompt}\n\n当前可用上下文状态:\n{state}\n\n请根据要求输出结果："
            response = llm.invoke(prompt)

            if response.tool_calls:
                return {"tool_calls": response.tool_calls}
            else:

                result_text = response.content.strip()
                output_key = config.get("output_key", "draft")
                return {output_key: result_text, "tool_calls": []}

        return node_func
