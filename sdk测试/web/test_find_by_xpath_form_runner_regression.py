"""XPath 元素查找脚本的离线判据回归；不操作浏览器。"""
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

import test_web_element_find_by_xpath_form as runner


class Element(runner.WebElement):
    def __init__(self, dom_id="", html=None):
        self.dom_id, self.html = dom_id, html

    def get_attribute(self, name):
        return self.dom_id if name == "id" else None

    def get_html(self):
        return self.html or f'<input id="{self.dom_id}">'


PASSWORD_HTML = ('<span class="ant-input-affix-wrapper ant-input-password">'
                 '<input type="password" id="form-controls-ant-password"></span>')


class Root:
    def __init__(self, scope="root", wrong_multiple=False, syntax_trace="xpath_segment_evaluate_failed"):
        self.scope = scope
        self.wrong_multiple = wrong_multiple
        self.syntax_trace = syntax_trace

    def find_by_xpath(self, xpath_selector, *, timeout=10):
        if not isinstance(xpath_selector, str) or not xpath_selector.strip():
            raise runner.InvalidParamsError("bad selector")
        if timeout in (-2, "bad"):
            raise runner.InvalidParamsError("bad timeout")
        if xpath_selector == ".//[":
            raise runner.RpcProtocolError("bad XPath", trace_info=self.syntax_trace)
        if xpath_selector == ".":
            return Element("shadow-form-content")
        if self.scope == "password" and xpath_selector == "./input":
            return Element("form-controls-ant-password")
        if self.scope == "password" and xpath_selector == "./input/..":
            return Element(html=PASSWORD_HTML)
        if self.scope == "leaf" or xpath_selector in (runner.MISSING_XPATH, runner.DESCENDANT_SELF_XPATH):
            raise runner.ElementNotFoundError("missing")
        if xpath_selector == ".//input":
            if self.scope == "password":
                return Element("form-controls-ant-password")
            if self.wrong_multiple:
                return Element("form-controls-ant-text")
            raise runner.AmbiguousElementError([])
        for label, css, name, wrapper in runner.XPATH_CASES:
            if xpath_selector == css:
                return Element(html=PASSWORD_HTML) if wrapper else Element(runner.INPUT_IDS[name])
        raise AssertionError(f"Unexpected test selector: {xpath_selector!r}")


class XpathRunnerTests(unittest.TestCase):
    def snapshot(self):
        return {
            'inputs': [{'id': dom_id, 'count': 1, 'tag': 'INPUT', 'children': 0}
                       for dom_id in runner.INPUT_IDS.values()],
            'queries': [{'xpath': css, 'count': 1, 'nodes': [{
                'tag': 'SPAN' if wrapper else 'INPUT',
                'id': None if wrapper else runner.INPUT_IDS[name],
            }]} for label, css, name, wrapper in runner.XPATH_CASES],
            'multiple_count': 20, 'missing_count': 0, 'descendant_self_count': 0,
            'self_count': 1, 'self_id': 'shadow-form-content', 'outside_count': 0,
            'password_input_count': 1, 'parent_count': 1, 'parent_is_wrapper': True,
        }

    def test_dom_oracle_requires_correct_nodes_and_scope_counts(self):
        self.assertIn('唯一命中', runner.validate_dom(self.snapshot()))
        bad = self.snapshot()
        bad['queries'][3]['nodes'][0]['id'] = 'form-controls-native-email'
        with self.assertRaisesRegex(AssertionError, '错误节点'):
            runner.validate_dom(bad)
        bad = self.snapshot()
        bad['password_input_count'] = 2
        with self.assertRaisesRegex(AssertionError, 'password_input_count'):
            runner.validate_dom(bad)

    def run_cases(self, root):
        seeds = {runner.TARGETS[0]: Root("leaf"), runner.PASSWORD_NAME: Root("password")}
        return runner.run_find_by_xpath_cases(root, SimpleNamespace(timeout=0, empty_timeout=0), seeds)

    def test_valid_results_and_expected_errors_pass(self):
        rows = self.run_cases(Root())
        self.assertGreaterEqual(len(rows), 20)
        self.assertTrue(all(row["status"] == "PASS" for row in rows), rows)

    def test_multiple_match_must_not_silently_return_first(self):
        rows = self.run_cases(Root(wrong_multiple=True))
        row = next(row for row in rows if row["case_id"] == "ambiguous")
        self.assertEqual(row["status"], "FAIL")

    def test_self_context_must_not_use_css_exclusion_rule(self):
        class NoSelf(Root):
            def find_by_xpath(self, xpath_selector, *, timeout=10):
                if xpath_selector == ".":
                    raise runner.ElementNotFoundError("self wrongly excluded")
                return super().find_by_xpath(xpath_selector, timeout=timeout)
        rows = self.run_cases(NoSelf())
        self.assertEqual(next(row for row in rows if row["case_id"] == "self_context")["status"], "FAIL")

    def test_dom_parent_axis_must_resolve_to_actual_wrapper(self):
        bad = self.snapshot()
        bad['parent_is_wrapper'] = False
        with self.assertRaisesRegex(AssertionError, 'parent_is_wrapper'):
            runner.validate_dom(bad)

    def test_unrelated_protocol_failure_cannot_count_as_invalid_xpath(self):
        rows = self.run_cases(Root(syntax_trace="page_runtime_probe_timeout"))
        row = next(row for row in rows if row["case_id"] == "invalid_xpath_syntax")
        self.assertEqual(row["status"], "FAIL")
        self.assertIn("page_runtime_probe_timeout", row["detail"])

    def test_native_email_cannot_satisfy_ant_email(self):
        with self.assertRaisesRegex(AssertionError, "form-controls-native-email"):
            runner.check_element(Element("form-controls-native-email"), "form-controls-ant-email")

    def test_single_api_rejects_list_and_none(self):
        for value in (None, [], [Element("x")]):
            with self.subTest(value_type=type(value).__name__):
                with self.assertRaises(AssertionError):
                    runner.check_element(value, "x")

    def test_saved_password_wrapper_keeps_its_identity(self):
        detail = runner.check_saved_element(Element(html=PASSWORD_HTML), runner.PASSWORD_NAME)
        self.assertIn("span", detail)
        with self.assertRaises(AssertionError):
            runner.check_saved_element(Element("form-controls-ant-password"), runner.PASSWORD_NAME)

    def test_missing_with_wait_rejects_premature_return(self):
        def missing():
            raise runner.ElementNotFoundError("missing")
        with self.assertRaisesRegex(AssertionError, "等待"):
            runner.expect_exception(missing, runner.ElementNotFoundError, min_elapsed=0.3)

    def test_preparation_failure_cleans_partial_resources(self):
        with TemporaryDirectory() as temp:
            library = Path(temp) / "library"
            library.mkdir()
            args = SimpleNamespace(contract_only=False, library=library, temp_root=Path(temp),
                                   mode="chrome", timeout=0, empty_timeout=0.3,
                                   element_timeout=1, load_timeout=1, runtime_timeout=1)
            package = Mock()
            with patch.object(runner.uiautoma, "open", return_value=package), \
                 patch.object(runner.web, "create", side_effect=RuntimeError("page failed")):
                rows, code = runner.run(args)
            self.assertEqual(code, 1)
            self.assertTrue(any(row["case_id"] == "page_prepare" and row["status"] == "FAIL" for row in rows))
            package.close.assert_called_once()
            self.assertFalse(list(Path(temp).glob("uiautoma-element-xpath-*")))

    def test_cleanup_failure_is_not_swallowed(self):
        with TemporaryDirectory() as temp:
            copy = Path(temp) / "uiautoma-element-xpath-owned"
            copy.mkdir()
            page, package = Mock(), Mock()
            page.close.side_effect = RuntimeError("close failed")
            rows = []
            runner.cleanup({"page": page, "package": package, "temp_dir": copy}, rows, Path(temp))
            self.assertEqual(rows[0]["status"], "FAIL")
            self.assertFalse(copy.exists())
            package.close.assert_called_once()


if __name__ == "__main__":
    unittest.main()
