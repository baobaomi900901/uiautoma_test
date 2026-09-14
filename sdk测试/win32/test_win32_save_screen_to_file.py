"""``uiautoma.win32.screenshot.save_screen_to_file()`` 测试。

API 参数（不是测试脚本参数）::

    win32.screenshot.save_screen_to_file(
        image_path: str,
        image_format: str = "",
        left: int = 0,
        top: int = 0,
        right: int = 0,
        bottom: int = 0,
    ) -> str

``image_format`` 支持 ``png``、``jpg``、``jpeg`` 和 ``bmp``；为空时根据
``image_path`` 的扩展名推断。四个边界全部为 ``0`` 时截取完整虚拟桌面，否则区域
必须满足 ``right > left`` 且 ``bottom > top``。

脚本只调用目标 UIAutoma SDK API。生成的图片会通过文件头验证格式和像素尺寸，并在
测试结束后删除临时目录。不测试非法参数。
"""

from __future__ import annotations

import ctypes
import os
import shutil
import sys
import tempfile
import time
from ctypes import wintypes
from pathlib import Path
from typing import Any, Callable

from uiautoma import win32


__test__ = False

SM_XVIRTUALSCREEN = 76
SM_YVIRTUALSCREEN = 77
SM_CXVIRTUALSCREEN = 78
SM_CYVIRTUALSCREEN = 79
REGION = (100, 100, 500, 400)

ANSI_GREEN = "\x1b[32m"
ANSI_RED = "\x1b[31m"
ANSI_CYAN = "\x1b[36m"
ANSI_RESET = "\x1b[0m"

JPEG_SOF_MARKERS = {
    0xC0,
    0xC1,
    0xC2,
    0xC3,
    0xC5,
    0xC6,
    0xC7,
    0xC9,
    0xCA,
    0xCB,
    0xCD,
    0xCE,
    0xCF,
}

_user32 = ctypes.WinDLL("user32", use_last_error=True)
_user32.GetSystemMetrics.argtypes = [ctypes.c_int]
_user32.GetSystemMetrics.restype = ctypes.c_int


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


def _jpeg_size(data: bytes) -> tuple[int, int]:
    position = 2
    while position < len(data):
        if data[position] != 0xFF:
            position += 1
            continue
        while position < len(data) and data[position] == 0xFF:
            position += 1
        if position >= len(data):
            break

        marker = data[position]
        position += 1
        if marker in {0x01, 0xD8, 0xD9} or 0xD0 <= marker <= 0xD7:
            continue
        if position + 2 > len(data):
            break

        segment_length = int.from_bytes(data[position : position + 2], "big")
        if segment_length < 2 or position + segment_length > len(data):
            break
        if marker in JPEG_SOF_MARKERS:
            if segment_length < 7:
                break
            height = int.from_bytes(data[position + 3 : position + 5], "big")
            width = int.from_bytes(data[position + 5 : position + 7], "big")
            return width, height
        position += segment_length

    raise ValueError("JPEG 文件中没有有效的 SOF 尺寸信息")


def _read_image_info(path: Path) -> dict[str, Any]:
    data = path.read_bytes()
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        if len(data) < 24 or data[12:16] != b"IHDR":
            raise ValueError("PNG 文件头不完整")
        width = int.from_bytes(data[16:20], "big")
        height = int.from_bytes(data[20:24], "big")
        image_format = "PNG"
    elif data.startswith(b"BM"):
        if len(data) < 26:
            raise ValueError("BMP 文件头不完整")
        width = abs(int.from_bytes(data[18:22], "little", signed=True))
        height = abs(int.from_bytes(data[22:26], "little", signed=True))
        image_format = "BMP"
    elif data.startswith(b"\xff\xd8"):
        width, height = _jpeg_size(data)
        image_format = "JPEG"
    else:
        raise ValueError("无法识别图片文件格式")

    return {
        "format": image_format,
        "width": width,
        "height": height,
        "size_bytes": len(data),
    }


def _run_case(
    label: str,
    call: str,
    invoke: Callable[[], str],
    expected_path: Path,
    expected_format: str,
    expected_size: tuple[int, int],
) -> dict[str, Any]:
    started = time.perf_counter()
    try:
        returned = invoke()
        returned_path = Path(returned)
        image = _read_image_info(returned_path)
    except Exception as exc:  # noqa: BLE001
        return {
            "label": label,
            "status": "FAIL",
            "call": call,
            "detail": "截图保存或图片校验失败",
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
    format_ok = image["format"] == expected_format
    size_ok = actual_size == expected_size
    passed = return_ok and path_ok and format_ok and size_ok and image["size_bytes"] > 0
    return {
        "label": label,
        "status": "PASS" if passed else "FAIL",
        "call": call,
        "detail": "返回路径、图片格式和尺寸均符合预期" if passed else "保存结果与预期不一致",
        "expected_format": expected_format,
        "expected_size": expected_size,
        "expected_path": str(expected_path),
        "returned_path": returned,
        "actual_format": image["format"],
        "actual_size": actual_size,
        "size_bytes": image["size_bytes"],
        "return_type_ok": return_ok,
        "path_ok": path_ok,
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
    print(f"      预期: {result['expected_format']}，{expected[0]} x {expected[1]}")
    if "actual_size" in result:
        actual = result["actual_size"]
        print(
            f"      实际: {result['actual_format']}，{actual[0]} x {actual[1]}，"
            f"{result['size_bytes']} bytes"
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
    virtual = _virtual_screen()
    full_size = (virtual[2], virtual[3])
    region_size = (REGION[2] - REGION[0], REGION[3] - REGION[1])
    output_dir = Path(tempfile.mkdtemp(prefix="uiautoma-save-screen-to-file-"))

    full_png = output_dir / "full_screen.png"
    region_png = output_dir / "region.png"
    jpg_requested = output_dir / "explicit_jpg.png"
    jpg_actual = output_dir / "explicit_jpg.jpg"
    jpeg_requested = output_dir / "jpeg_alias.jpeg"
    jpeg_actual = output_dir / "jpeg_alias.jpg"
    inferred_bmp = output_dir / "inferred.bmp"

    print(_color("UIAutoma Win32 API 测试", ANSI_CYAN, enabled=color))
    print()
    print("  API     : uiautoma.win32.screenshot.save_screen_to_file")
    print(f"  虚拟桌面: ({virtual[0]}, {virtual[1]}) {virtual[2]} x {virtual[3]}")
    print(f"  测试区域: {REGION} -> {region_size[0]} x {region_size[1]}")
    print("  输出目录: 临时目录（测试结束后删除）")
    print()

    cases = (
        (
            "默认完整桌面 PNG",
            'win32.screenshot.save_screen_to_file("<临时目录>\\full_screen.png")',
            lambda: win32.screenshot.save_screen_to_file(str(full_png)),
            full_png,
            "PNG",
            full_size,
        ),
        (
            "显式区域 PNG",
            'win32.screenshot.save_screen_to_file("<临时目录>\\region.png", "png", 100, 100, 500, 400)',
            lambda: win32.screenshot.save_screen_to_file(str(region_png), "png", *REGION),
            region_png,
            "PNG",
            region_size,
        ),
        (
            "显式 JPG",
            'win32.screenshot.save_screen_to_file("<临时目录>\\explicit_jpg.png", "jpg", 100, 100, 500, 400)',
            lambda: win32.screenshot.save_screen_to_file(str(jpg_requested), "jpg", *REGION),
            jpg_actual,
            "JPEG",
            region_size,
        ),
        (
            "JPEG 别名",
            'win32.screenshot.save_screen_to_file("<临时目录>\\jpeg_alias.jpeg", "jpeg", 100, 100, 500, 400)',
            lambda: win32.screenshot.save_screen_to_file(str(jpeg_requested), "jpeg", *REGION),
            jpeg_actual,
            "JPEG",
            region_size,
        ),
        (
            "扩展名推断 BMP",
            'win32.screenshot.save_screen_to_file("<临时目录>\\inferred.bmp", left=100, top=100, right=500, bottom=400)',
            lambda: win32.screenshot.save_screen_to_file(
                str(inferred_bmp),
                left=REGION[0],
                top=REGION[1],
                right=REGION[2],
                bottom=REGION[3],
            ),
            inferred_bmp,
            "BMP",
            region_size,
        ),
    )

    started = time.perf_counter()
    results: list[dict[str, Any]] = []
    cleanup_error = ""
    try:
        total = len(cases)
        for index, case in enumerate(cases, start=1):
            result = _run_case(*case)
            results.append(result)
            _print_result(index, total, result, color=color)
    finally:
        try:
            shutil.rmtree(output_dir)
        except Exception as exc:  # noqa: BLE001
            cleanup_error = f"{exc.__class__.__name__}: {exc}"

    cleanup_ok = not output_dir.exists()
    passed_count = sum(result["status"] == "PASS" for result in results)
    exit_code = 0 if passed_count == len(cases) and cleanup_ok else 1
    elapsed_ms = (time.perf_counter() - started) * 1000

    print()
    summary = "测试通过" if exit_code == 0 else "测试失败"
    print(_color(summary, ANSI_GREEN if exit_code == 0 else ANSI_RED, enabled=color))
    print(f"  结果    : {passed_count}/{len(cases)} 通过")
    print(f"  总耗时  : {elapsed_ms:.1f}ms")
    print(f"  临时截图: {'已删除' if cleanup_ok else '删除失败'}")
    if cleanup_error:
        print(f"  清理异常: {cleanup_error}")
    print(f"  退出码  : {exit_code}")
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
