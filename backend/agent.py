import json
import os
from typing import TypedDict, List
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
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
        self.model_id = model_id
        
        # 读取配置
        config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "models.json")
        model_config = None
        if os.path.exists(config_path):
            with open(config_path, "r", encoding="utf-8") as f:
                models = json.load(f)
                model_config = next((m for m in models if m["id"] == model_id), None)
                
        if model_config and model_config["provider"] == "anthropic":
            llm = ChatAnthropic(
                model=model_config["id"], 
                api_key=os.environ.get(model_config["api_key_env"])
            )
        else:
            # 默认走 OpenAI 兼容格式 (DeepSeek, Qwen, GPT 都支持这种格式)
            api_key = os.environ.get(model_config["api_key_env"]) if model_config else os.environ.get("OPENAI_API_KEY")
            base_url = model_config["base_url"] if model_config else None
            
            llm = ChatOpenAI(
                model=model_id, 
                api_key=api_key, 
                base_url=base_url
            )
            
        self.model = create_agent(llm, tools)
    
    def run_node(self, state: dict, config: dict) -> dict:
        # 1. 组装 System Prompt
        system_prompt = f"你是一个{self.name}。职责：{self.description}。"
        
        # 2. 读取整个上下文消息（这就是为什么后面的 Agent 能知道前面的 Agent 说了啥）
        messages = state.get("messages", [])
        
        # 将系统提示词插在最前面传给大模型
        inputs = {"messages": [SystemMessage(content=system_prompt)] + messages}
        
        final_text = ""
        
        for msg, metadata in self.model.stream(inputs, config=config,  stream_mode="messages"):
            if isinstance(msg, AIMessageChunk) and msg.content:
                msg.name = self.name # 确保每个 chunk 都带上这个节点的名字，方便后续调试和记录
                final_text += msg.content   
        
        # 3. 核心改变：我们不再只是更新 current_draft，
        # 我们要把自己的回答作为一个 AIMessage 返回，这样它会自动被“追加”到下个节点的 state["messages"] 里！
        return_msg = AIMessage(content=final_text, name=self.name)
        
        return {
            "current_draft": final_text, 
            "messages": [return_msg] # 这里返回列表，LangGraph 底层会自动把它拼接到总记录里
        }