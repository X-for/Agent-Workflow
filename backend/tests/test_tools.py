import os
import tempfile
import unittest

from tools.code_tools import _create_temp_script, execute_python_code
from tools.file_tools import _ensure_within
from tools.web_tools import _validate_public_http_url


class ToolSafetyTests(unittest.TestCase):
    def test_commonpath_rejects_sibling_prefix(self):
        with tempfile.TemporaryDirectory() as directory:
            base = os.path.join(directory, "task")
            sibling = os.path.join(directory, "task-escape", "file.txt")
            os.makedirs(base)
            with self.assertRaises(ValueError):
                _ensure_within(base, sibling)

    def test_concurrent_scripts_get_unique_paths(self):
        first = _create_temp_script("print(1)", ".py")
        second = _create_temp_script("print(2)", ".py")
        try:
            self.assertNotEqual(first, second)
            self.assertTrue(os.path.exists(first))
            self.assertTrue(os.path.exists(second))
        finally:
            os.remove(first)
            os.remove(second)

    def test_url_validator_rejects_loopback(self):
        with self.assertRaisesRegex(ValueError, "内网"):
            _validate_public_http_url("http://127.0.0.1/private")

    def test_python_tool_runs_without_model_or_uv(self):
        result = execute_python_code.invoke({"code": "print(6 * 7)"})
        self.assertIn("42", result)
        self.assertIn("执行成功", result)


if __name__ == "__main__":
    unittest.main()
