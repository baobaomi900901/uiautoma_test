"""next_sibling 验收脚本的离线判据回归，不操作浏览器。"""
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

import test_web_element_next_sibling_form as runner


def info(html, tag='DIV', dom_id='', classes=''):
    return {'html': html, 'tag': tag, 'id': dom_id, 'class': classes}


INPUT = info('<input id="form-controls-ant-text">', 'INPUT', 'form-controls-ant-text')
FIRST = info('<label>输入框</label>', 'LABEL')
SECOND = info('<div>' + INPUT['html'] + '</div>')
CONTAINER = info('<section>' + FIRST['html'] + SECOND['html'] + '</section>', 'SECTION')


def oracle():
    return {
        'input': INPUT, 'leaf_children': [], 'input_next': None,
        'target_index': 0, 'multi_index': 1,
        'ancestors': [
            {'node': SECOND, 'children': [INPUT], 'next': [None],
             'descendant_count': 1, 'non_element_count': 0},
            {'node': CONTAINER, 'children': [FIRST, SECOND], 'next': [SECOND, None],
             'descendant_count': 3, 'non_element_count': 0},
        ],
    }


class Element(runner.WebElement):
    def __init__(self, html):
        self.html = html

    @property
    def id(self):
        raise AssertionError('不能以 Runtime id 代替 DOM 身份')

    def get_html(self):
        return self.html


def action_error(trace='web_dom_timeout'):
    return runner.ActionError(SimpleNamespace(error=3, trace_info=trace, trace_id='offline-only'))


class LinkedElement(Element):
    """仅给验收器提供可控的兄弟关系，不作为 SDK 行为证据。"""
    def __init__(self, html, following=None, owner=None):
        super().__init__(html)
        self.following, self.owner = following, owner

    def next_sibling(self, *, timeout=5.0):
        try:
            seconds = 5.0 if timeout is None else float(timeout)
        except (TypeError, ValueError) as exc:
            raise runner.InvalidParamsError('timeout 必须是秒数') from exc
        if seconds < 0:
            raise runner.InvalidParamsError('timeout 不能小于 0')
        return self.following

    def parent(self, *, timeout=5.0):
        return self.owner


def linked_elements():
    container = Element(CONTAINER['html'])
    second = LinkedElement(SECOND['html'], owner=container)
    first = LinkedElement(FIRST['html'], following=second, owner=container)
    target = LinkedElement(INPUT['html'], owner=second)
    return target, first, second


class NextSiblingRunnerTests(unittest.TestCase):
    def test_matrix_accepts_forward_relation_and_last_boundary(self):
        target, first, second = linked_elements()
        rows = runner.run_next_sibling_cases(target, [first, second], SimpleNamespace(timeout=2), oracle())
        self.assertEqual(len(rows), 17)
        self.assertTrue(all(row['status'] == 'PASS' for row in rows), rows)

    def test_matrix_rejects_reversed_direction(self):
        target, first, second = linked_elements()
        first.following, second.following = None, first
        rows = runner.run_next_sibling_cases(target, [first, second], SimpleNamespace(timeout=2), oracle())
        by_name = {row['case_id']: row for row in rows}
        for name in ('next_default', 'all_sibling_positions', 'last_none', 'forward_chain'):
            with self.subTest(case=name):
                self.assertEqual(by_name[name]['status'], 'FAIL')

    def test_correct_next_uses_dom_structure(self):
        self.assertIn('outerHTML', runner.check_next(Element(FIRST['html']), FIRST))

    def test_wrong_sibling_parent_or_descendant_fails(self):
        for value in (SECOND, CONTAINER, INPUT):
            with self.subTest(html=value['html']):
                with self.assertRaises(AssertionError):
                    runner.check_next(Element(value['html']), FIRST)

    def test_no_next_requires_exact_none(self):
        self.assertIn('实际 None', runner.check_next(None, None))
        for value in ([], False, 0, '', Element(FIRST['html'])):
            with self.subTest(kind=type(value).__name__):
                with self.assertRaises(AssertionError):
                    runner.check_next(value, None)

    def test_existing_next_rejects_none_or_non_element(self):
        for value in (None, [], FIRST['html']):
            with self.subTest(kind=type(value).__name__):
                with self.assertRaises(AssertionError):
                    runner.check_next(value, FIRST)

    def test_zero_budget_reports_timeout_without_claiming_successful_read(self):
        target = Mock()
        target.next_sibling.side_effect = action_error()
        detail = runner.check_zero_timeout(target, FIRST)
        self.assertIn('web_dom_timeout', detail)
        self.assertIn('未取得兄弟元素', detail)

    def test_zero_budget_rejects_other_failure(self):
        target = Mock()
        target.next_sibling.side_effect = action_error('stale_element_reference')
        with self.assertRaises(runner.ActionError):
            runner.check_zero_timeout(target, FIRST)

    def test_zero_budget_success_still_checks_node(self):
        target = Mock()
        target.next_sibling.return_value = Element(FIRST['html'])
        self.assertIn('零预算内返回兄弟元素', runner.check_zero_timeout(target, FIRST))
        target.next_sibling.return_value = None
        with self.assertRaises(AssertionError):
            runner.check_zero_timeout(target, FIRST)

    def test_normal_budget_timeout_is_failure(self):
        target = Mock()
        target.next_sibling.side_effect = action_error()
        rows = []
        runner.record_case(rows, 'next_default', lambda:
                           runner.check_next(target.next_sibling(), FIRST))
        self.assertEqual(rows[0]['status'], 'FAIL')
        self.assertIn('web_dom_timeout', rows[0]['detail'])

    def test_dom_oracle_requires_consistent_next_order(self):
        runner.validate_dom(oracle())
        data = oracle()
        data['ancestors'][1]['next'] = [None, SECOND]
        with self.assertRaises(AssertionError):
            runner.validate_dom(data)

    def test_missing_input_next_is_not_assumed_none(self):
        data = oracle()
        del data['input_next']
        with self.assertRaises(AssertionError):
            runner.validate_dom(data)

    def test_prepare_checks_each_sibling_before_api_test(self):
        container = Mock()
        container.child_at.side_effect = [Element(FIRST['html']), Element(SECOND['html'])]
        self.assertEqual(len(runner.prepare_siblings(container, oracle(), timeout=2)), 2)
        container.child_at.side_effect = [Element(SECOND['html']), Element(FIRST['html'])]
        with self.assertRaisesRegex(AssertionError, 'index=0'):
            runner.prepare_siblings(container, oracle(), timeout=2)

    def test_partial_setup_failure_cleans_owned_resources(self):
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
            self.assertFalse(list(Path(temp).glob('uiautoma-element-next-sibling-*')))


if __name__ == '__main__':
    unittest.main()
