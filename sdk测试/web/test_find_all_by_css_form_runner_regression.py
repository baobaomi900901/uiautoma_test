"""find_all_by_css 脚本离线回归，不访问浏览器。"""
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

import test_web_element_find_all_by_css_form as runner


PASSWORD_HTML = ('<span class="ant-input-affix-wrapper ant-input-password">'
                 '<input type="password" id="form-controls-ant-password"></span>')


class Element(runner.WebElement):
    def __init__(self, dom_id=None, attrs=None, html=None):
        self.attrs = attrs if attrs is not None else {"id": dom_id}
        self.html = html

    def get_attribute(self, name):
        return self.attrs.get(name)

    def get_all_attributes(self):
        return dict(self.attrs)

    def get_html(self):
        return self.html or f'<input id="{self.attrs.get("id", "")}">'


def descriptors():
    return [{"id": value, "type": "text", "role": None, "placeholder": None}
            for value in runner.INPUT_IDS.values()]


class Root:
    def __init__(self, scope="root", truncated=False, none_on_missing=False, syntax_trace="invalid_css_selector"):
        self.scope, self.truncated = scope, truncated
        self.none_on_missing, self.syntax_trace = none_on_missing, syntax_trace

    def find_all_by_css(self, css_selector, *, timeout=10):
        if not isinstance(css_selector, str) or not css_selector.strip():
            raise runner.InvalidParamsError("bad selector")
        if timeout in (-2, "bad"):
            raise runner.InvalidParamsError("bad timeout")
        if css_selector == "input[":
            raise runner.RpcProtocolError("bad CSS", trace_info=self.syntax_trace)
        if self.scope == "leaf" or css_selector in (runner.MISSING_CSS, "#shadow-form-content"):
            return None if self.none_on_missing else []
        if css_selector == "input":
            if self.scope == "password":
                return [Element("form-controls-ant-password")]
            items = [Element(attrs={k: v for k, v in row.items() if v is not None}) for row in descriptors()]
            return items[:1] if self.truncated else items
        if css_selector == runner.GROUP_CSS:
            return [Element(value) for value in reversed(tuple(runner.INPUT_IDS.values()))]
        for label, css, name, wrapper in runner.CSS_CASES:
            if css_selector == css:
                return [Element(html=PASSWORD_HTML)] if wrapper else [Element(runner.INPUT_IDS[name])]
        raise AssertionError(f"Unexpected selector: {css_selector!r}")


class CssListTests(unittest.TestCase):
    def snapshot(self):
        return {
            "inputs": [{"id": value, "tag": "INPUT", "count": 1, "children": 0}
                       for value in runner.INPUT_IDS.values()],
            "queries": [{"css": css, "count": 1, "nodes": [{
                "tag": "SPAN" if wrapper else "INPUT", "id": None if wrapper else runner.INPUT_IDS[name],
            }]} for label, css, name, wrapper in runner.CSS_CASES],
            "multiple_count": len(descriptors()), "all_inputs": descriptors(),
            "group_ids": list(runner.INPUT_IDS.values()),
            "missing_count": 0, "self_count": 0, "password_input_count": 1,
        }

    def run_cases(self, root):
        seeds = {runner.TARGETS[0]: Root("leaf"), runner.PASSWORD_NAME: Root("password")}
        return runner.run_find_all_by_css_cases(
            root, SimpleNamespace(timeout=0, empty_timeout=0), seeds, self.snapshot())

    def test_full_matrix_accepts_valid_lists(self):
        rows = self.run_cases(Root())
        self.assertGreaterEqual(len(rows), 20)
        self.assertTrue(all(row["status"] == "PASS" for row in rows), rows)

    def test_truncation_fails(self):
        rows = self.run_cases(Root(truncated=True))
        self.assertEqual(next(row for row in rows if row["case_id"] == "multiple_matches")["status"], "FAIL")

    def test_equal_count_with_wrong_membership_fails(self):
        expected = descriptors()
        actual = [Element(attrs=row) for row in expected]
        actual[-1] = actual[0]
        with self.assertRaises(AssertionError):
            runner.check_all_inputs(actual, expected)

    def test_attribute_absence_and_empty_string_are_distinct(self):
        expected = [{"id": "x", "type": None, "role": None, "placeholder": None}]
        runner.check_all_inputs([Element("x")], expected)
        with self.assertRaises(AssertionError):
            runner.check_all_inputs([Element(attrs={"id": "x", "type": ""})], expected)

    def test_single_object_cannot_replace_list(self):
        with self.assertRaises(AssertionError):
            runner.check_matches(Element("x"), ["x"])

    def test_none_cannot_replace_empty_list(self):
        rows = self.run_cases(Root(none_on_missing=True))
        self.assertEqual(next(row for row in rows if row["case_id"] == "missing_zero")["status"], "FAIL")

    def test_missing_list_does_not_accept_exception(self):
        def missing():
            raise runner.ElementNotFoundError("missing")
        rows = []
        runner.record_case(rows, "missing", lambda: runner.check_empty(missing))
        self.assertEqual(rows[0]["status"], "FAIL")

    def test_empty_wait_rejects_early_return(self):
        with self.assertRaisesRegex(AssertionError, "等待"):
            runner.check_empty(lambda: [], min_elapsed=0.3)

    def test_wrong_runtime_exception_is_not_invalid_css(self):
        rows = self.run_cases(Root(syntax_trace="page_runtime_probe_timeout"))
        self.assertEqual(next(row for row in rows if row["case_id"] == "invalid_css_syntax")["status"], "FAIL")

    def test_dom_reference_checks_all_and_subset(self):
        runner.validate_dom(self.snapshot())
        bad = self.snapshot()
        bad["multiple_count"] += 1
        with self.assertRaises(AssertionError):
            runner.validate_dom(bad)
        bad = self.snapshot()
        bad["group_ids"][-1] = "form-controls-native-number"
        with self.assertRaises(AssertionError):
            runner.validate_dom(bad)

    def test_preparation_failure_cleans_owned_resources(self):
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
            self.assertFalse(list(Path(temp).glob("uiautoma-element-all-css-*")))


if __name__ == "__main__":
    unittest.main()
