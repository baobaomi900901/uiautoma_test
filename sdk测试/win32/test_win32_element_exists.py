r"""Win32Element.exists(*, timeout: float=3.0) -> bool，区别于win32.exists(window)。

API参数：timeout仅限关键字，默认3秒；0单次检查，正数有限等待。
当前SDK None使用3秒、数字字符串可转换；负数（包括-1）和非数字抛InvalidParamsError。
返回bool。覆盖现存True、按钮销毁后原对象False、重置重建后新对象True。
脚本参数：--non-interactive 焦点恢复失败只警告，不等待人工；默认允许手动切回Tabby。
运行：uv run .\win32\test_win32_element_exists.py --non-interactive
前置：dev、Win32靶场运行，启用 D:\code\元素库\260902_win元素。
自动切换拖拽页；原生确认drag-target存在。测试期间保持窗口和鼠标不动。
点击“win32靶场_拖拽测试_隐藏_drag-target”销毁目标控件；“重置位置”重新创建。
不关闭靶场、不使用剪贴板。结束确保目标已重建，恢复鼠标/前台、释放Package。
重置将目标恢复到靶场默认位置，不恢复测试前自定义拖拽位置。
复用highlight的运行模式和焦点辅助，以及get_anchor_position的原生目标定位。
"""

import inspect
import time
from pathlib import Path
import test_win32_get_value as helper
from test_win32_get_anchor_position import native_target
from test_win32_highlight import restore_focus_for_mode, parse_run_options, focus_api
from uiautoma import current, win32, InvalidParamsError
from uiautoma.win32 import Win32Element


def contract():
    sig=inspect.signature(Win32Element.exists)
    assert list(sig.parameters)==['self','timeout'],sig
    p=sig.parameters['timeout']
    assert p.kind==p.KEYWORD_ONLY and p.default==3.0,sig
    assert str(sig.return_annotation) in ('bool',"<class 'bool'>"),sig
    return 'timeout默认3秒且仅限关键字，返回bool'


def main(non_interactive=False):
    print('UIAutoma Win32 Element API 测试\n  API: Win32Element.exists')
    print('  目标: win32靶场_拖拽测试_可拖拽元素\n  覆盖: 存在True → 销毁后原对象False → 重建后新对象True')
    print('  模式: '+('自动复测' if non_interactive else '人工测试'))
    results=[helper.run_case('API 合同',contract)]
    package=element=hwnd=None
    window=hide_button=reset_button=None
    needs_restore=False
    mouse,foreground=helper.current_cursor(),helper.current_foreground()
    focus_status='未检查'
    started=time.perf_counter()

    def prepare():
        nonlocal package,element,hwnd,window,hide_button,reset_button
        package=current(required=True,refresh=True,timeout=5)
        assert Path(package.package_dir).resolve()==Path(r'D:\code\元素库\260902_win元素').resolve()
        window=win32.get(title='Win32 靶场 - UIA',process_name='win32-shooting-range-uia.exe',timeout=5)
        window.find(package.selector('win32靶场_tab_item拖拽测试',kind='win'),timeout=5).click(delay_after=0.2)
        hide_button=window.find(package.selector('win32靶场_拖拽测试_隐藏_drag-target',kind='win'),timeout=5)
        reset_button=window.find(package.selector('win32靶场_拖拽测试_重置位置',kind='win'),timeout=5)
        element=window.find(package.selector('win32靶场_拖拽测试_可拖拽元素',kind='win'),timeout=5)
        hwnd=native_target(window.get_detail('handle'))
        assert focus_api().IsWindow(hwnd), '原生目标句柄无效'
        return 'SDK元素已定位，原生窗口存在',[f'目标句柄: {hwnd}']

    def present(kwargs):
        assert focus_api().IsWindow(hwnd),'测试目标已关闭'
        before=helper.window_rect(hwnd,helper._user32())
        old=element.last_result
        returned=element.exists(**kwargs)
        assert type(returned) is bool and returned is True,f'预期True，实际{returned!r}'
        assert focus_api().IsWindow(hwnd),'读取期间目标已关闭'
        assert helper.window_rect(hwnd,helper._user32())==before,'目标位置发生变化'
        assert element.last_result is old,'exists意外更新last_result'
        return '返回True，与原生存在状态一致，边界和last_result不变',[f'调用: element.exists(**{kwargs!r})']

    def repeated():
        for _ in range(3): present(dict(timeout=0))
        return '连续三次返回True，原生窗口保持存在'

    def rejected(calls,error):
        old=element.last_result
        for invoke in calls:
            try: invoke()
            except error: pass
            else: raise AssertionError(f'没有抛出{error.__name__}')
        assert element.last_result is old,'非法调用改变last_result'
        return f'{error.__name__}正确拒绝，last_result未改变'

    def remove_target():
        nonlocal needs_restore
        assert focus_api().IsWindow(hwnd),'移除前目标已不存在'
        needs_restore=True  # 即使点击返回错误，也要尝试恢复场景。
        hide_button.click(delay_after=0.1)
        deadline=time.monotonic()+2
        while focus_api().IsWindow(hwnd) and time.monotonic()<deadline:
            time.sleep(0.02)
        assert not focus_api().IsWindow(hwnd),'隐藏按钮未销毁原生目标，不能进入False用例'
        return '隐藏按钮已销毁控件，IsWindow确认原句柄失效',[f'原句柄: {hwnd}；沿用原SDK元素对象']

    def absent(timeout):
        assert not focus_api().IsWindow(hwnd),'原句柄重新有效，缺失场景不成立'
        old=element.last_result
        begin=time.perf_counter()
        returned=element.exists(timeout=timeout)
        elapsed=(time.perf_counter()-begin)*1000
        assert type(returned) is bool and returned is False,f'预期False，实际{returned!r}'
        assert not focus_api().IsWindow(hwnd),'查询期间原句柄重新有效'
        assert element.last_result is old,'读取改变last_result'
        return '原生控件已销毁，原element.exists返回False',[f'timeout={timeout}；调用耗时{elapsed:.1f}ms']

    def restore_target():
        nonlocal needs_restore,element,hwnd
        if not needs_restore:
            return '无需重建目标'
        reset_button.click(delay_after=0.1)
        fresh_hwnd=native_target(window.get_detail('handle'))
        assert focus_api().IsWindow(fresh_hwnd),'重置后目标句柄无效'
        fresh=window.find(package.selector('win32靶场_拖拽测试_可拖拽元素',kind='win'),timeout=5)
        returned=fresh.exists(timeout=0)
        assert returned is True,'重建后的新元素未返回True'
        element,hwnd=fresh,fresh_hwnd
        needs_restore=False
        return '重置已重建目标，重新获取的元素exists返回True',[f'重建句柄: {hwnd}（不要求句柄数值不同）']

    try:
        results.append(helper.run_case('测试目标',prepare))
        if all(r.passed for r in results):
            for name,kwargs in [('默认超时',{}),('零超时',dict(timeout=0)),('有限超时',dict(timeout=0.5)),
                                ('None超时',dict(timeout=None)),('数字字符串',dict(timeout='0.5'))]:
                results.append(helper.run_case(name,lambda k=kwargs:present(k)))
            results.append(helper.run_case('重复读取',repeated))
            results.append(helper.run_case('负数超时',lambda:rejected([
                lambda:element.exists(timeout=-1),lambda:element.exists(timeout=-2)],InvalidParamsError)))
            results.append(helper.run_case('非数字超时',lambda:rejected([
                lambda:element.exists(timeout='invalid')],InvalidParamsError)))
            results.append(helper.run_case('禁止位置参数',lambda:rejected([
                lambda:element.exists(0)],TypeError)))
            removed=helper.run_case('移除目标',remove_target)
            results.append(removed)
            if removed.passed:
                results.append(helper.run_case('移除后零超时',lambda:absent(0)))
                results.append(helper.run_case('移除后有限超时',lambda:absent(0.3)))
            results.append(helper.run_case('重建后存在',restore_target))
    finally:
        def cleanup():
            nonlocal focus_status
            errors=[]
            def restore_focus():
                nonlocal focus_status
                focus_status=restore_focus_for_mode(foreground,non_interactive)
            actions=[('重建目标',restore_target),('前台',restore_focus),('鼠标',lambda:helper.restore_cursor(mouse))]
            if package is not None: actions.append(('Package',package.close))
            for name,action in actions:
                try: action()
                except Exception as exc: errors.append(f'{name}: {exc}')
            if errors: raise RuntimeError('；'.join(errors))
            return '目标恢复完成（如曾移除），鼠标已恢复，Package已释放；靶场保持运行',[f'焦点: {focus_status}']
        results.append(helper.run_case('资源清理',cleanup))
        helper.render_results(results)
    passed=sum(r.passed for r in results)
    ok=passed==len(results)
    print(helper.colored('\n本轮检查通过' if ok else '\n测试失败',helper.ANSI_GREEN if ok else helper.ANSI_RED))
    print(f"  生命周期: READY_FOR_LIVE\n  结果: {passed}/{len(results)} 通过\n  总耗时: {(time.perf_counter()-started)*1000:.1f}ms\n  退出码: {0 if ok else 1}")
    print(f'  焦点: {focus_status}\n  范围: 原控件销毁后检查False；重建后重新获取对象检查True，不要求旧对象自动绑定新控件')
    return 0 if ok else 1


if __name__=='__main__':
    raise SystemExit(main(non_interactive=parse_run_options().non_interactive))
