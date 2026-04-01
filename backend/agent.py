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
    
    # 注意：参数必须要有 config
    def run_node(self, state: dict, config: dict) -> dict:
        current_task = state.get("task", "")
        draft = state.get("current_draft", "")
        
        print(f"-> [{self.name}] 正在处理任务: {current_task}")
        
        system_prompt = f"你是一个{self.name}。职责：{self.description}。"
        user_prompt = f"用户的原始任务是：{current_task}"
        if draft:
            user_prompt += f"\n\n=== 前面节点的处理结果 ===\n{draft}\n\n==================\n请基于上述结果继续你的处理工作。"
            
        inputs = {"messages": [SystemMessage(content=system_prompt), ("user", user_prompt)]}
        
        final_text = ""
        
        # 🌟 核心杀招：复制 config，并强行把当前 Agent 的名字塞进 metadata 里！
        # 这样底层大模型吐出的每一个流式字，都会被 LangChain 自动打上这个名字烙印！
        run_config = config.copy()
        run_config["metadata"] = {**run_config.get("metadata", {}), "MY_AGENT_NAME": self.name}
        
        # 🌟 把改过手脚的 run_config 传给大模型
        for msg, metadata in self.model.stream(inputs, config=run_config, stream_mode="messages"):
            if isinstance(msg, AIMessageChunk) and msg.content:
                final_text += msg.content   
        
        return_msg = AIMessage(content=final_text, name=self.name)
        
        return {
            "current_draft": final_text, 
            "messages": [return_msg]
        }