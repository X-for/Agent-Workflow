import json
import os

from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage, ToolMessage
from pydantic import SecretStr
from dotenv import load_dotenv

load_dotenv()  # 加载环境变量




AGENT_CONFIG_DIR = os.environ.get("AGENT_CONFIG_DIR", "./nodes")
BASEDIR = os.environ.get("BASE_DIR", ".")


class Node:
    """
    所有节点类型的基类
    """
    def __init__(self, node_type: str = "BASE"):
        self.type = node_type
        self.name = f"Node_{node_type}"

    def node_func(self, state: dict) -> dict:
        """
        执行节点的主要功能
        :param state: 当前工作流的状态
        :return: 更新后的状态
        """
        raise NotImplementedError("子类必须实现 node_func 方法")

class AgentNode(Node):
    def __init__(self, config_path: str | dict, tool_registry: dict = None, node_type: str = "AGENT"):
        super().__init__(node_type)
        if isinstance(config_path, str) and config_path.endswith('.json'):
            self.cfg = self._load_node_file(config_path)
        else:
            self.cfg = config_path
        self.name = self.cfg.get('name', 'AgentNode')

        # 数据流动端口
        self.input_ports = self.cfg.get('input_ports', [])
        self.output_ports = self.cfg.get('output_ports', [])

        # 核心配置
        self.model_name = self.cfg.get('model_name', 'chat-deepseek')
        self.system_prompt = self.cfg.get('system_prompt', '')
        self.tools_name = self.cfg.get('tools', [])
        api = self.cfg.get("api", "DEEPSEEK_API_KEY")

        # 初始化llm
        # 1. 初始化 LLM
        llm = ChatOpenAI(
            model=self.model_name,
            api_key=os.environ.get(api),
            base_url=self.cfg.get("base_url", "https://api.deepseek.com"),
            temperature=self.cfg.get("temperature", 0.1)
        )

        self.tools_map = {}
        actual_tools = []
        if tool_registry and self.tools_name:
            for t_name in self.tools_name:
                if t_name in tool_registry:
                    tool_obj = tool_registry[t_name]
                    actual_tools.append(tool_obj)
                    self.tools_map[tool_obj.name] = tool_obj
        
        print(f"[{self.name}] 实际挂载的工具列表: {list(self.tools_map.keys())}")
        
        if actual_tools:
            self.llm = llm.bind_tools(actual_tools)
        else:
            self.llm = llm

    def _load_node_file(self, file_path: str) -> dict:
        """从独立保存的文件中读取节点配置"""
        file_path = os.path.join(BASEDIR, AGENT_CONFIG_DIR, file_path)
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"找不到独立的节点配置文件: {file_path}")
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)

    def node_func(self, state: dict) -> dict:
        """
        核心执行逻辑（包含内部工具闭环）
        """
        # --- 步骤 1：从外部 State 中精准提取本节点 Input Ports 需要的数据 ---
        inputs_context = []
        for port in self.input_ports:
            port_id = port.get("id")
            port_name = port.get("name", port_id)

            box_key = f"{self.name}:{port_id}"

            if box_key in state:
                inputs_context.append(f"【输入端点 - {port_name}】:\n{state[box_key]}")

        combined_input = "\n\n".join(inputs_context) if inputs_context else "无外部输入"
        print(f"[{self.name}] 收集到的输入上下文:\n{combined_input}\n---")

        # --- 步骤 2：组装初始对话消息 ---
        # 提取当前节点所有可用的输出端口信息
        port_options_str = ""
        for p in self.output_ports:
            p_id = p.get("id", "unknown")
            p_desc = p.get("description", "未提供描述")
            port_options_str += f"- 【{p_id}】: {p_desc}\n"

        # ✨【核心修复】：将 target_port 改为 deliveries 数组
        routing_instruction = f"""
        \n\n=========================
        【最终交付协议】（极其重要）
        当你完成当前节点任务时，你可以自主决定将数据分发到一个或【多个】合适的端口。
        当前你可用的输出端口有：
        {port_options_str}
        
        请务必以如下严格的 JSON 格式作为你的最后一次回复（不要包含多余文本）：
        ```json
        {{
            "deliveries": [
                {{
                    "target_port": "选择的可用端口1",
                    "payload": "投递给该端口的具体数据内容"
                }},
                {{
                    "target_port": "选择的可用端口2(如果有需要同时分发)",
                    "payload": "投递给该端口的具体数据内容"
                }}
            ],
            "console_msg": "用一句简短的话总结你的工作，这将展示给用户控制台"
        }}
        ```
        """
        
        messages = [
            SystemMessage(content=self.system_prompt + routing_instruction),
            HumanMessage(content=f"请根据以下输入执行任务：\n{combined_input}")
        ]

        # --- 步骤 3：内部微型 Agent Loop (自主调用工具并收集结果) ---
        max_iterations = 10  # 防止大模型内部死循环的物理限制
        iteration = 0

        while iteration < max_iterations:
            iteration += 1
            response = self.llm.invoke(messages)
            messages.append(response)

            # 如果大模型没有要求调用工具，说明它已经得出了最终结论，退出内循环！
            if not response.tool_calls:
                break

            # 执行大模型请求的工具
            for tool_call in response.tool_calls:
                tool_name = tool_call["name"]
                tool_args = tool_call["args"]
                tool_id = tool_call["id"]

                print(f"[{self.name}] 决定调用工具: {tool_name}，参数: {tool_args}")

                if tool_name in self.tools_map:
                    try:
                        print(f"[{self.name}] 正在执行工具: {tool_name} ...")
                        tool_result = self.tools_map[tool_name].invoke(tool_args)
                        print(f"[{self.name}] 工具 {tool_name} 执行成功！")
                    except Exception as e:
                        tool_result = f"工具执行异常: {str(e)}"
                        print(f"[{self.name}] 工具 {tool_name} 执行失败: {str(e)}")
                else:
                    tool_result = f"错误: 节点未装备名为 {tool_name} 的工具"
                    print(f"[{self.name}] 工具调用失败: 未找到名为 {tool_name} 的工具。当前可用工具: {list(self.tools_map.keys())}")

                # 将工具执行结果作为 ToolMessage 塞回历史记录，供大模型下一步判断
                messages.append(ToolMessage(content=str(tool_result), tool_call_id=tool_id))

        # --- 步骤 4：解析多端口分发列表，并封装为标准协议 ---
        final_answer = response.content
        outputs_list = []
        console_message = f"[{self.name}] 任务执行完毕"
        
        try:
            clean_json_str = final_answer.replace("```json", "").replace("```", "").strip()
            decision = json.loads(clean_json_str)
            
            #【核心修复】：遍历解析 deliveries 数组，实现多路并发分发
            if "deliveries" in decision and isinstance(decision["deliveries"], list):
                for delivery in decision["deliveries"]:
                    outputs_list.append({
                        "port_id": delivery.get("target_port", "default_out"),
                        "port_status": "success",
                        "payload": delivery.get("payload", ""),
                        "ui_show": False
                    })
                    
            if "console_msg" in decision:
                console_message = f"[{self.name}]: {decision['console_msg']}"
                
        except json.JSONDecodeError:
            print(f"[{self.name}] 警告：未输出规范的路由 JSON，触发降级默认投递。")
            default_port = self.output_ports[0]["id"] if self.output_ports else "default_out"
            outputs_list.append({
                "port_id": default_port,
                "port_status": "success",
                "payload": final_answer,
                "ui_show": False
            })
            console_message = f"[{self.name}]: {final_answer[:50]}..."

        # 强制追加前端 UI 的展示端口
        outputs_list.append({
            "port_id": "console_out",
            "port_status": "success",
            "payload": console_message,
            "ui_show": True
        })

        workflow_id = state.get("workflow_id", "default_workflow")
        session_id = state.get("session_id", "default_session")

        agent_output = {
            "workflow_id": workflow_id,
            "session_id": session_id,
            "node_name": self.name,
            "status": "success", 
            "message": "Node execution completed.",
            "outputs": outputs_list  # ✨ 将解析出来的多路输出数组直接赋值
        }
        
        return {
            "latest_node_output": agent_output
        }
    
class StartNode(Node):
    def __init__(self, config_path: str | dict = None):
        super().__init__("START")
        # Start节点的配置
        if isinstance(config_path, str) and config_path.endswith('.json'):
            self.cfg = self._load_node_file(config_path)
        else:
            self.cfg = config_path or {}
        
        # 重写name属性以使用特定名称
        self.name = "StartNode"
        
        # 数据流动端口
        self.input_ports = self.cfg.get('input_ports', [{"id": "user_input", "name": "用户输入", "description": "接收用户的原始输入"}])
        self.output_ports = self.cfg.get('output_ports', [{"id": "out_query", "name": "查询输出", "description": "输出标准化的查询"}])

    def _load_node_file(self, file_path: str) -> dict:
        """从独立保存的文件中读取节点配置"""
        file_path = os.path.join(BASEDIR, AGENT_CONFIG_DIR, file_path)
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"找不到独立的节点配置文件: {file_path}")
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)

    def node_func(self, state: dict) -> dict:
        """
        Start节点功能：将用户输入打包成项目标准的数据流转结构
        """
        # 从配置中动态获取输入和输出端口的ID
        in_port_id = self.input_ports[0]["id"] if self.input_ports else "user_input"
        out_port_id = self.output_ports[0]["id"] if self.output_ports else "out_query"

        # 从state中获取用户输入
        user_input_key = f"{self.name}:{in_port_id}"
        # run.py 是将数据放入 f"{start_node_id}:{start_port_id}" 的，例如 "start_node:out_query"
        user_query_key = f"{self.name}:{out_port_id}"
        
        # 兼容多种可能的数据存放位置
        user_input = state.get(user_input_key, state.get(user_query_key, state.get("user_input", "无输入")))
        
        # 创建标准化的输出结构
        standardized_data = {
            "original_input": user_input,
            "processed_at": self.name,
            "format_version": "1.0"
        }
        
        # 构建输出
        outputs_list = [{
            "port_id": out_port_id,
            "port_status": "success",
            "payload": json.dumps(standardized_data, ensure_ascii=False),
            "ui_show": False
        }]
        
        # 添加UI显示信息
        outputs_list.append({
            "port_id": "console_out",
            "port_status": "success",
            "payload": f"[{self.name}]: 已将用户输入标准化",
            "ui_show": True
        })

        workflow_id = state.get("workflow_id", "default_workflow")
        session_id = state.get("session_id", "default_session")

        node_output = {
            "workflow_id": workflow_id,
            "session_id": session_id,
            "node_name": self.name,
            "status": "success",
            "message": "Start node processed user input.",
            "outputs": outputs_list
        }
        
        return {
            "latest_node_output": node_output
        }


class EndNode(Node):
    def __init__(self, config_path: str | dict = None):
        super().__init__("END")
        # End节点的配置
        if isinstance(config_path, str) and config_path.endswith('.json'):
            self.cfg = self._load_node_file(config_path)
        else:
            self.cfg = config_path or {}
        
        # 重写name属性以使用特定名称
        self.name = "EndNode"
        
        # 数据流动端口
        self.input_ports = self.cfg.get('input_ports', [{"id": "final_result", "name": "最终结果", "description": "接收最后的处理结果"}])
        self.output_ports = self.cfg.get('output_ports', [{"id": "text_output", "name": "文本输出", "description": "解析后的文本输出"}])

    def _load_node_file(self, file_path: str) -> dict:
        """从独立保存的文件中读取节点配置"""
        file_path = os.path.join(BASEDIR, AGENT_CONFIG_DIR, file_path)
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"找不到独立的节点配置文件: {file_path}")
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)

    def node_func(self, state: dict) -> dict:
        """
        End节点功能：将最后一个agent节点输出解析成文本
        """
        # 从配置中动态获取输入和输出端口的ID
        in_port_id = self.input_ports[0]["id"] if self.input_ports else "final_result"
        out_port_id = self.output_ports[0]["id"] if self.output_ports else "text_output"

        # 从state中获取最终结果
        final_result_key = f"{self.name}:{in_port_id}"
        final_result = state.get(final_result_key, state.get("final_result", "无结果"))
        
        # 解析结果并转换为文本
        parsed_text = self._parse_to_text(final_result)
        
        # 构建输出
        outputs_list = [{
            "port_id": out_port_id,
            "port_status": "success",
            "payload": parsed_text,
            "ui_show": False
        }]
        
        # 添加UI显示信息
        outputs_list.append({
            "port_id": "console_out",
            "port_status": "success",
            "payload": f"[{self.name}]: 已将最终结果解析为文本",
            "ui_show": True
        })

        workflow_id = state.get("workflow_id", "default_workflow")
        session_id = state.get("session_id", "default_session")

        node_output = {
            "workflow_id": workflow_id,
            "session_id": session_id,
            "node_name": self.name,
            "status": "success",
            "message": "End node processed final result.",
            "outputs": outputs_list
        }
        
        return {
            "latest_node_output": node_output
        }
    
    def _parse_to_text(self, result):
        """
        将最终结果解析为文本
        """
        if isinstance(result, str):
            return result
        elif isinstance(result, dict):
            # 如果是字典，尝试提取关键信息
            if 'payload' in result:
                return str(result['payload'])
            elif 'content' in result:
                return str(result['content'])
            else:
                return json.dumps(result, ensure_ascii=False, indent=2)
        elif isinstance(result, list):
            # 如果是列表，连接所有元素
            return "\n".join([str(item) for item in result])
        else:
            return str(result)


class SystemNode:
    def __init__(self, type="START"):
        self.name = f"SystemNode_{type}"
        self.type =  type

    def node_func(self, state: dict) -> dict:
        # 直接在全局状态里放一个标记，告诉后续节点这是一个系统节点的输出
        state[f"{self.name}:system_message"] = f"这是一个系统节点，类型为 {self.type}"
        return {
            "latest_node_output": {
                "node_name": self.name,
                "status": "success",
                "message": f"System node of type {self.type} executed.",
                "outputs": []
            }
        }

    