"""``uiautoma.win32.screenshot.save_window_to_file()`` 测试。

API 参数（不是测试脚本参数）::

    win32.screenshot.save_window_to_file(
        hwnd: int | str | None,
        image_path: str,
        image_format: str = "",
        left: int = 0,
        top: int = 0,
        right: int = 0,
        bottom: int = 0,
    ) -> str

``hwnd`` 和 ``image_path`` 是必填参数。``hwnd`` 可传整数、十进制字符串、十六进制
字符串；传 ``0``、``None`` 或空字符串时使用当前活动窗口。``image_format`` 支持
``png``、``jpg``、``jpeg`` 和 ``bmp``，为空时从扩展名推断。四个边界全为 ``0``
时截取整个窗口，否则边界是相对窗口左上角的像素坐标。

脚本自动打开记事本作为测试窗口，只调用目标 UIAutoma SDK API。生成的图片使用
Windows 自带 GDI+ 解码并验证格式、尺寸和非纯色内容；测试结束后关闭记事本并删除
临时文件和截图。不测试非法参数。
"""

from __future__ import annotations

import ctypes
import os
import shutil
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

WM_CLOSE = 0x0010
SW_RESTORE = 9
REGION = (50, 100, 450, 400)
WINDOW_POSITION = (180, 140)
WINDOW_SIZE = (900, 700)

IMAGE_LOCK_MODE_READ = 1
PIXEL_FORMAT_32BPP_ARGB = 0x26200A


class RECT(ctypes.Structure):
    _fields_ = [
        ("left", wintypes.LONG),
        ("top", wintypes.LONG),
        ("right", wintypes.LONG),
        ("bottom", wintypes.LONG),
    ]


class GDIP_STARTUP_INPUT(ctypes.Structure):
    _fields_ = [
        ("GdiplusVersion", ctypes.c_uint32),
        ("DebugEventCallback", ctypes.c_void_p),
        ("SuppressBackgroundThread", wintypes.BOOL),
        ("SuppressExternalCodecs", wintypes.BOOL),
    ]


class GDIP_RECT(ctypes.Structure):
    _fields_ = [
        ("X", ctypes.c_int),
        ("Y", ctypes.c_int),
        ("Width", ctypes.c_int),
        ("Height", ctypes.c_int),
    ]


class GDIP_BITMAP_DATA(ctypes.Structure):
    _fields_ = [
        ("Width", ctypes.c_uint),
        ("Height", ctypes.c_uint),
        ("Stride", ctypes.c_int),
        ("PixelFormat", ctypes.c_int),
        ("Scan0", ctypes.c_void_p),
        ("Reserved", ctypes.c_size_t),
    ]


ENUM_WINDOWS_CALLBACK = ctypes.WINFUNCTYPE(
    wintypes.BOOL,
    wintypes.HWND,
    wintypes.LPARAM,
)

_user32 = ctypes.WinDLL("user32", use_last_error=True)
_gdiplus = ctypes.WinDLL("gdiplus", use_last_error=True)

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

_gdiplus.GdiplusStartup.argtypes = [
    ctypes.POINTER(ctypes.c_size_t),
    ctypes.POINTER(GDIP_STARTUP_INPUT),
    ctypes.c_void_p,
]
_gdiplus.GdiplusStartup.restype = ctypes.c_int
_gdiplus.GdiplusShutdown.argtypes = [ctypes.c_size_t]
_gdiplus.GdiplusShutdown.restype = None
_gdiplus.GdipCreateBitmapFromFile.argtypes = [ctypes.c_wchar_p, ctypes.POINTER(ctypes.c_void_p)]
_gdiplus.GdipCreateBitmapFromFile.restype = ctypes.c_int
_gdiplus.GdipGetImageWidth.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_uint)]
_gdiplus.GdipGetImageWidth.restype = ctypes.c_int
_gdiplus.GdipGetImageHeight.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_uint)]
_gdiplus.GdipGetImageHeight.restype = ctypes.c_int
_gdiplus.GdipBitmapLockBits.argtypes = [
    ctypes.c_void_p,
    ctypes.POINTER(GDIP_RECT),
    ctypes.c_uint,
    ctypes.c_int,
    ctypes.POINTER(GDIP_BITMAP_DATA),
]
_gdiplus.GdipBitmapLockBits.restype = ctypes.c_int
_gdiplus.GdipBitmapUnlockBits.argtypes = [ctypes.c_void_p, ctypes.POINTER(GDIP_BITMAP_DATA)]
_gdiplus.GdipBitmapUnlockBits.restype = ctypes.c_int
_gdiplus.GdipDisposeImage.argtypes = [ctypes.c_void_p]
_gdiplus.GdipDisposeImage.restype = ctypes.c_int


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
        prefix="uiautoma-save-window-to-file-",
        suffix=".txt",
    )
    path = Path(raw_path)
    lines = [
        f"UIAutoma save_window_to_file test line {index:02d}"
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


def _detect_image_format(path: Path) -> str:
    signature = path.read_bytes()[:16]
    if signature.startswith(b"\x89PNG\r\n\x1a\n"):
        return "PNG"
    if signature.startswith(b"\xff\xd8"):
        return "JPEG"
    if signature.startswith(b"BM"):
        return "BMP"
    raise ValueError("无法识别图片文件格式")


def _gdip_check(status: int, operation: str) -> None:
    if status != 0:
        raise RuntimeError(f"{operation} 失败，GDI+ 状态码 {status}")


def _gdiplus_image_info(path: Path) -> dict[str, Any]:
    token = ctypes.c_size_t()
    startup = GDIP_STARTUP_INPUT(1, None, False, False)
    _gdip_check(_gdiplus.GdiplusStartup(ctypes.byref(token), ctypes.byref(startup), None), "GdiplusStartup")

    bitmap = ctypes.c_void_p()
    bitmap_data = GDIP_BITMAP_DATA()
    locked = False
    try:
        _gdip_check(
            _gdiplus.GdipCreateBitmapFromFile(str(path), ctypes.byref(bitmap)),
            "GdipCreateBitmapFromFile",
        )
        width = ctypes.c_uint()
        height = ctypes.c_uint()
        _gdip_check(_gdiplus.GdipGetImageWidth(bitmap, ctypes.byref(width)), "GdipGetImageWidth")
        _gdip_check(_gdiplus.GdipGetImageHeight(bitmap, ctypes.byref(height)), "GdipGetImageHeight")
        rect = GDIP_RECT(0, 0, int(width.value), int(height.value))
        _gdip_check(
            _gdiplus.GdipBitmapLockBits(
                bitmap,
                ctypes.byref(rect),
                IMAGE_LOCK_MODE_READ,
                PIXEL_FORMAT_32BPP_ARGB,
                ctypes.byref(bitmap_data),
            ),
            "GdipBitmapLockBits",
        )
        locked = True

        base = int(bitmap_data.Scan0 or 0)
        stride = int(bitmap_data.Stride)
        if base == 0 or stride == 0:
            raise RuntimeError("GDI+ 未返回有效像素缓冲区")

        first_color: bytes | None = None
        non_uniform = False
        row_bytes = int(width.value) * 4
        for row_index in range(int(height.value)):
            row = ctypes.string_at(base + row_index * stride, row_bytes)
            for offset in range(0, row_bytes, 4):
                color = row[offset : offset + 3]
                if first_color is None:
                    first_color = color
                elif color != first_color:
                    non_uniform = True
                    break
            if non_uniform:
                break

        return {
            "width": int(width.value),
            "height": int(height.value),
            "non_uniform": non_uniform,
        }
    finally:
        if locked:
            _gdiplus.GdipBitmapUnlockBits(bitmap, ctypes.byref(bitmap_data))
        if bitmap:
            _gdiplus.GdipDisposeImage(bitmap)
        if token.value:
            _gdiplus.GdiplusShutdown(token)


def _read_image_info(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise FileNotFoundError(f"截图文件不存在：{path}")
    decoded = _gdiplus_image_info(path)
    return {
        "format": _detect_image_format(path),
        "width": decoded["width"],
        "height": decoded["height"],
        "non_uniform": decoded["non_uniform"],
        "size_bytes": path.stat().st_size,
    }


def _run_case(
    label: str,
    call: str,
    invoke: Callable[[], str],
    *,
    handle: int,
    expected_path: Path,
    expected_format: str,
    expected_size: tuple[int, int],
) -> dict[str, Any]:
    started = time.perf_counter()
    try:
        if not _activate_window(handle):
            raise RuntimeError("调用前无法激活记事本窗口")
        returned = invoke()
        returned_path = Path(returned)
        image = _read_image_info(returned_path)
    except Exception as exc:  # noqa: BLE001
        return {
            "label": label,
            "status": "FAIL",
            "call": call,
            "detail": "窗口截图保存或图片校验失败",
            "expected_format": expected_format,
            "expected_size": expected_size,
            "expected_path": str(expected_path),
            "elapsed_ms": (time.perf_counter() - started) * 1000,
            "exception": exc.__class__.__name__,
            "message": str(exc),
        }

    elapsed_ms = (time.perf_counter() - started) * 1000
    actual_size = (image["width"], image["height"])
    return_ok = isinstance(returned, str)
    path_ok = returned_path.resolve() == expected_path.resolve()
    passed = (
        return_ok
        and path_ok
        and image["format"] == expected_format
        and actual_size == expected_size
        and image["non_uniform"]
        and image["size_bytes"] > 0
    )
    return {
        "label": label,
        "status": "PASS" if passed else "FAIL",
        "call": call,
        "detail": "返回路径、图片格式、尺寸和内容均符合预期" if passed else "保存结果与预期不一致",
        "expected_format": expected_format,
        "expected_size": expected_size,
        "expected_path": str(expected_path),
        "returned_path": returned,
        "actual_format": image["format"],
        "actual_size": actual_size,
        "non_uniform": image["non_uniform"],
        "size_bytes": image["size_bytes"],
        "return_type_ok": return_ok,
        "path_ok": path_ok,
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
    print(f"      预期: {result['expected_format']}，{expected[0]} x {expected[1]}，非纯色")
    if "actual_size" in result:
        actual = result["actual_size"]
        content = "非纯色" if result["non_uniform"] else "纯色"
        print(
            f"      实际: {result['actual_format']}，{actual[0]} x {actual[1]}，"
            f"{content}，{result['size_bytes']} bytes"
        )
        print(f"      返回: {result['returned_path']}")
    else:
        print("      实际: —")
    print(f"      结果: {result['detail']}  {result['elapsed_ms']:.1f}ms")
    if result.get("exception"):
        print(f"      异常: {result['exception']}: {result['message']}")


def main() -> int:
    _enable_dpi_awareness()
    color = "NO_COLOR" not in os.environ and sys.stdout.isatty()
    output_dir = Path(tempfile.mkdtemp(prefix="uiautoma-save-window-to-file-output-"))

    print(_color("UIAutoma Win32 API 测试", ANSI_CYAN, enabled=color))
    print()
    print("  API : uiautoma.win32.screenshot.save_window_to_file")
    print("  对象: 自动打开的记事本")
    print()

    try:
        process, source_path, handle, title, rect = _launch_notepad()
    except Exception as exc:  # noqa: BLE001
        shutil.rmtree(output_dir, ignore_errors=True)
        print(_color("[失败] 记事本准备失败", ANSI_RED, enabled=color))
        print(f"  异常: {exc.__class__.__name__}: {exc}")
        return 1

    window_size = (rect[2] - rect[0], rect[3] - rect[1])
    region_size = (REGION[2] - REGION[0], REGION[3] - REGION[1])
    actual_pid = _window_pid(handle)

    active_png = output_dir / "active_zero.png"
    none_png = output_dir / "none_explicit.png"
    empty_bmp = output_dir / "empty_inferred.bmp"
    int_jpg_requested = output_dir / "integer_jpg.png"
    int_jpg_actual = output_dir / "integer_jpg.jpg"
    decimal_jpeg_requested = output_dir / "decimal_jpeg.jpeg"
    decimal_jpeg_actual = output_dir / "decimal_jpeg.jpg"
    hex_bmp_requested = output_dir / "hex_bmp.png"
    hex_bmp_actual = output_dir / "hex_bmp.bmp"
    region_png = output_dir / "region.png"

    print(f"  窗口    : {title}")
    print(f"  句柄    : {handle} ({hex(handle)})")
    print(f"  PID     : {actual_pid}（启动命令 PID {process.pid}）")
    print(f"  窗口尺寸: {window_size[0]} x {window_size[1]}")
    print(f"  测试区域: {REGION} -> {region_size[0]} x {region_size[1]}")
    print("  输出目录: 临时目录（测试结束后删除）")
    print()

    cases = (
        (
            "活动窗口 PNG",
            'win32.screenshot.save_window_to_file(0, "<临时目录>\\active_zero.png")',
            lambda: win32.screenshot.save_window_to_file(0, str(active_png)),
            active_png,
            "PNG",
            window_size,
        ),
        (
            "None 显式 PNG",
            'win32.screenshot.save_window_to_file(None, "<临时目录>\\none_explicit.png", "png")',
            lambda: win32.screenshot.save_window_to_file(None, str(none_png), "png"),
            none_png,
            "PNG",
            window_size,
        ),
        (
            "空字符串推断 BMP",
            'win32.screenshot.save_window_to_file("", "<临时目录>\\empty_inferred.bmp")',
            lambda: win32.screenshot.save_window_to_file("", str(empty_bmp)),
            empty_bmp,
            "BMP",
            window_size,
        ),
        (
            "整数句柄 JPG",
            f'win32.screenshot.save_window_to_file({handle}, "<临时目录>\\integer_jpg.png", "jpg")',
            lambda: win32.screenshot.save_window_to_file(handle, str(int_jpg_requested), "jpg"),
            int_jpg_actual,
            "JPEG",
            window_size,
        ),
        (
            "十进制字符串 JPEG",
            f'win32.screenshot.save_window_to_file("{handle}", "<临时目录>\\decimal_jpeg.jpeg", "jpeg")',
            lambda: win32.screenshot.save_window_to_file(str(handle), str(decimal_jpeg_requested), "jpeg"),
            decimal_jpeg_actual,
            "JPEG",
            window_size,
        ),
        (
            "十六进制字符串 BMP",
            f'win32.screenshot.save_window_to_file("{hex(handle)}", "<临时目录>\\hex_bmp.png", "bmp")',
            lambda: win32.screenshot.save_window_to_file(hex(handle), str(hex_bmp_requested), "bmp"),
            hex_bmp_actual,
            "BMP",
            window_size,
        ),
        (
            "显式窗口区域",
            f'win32.screenshot.save_window_to_file({handle}, "<临时目录>\\region.png", "png", 50, 100, 450, 400)',
            lambda: win32.screenshot.save_window_to_file(handle, str(region_png), "png", *REGION),
            region_png,
            "PNG",
            region_size,
        ),
    )

    started = time.perf_counter()
    results: list[dict[str, Any]] = []
    total = len(cases)
    for index, (label, call, invoke, expected_path, expected_format, expected_size) in enumerate(cases, start=1):
        result = _run_case(
            label,
            call,
            invoke,
            handle=handle,
            expected_path=expected_path,
            expected_format=expected_format,
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

    source_deleted = False
    try:
        source_path.unlink(missing_ok=True)
        source_deleted = not source_path.exists()
    except OSError:
        source_deleted = False

    output_deleted = False
    try:
        shutil.rmtree(output_dir)
        output_deleted = not output_dir.exists()
    except OSError:
        output_deleted = False

    passed_count = sum(result["status"] == "PASS" for result in results)
    cleanup_ok = window_closed and source_deleted and output_deleted
    exit_code = 0 if passed_count == total and cleanup_ok else 1
    elapsed_ms = (time.perf_counter() - started) * 1000

    print()
    summary = "测试通过" if exit_code == 0 else "测试失败"
    print(_color(summary, ANSI_GREEN if exit_code == 0 else ANSI_RED, enabled=color))
    print(f"  结果    : {passed_count}/{total} 通过")
    print(f"  总耗时  : {elapsed_ms:.1f}ms")
    print(f"  临时截图: {'已删除' if output_deleted else '删除失败'}")
    print(f"  记事本  : {'已关闭' if window_closed else '关闭失败'}")
    print(f"  临时文件: {'已删除' if source_deleted else '删除失败'}")
    print(f"  退出码  : {exit_code}")
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
