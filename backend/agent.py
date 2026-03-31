import os
from typing import TypedDict, List
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv
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
        if self.tools:
            self.model = deepseek_model.bind_tools(self.tools)
        else:
            self.model = deepseek_model


    def think(self, observation: str) -> str:
        prompt = f"你是一个{self.name}。职责：{self.description}。\n当前需求：{observation}\n请给出你的思考过程。"
        full_response = ""
        
        print(f"\n-> [{self.name}] 思考过程: ", end="", flush=True)
        
        # 【关键修正】：确保这里使用的是 .stream() 而不是 .invoke()
        for chunk in self.model.stream(prompt): 
            print(chunk.content, end="", flush=True)
            full_response += chunk.content
            
        print("\n")
        return full_response

    def act(self, thought: str) -> str:
        prompt = f"基于以下思考，直接输出最终的计划，不要废话：\n{thought}"
        
        # 1. 准备一个空字符串，用来在后台“攒”完整的回复
        full_response = ""
        
        print("\n-> [最终计划生成中]: ", end="", flush=True)
        
        # 2. 把原来的 invoke 换成 stream，开始循环接收
        for chunk in self.model.stream(prompt):
            # 实时把当前拿到的这个字打印到屏幕上 (打字机效果)
            print(chunk.content, end="", flush=True)
            # 同时把这个字追加存进我们的完整记录里
            full_response += chunk.content
            
        print("\n") # 打印完毕后换个行，保持终端整洁
        
        # 3. 规矩不变，把攒好的完整文本返回给 run_node，用于更新 state
        return full_response
    
    def run_node(self, state: dict) -> dict:
        # 单一功能：负责与 LangGraph 的状态字典进行交互
        current_task = state.get("task", "")
        print(f"-> [{self.name}] 正在处理任务: {current_task}")
        
        # 依次调用自己的内部方法
        thought_process = self.think(current_task)
        final_result = self.act(thought_process)
        
        # 按照接口规矩，返回需要更新的字典标签
        return {"current_draft": final_result}