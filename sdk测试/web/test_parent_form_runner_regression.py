"""parent 表单脚本离线回归；不操作浏览器。"""
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch
from uiautoma import ActionError

import test_web_element_parent_form as runner


LEAF_HTML = '<input id="form-controls-ant-text" type="text">'
PARENT_HTML = '<div class="ant-form-item-control-input-content">' + LEAF_HTML + '</div>'
ROOT_HTML = '<div id="shadow-form-content">' + PARENT_HTML + '</div>'


def descriptor(html, tag="DIV", dom_id="", classes=""):
    return {"html": html, "tag": tag, "id": dom_id, "class": classes}


def oracle():
    return {
        "input_id": "form-controls-ant-text", "input_tag": "INPUT",
        "ancestors": [
            descriptor(PARENT_HTML, classes="ant-form-item-control-input-content"),
            descriptor(ROOT_HTML, dom_id="shadow-form-content"),
        ],
        "boundary": {"id": "shadow-form-content", "parent_element_null": True,
                     "parent_node_type": 11, "shadow_host_id": "form-shadow-host"},
    }


class Element(runner.WebElement):
    def __init__(self, html, parent=None, failure=None):
        self.html, self.owner, self.failure = html, parent, failure

    @property
    def id(self):
        raise AssertionError("不能用 Runtime id 比较父节点身份")

    def get_html(self):
        return self.html

    def parent(self, *, timeout=5.0):
        try:
            seconds = 5.0 if timeout is None else float(timeout)
        except (ValueError, TypeError) as exc:
            raise runner.InvalidParamsError("bad timeout") from exc
        if seconds < 0:
            raise runner.InvalidParamsError("negative timeout")
        if self.failure:
            raise self.failure
        return self.owner


def target():
    root = Element(ROOT_HTML)
    return Element(LEAF_HTML, Element(PARENT_HTML, root))


def timeout_error(trace="web_dom_timeout"):
    return ActionError(SimpleNamespace(error=3, trace_info=trace, trace_id="zero-budget-probe"), "probe timeout")


class ZeroBudgetElement(Element):
    def parent(self, *, timeout=5.0):
        if timeout == 0:
            raise timeout_error()
        return super().parent(timeout=timeout)


class ParentRunnerTests(unittest.TestCase):
    def test_zero_budget_timeout_is_reported_as_boundary(self):
        normal = target()
        node = ZeroBudgetElement(normal.html, normal.owner)
        rows = runner.run_parent_cases(node, SimpleNamespace(timeout=2), oracle())
        zero = next(row for row in rows if row["case_id"] == "parent_zero_timeout")
        self.assertEqual(zero["status"], "PASS", zero)
        self.assertIn("web_dom_timeout", zero["detail"])
        self.assertIn("zero-budget-probe", zero["detail"])
        self.assertTrue(all(row["status"] == "PASS" for row in rows), rows)

    def test_other_action_error_is_not_accepted_for_zero_budget(self):
        node = Element(LEAF_HTML, failure=timeout_error("stale_element_reference"))
        with self.assertRaises(ActionError):
            runner.check_zero_timeout(node, oracle()["ancestors"][0])

    def test_unrelated_exception_with_matching_trace_is_not_accepted(self):
        error = RuntimeError("not an ActionError")
        error.trace_info = "web_dom_timeout"
        with self.assertRaises(RuntimeError):
            runner.check_zero_timeout(Element(LEAF_HTML, failure=error), oracle()["ancestors"][0])

    def test_zero_budget_does_not_accept_none_when_parent_exists(self):
        with self.assertRaises(AssertionError):
            runner.check_zero_timeout(Element(LEAF_HTML), oracle()["ancestors"][0])

    def test_positive_budget_timeout_remains_failure(self):
        rows = runner.run_parent_cases(Element(LEAF_HTML, failure=timeout_error()),
                                       SimpleNamespace(timeout=2), oracle())
        default = next(row for row in rows if row["case_id"] == "parent_default")
        self.assertEqual(default["status"], "FAIL")

    def test_matrix_accepts_valid_parent_chain_and_none(self):
        rows = runner.run_parent_cases(target(), SimpleNamespace(timeout=2), oracle())
        self.assertTrue(all(row["status"] == "PASS" for row in rows), rows)
        self.assertTrue(any(row["case_id"] == "boundary_none" for row in rows))

    def test_correct_parent_compared_without_runtime_id(self):
        self.assertIn("DOM", runner.check_parent(target().parent(), oracle()["ancestors"][0]))

    def test_same_class_wrong_branch_is_rejected(self):
        wrong = Element(PARENT_HTML.replace('form-controls-ant-text', 'form-controls-ant-email'))
        with self.assertRaises(AssertionError):
            runner.check_parent(wrong, oracle()["ancestors"][0])

    def test_parent_none_is_not_accepted_early(self):
        with self.assertRaisesRegex(AssertionError, "None"):
            runner.check_parent(None, oracle()["ancestors"][0])

    def test_boundary_requires_exact_none(self):
        self.assertIn("None", runner.check_parent(None, None))
        for value in ([], False, Element('<div id="form-shadow-host"></div>')):
            with self.subTest(value_type=type(value).__name__):
                with self.assertRaises(AssertionError):
                    runner.check_parent(value, None)

    def test_chain_fails_on_skipped_parent(self):
        wrong = Element(LEAF_HTML, Element(ROOT_HTML))
        with self.assertRaisesRegex(AssertionError, "第 1 层"):
            runner.walk_ancestors(wrong, oracle()["ancestors"], timeout=2)

    def test_chain_failure_cannot_mark_boundary_pass(self):
        rows = runner.run_parent_cases(Element(LEAF_HTML), SimpleNamespace(timeout=2), oracle())
        boundary = next(row for row in rows if row["case_id"] == "boundary_none")
        self.assertEqual(boundary["status"], "FAIL")

    def test_runtime_exception_is_not_treated_as_no_parent(self):
        rows = []
        node = Element(ROOT_HTML, failure=RuntimeError("relation failed"))
        runner.record_case(rows, "boundary", lambda: runner.check_parent(node.parent(), None))
        self.assertEqual(rows[0]["status"], "FAIL")
        self.assertIn("relation failed", rows[0]["detail"])

    def test_dom_oracle_must_prove_shadow_boundary(self):
        runner.validate_dom(oracle())
        for key, value in (("parent_element_null", False), ("parent_node_type", 1),
                           ("shadow_host_id", "wrong-host")):
            with self.subTest(key=key):
                snapshot = oracle()
                snapshot["boundary"][key] = value
                with self.assertRaises(AssertionError):
                    runner.validate_dom(snapshot)

    def test_prepare_failure_releases_package_and_copy(self):
        with TemporaryDirectory() as temp:
            library = Path(temp) / "library"
            library.mkdir()
            args = SimpleNamespace(contract_only=False, library=library, temp_root=Path(temp),
                                   mode="chrome", timeout=2, element_timeout=10,
                                   load_timeout=20, runtime_timeout=20)
            package = Mock()
            with patch.object(runner.uiautoma, "open", return_value=package), \
                 patch.object(runner.web, "create", side_effect=RuntimeError("page failed")):
                rows, code = runner.run(args)
            self.assertEqual(code, 1)
            package.close.assert_called_once()
            self.assertFalse(list(Path(temp).glob("uiautoma-element-parent-*")))


if __name__ == "__main__":
    unittest.main()
