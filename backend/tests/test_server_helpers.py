import asyncio
import mimetypes
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import server
from server import normalize_json_filename, safe_json_path


class ServerHelperTests(unittest.TestCase):
    def test_javascript_assets_use_browser_compatible_mime_type(self):
        self.assertEqual(mimetypes.guess_type("bundle.js")[0], "text/javascript")

    def test_json_filename_normalization(self):
        self.assertEqual(normalize_json_filename("demo"), "demo.json")
        self.assertEqual(normalize_json_filename("中文.json"), "中文.json")

    def test_path_traversal_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(ValueError):
                safe_json_path(Path(directory), "../outside", "测试文件")
            with self.assertRaises(ValueError):
                safe_json_path(Path(directory), "sub/file", "测试文件")

    def test_session_round_trip_adds_message_ids(self):
        with tempfile.TemporaryDirectory() as directory:
            with patch.object(server, "SESSIONS_DIR", Path(directory)):
                server.chat_memories.clear()
                server.save_session_memory(
                    "demo_session",
                    [{"role": "user", "content": "hello"}],
                )
                server.chat_memories.clear()
                messages = server.load_session_memory("demo_session")
        self.assertEqual(messages[0]["content"], "hello")
        self.assertTrue(messages[0]["id"])

    def test_same_session_requests_are_serialized(self):
        class FakeEngine:
            def __init__(self):
                self.histories = []

            async def run(self, **kwargs):
                self.histories.append(list(kwargs["history"]))
                await asyncio.sleep(0.01)
                return {"_result": f"answer-{len(self.histories)}"}

        async def scenario():
            engine = FakeEngine()
            first = server.ChatRequest(
                query="first",
                workflow_id="demo.json",
                session_id="shared",
                request_id="request_one",
            )
            second = server.ChatRequest(
                query="second",
                workflow_id="demo.json",
                session_id="shared",
                request_id="request_two",
            )
            with patch.object(server, "get_engine", return_value=engine):
                await asyncio.gather(server.chat_endpoint(first), server.chat_endpoint(second))
            return engine

        with tempfile.TemporaryDirectory() as directory:
            with patch.object(server, "SESSIONS_DIR", Path(directory)):
                server.chat_memories.clear()
                server.session_locks.clear()
                server.active_chat_tasks.clear()
                engine = asyncio.run(scenario())
                messages = server.load_session_memory("demo.json_shared")

        self.assertEqual(len(engine.histories), 2)
        self.assertEqual(len(engine.histories[0]), 0)
        self.assertEqual(len(engine.histories[1]), 2)
        self.assertEqual(len(messages), 4)

    def test_cancel_endpoint_cancels_registered_task(self):
        async def scenario():
            task = asyncio.create_task(asyncio.sleep(60))
            server.active_chat_tasks["cancel_me"] = task
            result = await server.cancel_chat("cancel_me")
            with self.assertRaises(asyncio.CancelledError):
                await task
            server.active_chat_tasks.clear()
            return result

        result = asyncio.run(scenario())
        self.assertEqual(result["status"], "success")


if __name__ == "__main__":
    unittest.main()
