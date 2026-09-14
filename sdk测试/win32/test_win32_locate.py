r"""Win32Element.locate(*, timeout: float=3.0) -> LocateResult。

API参数：timeout仅限关键字，默认3秒；0单次、正数有限等待；None使用3秒，数字字符串可转换。
负数（含-1）和非数字被InvalidParamsError拒绝。高层源码未写返回注解，实际返回LocateResult。
结果字段：found(bool)、rect(dict或None)、strategy/trace_info/fallback_reason(str)、raw(dict)。
脚本参数：--non-interactive 焦点恢复失败只警告、不等待人工；默认人工模式。
运行：uv run .\win32\test_win32_locate.py --non-interactive
前置：dev、Win32靶场运行，启用 D:\code\元素库\260902_win元素。
切换拖拽页，读取目标；隐藏按钮实际销毁目标，重置按钮重新创建，最后确保目标恢复。
重置恢复靶场默认位置，不恢复自定义拖拽位置；不使用剪贴板，不关闭靶场。
复用现有DPI、原生边界、焦点及日志辅助。未验证等待过程中动态重现或旧对象自动重绑定。
"""

import inspect
import time
from pathlib import Path
import test_win32_get_value as helper
from test_win32_get_anchor_position import native_target
from test_win32_highlight import restore_focus_for_mode, parse_run_options, focus_api
from uiautoma import current, win32, InvalidParamsError, LocateResult
from uiautoma.win32 import Win32Element

TARGET='win32靶场_拖拽测试_可拖拽元素'


def contract():
    sig=inspect.signature(Win32Element.locate)
    assert list(sig.parameters)==['self','timeout'],sig
    p=sig.parameters['timeout']
    assert p.kind==p.KEYWORD_ONLY and p.default==3.0,sig
    return 'timeout默认3秒且仅限关键字；返回类型在实际调用中检查'


def validate_result(result, found, expected_rect=None):
    assert isinstance(result,LocateResult),type(result)
    assert type(result.found) is bool and result.found is found,f'预期found={found}，实际{result.found!r}；诊断{result.trace_info}'
    assert all(isinstance(getattr(result,k),str) for k in ('strategy','trace_info','fallback_reason')),result
    assert isinstance(result.raw,dict),type(result.raw)
    if found:
        assert isinstance(result.rect,dict),result.rect
        values=tuple(result.rect[k] for k in ('x','y','w','h'))
        assert all(type(v) is int for v in values),values
        assert values==expected_rect,f'原生边界{expected_rect}，SDK边界{values}'
        assert result.strategy,'成功定位没有策略信息'
    else:
        assert result.rect is None,'未找到时仍返回旧边界'
    return f'found={result.found}；rect={result.rect}；strategy={result.strategy}；trace={result.trace_info}'


def main(non_interactive=False):
    print('UIAutoma Win32 Element API 测试\n  API: Win32Element.locate')
    print(f'  目标: {TARGET}\n  原生参照: IsWindow / GetWindowRect\n  模式: '+('自动复测' if non_interactive else '人工测试'))
    results=[helper.run_case('API 合同',contract)]
    package=window=element=hwnd=hide=reset=None
    needs_restore=False
    focus_status='未检查'
    mouse,foreground=helper.current_cursor(),helper.current_foreground()
    started=time.perf_counter()

    def prepare():
        nonlocal package,window,element,hwnd,hide,reset
        package=current(required=True,refresh=True,timeout=5)
        assert Path(package.package_dir).resolve()==Path(r'D:\code\元素库\260902_win元素').resolve()
        window=win32.get(title='Win32 靶场 - UIA',process_name='win32-shooting-range-uia.exe',timeout=5)
        def find(name): return window.find(package.selector(name,kind='win'),timeout=5)
        find('win32靶场_tab_item拖拽测试').click(delay_after=0.2)
        hide=find('win32靶场_拖拽测试_隐藏_drag-target')
        reset=find('win32靶场_拖拽测试_重置位置')
        element=find(TARGET)
        hwnd=native_target(window.get_detail('handle'))
        assert focus_api().IsWindow(hwnd),'原生目标不存在'
        return '定位对象与原生目标准备完成',[f'目标句柄: {hwnd}']

    def observe(kwargs,found=True):
        assert bool(focus_api().IsWindow(hwnd)) is found,'原生存在状态与场景不符'
        bounds=helper.window_rect(hwnd,helper._user32()) if found else None
        old=element.last_result
        result=element.locate(**kwargs)
        detail=validate_result(result,found,bounds)
        assert element.last_result is old,'locate改变last_result'
        assert bool(focus_api().IsWindow(hwnd)) is found,'调用期间原生存在状态变化'
        if found:
            assert helper.window_rect(hwnd,helper._user32())==bounds,'调用期间窗口边界变化'
        return 'LocateResult类型、状态和边界符合预期',[detail,f'调用: locate(**{kwargs!r})']

    def repeated():
        for _ in range(3): observe(dict(timeout=0))
        return '连续三次定位成功，返回边界与原生一致'

    def rejected(calls,error):
        old=element.last_result
        for call in calls:
            try: call()
            except error: pass
            else: raise AssertionError(f'未抛出{error.__name__}')
        assert element.last_result is old,'非法调用改变last_result'
        return f'{error.__name__}正确拒绝'

    def remove():
        nonlocal needs_restore
        needs_restore=True
        hide.click(delay_after=0.1)
        deadline=time.monotonic()+2
        while focus_api().IsWindow(hwnd) and time.monotonic()<deadline: time.sleep(0.02)
        assert not focus_api().IsWindow(hwnd),'原句柄未失效，不能检查未找到'
        return '已销毁目标，原生确认原句柄失效；保留原SDK对象'

    def restore():
        nonlocal needs_restore,element,hwnd
        if not needs_restore: return '无需重建'
        reset.click(delay_after=0.1)
        hwnd=native_target(window.get_detail('handle'))
        element=window.find(package.selector(TARGET,kind='win'),timeout=5)
        result=observe(dict(timeout=0))
        needs_restore=False
        return result

    try:
        results.append(helper.run_case('测试目标',prepare))
        if all(r.passed for r in results):
            for name,kwargs in [('默认超时',{}),('零超时',dict(timeout=0)),('有限超时',dict(timeout=0.5)),
                                ('None超时',dict(timeout=None)),('数字字符串',dict(timeout='0.5'))]:
                results.append(helper.run_case(name,lambda k=kwargs:observe(k)))
            results.append(helper.run_case('重复定位',repeated))
            results.append(helper.run_case('负数超时',lambda:rejected([lambda:element.locate(timeout=-1),lambda:element.locate(timeout=-2)],InvalidParamsError)))
            results.append(helper.run_case('非法超时',lambda:rejected([lambda:element.locate(timeout='invalid')],InvalidParamsError)))
            results.append(helper.run_case('禁止位置参数',lambda:rejected([lambda:element.locate(0)],TypeError)))
            removed=helper.run_case('销毁目标',remove)
            results.append(removed)
            if removed.passed:
                results.append(helper.run_case('未找到零超时',lambda:observe(dict(timeout=0),False)))
                results.append(helper.run_case('未找到有限超时',lambda:observe(dict(timeout=0.3),False)))
            results.append(helper.run_case('重建后定位',restore))
    finally:
        def cleanup():
            nonlocal focus_status
            errors=[]
            def focus():
                nonlocal focus_status
                focus_status=restore_focus_for_mode(foreground,non_interactive)
            actions=[('重建目标',restore),('前台',focus),('鼠标',lambda:helper.restore_cursor(mouse))]
            if package is not None: actions.append(('Package',package.close))
            for name,action in actions:
                try: action()
                except Exception as exc: errors.append(f'{name}: {exc}')
            if errors: raise RuntimeError('；'.join(errors))
            return '目标恢复（如曾销毁）、鼠标恢复及连接清理完成',[f'焦点: {focus_status}']
        results.append(helper.run_case('资源清理',cleanup))
        helper.render_results(results)
    passed=sum(r.passed for r in results)
    ok=passed==len(results)
    print(helper.colored('\n本轮检查通过' if ok else '\n测试失败',helper.ANSI_GREEN if ok else helper.ANSI_RED))
    print(f'  生命周期: READY_FOR_LIVE\n  结果: {passed}/{len(results)} 通过\n  总耗时: {(time.perf_counter()-started)*1000:.1f}ms\n  退出码: {0 if ok else 1}\n  焦点: {focus_status}')
    return 0 if ok else 1


if __name__=='__main__':
    raise SystemExit(main(non_interactive=parse_run_options().non_interactive))
