"""``uiautoma.win32.exists()`` 受控窗口生命周期测试。

API 参数（不是测试脚本参数）::

    win32.exists(
        window: object,
    ) -> bool

``window`` 是必填参数。当前源码接受 ``Win32Window``、``Win32Element`` 和
``RawWinElement``；本脚本只验证 ``Win32Window`` 的真实窗口生命周期。

脚本自动打开一个记事本，用原生 Win32 句柄构造 ``Win32Window`` 测试对象。测试过程
只调用 ``win32.exists()``：关闭前应返回 ``True``，原生关闭窗口后应返回 ``False``。
测试结束后脚本会确认窗口关闭并删除临时文件。
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
from uiautoma.win32 import Win32Window
from uiautoma.win32.native_window import NativeWindow


__test__ = False

ANSI_GREEN = "\x1b[32m"
ANSI_RED = "\x1b[31m"
ANSI_CYAN = "\x1b[36m"
ANSI_RESET = "\x1b[0m"
WM_CLOSE = 0x0010


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
_user32.GetClassNameW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
_user32.GetClassNameW.restype = ctypes.c_int
_user32.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
_user32.GetWindowThreadProcessId.restype = wintypes.DWORD
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


def _window_class(handle: int) -> str:
    buffer = ctypes.create_unicode_buffer(256)
    _user32.GetClassNameW(wintypes.HWND(handle), buffer, len(buffer))
    return buffer.value


def _window_process_id(handle: int) -> int:
    process_id = wintypes.DWORD()
    _user32.GetWindowThreadProcessId(
        wintypes.HWND(handle),
        ctypes.byref(process_id),
    )
    return int(process_id.value)


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


def _launch_notepad(
    *, timeout: float = 8.0
) -> tuple[subprocess.Popen[Any], Path, int, str, Win32Window]:
    descriptor, raw_path = tempfile.mkstemp(
        prefix="uiautoma-exists-",
        suffix=".txt",
    )
    path = Path(raw_path)
    with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
        stream.write("UIAutoma exists test target\n")

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
    class_name = _window_class(handle)
    process_id = _window_process_id(handle)
    native = NativeWindow(
        handle=handle,
        title=title,
        class_name=class_name,
        process_id=process_id,
        process_name="notepad.exe",
    )
    window = Win32Window(
        title=title,
        class_name=class_name,
        raw=native.raw,
        _native=native,
    )
    return process, path, handle, title, window


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


def _run_case(
    label: str,
    call: str,
    window: Win32Window,
    *,
    expected: bool,
) -> dict[str, Any]:
    started = time.perf_counter()
    try:
        actual = win32.exists(window)
    except Exception as exc:  # noqa: BLE001
        return {
            "label": label,
            "status": "FAIL",
            "detail": "调用失败",
            "call": call,
            "expected": expected,
            "elapsed_ms": (time.perf_counter() - started) * 1000,
            "exception": exc.__class__.__name__,
            "message": str(exc),
        }

    elapsed_ms = (time.perf_counter() - started) * 1000
    passed = actual is expected
    return {
        "label": label,
        "status": "PASS" if passed else "FAIL",
        "detail": "返回值与预期一致" if passed else "返回值与预期不一致",
        "call": call,
        "expected": expected,
        "actual": actual,
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
    print(f"      预期: {result['expected']}")
    print(f"      实际: {result.get('actual', '—')}")
    print(f"      结果: {result['detail']}  {result['elapsed_ms']:.1f}ms")
    if result.get("exception"):
        print(f"      异常: {result['exception']}: {result['message']}")


def main() -> int:
    color = "NO_COLOR" not in os.environ and sys.stdout.isatty()
    print(_color("UIAutoma Win32 API 测试", ANSI_CYAN, enabled=color))
    print()
    print("  API : uiautoma.win32.exists")
    print("  对象: 自动打开的记事本窗口")
    print()

    try:
        process, path, handle, title, window = _launch_notepad()
    except Exception as exc:  # noqa: BLE001
        print(_color("[失败] 记事本准备失败", ANSI_RED, enabled=color))
        print(f"  异常: {exc.__class__.__name__}: {exc}")
        return 1

    print(f"  窗口: {title}")
    print(f"  类型: {window.__class__.__name__}")
    print(f"  句柄: {handle}")
    print(f"  PID : {_window_process_id(handle)}（启动命令 PID {process.pid}）")
    print()

    started = time.perf_counter()
    before = _run_case(
        "关闭前存在",
        "win32.exists(window)",
        window,
        expected=True,
    )
    _print_result(1, 2, before, color=color)

    window_closed = _close_window(handle)
    after = _run_case(
        "关闭后不存在",
        "win32.exists(window)",
        window,
        expected=False,
    )
    _print_result(2, 2, after, color=color)

    path_deleted = False
    try:
        path.unlink(missing_ok=True)
        path_deleted = True
    except OSError:
        pass

    results = [before, after]
    passed_count = sum(result["status"] == "PASS" for result in results)
    cleanup_ok = window_closed and path_deleted
    exit_code = 0 if passed_count == len(results) and cleanup_ok else 1
    elapsed_ms = (time.perf_counter() - started) * 1000
    print()
    summary = "测试通过" if exit_code == 0 else "测试失败"
    print(_color(summary, ANSI_GREEN if exit_code == 0 else ANSI_RED, enabled=color))
    print(f"  结果    : {passed_count}/2 通过")
    print(f"  总耗时  : {elapsed_ms:.1f}ms")
    print(f"  记事本  : {'已关闭' if window_closed else '关闭失败'}")
    print(f"  临时文件: {'已删除' if path_deleted else path}")
    print(f"  退出码  : {exit_code}")
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
