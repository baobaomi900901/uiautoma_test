r"""仅测试 Win32Element.highlight(duration: float=1.0, delay_after: float=0) -> None。

API参数均可按位置/关键字传入：duration为高亮秒数，delay_after为动作后等待秒数。
当前实现duration经float转换；None使用1秒，负数/非数字被InvalidParamsError拒绝。
delay_after=None/0不等待；非法延时在高亮动作完成后才拒绝。返回None并更新last_result。
脚本参数：--non-interactive 自动复测；默认人工模式。
运行：uv run .\win32\test_win32_highlight.py [--non-interactive]
自动模式焦点恢复失败仅记录警告，不等待人工；退出码0仅表示自动检查和必要清理通过，
高亮视觉效果仍未自动验证。鼠标恢复和Package释放失败仍使退出码非0。
前置：dev运行，启用 D:\code\元素库\260902_win元素，Win32靶场已启动。
自动切换拖拽页，高亮“win32靶场_拖拽测试_可拖拽元素”，无需剪贴板。
包含2秒观察用例；请人工确认框住正确元素，结束后高亮消失。
自动检查不能代替视觉验收，通过后仍等待测试者确认再更新证据。
保持靶场及鼠标不动；结束恢复鼠标/前台并关闭借用Package，保留拖拽页。
自动恢复前台失败时，允许30秒内手动切回原终端窗口；无需按Enter，脚本核对句柄后继续。
未恢复或原窗口失效仍判清理失败；日志区分自动恢复与人工恢复。
复用get_value的DPI/日志/清理辅助，以及get_anchor_position的原生目标定位。
"""

import inspect
import argparse
import time
import ctypes
import json
from ctypes import wintypes
from pathlib import Path
import test_win32_get_value as helper
from test_win32_get_anchor_position import native_target
from uiautoma import current, win32, InvalidParamsError
from uiautoma.win32 import Win32Element

LIBRARY=Path(r'D:\code\元素库\260902_win元素')
TARGET='win32靶场_拖拽测试_可拖拽元素'


def focus_api():
    user32 = ctypes.WinDLL('user32', use_last_error=True)
    for name in ('IsWindow', 'IsWindowVisible', 'IsIconic', 'SetForegroundWindow'):
        func = getattr(user32, name)
        func.argtypes = [wintypes.HWND]
        func.restype = wintypes.BOOL
    user32.GetForegroundWindow.argtypes = []
    user32.GetForegroundWindow.restype = wintypes.HWND
    user32.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
    user32.GetWindowThreadProcessId.restype = wintypes.DWORD
    for name in ('GetWindowTextW', 'GetClassNameW'):
        func = getattr(user32, name)
        func.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
        func.restype = ctypes.c_int
    return user32


def window_info(user32, handle):
    info = {'handle': int(handle or 0), 'valid': bool(user32.IsWindow(handle))}
    if info['valid']:
        pid = wintypes.DWORD()
        tid = user32.GetWindowThreadProcessId(handle, ctypes.byref(pid))
        title, clazz = ctypes.create_unicode_buffer(512), ctypes.create_unicode_buffer(256)
        user32.GetWindowTextW(handle, title, len(title))
        user32.GetClassNameW(handle, clazz, len(clazz))
        info.update(title=title.value, class_name=clazz.value, pid=pid.value, tid=tid,
                    visible=bool(user32.IsWindowVisible(handle)), minimized=bool(user32.IsIconic(handle)))
    return info


def restore_foreground_diagnostic(handle, *, allow_manual=True):
    """自动恢复失败时，等待用户切回原窗口，并以实际前台句柄验收。"""
    user32 = focus_api()
    target = window_info(user32, handle)
    before = window_info(user32, user32.GetForegroundWindow())
    print('  焦点恢复目标: ' + json.dumps(target, ensure_ascii=False), flush=True)
    print('  恢复前的前台: ' + json.dumps(before, ensure_ascii=False), flush=True)
    if not target['valid']:
        raise RuntimeError(f'原前台窗口已失效，无法恢复：{handle}')
    accepted = bool(user32.SetForegroundWindow(handle))
    print(f'  SetForegroundWindow 返回: {accepted}', flush=True)
    # 此API不承诺GetLastError有效，不将残留错误码当作失败原因。
    started = time.perf_counter()
    last = before['handle']
    while True:
        actual = int(user32.GetForegroundWindow() or 0)
        if actual != last:
            print(f'  前台变化 +{(time.perf_counter()-started)*1000:.1f}ms: '
                  + json.dumps(window_info(user32, actual), ensure_ascii=False), flush=True)
            last = actual
        if actual == handle:
            print('  焦点恢复确认: 自动恢复成功', flush=True)
            return
        if time.perf_counter() - started >= 1.0:
            break
        time.sleep(0.02)
    final = window_info(user32, actual)
    print('  等待后的前台: ' + json.dumps(final, ensure_ascii=False), flush=True)
    if not allow_manual:
        raise RuntimeError(f'自动恢复失败：目标前台={handle}；实际前台={actual}；切换返回={accepted}')
    print(f"  [需要人工恢复] 请在30秒内手动切回原终端窗口：{target.get('title', '')}（句柄 {handle}）。", flush=True)
    print('  无需按Enter；检测到原窗口成为前台后自动继续。', flush=True)
    deadline = time.monotonic() + 30
    while time.monotonic() < deadline:
        if not user32.IsWindow(handle):
            raise RuntimeError(f'等待人工恢复期间原窗口已失效：{handle}')
        actual = int(user32.GetForegroundWindow() or 0)
        if actual == handle:
            print('  焦点恢复确认: 人工恢复成功（已核对前台句柄）', flush=True)
            return
        time.sleep(0.1)
    raise RuntimeError(f'人工恢复超时，原前台窗口未恢复：{handle}；实际前台={actual}')


def restore_focus_for_mode(handle, non_interactive):
    try:
        restore_foreground_diagnostic(handle, allow_manual=not non_interactive)
    except Exception as exc:
        if not non_interactive:
            raise
        print(f'  [警告] 焦点未恢复：{exc}；自动模式继续，不等待人工。', flush=True)
        return '未恢复（警告，不影响API检查和必要清理判定）'
    return '已恢复（已核对前台句柄）'


def parse_run_options():
    parser = argparse.ArgumentParser(description='Win32 API 实时测试；默认允许人工恢复焦点')
    parser.add_argument('--non-interactive', action='store_true',
                        help='不等待人工恢复焦点，失败仅警告；仍需已登录的可交互Windows桌面')
    return parser.parse_args()


def contract():
    sig=inspect.signature(Win32Element.highlight)
    assert list(sig.parameters)==['self','duration','delay_after'],sig
    for name,value in [('duration',1.0),('delay_after',0)]:
        p=sig.parameters[name]
        assert p.kind==p.POSITIONAL_OR_KEYWORD and p.default==value,sig
    assert sig.return_annotation in (None,'None',type(None)),sig
    return '两个公开参数、默认值和位置/关键字规则符合合同'


def main(non_interactive=False):
    print('UIAutoma Win32 Element API 测试\n')
    print(f'  API     : Win32Element.highlight\n  目标    : {TARGET}\n  DPI 模式: {helper.DPI_AWARENESS_MODE}')
    print('  模式: ' + ('自动复测；视觉效果未自动验证' if non_interactive else '人工测试；请观察高亮覆盖和消失'))
    results=[helper.run_case('API 合同',contract)]
    package=element=hwnd=None
    focus_status='未检查'
    mouse,foreground=helper.current_cursor(),helper.current_foreground()
    print('  初始前台记录: ' + json.dumps(window_info(focus_api(),foreground),ensure_ascii=False),flush=True)
    started=time.perf_counter()

    def prepare():
        nonlocal package,element,hwnd
        package=current(required=True,refresh=True,timeout=5)
        assert Path(package.package_dir).resolve()==LIBRARY.resolve(),package.package_dir
        window=win32.get(title='Win32 靶场 - UIA',process_name='win32-shooting-range-uia.exe',timeout=5)
        window.find(package.selector('win32靶场_tab_item拖拽测试',kind='win'),timeout=5).click(delay_after=0.2)
        element=window.find(package.selector(TARGET,kind='win'),timeout=5)
        hwnd=native_target(window.get_detail('handle'))
        return '拖拽页和高亮目标已就绪',[f'原生物理边界: {helper.window_rect(hwnd,helper._user32())}']

    def call(args=(),kwargs=None,error=None,acted=True):
        kwargs=kwargs or {}
        before=helper.window_rect(hwnd,helper._user32())
        old=element.last_result
        bound=inspect.signature(Win32Element.highlight).bind(element,*args,**kwargs)
        bound.apply_defaults()
        params=bound.arguments
        print(f'  执行: highlight{args!r} {kwargs!r}',flush=True)
        begin=time.perf_counter()
        caught=None
        returned=None
        try:
            returned=element.highlight(*args,**kwargs)
        except Exception as exc:
            caught=exc
        elapsed=(time.perf_counter()-begin)*1000
        if error:
            assert isinstance(caught,error),f'预期{error.__name__}，实际{caught!r}'
        elif caught:
            raise caught
        else:
            assert returned is None,returned
        assert helper.window_rect(hwnd,helper._user32())==before,'高亮期间目标窗口边界发生变化'
        if acted:
            assert element.last_result is not old and element.last_result is not None,'last_result未更新'
            element.last_result.raise_for_error()
            duration=1 if params['duration'] is None else float(params['duration'])
            assert elapsed+30>=duration*1000,f'持续时间不足: {elapsed:.1f}ms'
        else:
            assert element.last_result is old,'非法duration触发了动作'
        return elapsed

    def positive(args=(),kwargs=None):
        elapsed=call(args,kwargs)
        return '返回None、动作结果成功、目标边界不变，持续时间检查通过',[f'调用耗时: {elapsed:.1f}ms；视觉效果请人工确认']

    def delay_pair():
        baseline=call(kwargs=dict(duration=0.3,delay_after=0))
        delayed=call(kwargs=dict(duration=0.3,delay_after=0.3))
        delta=delayed-baseline
        assert 200<=delta<=500,f'预期增加约300ms，实际差值{delta:.1f}ms；系统忙时请复测'
        return '配对调用确认动作后延时生效',[f'基线{baseline:.1f}ms；延时调用{delayed:.1f}ms；差值{delta:.1f}ms']

    def invalid(kwargs,acted):
        elapsed=call(kwargs=kwargs,error=InvalidParamsError,acted=acted)
        return ('高亮结束后非法延时被拒绝' if acted else '非法duration在动作前被拒绝'),[f'调用耗时: {elapsed:.1f}ms']

    try:
        results.append(helper.run_case('测试目标',prepare))
        if all(r.passed for r in results):
            for name,args,kwargs in [('默认高亮',(),{}),('两秒观察',(2,0),{}),
                ('全关键字',(),dict(duration=0.4,delay_after=0)),('零时长',(),dict(duration=0,delay_after=0)),
                ('None延时',(),dict(duration=0.3,delay_after=None)),('None时长',(),dict(duration=None)),
                ('数字文本时长',(),dict(duration='0.3'))]:
                results.append(helper.run_case(name,lambda a=args,k=kwargs:positive(a,k)))
            results.append(helper.run_case('动作后延时',delay_pair))
            for name,kwargs,acted in [('负数时长',dict(duration=-1),False),('非数字时长',dict(duration='invalid'),False),
                                     ('负数延时',dict(duration=0.2,delay_after=-1),True),
                                     ('非数字延时',dict(duration=0.2,delay_after='invalid'),True)]:
                results.append(helper.run_case(name,lambda k=kwargs,a=acted:invalid(k,a)))
    finally:
        def cleanup():
            errors=[]
            def restore_focus():
                nonlocal focus_status
                focus_status=restore_focus_for_mode(foreground,non_interactive)
            # 人工切窗可能移动鼠标，因此在焦点恢复结束后再恢复鼠标位置。
            actions=[('前台',restore_focus),('鼠标',lambda:helper.restore_cursor(mouse))]
            if package is not None: actions.append(('Package',package.close))
            for name,action in actions:
                try: action()
                except Exception as exc: errors.append(f'{name}: {exc}')
            if errors: raise RuntimeError('；'.join(errors))
            return '鼠标已恢复，Package已关闭（如已取得）',[f'焦点: {focus_status}；视觉效果未自动验证']
        results.append(helper.run_case('资源清理',cleanup))
        helper.render_results(results)
    passed=sum(r.passed for r in results)
    ok=passed==len(results)
    print(helper.colored('\n自动检查通过' if ok else '\n测试失败',helper.ANSI_GREEN if ok else helper.ANSI_RED))
    print(f'  生命周期: READY_FOR_LIVE\n  结果    : {passed}/{len(results)} 通过')
    print(f'  总耗时  : {(time.perf_counter()-started)*1000:.1f}ms\n  退出码  : {0 if ok else 1}')
    print(f'  焦点恢复: {focus_status}')
    print('  视觉效果: 未自动验证' if non_interactive else '  人工确认: 高亮框是否包围正确元素，并在结束后消失？')
    return 0 if ok else 1


if __name__=='__main__':
    raise SystemExit(main(non_interactive=parse_run_options().non_interactive))
