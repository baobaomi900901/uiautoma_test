"""close_all 测试脚本自身的离线回归；不启动或关闭浏览器。"""
import unittest
from urllib.parse import parse_qs, urlsplit

import test_web_close_all as runner


TARGET_URL = "https://baobaomi900901.github.io/xpath/#/iframe-shadow-form"


class CloseAllRunnerRegression(unittest.TestCase):
    def test_default_targets_use_current_site(self):
        args = runner.parse_args(["--mode", "chrome"])
        self.assertEqual((args.base_url, args.second_url), (TARGET_URL, TARGET_URL))

    def test_same_site_is_valid_for_two_owned_tabs(self):
        args = runner.parse_args([
            "--mode", "chrome", "--base-url", TARGET_URL, "--second-url", TARGET_URL,
        ])
        first = runner._marked_url(args.base_url, "offline-run", "owned_first")
        second = runner._marked_url(args.second_url, "offline-run", "owned_second")
        self.assertNotEqual(runner._canonical_url(first), runner._canonical_url(second))

    def test_run_marker_preserves_hash_route(self):
        marked = runner._marked_url(TARGET_URL, "offline-run", "owned_first")
        self.assertEqual(urlsplit(marked).fragment, "/iframe-shadow-form")
        self.assertEqual(parse_qs(urlsplit(marked).query)[runner.RUN_QUERY_KEY], ["offline-run"])
        self.assertNotEqual(runner._canonical_url(TARGET_URL),
                            runner._canonical_url(TARGET_URL.replace("iframe-shadow-form", "other")))

    def test_bad_url_diagnostic_without_network(self):
        report = runner.preflight_targets(["invalid-url"], 0.1)
        self.assertEqual(report["status"], "BLOCKED")
        self.assertEqual(report.get("failed_url"), "invalid-url")
        self.assertEqual(report.get("exception"), "ValueError")
        self.assertTrue(report.get("error"))

    def test_explicit_consent_is_still_required(self):
        self.assertEqual(runner.check_destructive_authorization(False)["status"], "BLOCKED")


if __name__ == "__main__":
    unittest.main()
