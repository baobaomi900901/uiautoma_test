"""find_all 表单运行器的离线回归，不连接 Runtime/浏览器。"""
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

import test_web_element_find_all_form as runner


class Element(runner.WebElement):
    def __init__(self, dom_id="", text="", html=None):
        self.dom_id = dom_id
        self.text = text
        self.html = html

    @property
    def name(self):
        return "运行时 DOM 名称，不是元素库名称"

    def get_attribute(self, name):
        return self.dom_id if name == "id" else None

    def get_text(self):
        return self.text

    def get_html(self):
        return self.html if self.html is not None else f'<input id="{self.dom_id}">'


PASSWORD_NAME = 'web靶场_表单测试_ant_密码输入框'
PASSWORD_HTML = ('<span class="ant-input-affix-wrapper css-example">'
                 '<input id="form-controls-ant-password" type="password">'
                 '<span class="ant-input-suffix"></span></span>')


class QueryRoot:
    def __init__(self, empty=False):
        self.empty = empty

    def find_all(self, selector, *, timeout=10):
        if not isinstance(selector, str) or not selector.strip():
            raise runner.InvalidParamsError("invalid selector")
        if timeout in (-2, "bad"):
            raise runner.InvalidParamsError("invalid timeout")
        if selector.startswith("__uiautoma_missing_"):
            raise runner.ElementNotFoundError("未找到选择器")
        if self.empty:
            return []
        if selector == runner.MULTI_NAME:
            return [Element(text=text) for text in ("其他", "男", "女")]
        if selector == PASSWORD_NAME:
            return [Element(html=PASSWORD_HTML)]
        return [Element(runner.INPUT_IDS[selector])]


class ResultTests(unittest.TestCase):
    def run_cases(self, empty):
        package = Mock()
        package.selector.side_effect = lambda name: name
        return runner.run_find_all_cases(
            QueryRoot(empty=empty), package, SimpleNamespace(timeout=0, empty_timeout=0),
            {name: QueryRoot(empty=True) for name in runner.TARGETS}, ["男", "女", "其他"])

    def test_all_cases_accept_valid_results(self):
        rows = self.run_cases(empty=False)
        self.assertEqual(len(rows), 19)
        self.assertTrue(all(row["status"] == "PASS" for row in rows), rows)

    def test_issue64_empty_results_remain_seven_positive_failures(self):
        rows = self.run_cases(empty=True)
        failures = [row for row in rows if row["status"] == "FAIL"]
        self.assertEqual(len(failures), 7)
        self.assertTrue(all("实际 0 项" in row["detail"] for row in failures))
        unknown = next(row for row in rows if row["case_id"] == "unknown_library_name")
        self.assertEqual(unknown["status"], "PASS")

    def test_checks_dom_id_without_requiring_library_name(self):
        value = [Element("form-controls-ant-email")]
        self.assertIn("form-controls-ant-email", runner.check_matches(value, [value[0].dom_id]))

    def test_password_wrapper_without_id_is_the_saved_target(self):
        detail = runner.check_input_matches([Element(html=PASSWORD_HTML)], PASSWORD_NAME)
        self.assertIn('span', detail)
        self.assertIn('form-controls-ant-password', detail)

    def test_password_child_is_not_substituted_for_saved_wrapper(self):
        html = '<input id="form-controls-ant-password" type="password">'
        with self.assertRaisesRegex(AssertionError, "实际.*input"):
            runner.check_input_matches([Element(html=html)], PASSWORD_NAME)

    def test_password_wrong_wrapper_or_child_fails_with_actual_details(self):
        samples = (
            PASSWORD_HTML.replace('ant-input-affix-wrapper', 'unrelated'),
            PASSWORD_HTML.replace('form-controls-ant-password', 'form-controls-ant-search'),
            PASSWORD_HTML.replace('type="password"', 'type="text"'),
            '<span class="ant-input-affix-wrapper"></span>',
        )
        for html in samples:
            with self.subTest(html=html):
                with self.assertRaisesRegex(AssertionError, "实际"):
                    runner.check_input_matches([Element(html=html)], PASSWORD_NAME)

    def test_password_count_and_return_type_are_still_strict(self):
        for value in ([], None, ["wrong"], [Element(html=PASSWORD_HTML)] * 2):
            with self.subTest(value_type=type(value).__name__):
                with self.assertRaises(AssertionError):
                    runner.check_input_matches(value, PASSWORD_NAME)

    def test_positive_empty_list_remains_failure(self):
        with self.assertRaisesRegex(AssertionError, "实际.*0"):
            runner.check_matches([], ["form-controls-ant-text"])

    def test_rejects_non_list_and_non_element_items(self):
        for value in (None, Element("x"), ["x"]):
            with self.subTest(value=type(value).__name__):
                with self.assertRaises(AssertionError):
                    runner.check_matches(value, ["x"])

    def test_rejects_duplicate_or_wrong_dom_nodes(self):
        for value in ([Element("a"), Element("a")], [Element("a"), Element("c")]):
            with self.subTest(ids=[item.dom_id for item in value]):
                with self.assertRaises(AssertionError):
                    runner.check_matches(value, ["a", "b"])

    def test_multi_match_compares_all_texts_without_order_assumption(self):
        self.assertIn("3", runner.check_matches(
            [Element(text=text) for text in ("其他", "男", "女")], ["男", "女", "其他"], by_text=True))

    def test_empty_scope_requires_list_not_exception(self):
        self.assertIn("0", runner.check_matches([], []))
        rows = []
        def fail():
            raise runner.ElementNotFoundError("missing")
        runner.record_case(rows, "empty", lambda: runner.check_matches(fail(), []))
        self.assertEqual(rows[0]["status"], "FAIL")

    def test_exception_is_reported_with_trace(self):
        rows = []
        def fail():
            error = RuntimeError("probe failure")
            error.trace_info = "probe_trace"
            error.trace_id = "probe_id"
            raise error
        runner.record_case(rows, "email", fail)
        self.assertEqual(rows[0]["status"], "FAIL")
        self.assertIn("probe_trace", rows[0]["detail"])
        self.assertIn("probe_id", rows[0]["detail"])

    def test_cleanup_failure_does_not_hide_other_cleanup(self):
        with TemporaryDirectory() as temp:
            copy = Path(temp) / "uiautoma-element-find-all-owned"
            copy.mkdir()
            page, package = Mock(), Mock()
            page.close.side_effect = RuntimeError("close failed")
            resources = {"page": page, "package": package, "temp_dir": copy}
            rows = []
            runner.cleanup(resources, rows, Path(temp))
            self.assertEqual(rows[0]["status"], "FAIL")
            package.close.assert_called_once()
            self.assertFalse(copy.exists())

    def test_package_close_failure_retains_copy_and_reports_failure(self):
        with TemporaryDirectory() as temp:
            copy = Path(temp) / "uiautoma-element-find-all-owned"
            copy.mkdir()
            package = Mock()
            package.close.side_effect = RuntimeError("package close failed")
            rows = []
            runner.cleanup({"package": package, "temp_dir": copy}, rows, Path(temp))
            self.assertTrue(copy.exists())
            self.assertTrue(all(row["status"] == "FAIL" for row in rows))

    def test_preparation_failure_still_closes_open_package(self):
        with TemporaryDirectory() as temp:
            library = Path(temp) / "library"
            library.mkdir()
            args = SimpleNamespace(contract_only=False, library=library, temp_root=Path(temp),
                                   mode="chrome", timeout=1, empty_timeout=0.3,
                                   runtime_timeout=1, load_timeout=1, element_timeout=1)
            package = Mock()
            with patch.object(runner.uiautoma, "open", return_value=package), \
                 patch.object(runner.web, "create", side_effect=RuntimeError("page failed")):
                rows, code = runner.run(args)
            self.assertEqual(code, 1)
            self.assertTrue(any(r["case_id"] == "page_prepare" and r["status"] == "FAIL" for r in rows))
            package.close.assert_called_once()
            self.assertFalse(list(Path(temp).glob("uiautoma-element-find-all-*")))


if __name__ == "__main__":
    unittest.main()
