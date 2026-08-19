import asyncio
import inspect
import json
import os
from collections import defaultdict
from typing import Any

from dotenv import load_dotenv

from Agent import AgentNode, EndNode, StartNode


load_dotenv()


class WorkflowValidationError(ValueError):
    """工作流结构无效。"""


class WorkflowExecutionError(RuntimeError):
    """工作流没有成功产生最终结果。"""


def validate_workflow_schema(workflow_schema: dict) -> None:
    """执行不依赖模型或节点模板的基础结构校验。"""
    if not isinstance(workflow_schema, dict):
        raise WorkflowValidationError("工作流配置必须是 JSON 对象")

    nodes = workflow_schema.get("nodes")
    connections = workflow_schema.get("connections")
    if not isinstance(nodes, list) or not nodes:
        raise WorkflowValidationError("工作流至少需要一个节点")
    if not isinstance(connections, list):
        raise WorkflowValidationError("connections 必须是数组")

    node_ids = []
    node_types = {}
    for index, node in enumerate(nodes):
        if not isinstance(node, dict):
            raise WorkflowValidationError(f"第 {index + 1} 个节点必须是对象")
        node_id = node.get("id")
        if not isinstance(node_id, str) or not node_id.strip():
            raise WorkflowValidationError(f"第 {index + 1} 个节点缺少有效 id")
        if node_id in node_types:
            raise WorkflowValidationError(f"节点 id 重复: {node_id}")
        node_ids.append(node_id)
        node_types[node_id] = str(node.get("type", "AGENT")).upper()

    starts = [node_id for node_id, node_type in node_types.items() if node_type == "START"]
    ends = [node_id for node_id, node_type in node_types.items() if node_type == "END"]
    if len(starts) != 1:
        raise WorkflowValidationError(f"工作流必须且只能包含一个 START 节点，当前为 {len(starts)} 个")
    if len(ends) != 1:
        raise WorkflowValidationError(f"工作流必须且只能包含一个 END 节点，当前为 {len(ends)} 个")

    adjacency = {node_id: set() for node_id in node_ids}
    seen_edges = set()
    for index, connection in enumerate(connections):
        if not isinstance(connection, dict):
            raise WorkflowValidationError(f"第 {index + 1} 条连接必须是对象")
        source = connection.get("source_node")
        target = connection.get("target_node")
        source_port = connection.get("source_port")
        target_port = connection.get("target_port")
        if source not in node_types:
            raise WorkflowValidationError(f"连接引用了不存在的源节点: {source}")
        if target not in node_types:
            raise WorkflowValidationError(f"连接引用了不存在的目标节点: {target}")
        if not isinstance(source_port, str) or not source_port:
            raise WorkflowValidationError(f"连接 {source} -> {target} 缺少源端口")
        if not isinstance(target_port, str) or not target_port:
            raise WorkflowValidationError(f"连接 {source} -> {target} 缺少目标端口")
        if target == starts[0]:
            raise WorkflowValidationError("START 节点不能有入边")
        if source == ends[0]:
            raise WorkflowValidationError("END 节点不能有出边")
        edge_key = (source, source_port, target, target_port)
        if edge_key in seen_edges:
            raise WorkflowValidationError(
                f"连接重复: {source}:{source_port} -> {target}:{target_port}"
            )
        seen_edges.add(edge_key)
        adjacency[source].add(target)

    # Kahn 拓扑校验：执行器的就绪/跳过语义以 DAG 为前提。
    indegree = {node_id: 0 for node_id in node_ids}
    for targets in adjacency.values():
        for target in targets:
            indegree[target] += 1
    queue = [node_id for node_id in node_ids if indegree[node_id] == 0]
    visited = 0
    while queue:
        node_id = queue.pop(0)
        visited += 1
        for target in adjacency[node_id]:
            indegree[target] -= 1
            if indegree[target] == 0:
                queue.append(target)
    if visited != len(node_ids):
        raise WorkflowValidationError("工作流包含环路；当前执行器只支持有向无环图 (DAG)")

    # START 必须能到达 END，避免保存后必然没有结果。
    reachable = set()
    stack = [starts[0]]
    while stack:
        node_id = stack.pop()
        if node_id in reachable:
            continue
        reachable.add(node_id)
        stack.extend(adjacency[node_id])
    if ends[0] not in reachable:
        raise WorkflowValidationError("END 节点无法从 START 节点到达")
    unreachable = [node_id for node_id in node_ids if node_id not in reachable]
    if unreachable:
        raise WorkflowValidationError(
            f"存在无法从 START 到达的节点: {', '.join(unreachable)}"
        )


class GraphEngine:
    """加载并执行基于端口路由的多 Agent DAG。"""

    def __init__(self, workflow_config: dict | str, tool_registry: dict | None = None):
        if isinstance(workflow_config, str) and workflow_config.endswith(".json"):
            if not os.path.exists(workflow_config):
                raise FileNotFoundError(f"找不到工作流配置文件: {workflow_config}")
            with open(workflow_config, "r", encoding="utf-8") as file_obj:
                workflow_schema = json.load(file_obj)
        else:
            workflow_schema = workflow_config

        validate_workflow_schema(workflow_schema)
        self.workflow_id = workflow_schema.get(
            "workflow_id", workflow_schema.get("workflows_id", "default_workflow")
        )
        self.nodes_config = workflow_schema.get("nodes", [])
        self.connections = workflow_schema.get("connections", [])
        self.tools_registry = (
            tool_registry if tool_registry is not None else workflow_schema.get("tools_registry", {})
        )
        self.node_order = [node["id"] for node in self.nodes_config]
        self.agent_instances = self._init_agents()
        self._validate_runtime_ports()
        self.routing_table = self._build_routing_table()
        self.predecessors = self._build_predecessors()

        self.start_node_id = next(
            node["id"] for node in self.nodes_config if str(node.get("type", "AGENT")).upper() == "START"
        )
        self.end_node_id = next(
            node["id"] for node in self.nodes_config if str(node.get("type", "AGENT")).upper() == "END"
        )

    def _build_routing_table(self):
        table = defaultdict(list)
        for connection in self.connections:
            source_key = (connection["source_node"], connection["source_port"])
            table[source_key].append((connection["target_node"], connection["target_port"]))
        return dict(table)

    def _build_predecessors(self):
        predecessors = {node_id: set() for node_id in self.node_order}
        for connection in self.connections:
            predecessors[connection["target_node"]].add(connection["source_node"])
        return predecessors

    def _init_agents(self) -> dict:
        instances = {}
        for node_cfg in self.nodes_config:
            node_id = node_cfg["id"]
            node_type = str(node_cfg.get("type", "AGENT")).upper()

            # AgentNode 会在存在 ref 时加载模板，并用当前工作流节点配置覆盖模板。
            if node_type == "START":
                node_instance = StartNode(node_cfg)
            elif node_type == "END":
                node_instance = EndNode(node_cfg)
            else:
                node_instance = AgentNode(node_cfg, tool_registry=self.tools_registry)

            node_instance.name = node_id
            instances[node_id] = node_instance
            print(f"[GraphEngine] 成功加载并实例化节点: {node_id} (类型: {node_type})")
        return instances

    def _validate_runtime_ports(self) -> None:
        input_ports = {
            node_id: {port.get("id") for port in node.input_ports if port.get("id")}
            for node_id, node in self.agent_instances.items()
        }
        output_ports = {
            node_id: {port.get("id") for port in node.output_ports if port.get("id")}
            for node_id, node in self.agent_instances.items()
        }
        for connection in self.connections:
            source = connection["source_node"]
            target = connection["target_node"]
            source_port = connection["source_port"]
            target_port = connection["target_port"]
            if source_port not in output_ports[source]:
                raise WorkflowValidationError(f"节点 {source} 不存在输出端口 {source_port}")
            if target_port not in input_ports[target]:
                raise WorkflowValidationError(f"节点 {target} 不存在输入端口 {target_port}")

    @staticmethod
    def _store_inbox_value(global_state: dict, box_key: str, payload: Any) -> None:
        if box_key not in global_state:
            global_state[box_key] = payload
            return
        existing = global_state[box_key]
        if isinstance(existing, list):
            existing.append(payload)
        else:
            global_state[box_key] = [existing, payload]

    def send_message(self, agent_output: dict, global_state: dict):
        current_node = agent_output.get("node_name")
        status = agent_output.get("status")
        outputs = agent_output.get("outputs", [])
        if status != "success":
            error_message = agent_output.get("message", f"节点 {current_node} 执行失败")
            global_state.setdefault("_errors", []).append(error_message)
            return global_state, [], False

        activated_targets = set()
        fallback_to_end = False
        declared_ports = {
            port.get("id")
            for port in self.agent_instances[current_node].output_ports
            if port.get("id")
        }
        for output in outputs:
            port_id = output.get("port_id")
            payload = output.get("payload")
            ui_show = output.get("ui_show", False)
            if ui_show:
                self._send_to_frontend(payload)
                continue

            invalid_port = not port_id or port_id not in declared_ports
            if output.get("fallback_to_end") or invalid_port:
                reason = output.get("fallback_reason") or (
                    f"节点 {current_node} 输出了不存在的端口: {port_id or '<missing>'}"
                )
                end_node = self.agent_instances[self.end_node_id]
                end_port = (
                    end_node.input_ports[0]["id"]
                    if end_node.input_ports
                    else "final_result"
                )
                global_state[f"{current_node}:{port_id or '<missing>'}"] = payload
                self._store_inbox_value(
                    global_state,
                    f"{self.end_node_id}:{end_port}",
                    payload,
                )
                global_state.setdefault("_fallbacks", []).append({
                    "source_node": current_node,
                    "source_port": port_id,
                    "target_node": self.end_node_id,
                    "target_port": end_port,
                    "reason": reason,
                })
                print(
                    f"[routing] 端口无效，降级投递: "
                    f"{current_node}:{port_id or '<missing>'} -> "
                    f"{self.end_node_id}:{end_port} ({reason})"
                )
                activated_targets.add(self.end_node_id)
                fallback_to_end = True
                continue

            # 始终保留源节点输出，最终结果不再依赖“没有下游连接”这一偶然条件。
            global_state[f"{current_node}:{port_id}"] = payload
            for target_node, target_port in self.routing_table.get((current_node, port_id), []):
                print(
                    f"[routing] 投递成功: {current_node}:{port_id} -> {target_node}:{target_port}"
                )
                self._store_inbox_value(global_state, f"{target_node}:{target_port}", payload)
                activated_targets.add(target_node)

        return global_state, list(activated_targets), fallback_to_end

    @staticmethod
    def _send_to_frontend(message):
        # 当前 HTTP 接口不是流式传输；这里只保留服务端日志。
        print(f"[frontend] {message}")

    def _ordered(self, node_ids: set[str]) -> list[str]:
        return [node_id for node_id in self.node_order if node_id in node_ids]

    def _settle_inactive_nodes(
        self,
        activated: set[str],
        executed: set[str],
        skipped: set[str],
    ) -> None:
        """传播确定不会收到消息的分支，使可选分支不会阻塞汇合节点。"""
        changed = True
        while changed:
            changed = False
            settled = executed | skipped
            for node_id in self.node_order:
                if node_id in activated or node_id in settled:
                    continue
                predecessors = self.predecessors[node_id]
                if not predecessors or predecessors.issubset(settled):
                    skipped.add(node_id)
                    changed = True

    async def run(
        self,
        start_node_id: str | None = None,
        start_port_id: str | None = None,
        initial_data: Any = None,
        history: list | None = None,
        workflow_id: str | None = None,
        session_id: str | None = None,
    ):
        start_node_id = start_node_id or self.start_node_id
        if start_node_id != self.start_node_id:
            raise WorkflowExecutionError(
                f"启动节点必须是工作流声明的 START 节点 {self.start_node_id}"
            )
        start_node = self.agent_instances[start_node_id]
        start_port_id = start_port_id or (
            start_node.output_ports[0]["id"] if start_node.output_ports else "out_query"
        )

        global_state = {
            "history": list(history or []),
            "workflow_id": workflow_id or self.workflow_id,
            "session_id": session_id or "default_session",
            "_errors": [],
        }
        global_state[f"{start_node_id}:{start_port_id}"] = initial_data

        activated = {start_node_id}
        executed = set()
        skipped = set()

        while True:
            self._settle_inactive_nodes(activated, executed, skipped)
            settled = executed | skipped
            ready = {
                node_id
                for node_id in activated - settled
                if self.predecessors[node_id].issubset(settled)
            }
            if not ready:
                break
            current_batch = self._ordered(ready)
            print(f"\n[GraphEngine] 并发执行节点: {current_batch}")

            async def process_node(current_node_id):
                agent = self.agent_instances[current_node_id]
                try:
                    if inspect.iscoroutinefunction(agent.node_func):
                        result = await agent.node_func(global_state)
                    else:
                        result = agent.node_func(global_state)
                    if not isinstance(result, dict):
                        raise TypeError("节点必须返回字典")
                    return result.get("latest_node_output", result)
                except asyncio.CancelledError:
                    raise
                except Exception as exc:
                    return {
                        "node_name": current_node_id,
                        "status": "fail",
                        "message": f"节点 {current_node_id} 执行失败: {exc}",
                        "outputs": [],
                    }

            batch_results = await asyncio.gather(
                *(process_node(node_id) for node_id in current_batch)
            )
            executed.update(current_batch)
            batch_fallback_to_end = False
            for output in batch_results:
                global_state, targets, fallback_to_end = self.send_message(output, global_state)
                activated.update(targets)
                batch_fallback_to_end = batch_fallback_to_end or fallback_to_end

            if batch_fallback_to_end:
                skipped.update(set(self.node_order) - executed - {self.end_node_id})
                activated = {self.end_node_id}

        end_node = self.agent_instances[self.end_node_id]
        result = None
        for port in end_node.output_ports:
            result_key = f"{self.end_node_id}:{port.get('id')}"
            if result_key in global_state:
                result = global_state[result_key]
                break
        global_state["_result"] = result
        global_state["_executed_nodes"] = self._ordered(executed)
        global_state["_skipped_nodes"] = self._ordered(skipped)

        if result is None:
            details = "; ".join(global_state["_errors"]) or "END 节点未被执行"
            raise WorkflowExecutionError(f"工作流未产生最终结果: {details}")

        print("\n[GraphEngine] 工作流执行结束。")
        return global_state
