"""WebElement.screenshot_to_clipboard() 元素对象 API 专项验收。

前置（元素库与靶场）：
- 元素库：`D:\\code\\元素库\\260902_web元素`（Schema2，70 个 web 元素）
- 靶场：维护者的官方靶场（测试侧不自建页面）
  - `https://baobaomi900901.github.io/xpath/#/iframe-shadow-form`（库元素所属页面）
  - `https://baobaomi900901.github.io/xpath/#/form-controls`（主框架取景验证用）
- 元素库**复制到本工作区 `.pytest_tmp/<run_id>/` 后再打开**，结束时删除，绝不写入用户原件。

本 API 返回 `None`，「写进去了」不能靠返回值判定。脚本用 `ctypes` 走**与产品无关的通道**
直读剪贴板，做四层独立校验：

1. **格式层**：调用后剪贴板必须出现 `CF_DIB`。
2. **结构层**：解析 `BITMAPINFOHEADER`（宽/高/位深/压缩方式/朝向），
   并核对字节数精确等于 `40 + stride × height`。
3. **像素层**：独立解开 `CF_DIB` 与元素文件截图 `WebElement.screenshot()` 的 PNG
   （纯标准库解码器，无第三方依赖），逐像素比对；用「同参数连截 A、B 两张文件图」
   实测当时抖动，再与剪贴板图 C 做**三角比对**，避免把偶发的单像素抖动当成缺陷。
4. **取景层**：在主框架上用 `getBoundingClientRect()` **活推导**元素的页面矩形，
   把页面整页截图按该矩形裁切，与元素截图做**偏移扫描**——最小区块差异必须出现在
   偏移 `(0, 0)`，否则就是取景偏移（这正是元素级截图历史缺陷 Issue #20 的判据）。

另用**哨兵文本**证明剪贴板内容确由本次调用改写，并验证元素失效后立即在 SDK 侧拒绝。

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

import uiautoma
from uiautoma import ActionError, web
from uiautoma.web import WebBrowser, WebElement

__test__ = False

DEFAULT_URL = "https://baobaomi900901.github.io/xpath/#/iframe-shadow-form"
FRAMING_URL = "https://baobaomi900901.github.io/xpath/#/form-controls"
FRAMING_SELECTOR = "#form-controls-ant-submit"
DEFAULT_LIBRARY = Path(r"D:\code\元素库\260902_web元素")
FIRST_ELEMENT = "web靶场_表单测试_ant_输入框"
SECOND_ELEMENT = "web靶场_表单测试_ant_数字输入框"
LIB_TMP_ROOT = Path(__file__).resolve().parents[1] / ".pytest_tmp"
PNG_MAGIC = b"\x89PNG\r\n\x1a\n"
CF_DIB, CF_UNICODETEXT = 8, 13
SENTINEL = "UIAUTOMA-CLIPBOARD-SENTINEL"
JITTER_BUDGET_BYTES = 64
"""像素比对的抖动预算（字节）：许可差异 = 实测抖动 + 本预算（详见证据文档）。"""
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


def snapshot_clipboard() -> dict:
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


def image_size(path: Path):
    """独立解析 PNG 文件尺寸。"""
    try:
        data = path.read_bytes()
    except Exception as exc:  # noqa: BLE001
        return None, f"读取失败 {type(exc).__name__}"
    if data[:8] == PNG_MAGIC and len(data) >= 24:
        return struct.unpack(">II", data[16:24]), None
    return None, f"未知格式，前 4 字节={data[:4]!r}"


def byte_diff(left: tuple, right: tuple) -> tuple[int, int, str]:
    lw, lh, lrows = left
    rw, rh, rrows = right
    if (lw, lh) != (rw, rh):
        return 0, 0, f"尺寸不同 {lw}×{lh} vs {rw}×{rh}"
    total = lw * lh * 3
    diff = sum(1 for a, b in zip(b"".join(lrows), b"".join(rrows)) if a != b)
    return diff, total, ""


def crop(rows: tuple, x: int, y: int, width: int, height: int) -> tuple:
    row_width, row_height, lines = rows
    if x < 0 or y < 0 or x + width > row_width or y + height > row_height:
        return 0, 0, []
    return width, height, [line[x * 3:(x + width) * 3] for line in lines[y:y + height]]


# ---------------------------------------------------------------- 契约与用例


def check_contract():
    method = getattr(WebElement, "screenshot_to_clipboard", None)
    sig = inspect.signature(method) if callable(method) else None
    if sig is None:
        return result("api_contract", "FAIL", "WebElement.screenshot_to_clipboard 不存在")
    names = tuple(sig.parameters)
    ok = names == ("self",) and str(sig.return_annotation) == "None"
    detail = (
        "无任何参数（不含目录/文件名）；返回注解 None" if ok else f"公开签名不符合合同: {sig}"
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


def element_case(case_id: str, label: str, element, folder: Path, expected_size=None):
    """元素剪贴板 CF_DIB 必须与同元素的文件截图逐像素一致（三角比对）。"""
    shutil.rmtree(folder, ignore_errors=True)
    try:
        element.screenshot(str(folder), file_name="reference-a.png")
        element.screenshot(str(folder), file_name="reference-b.png")
    except Exception as exc:  # noqa: BLE001
        return result(case_id, "FAIL", error_detail(f"{label} 参考文件截图失败", exc))
    reference_a, reference_b = folder / "reference-a.png", folder / "reference-b.png"
    if not reference_a.is_file() or not reference_b.is_file():
        return result(case_id, "FAIL", f"{label} 参考文件截图未产出预期文件")
    ref_size, error = image_size(reference_a)
    if error:
        return result(case_id, "FAIL", f"{label} 参考文件不可解析：{error}")
    if image_size(reference_b)[0] != ref_size:
        return result(case_id, "FAIL",
                      f"{label} 两次参考文件截图尺寸不一致：{ref_size} vs {image_size(reference_b)[0]}")
    if expected_size is not None and tuple(ref_size) != tuple(expected_size):
        return result(case_id, "FAIL",
                      f"{label} 参考文件尺寸与活推导不符：期望 {tuple(expected_size)}，实际 {ref_size}")

    started = time.perf_counter()
    try:
        returned = element.screenshot_to_clipboard()
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
                      f"{label} 剪贴板尺寸 {info['width']}×{info['height']} 与元素文件截图 "
                      f"{tuple(ref_size)} 不符", elapsed_s=elapsed)
    if info["actual_size"] != info["expected_size"]:
        return result(case_id, "FAIL",
                      f"{label} DIB 字节数不完整：{info['actual_size']} != 40 + {info['stride']}×{info['height']}",
                      elapsed_s=elapsed)
    if (info["bit_count"], info["compression"], info["top_down"]) != (24, 0, False):
        return result(case_id, "FAIL",
                      f"{label} DIB 形式异常：{info['bit_count']}bpp/压缩{info['compression']}/"
                      f"top_down={info['top_down']}", elapsed_s=elapsed)
    try:
        rows_a, rows_b = png_rows(reference_a), png_rows(reference_b)
        rows_c = dib_rows(dib)
    except Exception as exc:  # noqa: BLE001
        return result(case_id, "FAIL", f"{label} 像素解析失败：{exception_name(exc)}: {exc}", elapsed_s=elapsed)
    jitter, jitter_total, mismatch = byte_diff(rows_a, rows_b)
    if mismatch:
        return result(case_id, "FAIL", f"{label} 参考文件像素比对失败：{mismatch}", elapsed_s=elapsed)
    diff_a, total, mismatch = byte_diff(rows_a, rows_c)
    if mismatch:
        return result(case_id, "FAIL", f"{label} 像素比对失败：{mismatch}", elapsed_s=elapsed)
    diff_b, _, _ = byte_diff(rows_b, rows_c)
    allowed = jitter + JITTER_BUDGET_BYTES
    if max(diff_a, diff_b) > allowed:
        return result(case_id, "FAIL",
                      f"{label} 剪贴板像素与元素文件截图不一致：与 A 差 {diff_a} 字节、与 B 差 {diff_b} 字节，"
                      f"允许 ≤ {allowed}（当时抖动 {jitter} + 预算 {JITTER_BUDGET_BYTES}）",
                      elapsed_s=elapsed, pixel_diff_bytes=diff_a, pixel_jitter_bytes=jitter)
    return result(
        case_id, "PASS",
        f"{label} 剪贴板 CF_DIB {info['width']}×{info['height']}、24bpp、{info['actual_size']} 字节精确吻合，"
        f"像素与元素文件截图差 {diff_a} 字节（{total} 字节中，{elapsed}s）"
        + ("，同参数两次文件截图零差异" if not jitter else f"，当时抖动 {jitter} 字节"),
        elapsed_s=elapsed, width=info["width"], height=info["height"],
        dib_bytes=info["actual_size"], pixel_diff_bytes=diff_a,
        pixel_diff_vs_second_bytes=diff_b, pixel_jitter_bytes=jitter, pixel_total_bytes=total)


def run(args):
    results = [check_contract()]
    if results[-1]["status"] != "PASS" or args.contract_only:
        return results, 0 if results[-1]["status"] == "PASS" else 1

    run_id = uuid.uuid4().hex
    run_dir = LIB_TMP_ROOT / run_id
    copy_dir = run_dir / "lib"
    package = None
    page = None
    page_id = ""
    snapshot = {"formats": [], "text": None, "dib": None}
    restore_note = ""
    final_dib = None
    try:
        # 剪贴板独立通道可用性（先证明通道可信，后续结论才成立）
        try:
            snapshot = snapshot_clipboard()
        except ClipboardUnavailable as exc:
            results.append(result("clipboard_readable", "BLOCKED",
                                  f"进入时无法读取剪贴板，后续剪贴板校验不可信：{exc}"))
            return results, 2
        results.append(result(
            "clipboard_readable", "PASS",
            f"ctypes 独立通道可读写剪贴板；进入时格式={snapshot['formats']}，"
            f"原文本={'有' if snapshot['text'] is not None else '无'}，"
            f"原图像={'有' if snapshot['dib'] else '无'}", formats=snapshot["formats"]))
        try:
            write_text(SENTINEL)
            ok_self = read_text() == SENTINEL
        except ClipboardUnavailable as exc:
            results.append(result("clipboard_channel_selftest", "BLOCKED", f"剪贴板通道不可用：{exc}"))
            return results, 2
        results.append(result(
            "clipboard_channel_selftest", "PASS" if ok_self else "FAIL",
            "脚本自身哨兵文本写入与读取一致（保证收尾还原可信）" if ok_self else "哨兵写入后读回不一致"))
        if not ok_self:
            return results, 1

        # 场景准备 1：复制并打开元素库
        try:
            if not args.library.is_dir():
                results.append(result("library_prepare", "BLOCKED", f"元素库不存在: {args.library}"))
                return results, 2
            shutil.copytree(args.library, copy_dir)
            package = uiautoma.open(str(copy_dir), timeout=20, connect_timeout=20)
            listed = package.elements.list(kind="web")
            ok = package.web_count == len(listed) and package.web_count > 0
            results.append(result(
                "library_prepare", "PASS" if ok else "FAIL",
                f"已打开元素库副本：web 元素 {package.web_count} 个（与列举一致）" if ok else
                f"元素数与列举不一致: web_count={package.web_count}, listed={len(listed)}",
                web_count=package.web_count))
            if not ok:
                return results, 1
        except Exception as exc:  # noqa: BLE001
            results.append(result("library_prepare", "BLOCKED", error_detail("无法准备元素库", exc)))
            return results, 2

        # 场景准备 2：打开库元素所属靶场页
        try:
            page = web.create(args.target_url, mode=args.mode, load_timeout=args.load_timeout)
            page_id = page.id
            current = page.get_url()
            ok = isinstance(page, WebBrowser) and same_url(current, args.target_url)
            results.append(result(
                "page_prepare", "PASS" if ok else "FAIL",
                "已打开库元素所属靶场页" if ok else f"URL 不符: {current!r}", url=current))
            if not ok:
                return results, 1
        except Exception as exc:  # noqa: BLE001
            results.append(result("page_prepare", "BLOCKED", error_detail("无法打开靶场页", exc)))
            return results, 2

        # 目标用例 1：绑定库元素（记录活矩形，供尺寸交叉核对）
        first = None
        bounds = {}
        try:
            first = page.find(FIRST_ELEMENT, timeout=args.timeout)
            bounds = first.get_bounding() or {}
            ok = (str(first.id or "").startswith("rt:web:")
                  and int(bounds.get("width") or 0) > 0 and int(bounds.get("height") or 0) > 0)
            results.append(result(
                "library_element_bind", "PASS" if ok else "FAIL",
                f"已绑定库元素 {FIRST_ELEMENT}（标签 {first.name}，活矩形 "
                f"{bounds.get('width')}×{bounds.get('height')}）" if ok else
                f"绑定异常: id={first.id!r}, bounds={bounds}", element_id=str(first.id or ""),
                bounding=bounds))
            if not ok:
                return results, 1
        except Exception as exc:  # noqa: BLE001
            results.append(result("library_element_bind", "FAIL", error_detail("库元素绑定失败", exc)))
            return results, 1

        # 目标用例 2：哨兵守卫
        try:
            write_text(SENTINEL)
            before = {"text": read_text(), "dib": CF_DIB in clipboard_formats()}
            first.screenshot_to_clipboard()
            after = {"text": read_text(), "dib": CF_DIB in clipboard_formats()}
            ok = before == {"text": SENTINEL, "dib": False} and after["text"] is None and after["dib"]
            results.append(result(
                "sentinel_replaced", "PASS" if ok else "FAIL",
                "哨兵文本已消失且出现 CF_DIB，剪贴板内容确由本次调用改写" if ok else
                f"哨兵前后状态不符: before={before}, after={after}"))
        except ClipboardUnavailable as exc:
            results.append(result("sentinel_replaced", "BLOCKED", f"剪贴板通道不可用：{exc}"))
        except Exception as exc:  # noqa: BLE001
            results.append(result("sentinel_replaced", "FAIL", error_detail("哨兵用例执行失败", exc)))

        # 目标用例 3：库元素（iframe 内）剪贴板 vs 文件截图
        results.append(element_case(
            "library_element_clipboard", f"库元素 {FIRST_ELEMENT}", first, run_dir / "first",
            expected_size=(int(bounds.get("width") or 0), int(bounds.get("height") or 0))))
        if results[-1].get("width"):
            results[-1]["detail"] += "；尺寸与 get_bounding() 完全一致"

        # 目标用例 4：连续两次调用内容一致（排除残留）
        try:
            first.screenshot_to_clipboard()
            one = read_dib()
            first.screenshot_to_clipboard()
            two = read_dib()
            ok = bool(one) and one == two
            results.append(result(
                "repeated_call_identical", "PASS" if ok else "FAIL",
                f"同一元素连续两次调用产出完全相同的 CF_DIB（{len(one or b'')} 字节）" if ok else
                f"两次结果不一致: {len(one or b'')} vs {len(two or b'')} 字节",
                dib_bytes=len(one or b"")))
            final_dib = one or final_dib
        except ClipboardUnavailable as exc:
            results.append(result("repeated_call_identical", "BLOCKED", f"剪贴板通道不可用：{exc}"))
        except Exception as exc:  # noqa: BLE001
            results.append(result("repeated_call_identical", "FAIL", error_detail("重复调用失败", exc)))

        # 目标用例 5：第二个库元素 → 尺寸随元素变化且与活矩形一致
        try:
            second = page.find(SECOND_ELEMENT, timeout=args.timeout)
            second_bounds = second.get_bounding() or {}
            second.screenshot_to_clipboard()
            dib = read_dib()
            info = dib_info(dib) if dib else {}
            expected = (int(second_bounds.get("width") or 0), int(second_bounds.get("height") or 0))
            ok = bool(dib) and (info["width"], info["height"]) == expected and expected != (
                int(bounds.get("width") or 0), int(bounds.get("height") or 0))
            results.append(result(
                "second_element_different_size", "PASS" if ok else "FAIL",
                f"第二个库元素 {SECOND_ELEMENT} 剪贴板尺寸 "
                f"{info.get('width')}×{info.get('height')} 与其活矩形一致，且与第一个元素不同"
                f"（{bounds.get('width')}×{bounds.get('height')}）" if ok else
                f"结果不符: dib={info.get('width')}×{info.get('height')}, expected={expected}, "
                f"first={bounds.get('width')}×{bounds.get('height')}",
                width=info.get("width"), height=info.get("height")))
            final_dib = dib or final_dib
        except ClipboardUnavailable as exc:
            results.append(result("second_element_different_size", "BLOCKED", f"剪贴板通道不可用：{exc}"))
        except Exception as exc:  # noqa: BLE001
            results.append(result("second_element_different_size", "FAIL", error_detail("第二个元素失败", exc)))

        # 目标用例 6：切到主框架页，用活矩形独立验证取景（Issue #20 判据）
        framing_element = None
        rect = {}
        try:
            page.navigate(FRAMING_URL, load_timeout=args.load_timeout)
            # 靶场是 hash 路由：navigate 到 #/form-controls 属于同文档跳转，
            # 页面不会重新加载，必须等 SPA 完成重渲染后才能读到元素。
            # 注意 execute_javascript 的调用约定是 function (element, args)：
            # 第一个形参恒为 element（null），输入参数在第二个形参。
            candidates = page.find_all_by_css(FRAMING_SELECTOR, timeout=args.timeout)
            metrics = None
            for _ in range(20):
                metrics = page.execute_javascript(
                    "function (element, args) { const els = document.querySelectorAll(args.sel);"
                    " if (!els.length) return null; const r = els[0].getBoundingClientRect();"
                    " return {count: els.length, id: els[0].id, x: r.x, y: r.y, w: r.width, h: r.height,"
                    "   dpr: window.devicePixelRatio || 1, sx: window.scrollX, sy: window.scrollY,"
                    "   sw: document.documentElement.scrollWidth,"
                    "   sh: document.documentElement.scrollHeight}; }",
                    {"sel": FRAMING_SELECTOR})
                if isinstance(metrics, dict) and metrics.get("w") and metrics.get("h"):
                    break
                time.sleep(0.3)
            ok = (isinstance(metrics, dict) and metrics.get("w") and metrics.get("h")
                  and metrics.get("count") == 1 and len(candidates) == 1)
            results.append(result(
                "framing_prepare", "PASS" if ok else "FAIL",
                f"已切到主框架页并活取 {FRAMING_SELECTOR} 矩形 "
                f"{metrics.get('w')}×{metrics.get('h')}（dpr={metrics.get('dpr')}，"
                f"页面 {metrics.get('sw')}×{metrics.get('sh')}）" if ok else
                f"准备失败: metrics={metrics}, matches={len(candidates) if candidates else 0}",
                metrics=metrics if isinstance(metrics, dict) else None))
            if ok:
                framing_element, rect = candidates[0], metrics
            else:
                results.append(result("framing_aligned", "BLOCKED", "无法准备主框架取景验证"))
        except Exception as exc:  # noqa: BLE001
            results.append(result("framing_prepare", "BLOCKED", error_detail("主框架准备失败", exc)))

        if framing_element is not None:
            dpr = float(rect.get("dpr") or 1)
            expected = (round(float(rect["w"]) * dpr), round(float(rect["h"]) * dpr))
            folder = run_dir / "framing"
            shutil.rmtree(folder, ignore_errors=True)
            try:
                element_path = Path(framing_element.screenshot(str(folder), file_name="element.png"))
                element_rows = png_rows(element_path)
                element_size = image_size(element_path)[0]
                framing_element.screenshot_to_clipboard()
                dib = read_dib()
                clip_info = dib_info(dib) if dib else {}
                page.screenshot(str(folder), file_name="page.png")
                page_rows = png_rows(folder / "page.png")
            except Exception as exc:  # noqa: BLE001
                results.append(result("framing_aligned", "FAIL", error_detail("取景验证执行失败", exc)))
            else:
                x = round(float(rect["x"]) * dpr) + round(float(rect.get("sx") or 0) * dpr)
                y = round(float(rect["y"]) * dpr) + round(float(rect.get("sy") or 0) * dpr)
                scan = []
                for dy in range(-6, 7):
                    for dx in range(-6, 7):
                        piece = crop(page_rows, x + dx, y + dy, element_rows[0], element_rows[1])
                        if not piece[2]:
                            continue
                        scan.append((byte_diff(piece, element_rows)[0], dx, dy))
                best = min(scan) if scan else None
                aligned = (element_size == expected and clip_info.get("width") == expected[0]
                           and clip_info.get("height") == expected[1]
                           and best is not None and best[1] == 0 and best[2] == 0)
                results.append(result(
                    "framing_aligned", "PASS" if aligned else "FAIL",
                    f"元素截图与剪贴板均为活矩形尺寸 {expected[0]}×{expected[1]}"
                    f"（= {rect['w']}×{rect['h']} CSS × dpr {dpr}）；把整页截图按活矩形裁切后做"
                    f"±6 像素偏移扫描，最小区块差异出现在偏移 (0, 0)，即取景精确对准"
                    if aligned else
                    f"取景不符: 元素截图={element_size}, 剪贴板="
                    f"{clip_info.get('width')}×{clip_info.get('height')}, 期望={expected}, "
                    f"最佳偏移=({best[1] if best else None}, {best[2] if best else None})",
                    expected=list(expected), best_offset=[best[1], best[2]] if best else None,
                    best_offset_diff=best[0] if best else None))
                results.append(element_case(
                    "framing_clipboard_vs_file", "主框架元素（活矩形独立验证）", framing_element,
                    run_dir / "framing-cmp", expected_size=expected))
                final_dib = read_dib() or final_dib

        # 目标用例 7：导航后旧元素句柄失效
        if first is not None:
            results.append(expect_raises(
                lambda: first.screenshot_to_clipboard(), ActionError, "stale_after_navigate",
                message_contains="未找到", max_elapsed=5.0))

        # 目标用例 8：页面关闭后旧元素句柄失效
        try:
            page.close(ignore_beforeunload=True)
        except Exception as exc:  # noqa: BLE001
            results.append(result("page_close_verified", "FAIL", error_detail("page.close 调用失败", exc)))
        else:
            time.sleep(0.5)
            leftover = [p for p in web.get_all(mode=args.mode)
                        if str(getattr(p, "id", "") or "") == page_id]
            results.append(result(
                "page_close_verified", "PASS" if not leftover else "FAIL",
                "页面已关闭，且 web.get_all() 复核无残留" if not leftover else
                f"关闭后仍有残留: {len(leftover)}", leftover_pages=len(leftover)))
        target = framing_element or first
        if target is not None:
            results.append(expect_raises(
                lambda: target.screenshot_to_clipboard(), ActionError, "stale_after_close",
                message_contains="失效", max_elapsed=5.0))
        page = None

        # 目标用例 9：关闭 Package
        try:
            package.close()
            results.append(result("package_close_verified", "PASS", "Package 已关闭"))
        except Exception as exc:  # noqa: BLE001
            results.append(result("package_close_verified", "FAIL", error_detail("Package 关闭失败", exc)))
        package = None
    except Exception as exc:  # noqa: BLE001
        results.append(result("scenario", "FAIL",
                              error_detail("screenshot_to_clipboard 元素场景执行失败", exc)))
    finally:
        page_close_error = ""
        if page is not None:
            try:
                page.close(ignore_beforeunload=True)
            except Exception as exc:  # noqa: BLE001
                page_close_error = f"{type(exc).__name__}: {exc}"
        if package is not None:
            try:
                package.close()
            except Exception as exc:  # noqa: BLE001
                page_close_error = page_close_error or f"Package 关闭失败: {type(exc).__name__}"
        produced = len([p for p in run_dir.rglob("*") if p.is_file()]) if run_dir.exists() else 0
        shutil.rmtree(run_dir, ignore_errors=True)
        leftover = []
        try:
            leftover = [p for p in web.get_all(mode=args.mode) if str(getattr(p, "id", "") or "") == page_id]
        except Exception as exc:  # noqa: BLE001
            page_close_error = page_close_error or f"get_all 复核失败: {type(exc).__name__}: {exc}"
        try:
            restore_note = restore_clipboard(snapshot, final_dib)
            clipboard_error = ""
        except ClipboardUnavailable as exc:
            clipboard_error = str(exc)
        cleaned = (not leftover and not page_close_error and not run_dir.exists()
                   and not clipboard_error)
        results.append(result(
            "cleanup", "PASS" if cleaned else "FAIL",
            f"已关闭页面（get_all 复核无残留）、关闭 Package、删除临时目录（含 {produced} 个文件，"
            f"含元素库副本）；剪贴板收尾：{restore_note}" if cleaned else
            f"清理不完整: 残留页面={len(leftover)}, close/package 错误={page_close_error or '无'}, "
            f"临时目录残留={run_dir.exists()}, 剪贴板错误={clipboard_error or '无'}",
            leftover_pages=len(leftover), produced_files=produced,
            page_close_error=page_close_error, clipboard_note=restore_note))

    statuses = {item["status"] for item in results}
    code = 1 if "FAIL" in statuses else (2 if "BLOCKED" in statuses else 0)
    return results, code


def main(argv=None):
    parser = argparse.ArgumentParser(description="WebElement.screenshot_to_clipboard() 元素对象 API 验收")
    parser.add_argument("--target-url", default=DEFAULT_URL, help="库元素所属靶场页")
    parser.add_argument("--mode", choices=("chrome", "edge"), default="chrome")
    parser.add_argument("--load-timeout", type=float, default=20)
    parser.add_argument("--timeout", type=float, default=8, help="find 的 timeout，默认 8")
    parser.add_argument("--library", type=Path, default=DEFAULT_LIBRARY, help="元素库目录")
    parser.add_argument("--contract-only", action="store_true")
    parser.add_argument("--json", action="store_true", help="在表格后额外输出 JSON 报告（用于归档验收产物）")
    args = parser.parse_args(argv)
    if args.load_timeout <= 0:
        parser.error("--load-timeout 必须大于 0")

    results, code = run(args)
    print("UIAutoma Web API 测试")
    print("API     : uiautoma.web.WebElement.screenshot_to_clipboard")
    print(f"页面    : {args.target_url}")
    print(f"元素库  : {args.library}")
    print("进度     状态    测试项                  测试结果")
    print("────────────────────────────────────────────────────────────────────────")
    for index, current in enumerate(results, 1):
        status = current["status"]
        color = {"PASS": GREEN, "BLOCKED": YELLOW}.get(status, RED)
        label = {"PASS": "通过", "BLOCKED": "阻塞"}.get(status, "失败")
        print(f"{index:02d}/{len(results):02d}    {color}[{label}]{RESET}  "
              f"{current['case_id']:<32}  {current['detail']}")
    print("────────────────────────────────────────────────────────────────────────")
    summary = "测试通过" if code == 0 else ("测试阻塞" if code == 2 else "测试失败")
    print(f"{summary} · {sum(item['status'] == 'PASS' for item in results)}/{len(results)} 通过 · 退出码 {code}")
    if args.json:
        print(json.dumps({
            "api": "uiautoma.web.WebElement.screenshot_to_clipboard",
            "target_url": args.target_url, "mode": args.mode,
            "library": str(args.library),
            "status": "PASS" if code == 0 else ("BLOCKED" if code == 2 else "FAIL"),
            "exit_code": code, "results": results,
        }, ensure_ascii=False, indent=2))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
