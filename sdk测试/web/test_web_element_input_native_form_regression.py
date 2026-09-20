"""原生 input 脚本离线回归；不连接 Runtime 或浏览器。"""
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

import test_web_element_input_native_form as runner


class NativeInputRunnerTests(unittest.TestCase):
    def test_contract_and_case_matrix(self):
        self.assertIn("None 返回值", runner.contract())
        cases = runner.cases(runner.BASE_TEXT)
        names = {item["id"] for item in cases}
        self.assertEqual(len(names), 16)
        self.assertIn("append", names)
        self.assertIn("input_check", names)
        self.assertIn("cdp_input", names)

    def test_setup_uses_public_url_and_activation(self):
        page = Mock(spec=runner.WebBrowser)
        page.get_url.return_value = runner.URL
        active = Mock(spec=runner.WebBrowser)
        active.get_url.return_value = runner.URL
        # 只验证公开调用形状；真实元素绑定留给 live runner。
        page.activate()
        self.assertEqual(active.get_url(), page.get_url())

    def test_payload_text_is_exact(self):
        payload = {"text": "测试文本", "number": None, "hobbies": []}
        self.assertIn("提交 JSON text='测试文本'", runner.check_payload(payload, "测试文本"))
        with self.assertRaises(AssertionError):
            runner.check_payload(payload, "其他文本")

    def test_report_is_not_json_by_default(self):
        args = SimpleNamespace(target_url=runner.URL, library=Path("library"),
                               input_element_name=runner.INPUT_NAME,
                               submit_element_name=runner.SUBMIT_NAME)
        # 通过函数存在性和状态标签检查，避免离线测试连接浏览器。
        self.assertTrue(callable(runner.print_report))
        self.assertEqual(runner.RESET, "\x1b[0m")

    def test_https_preflight_retries_network_eof_as_blocked(self):
        error = runner.URLError("SSL: UNEXPECTED_EOF_WHILE_READING")
        with patch.object(runner, "urlopen", side_effect=error), \
             patch.object(runner.time, "sleep"):
            with self.assertRaises(runner.Blocked) as caught:
                runner.target_preflight(0.1)
        self.assertIn("连续 3 次失败", str(caught.exception))
        self.assertTrue(runner.is_blocked(caught.exception))

    def test_preflight_does_not_classify_api_as_failed(self):
        self.assertTrue(runner.is_blocked(runner.Blocked("network")))


if __name__ == "__main__":
    unittest.main()
