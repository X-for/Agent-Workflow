from langchain_openai import ChatOpenAI
from typing import TypedDict, Optional
import os
from dotenv import load_dotenv
load_dotenv()

# 1. 定义共享状态 (State)
class AgentState(TypedDict):
    user_input: str
    parsed_query: Optional[str]
    search_results: Optional[str]
    draft: Optional[str]
    feedback: Optional[str]
    is_approved: bool

# 假设您已经初始化好了 llm 实例
# llm = ... 
llm = ChatOpenAI(
    model="deepseek-chat", 
    api_key=os.environ.get("DEEPSEEK_API_KEY"), 
    base_url="https://api.deepseek.com/v1",  # 必须显式指定 DeepSeek 的 API 地址
)

# 2. 解析智能体 (Parser Node)
def parser_node(state: AgentState) -> dict:
    """负责将用户的输入转化为具体的搜索词"""
    user_input = state["user_input"]
    
    # 构造简单的 Prompt 提取搜索词
    prompt = f"请从以下用户输入中提取出最核心的搜索关键词，不要输出任何其他废话：\n{user_input}"
    
    # 调用大模型 (具体调用方式根据您使用的 llm 实例而定，这里使用伪代码展示逻辑)
    response = llm.invoke(prompt)
    parsed_query = response.content.strip()
    
    # 只返回需要更新到 State 中的字段
    return {"parsed_query": parsed_query}

# 3. 搜索智能体 (Search Node)
def search_node(state: AgentState) -> dict:
    import tools
    """负责调用 tools.py 中的搜索工具"""
    query = state.get("parsed_query")
    
    if not query:
        return {"search_results": "无搜索词，跳过搜索。"}
        
    # 调用外部工具
    results = tools.web_search.invoke(query)
    
    return {"search_results": results}

import json

# 4. 生成智能体 (Generator Node)
def generator_node(state: AgentState) -> dict:
    """负责结合检索结果和用户输入生成回答；若有审核意见则进行修改"""
    user_input = state["user_input"]
    search_results = state.get("search_results", "")
    feedback = state.get("feedback", "")
    
    # 动态构建 Prompt：如果有 feedback，说明是被审核员打回的重写过程
    prompt = f"用户问题：{user_input}\n\n参考资料：{search_results}\n\n"
    if feedback and state.get("draft"):
        prompt += f"你之前的回答被审核打回，审核意见如下：{feedback}\n请根据审核意见修改你的回答。\n\n"
    else:
        prompt += "请根据参考资料，生成专业、准确的回答。\n\n"
        
    response = llm.invoke(prompt)
    draft = response.content.strip()
    
    return {"draft": draft}

# 5. 审核智能体 (Reviewer Node)
def reviewer_node(state: AgentState) -> dict:
    """负责审核生成的初稿，并严格输出 JSON 格式以控制流程走向"""
    user_input = state["user_input"]
    draft = state["draft"]
    
    prompt = f"""
    你是一个严苛的质量审核员。请判断下方的回答是否完美解答了用户的问题。
    用户问题: {user_input}
    待审核回答: {draft}

    请严格以 JSON 格式返回结果，不要输出任何 markdown 标记或其他说明文字。包含以下两个字段：
    {{
        "is_approved": true或false (如果准确无误、结构清晰则为true，否则为false),
        "feedback": "如果为false，请给出明确的修改指导；如果为true，直接输出'无'"
    }}
    """
    
    response = llm.invoke(prompt)
    raw_content = response.content.strip()
    
    # 移除大模型可能自带的 ```json ``` 标记
    if raw_content.startswith("```json"):
        raw_content = raw_content[7:-3].strip()
    elif raw_content.startswith("```"):
        raw_content = raw_content[3:-3].strip()
        
    try:
        result = json.loads(raw_content)
        return {
            "is_approved": result.get("is_approved", False),
            "feedback": result.get("feedback", "")
        }
    except json.JSONDecodeError:
        # 如果模型输出格式错误，强制打回重写
        return {
            "is_approved": False,
            "feedback": "审核员格式输出异常，请重新审视问题并生成更加规范的回答。"
        }