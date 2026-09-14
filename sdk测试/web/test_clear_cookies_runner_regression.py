"""脚本自身的离线检查；替换 SDK 边界，不连接浏览器、不修改 Cookie。"""
import unittest
from unittest.mock import Mock, patch

import test_web_clear_cookies as runner


class ClearCookiesRunnerRegression(unittest.TestCase):
    def test_contract_only_does_not_connect(self):
        with patch.object(runner.web, "create", side_effect=AssertionError("不应连接浏览器")):
            results = runner.run(Mock(contract_only=True))
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0][1], "PASS")

    def test_fixture_scope_is_unique_and_not_the_site(self):
        first, second = runner.make_fixtures(), runner.make_fixtures()
        self.assertEqual(len(first), 5)
        self.assertTrue(all(runner.urlsplit(i["url"]).hostname.endswith(".test") for i in first))
        self.assertNotEqual(first[0]["url"], second[0]["url"])

    def test_unfiltered_clear_is_refused(self):
        with patch.object(runner.web, "clear_cookies", side_effect=AssertionError("不应调用")) as call:
            with self.assertRaisesRegex(AssertionError, "拒绝无筛选清理"):
                runner.clear_and_check([], set(), "chrome")
        call.assert_not_called()

    def test_remaining_cookie_fails_deletion_check(self):
        fixture = runner.make_fixtures()[0]
        with patch.object(runner.web, "get_cookie", return_value={"name": fixture["name"]}):
            with self.assertRaisesRegex(AssertionError, "仍存在"):
                runner.verify_state([fixture], set(), "chrome")

    def test_deleted_control_cookie_fails_preservation_check(self):
        with patch.object(runner.web, "get_cookie", return_value={}):
            with self.assertRaisesRegex(AssertionError, "应保留"):
                runner.verify_state(runner.make_fixtures(), {0}, "chrome")

    def test_cleanup_error_is_not_hidden_and_page_close_is_attempted(self):
        page = Mock()
        with patch.object(runner.web, "remove_cookie", side_effect=RuntimeError("删除失败")):
            with self.assertRaisesRegex(AssertionError, "删除失败"):
                runner.cleanup(runner.make_fixtures()[:1], page, "chrome")
        page.close.assert_called_once_with(ignore_beforeunload=True)

    def test_failure_reason_is_reported(self):
        results = []
        self.assertFalse(runner.run_case(results, "故障样例", lambda: runner.require(False, "没有删除")))
        self.assertEqual(results[0][1], "FAIL")
        self.assertIn("没有删除", results[0][2])


if __name__ == "__main__":
    unittest.main()
