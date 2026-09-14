"""``uiautoma.win32.screenshot.save_window_to_clipboard()`` 测试。

API 参数（不是测试脚本参数）::

    win32.screenshot.save_window_to_clipboard(
        hwnd: int | str | None = 0,
        left: int = 0,
        top: int = 0,
        right: int = 0,
        bottom: int = 0,
    ) -> None

``hwnd`` 支持整数、十进制字符串和十六进制字符串；传 ``0``、``None`` 或空字符串
时使用当前活动窗口。四个边界全为 ``0`` 时截取整个窗口，否则边界是相对窗口左上角
的像素坐标。

脚本自动打开记事本作为测试窗口，只调用目标 UIAutoma SDK API。每次调用前使用原生
Win32 API 清空剪贴板，调用后读取 ``CF_DIB`` 文件头，验证截图尺寸、位深和像素内容。
最后保留区域截图供人工粘贴确认，并关闭记事本、删除临时文件。不测试非法参数。
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
from typing import Any, Callable

from uiautoma import win32


__test__ = False

ANSI_GREEN = "\x1b[32m"
ANSI_RED = "\x1b[31m"
ANSI_CYAN = "\x1b[36m"
ANSI_RESET = "\x1b[0m"

CF_DIB = 8
WM_CLOSE = 0x0010
SW_RESTORE = 9
REGION = (50, 100, 450, 400)
WINDOW_POSITION = (180, 140)
WINDOW_SIZE = (900, 700)


class RECT(ctypes.Structure):
    _fields_ = [
        ("left", wintypes.LONG),
        ("top", wintypes.LONG),
        ("right", wintypes.LONG),
        ("bottom", wintypes.LONG),
    ]


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


ENUM_WINDOWS_CALLBACK = ctypes.WINFUNCTYPE(
    wintypes.BOOL,
    wintypes.HWND,
    wintypes.LPARAM,
)

_user32 = ctypes.WinDLL("user32", use_last_error=True)
_kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

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
_user32.GetForegroundWindow.argtypes = []
_user32.GetForegroundWindow.restype = wintypes.HWND
_user32.ShowWindow.argtypes = [wintypes.HWND, ctypes.c_int]
_user32.ShowWindow.restype = wintypes.BOOL
_user32.BringWindowToTop.argtypes = [wintypes.HWND]
_user32.BringWindowToTop.restype = wintypes.BOOL
_user32.SetForegroundWindow.argtypes = [wintypes.HWND]
_user32.SetForegroundWindow.restype = wintypes.BOOL
_user32.MoveWindow.argtypes = [
    wintypes.HWND,
    ctypes.c_int,
    ctypes.c_int,
    ctypes.c_int,
    ctypes.c_int,
    wintypes.BOOL,
]
_user32.MoveWindow.restype = wintypes.BOOL
_user32.GetWindowRect.argtypes = [wintypes.HWND, ctypes.POINTER(RECT)]
_user32.GetWindowRect.restype = wintypes.BOOL
_user32.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
_user32.GetWindowThreadProcessId.restype = wintypes.DWORD
_user32.PostMessageW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
_user32.PostMessageW.restype = wintypes.BOOL
_user32.OpenClipboard.argtypes = [wintypes.HWND]
_user32.OpenClipboard.restype = wintypes.BOOL
_user32.EmptyClipboard.argtypes = []
_user32.EmptyClipboard.restype = wintypes.BOOL
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
        _user32.ShowWindow(hwnd, SW_RESTORE)
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


def _window_pid(handle: int) -> int:
    pid = wintypes.DWORD()
    _user32.GetWindowThreadProcessId(wintypes.HWND(handle), ctypes.byref(pid))
    return int(pid.value)


def _launch_notepad(
    *, timeout: float = 8.0
) -> tuple[subprocess.Popen[Any], Path, int, str, tuple[int, int, int, int]]:
    descriptor, raw_path = tempfile.mkstemp(
        prefix="uiautoma-save-window-to-clipboard-",
        suffix=".txt",
    )
    path = Path(raw_path)
    lines = [
        f"UIAutoma save_window_to_clipboard test line {index:02d}"
        for index in range(1, 41)
    ]
    with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
        stream.write("\n".join(lines))

    process: subprocess.Popen[Any] | None = None
    handle = 0
    try:
        process = subprocess.Popen(["notepad.exe", str(path)])
        deadline = time.monotonic() + timeout
        match: tuple[int, str] | None = None
        while time.monotonic() < deadline:
            match = _find_window(path.name)
            if match is not None:
                break
            time.sleep(0.1)
        if match is None:
            raise RuntimeError("记事本窗口未在超时内出现")

        handle, title = match
        hwnd = wintypes.HWND(handle)
        _user32.ShowWindow(hwnd, SW_RESTORE)
        if not _user32.MoveWindow(
            hwnd,
            WINDOW_POSITION[0],
            WINDOW_POSITION[1],
            WINDOW_SIZE[0],
            WINDOW_SIZE[1],
            True,
        ):
            raise ctypes.WinError(ctypes.get_last_error())
        time.sleep(0.2)
        if not _activate_window(handle):
            raise RuntimeError("无法激活记事本窗口")

        rect = _window_rect(handle)
        width = rect[2] - rect[0]
        height = rect[3] - rect[1]
        if width < REGION[2] or height < REGION[3]:
            raise RuntimeError(f"记事本窗口过小：{width} x {height}")
        return process, path, handle, title, rect
    except Exception:
        if handle > 0 and _user32.IsWindow(wintypes.HWND(handle)):
            _user32.PostMessageW(wintypes.HWND(handle), WM_CLOSE, 0, 0)
        if process is not None and process.poll() is None:
            process.terminate()
        path.unlink(missing_ok=True)
        raise


def _open_clipboard(*, timeout: float = 2.0) -> None:
    deadline = time.monotonic() + timeout
    while True:
        if _user32.OpenClipboard(None):
            return
        if time.monotonic() >= deadline:
            raise ctypes.WinError(ctypes.get_last_error())
        time.sleep(0.05)


def _clear_clipboard() -> None:
    _open_clipboard()
    try:
        if not _user32.EmptyClipboard():
            raise ctypes.WinError(ctypes.get_last_error())
    finally:
        _user32.CloseClipboard()


def _clipboard_dib_info() -> dict[str, Any]:
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
        data_size = int(_kernel32.GlobalSize(raw_handle))
        if data_size < ctypes.sizeof(BITMAPINFOHEADER):
            raise RuntimeError("剪贴板 CF_DIB 数据小于 BITMAPINFOHEADER")
        raw_pointer = _kernel32.GlobalLock(raw_handle)
        if not raw_pointer:
            raise ctypes.WinError(ctypes.get_last_error())
        pointer = int(raw_pointer)
        header = ctypes.cast(raw_pointer, ctypes.POINTER(BITMAPINFOHEADER)).contents
        raw = ctypes.string_at(raw_pointer, data_size)
        pixel_offset = max(int(header.biSize), ctypes.sizeof(BITMAPINFOHEADER))
        pixels = raw[pixel_offset:]
        first_color = pixels[:3]
        non_uniform = bool(first_color) and any(
            pixels[index : index + 3] != first_color
            for index in range(0, max(0, len(pixels) - 3), 4)
        )
        return {
            "width": abs(int(header.biWidth)),
            "height": abs(int(header.biHeight)),
            "planes": int(header.biPlanes),
            "bit_count": int(header.biBitCount),
            "compression": int(header.biCompression),
            "size_bytes": data_size,
            "non_uniform": non_uniform,
        }
    finally:
        if handle is not None and pointer is not None:
            _kernel32.GlobalUnlock(wintypes.HANDLE(handle))
        _user32.CloseClipboard()


def _run_case(
    label: str,
    call: str,
    invoke: Callable[[], None],
    *,
    handle: int,
    expected_size: tuple[int, int],
) -> dict[str, Any]:
    started = time.perf_counter()
    try:
        if not _activate_window(handle):
            raise RuntimeError("调用前无法激活记事本窗口")
        _clear_clipboard()
        returned = invoke()
        dib = _clipboard_dib_info()
    except Exception as exc:  # noqa: BLE001
        return {
            "label": label,
            "status": "FAIL",
            "call": call,
            "detail": "窗口截图或剪贴板读取失败",
            "expected_size": expected_size,
            "elapsed_ms": (time.perf_counter() - started) * 1000,
            "exception": exc.__class__.__name__,
            "message": str(exc),
        }

    elapsed_ms = (time.perf_counter() - started) * 1000
    actual_size = (dib["width"], dib["height"])
    passed = (
        returned is None
        and actual_size == expected_size
        and dib["planes"] == 1
        and dib["bit_count"] == 32
        and dib["compression"] == 0
        and dib["non_uniform"]
    )
    return {
        "label": label,
        "status": "PASS" if passed else "FAIL",
        "call": call,
        "detail": "窗口截图已写入剪贴板且尺寸正确" if passed else "返回值或 CF_DIB 内容不符合预期",
        "expected_size": expected_size,
        "actual_size": actual_size,
        "dib": dib,
        "return_value": returned,
        "elapsed_ms": elapsed_ms,
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
    expected = result["expected_size"]
    print(f"      预期: {expected[0]} x {expected[1]}，CF_DIB 32 bit，非纯色")
    if "actual_size" in result:
        actual = result["actual_size"]
        dib = result["dib"]
        content = "非纯色" if dib["non_uniform"] else "纯色"
        print(
            f"      实际: {actual[0]} x {actual[1]}，CF_DIB {dib['bit_count']} bit，"
            f"{content}，{dib['size_bytes']} bytes"
        )
    else:
        print("      实际: —")
    print(f"      结果: {result['detail']}  {result['elapsed_ms']:.1f}ms")
    if result.get("exception"):
        print(f"      异常: {result['exception']}: {result['message']}")


def main() -> int:
    _enable_dpi_awareness()
    color = "NO_COLOR" not in os.environ and sys.stdout.isatty()

    print(_color("UIAutoma Win32 API 测试", ANSI_CYAN, enabled=color))
    print()
    print("  API : uiautoma.win32.screenshot.save_window_to_clipboard")
    print("  对象: 自动打开的记事本")
    print()

    try:
        process, path, handle, title, rect = _launch_notepad()
    except Exception as exc:  # noqa: BLE001
        print(_color("[失败] 记事本准备失败", ANSI_RED, enabled=color))
        print(f"  异常: {exc.__class__.__name__}: {exc}")
        return 1

    window_size = (rect[2] - rect[0], rect[3] - rect[1])
    region_size = (REGION[2] - REGION[0], REGION[3] - REGION[1])
    actual_pid = _window_pid(handle)

    print(f"  窗口    : {title}")
    print(f"  句柄    : {handle} ({hex(handle)})")
    print(f"  PID     : {actual_pid}（启动命令 PID {process.pid}）")
    print(f"  窗口尺寸: {window_size[0]} x {window_size[1]}")
    print(f"  测试区域: {REGION} -> {region_size[0]} x {region_size[1]}")
    print()

    cases = (
        (
            "默认活动窗口",
            "win32.screenshot.save_window_to_clipboard()",
            lambda: win32.screenshot.save_window_to_clipboard(),
            window_size,
        ),
        (
            "None 活动窗口",
            "win32.screenshot.save_window_to_clipboard(None)",
            lambda: win32.screenshot.save_window_to_clipboard(None),
            window_size,
        ),
        (
            "空字符串活动窗口",
            'win32.screenshot.save_window_to_clipboard("")',
            lambda: win32.screenshot.save_window_to_clipboard(""),
            window_size,
        ),
        (
            "整数句柄",
            f"win32.screenshot.save_window_to_clipboard({handle})",
            lambda: win32.screenshot.save_window_to_clipboard(handle),
            window_size,
        ),
        (
            "十进制字符串",
            f'win32.screenshot.save_window_to_clipboard("{handle}")',
            lambda: win32.screenshot.save_window_to_clipboard(str(handle)),
            window_size,
        ),
        (
            "十六进制字符串",
            f'win32.screenshot.save_window_to_clipboard("{hex(handle)}")',
            lambda: win32.screenshot.save_window_to_clipboard(hex(handle)),
            window_size,
        ),
        (
            "显式窗口区域",
            f"win32.screenshot.save_window_to_clipboard({handle}, 50, 100, 450, 400)",
            lambda: win32.screenshot.save_window_to_clipboard(handle, *REGION),
            region_size,
        ),
    )

    started = time.perf_counter()
    results: list[dict[str, Any]] = []
    total = len(cases)
    for index, (label, call, invoke, expected_size) in enumerate(cases, start=1):
        result = _run_case(
            label,
            call,
            invoke,
            handle=handle,
            expected_size=expected_size,
        )
        results.append(result)
        _print_result(index, total, result, color=color)

    window_closed = _close_window(handle)
    if not window_closed and process.poll() is None:
        process.terminate()
        try:
            process.wait(timeout=2.0)
        except subprocess.TimeoutExpired:
            process.kill()
        window_closed = not _user32.IsWindow(wintypes.HWND(handle))

    path_deleted = False
    try:
        path.unlink(missing_ok=True)
        path_deleted = not path.exists()
    except OSError:
        path_deleted = False

    passed_count = sum(result["status"] == "PASS" for result in results)
    cleanup_ok = window_closed and path_deleted
    exit_code = 0 if passed_count == total and cleanup_ok else 1
    elapsed_ms = (time.perf_counter() - started) * 1000

    print()
    summary = "测试通过" if exit_code == 0 else "测试失败"
    print(_color(summary, ANSI_GREEN if exit_code == 0 else ANSI_RED, enabled=color))
    print(f"  结果    : {passed_count}/{total} 通过")
    print(f"  总耗时  : {elapsed_ms:.1f}ms")
    print("  剪贴板  : 保留最后一次 400 x 300 区域截图")
    print("  人工确认: 可将剪贴板内容粘贴到画图或聊天窗口查看")
    print(f"  记事本  : {'已关闭' if window_closed else '关闭失败'}")
    print(f"  临时文件: {'已删除' if path_deleted else '删除失败'}")
    print(f"  退出码  : {exit_code}")
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
