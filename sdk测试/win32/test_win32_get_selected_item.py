r"""验证 ``uiautoma.win32.Win32Element.get_selected_item()`` 的公开行为。

API 参数：无。

返回值：
    list[str]    当前选择控件的选中项文本列表；单选控件也返回列表。

脚本参数：无。

前置条件：UIAutoma.exe 正在 dev 运行；当前元素库为
``D:\code\元素库\260902_win元素``；Win32 靶场已启动；元素库中存在
``win32靶场_表单控件_下拉框_城市``。

脚本使用已验证的 ``select_by_index()`` 准备不同选中状态，并通过 Windows 原生
ComboBox 消息独立读取当前索引和文本。测试结束后恢复原选项、鼠标、前台窗口和
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

import uiautoma
from uiautoma import win32
from uiautoma.win32 import Win32Element


LIBRARY_DIR = Path(r"D:\code\元素库\260902_win元素")
TARGET_ELEMENT = "win32靶场_表单控件_下拉框_城市"
TARGET_TITLE = "Win32 靶场 - UIA"
TARGET_CLASS = "XPathWin32ShootingRange"
TARGET_PROCESS = "win32-shooting-range-uia.exe"

CB_GETCOUNT = 0x0146
CB_GETCURSEL = 0x0147
CB_GETLBTEXT = 0x0148
CB_GETLBTEXTLEN = 0x0149
CB_SHOWDROPDOWN = 0x014F
CB_GETDROPPEDSTATE = 0x0157
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
class NativeComboSnapshot:
    handle: int
    items: list[str]
    selected_index: int
    dropped: bool


@dataclass(frozen=True)
class ReadObservation:
    elapsed_ms: float
    sdk_items: list[str]
    native_index: int
    native_item: str


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
    user32.SendMessageW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
    user32.SendMessageW.restype = wintypes.LPARAM
    return user32


def class_name(handle: int, user32: Any) -> str:
    buffer = ctypes.create_unicode_buffer(256)
    length = user32.GetClassNameW(handle, buffer, len(buffer))
    return buffer.value[:length] if length > 0 else ""


def combo_items(handle: int, user32: Any) -> list[str]:
    count = int(user32.SendMessageW(handle, CB_GETCOUNT, 0, 0))
    if count < 0:
        return []
    items: list[str] = []
    for index in range(count):
        length = int(user32.SendMessageW(handle, CB_GETLBTEXTLEN, index, 0))
        if length < 0:
            raise RuntimeError(f"CB_GETLBTEXTLEN({index}) 失败：{length}")
        buffer = ctypes.create_unicode_buffer(length + 1)
        copied = int(
            user32.SendMessageW(
                handle,
                CB_GETLBTEXT,
                index,
                ctypes.cast(buffer, ctypes.c_void_p).value or 0,
            )
        )
        if copied < 0:
            raise RuntimeError(f"CB_GETLBTEXT({index}) 失败：{copied}")
        items.append(buffer.value)
    return items


def snapshot_combo(handle: int) -> NativeComboSnapshot:
    user32 = _user32()
    return NativeComboSnapshot(
        handle=handle,
        items=combo_items(handle, user32),
        selected_index=int(user32.SendMessageW(handle, CB_GETCURSEL, 0, 0)),
        dropped=bool(user32.SendMessageW(handle, CB_GETDROPPEDSTATE, 0, 0)),
    )


def find_native_combo(parent_handle: int) -> NativeComboSnapshot:
    user32 = _user32()
    candidates: list[NativeComboSnapshot] = []

    @WNDENUMPROC
    def callback(handle: int, _lparam: int) -> bool:
        if class_name(handle, user32).casefold() == "combobox":
            items = combo_items(handle, user32)
            if items:
                candidates.append(
                    NativeComboSnapshot(
                        handle=int(handle),
                        items=items,
                        selected_index=int(user32.SendMessageW(handle, CB_GETCURSEL, 0, 0)),
                        dropped=bool(user32.SendMessageW(handle, CB_GETDROPPEDSTATE, 0, 0)),
                    )
                )
        return True

    if not user32.EnumChildWindows(parent_handle, callback, 0) and ctypes.get_last_error():
        raise OSError(f"EnumChildWindows 失败：{ctypes.get_last_error()}")
    if len(candidates) != 1:
        summary = [(item.handle, item.items) for item in candidates]
        raise RuntimeError(f"预期找到一个含候选项的原生 ComboBox，实际为 {summary!r}")
    return candidates[0]


def read_and_verify(
    element: Win32Element,
    native_handle: int,
    expected_index: int,
    expected_item: str,
) -> ReadObservation:
    started = time.perf_counter()
    returned = element.get_selected_item()
    elapsed_ms = (time.perf_counter() - started) * 1000.0
    if not isinstance(returned, list) or not all(isinstance(item, str) for item in returned):
        raise TypeError(f"返回值不是 list[str]：{returned!r}")
    native = snapshot_combo(native_handle)
    if native.selected_index != expected_index:
        raise AssertionError(
            f"原生选中索引不一致：期望 {expected_index}，实际 {native.selected_index}"
        )
    native_item = native.items[native.selected_index]
    if native_item != expected_item:
        raise AssertionError(f"原生选中项不一致：期望 {expected_item!r}，实际 {native_item!r}")
    if returned != [native_item]:
        raise AssertionError(f"SDK 与原生选中项不一致：SDK={returned!r}，原生={[native_item]!r}")
    if native.dropped:
        raise AssertionError("读取结束后城市下拉框仍处于展开状态")
    return ReadObservation(elapsed_ms, returned, native.selected_index, native_item)


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
    print("  API     : uiautoma.win32.Win32Element.get_selected_item")
    print(f"  元素库  : {LIBRARY_DIR}")
    print(f"  下拉元素: {TARGET_ELEMENT}")
    print(f"  测试窗口: {TARGET_TITLE}")
    print(f"  目标进程: {TARGET_PROCESS}")
    print("  场景准备: 使用已验证的 select_by_index() 依次选择所有候选项")
    print("  原生参照: CB_GETCURSEL 与 CB_GETLBTEXT 独立读取当前选项")
    print("  状态恢复: 测试结束后恢复下拉框运行前的原选项")

    results: list[CaseResult] = []
    package: Any = None
    element: Win32Element | None = None
    native_before: NativeComboSnapshot | None = None
    original_mouse: tuple[int, int] | None = None
    original_foreground = 0

    def contract() -> str:
        signature = inspect.signature(Win32Element.get_selected_item)
        parameters = list(signature.parameters.values())
        if [item.name for item in parameters] != ["self"]:
            raise AssertionError(f"公开参数发生变化：{signature}")
        if parameters[0].kind is not inspect.Parameter.POSITIONAL_OR_KEYWORD:
            raise AssertionError(f"self 参数种类变化：{signature}")
        annotation = str(signature.return_annotation).replace(" ", "")
        if annotation not in {"list[str]", "typing.List[str]"}:
            raise AssertionError(f"返回注解变化：{signature}")
        return "公开签名无参数并返回 list[str]"

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

        def acquire_target() -> tuple[str, list[str]]:
            nonlocal element, native_before, original_mouse, original_foreground
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
            if not isinstance(element, Win32Element):
                raise TypeError(f"目标类型不是 Win32Element：{type(element).__name__}")
            native_before = find_native_combo(window_handle)
            if len(native_before.items) < 2:
                raise RuntimeError(f"原生 ComboBox 候选项不足：{native_before.items!r}")
            if native_before.selected_index < 0 or native_before.selected_index >= len(
                native_before.items
            ):
                raise RuntimeError(f"原生 ComboBox 选中索引无效：{native_before.selected_index}")
            if native_before.dropped:
                raise RuntimeError("运行测试前请先收起城市下拉框")
            original_mouse = current_cursor()
            original_foreground = current_foreground()
            return (
                "已定位 SDK 元素及唯一原生 ComboBox，初始选中状态有效",
                [
                    f"ComboBox : {native_before.handle} (0x{native_before.handle:x})",
                    f"候选项  : {list(enumerate(native_before.items))!r}",
                    f"原选项  : [{native_before.selected_index}] "
                    f"{native_before.items[native_before.selected_index]!r}",
                ],
            )

        target_result = run_case("测试目标", acquire_target)
        results.append(target_result)
        if not target_result.passed:
            raise RuntimeError("测试目标准备失败")

        assert element is not None
        assert native_before is not None

        def initial_read_case() -> tuple[str, list[str]]:
            expected_index = native_before.selected_index
            expected_item = native_before.items[expected_index]
            observation = read_and_verify(
                element,
                native_before.handle,
                expected_index,
                expected_item,
            )
            return (
                "初始单选状态以 list[str] 返回，并与原生当前项一致",
                [
                    f"SDK 返回: {observation.sdk_items!r}",
                    f"原生项  : [{observation.native_index}] {observation.native_item!r}",
                ],
            )

        results.append(run_case("初始选中项", initial_read_case))

        for candidate_index, candidate_item in enumerate(native_before.items):
            def indexed_read_case(
                index: int = candidate_index,
                item: str = candidate_item,
            ) -> tuple[str, list[str]]:
                setup_started = time.perf_counter()
                element.select_by_index(index, delay_after=0)
                setup_ms = (time.perf_counter() - setup_started) * 1000.0
                observation = read_and_verify(element, native_before.handle, index, item)
                return (
                    "场景准备后 SDK 与原生均返回对应选中项",
                    [
                        f"索引    : {index}",
                        f"选中项  : {observation.sdk_items!r}",
                        f"准备耗时: {setup_ms:.1f}ms",
                        f"读取耗时: {observation.elapsed_ms:.1f}ms",
                    ],
                )

            results.append(run_case(f"索引 {candidate_index} 读取", indexed_read_case))

        def repeatability_case() -> tuple[str, list[str]]:
            native = snapshot_combo(native_before.handle)
            expected = [native.items[native.selected_index]]
            started = time.perf_counter()
            readings = [element.get_selected_item() for _ in range(3)]
            elapsed_ms = (time.perf_counter() - started) * 1000.0
            if any(reading != expected for reading in readings):
                raise AssertionError(f"三次读取结果不一致：期望 {expected!r}，实际 {readings!r}")
            return (
                "连续三次读取均返回相同的单项列表",
                [f"单次结果: {expected!r}", f"三次耗时: {elapsed_ms:.1f}ms"],
            )

        results.append(run_case("重复读取", repeatability_case))

        def result_isolation_case() -> str:
            native = snapshot_combo(native_before.handle)
            expected = [native.items[native.selected_index]]
            first = element.get_selected_item()
            first.append("__LOCAL_MUTATION__")
            second = element.get_selected_item()
            if second != expected:
                raise AssertionError(f"修改上次返回列表影响了后续读取：{second!r}")
            return "修改调用方持有的返回列表不会影响 Runtime 选中状态"

        results.append(run_case("返回列表隔离", result_isolation_case))

        def last_result_case() -> str:
            before = element.last_result
            element.get_selected_item()
            if element.last_result is not before:
                raise AssertionError("读取 API 意外修改了 element.last_result")
            return "读取 API 不创建动作结果，element.last_result 保持场景准备结果"

        results.append(run_case("动作结果隔离", last_result_case))

        def extra_arguments_case() -> str:
            expect_type_error(
                "get_selected_item(0)",
                lambda: element.get_selected_item(0),  # type: ignore[call-arg]
            )
            expect_type_error(
                "get_selected_item(timeout=0)",
                lambda: element.get_selected_item(timeout=0),  # type: ignore[call-arg]
            )
            return "额外位置参数和 timeout 关键字均被 TypeError 拒绝"

        results.append(run_case("额外参数", extra_arguments_case))

    except Exception as exc:
        if not results or results[-1].passed:
            results.append(
                CaseResult(
                    "测试准备",
                    False,
                    "无法继续执行选中项读取用例",
                    0.0,
                    [f"原因    : {exc}"],
                )
            )
    finally:
        def cleanup() -> tuple[str, list[str]]:
            errors: list[str] = []
            restored_selection = False
            collapsed = False
            if native_before is not None:
                try:
                    current = snapshot_combo(native_before.handle)
                    if current.selected_index != native_before.selected_index and element is not None:
                        element.select_by_index(native_before.selected_index, delay_after=0)
                    current = snapshot_combo(native_before.handle)
                    restored_selection = current.selected_index == native_before.selected_index
                    if not restored_selection:
                        errors.append(
                            f"原选中索引未恢复：期望 {native_before.selected_index}，"
                            f"实际 {current.selected_index}"
                        )
                    if current.dropped:
                        _user32().SendMessageW(native_before.handle, CB_SHOWDROPDOWN, 0, 0)
                    collapsed = not snapshot_combo(native_before.handle).dropped
                    if not collapsed:
                        errors.append("城市下拉框未恢复为收起状态")
                except Exception as exc:
                    errors.append(f"恢复 ComboBox 状态失败：{exc}")
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
            if native_before is not None and restored_selection:
                extras.append(
                    f"恢复选项: [{native_before.selected_index}] "
                    f"{native_before.items[native_before.selected_index]!r}"
                )
            if native_before is not None and collapsed:
                extras.append("展开状态: 已收起")
            if not extras:
                extras.append("未产生待恢复的 ComboBox 状态")
            return (
                "原选项和收起状态已恢复，鼠标、前台窗口及 Package 已清理",
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
    print(
        f"  下拉框  : 已恢复原选项 "
        f"[{native_before.selected_index}] {native_before.items[native_before.selected_index]!r}"
        if native_before is not None
        else "  下拉框  : 未产生待恢复状态"
    )
    print("  展开状态: 已收起")
    print("  鼠标位置: 已恢复")
    print("  Package : 已关闭")
    print("  靶场程序: 保持运行")
    print("  退出码  : 0")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
