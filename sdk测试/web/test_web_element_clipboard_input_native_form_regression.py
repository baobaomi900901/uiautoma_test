"""clipboard_input 双模式脚本离线回归。"""
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import Mock

import test_web_element_clipboard_input_native_form as runner


class ClipboardInputRunnerTests(unittest.TestCase):
    def test_contract_and_parameters(self):
        detail = runner.contract()
        self.assertIn("clipboard_input", detail)
        self.assertEqual(tuple(runner.EXPECTED_PARAMS), (
            "self", "text", "append", "focus_timeout", "delay_after",
            "send_key_delay", "click_before_input", "anchor", "input_check",
            "retry_times", "check_value"))

    def test_both_variants_are_configurable(self):
        runner.configure_variant("noniframe")
        self.assertIn("form-controls", runner.URL)
        self.assertIn("非iframe", runner.INPUT_NAME)
        runner.configure_variant("iframe")
        self.assertIn("iframe-shadow-form", runner.URL)
        self.assertNotIn("非iframe", runner.INPUT_NAME)
        runner.configure_variant("noniframe")

    def test_case_matrix_has_clipboard_input_only_parameters(self):
        cases = runner.cases(runner.BASE_TEXT)
        self.assertEqual(len(cases), 13)
        allowed = {"append", "focus_timeout", "delay_after", "send_key_delay",
                   "click_before_input", "anchor", "input_check", "retry_times", "check_value"}
        self.assertTrue(all(set(step[1]) <= allowed for item in cases for step in item["steps"]))

    def test_payload_text_is_exact(self):
        self.assertIn("提交 JSON text='测试文本'", runner.check_payload({"text": "测试文本"}, "测试文本"))
        with self.assertRaises(AssertionError):
            runner.check_payload({"text": ""}, "测试文本")

    def test_terminal_report_is_available(self):
        self.assertTrue(callable(runner.print_report))
        self.assertEqual(runner.RESET, "\x1b[0m")


if __name__ == "__main__":
    unittest.main()
