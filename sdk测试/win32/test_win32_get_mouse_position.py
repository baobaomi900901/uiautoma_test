"""``uiautoma.win32.get_mouse_position()`` 合法参数测试。

API 参数（不是测试脚本参数）::

    win32.get_mouse_position(
        relative_to: str = "screen",
    ) -> tuple[int, int]

脚本自动打开一个记事本作为受控活动窗口，并使用原生 Win32 API 定位鼠标、读取
预期屏幕坐标及窗口矩形。测试过程只调用 ``win32.get_mouse_position()``，覆盖：

* 不传参数时的默认 ``screen`` 坐标；
* 显式传入 ``screen``；
* 显式传入 ``window``。

测试结束后脚本会恢复鼠标位置、关闭记事本并删除临时文件。
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

SCREEN_TOLERANCE_PX = 2
WINDOW_TOLERANCE_PX = 10
WM_CLOSE = 0x0010

CASES: tuple[tuple[str, str, str | None], ...] = (
    ("默认屏幕坐标", "win32.get_mouse_position()", None),
    ("显式屏幕坐标", 'win32.get_mouse_position("screen")', "screen"),
    ("活动窗口坐标", 'win32.get_mouse_position("window")', "window"),
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
_user32.IsWindow.argtypes = [wintypes.HWND]
_user32.IsWindow.restype = wintypes.BOOL
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
_user32.GetWindowRect.argtypes = [wintypes.HWND, ctypes.POINTER(RECT)]
_user32.GetWindowRect.restype = wintypes.BOOL
_user32.SetCursorPos.argtypes = [ctypes.c_int, ctypes.c_int]
_user32.SetCursorPos.restype = wintypes.BOOL
_user32.GetCursorPos.argtypes = [ctypes.POINTER(POINT)]
_user32.GetCursorPos.restype = wintypes.BOOL
_user32.PostMessageW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
_user32.PostMessageW.restype = wintypes.BOOL


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


def _window_rect(handle: int) -> tuple[int, int, int, int]:
    rect = RECT()
    if not _user32.GetWindowRect(wintypes.HWND(handle), ctypes.byref(rect)):
        raise ctypes.WinError(ctypes.get_last_error())
    return int(rect.left), int(rect.top), int(rect.right), int(rect.bottom)


def _cursor_position() -> tuple[int, int]:
    point = POINT()
    if not _user32.GetCursorPos(ctypes.byref(point)):
        raise ctypes.WinError(ctypes.get_last_error())
    return int(point.x), int(point.y)


def _set_cursor(point: tuple[int, int]) -> None:
    if not _user32.SetCursorPos(*point):
        raise ctypes.WinError(ctypes.get_last_error())
    time.sleep(0.15)


def _near(
    actual: tuple[int, int],
    expected: tuple[int, int],
    *,
    tolerance: int,
) -> bool:
    return (
        abs(actual[0] - expected[0]) <= tolerance
        and abs(actual[1] - expected[1]) <= tolerance
    )


def _launch_notepad(
    *, timeout: float = 8.0
) -> tuple[subprocess.Popen[Any], Path, int, str, tuple[int, int, int, int]]:
    descriptor, raw_path = tempfile.mkstemp(
        prefix="uiautoma-get-mouse-position-",
        suffix=".txt",
    )
    path = Path(raw_path)
    with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
        stream.write("UIAutoma get_mouse_position test target\n")

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

    rect = _window_rect(handle)
    if rect[2] - rect[0] < 120 or rect[3] - rect[1] < 120:
        raise RuntimeError(f"记事本窗口过小：{rect}")
    return process, path, handle, title, rect


def _run_case(
    label: str,
    call: str,
    relative_to: str | None,
    *,
    screen_point: tuple[int, int],
    window_origin: tuple[int, int],
) -> dict[str, Any]:
    expected = (
        screen_point
        if relative_to in (None, "screen")
        else (
            screen_point[0] - window_origin[0],
            screen_point[1] - window_origin[1],
        )
    )
    tolerance = SCREEN_TOLERANCE_PX if relative_to in (None, "screen") else WINDOW_TOLERANCE_PX
    started = time.perf_counter()
    try:
        if relative_to is None:
            actual = win32.get_mouse_position()
        else:
            actual = win32.get_mouse_position(relative_to)
    except Exception as exc:  # noqa: BLE001
        return {
            "label": label,
            "status": "FAIL",
            "detail": "调用失败",
            "call": call,
            "elapsed_ms": (time.perf_counter() - started) * 1000,
            "exception": exc.__class__.__name__,
            "message": str(exc),
        }

    elapsed_ms = (time.perf_counter() - started) * 1000
    type_ok = (
        isinstance(actual, tuple)
        and len(actual) == 2
        and all(isinstance(value, int) for value in actual)
    )
    actual_point = (int(actual[0]), int(actual[1])) if type_ok else None
    position_ok = actual_point is not None and _near(
        actual_point,
        expected,
        tolerance=tolerance,
    )
    passed = type_ok and position_ok
    return {
        "label": label,
        "status": "PASS" if passed else "FAIL",
        "detail": "返回坐标与预期一致" if passed else "返回类型或坐标与预期不一致",
        "call": call,
        "elapsed_ms": elapsed_ms,
        "actual": actual,
        "expected": expected,
        "tolerance": tolerance,
    }


def _close_window(handle: int, *, timeout: float = 3.0) -> bool:
    hwnd = wintypes.HWND(handle)
    if not _user32.IsWindow(hwnd):
        return True
    if not _user32.PostMessageW(hwnd, WM_CLOSE, 0, 0):
        return False
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if not _user32.IsWindow(hwnd):
            return True
        time.sleep(0.05)
    return not _user32.IsWindow(hwnd)


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
    print(f"      预期: {result.get('expected', '—')}")
    print(f"      实际: {result.get('actual', '—')}")
    print(f"      结果: {result['detail']}  {result['elapsed_ms']:.1f}ms")
    if result.get("exception"):
        print(f"      异常: {result['exception']}: {result['message']}")


def main() -> int:
    color = "NO_COLOR" not in os.environ and sys.stdout.isatty()
    print(_color("UIAutoma Win32 API 测试", ANSI_CYAN, enabled=color))
    print()
    print("  API : uiautoma.win32.get_mouse_position")
    print("  对象: 自动打开的记事本")
    print()

    original_cursor = _cursor_position()
    try:
        process, path, handle, title, rect = _launch_notepad()
    except Exception as exc:  # noqa: BLE001
        print(_color("[失败] 记事本准备失败", ANSI_RED, enabled=color))
        print(f"  异常: {exc.__class__.__name__}: {exc}")
        return 1

    window_origin = (rect[0], rect[1])
    screen_point = (
        rect[0] + (rect[2] - rect[0]) // 2,
        rect[1] + (rect[3] - rect[1]) // 2,
    )
    _set_cursor(screen_point)

    print(f"  窗口    : {title}")
    print(f"  句柄    : {handle}")
    print(f"  PID     : {process.pid}")
    print(f"  窗口原点: {window_origin}")
    print(f"  屏幕坐标: {screen_point}")
    print()

    started = time.perf_counter()
    results: list[dict[str, Any]] = []
    total = len(CASES)
    for index, (label, call, relative_to) in enumerate(CASES, start=1):
        result = _run_case(
            label,
            call,
            relative_to,
            screen_point=screen_point,
            window_origin=window_origin,
        )
        results.append(result)
        _print_result(index, total, result, color=color)

    cursor_restored = True
    try:
        _set_cursor(original_cursor)
    except OSError:
        cursor_restored = False

    window_closed = _close_window(handle)
    path_deleted = False
    try:
        path.unlink(missing_ok=True)
        path_deleted = True
    except OSError:
        pass

    passed_count = sum(result["status"] == "PASS" for result in results)
    cleanup_ok = cursor_restored and window_closed and path_deleted
    exit_code = 0 if passed_count == total and cleanup_ok else 1
    elapsed_ms = (time.perf_counter() - started) * 1000
    print()
    summary = "测试通过" if exit_code == 0 else "测试失败"
    print(_color(summary, ANSI_GREEN if exit_code == 0 else ANSI_RED, enabled=color))
    print(f"  结果    : {passed_count}/{total} 通过")
    print(f"  总耗时  : {elapsed_ms:.1f}ms")
    print(f"  鼠标位置: {'已恢复' if cursor_restored else '恢复失败'}")
    print(f"  记事本  : {'已关闭' if window_closed else '关闭失败'}")
    print(f"  临时文件: {'已删除' if path_deleted else path}")
    print(f"  退出码  : {exit_code}")
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
