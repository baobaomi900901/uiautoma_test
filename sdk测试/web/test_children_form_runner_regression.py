"""children 表单脚本的离线回归；不操作浏览器。"""
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

import test_web_element_children_form as runner


INPUT_HTML = '<input id="form-controls-ant-text" type="text">'
PARENT_HTML = '<div class="input-content">' + INPUT_HTML + '</div>'
LABEL_HTML = '<label>文本输入框</label>'
MULTI_HTML = '<div id="multi">' + LABEL_HTML + '\n' + PARENT_HTML + '</div>'


def info(html, tag="DIV", dom_id="", classes=""):
    return {"html": html, "tag": tag, "id": dom_id, "class": classes}


def oracle():
    leaf = info(INPUT_HTML, "INPUT", "form-controls-ant-text")
    parent = info(PARENT_HTML, classes="input-content")
    label = info(LABEL_HTML, "LABEL")
    return {
        "input": leaf, "leaf_children": [], "target_index": 0, "multi_index": 1,
        "ancestors": [
            {"node": parent, "children": [leaf], "descendant_count": 1, "non_element_count": 0},
            {"node": info(MULTI_HTML, dom_id="multi"), "children": [label, parent],
             "descendant_count": 3, "non_element_count": 1},
        ],
    }


class Element(runner.WebElement):
    def __init__(self, html, children=(), parent=None, failure=None, zero_error=False):
        self.html, self.kids, self.owner = html, list(children), parent
        self.failure, self.zero_error = failure, zero_error

    @property
    def id(self):
        raise AssertionError("不能以 Runtime id 判断 DOM 身份")

    def get_html(self):
        return self.html

    def parent(self, *, timeout=5.0):
        return self.owner

    def children(self, *, timeout=5.0):
        try:
            seconds = 5.0 if timeout is None else float(timeout)
        except (ValueError, TypeError) as exc:
            raise runner.InvalidParamsError("bad timeout") from exc
        if seconds < 0:
            raise runner.InvalidParamsError("negative timeout")
        if self.failure:
            raise self.failure
        if seconds == 0 and self.zero_error:
            raise runner.ActionError(SimpleNamespace(error=3, trace_info="web_dom_timeout", trace_id="zero-children"))
        return list(self.kids)


def targets():
    leaf = Element(INPUT_HTML)
    parent = Element(PARENT_HTML, [leaf])
    multi = Element(MULTI_HTML, [Element(LABEL_HTML), parent])
    leaf.owner, parent.owner = parent, multi
    return leaf, parent, multi


class ChildrenRunnerTests(unittest.TestCase):
    def test_full_matrix_valid(self):
        leaf, parent, multi = targets()
        rows = runner.run_children_cases(leaf, parent, multi, SimpleNamespace(timeout=2), oracle())
        self.assertTrue(all(row["status"] == "PASS" for row in rows), rows)

    def test_dom_order_is_checked(self):
        multi = targets()[2]
        with self.assertRaisesRegex(AssertionError, "第 1 项"):
            runner.check_children(list(reversed(multi.kids)), oracle()["ancestors"][1]["children"])

    def test_all_descendants_cannot_replace_direct_children(self):
        leaf, parent, multi = targets()
        with self.assertRaisesRegex(AssertionError, "实际 3"):
            runner.check_children(multi.kids + [leaf], oracle()["ancestors"][1]["children"])

    def test_equal_count_duplicate_child_fails(self):
        multi = targets()[2]
        with self.assertRaises(AssertionError):
            runner.check_children([multi.kids[0]] * 2, oracle()["ancestors"][1]["children"])

    def test_leaf_requires_empty_list(self):
        self.assertIn("0", runner.check_children([], []))
        for value in (None, False, targets()[0]):
            with self.subTest(kind=type(value).__name__):
                with self.assertRaises(AssertionError):
                    runner.check_children(value, [])

    def test_list_items_must_be_elements(self):
        with self.assertRaises(AssertionError):
            runner.check_children(["input"], oracle()["ancestors"][0]["children"])

    def test_zero_timeout_can_report_specific_budget_error(self):
        _, parent, _ = targets()
        parent.zero_error = True
        detail = runner.check_zero_timeout(parent, oracle()["ancestors"][0]["children"])
        self.assertIn("web_dom_timeout", detail)
        self.assertIn("未取得子元素列表", detail)

    def test_zero_timeout_other_errors_still_fail(self):
        error = runner.ActionError(SimpleNamespace(error=3, trace_info="stale_element_reference"))
        parent = Element(PARENT_HTML, failure=error)
        with self.assertRaises(runner.ActionError):
            runner.check_zero_timeout(parent, oracle()["ancestors"][0]["children"])

    def test_zero_success_with_wrong_list_still_fails(self):
        with self.assertRaises(AssertionError):
            runner.check_zero_timeout(Element(PARENT_HTML), oracle()["ancestors"][0]["children"])

    def test_positive_budget_timeout_remains_failure(self):
        leaf, parent, multi = targets()
        parent.failure = runner.ActionError(SimpleNamespace(error=3, trace_info="web_dom_timeout"))
        rows = runner.run_children_cases(leaf, parent, multi, SimpleNamespace(timeout=2), oracle())
        default = next(row for row in rows if row["case_id"] == "children_default")
        self.assertEqual(default["status"], "FAIL")

    def test_dom_oracle_requires_a_nested_multi_child_container(self):
        runner.validate_dom(oracle())
        data = oracle()
        data["ancestors"][1]["descendant_count"] = 2
        with self.assertRaises(AssertionError):
            runner.validate_dom(data)

    def test_prepared_containers_follow_native_chain(self):
        leaf, parent, multi = targets()
        self.assertEqual(runner.prepare_containers(leaf, oracle(), timeout=2), (parent, multi))
        leaf.owner = multi
        with self.assertRaises(AssertionError):
            runner.prepare_containers(leaf, oracle(), timeout=2)

    def test_prepare_failure_cleans_resources(self):
        with TemporaryDirectory() as temp:
            library = Path(temp) / "library"
            library.mkdir()
            args = SimpleNamespace(contract_only=False, library=library, temp_root=Path(temp),
                                   mode="chrome", timeout=2, element_timeout=10,
                                   runtime_timeout=20, load_timeout=20)
            package = Mock()
            with patch.object(runner.uiautoma, "open", return_value=package), \
                 patch.object(runner.web, "create", side_effect=RuntimeError("page failed")):
                rows, code = runner.run(args)
            self.assertEqual(code, 1)
            package.close.assert_called_once()
            self.assertFalse(list(Path(temp).glob("uiautoma-element-children-*")))


if __name__ == "__main__":
    unittest.main()
