import asyncio
import json
import unittest
from pathlib import Path
from unittest.mock import patch

from Graph import (
    GraphEngine,
    WorkflowExecutionError,
    WorkflowValidationError,
    validate_workflow_schema,
)


class FakeAgentNode:
    observations = {}
    started_at = {}

    def __init__(self, config, tool_registry=None):
        self.cfg = config
        self.name = config.get("id", "fake")
        self.input_ports = config.get("input_ports", [])
        self.output_ports = config.get("output_ports", [])

    async def node_func(self, state):
        self.started_at[self.name] = asyncio.get_running_loop().time()
        inputs = {
            port["id"]: state.get(f"{self.name}:{port['id']}")
            for port in self.input_ports
            if f"{self.name}:{port['id']}" in state
        }
        self.observations.setdefault(self.name, []).append(inputs)
        if self.cfg.get("raise_error"):
            raise RuntimeError(self.cfg["raise_error"])
        if self.cfg.get("delay"):
            await asyncio.sleep(self.cfg["delay"])
        outputs = []
        for port_id in self.cfg.get("emit_ports", [port["id"] for port in self.output_ports]):
            payload = self.cfg.get("payload", self.name)
            if self.cfg.get("combine_inputs"):
                payload = "|".join(str(inputs[port["id"]]) for port in self.input_ports if port["id"] in inputs)
            outputs.append({
                "port_id": port_id,
                "payload": payload,
                "ui_show": False,
            })
        return {
            "latest_node_output": {
                "node_name": self.name,
                "status": "success",
                "message": "ok",
                "outputs": outputs,
            }
        }


def node(node_id, inputs, outputs, **extra):
    return {
        "id": node_id,
        "type": "AGENT",
        "input_ports": [{"id": port, "name": port} for port in inputs],
        "output_ports": [{"id": port, "description": port} for port in outputs],
        **extra,
    }


class GraphEngineTests(unittest.TestCase):
    def setUp(self):
        FakeAgentNode.observations = {}
        FakeAgentNode.started_at = {}

    def test_parallel_fan_out_and_fan_in(self):
        workflow = {
            "workflow_id": "parallel_fan_in",
            "nodes": [
                {"id": "start", "type": "START", "output_ports": [{"id": "out"}]},
                node("left", ["in"], ["out"], payload="L", delay=0.05),
                node("right", ["in"], ["out"], payload="R", delay=0.05),
                node("join", ["left", "right"], ["final"], combine_inputs=True),
                {"id": "end", "type": "END", "input_ports": [{"id": "in"}]},
            ],
            "connections": [
                {"source_node": "start", "source_port": "out", "target_node": "left", "target_port": "in"},
                {"source_node": "start", "source_port": "out", "target_node": "right", "target_port": "in"},
                {"source_node": "left", "source_port": "out", "target_node": "join", "target_port": "left"},
                {"source_node": "right", "source_port": "out", "target_node": "join", "target_port": "right"},
                {"source_node": "join", "source_port": "final", "target_node": "end", "target_port": "in"},
            ],
        }

        with patch("Graph.AgentNode", FakeAgentNode):
            state = asyncio.run(GraphEngine(workflow, {}).run(initial_data="question"))

        self.assertEqual(state["_result"], "L|R")
        self.assertLess(
            abs(FakeAgentNode.started_at["left"] - FakeAgentNode.started_at["right"]),
            0.02,
        )
        self.assertEqual(len(FakeAgentNode.observations["join"]), 1)

    def test_multiple_edges_to_same_input_port_are_aggregated(self):
        workflow = {
            "workflow_id": "aggregate",
            "nodes": [
                {"id": "start", "type": "START", "output_ports": [{"id": "out"}]},
                node("left", ["in"], ["out"], payload="L"),
                node("right", ["in"], ["out"], payload="R"),
                node("join", ["items"], ["final"]),
                {"id": "end", "type": "END", "input_ports": [{"id": "in"}]},
            ],
            "connections": [
                {"source_node": "start", "source_port": "out", "target_node": "left", "target_port": "in"},
                {"source_node": "start", "source_port": "out", "target_node": "right", "target_port": "in"},
                {"source_node": "left", "source_port": "out", "target_node": "join", "target_port": "items"},
                {"source_node": "right", "source_port": "out", "target_node": "join", "target_port": "items"},
                {"source_node": "join", "source_port": "final", "target_node": "end", "target_port": "in"},
            ],
        }

        with patch("Graph.AgentNode", FakeAgentNode):
            asyncio.run(GraphEngine(workflow, {}).run(initial_data="question"))

        self.assertEqual(FakeAgentNode.observations["join"], [{"items": ["L", "R"]}])

    def test_failed_parallel_node_does_not_deadlock_join(self):
        workflow = {
            "workflow_id": "partial_failure",
            "nodes": [
                {"id": "start", "type": "START", "output_ports": [{"id": "out"}]},
                node("good", ["in"], ["out"], payload="usable"),
                node("bad", ["in"], ["out"], raise_error="boom"),
                node("join", ["good", "bad"], ["final"], combine_inputs=True),
                {"id": "end", "type": "END", "input_ports": [{"id": "in"}]},
            ],
            "connections": [
                {"source_node": "start", "source_port": "out", "target_node": "good", "target_port": "in"},
                {"source_node": "start", "source_port": "out", "target_node": "bad", "target_port": "in"},
                {"source_node": "good", "source_port": "out", "target_node": "join", "target_port": "good"},
                {"source_node": "bad", "source_port": "out", "target_node": "join", "target_port": "bad"},
                {"source_node": "join", "source_port": "final", "target_node": "end", "target_port": "in"},
            ],
        }

        with patch("Graph.AgentNode", FakeAgentNode):
            state = asyncio.run(GraphEngine(workflow, {}).run(initial_data="question"))

        self.assertEqual(state["_result"], "usable")
        self.assertTrue(any("boom" in error for error in state["_errors"]))
        self.assertEqual(len(FakeAgentNode.observations["join"]), 1)

    def test_suppressed_only_branch_reports_no_result(self):
        workflow = {
            "workflow_id": "suppressed",
            "nodes": [
                {"id": "start", "type": "START", "output_ports": [{"id": "out"}]},
                node("router", ["in"], ["selected"], emit_ports=[]),
                {"id": "end", "type": "END", "input_ports": [{"id": "in"}]},
            ],
            "connections": [
                {"source_node": "start", "source_port": "out", "target_node": "router", "target_port": "in"},
                {"source_node": "router", "source_port": "selected", "target_node": "end", "target_port": "in"},
            ],
        }

        with patch("Graph.AgentNode", FakeAgentNode):
            with self.assertRaises(WorkflowExecutionError):
                asyncio.run(GraphEngine(workflow, {}).run(initial_data="question"))

    def test_unknown_output_port_short_circuits_to_end(self):
        workflow = {
            "workflow_id": "unknown_port_fallback",
            "nodes": [
                {"id": "start", "type": "START", "output_ports": [{"id": "out"}]},
                node(
                    "router",
                    ["in"],
                    ["declared"],
                    emit_ports=["missing"],
                    payload="fallback answer",
                ),
                node("worker", ["in"], ["out"], payload="must not run"),
                {"id": "end", "type": "END", "input_ports": [{"id": "in"}]},
            ],
            "connections": [
                {"source_node": "start", "source_port": "out", "target_node": "router", "target_port": "in"},
                {"source_node": "router", "source_port": "declared", "target_node": "worker", "target_port": "in"},
                {"source_node": "worker", "source_port": "out", "target_node": "end", "target_port": "in"},
            ],
        }

        with patch("Graph.AgentNode", FakeAgentNode):
            state = asyncio.run(GraphEngine(workflow, {}).run(initial_data="question"))

        self.assertEqual(state["_result"], "fallback answer")
        self.assertEqual(state["_executed_nodes"], ["start", "router", "end"])
        self.assertIn("worker", state["_skipped_nodes"])
        self.assertNotIn("worker", FakeAgentNode.observations)
        self.assertEqual(state["_fallbacks"][0]["source_port"], "missing")
        self.assertEqual(state["_fallbacks"][0]["target_node"], "end")

    def test_uneven_branches_wait_before_join(self):
        workflow = {
            "workflow_id": "uneven",
            "nodes": [
                {"id": "start", "type": "START", "output_ports": [{"id": "out"}]},
                node("a", ["in"], ["out"], payload="A"),
                node("b", ["in"], ["out"], payload="B"),
                node("c", ["in"], ["out"], payload="C"),
                node("join", ["from_a", "from_c"], ["final"], combine_inputs=True),
                {"id": "end", "type": "END", "input_ports": [{"id": "in"}]},
            ],
            "connections": [
                {"source_node": "start", "source_port": "out", "target_node": "a", "target_port": "in"},
                {"source_node": "start", "source_port": "out", "target_node": "b", "target_port": "in"},
                {"source_node": "a", "source_port": "out", "target_node": "join", "target_port": "from_a"},
                {"source_node": "b", "source_port": "out", "target_node": "c", "target_port": "in"},
                {"source_node": "c", "source_port": "out", "target_node": "join", "target_port": "from_c"},
                {"source_node": "join", "source_port": "final", "target_node": "end", "target_port": "in"},
            ],
        }

        with patch("Graph.AgentNode", FakeAgentNode):
            engine = GraphEngine(workflow, {})
            state = asyncio.run(engine.run(initial_data="question"))

        self.assertEqual(state["_result"], "A|C")
        self.assertEqual(len(FakeAgentNode.observations["join"]), 1)
        self.assertEqual(
            FakeAgentNode.observations["join"][0],
            {"from_a": "A", "from_c": "C"},
        )

    def test_inactive_optional_branch_does_not_block_join(self):
        workflow = {
            "workflow_id": "conditional",
            "nodes": [
                {"id": "start", "type": "START", "output_ports": [{"id": "out"}]},
                node("router", ["in"], ["active", "inactive"], emit_ports=["active"]),
                node("active", ["in"], ["out"], payload="done"),
                node("inactive", ["in"], ["out"], payload="should-not-run"),
                node("join", ["active", "inactive"], ["final"], combine_inputs=True),
                {"id": "end", "type": "END", "input_ports": [{"id": "in"}]},
            ],
            "connections": [
                {"source_node": "start", "source_port": "out", "target_node": "router", "target_port": "in"},
                {"source_node": "router", "source_port": "active", "target_node": "active", "target_port": "in"},
                {"source_node": "router", "source_port": "inactive", "target_node": "inactive", "target_port": "in"},
                {"source_node": "active", "source_port": "out", "target_node": "join", "target_port": "active"},
                {"source_node": "inactive", "source_port": "out", "target_node": "join", "target_port": "inactive"},
                {"source_node": "join", "source_port": "final", "target_node": "end", "target_port": "in"},
            ],
        }

        with patch("Graph.AgentNode", FakeAgentNode):
            engine = GraphEngine(workflow, {})
            state = asyncio.run(engine.run(initial_data="question"))

        self.assertEqual(state["_result"], "done")
        self.assertIn("inactive", state["_skipped_nodes"])
        self.assertNotIn("inactive", FakeAgentNode.observations)

    def test_cycle_is_rejected(self):
        workflow = {
            "nodes": [
                {"id": "start", "type": "START"},
                node("a", ["in"], ["out"]),
                {"id": "end", "type": "END"},
            ],
            "connections": [
                {"source_node": "start", "source_port": "out", "target_node": "a", "target_port": "in"},
                {"source_node": "a", "source_port": "out", "target_node": "a", "target_port": "in"},
                {"source_node": "a", "source_port": "out", "target_node": "end", "target_port": "in"},
            ],
        }
        with self.assertRaisesRegex(WorkflowValidationError, "环路"):
            validate_workflow_schema(workflow)

    def test_invalid_start_end_boundaries_and_unreachable_nodes_are_rejected(self):
        cases = {
            "incoming_start": (
                {
                    "nodes": [
                        {"id": "start", "type": "START"},
                        node("rogue", [], ["out"]),
                        {"id": "end", "type": "END"},
                    ],
                    "connections": [
                        {"source_node": "rogue", "source_port": "out", "target_node": "start", "target_port": "in"},
                        {"source_node": "start", "source_port": "out", "target_node": "end", "target_port": "in"},
                    ],
                },
                "START",
            ),
            "outgoing_end": (
                {
                    "nodes": [
                        {"id": "start", "type": "START"},
                        {"id": "end", "type": "END"},
                        node("tail", ["in"], []),
                    ],
                    "connections": [
                        {"source_node": "start", "source_port": "out", "target_node": "end", "target_port": "in"},
                        {"source_node": "end", "source_port": "out", "target_node": "tail", "target_port": "in"},
                    ],
                },
                "END",
            ),
            "unreachable": (
                {
                    "nodes": [
                        {"id": "start", "type": "START"},
                        node("orphan", [], []),
                        {"id": "end", "type": "END"},
                    ],
                    "connections": [
                        {"source_node": "start", "source_port": "out", "target_node": "end", "target_port": "in"},
                    ],
                },
                "无法从 START 到达",
            ),
        }

        for name, (workflow, message) in cases.items():
            with self.subTest(name=name):
                with self.assertRaisesRegex(WorkflowValidationError, message):
                    validate_workflow_schema(workflow)

    def test_all_bundled_workflows_load_without_model_calls(self):
        workflow_dir = Path(__file__).resolve().parents[2] / "workflows"
        workflow_files = sorted(workflow_dir.glob("*.json"))
        self.assertGreater(len(workflow_files), 0)
        for workflow_file in workflow_files:
            with self.subTest(workflow=workflow_file.name):
                GraphEngine(str(workflow_file), {})

    def test_all_bundled_workflows_execute_with_fake_agents(self):
        workflow_dir = Path(__file__).resolve().parents[2] / "workflows"
        workflow_files = sorted(workflow_dir.glob("*.json"))
        self.assertGreater(len(workflow_files), 0)

        with patch("Graph.AgentNode", FakeAgentNode):
            for workflow_file in workflow_files:
                with self.subTest(workflow=workflow_file.name):
                    FakeAgentNode.observations = {}
                    state = asyncio.run(
                        GraphEngine(str(workflow_file), {}).run(
                            initial_data="offline topology test"
                        )
                    )
                    self.assertIsNotNone(state["_result"])
                    self.assertIn("start_node", state["_executed_nodes"])
                    self.assertIn("end_node", state["_executed_nodes"])

    def test_adaptive_router_single_branch_and_direct_answer(self):
        workflow_path = (
            Path(__file__).resolve().parents[2]
            / "workflows"
            / "adaptive_task_router.json"
        )
        cases = {
            "software_task": [
                "start_node",
                "task_router",
                "software_specialist",
                "result_aggregator",
                "end_node",
            ],
            "direct_answer": ["start_node", "task_router", "end_node"],
        }

        with patch("Graph.AgentNode", FakeAgentNode):
            for selected_port, expected_nodes in cases.items():
                with self.subTest(selected_port=selected_port):
                    workflow = json.loads(workflow_path.read_text(encoding="utf-8"))
                    router = next(
                        node for node in workflow["nodes"] if node["id"] == "task_router"
                    )
                    router["emit_ports"] = [selected_port]
                    router["payload"] = f"payload for {selected_port}"
                    FakeAgentNode.observations = {}

                    state = asyncio.run(
                        GraphEngine(workflow, {}).run(initial_data="route this task")
                    )

                    self.assertEqual(state["_executed_nodes"], expected_nodes)
                    if selected_port == "software_task":
                        self.assertNotIn("research_specialist", FakeAgentNode.observations)
                        self.assertNotIn("data_specialist", FakeAgentNode.observations)
                        self.assertNotIn("content_specialist", FakeAgentNode.observations)
                    else:
                        self.assertEqual(state["_result"], "payload for direct_answer")
                        self.assertNotIn("result_aggregator", FakeAgentNode.observations)


if __name__ == "__main__":
    unittest.main()
