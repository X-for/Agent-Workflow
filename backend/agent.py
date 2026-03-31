import os
from typing import TypedDict, List
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, ToolMessage
from langchain.agents import create_agent
from langchain_core.messages import AIMessageChunk  # 引入类型判断，用于更精准的拦截
load_dotenv()


class Agent:
    def __init__(self, name: str, description: str, tools: List[str]):
        self.name = name
        self.description = description
        self.tools = tools
        deepseek_model = ChatOpenAI(
            model="deepseek-chat", 
            api_key=os.environ.get("DEEPSEEK_API_KEY"), 
            base_url="https://api.deepseek.com"
        )
        self.model = create_agent(deepseek_model, tools)
    
    def run_node(self, state: dict) -> dict:
        # 单一功能：负责与 LangGraph 的状态字典进行交互
        current_task = state.get("task", "")
        print(f"-> [{self.name}] 正在处理任务: {current_task}")
        
        # 1. 把你的系统设定和当前任务，组装成官方引擎认识的 input
        system_prompt = f"你是一个{self.name}。职责：{self.description}。"
        inputs = {"messages": [("system", system_prompt), ("user", current_task)]}
        
        final_text = ""
        print(f"\n-> [{self.name}] 思考与输出: ", end="", flush=True)
        
        # 核心修改：使用 stream 方法，并开启 messages 模式来捕获底层 token
        # 核心修改：使用 isinstance 来判断消息的真实身份
        for msg, metadata in self.model.stream(inputs, stream_mode="messages"):
            # 过滤判断：只要是大模型发出的片段 (AIMessageChunk)，并且包含实际文本，就打印
            if isinstance(msg, AIMessageChunk) and msg.content:
                print(msg.content, end="", flush=True)
                final_text += msg.content   
                
        print("\n")
        
        # 4. 规矩不变，返回给你自己的外层 LangGraph 需要更新的字典
        return {"current_draft": final_text}