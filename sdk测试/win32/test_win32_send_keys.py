"""``uiautoma.win32.send_keys()`` 合法参数冒烟测试。

API 参数（不是测试脚本参数）::

    win32.send_keys(
        keys: str = "",
        send_key_delay: int = 50,
        delay_after: float = 1,
        contains_hotkey: bool = True,
        force_ime_eng: bool = False,
    ) -> None

脚本自动打开并激活一个空白记事本，只执行以下两次 UIAutoma SDK 调用：

    win32.send_keys("UIAutoma123", 50, 1, False, True)
    win32.send_keys("^a", 20, 0, True, False)

第一次按普通文本输入，第二次发送 ``Ctrl+A`` 全选。记事本会保留在前台供人工观察，
请测试后手动关闭并选择不保存。窗口查找与激活使用 Win32 API，不调用其他 UIAutoma
SDK API。
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

_user32 = ctypes.WinDLL("user32", use_last_error=True)
_user32.EnumWindows.argtypes = [ctypes.c_void_p, wintypes.LPARAM]
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

ENUM_WINDOWS_CALLBACK = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)


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


def _launch_notepad(*, timeout: float = 8.0) -> tuple[subprocess.Popen[Any], Path, int, str]:
    descriptor, raw_path = tempfile.mkstemp(prefix="uiautoma-send-keys-", suffix=".txt")
    os.close(descriptor)
    path = Path(raw_path)
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
    time.sleep(0.3)
    return process, path, handle, title


def _run_plain_text() -> dict[str, Any]:
    started = time.perf_counter()
    try:
        result = win32.send_keys("UIAutoma123", 50, 1, False, True)
    except Exception as exc:  # noqa: BLE001
        return {
            "status": "FAIL",
            "detail": "普通文本输入失败",
            "elapsed_ms": (time.perf_counter() - started) * 1000,
            "exception": exc.__class__.__name__,
            "message": str(exc),
        }
    return {
        "status": "PASS" if result is None else "FAIL",
        "detail": "普通文本已发送并返回 None" if result is None else "返回值不是 None",
        "elapsed_ms": (time.perf_counter() - started) * 1000,
    }


def _run_ctrl_a() -> dict[str, Any]:
    started = time.perf_counter()
    try:
        result = win32.send_keys("^a", 20, 0, True, False)
    except Exception as exc:  # noqa: BLE001
        return {
            "status": "FAIL",
            "detail": "Ctrl+A 快捷键发送失败",
            "elapsed_ms": (time.perf_counter() - started) * 1000,
            "exception": exc.__class__.__name__,
            "message": str(exc),
        }
    return {
        "status": "PASS" if result is None else "FAIL",
        "detail": "Ctrl+A 已发送并返回 None" if result is None else "返回值不是 None",
        "elapsed_ms": (time.perf_counter() - started) * 1000,
    }


def _print_result(
    index: int,
    label: str,
    call: str,
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
    print(f"[{index}/2] {badge} {label}")
    print(f"      调用: {call}")
    print(f"      结果: {result['detail']}  {result['elapsed_ms']:.1f}ms")
    if result.get("exception"):
        print(f"      异常: {result['exception']}: {result['message']}")


def main() -> int:
    color = "NO_COLOR" not in os.environ and sys.stdout.isatty()
    print(_color("UIAutoma Win32 API 测试", ANSI_CYAN, enabled=color))
    print()
    print("  API : uiautoma.win32.send_keys")
    print("  对象: 自动打开的记事本")
    print()

    try:
        process, path, handle, title = _launch_notepad()
    except Exception as exc:  # noqa: BLE001
        print(_color("[失败] 记事本准备失败", ANSI_RED, enabled=color))
        print(f"  异常: {exc.__class__.__name__}: {exc}")
        return 1

    print(f"  窗口: {title}")
    print(f"  句柄: {handle}")
    print(f"  PID : {process.pid}")
    print()

    started = time.perf_counter()
    plain = _run_plain_text()
    _print_result(
        1,
        "普通文本",
        'win32.send_keys("UIAutoma123", 50, 1, False, True)',
        plain,
        color=color,
    )
    hotkey = _run_ctrl_a()
    _print_result(
        2,
        "Ctrl+A 全选",
        'win32.send_keys("^a", 20, 0, True, False)',
        hotkey,
        color=color,
    )

    path_deleted = False
    try:
        path.unlink(missing_ok=True)
        path_deleted = True
    except OSError:
        pass

    results = [plain, hotkey]
    passed_count = sum(result["status"] == "PASS" for result in results)
    exit_code = 0 if passed_count == len(results) else 1
    elapsed_ms = (time.perf_counter() - started) * 1000
    print()
    summary = "测试通过" if exit_code == 0 else "测试失败"
    print(_color(summary, ANSI_GREEN if exit_code == 0 else ANSI_RED, enabled=color))
    print(f"  结果    : {passed_count}/2 通过")
    print(f"  总耗时  : {elapsed_ms:.1f}ms")
    print(f"  临时文件: {'已删除' if path_deleted else path}")
    print("  人工确认: 记事本中应显示并全选 UIAutoma123")
    print("  提示    : 请手动关闭记事本并选择不保存")
    print(f"  退出码  : {exit_code}")
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
