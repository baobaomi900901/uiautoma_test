r"""验证 ``uiautoma.win32.Win32Element.clipboard_input()`` 的全部公开参数。

API 参数（均可按位置或关键字传入）：
    text: str                         必填；实现会先调用 str(text)。
    append: bool = False              False 覆盖，True 在当前光标位置粘贴。
    focus_timeout: int = 1000         点击或聚焦后到粘贴前的等待毫秒数。
    delay_after: float = 1            粘贴后的等待秒数；None 或 0 不等待。
    send_key_delay: int = 50          Ctrl+A、Delete、Ctrl+V 之间的等待毫秒数。
    click_before_input: bool = True   粘贴前是否点击元素。
    anchor: object | None = None      九宫格、random、三元组或字典偏移锚点。

脚本参数：无。

前置条件：UIAutoma.exe 正在 dev 运行；当前元素库为
``D:\code\元素库\260902_win元素``；Win32 靶场已启动；运行前剪贴板中存在普通
Unicode 文本。

每次调用后均校验剪贴板文本已恢复。结束时恢复输入框原值、剪贴板文本、鼠标和前台窗口。
"""

from __future__ import annotations

from _form_tab import ensure_form_tab

import ctypes
import inspect
import os
import sys
import time
import unicodedata
from ctypes import wintypes
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

import uiautoma
from uiautoma import InvalidParamsError, win32
from uiautoma.win32 import Win32Element


LIBRARY_DIR = Path(r"D:\code\元素库\260902_win元素")
TARGET_ELEMENT = "win32靶场_表单控件_输入框_姓名"
TARGET_TITLE = "Win32 靶场 - UIA"
TARGET_CLASS = "XPathWin32ShootingRange"
TARGET_PROCESS = "win32-shooting-range-uia.exe"
CF_UNICODETEXT = 13
GMEM_MOVEABLE = 0x0002

ANSI_GREEN = "\033[32m"
ANSI_RED = "\033[31m"
ANSI_BOLD = "\033[1m"
ANSI_RESET = "\033[0m"
USE_COLOR = sys.stdout.isatty() and not os.environ.get("NO_COLOR")


@dataclass
class CaseResult:
    name: str
    passed: bool
    detail: str
    elapsed_ms: float
    extras: list[str] = field(default_factory=list)


@dataclass
class InputObservation:
    elapsed_ms: float
    strategy: str
    value: str
    point: tuple[int, int] | None


class POINT(ctypes.Structure):
    _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]


def colored(text: str, code: str) -> str:
    return f"{code}{text}{ANSI_RESET}" if USE_COLOR else text


def display_width(text: str) -> int:
    width = 0
    for character in text:
        if unicodedata.combining(character):
            continue
        width += 2 if unicodedata.east_asian_width(character) in {"W", "F"} else 1
    return width


def pad(text: str, width: int) -> str:
    return text + " " * max(0, width - display_width(text))


def same_path(left: Path, right: Path) -> bool:
    return os.path.normcase(str(left.resolve())) == os.path.normcase(str(right.resolve()))


def preview(value: str, limit: int = 60) -> str:
    escaped = value.replace("\r", "\\r").replace("\n", "\\n")
    return repr(escaped if len(escaped) <= limit else escaped[: limit - 1] + "…")


def _clipboard_api() -> tuple[Any, Any]:
    user32 = ctypes.WinDLL("user32", use_last_error=True)
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    user32.OpenClipboard.argtypes = [wintypes.HWND]
    user32.OpenClipboard.restype = wintypes.BOOL
    user32.CloseClipboard.argtypes = []
    user32.CloseClipboard.restype = wintypes.BOOL
    user32.EmptyClipboard.argtypes = []
    user32.EmptyClipboard.restype = wintypes.BOOL
    user32.IsClipboardFormatAvailable.argtypes = [wintypes.UINT]
    user32.IsClipboardFormatAvailable.restype = wintypes.BOOL
    user32.GetClipboardData.argtypes = [wintypes.UINT]
    user32.GetClipboardData.restype = wintypes.HANDLE
    user32.SetClipboardData.argtypes = [wintypes.UINT, wintypes.HANDLE]
    user32.SetClipboardData.restype = wintypes.HANDLE
    kernel32.GlobalAlloc.argtypes = [wintypes.UINT, ctypes.c_size_t]
    kernel32.GlobalAlloc.restype = wintypes.HGLOBAL
    kernel32.GlobalLock.argtypes = [wintypes.HGLOBAL]
    kernel32.GlobalLock.restype = ctypes.c_void_p
    kernel32.GlobalUnlock.argtypes = [wintypes.HGLOBAL]
    kernel32.GlobalUnlock.restype = wintypes.BOOL
    kernel32.GlobalFree.argtypes = [wintypes.HGLOBAL]
    kernel32.GlobalFree.restype = wintypes.HGLOBAL
    return user32, kernel32


def read_clipboard_text() -> tuple[bool, str]:
    user32, kernel32 = _clipboard_api()
    if not user32.OpenClipboard(None):
        raise OSError(f"OpenClipboard 失败：{ctypes.get_last_error()}")
    try:
        if not user32.IsClipboardFormatAvailable(CF_UNICODETEXT):
            return False, ""
        handle = user32.GetClipboardData(CF_UNICODETEXT)
        if not handle:
            raise OSError(f"GetClipboardData 失败：{ctypes.get_last_error()}")
        pointer = kernel32.GlobalLock(handle)
        if not pointer:
            raise OSError(f"GlobalLock 失败：{ctypes.get_last_error()}")
        try:
            return True, ctypes.wstring_at(pointer)
        finally:
            kernel32.GlobalUnlock(handle)
    finally:
        user32.CloseClipboard()


def write_clipboard_text(text: str) -> None:
    user32, kernel32 = _clipboard_api()
    if not user32.OpenClipboard(None):
        raise OSError(f"OpenClipboard 失败：{ctypes.get_last_error()}")
    handle = None
    try:
        if not user32.EmptyClipboard():
            raise OSError(f"EmptyClipboard 失败：{ctypes.get_last_error()}")
        buffer = ctypes.create_unicode_buffer(text)
        handle = kernel32.GlobalAlloc(GMEM_MOVEABLE, ctypes.sizeof(buffer))
        if not handle:
            raise OSError(f"GlobalAlloc 失败：{ctypes.get_last_error()}")
        pointer = kernel32.GlobalLock(handle)
        if not pointer:
            raise OSError(f"GlobalLock 失败：{ctypes.get_last_error()}")
        try:
            ctypes.memmove(pointer, ctypes.addressof(buffer), ctypes.sizeof(buffer))
        finally:
            kernel32.GlobalUnlock(handle)
        if not user32.SetClipboardData(CF_UNICODETEXT, handle):
            raise OSError(f"SetClipboardData 失败：{ctypes.get_last_error()}")
        handle = None
    finally:
        if handle:
            kernel32.GlobalFree(handle)
        user32.CloseClipboard()


def current_cursor() -> tuple[int, int]:
    point = POINT()
    if not ctypes.windll.user32.GetCursorPos(ctypes.byref(point)):
        raise OSError("GetCursorPos 失败")
    return int(point.x), int(point.y)


def restore_cursor(point: tuple[int, int]) -> None:
    if not ctypes.windll.user32.SetCursorPos(point[0], point[1]):
        raise OSError("SetCursorPos 失败")


def current_foreground() -> int:
    return int(ctypes.windll.user32.GetForegroundWindow())


def restore_foreground(handle: int) -> None:
    if not handle or not ctypes.windll.user32.IsWindow(handle):
        return
    ctypes.windll.user32.SetForegroundWindow(handle)
    deadline = time.perf_counter() + 1.0
    while time.perf_counter() < deadline:
        if current_foreground() == handle:
            return
        time.sleep(0.02)
    raise RuntimeError(f"原前台窗口未恢复：{handle}")


def point_from_result(raw: Any) -> tuple[int, int] | None:
    if isinstance(raw, dict) and "x" in raw and "y" in raw:
        return int(raw["x"]), int(raw["y"])
    if isinstance(raw, (tuple, list)) and len(raw) >= 2:
        return int(raw[0]), int(raw[1])
    if hasattr(raw, "x") and hasattr(raw, "y"):
        return int(raw.x), int(raw.y)
    return None


def anchor_point(
    rect: tuple[int, int, int, int],
    anchor: str,
    offset_x: int = 0,
    offset_y: int = 0,
) -> tuple[int, int]:
    x, y, width, height = rect
    left, right = x + 2, x + width - 2
    top, bottom = y + 2, y + height - 2
    if right <= left:
        left, right = x, x + width
    if bottom <= top:
        top, bottom = y, y + height
    center_x, center_y = (left + right) // 2, (top + bottom) // 2
    positions = {
        "topLeft": (left, top),
        "topCenter": (center_x, top),
        "topRight": (right, top),
        "middleLeft": (left, center_y),
        "middleCenter": (center_x, center_y),
        "middleRight": (right, center_y),
        "bottomLeft": (left, bottom),
        "bottomCenter": (center_x, bottom),
        "bottomRight": (right, bottom),
    }
    point_x, point_y = positions[anchor]
    return point_x + offset_x, point_y + offset_y


def point_inside(point: tuple[int, int], rect: tuple[int, int, int, int]) -> bool:
    x, y, width, height = rect
    return x <= point[0] < x + width and y <= point[1] < y + height


def point_near(actual: tuple[int, int], expected: tuple[int, int], tolerance: int = 2) -> bool:
    return abs(actual[0] - expected[0]) <= tolerance and abs(actual[1] - expected[1]) <= tolerance


def observe_input(
    element: Win32Element,
    call_text: str,
    invoke: Callable[[], Any],
    *,
    expected_value: str,
    expected_clipboard: str,
    rect: tuple[int, int, int, int],
    point_rule: str = "optional",
    expected_point: tuple[int, int] | None = None,
) -> InputObservation:
    started = time.perf_counter()
    returned = invoke()
    elapsed_ms = (time.perf_counter() - started) * 1000.0
    if returned is not None:
        raise AssertionError(f"{call_text} 应返回 None，实际为 {returned!r}")
    result = element.last_result
    if result is None or not result.ok or not str(result.strategy or "").strip():
        raise AssertionError(f"{call_text} 未留下完整的成功 last_result")
    actual_value = element.get_value()
    if actual_value != expected_value:
        raise AssertionError(f"{call_text} 期望值 {expected_value!r}，实际 {actual_value!r}")
    available, clipboard = read_clipboard_text()
    if not available or clipboard != expected_clipboard:
        raise AssertionError(
            f"{call_text} 后剪贴板未恢复：期望 {expected_clipboard!r}，实际 {clipboard!r}"
        )
    point = point_from_result(result.clicked_point)
    if point_rule == "required":
        if point is None or not point_inside(point, rect):
            raise AssertionError(f"{call_text} 输入前点击点无效：{point}")
    elif point_rule == "absent" and point is not None:
        raise AssertionError(f"{call_text} 禁用输入前点击后仍返回点击点 {point}")
    if expected_point is not None and (point is None or not point_near(point, expected_point)):
        raise AssertionError(f"{call_text} 点击点应接近 {expected_point}，实际为 {point}")
    return InputObservation(elapsed_ms, str(result.strategy), actual_value, point)


def expect_exception(call_text: str, expected: type[BaseException], invoke: Callable[[], Any]) -> None:
    try:
        invoke()
    except expected:
        return
    except Exception as exc:
        raise AssertionError(
            f"{call_text} 应抛出 {expected.__name__}，实际为 {type(exc).__name__}: {exc}"
        ) from exc
    raise AssertionError(f"{call_text} 未抛出 {expected.__name__}")


def run_case(name: str, check: Callable[[], tuple[str, list[str]] | str]) -> CaseResult:
    started = time.perf_counter()
    try:
        outcome = check()
        detail, extras = outcome if isinstance(outcome, tuple) else (outcome, [])
        return CaseResult(name, True, detail, (time.perf_counter() - started) * 1000.0, extras)
    except Exception as exc:
        return CaseResult(
            name,
            False,
            "测试条件或实际结果不符合预期",
            (time.perf_counter() - started) * 1000.0,
            [f"原因    : {exc}", f"异常    : {type(exc).__name__}"],
        )


def render_results(results: list[CaseResult]) -> None:
    progress_width, status_width, name_width, elapsed_width = 7, 6, 18, 9
    detail_width = max(70, max(display_width(item.detail) for item in results) + 2)
    print()
    print(
        f"{pad('进度', progress_width)}  {pad('状态', status_width)}  "
        f"{pad('测试项', name_width)}  {pad('测试结果', detail_width)}  {'耗时':>{elapsed_width}}"
    )
    print(
        f"{'─' * progress_width}  {'─' * status_width}  {'─' * name_width}  "
        f"{'─' * detail_width}  {'─' * elapsed_width}"
    )
    total = len(results)
    for index, item in enumerate(results, start=1):
        raw_status = "[通过]" if item.passed else "[失败]"
        status = colored(pad(raw_status, status_width), ANSI_GREEN if item.passed else ANSI_RED)
        print(
            f"{pad(f'{index:02d}/{total:02d}', progress_width)}  {status}  "
            f"{pad(item.name, name_width)}  {pad(item.detail, detail_width)}  "
            f"{item.elapsed_ms:>7.1f}ms"
        )
        indent = " " * (progress_width + status_width + name_width + 6)
        for extra in item.extras:
            print(f"{indent}{extra}")
    line_width = progress_width + status_width + name_width + detail_width + elapsed_width + 8
    print("─" * line_width)


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    print(colored("UIAutoma Win32 Element API 测试", ANSI_BOLD))
    print()
    print("  API       : uiautoma.win32.Win32Element.clipboard_input")
    print(f"  元素库    : {LIBRARY_DIR}")
    print(f"  输入元素  : {TARGET_ELEMENT}")
    print(f"  测试窗口  : {TARGET_TITLE}")
    print(f"  目标进程  : {TARGET_PROCESS}")
    print("  剪贴板保护: 每次调用后校验运行前的 Unicode 文本已恢复")
    print("  数据恢复  : 测试结束后恢复输入框原值、剪贴板、鼠标和前台窗口")

    results: list[CaseResult] = []
    package: Any = None
    element: Win32Element | None = None
    rect: tuple[int, int, int, int] | None = None
    original_value: str | None = None
    original_clipboard: str | None = None
    original_mouse: tuple[int, int] | None = None
    original_foreground = 0

    def contract() -> str:
        signature = inspect.signature(Win32Element.clipboard_input)
        parameters = list(signature.parameters.values())
        expected_names = [
            "self",
            "text",
            "append",
            "focus_timeout",
            "delay_after",
            "send_key_delay",
            "click_before_input",
            "anchor",
        ]
        expected_defaults = [
            inspect.Parameter.empty,
            inspect.Parameter.empty,
            False,
            1000,
            1,
            50,
            True,
            None,
        ]
        if [item.name for item in parameters] != expected_names:
            raise AssertionError(f"参数顺序变化：{signature}")
        if [item.default for item in parameters] != expected_defaults:
            raise AssertionError(f"参数默认值变化：{signature}")
        if any(item.kind is not inspect.Parameter.POSITIONAL_OR_KEYWORD for item in parameters):
            raise AssertionError(f"参数种类变化：{signature}")
        if str(signature.return_annotation) not in {"None", "<class 'NoneType'>"}:
            raise AssertionError(f"返回注解变化：{signature}")
        return "七个公开参数、默认值和位置/关键字调用规则符合合同"

    results.append(run_case("API 合同", contract))

    try:
        def acquire_package() -> str:
            nonlocal package
            if not LIBRARY_DIR.is_dir():
                raise FileNotFoundError(f"元素库目录不存在：{LIBRARY_DIR}")
            package = uiautoma.current(required=False, refresh=True, timeout=5)
            ensure_form_tab(package)
            if package is None:
                raise RuntimeError("UIAutoma.exe 当前没有启用元素库")
            actual_library = Path(package.package_dir)
            if not same_path(actual_library, LIBRARY_DIR):
                raise RuntimeError(
                    f"当前元素库不是测试库：期望 {LIBRARY_DIR}，实际 {actual_library}"
                )
            return "当前启用元素库与测试库一致，已借用 Package"

        package_result = run_case("当前元素库", acquire_package)
        results.append(package_result)
        if not package_result.passed:
            raise RuntimeError("当前元素库准备失败")

        def acquire_environment() -> tuple[str, list[str]]:
            nonlocal element, rect, original_value, original_clipboard
            nonlocal original_mouse, original_foreground
            available, clipboard_text = read_clipboard_text()
            if not available:
                raise RuntimeError("剪贴板没有 CF_UNICODETEXT；请先复制一段普通文本")
            original_clipboard = clipboard_text
            window = win32.get(
                TARGET_TITLE,
                class_name=TARGET_CLASS,
                process_name=TARGET_PROCESS,
                timeout=5,
            )
            selector = package.selector(TARGET_ELEMENT, kind="win")
            element = window.find(selector, timeout=5)
            if not isinstance(element, Win32Element):
                raise TypeError(f"目标类型不是 Win32Element：{type(element).__name__}")
            raw_rect = element.get_bounding(to96dpi=False, relative_to="screen")
            if not isinstance(raw_rect, (tuple, list)) or len(raw_rect) != 4:
                raise AssertionError(f"元素边界格式无效：{raw_rect!r}")
            rect = tuple(int(value) for value in raw_rect)
            if rect[2] <= 0 or rect[3] <= 0:
                raise AssertionError(f"元素边界无效：{rect}")
            original_value = element.get_value()
            original_mouse = current_cursor()
            original_foreground = current_foreground()
            win32.manual_motion_off()
            return (
                "已定位输入框并保存可恢复的 Unicode 剪贴板文本",
                [
                    f"边界      : {rect}",
                    f"输入框原值: {preview(original_value)}",
                    f"剪贴板原文: {preview(original_clipboard)}",
                    f"原鼠标    : {original_mouse}",
                ],
            )

        environment_result = run_case("测试环境", acquire_environment)
        results.append(environment_result)
        if not environment_result.passed:
            raise RuntimeError("测试环境准备失败")

        assert element is not None
        assert rect is not None
        assert original_clipboard is not None

        def checked(
            call_text: str,
            invoke: Callable[[], Any],
            expected_value: str,
            *,
            point_rule: str = "optional",
            expected_point: tuple[int, int] | None = None,
        ) -> InputObservation:
            return observe_input(
                element,
                call_text,
                invoke,
                expected_value=expected_value,
                expected_clipboard=original_clipboard,
                rect=rect,
                point_rule=point_rule,
                expected_point=expected_point,
            )

        def defaults() -> tuple[str, list[str]]:
            value = "Clipboard_Default_01"
            observation = checked(
                f"element.clipboard_input({value!r})",
                lambda: element.clipboard_input(value),
                value,
                point_rule="required",
                expected_point=anchor_point(rect, "middleCenter"),
            )
            if observation.elapsed_ms < 1800:
                raise AssertionError(
                    f"默认 focus_timeout 与 delay_after 等待不足：{observation.elapsed_ms:.1f}ms"
                )
            return (
                "六项默认值生效，覆盖输入并恢复原剪贴板文本",
                [
                    f"实际值    : {observation.value!r}",
                    f"策略      : {observation.strategy}",
                    f"点击点    : {observation.point}",
                    f"剪贴板恢复: {preview(original_clipboard)}",
                ],
            )

        results.append(run_case("全部默认参数", defaults))

        def all_positional() -> tuple[str, list[str]]:
            value = "Clipboard_All_02"
            observation = checked(
                "七个参数全部按位置传入",
                lambda: element.clipboard_input(value, False, 0, 0, 0, True, "middleCenter"),
                value,
                point_rule="required",
                expected_point=anchor_point(rect, "middleCenter"),
            )
            return (
                "七个参数可按位置传入，输入值、点击点和剪贴板恢复均正确",
                [f"实际值    : {observation.value!r}", f"策略      : {observation.strategy}"],
            )

        results.append(run_case("全位置参数", all_positional))

        def overwrite_append_case() -> tuple[str, list[str]]:
            base = "Clipboard_Base"
            checked(
                "append=False",
                lambda: element.clipboard_input(
                    base,
                    append=False,
                    focus_timeout=0,
                    delay_after=0,
                    send_key_delay=0,
                    click_before_input=False,
                ),
                base,
                point_rule="absent",
            )
            expected = base + "_APPEND"
            observation = checked(
                "append=True",
                lambda: element.clipboard_input(
                    "_APPEND",
                    append=True,
                    focus_timeout=0,
                    delay_after=0,
                    send_key_delay=0,
                    click_before_input=False,
                ),
                expected,
                point_rule="absent",
            )
            return (
                "append=False 覆盖，append=True 在现有内容后追加",
                [f"最终值    : {observation.value!r}", f"剪贴板恢复: {preview(original_clipboard)}"],
            )

        results.append(run_case("覆盖与追加", overwrite_append_case))

        def unicode_case() -> tuple[str, list[str]]:
            value = "中文_Clipboard_{}[]_✓"
            observation = checked(
                "Unicode 文本",
                lambda: element.clipboard_input(
                    value,
                    focus_timeout=0,
                    delay_after=0,
                    send_key_delay=0,
                    click_before_input=False,
                ),
                value,
                point_rule="absent",
            )
            return "中文与符号经剪贴板输入正确", [f"实际值    : {observation.value!r}"]

        results.append(run_case("Unicode 文本", unicode_case))

        def focus_delay_case() -> tuple[str, list[str]]:
            fast = checked(
                "focus_timeout=0",
                lambda: element.clipboard_input(
                    "Focus000",
                    focus_timeout=0,
                    delay_after=0,
                    send_key_delay=0,
                    click_before_input=True,
                ),
                "Focus000",
                point_rule="required",
            )
            delayed = checked(
                "focus_timeout=200",
                lambda: element.clipboard_input(
                    "Focus200",
                    focus_timeout=200,
                    delay_after=0,
                    send_key_delay=0,
                    click_before_input=True,
                ),
                "Focus200",
                point_rule="required",
            )
            if delayed.elapsed_ms < fast.elapsed_ms + 150:
                raise AssertionError(
                    f"聚焦等待差异不足：0ms={fast.elapsed_ms:.1f}ms，200ms={delayed.elapsed_ms:.1f}ms"
                )
            return (
                "focus_timeout=200 相比 0 产生可测输入前等待",
                [f"0ms       : {fast.elapsed_ms:.1f}ms", f"200ms     : {delayed.elapsed_ms:.1f}ms"],
            )

        results.append(run_case("聚焦等待", focus_delay_case))

        def key_delay_case() -> tuple[str, list[str]]:
            fast = checked(
                "send_key_delay=0",
                lambda: element.clipboard_input(
                    "Keys000",
                    focus_timeout=0,
                    delay_after=0,
                    send_key_delay=0,
                    click_before_input=False,
                ),
                "Keys000",
                point_rule="absent",
            )
            delayed = checked(
                "send_key_delay=150",
                lambda: element.clipboard_input(
                    "Keys150",
                    focus_timeout=0,
                    delay_after=0,
                    send_key_delay=150,
                    click_before_input=False,
                ),
                "Keys150",
                point_rule="absent",
            )
            if delayed.elapsed_ms < fast.elapsed_ms + 130:
                raise AssertionError(
                    f"快捷键等待差异不足：0ms={fast.elapsed_ms:.1f}ms，150ms={delayed.elapsed_ms:.1f}ms"
                )
            return (
                "send_key_delay=150 相比 0 产生可测快捷键等待",
                [f"0ms       : {fast.elapsed_ms:.1f}ms", f"150ms     : {delayed.elapsed_ms:.1f}ms"],
            )

        results.append(run_case("快捷键等待", key_delay_case))

        def click_before_case() -> str:
            checked(
                "click_before_input=True",
                lambda: element.clipboard_input(
                    "Click_True",
                    focus_timeout=0,
                    delay_after=0,
                    send_key_delay=0,
                    click_before_input=True,
                ),
                "Click_True",
                point_rule="required",
            )
            checked(
                "click_before_input=False",
                lambda: element.clipboard_input(
                    "Click_False",
                    focus_timeout=0,
                    delay_after=0,
                    send_key_delay=0,
                    click_before_input=False,
                ),
                "Click_False",
                point_rule="absent",
            )
            return "启用时先点击并返回点位；禁用时自动化聚焦且无点击点"

        results.append(run_case("输入前点击", click_before_case))

        fixed_anchors = (
            "topLeft",
            "topCenter",
            "topRight",
            "middleLeft",
            "middleCenter",
            "middleRight",
            "bottomLeft",
            "bottomCenter",
            "bottomRight",
        )

        def fixed_anchor_case() -> str:
            for index, anchor in enumerate(fixed_anchors, start=1):
                value = f"Anchor_{index:02d}"
                checked(
                    f'element.clipboard_input(..., anchor="{anchor}")',
                    lambda value=value, anchor=anchor: element.clipboard_input(
                        value, False, 0, 0, 0, True, anchor
                    ),
                    value,
                    point_rule="required",
                    expected_point=anchor_point(rect, anchor),
                )
            return "九宫格锚点全部命中对应物理位置，输入值和剪贴板恢复均正确"

        results.append(run_case("九宫格锚点", fixed_anchor_case))

        def random_anchor_case() -> tuple[str, list[str]]:
            observation = checked(
                'element.clipboard_input(..., anchor="random")',
                lambda: element.clipboard_input(
                    "Anchor_Random", False, 0, 0, 0, True, "random"
                ),
                "Anchor_Random",
                point_rule="required",
            )
            return "random 点击点位于元素边界内且输入成功", [f"随机点    : {observation.point}"]

        results.append(run_case("随机锚点", random_anchor_case))

        def tuple_anchor_case() -> tuple[str, list[str]]:
            observation = checked(
                "三元组锚点",
                lambda: element.clipboard_input(
                    "Anchor_Tuple", False, 0, 0, 0, True, ("middleCenter", 10, 4)
                ),
                "Anchor_Tuple",
                point_rule="required",
                expected_point=anchor_point(rect, "middleCenter", 10, 4),
            )
            return "三元组锚点及 X/Y 偏移量生效", [f"点击点    : {observation.point}"]

        results.append(run_case("三元组锚点", tuple_anchor_case))

        def mapping_anchor_case() -> tuple[str, list[str]]:
            anchor = {"anchor": "middleCenter", "offset_x": -10, "offset_y": -4}
            observation = checked(
                "字典锚点",
                lambda: element.clipboard_input(
                    "Anchor_Mapping", False, 0, 0, 0, True, anchor
                ),
                "Anchor_Mapping",
                point_rule="required",
                expected_point=anchor_point(rect, "middleCenter", -10, -4),
            )
            return "字典锚点及 offset_x/offset_y 生效", [f"点击点    : {observation.point}"]

        results.append(run_case("字典锚点", mapping_anchor_case))

        def text_conversion_case() -> tuple[str, list[str]]:
            value = 20260906
            observation = checked(
                "element.clipboard_input(20260906, ...)",
                lambda: element.clipboard_input(
                    value,  # type: ignore[arg-type]
                    focus_timeout=0,
                    delay_after=0,
                    send_key_delay=0,
                    click_before_input=False,
                ),
                str(value),
                point_rule="absent",
            )
            return "非字符串 text 按当前实现转换为字符串后输入", [f"实际值    : {observation.value!r}"]

        results.append(run_case("文本转换", text_conversion_case))

        def delay_after_case() -> tuple[str, list[str]]:
            fast = checked(
                "delay_after=None",
                lambda: element.clipboard_input(
                    "After_None",
                    focus_timeout=0,
                    delay_after=None,
                    send_key_delay=0,
                    click_before_input=False,
                ),
                "After_None",
                point_rule="absent",
            )
            delayed = checked(
                "delay_after=0.2",
                lambda: element.clipboard_input(
                    "After_200",
                    focus_timeout=0,
                    delay_after=0.2,
                    send_key_delay=0,
                    click_before_input=False,
                ),
                "After_200",
                point_rule="absent",
            )
            if delayed.elapsed_ms < fast.elapsed_ms + 160:
                raise AssertionError(
                    f"动作后延时差异不足：None={fast.elapsed_ms:.1f}ms，0.2={delayed.elapsed_ms:.1f}ms"
                )
            return (
                "delay_after=None 不等待，0.2 秒等待生效；默认 1 秒亦已覆盖",
                [f"None      : {fast.elapsed_ms:.1f}ms", f"0.2s      : {delayed.elapsed_ms:.1f}ms"],
            )

        results.append(run_case("动作后延时", delay_after_case))

        def millisecond_boundaries() -> str:
            checked(
                "负数毫秒参数",
                lambda: element.clipboard_input(
                    "Negative_MS",
                    focus_timeout=-20,
                    delay_after=0,
                    send_key_delay=-10,
                    click_before_input=True,
                ),
                "Negative_MS",
                point_rule="required",
            )
            expect_exception(
                'send_key_delay="bad"',
                ValueError,
                lambda: element.clipboard_input(
                    "Bad_Key_Delay", send_key_delay="bad"  # type: ignore[arg-type]
                ),
            )
            expect_exception(
                'focus_timeout="bad"',
                ValueError,
                lambda: element.clipboard_input(
                    "Bad_Focus", focus_timeout="bad"  # type: ignore[arg-type]
                ),
            )
            available, actual = read_clipboard_text()
            if not available or actual != original_clipboard:
                raise AssertionError("毫秒参数边界测试后剪贴板文本发生变化")
            return "负数毫秒值按 0 处理；非整数值在 SDK 转换阶段抛出 ValueError"

        results.append(run_case("毫秒参数边界", millisecond_boundaries))

        def invalid_anchor_case() -> str:
            expect_exception(
                'anchor="center"',
                InvalidParamsError,
                lambda: element.clipboard_input("Bad_Anchor", anchor="center", delay_after=0),
            )
            expect_exception(
                "anchor=123",
                InvalidParamsError,
                lambda: element.clipboard_input("Bad_Anchor", anchor=123, delay_after=0),
            )
            available, actual = read_clipboard_text()
            if not available or actual != original_clipboard:
                raise AssertionError("非法锚点测试后剪贴板文本发生变化")
            return "未知锚点名称和不支持的锚点类型均被 InvalidParamsError 拒绝"

        results.append(run_case("非法锚点", invalid_anchor_case))

        def invalid_delay_case() -> str:
            expect_exception(
                "delay_after=-1",
                InvalidParamsError,
                lambda: element.clipboard_input(
                    "Invalid_Delay_Negative",
                    focus_timeout=0,
                    delay_after=-1,
                    send_key_delay=0,
                    click_before_input=False,
                ),
            )
            if element.get_value() != "Invalid_Delay_Negative":
                raise AssertionError("负延时异常前的剪贴板输入动作没有完成")
            available, actual = read_clipboard_text()
            if not available or actual != original_clipboard:
                raise AssertionError("负延时异常后剪贴板文本没有恢复")
            expect_exception(
                'delay_after="bad"',
                InvalidParamsError,
                lambda: element.clipboard_input(
                    "Invalid_Delay_Text",
                    focus_timeout=0,
                    delay_after="bad",  # type: ignore[arg-type]
                    send_key_delay=0,
                    click_before_input=False,
                ),
            )
            if element.get_value() != "Invalid_Delay_Text":
                raise AssertionError("非数字延时异常前的剪贴板输入动作没有完成")
            available, actual = read_clipboard_text()
            if not available or actual != original_clipboard:
                raise AssertionError("非数字延时异常后剪贴板文本没有恢复")
            return "非法延时在输入完成后被拒绝，且两次均恢复原剪贴板文本"

        results.append(run_case("非法延时", invalid_delay_case))

    except Exception as exc:
        if not results or results[-1].passed:
            results.append(
                CaseResult(
                    "测试准备",
                    False,
                    "无法继续执行剪贴板输入用例",
                    0.0,
                    [f"原因    : {exc}"],
                )
            )
    finally:
        def cleanup() -> tuple[str, list[str]]:
            errors: list[str] = []
            restored_value = False
            restored_clipboard = False
            if element is not None and original_value is not None:
                try:
                    element.input(
                        original_value,
                        False,
                        False,
                        False,
                        0,
                        0,
                        0,
                        False,
                    )
                    restored_value = element.get_value() == original_value
                    if not restored_value:
                        errors.append(
                            f"输入框原值未恢复：期望 {original_value!r}，实际 {element.get_value()!r}"
                        )
                except Exception as exc:
                    errors.append(f"恢复输入框原值失败：{exc}")
            if original_clipboard is not None:
                try:
                    write_clipboard_text(original_clipboard)
                    available, actual = read_clipboard_text()
                    restored_clipboard = available and actual == original_clipboard
                    if not restored_clipboard:
                        errors.append(
                            f"剪贴板原文未恢复：期望 {original_clipboard!r}，实际 {actual!r}"
                        )
                except Exception as exc:
                    errors.append(f"恢复剪贴板失败：{exc}")
            try:
                win32.manual_motion_off()
            except Exception as exc:
                errors.append(f"关闭人工轨迹失败：{exc}")
            if original_mouse is not None:
                try:
                    restore_cursor(original_mouse)
                except Exception as exc:
                    errors.append(f"恢复鼠标失败：{exc}")
            if original_foreground:
                try:
                    restore_foreground(original_foreground)
                except Exception as exc:
                    errors.append(f"恢复前台窗口失败：{exc}")
            if package is not None:
                try:
                    package.close()
                except Exception as exc:
                    errors.append(f"关闭 Package 失败：{exc}")
            if errors:
                raise RuntimeError("；".join(errors))
            extras: list[str] = []
            if restored_value:
                extras.append(f"恢复值    : {preview(original_value or '')}")
            if restored_clipboard:
                extras.append(f"剪贴板    : {preview(original_clipboard or '')}")
            if not extras:
                extras.append("未产生待恢复的输入框或剪贴板状态")
            return (
                "输入框原值、剪贴板、鼠标和原前台窗口已恢复，Package 已关闭",
                extras,
            )

        results.append(run_case("资源清理", cleanup))

    render_results(results)
    passed = sum(result.passed for result in results)
    failed = len(results) - passed
    total_ms = sum(result.elapsed_ms for result in results)
    print()
    if failed:
        print(colored("测试失败", ANSI_RED))
        print("  生命周期: READY_FOR_LIVE")
        print(f"  结果    : {passed}/{len(results)} 通过，{failed} 失败")
        print(f"  总耗时  : {total_ms:.1f}ms")
        print("  靶场程序: 保持运行")
        print("  退出码  : 1")
        return 1

    print(colored("测试通过", ANSI_GREEN))
    print("  生命周期: VERIFIED")
    print(f"  结果    : {passed}/{len(results)} 通过")
    print(f"  总耗时  : {total_ms:.1f}ms")
    print("  输入框  : 已恢复原值")
    print("  剪贴板  : 已恢复原文本")
    print("  鼠标位置: 已恢复")
    print("  Package : 已关闭")
    print("  靶场程序: 保持运行")
    print("  退出码  : 0")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
