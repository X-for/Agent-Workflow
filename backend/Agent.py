import json
import os
from pathlib import Path
from typing import Any

from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage, ToolMessage
from dotenv import load_dotenv

load_dotenv()  # 加载环境变量




PROJECT_ROOT = Path(__file__).resolve().parent.parent
BASEDIR = Path(os.environ.get("BASE_DIR", PROJECT_ROOT)).resolve()
AGENT_CONFIG_DIR = Path(os.environ.get(
    "AGENT_CONFIG_DIR",
    os.environ.get("NODES_DIR", BASEDIR / "nodes"),
))
if not AGENT_CONFIG_DIR.is_absolute():
    AGENT_CONFIG_DIR = (BASEDIR / AGENT_CONFIG_DIR).resolve()
USER_NAME = os.environ.get("USER", "")

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
    def __init__(
        self,
        config_path: str | dict,
        tool_registry: dict = None,
        node_type: str = "AGENT",
        llm=None,
    ):
        super().__init__(node_type)
        if isinstance(config_path, str) and config_path.endswith('.json'):
            self.cfg = self._load_node_file(config_path)
        else:
            self.cfg = dict(config_path or {})
            ref = self.cfg.get("ref")
            if ref:
                template_cfg = self._load_node_file(ref)
                # 工作流内的配置具有更高优先级，允许安全地覆盖模板端口和模型参数。
                self.cfg = {**template_cfg, **self.cfg}
        self.name = self.cfg.get('name', 'AgentNode')

        # 数据流动端口
        self.input_ports = self.cfg.get('input_ports', [])
        self.output_ports = self.cfg.get('output_ports', [])

        # 核心配置
        self.model_name = self.cfg.get('model_name', 'deepseek-chat')
        self.system_prompt = self.cfg.get('system_prompt', '')
        self.tools_name = self.cfg.get('tools', [])
        
        # 智能匹配 API Key：
        # 如果 base_url 包含 openrouter，则使用 OPENROUTER_API_KEY
        # 如果 base_url 包含 openai，则使用 OPENAI_API_KEY
        # 否则默认尝试 DEEPSEEK_API_KEY
        base_url = self.cfg.get("base_url", "https://api.deepseek.com")
        if "openrouter" in base_url.lower():
            api_env_key = "OPENROUTER_API_KEY"
        elif "openai" in base_url.lower():
            api_env_key = "OPENAI_API_KEY"
        else:
            api_env_key = self.cfg.get("api", "DEEPSEEK_API_KEY")
            
        if llm is None:
            api_key = os.environ.get(api_env_key)
            if not api_key:
                print(f"警告: 节点 [{self.name}] 使用的 API Key ({api_env_key}) 未设置")
                # 保持服务可启动；真实请求会由服务商返回鉴权错误并进入节点失败路径。
                api_key = "dummy_key_please_set_environment_variable"
            llm_kwargs = {
                "model": self.model_name,
                "api_key": api_key,
                "base_url": base_url,
                "temperature": self.cfg.get("temperature", 0.1),
            }
            if self.cfg.get("max_tokens") is not None:
                llm_kwargs["max_tokens"] = self.cfg["max_tokens"]
            llm = ChatOpenAI(**llm_kwargs)

        self.tools_map = {}
        actual_tools = []
        if tool_registry and self.tools_name:
            for t_name in self.tools_name:
                if t_name in tool_registry:
                    tool_obj = tool_registry[t_name]
                    actual_tools.append(tool_obj)
                    self.tools_map[tool_obj.name] = tool_obj
        
        print(f"[{self.name}] 实际挂载的工具列表: {list(self.tools_map.keys())}")
        
        if actual_tools and hasattr(llm, "bind_tools"):
            self.llm = llm.bind_tools(actual_tools)
        else:
            self.llm = llm

    def _load_node_file(self, file_path: str) -> dict:
        """从独立保存的文件中读取节点配置"""
        target = Path(file_path)
        if not target.is_absolute():
            target = (AGENT_CONFIG_DIR / target).resolve()
        try:
            target.relative_to(AGENT_CONFIG_DIR.resolve())
        except ValueError as exc:
            raise ValueError(f"节点模板路径越出配置目录: {file_path}") from exc
        if not target.exists():
            raise FileNotFoundError(f"找不到独立的节点配置文件: {target}")
        with target.open('r', encoding='utf-8') as f:
            return json.load(f)

    @staticmethod
    def _content_to_text(content: Any) -> str:
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            parts = []
            for item in content:
                if isinstance(item, str):
                    parts.append(item)
                elif isinstance(item, dict) and isinstance(item.get("text"), str):
                    parts.append(item["text"])
            return "\n".join(parts)
        if content is None:
            return ""
        return str(content)

    def _parse_deliveries(self, final_answer: str) -> tuple[list[dict], str]:
        stripped = final_answer.strip()
        if stripped.startswith("```json") and stripped.endswith("```"):
            stripped = stripped[7:-3].strip()
        elif stripped.startswith("```") and stripped.endswith("```"):
            stripped = stripped[3:-3].strip()

        decision = json.loads(stripped)
        if not isinstance(decision, dict):
            raise ValueError("路由结果必须是 JSON 对象")
        deliveries = decision.get("deliveries")
        if not isinstance(deliveries, list):
            raise ValueError("路由结果缺少 deliveries 数组")

        allowed_ports = {port.get("id") for port in self.output_ports if port.get("id")}
        outputs = []
        for delivery in deliveries:
            if not isinstance(delivery, dict):
                raise ValueError("deliveries 中的元素必须是对象")
            target_port = delivery.get("target_port")
            if target_port not in allowed_ports:
                outputs.append({
                    "port_id": target_port,
                    "port_status": "fallback",
                    "payload": delivery.get("payload", ""),
                    "ui_show": False,
                    "fallback_to_end": True,
                    "fallback_reason": f"模型选择了未声明的输出端口: {target_port}",
                })
                continue
            outputs.append({
                "port_id": target_port,
                "port_status": "success",
                "payload": delivery.get("payload", ""),
                "ui_show": False,
            })
        console_message = str(decision.get("console_msg", f"[{self.name}] 任务执行完毕"))
        return outputs, console_message

    async def node_func(self, state: dict) -> dict:
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

        routing_instruction = f"""
        \n\n=========================
        {("用户名字是" + USER_NAME)  if USER_NAME else ""}
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
        
        # 注入历史记忆 (Memory)
        history = state.get("history", [])
        messages = [SystemMessage(content=self.system_prompt + routing_instruction)]
        
        # 将历史记录转换为 LangChain 消息格式
        from langchain_core.messages import AIMessage
        for msg in history:
            if msg["role"] == "user":
                messages.append(HumanMessage(content=msg["content"]))
            elif msg["role"] == "assistant":
                # 简单处理，不包含工具调用历史，仅包含最终文本
                messages.append(AIMessage(content=msg.get("content", "")))

        # 添加当前任务输入
        messages.append(HumanMessage(content=f"请根据以下输入执行任务：\n{combined_input}"))

        # --- 步骤 3：内部微型 Agent Loop (自主调用工具并收集结果) ---
        max_iterations = int(self.cfg.get("max_tool_iterations", 10))
        final_response = None

        for _ in range(max_iterations):
            response = await self.llm.ainvoke(messages)
            messages.append(response)

            tool_calls = getattr(response, "tool_calls", None) or []
            if not tool_calls:
                final_response = response
                break

            for tool_call in tool_calls:
                tool_name = tool_call["name"]
                tool_args = tool_call["args"]
                tool_id = tool_call["id"]

                print(f"[{self.name}] 决定调用工具: {tool_name}，参数: {tool_args}")

                if tool_name in self.tools_map:
                    try:
                        print(f"[{self.name}] 正在执行工具: {tool_name} ...")
                        # 如果工具支持异步则调用 ainvoke，否则调用 invoke
                        tool_obj = self.tools_map[tool_name]
                        if hasattr(tool_obj, "ainvoke"):
                            try:
                                tool_result = await tool_obj.ainvoke(tool_args)
                            except NotImplementedError:
                                tool_result = tool_obj.invoke(tool_args)
                        else:
                            tool_result = tool_obj.invoke(tool_args)
                        print(f"[{self.name}] 工具 {tool_name} 执行成功！")
                    except Exception as e:
                        tool_result = f"工具执行异常: {str(e)}"
                        print(f"[{self.name}] 工具 {tool_name} 执行失败: {str(e)}")
                else:
                    tool_result = f"错误: 节点未装备名为 {tool_name} 的工具"
                    print(f"[{self.name}] 工具调用失败: 未找到名为 {tool_name} 的工具。当前可用工具: {list(self.tools_map.keys())}")

                # 将工具执行结果作为 ToolMessage 塞回历史记录，供大模型下一步判断
                messages.append(ToolMessage(content=str(tool_result), tool_call_id=tool_id))

        if final_response is None:
            raise RuntimeError(
                f"节点在 {max_iterations} 轮工具调用后仍未生成最终答案，已停止执行"
            )

        # --- 步骤 4：解析多端口分发列表，并封装为标准协议 ---
        final_answer = self._content_to_text(final_response.content)
        outputs_list = []
        console_message = f"[{self.name}] 任务执行完毕"
        
        try:
            outputs_list, console_message = self._parse_deliveries(final_answer)
            console_message = f"[{self.name}]: {console_message}"
        except (json.JSONDecodeError, TypeError, ValueError) as exc:
            print(f"[{self.name}] 警告：路由结果无效（{exc}），降级投递到 END 节点。")
            outputs_list.append({
                "port_id": None,
                "port_status": "fallback",
                "payload": final_answer,
                "ui_show": False,
                "fallback_to_end": True,
                "fallback_reason": f"路由结果无效: {exc}",
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
        target = (AGENT_CONFIG_DIR / file_path).resolve()
        try:
            target.relative_to(AGENT_CONFIG_DIR.resolve())
        except ValueError as exc:
            raise ValueError(f"节点模板路径越出配置目录: {file_path}") from exc
        if not target.exists():
            raise FileNotFoundError(f"找不到独立的节点配置文件: {target}")
        with target.open('r', encoding='utf-8') as f:
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
        target = (AGENT_CONFIG_DIR / file_path).resolve()
        try:
            target.relative_to(AGENT_CONFIG_DIR.resolve())
        except ValueError as exc:
            raise ValueError(f"节点模板路径越出配置目录: {file_path}") from exc
        if not target.exists():
            raise FileNotFoundError(f"找不到独立的节点配置文件: {target}")
        with target.open('r', encoding='utf-8') as f:
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
        
        # 兼容处理：可能被存放在 f"{self.name}:{in_port_id}"，也可能是在配置覆盖时的其他名字
        final_result = state.get(final_result_key)
        
        # 遍历 state 寻找可能投递给这个 End 节点的任何输入数据
        if final_result is None:
            for key, val in state.items():
                if key.startswith(f"{self.name}:") and key != f"{self.name}:system_message":
                    final_result = val
                    break
        
        if final_result is None:
            final_result = "无结果"
        
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
