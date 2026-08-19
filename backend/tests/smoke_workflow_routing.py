"""Offline smoke test for prompt-driven workflow routing.

This script never calls a model API. It injects deterministic fake LLM replies
into the real AgentNode instances and verifies the actual GraphEngine routing.
"""

import asyncio
import json
import sys
from pathlib import Path
from types import SimpleNamespace


BACKEND_DIR = Path(__file__).resolve().parents[1]
PROJECT_ROOT = BACKEND_DIR.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from Graph import GraphEngine  # noqa: E402


class ScriptedLLM:
    def __init__(self, deliveries):
        self.deliveries = deliveries
        self.calls = 0
        self.prompt = ""

    async def ainvoke(self, messages):
        self.calls += 1
        self.prompt = "\n".join(str(message.content) for message in messages)
        content = json.dumps(
            {
                "deliveries": self.deliveries,
                "console_msg": "offline routing smoke test",
            },
            ensure_ascii=False,
        )
        return SimpleNamespace(content=content, tool_calls=[])


class FailIfCalledLLM:
    def __init__(self, node_id):
        self.node_id = node_id
        self.calls = 0

    async def ainvoke(self, _messages):
        self.calls += 1
        raise AssertionError(f"不应执行的节点被调用: {self.node_id}")


async def main():
    workflow_path = PROJECT_ROOT / "workflows" / "general_multi_agent.json"
    engine = GraphEngine(str(workflow_path), tool_registry={})

    dispatcher_llm = ScriptedLLM(
        [{"target_port": "code_task", "payload": "只执行代码类子任务"}]
    )
    coder_llm = ScriptedLLM(
        [{"target_port": "code_result", "payload": "代码节点已正确接收任务"}]
    )
    summarizer_llm = ScriptedLLM(
        [{"target_port": "final_summary", "payload": "工作流链路正常"}]
    )
    searcher_guard = FailIfCalledLLM("node_searcher")
    analyzer_guard = FailIfCalledLLM("node_analyzer")

    engine.agent_instances["node_dispatcher"].llm = dispatcher_llm
    engine.agent_instances["node_coder"].llm = coder_llm
    engine.agent_instances["node_searcher"].llm = searcher_guard
    engine.agent_instances["node_analyzer"].llm = analyzer_guard
    engine.agent_instances["node_summarizer"].llm = summarizer_llm

    state = await engine.run(initial_data="请写一个简单的 Python 加法函数")

    expected_executed = [
        "start_node",
        "node_dispatcher",
        "node_coder",
        "node_summarizer",
        "end_node",
    ]
    assert state["_result"] == "工作流链路正常", state["_result"]
    assert state["_executed_nodes"] == expected_executed, state["_executed_nodes"]
    assert {"node_searcher", "node_analyzer"}.issubset(state["_skipped_nodes"])
    assert state["node_coder:code_task"] == "只执行代码类子任务"
    assert "node_searcher:search_task" not in state
    assert "node_analyzer:analysis_task" not in state
    assert searcher_guard.calls == 0
    assert analyzer_guard.calls == 0

    for port_id in ("code_task", "search_task", "analysis_task", "direct_answer"):
        assert f"【{port_id}】" in dispatcher_llm.prompt
    assert '"deliveries"' in dispatcher_llm.prompt
    assert '"target_port"' in dispatcher_llm.prompt

    fallback_engine = GraphEngine(str(workflow_path), tool_registry={})
    invalid_dispatcher_llm = ScriptedLLM(
        [{"target_port": "missing_task", "payload": "非法端口时的直接回复"}]
    )
    fallback_guards = {
        node_id: FailIfCalledLLM(node_id)
        for node_id in (
            "node_coder",
            "node_searcher",
            "node_analyzer",
            "node_summarizer",
        )
    }
    fallback_engine.agent_instances["node_dispatcher"].llm = invalid_dispatcher_llm
    for node_id, guard in fallback_guards.items():
        fallback_engine.agent_instances[node_id].llm = guard

    fallback_state = await fallback_engine.run(initial_data="测试不存在的输出端口")
    assert fallback_state["_result"] == "非法端口时的直接回复"
    assert fallback_state["_executed_nodes"] == [
        "start_node",
        "node_dispatcher",
        "end_node",
    ]
    assert all(guard.calls == 0 for guard in fallback_guards.values())
    assert fallback_state["_fallbacks"][0]["source_port"] == "missing_task"
    assert fallback_state["_fallbacks"][0]["target_node"] == "end_node"

    direct_engine = GraphEngine(str(workflow_path), tool_registry={})
    direct_dispatcher_llm = ScriptedLLM(
        [{"target_port": "direct_answer", "payload": "普通问题直接回答"}]
    )
    direct_guards = {
        node_id: FailIfCalledLLM(node_id)
        for node_id in (
            "node_coder",
            "node_searcher",
            "node_analyzer",
            "node_summarizer",
        )
    }
    direct_engine.agent_instances["node_dispatcher"].llm = direct_dispatcher_llm
    for node_id, guard in direct_guards.items():
        direct_engine.agent_instances[node_id].llm = guard
    direct_state = await direct_engine.run(initial_data="你好")
    assert direct_state["_result"] == "普通问题直接回答"
    assert direct_state["_executed_nodes"] == [
        "start_node",
        "node_dispatcher",
        "end_node",
    ]
    assert all(guard.calls == 0 for guard in direct_guards.values())

    print(
        json.dumps(
            {
                "status": "PASS",
                "workflow": workflow_path.name,
                "selected_port": "code_task",
                "executed_nodes": state["_executed_nodes"],
                "skipped_nodes": state["_skipped_nodes"],
                "final_result": state["_result"],
                "prompt_contains_declared_ports": True,
                "direct_answer_route": {
                    "status": "PASS",
                    "executed_nodes": direct_state["_executed_nodes"],
                    "skipped_nodes": direct_state["_skipped_nodes"],
                    "final_result": direct_state["_result"],
                },
                "invalid_port_fallback": {
                    "status": "PASS",
                    "source_port": "missing_task",
                    "executed_nodes": fallback_state["_executed_nodes"],
                    "skipped_nodes": fallback_state["_skipped_nodes"],
                    "final_result": fallback_state["_result"],
                },
                "model_api_called": False,
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    asyncio.run(main())
