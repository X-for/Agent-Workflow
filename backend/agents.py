from langchain_openai import ChatOpenAI
from typing import TypedDict, Optional, Annotated
import os
from dotenv import load_dotenv
import json
import tools

load_dotenv()
# 1. 新增：归约器函数，用于自动合并并行节点产生的数据
def merge_dicts(a: dict, b: dict) -> dict:
    if a is None: a = {}
    if b is None: b = {}
    res = a.copy()
    res.update(b)
    return res

# 新增：工具调用队列的归约器（支持并发添加工具，支持节点清空队列）
def merge_tool_calls(left: Optional[list], right: Optional[list]) -> list:
    if not left: left = []
    if not right: right = []
    # 如果 right 是一个空列表，说明这是由 tool_executor 发出的清空指令
    if right == []:
        return []
    # 否则，如果是多个并发节点发出的工具调用，将它们合并到一个列表中执行
    return left + right

# 修改：在 AgentState 中使用 Annotated 包装 tool_calls
class AgentState(TypedDict):
    user_input: str
    tool_calls: Annotated[list, merge_tool_calls] # 核心修改点
    is_approved: bool
    draft: Optional[str]
    feedback: Optional[str]
    context_data: Annotated[dict, merge_dicts]


def tool_executor_node(state: AgentState) -> dict:
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

    new_res = "\n".join(results)

    # 【核心修复】：将工具结果写入 context_data 池子，供后续大模型读取
    existing_log = state.get("context_data", {}).get("tool_logs", "")
    combined_log = existing_log + "\n\n" + new_res if existing_log else new_res

    return {
        "context_data": {"tool_logs": combined_log},  # 写入公共资料池
        "tool_calls": []  # 发出清空工具队列的指令
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

            # 【提取动态上下文】：让大模型只看动态池里的资料，避免被其他系统字段干扰
            context_pool = state.get("context_data", {})

            if actual_tools and not context_pool.get(output_key):
                current_llm = llm.bind_tools(actual_tools)
                prompt = f"{self.base_prompt}\n\n用户原始问题：{state.get('user_input')}\n\n当前可用资料池:\n{context_pool}\n\n请根据要求输出结果："
            else:
                prompt = f"{self.base_prompt}\n\n用户原始问题：{state.get('user_input')}\n\n当前可用资料池:\n{context_pool}\n\n⚠️工具已执行完毕。请直接输出总结，绝对不要再说多余的话！"

            response = current_llm.invoke(prompt)

            if response.tool_calls:
                return {"tool_calls": response.tool_calls}
            else:
                result_text = response.content.strip()

                # 【移除所有的 "tool_calls": []】
                if output_key in ["draft", "feedback"]:
                    return {output_key: result_text}
                else:
                    if self.tools_names:
                        existing = context_pool.get(output_key, "")
                        final_text = f"{existing}\n\n[Agent总结]: {result_text}" if existing else result_text
                    else:
                        final_text = result_text

                    return {"context_data": {output_key: final_text}}

        return node_func
