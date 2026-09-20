"""dblclick 验收器的离线回归；不执行真实双击或读写系统剪贴板。"""
import copy
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

import test_web_element_dblclick_keys as runner


def case(**kwargs):
    return dict(kwargs={'simulative':False,'delay_after':0,**kwargs},position='center')


def events(**changes):
    base = dict(buttonId='btn-dblclick-target',button=0,keys='none',trusted=False,
                x=60,y=20,width=120,height=40)
    base.update(changes)
    return [dict(base,type=kind) for kind in ('click','click','dblclick')]


def log(**changes):
    value = dict(buttonId='btn-dblclick-target',buttonLabel='双击触发按钮',eventType='dblclick',
                 detectedKeys='none',isTrusted=False,clickSource='JS/插件模拟',time='12:00:00.123')
    return {**value,**changes}


class DblclickRunnerTests(unittest.TestCase):
    def test_chromium_internal_format_family_is_ignored_and_reported(self):
        native = runner.NativeState.__new__(runner.NativeState)
        native.ignored_formats = []
        native.EPHEMERAL_FORMAT_PREFIX = 'Chromium internal source '
        for name in ('Chromium internal source RFH token', 'Chromium internal source URL'):
            self.assertTrue(name.startswith(native.EPHEMERAL_FORMAT_PREFIX))
            native.ignored_formats.append('49943 (' + name + ')')
        self.assertEqual(len(native.ignored_formats), 2)

    def test_unknown_clipboard_format_remains_blocking(self):
        native = runner.NativeState.__new__(runner.NativeState)
        native.MEMORY_FORMATS = {1, 7, 8, 13, 15, 16, 17}
        native.NAMED_MEMORY_FORMATS = {'HTML Format'}
        native.EPHEMERAL_FORMAT_PREFIX = 'Chromium internal source '
        self.assertFalse('Unknown private format'.startswith(native.EPHEMERAL_FORMAT_PREFIX))

    def test_valid_dom_double_click_and_log(self):
        actual=runner.event_check(events(),case())
        runner.log_check(log(),actual)

    def test_real_mouse_events_require_trusted_true(self):
        runner.event_check(events(trusted=True),case(simulative=True))
        with self.assertRaises(AssertionError):
            runner.event_check(events(),case(simulative=True))

    def test_two_clicks_without_dblclick_cannot_pass(self):
        with self.assertRaisesRegex(AssertionError,'click/click/dblclick'):
            runner.event_check(events()[:2],case())

    def test_wrong_sequence_or_duplicate_double_click_fails(self):
        for items in (list(reversed(events())),events()+events(),[events()[-1]]):
            with self.subTest(items=items),self.assertRaises(AssertionError):
                runner.event_check(items,case())

    def test_every_event_must_match_target_button_and_keys(self):
        for field,value in (('buttonId','other'),('button',2),('keys','ctrl')):
            items=events()
            items[0][field]=value
            with self.subTest(field=field),self.assertRaises(AssertionError):
                runner.event_check(items,case())

    def test_changed_second_click_position_fails(self):
        items=events()
        items[1]['x']+=8
        with self.assertRaisesRegex(AssertionError,'位置不一致'):
            runner.event_check(items,case())

    def test_outside_or_invalid_geometry_fails(self):
        for changes in ({'x':-1},{'y':40},{'width':0},{'x':float('nan')}):
            with self.subTest(changes=changes),self.assertRaises(AssertionError):
                runner.event_check(events(**changes),case())

    def test_anchor_regions_and_center_are_independently_checked(self):
        runner.event_check(events(x=9,y=9),{**case(),'position':'top_left'})
        runner.event_check(events(x=111,y=31),{**case(),'position':'bottom_right'})
        with self.assertRaises(AssertionError):
            runner.event_check(events(x=9,y=9),case())

    def test_single_click_or_wrong_source_log_is_rejected(self):
        actual=events()[-1]
        for changes in ({'eventType':'click'},{'buttonId':'btn-click-target'},
                        {'isTrusted':0},{'clickSource':'真实鼠标'},{'detectedKeys':'win'}):
            with self.subTest(changes=changes),self.assertRaises(AssertionError):
                runner.log_check(log(**changes),actual)

    def test_cases_only_use_public_double_click_parameters(self):
        items=runner.dblclick_cases()
        self.assertEqual(len(items),len({item['name'] for item in items}))
        self.assertTrue(all(set(item['kwargs']) <= {'simulative','delay_after','move_mouse','anchor'} for item in items))
        self.assertEqual(set(runner.TARGETS),{'double','copy'})
        self.assertIn('dom_anchor_ignored',{item['name'] for item in items})

    def exercise(self, *, error_after=False, stale=False, overwrite=False,
                 copy_attempt=1, lose_focus=False, wrong_cursor=False):
        state=dict(events=events(),rows=[dict(key='btn-dblclick-target-dblclick-123',text='log')],
                   documentFocused=True,activeId='')
        native=Mock()
        native.window_info.return_value=dict(handle=10,pid=11,process='chrome.exe',class_name='Chrome_WidgetWin_1')
        native.held_keys.return_value=[]
        native.get_cursor.side_effect=[(0,0),(1,1)] if wrong_cursor else None
        native.get_cursor.return_value=(0,0)
        target,copier,page=Mock(),Mock(),Mock()
        copies=0
        native.read_text.side_effect=lambda:'marker' if stale or copies<copy_attempt else json.dumps(log())
        def tested(**kwargs):
            state['documentFocused']=not lose_focus
            if error_after:
                raise runner.InvalidParamsError('delay_after 不能小于 0')
        target.dblclick.side_effect=tested
        def activate():
            state['documentFocused']=True
        page.activate.side_effect=activate
        def copy_click(**kwargs):
            nonlocal copies
            self.assertTrue(state['documentFocused'])
            copies+=1
            if overwrite:
                state['rows'][0]['key']='new-log'
        copier.click.side_effect=copy_click
        item=case()
        if error_after:
            item['kwargs']['delay_after']=-1
            item['error_after']=True
        with patch.object(runner,'prepare_case',return_value='marker'), \
             patch.object(runner,'probe',side_effect=lambda *a,**kw:copy.deepcopy(state)), \
             patch.object(runner.time,'sleep'):
            try:
                detail=runner.run_dblclick_case(page,{'double':target,'copy':copier},'key',native,item,0)
            finally:
                target.dblclick.assert_called_once()
                target.click.assert_not_called()
                if wrong_cursor:
                    copier.click.assert_not_called()
        return detail,copier,page

    def test_full_scenario_uses_one_dblclick_call(self):
        detail,copier,_=self.exercise()
        self.assertIn('2 次 click + 1 次 dblclick',detail)
        copier.click.assert_called_once()

    def test_negative_delay_still_checks_completed_double_click(self):
        detail,_,_=self.exercise(error_after=True)
        self.assertIn('双击已发生后拒绝',detail)

    def test_retry_only_copies_original_log(self):
        detail,copier,_=self.exercise(copy_attempt=2)
        self.assertEqual(copier.click.call_count,2)
        self.assertIn('未重试被测双击',detail)

    def test_stale_clipboard_cannot_pass(self):
        with self.assertRaises(runner.Blocked):
            self.exercise(stale=True)

    def test_copy_cannot_replace_original_log(self):
        with self.assertRaisesRegex(AssertionError,'原日志'):
            self.exercise(overwrite=True)

    def test_focus_recovery_does_not_redo_double_click(self):
        detail,_,page=self.exercise(lose_focus=True)
        page.activate.assert_called_once()
        self.assertIn('焦点已恢复',detail)

    def test_dom_double_click_must_not_move_system_cursor(self):
        with self.assertRaisesRegex(AssertionError,'鼠标坐标'):
            self.exercise(wrong_cursor=True)

    def test_contract_only_has_no_live_resources(self):
        with patch.object(runner,'NativeState',side_effect=AssertionError('live')):
            rows=runner.run(SimpleNamespace(contract_only=True))
        self.assertEqual([item['status'] for item in rows],['PASS'])

    def test_setup_failure_still_restores_resources(self):
        with TemporaryDirectory() as directory:
            args=SimpleNamespace(contract_only=False,url=runner.URL,library=Path(directory)/'missing')
            native=Mock()
            native.captured=True
            native.capture.return_value='captured'
            native.restore.return_value='clipboard restored'
            native.restore_input.return_value='input restored'
            with patch.object(runner,'NativeState',return_value=native), \
                 patch.object(runner.web,'create',side_effect=AssertionError('must not open')):
                rows=runner.run(args)
            self.assertEqual(next(item for item in rows if item['case_id']=='library_prepare')['status'],'BLOCKED')
            native.restore.assert_called_once()
            native.restore_input.assert_called_once()

    def test_clipboard_block_happens_after_page_is_open_and_page_is_cleaned(self):
        with TemporaryDirectory() as directory:
            library=Path(directory)/'library'
            library.mkdir()
            args=SimpleNamespace(contract_only=False,url=runner.URL,library=library,
                                 temp_root=Path(directory)/'temp',mode='chrome',
                                 runtime_timeout=1,load_timeout=1,element_timeout=1,wait_timeout=1)
            native=Mock()
            native.capture.side_effect=runner.Blocked('clipboard format 49943 unsupported')
            native.restore.return_value='no clipboard mutation'
            native.captured=False
            page=Mock(spec=runner.WebBrowser)
            package=Mock()
            with patch.object(runner,'NativeState',return_value=native), \
                 patch.object(runner.uiautoma,'open',return_value=package), \
                 patch.object(runner.web,'create',return_value=page), \
                 patch.object(runner,'bind_target',return_value=Mock()), \
                 patch.object(runner,'probe',return_value=True):
                rows=runner.run(args)
            self.assertEqual(next(item for item in rows if item['case_id']=='native_state')['status'],'BLOCKED')
            page.close.assert_called_once()
            package.close.assert_called_once()
            native.restore.assert_called_once()


if __name__ == '__main__':
    unittest.main()
