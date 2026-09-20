"""child_at 验收脚本的离线判据回归，不代表浏览器实测通过。"""
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

import test_web_element_child_at_form as runner


def info(html, tag='DIV', dom_id='', classes=''):
    return {'html': html, 'tag': tag, 'id': dom_id, 'class': classes}


FIRST = info('<label>输入框</label>', 'LABEL')
SECOND = info('<div><input id="form-controls-ant-text"></div>')


class Element(runner.WebElement):
    def __init__(self, html):
        self.html = html

    @property
    def id(self):
        raise AssertionError('判据不得使用 Runtime id')

    def get_html(self):
        return self.html


def timeout_error(trace='web_dom_timeout'):
    return runner.ActionError(SimpleNamespace(error=3, trace_info=trace, trace_id='offline-only'))


class ChildAtRunnerTests(unittest.TestCase):
    def test_correct_child_uses_dom_structure(self):
        self.assertIn('outerHTML', runner.check_child(Element(FIRST['html']), FIRST, 0))

    def test_wrong_index_child_is_rejected(self):
        with self.assertRaises(AssertionError):
            runner.check_child(Element(SECOND['html']), FIRST, 0)

    def test_nested_descendant_cannot_replace_direct_child(self):
        descendant = Element('<input id="form-controls-ant-text">')
        with self.assertRaises(AssertionError):
            runner.check_child(descendant, SECOND, 1)

    def test_missing_child_requires_exact_none(self):
        self.assertIn('实际 None', runner.check_child(None, None, -1))
        for value in ([], False, 0, '', Element(FIRST['html'])):
            with self.subTest(value=type(value).__name__):
                with self.assertRaises(AssertionError):
                    runner.check_child(value, None, 2)

    def test_expected_child_rejects_none_and_wrong_types(self):
        for value in (None, [], FIRST['html']):
            with self.subTest(value=value):
                with self.assertRaises(AssertionError):
                    runner.check_child(value, FIRST, 0)

    def test_zero_budget_reports_timeout_without_claiming_read_success(self):
        container = Mock()
        container.child_at.side_effect = timeout_error()
        detail = runner.check_zero_timeout(container, FIRST)
        self.assertIn('未取得子元素', detail)
        self.assertIn('web_dom_timeout', detail)

    def test_zero_budget_rejects_unrelated_error(self):
        container = Mock()
        container.child_at.side_effect = timeout_error('stale_element_reference')
        with self.assertRaises(runner.ActionError):
            runner.check_zero_timeout(container, FIRST)

    def test_zero_budget_still_requires_correct_element(self):
        container = Mock()
        container.child_at.return_value = Element(FIRST['html'])
        self.assertIn('零预算内返回子元素', runner.check_zero_timeout(container, FIRST))
        container.child_at.return_value = None
        with self.assertRaises(AssertionError):
            runner.check_zero_timeout(container, FIRST)

    def test_normal_budget_timeout_is_failure_and_preserves_trace(self):
        container = Mock()
        container.child_at.side_effect = timeout_error()
        rows = []
        runner.record_case(rows, 'child_at_default', lambda:
                           runner.check_child(container.child_at(0), FIRST, 0))
        self.assertEqual(rows[0]['status'], 'FAIL')
        self.assertIn('web_dom_timeout', rows[0]['detail'])

    def test_expected_parameter_error_cannot_hide_other_errors(self):
        action = Mock(side_effect=timeout_error())
        with self.assertRaises(AssertionError):
            runner.expect_exception(action, runner.InvalidParamsError)

    def test_partial_setup_failure_still_cleans_owned_resources(self):
        with TemporaryDirectory() as temp:
            library = Path(temp) / 'library'
            library.mkdir()
            args = SimpleNamespace(contract_only=False, library=library, temp_root=Path(temp),
                                   mode='chrome', timeout=2, element_timeout=10,
                                   runtime_timeout=20, load_timeout=20)
            package = Mock()
            with patch.object(runner.uiautoma, 'open', return_value=package), \
                 patch.object(runner.web, 'create', side_effect=RuntimeError('page failed')):
                rows, code = runner.run(args)
            self.assertEqual(code, 1)
            self.assertEqual(next(row for row in rows if row['case_id'] == 'page_prepare')['status'], 'FAIL')
            package.close.assert_called_once()
            self.assertFalse(list(Path(temp).glob('uiautoma-element-child-at-*')))


if __name__ == '__main__':
    unittest.main()
