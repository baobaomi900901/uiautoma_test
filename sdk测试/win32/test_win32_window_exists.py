r"""Win32Window.exists() -> bool：判断窗口对象对应的原生顶层窗口是否仍有效。

API参数：无；不支持timeout或额外位置参数。区别于win32.exists(window)及Win32Element.exists。
脚本参数：--non-interactive 自动复测，焦点恢复失败仅警告；默认人工模式。
运行：uv run .\win32\test_win32_window_exists.py --non-interactive
前置：dev与Win32靶场运行，无需元素库。靶场只读，不会关闭。
另在独立原生消息线程创建一个隐藏的临时顶层窗口，验证隐藏仍存在、DestroyWindow后不存在。
临时窗口由脚本拥有，清理时仅销毁该窗口；不使用剪贴板，不操作其他应用窗口。
用IsWindow独立交叉校验。只覆盖有原生句柄的窗口对象，不覆盖Desktop伪窗口。
"""

import ctypes
import inspect
import queue
import threading
import time
import uuid
from ctypes import wintypes
from uiautoma import win32
from uiautoma.win32 import Win32Window
import test_win32_get_value as helper
from test_win32_highlight import focus_api, restore_focus_for_mode, parse_run_options


class OwnedWindow:
    def __init__(self):
        self.stop=threading.Event()
        self.ready=queue.Queue()
        self.errors=[]
        self.handle=0
        self.thread=threading.Thread(target=self.run,daemon=True)

    def run(self):
        user32=ctypes.WinDLL('user32',use_last_error=True)
        user32.CreateWindowExW.argtypes=[wintypes.DWORD,wintypes.LPCWSTR,wintypes.LPCWSTR,wintypes.DWORD,
            ctypes.c_int,ctypes.c_int,ctypes.c_int,ctypes.c_int,wintypes.HWND,wintypes.HMENU,wintypes.HINSTANCE,ctypes.c_void_p]
        user32.CreateWindowExW.restype=wintypes.HWND
        user32.DestroyWindow.argtypes=[wintypes.HWND]
        user32.DestroyWindow.restype=wintypes.BOOL
        user32.PeekMessageW.argtypes=[ctypes.POINTER(wintypes.MSG),wintypes.HWND,wintypes.UINT,wintypes.UINT,wintypes.UINT]
        user32.PeekMessageW.restype=wintypes.BOOL
        user32.TranslateMessage.argtypes=[ctypes.POINTER(wintypes.MSG)]
        user32.DispatchMessageW.argtypes=[ctypes.POINTER(wintypes.MSG)]
        user32.DispatchMessageW.restype=ctypes.c_ssize_t
        try:
            self.handle=int(user32.CreateWindowExW(0,'STATIC','UIAutoma-exists-'+uuid.uuid4().hex,
                0x00CF0000,0,0,240,120,None,None,None,None) or 0)
            if not self.handle: raise OSError(f'CreateWindowExW失败：{ctypes.get_last_error()}')
            self.ready.put(self.handle)
            message=wintypes.MSG()
            while not self.stop.is_set():
                while user32.PeekMessageW(ctypes.byref(message),None,0,0,1):
                    user32.TranslateMessage(ctypes.byref(message))
                    user32.DispatchMessageW(ctypes.byref(message))
                self.stop.wait(0.005)
        except Exception as exc:
            self.errors.append(str(exc))
            self.ready.put(exc)
        finally:
            if self.handle and not user32.DestroyWindow(self.handle):
                self.errors.append(f'DestroyWindow失败：{ctypes.get_last_error()}')

    def start(self):
        self.thread.start()
        result=self.ready.get(timeout=5)
        if isinstance(result,Exception): raise result
        return result

    def close(self):
        self.stop.set()
        if self.thread.ident is not None: self.thread.join(3)
        if self.thread.is_alive() or self.errors:
            raise RuntimeError(f'临时窗口线程清理失败：{self.errors}')
        if self.handle and focus_api().IsWindow(self.handle):
            raise RuntimeError('临时窗口仍存在')


def contract():
    sig=inspect.signature(Win32Window.exists)
    assert list(sig.parameters)==['self'] and str(sig.return_annotation) in ('bool',"<class 'bool'>"),sig
    return '无公开参数，返回bool'


def main(non_interactive=False):
    print('UIAutoma Win32 Window API 测试\n  API: Win32Window.exists')
    print('  对象: 运行中的靶场 + 脚本临时顶层窗口\n  原生参照: IsWindow；不关闭靶场')
    results=[helper.run_case('API 合同',contract)]
    owned=OwnedWindow()
    target=None
    focus_status='未检查'
    mouse,foreground=helper.current_cursor(),helper.current_foreground()
    started=time.perf_counter()

    def compare(window,handle,expected):
        native=bool(focus_api().IsWindow(handle))
        returned=window.exists()
        assert native is expected and type(returned) is bool and returned is expected,f'预期{expected}，原生{native}，SDK{returned!r}'
        return f'原生IsWindow与window.exists()均为{expected}'

    def live_target():
        window=win32.get(title='Win32 靶场 - UIA',process_name='win32-shooting-range-uia.exe',timeout=5)
        return compare(window,int(window.get_detail('handle')),True)

    def temporary():
        nonlocal target
        handle=owned.start()
        target=win32.get_by_handle(handle,timeout=0)
        assert isinstance(target,Win32Window)
        return '脚本临时顶层窗口已创建并绑定',[f'句柄: {handle}']

    def hidden():
        assert not focus_api().IsWindowVisible(owned.handle),'临时窗口应处于隐藏状态'
        return compare(target,owned.handle,True)

    def repeat():
        for _ in range(3): compare(target,owned.handle,True)
        return '连续三次返回True'

    def arguments():
        for invoke in (lambda:target.exists(0),lambda:target.exists(timeout=0)):
            try: invoke()
            except TypeError: pass
            else: raise AssertionError('额外参数未被拒绝')
        return compare(target,owned.handle,True)+'；错误参数均为TypeError'

    try:
        results.append(helper.run_case('靶场仍存在',live_target))
        prepared=helper.run_case('临时窗口准备',temporary)
        results.append(prepared)
        if prepared.passed:
            results.append(helper.run_case('隐藏窗口仍存在',hidden))
            results.append(helper.run_case('重复查询',repeat))
            results.append(helper.run_case('参数限制',arguments))
            def destroy():
                owned.close()
                return '原生DestroyWindow完成，原句柄已失效'
            destroyed=helper.run_case('销毁临时窗口',destroy)
            results.append(destroyed)
            if destroyed.passed:
                results.append(helper.run_case('原对象不再存在',lambda:compare(target,owned.handle,False)))
    finally:
        def cleanup():
            nonlocal focus_status
            errors=[]
            def focus():
                nonlocal focus_status
                focus_status=restore_focus_for_mode(foreground,non_interactive)
            for name,action in [('临时窗口',owned.close),('前台',focus),('鼠标',lambda:helper.restore_cursor(mouse))]:
                try: action()
                except Exception as exc: errors.append(f'{name}: {exc}')
            if errors: raise RuntimeError('；'.join(errors))
            return '临时窗口和线程已清理，鼠标已恢复；靶场保持运行',[f'焦点: {focus_status}']
        results.append(helper.run_case('资源清理',cleanup))
        helper.render_results(results)
    passed=sum(r.passed for r in results)
    ok=passed==len(results)
    print(helper.colored('\n测试通过' if ok else '\n测试失败',helper.ANSI_GREEN if ok else helper.ANSI_RED))
    print(f"  生命周期: {'VERIFIED' if ok else 'READY_FOR_LIVE'}\n  结果: {passed}/{len(results)} 通过\n  总耗时: {(time.perf_counter()-started)*1000:.1f}ms\n  退出码: {0 if ok else 1}")
    return 0 if ok else 1


if __name__=='__main__':
    raise SystemExit(main(non_interactive=parse_run_options().non_interactive))
