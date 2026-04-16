import json
import os
from Agent import AgentNode, StartNode, EndNode

from dotenv import load_dotenv

# 加载 .env 文件中的环境变量
load_dotenv()

class GraphEngine:
    """
    从配置文件加载图结构, 创建所有的agent实例
    基于端口的路由投递消息
    """
    def __init__(self, workflow_config: dict | str, tool_registry: dict = None):
        # 允许直接传入 json 文件路径
        if isinstance(workflow_config, str) and workflow_config.endswith('.json'):
            if not os.path.exists(workflow_config):
                raise FileNotFoundError(f"找不到工作流配置文件: {workflow_config}")
            with open(workflow_config, 'r', encoding='utf-8') as f:
                workflow_schema = json.load(f)
        else:
            workflow_schema = workflow_config

        self.workflows_id = workflow_schema.get("workflows_id", "default_workflow")
        self.nodes_config = workflow_schema.get("nodes", [])
        self.connections = workflow_schema.get("connections", [])
        
        # 优先使用传入的 tool_registry，如果没有则尝试从配置中读取
        self.tools_registry = tool_registry if tool_registry is not None else workflow_schema.get("tools_registry", {})

        self.routing_table = self._build_routing_table()

        self.agent_instances = self._init_agents()



    def _build_routing_table(self):
        table = {}

        for conn in self.connections:
            src_key = (conn["source_node"], conn["source_port"])
            if src_key not in table:
                table[src_key] = []
            
            table[src_key].append((conn["target_node"], conn["target_port"]))
        return table
    
    def _init_agents(self) -> dict:
        instances = {}
        for node_cfg in self.nodes_config:
            node_id = node_cfg.get("id")
            node_type = node_cfg.get("type", "AGENT")  # 默认为AGENT类型
            
            if "ref" in node_cfg:
                # 通过引用路径加载独立的节点配置文件
                config_target = node_cfg["ref"]
            else:
                # 直接使用内嵌的配置
                config_target = node_cfg
            
            # 根据节点类型创建不同的实例
            if node_type.upper() == "START":
                node_instance = StartNode(config_target)
            elif node_type.upper() == "END":
                node_instance = EndNode(config_target)
            elif node_type.upper() == "AGENT":
                node_instance = AgentNode(config_target, tool_registry=self.tools_registry)
            else:
                # 默认为AgentNode
                node_instance = AgentNode(config_target, tool_registry=self.tools_registry)
            
            node_instance.name = node_id
            instances[node_id] = node_instance
            print(f"[GraphEngine] 成功加载并实例化节点: {node_id} (类型: {node_type})")
        return instances


    def send_message(self, agent_output: dict, global_state: dict):
        current_node = agent_output.get("node_name")
        status = agent_output.get("status")
        outputs = agent_output.get("outputs", [])

        if status == "fail":
            print(f"[{current_node}] 执行失败，消息将不会被路由。")
            return global_state, ["error_handler_node"]
        next_nodes_to_run = set()

        for out in outputs:
            port_id = out.get("port_id")
            payload = out.get("payload")
            ui_show = out.get("ui_show", False)
            
            if ui_show:
                self._send_to_frontend(payload)

            src_key = (current_node, port_id)
            if src_key in self.routing_table:
                targets = self.routing_table[src_key]
                for target_node, target_port in targets:
                    print(f"[routing] 投递成功: {current_node}:{port_id} -> {target_node}:{target_port}")
                    
                    box_key = f"{target_node}:{target_port}"
                    global_state[box_key] = payload
                    next_nodes_to_run.add(target_node)
            else:
                if not ui_show and port_id != "console_out":  # 避免前端展示端口的警告
                    print(f"[routing] 警告: 没有找到路由规则 {current_node}:{port_id}，消息未被投递。")
                    global_state[f"{current_node}:{port_id}"] = payload

        return global_state, list(next_nodes_to_run)
    
    def _send_to_frontend(self, message):
        # 这里可以实现一个消息队列或者WebSocket连接，将消息发送到前端
        print(f"[frontend] {message}")

    async def run(self, start_node_id: str, start_port_id: str, initial_data: any, history: list = None):
        """
        启动工作流
        """
        print(f"[GraphEngine] 启动工作流...")
        global_state = {
            "history": history or []
        }

        initial_box_key = f"{start_node_id}:{start_port_id}"
        global_state[initial_box_key] = initial_data

        active_queue = [start_node_id]
        step = 0
        
        import asyncio
        import inspect

        while active_queue:
            step += 1
            if step > 50:
                print("[GraphEngine] 警告: 迭代次数过多，可能存在循环依赖，已强制停止。")
                break
                
            # 取出当前层级所有的节点进行并发执行
            current_batch = active_queue[:]
            active_queue.clear()
            
            print(f"\n[GraphEngine] 第 {step} 层级并发执行节点: {current_batch}")
            
            async def process_node(current_node_id):
                if current_node_id not in self.agent_instances:
                    print(f"[GraphEngine] 错误: 未找到节点实例 {current_node_id}，跳过执行。")
                    return None
                    
                print(f"[GraphEngine] 开始执行节点: {current_node_id}")
                agent = self.agent_instances[current_node_id]
                
                # 兼容：如果 node_func 是异步的就 await
                if inspect.iscoroutinefunction(agent.node_func):
                    agent_result = await agent.node_func(global_state)
                else:
                    agent_result = agent.node_func(global_state)
                    
                # 防止旧版 Agent 返回格式不兼容
                if "latest_node_output" in agent_result:
                    agent_output_json = agent_result["latest_node_output"]
                else:
                    agent_output_json = agent_result
                    
                return agent_output_json

            # 并发执行当前批次的所有节点任务
            batch_results = await asyncio.gather(*(process_node(node_id) for node_id in current_batch))
            
            # 收集当前批次执行后产生的所有下一步节点
            next_nodes_to_run = set()
            for agent_output_json in batch_results:
                if not agent_output_json:
                    continue
                # 更新全局状态并获取下一跳节点
                global_state, next_nodes = self.send_message(agent_output_json, global_state)
                for node in next_nodes:
                    next_nodes_to_run.add(node)

            # 将下一批收到信的节点加入激活队列
            for node in next_nodes_to_run:
                if node not in active_queue:
                    active_queue.append(node)
                    
        print(f"\n[GraphEngine] 工作流执行结束，所有节点均已休眠。")
        return global_state
    


