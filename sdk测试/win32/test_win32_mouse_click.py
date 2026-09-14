"""``uiautoma.win32.mouse_click()`` 合法参数冒烟测试。

API 参数（不是测试脚本参数）::

    win32.mouse_click(
        button: str = "left",
        click_type: str = "click",
        keys: str = "none",
        delay_after: float = 1,
    ) -> None

脚本自动打开一个包含测试文字的记事本，并使用原生 Win32 API 激活窗口、计算安全
点击位置和移动鼠标。测试过程只调用 ``win32.mouse_click()``，覆盖以下合法参数：

* ``button``：``left``、``middle``、``right``；
* ``click_type``：``click``、``doubleClick``；
* ``keys``：``none``、``ctrl``；
* ``delay_after``：默认值 ``1`` 和显式值 ``0``。

右键单击最后执行，因此测试结束时记事本应保留右键菜单，供人工观察。记事本不会
自动关闭，请测试后手动关闭。
"""

from __future__ import annotations

import ctypes
import os
import subprocess
import sys
import tempfile
import time
from ctypes import wintypes
from pathlib import Path
from typing import Any

from uiautoma import win32


__test__ = False

ANSI_GREEN = "\x1b[32m"
ANSI_RED = "\x1b[31m"
ANSI_CYAN = "\x1b[36m"
ANSI_RESET = "\x1b[0m"

CASES: tuple[tuple[str, str, tuple[Any, ...]], ...] = (
    ("默认左键单击", "win32.mouse_click()", ()),
    (
        "左键双击",
        'win32.mouse_click("left", "doubleClick", "none", 0)',
        ("left", "doubleClick", "none", 0),
    ),
    (
        "中键单击",
        'win32.mouse_click("middle", "click", "none", 0)',
        ("middle", "click", "none", 0),
    ),
    (
        "Ctrl+左键",
        'win32.mouse_click("left", "click", "ctrl", 0)',
        ("left", "click", "ctrl", 0),
    ),
    (
        "右键单击",
        'win32.mouse_click("right", "click", "none", 0)',
        ("right", "click", "none", 0),
    ),
)


class POINT(ctypes.Structure):
    _fields_ = [("x", wintypes.LONG), ("y", wintypes.LONG)]


class RECT(ctypes.Structure):
    _fields_ = [
        ("left", wintypes.LONG),
        ("top", wintypes.LONG),
        ("right", wintypes.LONG),
        ("bottom", wintypes.LONG),
    ]


ENUM_WINDOWS_CALLBACK = ctypes.WINFUNCTYPE(
    wintypes.BOOL,
    wintypes.HWND,
    wintypes.LPARAM,
)

_user32 = ctypes.WinDLL("user32", use_last_error=True)
_user32.EnumWindows.argtypes = [ENUM_WINDOWS_CALLBACK, wintypes.LPARAM]
_user32.EnumWindows.restype = wintypes.BOOL
_user32.IsWindowVisible.argtypes = [wintypes.HWND]
_user32.IsWindowVisible.restype = wintypes.BOOL
_user32.GetWindowTextLengthW.argtypes = [wintypes.HWND]
_user32.GetWindowTextLengthW.restype = ctypes.c_int
_user32.GetWindowTextW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
_user32.GetWindowTextW.restype = ctypes.c_int
_user32.GetForegroundWindow.restype = wintypes.HWND
_user32.ShowWindow.argtypes = [wintypes.HWND, ctypes.c_int]
_user32.ShowWindow.restype = wintypes.BOOL
_user32.BringWindowToTop.argtypes = [wintypes.HWND]
_user32.BringWindowToTop.restype = wintypes.BOOL
_user32.SetForegroundWindow.argtypes = [wintypes.HWND]
_user32.SetForegroundWindow.restype = wintypes.BOOL
_user32.GetClientRect.argtypes = [wintypes.HWND, ctypes.POINTER(RECT)]
_user32.GetClientRect.restype = wintypes.BOOL
_user32.ClientToScreen.argtypes = [wintypes.HWND, ctypes.POINTER(POINT)]
_user32.ClientToScreen.restype = wintypes.BOOL
_user32.SetCursorPos.argtypes = [ctypes.c_int, ctypes.c_int]
_user32.SetCursorPos.restype = wintypes.BOOL
_user32.GetCursorPos.argtypes = [ctypes.POINTER(POINT)]
_user32.GetCursorPos.restype = wintypes.BOOL


def _color(text: str, ansi: str, *, enabled: bool) -> str:
    return f"{ansi}{text}{ANSI_RESET}" if enabled else text


def _window_title(handle: int) -> str:
    length = int(_user32.GetWindowTextLengthW(wintypes.HWND(handle)))
    if length <= 0:
        return ""
    buffer = ctypes.create_unicode_buffer(length + 1)
    _user32.GetWindowTextW(wintypes.HWND(handle), buffer, len(buffer))
    return buffer.value


def _find_window(title_token: str) -> tuple[int, str] | None:
    matches: list[tuple[int, str]] = []

    @ENUM_WINDOWS_CALLBACK
    def collect(handle: int, _lparam: int) -> bool:
        if not _user32.IsWindowVisible(handle):
            return True
        title = _window_title(int(handle))
        if title_token.casefold() in title.casefold():
            matches.append((int(handle), title))
            return False
        return True

    _user32.EnumWindows(collect, 0)
    return matches[0] if matches else None


def _activate_window(handle: int, *, timeout: float = 2.0) -> bool:
    deadline = time.monotonic() + timeout
    hwnd = wintypes.HWND(handle)
    while True:
        if int(_user32.GetForegroundWindow() or 0) == handle:
            return True
        _user32.ShowWindow(hwnd, 9)
        _user32.BringWindowToTop(hwnd)
        _user32.SetForegroundWindow(hwnd)
        if time.monotonic() >= deadline:
            return int(_user32.GetForegroundWindow() or 0) == handle
        time.sleep(0.05)


def _target_point(handle: int) -> tuple[int, int]:
    rect = RECT()
    hwnd = wintypes.HWND(handle)
    if not _user32.GetClientRect(hwnd, ctypes.byref(rect)):
        raise ctypes.WinError(ctypes.get_last_error())
    width = int(rect.right - rect.left)
    height = int(rect.bottom - rect.top)
    if width < 120 or height < 120:
        raise RuntimeError(f"记事本客户区过小：{width}x{height}")

    point = POINT(width // 2, min(max(height // 2, 80), height - 40))
    if not _user32.ClientToScreen(hwnd, ctypes.byref(point)):
        raise ctypes.WinError(ctypes.get_last_error())
    return int(point.x), int(point.y)


def _set_cursor(point: tuple[int, int]) -> None:
    if not _user32.SetCursorPos(*point):
        raise ctypes.WinError(ctypes.get_last_error())
    time.sleep(0.15)


def _cursor_position() -> tuple[int, int]:
    point = POINT()
    if not _user32.GetCursorPos(ctypes.byref(point)):
        raise ctypes.WinError(ctypes.get_last_error())
    return int(point.x), int(point.y)


def _launch_notepad(
    *, timeout: float = 8.0
) -> tuple[subprocess.Popen[Any], Path, int, str, tuple[int, int]]:
    descriptor, raw_path = tempfile.mkstemp(
        prefix="uiautoma-mouse-click-",
        suffix=".txt",
    )
    path = Path(raw_path)
    with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
        stream.write("UIAutoma mouse_click test target\n")
        stream.write("测试结束时应看到记事本右键菜单。\n")

    process = subprocess.Popen(["notepad.exe", str(path)])
    deadline = time.monotonic() + timeout
    match: tuple[int, str] | None = None
    while time.monotonic() < deadline:
        match = _find_window(path.name)
        if match is not None:
            break
        time.sleep(0.1)

    if match is None:
        if process.poll() is None:
            process.terminate()
        path.unlink(missing_ok=True)
        raise RuntimeError("记事本窗口未在超时内出现")

    handle, title = match
    if not _activate_window(handle):
        if process.poll() is None:
            process.terminate()
        path.unlink(missing_ok=True)
        raise RuntimeError("无法激活记事本窗口")

    point = _target_point(handle)
    _set_cursor(point)
    return process, path, handle, title, point


def _run_case(
    handle: int,
    point: tuple[int, int],
    label: str,
    call: str,
    arguments: tuple[Any, ...],
) -> dict[str, Any]:
    try:
        if not _activate_window(handle):
            raise RuntimeError("无法重新激活记事本窗口")
        _set_cursor(point)
        started = time.perf_counter()
        result = win32.mouse_click(*arguments)
        elapsed_ms = (time.perf_counter() - started) * 1000
        actual = _cursor_position()
    except Exception as exc:  # noqa: BLE001
        return {
            "label": label,
            "status": "FAIL",
            "detail": "调用失败",
            "call": call,
            "elapsed_ms": (time.perf_counter() - locals().get("started", time.perf_counter()))
            * 1000,
            "exception": exc.__class__.__name__,
            "message": str(exc),
        }

    position_ok = abs(actual[0] - point[0]) <= 2 and abs(actual[1] - point[1]) <= 2
    passed = result is None and position_ok
    if result is not None:
        detail = "返回值不是 None"
    elif not position_ok:
        detail = f"调用后鼠标位置发生变化：{actual}"
    else:
        detail = "调用完成并返回 None"
    return {
        "label": label,
        "status": "PASS" if passed else "FAIL",
        "detail": detail,
        "call": call,
        "elapsed_ms": elapsed_ms,
    }


def _print_result(
    index: int,
    total: int,
    result: dict[str, Any],
    *,
    color: bool,
) -> None:
    passed = result["status"] == "PASS"
    badge = _color(
        "[通过]" if passed else "[失败]",
        ANSI_GREEN if passed else ANSI_RED,
        enabled=color,
    )
    print(f"[{index}/{total}] {badge} {result['label']}")
    print(f"      调用: {result['call']}")
    print(f"      结果: {result['detail']}  {result['elapsed_ms']:.1f}ms")
    if result.get("exception"):
        print(f"      异常: {result['exception']}: {result['message']}")


def main() -> int:
    color = "NO_COLOR" not in os.environ and sys.stdout.isatty()
    print(_color("UIAutoma Win32 API 测试", ANSI_CYAN, enabled=color))
    print()
    print("  API : uiautoma.win32.mouse_click")
    print("  对象: 自动打开的记事本")
    print()

    try:
        process, path, handle, title, point = _launch_notepad()
    except Exception as exc:  # noqa: BLE001
        print(_color("[失败] 记事本准备失败", ANSI_RED, enabled=color))
        print(f"  异常: {exc.__class__.__name__}: {exc}")
        return 1

    print(f"  窗口: {title}")
    print(f"  句柄: {handle}")
    print(f"  PID : {process.pid}")
    print(f"  坐标: {point}")
    print()

    started = time.perf_counter()
    results: list[dict[str, Any]] = []
    total = len(CASES)
    for index, (label, call, arguments) in enumerate(CASES, start=1):
        result = _run_case(handle, point, label, call, arguments)
        results.append(result)
        _print_result(index, total, result, color=color)

    path_deleted = False
    try:
        path.unlink(missing_ok=True)
        path_deleted = True
    except OSError:
        pass

    passed_count = sum(result["status"] == "PASS" for result in results)
    exit_code = 0 if passed_count == total else 1
    elapsed_ms = (time.perf_counter() - started) * 1000
    print()
    summary = "测试通过" if exit_code == 0 else "测试失败"
    print(_color(summary, ANSI_GREEN if exit_code == 0 else ANSI_RED, enabled=color))
    print(f"  结果    : {passed_count}/{total} 通过")
    print(f"  总耗时  : {elapsed_ms:.1f}ms")
    print(f"  临时文件: {'已删除' if path_deleted else path}")
    print("  人工确认: 记事本中应保留右键菜单")
    print("  提示    : 请手动关闭记事本")
    print(f"  退出码  : {exit_code}")
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
