"""短时只读WH_MOUSE_LL观察器；记录按下/抬起，不吞掉或生成输入。"""

import ctypes
import threading
import time
from ctypes import wintypes

MESSAGES = {0x0201: ('left', 'down'), 0x0202: ('left', 'up'),
            0x0204: ('right', 'down'), 0x0205: ('right', 'up'),
            0x0207: ('middle', 'down'), 0x0208: ('middle', 'up')}


class MouseData(ctypes.Structure):
    _fields_ = [('pt', wintypes.POINT), ('mouseData', wintypes.DWORD),
                ('flags', wintypes.DWORD), ('time', wintypes.DWORD),
                ('dwExtraInfo', ctypes.c_size_t)]


class MouseEventProbe:
    def __init__(self):
        self.events = []
        self.errors = []
        self.ready = threading.Event()
        self.stop = threading.Event()
        self.thread = threading.Thread(target=self._run, daemon=True)

    def _run(self):
        hook = None
        try:
            user32 = ctypes.WinDLL('user32', use_last_error=True)
            kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)
            callback_type = ctypes.WINFUNCTYPE(ctypes.c_ssize_t, ctypes.c_int, wintypes.WPARAM, wintypes.LPARAM)
            user32.SetWindowsHookExW.argtypes = [ctypes.c_int, callback_type, wintypes.HINSTANCE, wintypes.DWORD]
            user32.SetWindowsHookExW.restype = wintypes.HANDLE
            user32.CallNextHookEx.argtypes = [wintypes.HANDLE, ctypes.c_int, wintypes.WPARAM, wintypes.LPARAM]
            user32.CallNextHookEx.restype = ctypes.c_ssize_t
            user32.UnhookWindowsHookEx.argtypes = [wintypes.HANDLE]
            user32.UnhookWindowsHookEx.restype = wintypes.BOOL
            user32.GetAsyncKeyState.argtypes = [ctypes.c_int]
            user32.GetAsyncKeyState.restype = ctypes.c_short
            user32.PeekMessageW.argtypes = [ctypes.POINTER(wintypes.MSG), wintypes.HWND, wintypes.UINT, wintypes.UINT, wintypes.UINT]
            user32.PeekMessageW.restype = wintypes.BOOL
            user32.TranslateMessage.argtypes = [ctypes.POINTER(wintypes.MSG)]
            user32.DispatchMessageW.argtypes = [ctypes.POINTER(wintypes.MSG)]
            user32.DispatchMessageW.restype = ctypes.c_ssize_t
            kernel32.GetModuleHandleW.argtypes = [wintypes.LPCWSTR]
            kernel32.GetModuleHandleW.restype = wintypes.HMODULE

            @callback_type
            def callback(code, message, pointer):
                try:
                    if code >= 0 and message in MESSAGES:
                        data = ctypes.cast(pointer, ctypes.POINTER(MouseData)).contents
                        button, phase = MESSAGES[message]
                        keys = tuple(name for name, vks in (
                            ('ctrl', (17,)), ('shift', (16,)), ('alt', (18,)), ('win', (91, 92)))
                            if any(user32.GetAsyncKeyState(vk) & 0x8000 for vk in vks))
                        self.events.append(dict(button=button, phase=phase, point=(data.pt.x, data.pt.y),
                                                keys=keys, time_ms=int(data.time)))
                except Exception as exc:
                    self.errors.append(f'鼠标事件回调: {exc}')
                return user32.CallNextHookEx(None, code, message, pointer)

            hook = user32.SetWindowsHookExW(14, callback, kernel32.GetModuleHandleW(None), 0)
            if not hook:
                raise OSError(f'SetWindowsHookExW失败: {ctypes.get_last_error()}')
            self.ready.set()
            msg = wintypes.MSG()
            while not self.stop.is_set():
                while user32.PeekMessageW(ctypes.byref(msg), None, 0, 0, 1):
                    user32.TranslateMessage(ctypes.byref(msg))
                    user32.DispatchMessageW(ctypes.byref(msg))
                self.stop.wait(0.002)
        except Exception as exc:
            self.errors.append(str(exc))
        finally:
            if hook and not user32.UnhookWindowsHookEx(hook):
                self.errors.append(f'UnhookWindowsHookEx失败: {ctypes.get_last_error()}')
            self.ready.set()

    def start(self):
        self.thread.start()
        if not self.ready.wait(3) or self.errors:
            self.close()
            raise RuntimeError('鼠标事件观察器未就绪')

    def close(self):
        self.stop.set()
        self.thread.join(2)
        if self.thread.is_alive() or self.errors:
            raise RuntimeError(f'鼠标事件观察器失败/未退出: {self.errors}')


def verify_click_events(events, button, click_type, keys, point, clicked=True):
    count = (2 if click_type in ('doubleClick', 'dbclick', 'dblclick') else 1) if clicked else 0
    expected = [(button, phase) for _ in range(count) for phase in ('down', 'up')]
    actual = [(e['button'], e['phase']) for e in events]
    assert actual == expected, f'预期事件{expected}，实际{events}'
    modifiers = set() if keys == 'none' else set(keys.split('+'))
    for event in events:
        assert event['point'] == point, f'事件坐标预期{point}，实际{event}'
        if event['phase'] == 'down':
            assert set(event['keys']) == modifiers, f'按下时修饰键预期{sorted(modifiers)}，实际{event}'
    return f'原生事件: {count}次{button}点击，{len(events)}个按下/抬起事件；按下时修饰键={keys}'
