"""六个独立查找脚本的准备逻辑与独立性回归；不连接浏览器。"""
import ast
import importlib
from pathlib import Path
import unittest

APIS = ("find", "find_all", "find_by_css", "find_all_by_css", "find_by_xpath", "find_all_by_xpath")


class Switch:
    def __init__(self, initial, after_click=(), role="switch"):
        self.initial = initial
        self.after_click = list(after_click)
        self.role = role
        self.clicks = 0

    def get_attribute(self, name):
        if name == "role":
            return self.role
        if name == "aria-checked":
            if not self.clicks or not self.after_click:
                return self.initial
            if len(self.after_click) > 1:
                return self.after_click.pop(0)
            return self.after_click[0]
        return None

    def parent(self):
        return self

    def click(self, **kwargs):
        self.clicks += 1

    def is_checked(self):
        raise AssertionError("Ant Switch 不能用 is_checked()")


class InnerSpan:
    def __init__(self, parent):
        self.owner = parent

    def get_attribute(self, name):
        return None

    def parent(self):
        return self.owner

    def is_checked(self):
        raise AssertionError("捕获的是 span，不是 checkbox")


class AncestorNode:
    def __init__(self, element_id, parent=None, dom_id=None):
        self.id = element_id
        self.owner = parent
        self.dom_id = dom_id

    def parent(self):
        return self.owner

    def get_attribute(self, name):
        return self.dom_id if name == "id" else None


class DynamicSwitchChecks:
    def test_parent_none_ends_ancestor_walk(self):
        seeds = {name: AncestorNode(name) for name in self.runner.TARGETS}
        self.assertIsNone(self.runner.find_common_root(seeds))

    def test_fixture_container_is_used_as_common_root(self):
        top = AncestorNode("top", dom_id="shadow-form-content")
        shared = AncestorNode("shared", top)
        seeds = {
            name: AncestorNode(name, AncestorNode(f"wrapper-{index}", shared))
            for index, name in enumerate(self.runner.TARGETS)
        }
        self.assertIs(self.runner.find_common_root(seeds), top)

    def test_different_runtime_ids_can_refer_to_same_dom_container(self):
        # parent() 为同一个 DOM 节点创建不同的 Runtime 对象 ID。
        roots = [AncestorNode(f"rt:web:root-{i}", dom_id="shadow-form-content") for i in range(len(self.runner.TARGETS))]
        seeds = {name: AncestorNode(name, roots[i]) for i, name in enumerate(self.runner.TARGETS)}
        self.assertIs(self.runner.find_common_root(seeds), roots[0])

    def test_all_seeds_must_reach_fixture_container(self):
        root = AncestorNode("root", dom_id="shadow-form-content")
        seeds = {name: AncestorNode(name, root) for name in self.runner.TARGETS}
        seeds[self.runner.TARGETS[-1]] = AncestorNode("outside", dom_id="other-container")
        self.assertIsNone(self.runner.find_common_root(seeds))

    def test_parent_error_is_reported(self):
        class BrokenNode(AncestorNode):
            def parent(self):
                raise RuntimeError("parent probe failed")
        seeds = {name: BrokenNode(name) for name in self.runner.TARGETS}
        with self.assertRaisesRegex(RuntimeError, "parent probe failed"):
            self.runner.find_common_root(seeds)

    def test_switch_without_parent_reports_preparation_error(self):
        with self.assertRaisesRegex(RuntimeError, 'role="switch"'):
            self.runner.disable_dynamic_ids(InnerSpan(None), timeout=0)

    def test_script_is_self_contained(self):
        source = Path(self.runner.__file__).read_text(encoding="utf-8")
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                self.assertFalse(node.level, "不得使用相对导入依赖相邻脚本")
                self.assertNotIn(node.module, ("_web_element_find_form_common",))
        self.assertTrue(callable(getattr(self.runner, f"run_{self.api}_cases", None)))
        self.assertTrue(callable(getattr(self.runner, "main", None)))

    def test_already_off_does_not_toggle_on(self):
        button = Switch("false")
        self.assertFalse(self.runner.disable_dynamic_ids(InnerSpan(button), timeout=0.5))
        self.assertEqual(button.clicks, 0)

    def test_nested_span_waits_for_state_after_one_click(self):
        button = Switch("true", ["true", "false"])
        self.assertTrue(self.runner.disable_dynamic_ids(InnerSpan(InnerSpan(button)), timeout=0.5))
        self.assertEqual(button.clicks, 1)

    def test_captured_button_also_works(self):
        button = Switch("true", ["false"])
        self.assertTrue(self.runner.disable_dynamic_ids(button, timeout=0.5))
        self.assertEqual(button.clicks, 1)

    def test_unknown_state_is_rejected_without_click(self):
        for value in (None, "", "mixed"):
            with self.subTest(value=value):
                button = Switch(value)
                with self.assertRaisesRegex(RuntimeError, "aria-checked"):
                    self.runner.disable_dynamic_ids(InnerSpan(button), timeout=0)
                self.assertEqual(button.clicks, 0)

    def test_stuck_on_is_failure_without_second_click(self):
        button = Switch("true", ["true"])
        with self.assertRaisesRegex(RuntimeError, "未关闭"):
            self.runner.disable_dynamic_ids(InnerSpan(button), timeout=0)
        self.assertEqual(button.clicks, 1)

    def test_unrelated_element_is_not_clicked(self):
        button = Switch("true", role="button")
        with self.assertRaisesRegex(RuntimeError, 'role="switch"'):
            self.runner.disable_dynamic_ids(InnerSpan(button), timeout=0)
        self.assertEqual(button.clicks, 0)


for api in APIS:
    name = f"SwitchTests_{api}"
    globals()[name] = type(name, (DynamicSwitchChecks, unittest.TestCase), {
        "runner": importlib.import_module(f"test_web_element_{api}_form"),
        "api": api,
    })


if __name__ == "__main__":
    unittest.main()
