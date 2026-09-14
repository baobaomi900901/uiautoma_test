r"""win32.get_list(title=None, *, class_name=None, process_name=None,
use_wildcard=False, timeout=5) -> list[Win32Window]。

用途：批量获取符合过滤条件的顶层窗口。title可位置/关键字；其他参数仅限关键字。
支持标题/进程名片段及*、?通配符；timeout=0单次、正数有限等待、-1无限等待。
本轮-1仅在明确存在窗口时调用；未命中使用0和0.3秒检查返回[]。
脚本参数：--non-interactive 自动模式不等待恢复焦点；默认人工模式。
运行：uv run .\win32\test_win32_get_list.py --non-interactive
前置：dev运行。自动创建两个临时顶层窗口，原生EnumWindows独立核验顺序与数量。
临时窗口显示但不请求激活，测试结束销毁；不关闭用户窗口，不使用剪贴板或元素库。
复用window_exists的临时消息线程和highlight的原生诊断及清理辅助。
"""

import ctypes
import inspect
import os
import time
import uuid
from ctypes import wintypes
from uiautoma import win32
from uiautoma.win32 import Win32Window
from uiautoma import InvalidParamsError
import test_win32_get_value as helper
from test_win32_window_exists import OwnedWindow
from test_win32_highlight import focus_api, window_info, restore_focus_for_mode, parse_run_options


def contract():
    sig=inspect.signature(win32.get_list)
    defaults=dict(title=None,class_name=None,process_name=None,use_wildcard=False,timeout=5)
    assert list(sig.parameters)==list(defaults),sig
    for name,value in defaults.items():
        p=sig.parameters[name]
        assert p.default==value,sig
        assert p.kind==(p.POSITIONAL_OR_KEYWORD if name=='title' else p.KEYWORD_ONLY),sig
    assert str(sig.return_annotation)=='list[Win32Window]',sig
    return '五个参数、默认值、仅限关键字规则符合合同'


def main(non_interactive=False):
    print('UIAutoma Win32 API 测试\n  API: win32.get_list\n  场景: 两个临时窗口；原生EnumWindows校验')
    results=[helper.run_case('API 合同',contract)]
    owned=[]
    handles=[]
    prefix='UIAutoma-list-'+uuid.uuid4().hex
    native=focus_api()
    mouse,foreground=helper.current_cursor(),helper.current_foreground()
    focus_status='未检查'
    started=time.perf_counter()
    process_name=''

    def enumeration():
        found=[]
        callback_type=ctypes.WINFUNCTYPE(wintypes.BOOL,wintypes.HWND,wintypes.LPARAM)
        @callback_type
        def visit(hwnd,unused):
            if int(hwnd) in handles and native.IsWindowVisible(hwnd): found.append(int(hwnd))
            return True
        native.EnumWindows.argtypes=[callback_type,wintypes.LPARAM]
        native.EnumWindows.restype=wintypes.BOOL
        if not native.EnumWindows(visit,0): raise OSError('EnumWindows失败')
        return found

    def prepare():
        nonlocal process_name
        native.SetWindowTextW.argtypes=[wintypes.HWND,wintypes.LPCWSTR]
        native.SetWindowTextW.restype=wintypes.BOOL
        native.ShowWindow.argtypes=[wintypes.HWND,ctypes.c_int]
        native.ShowWindow.restype=wintypes.BOOL
        for suffix in ('A','B'):
            item=OwnedWindow()
            owned.append(item)
            handle=item.start()
            handles.append(handle)
            assert native.SetWindowTextW(handle,prefix+'-'+suffix),'设置临时标题失败'
            native.ShowWindow(handle,4)  # SW_SHOWNOACTIVATE
        assert set(enumeration())==set(handles),'临时窗口未全部显示'
        # 本脚本拥有这些窗口；查询本进程可执行文件名作为独立进程过滤参照。
        kernel=ctypes.WinDLL('kernel32',use_last_error=True)
        kernel.GetModuleFileNameW.argtypes=[wintypes.HMODULE,wintypes.LPWSTR,wintypes.DWORD]
        kernel.GetModuleFileNameW.restype=wintypes.DWORD
        buffer=ctypes.create_unicode_buffer(32768)
        assert kernel.GetModuleFileNameW(None,buffer,len(buffer)),'读取本进程文件名失败'
        process_name=os.path.basename(buffer.value)
        return '两个可见临时窗口已创建',[f'标题前缀: {prefix}；进程: {process_name}；句柄: {handles}']

    def check(args=(),kwargs=None,subset=None,all_windows=False):
        before=enumeration()
        windows=win32.get_list(*args,**(kwargs or {}))
        after=enumeration()
        assert before==after,'测试窗口Z序在查询期间变化，请勿切换窗口'
        assert type(windows) is list and all(isinstance(w,Win32Window) for w in windows),type(windows)
        actual=[]
        for window in windows:
            # 只读已返回对象的句柄描述，不以第二次SDK查找作为存在性参照。
            handle=int(window.raw.get('handle') or 0)
            assert handle and native.IsWindow(handle),f'无效返回句柄: {window.raw}'
            actual.append(handle)
        assert len(actual)==len(set(actual)),'重复返回同一窗口'
        expected=before if subset is None else [h for h in before if h in subset]
        if all_windows:
            assert [h for h in actual if h in handles]==expected,f'默认枚举遗漏临时窗口或顺序不符: {actual}'
        else:
            assert actual==expected,f'原生预期{expected}，SDK实际{actual}'
        return '列表类型、匹配数量与原生窗口顺序符合预期',[f'匹配数: {len(actual)}；临时窗口预期: {expected}']

    def missing(timeout):
        begin=time.perf_counter()
        returned=win32.get_list(prefix+'-missing',timeout=timeout)
        elapsed=(time.perf_counter()-begin)*1000
        assert type(returned) is list and returned==[],returned
        if timeout>0: assert elapsed+30>=timeout*1000,f'等待不足: {elapsed:.1f}ms'
        return f'未匹配返回[]，耗时{elapsed:.1f}ms'

    def invalid():
        for call,error in [(lambda:win32.get_list(timeout=-2),InvalidParamsError),
                           (lambda:win32.get_list(timeout='bad'),InvalidParamsError),
                           (lambda:win32.get_list(prefix,'STATIC'),TypeError)]:
            try: call()
            except error: pass
            else: raise AssertionError(f'没有抛出{error.__name__}')
        return '非法超时及多余位置参数正确拒绝'

    try:
        ready=helper.run_case('测试准备',prepare)
        results.append(ready)
        if ready.passed:
            results.append(helper.run_case('全部默认参数',lambda:check(all_windows=True)))
            results.append(helper.run_case('标题片段多项',lambda:check((prefix,))))
            results.append(helper.run_case('唯一标题',lambda:check((prefix+'-A',),subset=[handles[0]])))
            results.append(helper.run_case('类名过滤',lambda:check((prefix,),dict(class_name='Static',timeout=0))))
            results.append(helper.run_case('进程名过滤',lambda:check((prefix,),dict(process_name=process_name,timeout=0))))
            results.append(helper.run_case('全部关键字',lambda:check(kwargs=dict(title=prefix,class_name='Static',process_name=process_name,use_wildcard=False,timeout=0.5))))
            results.append(helper.run_case('通配符匹配',lambda:check(kwargs=dict(title=prefix+'-?',class_name='Sta*',process_name=process_name,use_wildcard=True,timeout=0))))
            results.append(helper.run_case('None超时',lambda:check((prefix,),dict(timeout=None))))
            results.append(helper.run_case('数字字符串超时',lambda:check((prefix,),dict(timeout='0.5'))))
            results.append(helper.run_case('无限值已有目标',lambda:check((prefix,),dict(timeout=-1))))
            results.append(helper.run_case('未命中零超时',lambda:missing(0)))
            results.append(helper.run_case('未命中有限等待',lambda:missing(0.3)))
            results.append(helper.run_case('错误传参',invalid))
    finally:
        def cleanup():
            nonlocal focus_status
            errors=[]
            actions=[('临时窗口',item.close) for item in owned]
            def focus():
                nonlocal focus_status
                focus_status=restore_focus_for_mode(foreground,non_interactive)
            actions += [('前台',focus),('鼠标',lambda:helper.restore_cursor(mouse))]
            for name,action in actions:
                try: action()
                except Exception as exc: errors.append(f'{name}: {exc}')
            if errors: raise RuntimeError('；'.join(errors))
            return '临时窗口和线程已清理，鼠标恢复',[f'焦点: {focus_status}']
        results.append(helper.run_case('资源清理',cleanup))
        helper.render_results(results)
    passed=sum(r.passed for r in results)
    ok=passed==len(results)
    print(helper.colored('\n测试通过' if ok else '\n测试失败',helper.ANSI_GREEN if ok else helper.ANSI_RED))
    print(f"  生命周期: {'VERIFIED' if ok else 'READY_FOR_LIVE'}\n  结果: {passed}/{len(results)} 通过\n  总耗时: {(time.perf_counter()-started)*1000:.1f}ms\n  退出码: {0 if ok else 1}")
    return 0 if ok else 1


if __name__=='__main__':
    raise SystemExit(main(non_interactive=parse_run_options().non_interactive))
