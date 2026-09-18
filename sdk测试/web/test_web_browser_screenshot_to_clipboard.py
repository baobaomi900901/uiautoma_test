"""WebBrowser.screenshot_to_clipboard() 页面对象 API 专项验收。

靶场：维护者的官方靶场 `https://baobaomi900901.github.io/xpath/#/form-controls`
（测试侧不自建页面）。

本 API 返回 `None`，所以「写进去了」不能靠返回值判定。脚本用 **ctypes 直接问 Windows**
读取剪贴板，且做三层独立校验：

1. **格式层**：调用后剪贴板必须出现 `CF_DIB`（`runtime/desktop/screen_capture.py`
   `copy_dib_to_clipboard()` 只 `SetClipboardData(CF_DIB)`；`CF_BITMAP`/`CF_DIBV5`
   由 Windows 自动合成）。
2. **结构层**：解析 `BITMAPINFOHEADER`（宽/高/位深/压缩方式/自下而上），
   并核对字节数必须精确等于 `40 + stride × height`。
3. **像素层**：把 DIB 像素解出来，与同页 `screenshot()` 产出的 PNG 文件截图
   **逐像素比对**（PNG 由脚本自带的纯标准库解码器解开，不使用任何第三方依赖）。
   为避免把偶发的单像素级渲染抖动当成缺陷，同时也不放过系统性偏差，比对做**三角确证**：
   同一参数连截两张文件图 A、B，再取剪贴板图 C，要求 C 与 A、B 的差异都不超过
   「A 与 B 的实测抖动 + 小抖动预算」，三者数值全部写进报告。

另外用**哨兵文本**证明剪贴板内容确实被本次调用改写（排除“读到上一次残留”的假通过），
并验证参数非法时剪贴板**不被触碰**（校验发生在写出之前）。

期望值来源：**活推导** —— 先用 `execute_javascript()` 读出
`documentElement.scrollWidth/scrollHeight` 与 `window.innerWidth/innerHeight`，
再与实际产出比对，不写死任何尺寸数字。

副作用与收尾：脚本会快照进入时的剪贴板文本/图像，结束时还原；若进入时剪贴板为空，
则保留最后一次验收截图（可直接 Ctrl+V 目视确认），并在报告中明确说明。
产物写入本工作区临时目录（`sdk测试/.pytest_tmp/<run_id>/`），结束时整目录删除。

退出码：0 = 全部 PASS；1 = 存在 FAIL；2 = 无非 FAIL 但存在 BLOCKED。
"""
from __future__ import annotations

import argparse
import ctypes
import inspect
import json
import shutil
import struct
import time
import uuid
import zlib
from ctypes import wintypes
from pathlib import Path
from urllib.parse import urlsplit

from uiautoma import ActionError, InvalidParamsError, web
from uiautoma.web import WebBrowser
from _web_page_identity import count_key, leaked, page_key

__test__ = False

DEFAULT_URL = "https://baobaomi900901.github.io/xpath/#/form-controls"
RUN_TMP_ROOT = Path(__file__).resolve().parents[1] / ".pytest_tmp"
PNG_MAGIC = b"\x89PNG\r\n\x1a\n"
CF_DIB, CF_UNICODETEXT = 8, 13
SENTINEL = "UIAUTOMA-CLIPBOARD-SENTINEL"
JITTER_BUDGET_BYTES = 64
"""像素比对的抖动预算（字节）。

实测页面在极低概率下会出现单像素级渲染抖动（曾观测到 3 / 15958344 字节），
因此除"文件截图 vs 剪贴板"外，再截一张同参数文件图测出当时的真实抖动
（`jitter`），许可差异 = `jitter + 本预算`。64 字节 ≈ 21 个像素，
占最小用例（2636×600）的 0.0014%，不足以掩盖系统性偏差。
"""
GREEN, RED, YELLOW, RESET = "\x1b[92m", "\x1b[91m", "\x1b[93m", "\x1b[0m"

_user32 = ctypes.WinDLL("user32", use_last_error=True)
_kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
_user32.OpenClipboard.argtypes = [wintypes.HWND]
_user32.OpenClipboard.restype = wintypes.BOOL
_user32.CloseClipboard.restype = wintypes.BOOL
_user32.EmptyClipboard.restype = wintypes.BOOL
_user32.GetClipboardData.argtypes = [wintypes.UINT]
_user32.GetClipboardData.restype = wintypes.HANDLE
_user32.SetClipboardData.argtypes = [wintypes.UINT, wintypes.HANDLE]
_user32.SetClipboardData.restype = wintypes.HANDLE
_user32.EnumClipboardFormats.argtypes = [wintypes.UINT]
_user32.EnumClipboardFormats.restype = wintypes.UINT
_kernel32.GlobalAlloc.argtypes = [wintypes.UINT, ctypes.c_size_t]
_kernel32.GlobalAlloc.restype = wintypes.HGLOBAL
_kernel32.GlobalLock.argtypes = [wintypes.HGLOBAL]
_kernel32.GlobalLock.restype = ctypes.c_void_p
_kernel32.GlobalUnlock.argtypes = [wintypes.HGLOBAL]
_kernel32.GlobalSize.argtypes = [wintypes.HGLOBAL]
_kernel32.GlobalSize.restype = ctypes.c_size_t


class ClipboardUnavailable(RuntimeError):
    """剪贴板被其他进程占用，读不到——环境问题，不是被测 API 的结论。"""


def result(case_id: str, status: str, detail: str, **extra):
    return {"case_id": case_id, "status": status, "detail": detail, **extra}


def same_url(actual: str, expected: str) -> bool:
    a, e = urlsplit(str(actual)), urlsplit(str(expected))
    return (
        a.scheme.casefold(), a.netloc.casefold(), a.path or "/", a.query, a.fragment
    ) == (
        e.scheme.casefold(), e.netloc.casefold(), e.path or "/", e.query, e.fragment
    )


def exception_name(exc: BaseException) -> str:
    return type(exc).__name__


def error_detail(prefix: str, exc: BaseException) -> str:
    trace_info = str(getattr(exc, "trace_info", "") or "")
    return f"{prefix}: {exception_name(exc)}: {exc}" + (f" [trace={trace_info}]" if trace_info else "")


# ---------------------------------------------------------------- 剪贴板（独立通道）


def _open_clipboard(retries: int = 20, delay: float = 0.25) -> None:
    for _ in range(retries):
        if _user32.OpenClipboard(None):
            return
        time.sleep(delay)
    raise ClipboardUnavailable(f"OpenClipboard 失败（被其他进程占用），GetLastError={ctypes.get_last_error()}")


def clipboard_formats() -> list[int]:
    _open_clipboard()
    try:
        found, current = [], 0
        while True:
            current = _user32.EnumClipboardFormats(current)
            if current == 0:
                return found
            found.append(int(current))
    finally:
        _user32.CloseClipboard()


def _read_format(data_format: int) -> bytes | None:
    _open_clipboard()
    try:
        handle = _user32.GetClipboardData(data_format)
        if not handle:
            return None
        size = _kernel32.GlobalSize(handle)
        pointer = _kernel32.GlobalLock(handle)
        if not pointer:
            raise ClipboardUnavailable(f"GlobalLock 失败，GetLastError={ctypes.get_last_error()}")
        try:
            return ctypes.string_at(pointer, size)
        finally:
            _kernel32.GlobalUnlock(handle)
    finally:
        _user32.CloseClipboard()


def read_dib() -> bytes | None:
    """读剪贴板 CF_DIB 原始字节（含 BITMAPINFOHEADER）。"""
    return _read_format(CF_DIB)


def read_text() -> str | None:
    raw = _read_format(CF_UNICODETEXT)
    return None if raw is None else raw.decode("utf-16-le").rstrip("\0")


def _set_format(data_format: int, payload: bytes) -> None:
    handle = _kernel32.GlobalAlloc(0x0002, len(payload))  # GMEM_MOVEABLE
    if not handle:
        raise ClipboardUnavailable("GlobalAlloc 失败")
    pointer = _kernel32.GlobalLock(handle)
    if not pointer:
        raise ClipboardUnavailable("GlobalLock 失败")
    ctypes.memmove(pointer, payload, len(payload))
    _kernel32.GlobalUnlock(handle)
    _open_clipboard()
    try:
        if not _user32.EmptyClipboard():
            raise ClipboardUnavailable("EmptyClipboard 失败")
        if not _user32.SetClipboardData(data_format, handle):
            raise ClipboardUnavailable("SetClipboardData 失败")
    finally:
        _user32.CloseClipboard()


def write_text(text: str) -> None:
    _set_format(CF_UNICODETEXT, (text + "\0").encode("utf-16-le"))


def write_dib(dib: bytes) -> None:
    _set_format(CF_DIB, dib)


def clear_clipboard() -> None:
    _open_clipboard()
    try:
        _user32.EmptyClipboard()
    finally:
        _user32.CloseClipboard()


def snapshot_clipboard() -> dict:
    """快照进入时的剪贴板文本/图像，供收尾还原。"""
    snapshot = {"formats": clipboard_formats(), "text": None, "dib": None}
    try:
        snapshot["text"] = read_text()
    except ClipboardUnavailable:
        pass
    try:
        if CF_DIB in snapshot["formats"]:
            snapshot["dib"] = read_dib()
    except ClipboardUnavailable:
        pass
    return snapshot


def restore_clipboard(snapshot: dict, fallback_dib: bytes | None = None) -> str:
    if snapshot.get("text") is not None:
        write_text(snapshot["text"])
        return "已还原进入时的剪贴板文本"
    if snapshot.get("dib"):
        write_dib(snapshot["dib"])
        return f"已还原进入时的剪贴板图像（{len(snapshot['dib'])} 字节 CF_DIB）"
    if fallback_dib:
        write_dib(fallback_dib)
        return (f"进入时剪贴板无文本/图像，保留最后一次验收截图"
                f"（{len(fallback_dib)} 字节 CF_DIB，可直接 Ctrl+V 目视确认）")
    return "进入时剪贴板无文本/图像，未改动"


# ---------------------------------------------------------------- DIB / PNG 解析


def dib_info(dib: bytes) -> dict:
    header_size, width, height, planes, bits, compression = struct.unpack("<IiiHHI", dib[:20])
    stride = ((width * bits // 8) + 3) // 4 * 4
    return {
        "header_size": header_size, "width": width, "height": abs(height), "planes": planes,
        "bit_count": bits, "compression": compression, "stride": stride,
        "top_down": height < 0, "expected_size": header_size + stride * abs(height),
        "actual_size": len(dib),
    }


def dib_rows(dib: bytes) -> tuple[int, int, list[bytes]]:
    """CF_DIB → (宽, 高, 自上而下 RGB 行)。"""
    info = dib_info(dib)
    if (info["bit_count"], info["compression"]) != (24, 0):
        raise ValueError(f"仅支持 24 位未压缩 DIB，实际 {info['bit_count']}bpp/压缩{info['compression']}")
    width, height, stride = info["width"], info["height"], info["stride"]
    body = dib[info["header_size"]:]
    rows = []
    for index in range(height):
        row = body[index * stride:index * stride + width * 3]
        rgb = bytearray(width * 3)
        rgb[0::3], rgb[1::3], rgb[2::3] = row[2::3], row[1::3], row[0::3]  # BGR → RGB
        rows.append(bytes(rgb))
    if not info["top_down"]:
        rows.reverse()
    return width, height, rows


def png_rows(path: Path) -> tuple[int, int, list[bytes]]:
    """最小 PNG 解码器：8bit、color type 2/6、非隔行 → 自上而下 RGB 行。"""
    raw = path.read_bytes()
    if raw[:8] != PNG_MAGIC:
        raise ValueError("不是 PNG")
    offset, idat, header = 8, bytearray(), None
    while offset < len(raw) - 8:
        length, kind = struct.unpack(">I4s", raw[offset:offset + 8])
        payload = raw[offset + 8:offset + 8 + length]
        if kind == b"IHDR":
            header = struct.unpack(">IIBBBBB", payload)
        elif kind == b"IDAT":
            idat += payload
        elif kind == b"IEND":
            break
        offset += 12 + length
    if header is None:
        raise ValueError("缺少 IHDR")
    width, height, depth, color, compression, filter_method, interlace = header
    if (depth, compression, filter_method, interlace) != (8, 0, 0, 0) or color not in (2, 6):
        raise ValueError(f"不支持的 PNG 形式: {header}")
    channels = 3 if color == 2 else 4
    stride = width * channels
    data = zlib.decompress(bytes(idat))
    rows, previous = [], bytearray(stride)
    for index in range(height):
        filter_type = data[index * (stride + 1)]
        line = bytearray(data[index * (stride + 1) + 1:(index + 1) * (stride + 1)])
        for position in range(stride):
            left = line[position - channels] if position >= channels else 0
            up = previous[position]
            up_left = previous[position - channels] if position >= channels else 0
            if filter_type == 1:
                line[position] = (line[position] + left) & 0xFF
            elif filter_type == 2:
                line[position] = (line[position] + up) & 0xFF
            elif filter_type == 3:
                line[position] = (line[position] + (left + up) // 2) & 0xFF
            elif filter_type == 4:
                estimate = left + up - up_left
                distances = (abs(estimate - left), abs(estimate - up), abs(estimate - up_left))
                predictor = (left, up, up_left)[distances.index(min(distances))]
                line[position] = (line[position] + predictor) & 0xFF
            elif filter_type != 0:
                raise ValueError(f"未知 PNG 过滤器 {filter_type}")
        rows.append(bytes(line) if channels == 3 else
                    bytes(bytearray(b for i, b in enumerate(line) if i % 4 != 3)))
        previous = line
    return width, height, rows


def image_info(path: Path):
    """独立解析产出的图片文件尺寸。"""
    try:
        data = path.read_bytes()
    except Exception as exc:  # noqa: BLE001
        return None, f"读取失败 {type(exc).__name__}"
    if data[:8] == PNG_MAGIC and len(data) >= 24:
        return struct.unpack(">II", data[16:24]), None
    return None, f"未知格式，前 4 字节={data[:4]!r}"


def pixel_diff(left: tuple, right: tuple) -> tuple[int, int, str]:
    lw, lh, lrows = left
    rw, rh, rrows = right
    if (lw, lh) != (rw, rh):
        return 0, 0, f"尺寸不同 {lw}×{lh} vs {rw}×{rh}"
    total = lw * lh * 3
    diff = sum(1 for a, b in zip(b"".join(lrows), b"".join(rrows)) if a != b)
    return diff, total, ""


# ---------------------------------------------------------------- 契约与用例


def check_contract():
    method = getattr(WebBrowser, "screenshot_to_clipboard", None)
    sig = inspect.signature(method) if callable(method) else None
    if sig is None:
        return result("api_contract", "FAIL", "WebBrowser.screenshot_to_clipboard 不存在")
    parameters = list(sig.parameters.values())
    names = tuple(sig.parameters)
    ok = (
        names == ("self", "full_size", "piece_height", "height")
        and all(p.kind is inspect.Parameter.KEYWORD_ONLY for p in parameters[1:])
        and parameters[1].default is True
        and parameters[2].default == 0
        and parameters[3].default == 0
        and str(sig.return_annotation) == "None"
    )
    detail = (
        "full_size / piece_height / height 均为仅限关键字（默认 True / 0 / 0）；无目录与文件名参数；"
        "返回注解 None" if ok else f"公开签名不符合合同: {sig}"
    )
    return result("api_contract", "PASS" if ok else "FAIL", detail)


def expect_raises(call, expected_type, label: str, message_contains: str = "",
                  max_elapsed: float | None = None):
    started = time.perf_counter()
    try:
        call()
    except expected_type as exc:
        elapsed = round(time.perf_counter() - started, 3)
        text = str(exc)
        if message_contains and message_contains not in text:
            return result(label, "FAIL", f"{exception_name(exc)} 消息不含 {message_contains!r}：{text}",
                          elapsed_s=elapsed)
        if max_elapsed is not None and elapsed > max_elapsed:
            return result(label, "FAIL", f"耗时过长：{elapsed}s > {max_elapsed}s（应在 SDK 侧立即拒绝）",
                          elapsed_s=elapsed)
        return result(label, "PASS", f"{exception_name(exc)} 正确拒绝（{elapsed}s）：{text}", elapsed_s=elapsed)
    except Exception as exc:  # noqa: BLE001
        return result(label, "FAIL",
                      f"拒绝类型错误，应为 {expected_type.__name__}: {exception_name(exc)}: {exc}")
    return result(label, "FAIL", "调用未被拒绝")


def clipboard_case(case_id: str, label: str, page, ref_root: Path, options: dict,
                   expected_size=None):
    """同一参数组合下，剪贴板 CF_DIB 必须与 screenshot() 的 PNG 文件截图逐像素一致。

    三角比对：先连截两张同参数文件图（A、B）测出当时的真实抖动，再取剪贴板图 C，
    要求 C 与 A、B 的差异都不超过「A 与 B 的差异 + 抖动预算」。
    """
    folder = ref_root / case_id
    try:
        page.screenshot(str(folder), file_name="reference-a.png", **options)
        page.screenshot(str(folder), file_name="reference-b.png", **options)
    except Exception as exc:  # noqa: BLE001
        return result(case_id, "FAIL", error_detail(f"{label} 参考文件截图失败", exc))
    reference_a, reference_b = folder / "reference-a.png", folder / "reference-b.png"
    if not reference_a.is_file() or not reference_b.is_file():
        return result(case_id, "FAIL", f"{label} 参考文件截图未产出预期文件")
    ref_size, error = image_info(reference_a)
    if error:
        return result(case_id, "FAIL", f"{label} 参考文件不可解析：{error}")
    if image_info(reference_b)[0] != ref_size:
        return result(case_id, "FAIL",
                      f"{label} 两次参考文件截图尺寸不一致：{ref_size} vs {image_info(reference_b)[0]}")
    if expected_size is not None and tuple(ref_size) != tuple(expected_size):
        return result(case_id, "FAIL",
                      f"{label} 参考文件尺寸与活推导不符：期望 {tuple(expected_size)}，实际 {ref_size}")

    started = time.perf_counter()
    try:
        returned = page.screenshot_to_clipboard(**options)
    except Exception as exc:  # noqa: BLE001
        return result(case_id, "FAIL", error_detail(f"{label} screenshot_to_clipboard 调用失败", exc))
    elapsed = round(time.perf_counter() - started, 3)
    if returned is not None:
        return result(case_id, "FAIL", f"{label} 应返回 None，实际 {returned!r}", elapsed_s=elapsed)
    try:
        dib = read_dib()
    except ClipboardUnavailable as exc:
        return result(case_id, "BLOCKED", f"{label} 无法读取剪贴板：{exc}")
    if not dib:
        return result(case_id, "FAIL", f"{label} 调用成功但剪贴板没有 CF_DIB", elapsed_s=elapsed)

    info = dib_info(dib)
    if (info["width"], info["height"]) != tuple(ref_size):
        return result(case_id, "FAIL",
                      f"{label} 剪贴板尺寸 {info['width']}×{info['height']} 与文件截图 {tuple(ref_size)} 不符",
                      elapsed_s=elapsed, dib=info)
    if info["actual_size"] != info["expected_size"]:
        return result(case_id, "FAIL",
                      f"{label} DIB 字节数不完整：{info['actual_size']} != 40 + {info['stride']}×{info['height']}",
                      elapsed_s=elapsed, dib=info)
    if (info["bit_count"], info["compression"], info["top_down"]) != (24, 0, False):
        return result(case_id, "FAIL",
                      f"{label} DIB 形式异常：{info['bit_count']}bpp/压缩{info['compression']}/"
                      f"top_down={info['top_down']}", elapsed_s=elapsed, dib=info)
    try:
        rows_a, rows_b = png_rows(reference_a), png_rows(reference_b)
        rows_c = dib_rows(dib)
    except Exception as exc:  # noqa: BLE001
        return result(case_id, "FAIL", f"{label} 像素解析失败：{exception_name(exc)}: {exc}", elapsed_s=elapsed)
    jitter, jitter_total, mismatch = pixel_diff(rows_a, rows_b)
    if mismatch:
        return result(case_id, "FAIL", f"{label} 参考文件像素比对失败：{mismatch}", elapsed_s=elapsed)
    diff_a, total, mismatch = pixel_diff(rows_a, rows_c)
    if mismatch:
        return result(case_id, "FAIL", f"{label} 像素比对失败：{mismatch}", elapsed_s=elapsed)
    diff_b, _, _ = pixel_diff(rows_b, rows_c)
    allowed = jitter + JITTER_BUDGET_BYTES
    if max(diff_a, diff_b) > allowed:
        return result(case_id, "FAIL",
                      f"{label} 剪贴板像素与文件截图不一致：与 A 差 {diff_a} 字节、与 B 差 {diff_b} 字节，"
                      f"允许 ≤ {allowed}（当时 A/B 抖动 {jitter} + 预算 {JITTER_BUDGET_BYTES}）",
                      elapsed_s=elapsed, pixel_diff_bytes=diff_a, pixel_diff_vs_second_bytes=diff_b,
                      pixel_jitter_bytes=jitter, pixel_total_bytes=total)
    jitter_note = (
        f"，与同参数第二次文件截图抖动同为 {jitter} 字节" if jitter else "，同参数两次文件截图零差异"
    )
    return result(
        case_id, "PASS",
        f"{label} 剪贴板 CF_DIB {info['width']}×{info['height']}、24bpp、{info['actual_size']} 字节精确吻合，"
        f"像素与文件截图差 {diff_a} 字节（{total} 字节中，{elapsed}s）{jitter_note}",
        elapsed_s=elapsed, width=info["width"], height=info["height"],
        dib_bytes=info["actual_size"], pixel_diff_bytes=diff_a,
        pixel_diff_vs_second_bytes=diff_b, pixel_jitter_bytes=jitter, pixel_total_bytes=total)


def run(args):
    results = [check_contract()]
    if results[-1]["status"] != "PASS" or args.contract_only:
        return results, 0 if results[-1]["status"] == "PASS" else 1

    run_id = uuid.uuid4().hex
    run_dir = RUN_TMP_ROOT / run_id
    ref_root = run_dir / "ref"
    page = None
    page_id = ""
    snapshot = {"formats": [], "text": None, "dib": None}
    restore_note = ""
    final_dib = None
    try:
        try:
            snapshot = snapshot_clipboard()
            readable = True
        except ClipboardUnavailable as exc:
            readable = False
            results.append(result("clipboard_readable", "BLOCKED",
                                  f"进入时无法读取剪贴板，后续剪贴板校验不可信：{exc}"))
            return results, 2
        if readable:
            results.append(result(
                "clipboard_readable", "PASS",
                f"ctypes 独立通道可读写剪贴板；进入时格式={snapshot['formats']}，"
                f"原文本={'有' if snapshot['text'] is not None else '无'}，"
                f"原图像={'有' if snapshot['dib'] else '无'}",
                formats=snapshot["formats"]))

        # 自检：脚本自身的“写入+还原”通道必须先证明可用，否则收尾还原不可信
        try:
            write_text(SENTINEL)
            ok_write = read_text() == SENTINEL
            restore_clipboard({"text": None, "dib": None})
            selftest_detail = (
                "脚本自身哨兵文本写入与读取一致；还原分支（无原内容时不清空剪贴板）已执行"
                if ok_write else "哨兵文本写入后读回不一致")
            results.append(result("clipboard_channel_selftest", "PASS" if ok_write else "FAIL", selftest_detail))
            if not ok_write:
                return results, 1
        except ClipboardUnavailable as exc:
            results.append(result("clipboard_channel_selftest", "BLOCKED", f"剪贴板通道不可用：{exc}"))
            return results, 2

        try:
            page = web.create(args.target_url, mode=args.mode, load_timeout=args.load_timeout)
            page_id = page_key(page)
            baseline_matches = count_key(page_id, args.mode)
            current = page.get_url()
            ok = isinstance(page, WebBrowser) and same_url(current, args.target_url)
            results.append(result(
                "page_prepare", "PASS" if ok else "FAIL",
                "已打开官方靶场页" if ok else f"URL 不符: {current!r}", url=current))
            if not ok:
                return results, 1
        except Exception as exc:  # noqa: BLE001
            results.append(result("page_prepare", "BLOCKED", error_detail("无法打开靶场页", exc)))
            return results, 2

        # 活推导：页面尺寸与视口尺寸
        try:
            metrics = page.execute_javascript(
                "function () { const el = document.documentElement;"
                " return {sh: el.scrollHeight, sw: el.scrollWidth,"
                " ih: window.innerHeight, iw: window.innerWidth}; }")
            ok = (
                isinstance(metrics, dict)
                and int(metrics.get("sh") or 0) > 0
                and int(metrics.get("sw") or 0) > 0
                and int(metrics.get("ih") or 0) > 0
            )
            results.append(result(
                "dom_expectations", "PASS" if ok else "FAIL",
                f"活推导页面尺寸 {metrics.get('sw')}×{metrics.get('sh')}，视口 {metrics.get('iw')}×{metrics.get('ih')}"
                if ok else f"无法取得页面尺寸: {metrics}", metrics=metrics))
            if not ok:
                return results, 1
            full_w, full_h = int(metrics["sw"]), int(metrics["sh"])
            view_h, view_w = int(metrics["ih"]), int(metrics["iw"])
        except Exception as exc:  # noqa: BLE001
            results.append(result("dom_expectations", "BLOCKED", error_detail("无法读取页面尺寸", exc)))
            return results, 2

        # 哨兵：调用前剪贴板是文本，调用后必须变成图像，证明内容确实被本次调用改写
        try:
            write_text(SENTINEL)
            before = {"text": read_text(), "dib": CF_DIB in clipboard_formats()}
            page.screenshot_to_clipboard()
            after = {"text": read_text(), "dib": CF_DIB in clipboard_formats()}
            ok = (
                before == {"text": SENTINEL, "dib": False}
                and after["text"] is None and after["dib"] is True
            )
            results.append(result(
                "sentinel_replaced", "PASS" if ok else "FAIL",
                "哨兵文本已消失且出现 CF_DIB，剪贴板内容确由本次调用改写" if ok else
                f"哨兵前后状态不符: before={before}, after={after}"))
        except ClipboardUnavailable as exc:
            results.append(result("sentinel_replaced", "BLOCKED", f"剪贴板通道不可用：{exc}"))
        except Exception as exc:  # noqa: BLE001
            results.append(result("sentinel_replaced", "FAIL", error_detail("哨兵用例执行失败", exc)))

        # 目标用例 1：默认整页
        results.append(clipboard_case(
            "default_full_page", "默认整页截图写入剪贴板", page, ref_root, {},
            expected_size=(full_w, full_h)))

        # 目标用例 2：仅视口（尺寸活推导自参考文件截图）
        results.append(clipboard_case(
            "viewport_only", "full_size=False 仅视口", page, ref_root, {"full_size": False}))
        viewport_case = results[-1]

        # 目标用例 3：height 限高
        results.append(clipboard_case(
            "height_clip", "height=600 限高", page, ref_root, {"height": 600},
            expected_size=(full_w, 600)))

        # 目标用例 4：piece_height 分段拼接
        results.append(clipboard_case(
            "piece_height_stitch", "piece_height=500 分段拼接", page, ref_root,
            {"piece_height": 500}, expected_size=(full_w, full_h)))

        # 目标用例 5：视口截图忽略 height（文档明确声明）
        results.append(clipboard_case(
            "viewport_ignores_height", "full_size=False 时 height 被忽略", page, ref_root,
            {"full_size": False, "height": 600}))
        both = results[-1]
        viewport_size = viewport_case.get("width"), viewport_case.get("height")
        if both["status"] == "PASS" and viewport_case["status"] == "PASS":
            if (both["width"], both["height"]) != viewport_size:
                results[-1] = result(
                    "viewport_ignores_height", "FAIL",
                    f"视口截图不应受 height 影响：仅视口 {viewport_size}，"
                    f"视口+height=600 得 {(both['width'], both['height'])}")
            else:
                results[-1]["detail"] += f"（与仅视口同为 {viewport_size[0]}×{viewport_size[1]}）"

        # 参数校验（均应在 SDK 侧立即拒绝，且不触碰剪贴板）
        try:
            final_dib = read_dib()
        except ClipboardUnavailable:
            final_dib = None
        results.append(expect_raises(
            lambda: page.screenshot_to_clipboard(full_size=1), InvalidParamsError,
            "full_size_non_bool", message_contains="full_size", max_elapsed=1.0))
        results.append(expect_raises(
            lambda: page.screenshot_to_clipboard(piece_height=-1), InvalidParamsError,
            "piece_height_negative", message_contains="piece_height", max_elapsed=1.0))
        results.append(expect_raises(
            lambda: page.screenshot_to_clipboard(piece_height=True), InvalidParamsError,
            "piece_height_bool", message_contains="piece_height", max_elapsed=1.0))
        results.append(expect_raises(
            lambda: page.screenshot_to_clipboard(height="x"), InvalidParamsError,
            "height_non_int", message_contains="height", max_elapsed=1.0))
        results.append(expect_raises(
            lambda: page.screenshot_to_clipboard(height=-1), InvalidParamsError,
            "height_negative", message_contains="height", max_elapsed=1.0))
        results.append(expect_raises(
            lambda: page.screenshot_to_clipboard("x"), TypeError,
            "positional_rejected", max_elapsed=1.0))
        results.append(expect_raises(
            lambda: page.screenshot_to_clipboard(folder="x"), TypeError,
            "unknown_kwarg_rejected", message_contains="folder", max_elapsed=1.0))

        # 参数非法时剪贴板不被触碰（校验发生在写出之前）
        try:
            write_text(SENTINEL)
            try:
                page.screenshot_to_clipboard(height=-5)
            except InvalidParamsError:
                pass
            untouched = read_text() == SENTINEL and CF_DIB not in clipboard_formats()
            results.append(result(
                "clipboard_untouched_on_invalid_param", "PASS" if untouched else "FAIL",
                "参数非法时剪贴板仍为哨兵文本且无 CF_DIB，校验发生在写出之前" if untouched else
                f"剪贴板被触碰: text={read_text()!r}, formats={clipboard_formats()}"))
        except ClipboardUnavailable as exc:
            results.append(result("clipboard_untouched_on_invalid_param", "BLOCKED", f"剪贴板通道不可用：{exc}"))

        # 页面失效后的行为：文档声称 ActionError
        write_text(SENTINEL)
        try:
            page.close(ignore_beforeunload=True)
        except Exception as exc:  # noqa: BLE001
            results.append(result("page_close_verified", "FAIL", error_detail("page.close 调用失败", exc)))
        else:
            time.sleep(0.5)
            leftover = leaked(page_id, baseline_matches, args.mode)
            ok = not leftover
            results.append(result(
                "page_close_verified", "PASS" if ok else "FAIL",
                "页面已关闭，且 web.get_all() 复核无残留" if ok else f"关闭后仍有残留: {len(leftover)}",
                leftover_pages=len(leftover)))
        results.append(expect_raises(
            lambda: page.screenshot_to_clipboard(), ActionError, "closed_page_error",
            message_contains="失效", max_elapsed=1.0))
        try:
            stayed = read_text() == SENTINEL and CF_DIB not in clipboard_formats()
            results.append(result(
                "clipboard_untouched_when_closed", "PASS" if stayed else "FAIL",
                "页面失效时剪贴板未被触碰" if stayed else
                f"页面失效却改动了剪贴板: text={read_text()!r}, formats={clipboard_formats()}"))
        except ClipboardUnavailable as exc:
            results.append(result("clipboard_untouched_when_closed", "BLOCKED", f"剪贴板通道不可用：{exc}"))
        page = None
    except Exception as exc:  # noqa: BLE001
        results.append(result("scenario", "FAIL", error_detail("screenshot_to_clipboard 场景执行失败", exc)))
    finally:
        page_close_error = ""
        if page is not None:
            try:
                page.close(ignore_beforeunload=True)
            except Exception as exc:  # noqa: BLE001
                page_close_error = f"{type(exc).__name__}: {exc}"
        produced = len([p for p in run_dir.rglob("*") if p.is_file()]) if run_dir.exists() else 0
        shutil.rmtree(run_dir, ignore_errors=True)
        leftover = []
        try:
            leftover = leaked(page_id, baseline_matches, args.mode)
        except Exception as exc:  # noqa: BLE001
            page_close_error = page_close_error or f"get_all 复核失败: {type(exc).__name__}: {exc}"
        try:
            restore_note = restore_clipboard(snapshot, final_dib)
            clipboard_error = ""
        except ClipboardUnavailable as exc:
            clipboard_error = str(exc)
        cleaned = not leftover and not page_close_error and not run_dir.exists() and not clipboard_error
        results.append(result(
            "cleanup", "PASS" if cleaned else "FAIL",
            f"已关闭页面（get_all 复核无残留）、删除本次截图目录（含 {produced} 个产物文件）；"
            f"剪贴板收尾：{restore_note}" if cleaned else
            f"清理不完整: 残留页面={len(leftover)}, close 错误={page_close_error or '无'}, "
            f"目录残留={run_dir.exists()}, 剪贴板错误={clipboard_error or '无'}",
            leftover_pages=len(leftover), produced_files=produced,
            page_close_error=page_close_error, clipboard_note=restore_note))

    statuses = {item["status"] for item in results}
    code = 1 if "FAIL" in statuses else (2 if "BLOCKED" in statuses else 0)
    return results, code


def main(argv=None):
    parser = argparse.ArgumentParser(description="WebBrowser.screenshot_to_clipboard() 页面对象 API 验收")
    parser.add_argument("--target-url", default=DEFAULT_URL, help="靶场页")
    parser.add_argument("--mode", choices=("chrome", "edge"), default="chrome")
    parser.add_argument("--load-timeout", type=float, default=20)
    parser.add_argument("--contract-only", action="store_true")
    parser.add_argument("--json", action="store_true", help="在表格后额外输出 JSON 报告（用于归档验收产物）")
    args = parser.parse_args(argv)
    if args.load_timeout <= 0:
        parser.error("--load-timeout 必须大于 0")

    results, code = run(args)
    print("UIAutoma Web API 测试")
    print("API     : uiautoma.web.WebBrowser.screenshot_to_clipboard")
    print(f"页面    : {args.target_url}")
    print("进度     状态    测试项                  测试结果")
    print("────────────────────────────────────────────────────────────────────────")
    for index, current in enumerate(results, 1):
        status = current["status"]
        color = {"PASS": GREEN, "BLOCKED": YELLOW}.get(status, RED)
        label = {"PASS": "通过", "BLOCKED": "阻塞"}.get(status, "失败")
        print(f"{index:02d}/{len(results):02d}    {color}[{label}]{RESET}  {current['case_id']:<34}  {current['detail']}")
    print("────────────────────────────────────────────────────────────────────────")
    summary = "测试通过" if code == 0 else ("测试阻塞" if code == 2 else "测试失败")
    print(f"{summary} · {sum(item['status'] == 'PASS' for item in results)}/{len(results)} 通过 · 退出码 {code}")
    if args.json:
        print(json.dumps({
            "api": "uiautoma.web.WebBrowser.screenshot_to_clipboard",
            "target_url": args.target_url, "mode": args.mode,
            "status": "PASS" if code == 0 else ("BLOCKED" if code == 2 else "FAIL"),
            "exit_code": code, "results": results,
        }, ensure_ascii=False, indent=2))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
