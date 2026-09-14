"""表单测试的共同前置条件；导入时不连接 Runtime 或操作窗口。"""

import ctypes
import time
from ctypes import wintypes
from pathlib import Path

from uiautoma import win32


FORM_TAB = "win32靶场_tab_item表单控件"
LIBRARY_DIR = Path(r"D:\code\元素库\260902_win元素")


def ensure_form_tab(package):
    """激活表单页，并通过原生 Tab 选中索引确认准备完成。"""
    if package is None:
        return
    if Path(package.package_dir).resolve() != LIBRARY_DIR.resolve():
        raise RuntimeError(f"当前元素库不是测试库：{package.package_dir}")
    user32 = ctypes.WinDLL("user32", use_last_error=True)
    user32.FindWindowExW.argtypes = [wintypes.HWND, wintypes.HWND, wintypes.LPCWSTR, wintypes.LPCWSTR]
    user32.FindWindowExW.restype = wintypes.HWND
    user32.SendMessageW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
    user32.SendMessageW.restype = ctypes.c_ssize_t
    window = win32.get(title="Win32 靶场 - UIA", process_name="win32-shooting-range-uia.exe", timeout=5)
    tab = window.find(package.selector(FORM_TAB, kind="win"), timeout=5)
    tab.click(simulative=False, delay_after=0.1, move_mouse=False)
    tab_handle = user32.FindWindowExW(window.get_detail("handle"), None, "SysTabControl32", None)
    if not tab_handle:
        raise RuntimeError("未找到靶场 Tab 控件，无法确认表单页激活")
    deadline = time.monotonic() + 3
    while user32.SendMessageW(tab_handle, 0x130B, 0, 0) != 0:  # TCM_GETCURSEL
        if time.monotonic() >= deadline:
            raise RuntimeError(f"表单页未激活：{FORM_TAB}")
        time.sleep(0.05)
    print(f"  表单页  : 已激活 {FORM_TAB}")
