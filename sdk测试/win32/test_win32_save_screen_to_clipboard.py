"""``uiautoma.win32.screenshot.save_screen_to_clipboard()`` 测试。

API 参数（不是测试脚本参数）::

    win32.screenshot.save_screen_to_clipboard(
        left: int = 0,
        top: int = 0,
        right: int = 0,
        bottom: int = 0,
    ) -> None

四个边界全部为 ``0`` 时截取完整虚拟桌面；指定区域时必须满足
``right > left`` 且 ``bottom > top``。脚本只调用目标 UIAutoma SDK API，使用原生
Win32 剪贴板 API 读取 ``CF_DIB`` 的位图头并验证截图尺寸。

不测试非法参数。测试结束后保留最后一次 ``400 x 300`` 区域截图，供人工粘贴查看。
"""

from __future__ import annotations

import ctypes
import os
import sys
import time
from ctypes import wintypes
from typing import Any

from uiautoma import win32


__test__ = False

CF_DIB = 8
SM_XVIRTUALSCREEN = 76
SM_YVIRTUALSCREEN = 77
SM_CXVIRTUALSCREEN = 78
SM_CYVIRTUALSCREEN = 79
REGION = (100, 100, 500, 400)

ANSI_GREEN = "\x1b[32m"
ANSI_RED = "\x1b[31m"
ANSI_CYAN = "\x1b[36m"
ANSI_RESET = "\x1b[0m"


class BITMAPINFOHEADER(ctypes.Structure):
    _fields_ = [
        ("biSize", wintypes.DWORD),
        ("biWidth", wintypes.LONG),
        ("biHeight", wintypes.LONG),
        ("biPlanes", wintypes.WORD),
        ("biBitCount", wintypes.WORD),
        ("biCompression", wintypes.DWORD),
        ("biSizeImage", wintypes.DWORD),
        ("biXPelsPerMeter", wintypes.LONG),
        ("biYPelsPerMeter", wintypes.LONG),
        ("biClrUsed", wintypes.DWORD),
        ("biClrImportant", wintypes.DWORD),
    ]


_user32 = ctypes.WinDLL("user32", use_last_error=True)
_kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

_user32.GetSystemMetrics.argtypes = [ctypes.c_int]
_user32.GetSystemMetrics.restype = ctypes.c_int
_user32.OpenClipboard.argtypes = [wintypes.HWND]
_user32.OpenClipboard.restype = wintypes.BOOL
_user32.CloseClipboard.argtypes = []
_user32.CloseClipboard.restype = wintypes.BOOL
_user32.IsClipboardFormatAvailable.argtypes = [wintypes.UINT]
_user32.IsClipboardFormatAvailable.restype = wintypes.BOOL
_user32.GetClipboardData.argtypes = [wintypes.UINT]
_user32.GetClipboardData.restype = wintypes.HANDLE
_kernel32.GlobalLock.argtypes = [wintypes.HANDLE]
_kernel32.GlobalLock.restype = ctypes.c_void_p
_kernel32.GlobalUnlock.argtypes = [wintypes.HANDLE]
_kernel32.GlobalUnlock.restype = wintypes.BOOL
_kernel32.GlobalSize.argtypes = [wintypes.HANDLE]
_kernel32.GlobalSize.restype = ctypes.c_size_t


def _enable_dpi_awareness() -> None:
    try:
        setter = _user32.SetProcessDpiAwarenessContext
        setter.argtypes = [ctypes.c_void_p]
        setter.restype = wintypes.BOOL
        setter(ctypes.c_void_p(-4))
    except (AttributeError, OSError):
        try:
            _user32.SetProcessDPIAware()
        except (AttributeError, OSError):
            pass


def _color(text: str, ansi: str, *, enabled: bool) -> str:
    return f"{ansi}{text}{ANSI_RESET}" if enabled else text


def _virtual_screen() -> tuple[int, int, int, int]:
    return (
        int(_user32.GetSystemMetrics(SM_XVIRTUALSCREEN)),
        int(_user32.GetSystemMetrics(SM_YVIRTUALSCREEN)),
        int(_user32.GetSystemMetrics(SM_CXVIRTUALSCREEN)),
        int(_user32.GetSystemMetrics(SM_CYVIRTUALSCREEN)),
    )


def _open_clipboard(*, timeout: float = 2.0) -> None:
    deadline = time.monotonic() + timeout
    while True:
        if _user32.OpenClipboard(None):
            return
        if time.monotonic() >= deadline:
            raise ctypes.WinError(ctypes.get_last_error())
        time.sleep(0.05)


def _clipboard_dib_info() -> dict[str, int]:
    _open_clipboard()
    handle: int | None = None
    pointer: int | None = None
    try:
        if not _user32.IsClipboardFormatAvailable(CF_DIB):
            raise RuntimeError("剪贴板中没有 CF_DIB 位图")
        raw_handle = _user32.GetClipboardData(CF_DIB)
        if not raw_handle:
            raise ctypes.WinError(ctypes.get_last_error())
        handle = int(raw_handle)
        if int(_kernel32.GlobalSize(raw_handle)) < ctypes.sizeof(BITMAPINFOHEADER):
            raise RuntimeError("剪贴板 CF_DIB 数据小于 BITMAPINFOHEADER")
        raw_pointer = _kernel32.GlobalLock(raw_handle)
        if not raw_pointer:
            raise ctypes.WinError(ctypes.get_last_error())
        pointer = int(raw_pointer)
        header = ctypes.cast(
            raw_pointer,
            ctypes.POINTER(BITMAPINFOHEADER),
        ).contents
        return {
            "header_size": int(header.biSize),
            "width": abs(int(header.biWidth)),
            "height": abs(int(header.biHeight)),
            "planes": int(header.biPlanes),
            "bit_count": int(header.biBitCount),
            "compression": int(header.biCompression),
        }
    finally:
        if handle is not None and pointer is not None:
            _kernel32.GlobalUnlock(wintypes.HANDLE(handle))
        _user32.CloseClipboard()


def _run_case(
    label: str,
    call: str,
    arguments: tuple[int, ...],
    expected_size: tuple[int, int],
) -> dict[str, Any]:
    started = time.perf_counter()
    try:
        result = win32.screenshot.save_screen_to_clipboard(*arguments)
        dib = _clipboard_dib_info()
    except Exception as exc:  # noqa: BLE001
        return {
            "label": label,
            "status": "FAIL",
            "call": call,
            "detail": "截图或剪贴板读取失败",
            "expected_size": expected_size,
            "elapsed_ms": (time.perf_counter() - started) * 1000,
            "exception": exc.__class__.__name__,
            "message": str(exc),
        }

    elapsed_ms = (time.perf_counter() - started) * 1000
    actual_size = (dib["width"], dib["height"])
    passed = result is None and actual_size == expected_size
    return {
        "label": label,
        "status": "PASS" if passed else "FAIL",
        "call": call,
        "detail": "截图已写入剪贴板且尺寸正确" if passed else "返回值或截图尺寸不符合预期",
        "expected_size": expected_size,
        "actual_size": actual_size,
        "dib": dib,
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
    expected = result["expected_size"]
    print(f"      预期: {expected[0]} x {expected[1]}")
    if "actual_size" in result:
        actual = result["actual_size"]
        print(f"      实际: {actual[0]} x {actual[1]}，CF_DIB {result['dib']['bit_count']} bit")
    else:
        print("      实际: —")
    print(f"      结果: {result['detail']}  {result['elapsed_ms']:.1f}ms")
    if result.get("exception"):
        print(f"      异常: {result['exception']}: {result['message']}")


def main() -> int:
    _enable_dpi_awareness()
    color = "NO_COLOR" not in os.environ and sys.stdout.isatty()
    virtual = _virtual_screen()
    region_size = (REGION[2] - REGION[0], REGION[3] - REGION[1])

    print(_color("UIAutoma Win32 API 测试", ANSI_CYAN, enabled=color))
    print()
    print("  API     : uiautoma.win32.screenshot.save_screen_to_clipboard")
    print(f"  虚拟桌面: ({virtual[0]}, {virtual[1]}) {virtual[2]} x {virtual[3]}")
    print(f"  测试区域: {REGION} -> {region_size[0]} x {region_size[1]}")
    print()

    cases = (
        (
            "完整虚拟桌面",
            "win32.screenshot.save_screen_to_clipboard()",
            (),
            (virtual[2], virtual[3]),
        ),
        (
            "指定屏幕区域",
            "win32.screenshot.save_screen_to_clipboard(100, 100, 500, 400)",
            REGION,
            region_size,
        ),
    )

    started = time.perf_counter()
    results: list[dict[str, Any]] = []
    total = len(cases)
    for index, (label, call, arguments, expected_size) in enumerate(cases, start=1):
        result = _run_case(label, call, arguments, expected_size)
        results.append(result)
        _print_result(index, total, result, color=color)

    passed_count = sum(result["status"] == "PASS" for result in results)
    exit_code = 0 if passed_count == total else 1
    elapsed_ms = (time.perf_counter() - started) * 1000
    print()
    summary = "测试通过" if exit_code == 0 else "测试失败"
    print(_color(summary, ANSI_GREEN if exit_code == 0 else ANSI_RED, enabled=color))
    print(f"  结果    : {passed_count}/{total} 通过")
    print(f"  总耗时  : {elapsed_ms:.1f}ms")
    print("  剪贴板  : 保留最后一次 400 x 300 区域截图")
    print("  人工确认: 可将剪贴板内容粘贴到画图或聊天窗口查看")
    print(f"  退出码  : {exit_code}")
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
