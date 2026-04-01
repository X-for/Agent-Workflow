import os
from typing import TypedDict, List
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from langchain.agents import create_agent
from langchain_core.messages import AIMessageChunk  # 引入类型判断，用于更精准的拦截
load_dotenv()


class Agent:
    def __init__(self, name: str, description: str, tools: List[str], model_id: str = "deepseek-chat"):
        self.name = name
        self.description = description
        self.tools = tools
        # === 动态选择大模型厂商和配置 ===
        api_key = ""
        base_url = ""
        
        if "gpt" in model_id:
            from langchain_openai import ChatOpenAI
            llm = ChatOpenAI(model=model_id, api_key=os.environ.get("OPENAI_API_KEY"))
            
        elif "claude" in model_id:
            from langchain_anthropic import ChatAnthropic
            llm = ChatAnthropic(model=model_id, api_key=os.environ.get("ANTHROPIC_API_KEY"))
            
        elif "glm" in model_id: # 智谱
            from langchain_openai import ChatOpenAI
            llm = ChatOpenAI(model=model_id, api_key=os.environ.get("ZHIPU_API_KEY"), base_url="https://open.bigmodel.cn/api/paas/v4/")
            
        else:
            # 默认兜底使用 DeepSeek
            from langchain_openai import ChatOpenAI
            llm = ChatOpenAI(
                model=model_id, # 这里可能是 deepseek-chat 或 deepseek-reasoner
                api_key=os.environ.get("DEEPSEEK_API_KEY"), 
                base_url="https://api.deepseek.com"
            )
            
        self.model = create_agent(llm, tools)
    
    def run_node(self, state: dict) -> dict:
        # 1. 组装 System Prompt
        system_prompt = f"你是一个{self.name}。职责：{self.description}。"
        
        # 2. 读取整个上下文消息（这就是为什么后面的 Agent 能知道前面的 Agent 说了啥）
        messages = state.get("messages", [])
        
        # 将系统提示词插在最前面传给大模型
        inputs = {"messages": [SystemMessage(content=system_prompt)] + messages}
        
        final_text = ""
        
        for msg, metadata in self.model.stream(inputs, stream_mode="messages"):
            if isinstance(msg, AIMessageChunk) and msg.content:
                final_text += msg.content   
        
        # 3. 核心改变：我们不再只是更新 current_draft，
        # 我们要把自己的回答作为一个 AIMessage 返回，这样它会自动被“追加”到下个节点的 state["messages"] 里！
        return_msg = AIMessage(content=final_text, name=self.name)
        
        return {
            "current_draft": final_text, 
            "messages": [return_msg] # 这里返回列表，LangGraph 底层会自动把它拼接到总记录里
        }