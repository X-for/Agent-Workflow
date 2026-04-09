from langchain_openai import ChatOpenAI
from typing import TypedDict, Optional, Annotated
import os
from dotenv import load_dotenv
import json
import tools

load_dotenv()

# 1. 归约器：合并字典，用于并发写出
def merge_dicts(a: dict, b: dict) -> dict:
    if a is None: a = {}
    if b is None: b = {}
    res = a.copy()
    res.update(b)
    return res

# 2. 状态定义：tool_calls 改为字典
class AgentState(TypedDict):
    user_input: str
    tool_calls: Annotated[dict, merge_dicts] # 核心修改点：改用 dict 和 merge_dicts
    is_approved: bool
    draft: Optional[str]
    feedback: Optional[str]
    context_data: Annotated[dict, merge_dicts]

# 3. 专属工具节点工厂
def create_tool_node(agent_name: str):
    def tool_executor_node(state: AgentState) -> dict:
        # 只从字典里拿属于自己的工具请求
        tool_calls = state.get("tool_calls", {}).get(agent_name, [])
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

        existing_log = state.get("context_data", {}).get("tool_logs", "")
        combined_log = existing_log + "\n\n" + new_res if existing_log else new_res

        return {
            "context_data": {"tool_logs": combined_log},
            "tool_calls": {agent_name: []}  # 执行完后，只清空自己的队列
        }
    return tool_executor_node


def should_continue(state: AgentState) -> str:
    feedback_str = state.get("feedback", "")
    is_approved = False
    if feedback_str:
        try:
            clean_str = feedback_str
            if clean_str.startswith("```json"):
                clean_str = clean_str[7:-3].strip()
            elif clean_str.startswith("```"):
                clean_str = clean_str[3:-3].strip()
            result = json.loads(clean_str)
            is_approved = result.get("is_approved", False)
        except Exception:
            is_approved = False

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
            context_pool = state.get("context_data", {})

            if actual_tools and not context_pool.get(output_key):
                current_llm = llm.bind_tools(actual_tools)
                prompt = f"{self.base_prompt}\n\n用户原始问题：{state.get('user_input')}\n\n当前可用资料池:\n{context_pool}\n\n请根据要求输出结果："
            else:
                prompt = f"{self.base_prompt}\n\n用户原始问题：{state.get('user_input')}\n\n当前可用资料池:\n{context_pool}\n\n⚠️工具已执行完毕。请直接输出总结，绝对不要再说多余的话！"

            response = current_llm.invoke(prompt)

            if response.tool_calls:
                # 核心修复：工具请求打包装入以自己名字命名的字典
                return {"tool_calls": {self.name: response.tool_calls}}
            else:
                result_text = response.content.strip()

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