import asyncio
import json
import unittest
from types import SimpleNamespace

from Agent import AgentNode


class FakeLLM:
    def __init__(self, responses):
        self.responses = list(responses)

    async def ainvoke(self, messages):
        if len(self.responses) == 1:
            return self.responses[0]
        return self.responses.pop(0)


def response(content="", tool_calls=None):
    return SimpleNamespace(content=content, tool_calls=tool_calls or [])


class AgentNodeTests(unittest.TestCase):
    def config(self, **overrides):
        return {
            "id": "agent",
            "name": "agent",
            "input_ports": [{"id": "in", "name": "input"}],
            "output_ports": [{"id": "out", "description": "output"}],
            "tools": [],
            **overrides,
        }

    def test_invalid_model_port_is_marked_for_end_fallback(self):
        content = json.dumps({
            "deliveries": [{"target_port": "invented", "payload": "answer"}],
            "console_msg": "done",
        })
        agent = AgentNode(self.config(), llm=FakeLLM([response(content)]))
        agent.name = "agent"
        result = asyncio.run(agent.node_func({"agent:in": "question", "history": []}))
        outputs = result["latest_node_output"]["outputs"]
        self.assertEqual(outputs[0]["port_id"], "invented")
        self.assertEqual(outputs[0]["payload"], "answer")
        self.assertTrue(outputs[0]["fallback_to_end"])

    def test_tool_loop_exhaustion_raises_instead_of_returning_empty_payload(self):
        tool_call = {"name": "missing", "args": {}, "id": "call-1"}
        agent = AgentNode(
            self.config(max_tool_iterations=2),
            llm=FakeLLM([response(tool_calls=[tool_call]), response(tool_calls=[tool_call])]),
        )
        agent.name = "agent"
        with self.assertRaisesRegex(RuntimeError, "仍未生成最终答案"):
            asyncio.run(agent.node_func({"agent:in": "question", "history": []}))

    def test_reference_node_ports_can_be_overridden(self):
        agent = AgentNode(
            {
                "id": "search",
                "ref": "searcher.json",
                "input_ports": [{"id": "custom_in", "name": "custom"}],
                "output_ports": [{"id": "custom_out", "description": "custom"}],
            },
            llm=FakeLLM([response("plain answer")]),
        )
        self.assertEqual(agent.input_ports[0]["id"], "custom_in")
        self.assertEqual(agent.output_ports[0]["id"], "custom_out")


if __name__ == "__main__":
    unittest.main()
