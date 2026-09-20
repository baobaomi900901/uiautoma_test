"""click 验收器的离线回归；不操作浏览器、剪贴板或键鼠。"""
import copy
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

import test_web_element_click_keys as runner


def case(target='single', **kwargs):
    return dict(target=target, kwargs=dict(simulative=False, delay_after=0, **kwargs), app_type='click')


def event(target='single', **changes):
    value = dict(buttonId=runner.TARGETS[target][1], type='click', button=0, keys='none', trusted=False,
                 x=150, y=150, width=300, height=300, offsetX=45, offsetY=12)
    value.update(changes)
    return value


def log(target='single', **changes):
    value = dict(buttonId=runner.TARGETS[target][1], eventType='click', detectedKeys='none',
                 isTrusted=False, clickSource='JS/插件模拟', time='12:00:00.123')
    value.update(changes)
    return value


class ClickKeysRunnerTests(unittest.TestCase):
    def clipboard_fixture(self):
        original = {13: '原文本 😀\0'.encode('utf-16-le'), 49410: b'<b>original HTML</b>\0'}
        current = dict(original)
        native = runner.NativeState.__new__(runner.NativeState)
        native.saved = None
        native.modified = native.captured = False
        native.held_keys = lambda: []
        native.snapshot_clipboard = lambda: {fmt: bytes(data) for fmt,data in current.items()}
        def write_snapshot(data):
            current.clear()
            current.update(data)
        native.write_snapshot = Mock(side_effect=write_snapshot)
        return native, original, current

    def test_clipboard_snapshot_survives_later_overwrite_and_restores_html(self):
        native, original, current = self.clipboard_fixture()
        native.capture()
        current.clear()
        current[13] = '哨兵\0'.encode('utf-16-le')
        native.modified = True
        self.assertEqual(native.saved, original)
        native.restore()
        self.assertEqual(current, original)
        native.write_snapshot.assert_called_once_with(original)

    def test_clipboard_restore_requires_all_saved_formats(self):
        native, _, current = self.clipboard_fixture()
        native.capture()
        native.modified = True
        current.pop(49410)
        native.write_snapshot.side_effect = None
        with self.assertRaisesRegex(AssertionError, '49410'):
            native.restore()

    def test_empty_clipboard_snapshot_restores_empty(self):
        native, _, current = self.clipboard_fixture()
        current.clear()
        native.capture()
        current[13] = '哨兵\0'.encode('utf-16-le')
        native.modified = True
        native.restore()
        self.assertEqual(current, {})

    def test_accepts_matching_dom_click(self):
        actual = runner.event_check([event()], case())
        runner.log_check(log(), actual, runner.TARGETS['single'][1], 'click')

    def test_rejects_wrong_target_button_keys_or_source(self):
        for changes in ({'buttonId':'other'}, {'button':2}, {'keys':'ctrl'}, {'trusted':True}):
            with self.subTest(changes=changes), self.assertRaises(AssertionError):
                runner.event_check([event(**changes)], case())

    def test_single_click_cannot_pass_as_double_or_duplicate(self):
        for events in ([event(type='dblclick')], [event(),event()], []):
            with self.subTest(events=events), self.assertRaises(AssertionError):
                runner.event_check(events, case())

    def test_right_click_requires_contextmenu_and_right_button(self):
        right = case('right', button='right')
        runner.event_check([event('right',type='contextmenu',button=2)], right)
        with self.assertRaises(AssertionError):
            runner.event_check([event('right')], right)

    def test_grid_uses_panel_coordinates_but_offsets_use_event_target(self):
        expected = case('grid')
        expected['position'] = 'topLeft-(左上)'
        actual = event('grid',x=15,y=20,offsetX=3,offsetY=4)
        runner.event_check([actual], expected)
        record = log('grid',clickPosition='topLeft-(左上)',offsetX=3,offsetY=4)
        runner.log_check(record,actual,runner.TARGETS['grid'][1],'click')
        record['offsetX'] = 15
        with self.assertRaises(AssertionError):
            runner.log_check(record,actual,runner.TARGETS['grid'][1],'click')

    def test_wrong_grid_position_and_outside_are_rejected(self):
        expected = case('grid')
        expected['position'] = 'bottomRight-(右下)'
        with self.assertRaises(AssertionError):
            runner.event_check([event('grid',x=10,y=10)],expected)
        expected['position'] = None
        with self.assertRaises(AssertionError):
            runner.event_check([event('grid',x=301)],expected)

    def test_log_requires_exact_types_and_correct_fields(self):
        for changes in ({'buttonId':'old'}, {'eventType':'dblclick'}, {'isTrusted':0},
                        {'detectedKeys':'win'}, {'clickSource':'真实鼠标'}, {'time':''}):
            with self.subTest(changes=changes), self.assertRaises(AssertionError):
                runner.log_check(log(**changes),event(),runner.TARGETS['single'][1],'click')

    def test_focus_log_has_dash_keys_and_trusted_focus_event(self):
        actual = event('focus',type='focusin',trusted=True)
        record = log('focus',eventType='focus',detectedKeys='-',isTrusted=True,clickSource='真实鼠标')
        runner.log_check(record,actual,runner.TARGETS['focus'][1],'focus')

    def test_case_matrix_has_unique_ids_all_targets_and_both_modes(self):
        cases = runner.click_cases()
        self.assertEqual(len(cases),len({row['name'] for row in cases}))
        for target in ('single','double','right','grid','hover','focus'):
            self.assertIn(target,{row['target'] for row in cases})
        for prefix in ('mouse','dom'):
            for key in ('none','alt','ctrl','shift','win'):
                self.assertIn(prefix+'_keys_'+key,{row['name'] for row in cases})
        self.assertEqual(runner.TARGETS['copy'][1],'btn-copy-latest-keys-log')
        self.assertNotEqual(runner.TARGETS['copy'][1],runner.TARGETS['focus'][1])

    def test_no_app_log_is_expected_for_single_click_on_double_button(self):
        for row in runner.click_cases():
            if row['target']=='double':
                self.assertIsNone(row['app_type'])
        for row in runner.click_cases():
            if row['target'] in ('hover','focus') and row['kwargs'].get('simulative') is False:
                self.assertIsNone(row['app_type'])

    def test_full_case_accepts_fresh_clipboard_log(self):
        self.exercise_case()

    def test_win_focus_recovery_copies_original_record_without_reclick(self):
        target, copier, native = self.exercise_case(win=True, focused=False)
        target.click.assert_called_once()
        copier.click.assert_called_once()
        native.restore_browser_foreground.assert_called_once()

    def test_focus_recovery_rejects_replaced_original_record(self):
        with self.assertRaisesRegex(AssertionError,'原日志'):
            self.exercise_case(win=True, focused=False, change_during_recovery=True)

    def test_unrecoverable_focus_never_copies_or_reclicks(self):
        with self.assertRaisesRegex(runner.Blocked,'焦点'):
            self.exercise_case(win=True, focused=False, recover=False)

    def test_clipboard_retry_only_clicks_copy_button(self):
        target, copier, _ = self.exercise_case(copy_on_attempt=2)
        target.click.assert_called_once()
        self.assertEqual(copier.click.call_count,2)

    def test_full_case_rejects_stale_clipboard(self):
        with self.assertRaises(runner.Blocked) as caught:
            self.exercise_case(stale=True)
        self.assertIn('独立事件已核对', str(caught.exception))
        self.assertIn('document.hasFocus()', str(caught.exception))

    def test_full_case_rejects_copy_overwriting_record(self):
        with self.assertRaisesRegex(AssertionError,'覆盖'):
            self.exercise_case(overwrite=True)

    def exercise_case(self, stale=False, overwrite=False, win=False, focused=True,
                      change_during_recovery=False, recover=True, copy_on_attempt=1):
        import json
        actual_event = event(keys='win',trusted=True) if win else event()
        record = log(detectedKeys='win',isTrusted=True,clickSource='真实鼠标') if win else log()
        state = dict(events=[actual_event], rows=[dict(key='btn-click-target-click-123',text='log')],
                     activeId='',documentFocused=focused)
        native = Mock()
        native.held_keys.return_value = []
        native.window_info.return_value = dict(handle=10,pid=11,process='chrome.exe',class_name='Chrome_WidgetWin_1')
        def restore(*args,**kwargs):
            if recover:
                state['documentFocused'] = True
            if change_during_recovery:
                state['rows'][0]['key'] = 'btn-click-target-click-new'
            return 'native recovery attempted'
        native.restore_browser_foreground.side_effect = restore
        target, copier = Mock(), Mock()
        def tested_click(**kwargs):
            state['documentFocused'] = focused
        target.click.side_effect = tested_click
        copies = 0
        native.read_text.side_effect = lambda: 'sentinel' if stale or copies < copy_on_attempt else json.dumps(record)
        def copy_click(**kwargs):
            nonlocal copies
            self.assertTrue(state['documentFocused'], '复制前必须核验页面焦点')
            copies += 1
            if overwrite:
                state['rows'][0]['key'] = 'focus-target-focus-124'
        copier.click.side_effect = copy_click
        page = Mock()
        error = RuntimeError('SDK activation denied')
        error.trace_info = 'activate_tab_failed'
        page.activate.side_effect = error
        test_case = case()
        if win:
            test_case['kwargs'].update(simulative=True,keys='win')
            # 点击前聚焦，click 后才变为 requested focused 状态。
            state['documentFocused'] = True
        with patch.object(runner,'prepare_case',return_value='sentinel'), \
             patch.object(runner,'probe',side_effect=lambda *a,**kw:copy.deepcopy(state)), \
             patch.object(runner.time,'sleep'):
            try:
                runner.run_click_case(page,{'single':target,'copy':copier},'key',native,test_case,0)
            finally:
                target.click.assert_called_once()
                if not recover or change_during_recovery:
                    copier.click.assert_not_called()
        return target, copier, native

    def test_native_recovery_does_not_send_escape_to_unrelated_app(self):
        native = runner.NativeState.__new__(runner.NativeState)
        native.user = Mock()
        native.held_keys = lambda: []
        browser = dict(handle=10,pid=11,process='chrome.exe',class_name='Chrome_WidgetWin_1')
        other = dict(handle=20,pid=21,process='notepad.exe',class_name='Notepad')
        native.window_info = Mock(side_effect=lambda handle=None:browser if handle==10 else other)
        native.restore_browser_foreground(browser,allow_start_menu=True)
        native.user.keybd_event.assert_not_called()
        native.user.SetForegroundWindow.assert_called_once_with(10)

    def test_native_recovery_dismisses_only_identified_start_menu(self):
        native = runner.NativeState.__new__(runner.NativeState)
        native.user = Mock()
        native.user.GetForegroundWindow.return_value = 10
        native.held_keys = lambda: []
        browser = dict(handle=10,pid=11,process='chrome.exe',class_name='Chrome_WidgetWin_1')
        menu = dict(handle=20,pid=21,process='StartMenuExperienceHost.exe',class_name='Windows.UI.Core.CoreWindow')
        native.window_info = Mock(side_effect=lambda handle=None:browser if handle==10 else menu)
        native.restore_browser_foreground(browser,allow_start_menu=True)
        self.assertEqual(native.user.keybd_event.call_args_list,[unittest.mock.call(0x1B,0,0,0),unittest.mock.call(0x1B,0,2,0)])

    def test_native_recovery_rejects_reused_window_handle(self):
        native = runner.NativeState.__new__(runner.NativeState)
        native.user = Mock()
        original = dict(handle=10,pid=11,process='chrome.exe',class_name='Chrome_WidgetWin_1')
        native.window_info = Mock(return_value={**original,'pid':99})
        with self.assertRaises(runner.Blocked):
            native.restore_browser_foreground(original,allow_start_menu=True)
        native.user.keybd_event.assert_not_called()
        native.user.SetForegroundWindow.assert_not_called()

    def test_contract_only_never_initializes_native_state(self):
        with patch.object(runner,'NativeState',side_effect=AssertionError('live call')):
            rows=runner.run(SimpleNamespace(contract_only=True))
        self.assertEqual([row['status'] for row in rows],['PASS'])

    def test_setup_failure_still_restores_native_state(self):
        with TemporaryDirectory() as directory:
            native = Mock()
            native.captured = True
            native.capture.return_value = 'captured'
            native.restore.return_value = 'clipboard restored'
            native.restore_input.return_value = 'input restored'
            args = SimpleNamespace(contract_only=False,url=runner.URL,library=Path(directory)/'missing')
            with patch.object(runner,'NativeState',return_value=native), \
                 patch.object(runner.web,'create',side_effect=AssertionError('must not create page')):
                rows = runner.run(args)
            self.assertEqual(next(row for row in rows if row['case_id']=='library_prepare')['status'],'BLOCKED')
            native.restore.assert_called_once()
            native.restore_input.assert_called_once()

    def test_physical_win_failure_cannot_poison_later_business_cases(self):
        with TemporaryDirectory() as directory:
            library = Path(directory)/'library'
            library.mkdir()
            args = SimpleNamespace(contract_only=False,url=runner.URL,library=library,
                                   temp_root=Path(directory)/'temp',runtime_timeout=1,
                                   load_timeout=1,element_timeout=1,wait_timeout=1,mode='chrome')
            native, package = Mock(), Mock()
            page = Mock(spec=runner.WebBrowser)
            native.captured = True
            native.capture.return_value = 'captured'
            native.restore.return_value = 'restored'
            native.restore_input.return_value = 'restored'
            poisoned = False
            executed = []
            def click(*arguments):
                nonlocal poisoned
                item = arguments[-2]
                name = item.get('name', 'after_invalid')
                executed.append(name)
                if poisoned:
                    raise AssertionError('被 Win 用例污染的后续点击')
                if item['kwargs'].get('keys') == 'win' and item['kwargs'].get('simulative',True):
                    poisoned = True
                    raise runner.Blocked('模拟 Win 点击后复制受阻')
                return 'passed'
            def invalid(*arguments,**keywords):
                executed.append('invalid_parameters')
                if poisoned:
                    raise AssertionError('被 Win 用例污染的参数检查')
                return 'rejected'
            with patch.object(runner,'NativeState',return_value=native), \
                 patch.object(runner.uiautoma,'open',return_value=package), \
                 patch.object(runner.web,'create',return_value=page), \
                 patch.object(runner.web,'get_all',return_value=[]), \
                 patch.object(runner,'bind_target',return_value=Mock()), \
                 patch.object(runner,'probe',return_value=True), \
                 patch.object(runner,'run_click_case',side_effect=click), \
                 patch.object(runner,'invalid_case',side_effect=invalid):
                rows = runner.run(args)
            self.assertEqual(executed[-1], 'mouse_keys_win')
            self.assertLess(executed.index('after_invalid'), executed.index('mouse_keys_win'))
            self.assertEqual([row['case_id'] for row in rows if row['status']!='PASS'],['mouse_keys_win'])
            self.assertEqual(next(row for row in rows if row['case_id']=='dom_keys_win')['status'],'PASS')
            native.restore.assert_called_once()
            native.restore_input.assert_called_once()

    def test_activation_failure_is_blocked_before_click(self):
        page, native = Mock(), Mock()
        error = RuntimeError('activate failed')
        error.trace_info = 'activate_tab_failed'
        error.trace_id = 'offline-activation'
        page.activate.side_effect = error
        with self.assertRaises(runner.Blocked) as caught:
            runner.prepare_case(page,'key',native,'btn-click-target',1)
        self.assertIn('click() 未执行',str(caught.exception))
        self.assertIn('offline-activation',str(caught.exception))
        native.park.assert_not_called()


if __name__ == '__main__':
    unittest.main()
