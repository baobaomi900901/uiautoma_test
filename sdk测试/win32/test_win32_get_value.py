r"""验证 ``uiautoma.win32.Win32Element.get_value()`` 的公开行为。

API 参数：无。

返回值：
    str    当前界面元素的实时值；没有可读 Value 时返回空字符串。

脚本参数：无。

前置条件：UIAutoma.exe 正在 dev 运行；当前元素库为
``D:\code\元素库\260902_win元素``；Win32 靶场已启动；元素库中存在
``win32靶场_表单控件_输入框_姓名`` 和 ``win32靶场_表单控件_按钮_保存``。

脚本根据 SDK 元素物理边界定位原生 Edit，通过 WM_SETTEXT/WM_GETTEXT 准备和独立读取
测试值；启动时启用 Per-Monitor DPI Awareness v2，确保两套边界都使用物理像素。
只把 ``get_value()`` 作为被测 API。测试结束后恢复输入框原值、鼠标、前台窗口和
Package 连接。
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


DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2 = ctypes.c_void_p(-4)


def enable_per_monitor_dpi_awareness() -> str:
    """让当前进程或线程的 User32 坐标 API 返回物理像素。"""

    user32 = ctypes.WinDLL("user32", use_last_error=True)
    try:
        set_process_context = user32.SetProcessDpiAwarenessContext
        set_process_context.argtypes = [ctypes.c_void_p]
        set_process_context.restype = wintypes.BOOL
        if set_process_context(DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2):
            return "Per-Monitor v2（进程）"
    except (AttributeError, OSError):
        pass

    try:
        set_thread_context = user32.SetThreadDpiAwarenessContext
        set_thread_context.argtypes = [ctypes.c_void_p]
        set_thread_context.restype = ctypes.c_void_p
        previous = set_thread_context(DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2)
        if previous:
            return "Per-Monitor v2（线程）"
    except (AttributeError, OSError):
        pass

    error = ctypes.get_last_error()
    message = ctypes.FormatError(error).strip() if error else "未知错误"
    raise RuntimeError(f"无法启用 Per-Monitor DPI Awareness v2：{message}")


DPI_AWARENESS_MODE = enable_per_monitor_dpi_awareness()

import uiautoma
from uiautoma import win32
from uiautoma.win32 import Win32Element


LIBRARY_DIR = Path(r"D:\code\元素库\260902_win元素")
TARGET_ELEMENT = "win32靶场_表单控件_输入框_姓名"
NO_VALUE_ELEMENT = "win32靶场_表单控件_按钮_保存"
TARGET_TITLE = "Win32 靶场 - UIA"
TARGET_CLASS = "XPathWin32ShootingRange"
TARGET_PROCESS = "win32-shooting-range-uia.exe"

WM_SETTEXT = 0x000C
WM_GETTEXT = 0x000D
WM_GETTEXTLENGTH = 0x000E
WNDENUMPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)

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


@dataclass(frozen=True)
class ValueObservation:
    elapsed_ms: float
    sdk_value: str
    native_value: str


class POINT(ctypes.Structure):
    _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]


class RECT(ctypes.Structure):
    _fields_ = [
        ("left", ctypes.c_long),
        ("top", ctypes.c_long),
        ("right", ctypes.c_long),
        ("bottom", ctypes.c_long),
    ]


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


def preview(value: str, limit: int = 70) -> str:
    escaped = value.replace("\r", "\\r").replace("\n", "\\n")
    return repr(escaped if len(escaped) <= limit else escaped[: limit - 1] + "…")


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


def _user32() -> Any:
    user32 = ctypes.WinDLL("user32", use_last_error=True)
    user32.EnumChildWindows.argtypes = [wintypes.HWND, WNDENUMPROC, wintypes.LPARAM]
    user32.EnumChildWindows.restype = wintypes.BOOL
    user32.GetClassNameW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
    user32.GetClassNameW.restype = ctypes.c_int
    user32.GetWindowRect.argtypes = [wintypes.HWND, ctypes.POINTER(RECT)]
    user32.GetWindowRect.restype = wintypes.BOOL
    user32.SendMessageW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
    user32.SendMessageW.restype = wintypes.LPARAM
    return user32


def class_name(handle: int, user32: Any) -> str:
    buffer = ctypes.create_unicode_buffer(256)
    length = user32.GetClassNameW(handle, buffer, len(buffer))
    return buffer.value[:length] if length > 0 else ""


def window_rect(handle: int, user32: Any) -> tuple[int, int, int, int]:
    rect = RECT()
    if not user32.GetWindowRect(handle, ctypes.byref(rect)):
        raise OSError(f"GetWindowRect({handle}) 失败：{ctypes.get_last_error()}")
    return (
        int(rect.left),
        int(rect.top),
        int(rect.right - rect.left),
        int(rect.bottom - rect.top),
    )


def rect_near(
    actual: tuple[int, int, int, int],
    expected: tuple[int, int, int, int],
    tolerance: int = 3,
) -> bool:
    return all(abs(left - right) <= tolerance for left, right in zip(actual, expected))


def find_native_edit(
    parent_handle: int,
    expected_rect: tuple[int, int, int, int],
) -> tuple[int, tuple[int, int, int, int]]:
    user32 = _user32()
    matches: list[tuple[int, tuple[int, int, int, int]]] = []

    @WNDENUMPROC
    def callback(handle: int, _lparam: int) -> bool:
        if class_name(handle, user32).casefold() == "edit":
            rect = window_rect(handle, user32)
            if rect_near(rect, expected_rect):
                matches.append((int(handle), rect))
        return True

    if not user32.EnumChildWindows(parent_handle, callback, 0) and ctypes.get_last_error():
        raise OSError(f"EnumChildWindows 失败：{ctypes.get_last_error()}")
    if len(matches) != 1:
        raise RuntimeError(
            f"无法按物理边界唯一定位原生 Edit：期望 {expected_rect}，匹配 {matches!r}"
        )
    return matches[0]


def get_native_text(handle: int) -> str:
    user32 = _user32()
    length = int(user32.SendMessageW(handle, WM_GETTEXTLENGTH, 0, 0))
    if length < 0:
        raise RuntimeError(f"WM_GETTEXTLENGTH 失败：{length}")
    buffer = ctypes.create_unicode_buffer(length + 1)
    copied = int(
        user32.SendMessageW(
            handle,
            WM_GETTEXT,
            len(buffer),
            ctypes.cast(buffer, ctypes.c_void_p).value or 0,
        )
    )
    if copied < 0:
        raise RuntimeError(f"WM_GETTEXT 失败：{copied}")
    return buffer.value


def set_native_text(handle: int, value: str) -> None:
    user32 = _user32()
    buffer = ctypes.create_unicode_buffer(value)
    succeeded = int(
        user32.SendMessageW(
            handle,
            WM_SETTEXT,
            0,
            ctypes.cast(buffer, ctypes.c_void_p).value or 0,
        )
    )
    if not succeeded:
        raise RuntimeError("WM_SETTEXT 返回失败")
    actual = get_native_text(handle)
    if actual != value:
        raise AssertionError(f"WM_SETTEXT 后原生值不一致：期望 {value!r}，实际 {actual!r}")


def observe_value(element: Win32Element, native_handle: int, expected: str) -> ValueObservation:
    started = time.perf_counter()
    returned = element.get_value()
    elapsed_ms = (time.perf_counter() - started) * 1000.0
    native = get_native_text(native_handle)
    if not isinstance(returned, str):
        raise TypeError(f"get_value() 返回类型不是 str：{type(returned).__name__}")
    if native != expected:
        raise AssertionError(f"原生 Edit 值不一致：期望 {expected!r}，实际 {native!r}")
    if returned != native:
        raise AssertionError(f"SDK 与原生值不一致：SDK={returned!r}，原生={native!r}")
    return ValueObservation(elapsed_ms, returned, native)


def expect_type_error(call_text: str, invoke: Callable[[], Any]) -> None:
    try:
        invoke()
    except TypeError:
        return
    except Exception as exc:
        raise AssertionError(
            f"{call_text} 应抛出 TypeError，实际为 {type(exc).__name__}: {exc}"
        ) from exc
    raise AssertionError(f"{call_text} 未抛出 TypeError")


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
    detail_width = max(72, max(display_width(item.detail) for item in results) + 2)
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
    print("  API       : uiautoma.win32.Win32Element.get_value")
    print(f"  元素库    : {LIBRARY_DIR}")
    print(f"  输入元素  : {TARGET_ELEMENT}")
    print(f"  无值元素  : {NO_VALUE_ELEMENT}")
    print(f"  测试窗口  : {TARGET_TITLE}")
    print(f"  目标进程  : {TARGET_PROCESS}")
    print(f"  DPI 模式  : {DPI_AWARENESS_MODE}")
    print("  原生参照  : WM_SETTEXT 准备值，WM_GETTEXT 独立读取值")
    print("  数据恢复  : 测试结束后恢复输入框运行前的原值")

    results: list[CaseResult] = []
    package: Any = None
    element: Win32Element | None = None
    no_value_element: Win32Element | None = None
    native_handle = 0
    native_rect: tuple[int, int, int, int] | None = None
    original_value: str | None = None
    original_mouse: tuple[int, int] | None = None
    original_foreground = 0
    original_last_result: Any = None

    def contract() -> str:
        signature = inspect.signature(Win32Element.get_value)
        parameters = list(signature.parameters.values())
        if [item.name for item in parameters] != ["self"]:
            raise AssertionError(f"公开参数发生变化：{signature}")
        if parameters[0].kind is not inspect.Parameter.POSITIONAL_OR_KEYWORD:
            raise AssertionError(f"self 参数种类变化：{signature}")
        if str(signature.return_annotation) not in {"str", "<class 'str'>"}:
            raise AssertionError(f"返回注解变化：{signature}")
        return "公开签名无参数并返回 str"

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

        def acquire_targets() -> tuple[str, list[str]]:
            nonlocal element, no_value_element, native_handle, native_rect
            nonlocal original_value, original_mouse, original_foreground, original_last_result
            window = win32.get(
                TARGET_TITLE,
                class_name=TARGET_CLASS,
                process_name=TARGET_PROCESS,
                timeout=5,
            )
            window_handle = int(window.get_detail("handle"))
            if window_handle <= 0:
                raise RuntimeError(f"靶场窗口句柄无效：{window_handle}")
            element = window.find(package.selector(TARGET_ELEMENT, kind="win"), timeout=5)
            no_value_element = window.find(
                package.selector(NO_VALUE_ELEMENT, kind="win"),
                timeout=5,
            )
            if not isinstance(element, Win32Element) or not isinstance(
                no_value_element, Win32Element
            ):
                raise TypeError("测试目标没有返回 Win32Element")
            raw_rect = element.get_bounding(to96dpi=False, relative_to="screen")
            if not isinstance(raw_rect, (tuple, list)) or len(raw_rect) != 4:
                raise RuntimeError(f"输入框物理边界无效：{raw_rect!r}")
            expected_rect = tuple(int(value) for value in raw_rect)
            native_handle, native_rect = find_native_edit(window_handle, expected_rect)
            original_value = get_native_text(native_handle)
            original_mouse = current_cursor()
            original_foreground = current_foreground()
            original_last_result = element.last_result
            return (
                "已按物理边界唯一定位 SDK 输入元素和原生 Edit",
                [
                    f"Edit 句柄 : {native_handle} (0x{native_handle:x})",
                    f"SDK 边界 : {expected_rect}",
                    f"原生边界 : {native_rect}",
                    f"输入框原值: {preview(original_value)}",
                ],
            )

        target_result = run_case("测试目标", acquire_targets)
        results.append(target_result)
        if not target_result.passed:
            raise RuntimeError("测试目标准备失败")

        assert element is not None
        assert no_value_element is not None
        assert native_handle > 0
        assert original_value is not None

        def initial_value_case() -> tuple[str, list[str]]:
            observation = observe_value(element, native_handle, original_value)
            return (
                "初始 SDK 值为 str，并与原生 Edit 当前值一致",
                [
                    f"SDK 值  : {preview(observation.sdk_value)}",
                    f"原生值  : {preview(observation.native_value)}",
                    f"读取耗时: {observation.elapsed_ms:.1f}ms",
                ],
            )

        results.append(run_case("初始值", initial_value_case))

        def value_case(name: str, value: str) -> Callable[[], tuple[str, list[str]]]:
            def check() -> tuple[str, list[str]]:
                set_native_text(native_handle, value)
                observation = observe_value(element, native_handle, value)
                return (
                    f"{name}经原生消息写入后，SDK 与原生读取一致",
                    [f"实际值  : {preview(observation.sdk_value)}", f"读取耗时: {observation.elapsed_ms:.1f}ms"],
                )

            return check

        results.append(run_case("空字符串", value_case("空字符串", "")))
        results.append(run_case("英文数字", value_case("英文数字", "UIAutoma_Value_123")))
        results.append(run_case("中文文本", value_case("中文文本", "中文值_自动化测试")))
        results.append(run_case("符号与空格", value_case("符号与空格", "  {}[]!@#_+-=()  ")))

        def repeatability_case() -> tuple[str, list[str]]:
            expected = get_native_text(native_handle)
            started = time.perf_counter()
            readings = [element.get_value() for _ in range(3)]
            elapsed_ms = (time.perf_counter() - started) * 1000.0
            if readings != [expected, expected, expected]:
                raise AssertionError(f"三次读取不一致：期望 {expected!r}，实际 {readings!r}")
            return (
                "连续三次读取均返回相同字符串",
                [f"实际值  : {preview(expected)}", f"三次耗时: {elapsed_ms:.1f}ms"],
            )

        results.append(run_case("重复读取", repeatability_case))

        def no_value_case() -> tuple[str, list[str]]:
            returned = no_value_element.get_value()
            if not isinstance(returned, str):
                raise TypeError(f"无 Value 控件返回类型不是 str：{type(returned).__name__}")
            if returned != "":
                raise AssertionError(f"保存按钮应返回空字符串，实际为 {returned!r}")
            return "保存按钮没有可读 Value，返回空字符串", [f"实际值  : {returned!r}"]

        results.append(run_case("无 Value 控件", no_value_case))

        def last_result_case() -> str:
            element.get_value()
            if element.last_result is not original_last_result:
                raise AssertionError("读取 API 意外修改了 element.last_result")
            return "读取 API 不创建动作结果，element.last_result 保持原值"

        results.append(run_case("动作结果隔离", last_result_case))

        def extra_arguments_case() -> str:
            expect_type_error("get_value(0)", lambda: element.get_value(0))  # type: ignore[call-arg]
            expect_type_error(
                "get_value(timeout=0)",
                lambda: element.get_value(timeout=0),  # type: ignore[call-arg]
            )
            return "额外位置参数和 timeout 关键字均被 TypeError 拒绝"

        results.append(run_case("额外参数", extra_arguments_case))

    except Exception as exc:
        if not results or results[-1].passed:
            results.append(
                CaseResult(
                    "测试准备",
                    False,
                    "无法继续执行实时值读取用例",
                    0.0,
                    [f"原因    : {exc}"],
                )
            )
    finally:
        def cleanup() -> tuple[str, list[str]]:
            errors: list[str] = []
            restored = False
            if native_handle > 0 and original_value is not None:
                try:
                    set_native_text(native_handle, original_value)
                    native_actual = get_native_text(native_handle)
                    sdk_actual = element.get_value() if element is not None else native_actual
                    restored = native_actual == original_value and sdk_actual == original_value
                    if not restored:
                        errors.append(
                            f"输入框原值未恢复：期望 {original_value!r}，"
                            f"原生 {native_actual!r}，SDK {sdk_actual!r}"
                        )
                except Exception as exc:
                    errors.append(f"恢复输入框原值失败：{exc}")
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
            return (
                "输入框原值、鼠标和原前台窗口已恢复，Package 已关闭",
                [f"恢复值  : {preview(original_value or '')}" if restored else "未产生待恢复输入值"],
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
    print(f"  输入框  : 已恢复原值 {preview(original_value or '')}")
    print("  鼠标位置: 已恢复")
    print("  Package : 已关闭")
    print("  靶场程序: 保持运行")
    print("  退出码  : 0")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
