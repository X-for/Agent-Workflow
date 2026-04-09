from langchain_openai import ChatOpenAI
from typing import TypedDict, Optional
import os
from dotenv import load_dotenv
import json
import tools

load_dotenv()


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
    for tc in tool_calls:
        tool_name = tc["name"]
        tool_args = tc["args"]

        if hasattr(tools, tool_name):
            tool_obj = getattr(tools, tool_name)
            res = tool_obj.invoke(tool_args)
            results.append(f"【{tool_name} 执行结果】: {res}")
        else:
            results.append(f"【{tool_name} 执行失败】: 找不到该工具")

    # 【修复】：将结果追加到 search_results 中，防止被覆盖丢失
    existing = state.get("search_results") or ""
    new_res = "\n".join(results)
    combined = existing + "\n\n" + new_res if existing else new_res

    return {
        "search_results": combined,
        "tool_calls": []  # 执行完毕，清空队列
    }


def should_continue(state: AgentState) -> str:
    """路由函数：解析审核员的反馈 JSON，判断是否通过审核"""
    feedback_str = state.get("feedback", "")
    is_approved = False

    if feedback_str:
        try:
            # 移除大模型输出时可能带有的 markdown 代码块标记
            clean_str = feedback_str
            if clean_str.startswith("```json"):
                clean_str = clean_str[7:-3].strip()
            elif clean_str.startswith("```"):
                clean_str = clean_str[3:-3].strip()

            # 解析 JSON 提取布尔值
            result = json.loads(clean_str)
            is_approved = result.get("is_approved", False)
        except Exception:
            # 解析失败则强制打回
            is_approved = False

    # 返回对应的信号字符串，供 graph.py 中的 mapping 进行路由
    if is_approved:
        return "END"
    else:
        return "generator"


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
            current_llm = llm
            output_key = config.get("output_key", "draft")
            # 【防死循环核心逻辑：动态绑定工具】
            # 如果当前节点配置了工具，且状态里还【没有】对应的数据，才给大模型绑定工具。
            # 如果状态里【已经有】数据（说明工具刚执行完绕回来了），就不绑定工具，逼迫它生成总结！
            if actual_tools and not state.get(output_key):
                current_llm = llm.bind_tools(actual_tools)
                prompt = f"{self.base_prompt}\n\n当前可用上下文状态:\n{state}\n\n请根据要求输出结果："
            else:
                prompt = f"{self.base_prompt}\n\n当前可用上下文状态:\n{state}\n\n⚠️工具已执行完毕并返回了上述结果。请直接输出总结，绝对不要再说多余的话！"

            response = current_llm.invoke(prompt)

            if response.tool_calls:
                return {"tool_calls": response.tool_calls}
            else:
                result_text = response.content.strip()
                output_key = config.get("output_key", "draft")

                # 【核心修复】：区分追加与覆盖
                # 如果这个节点配置了工具（self.tools_names 不为空），说明它是 search 节点，必须保留搜索结果并追加总结
                if self.tools_names:
                    existing_data = state.get(output_key)
                    if existing_data:
                        final_text = f"{existing_data}\n\n[Agent总结]: {result_text}"
                    else:
                        final_text = result_text
                # 如果没有配置工具（如 generator 和 reviewer），说明它是纯文本节点，必须【直接覆盖】旧状态！
                # 这样 reviewer 每次输出的都是干净的、可被解析的单一 JSON！
                else:
                    final_text = result_text

                return {output_key: final_text, "tool_calls": []}

            return node_func
