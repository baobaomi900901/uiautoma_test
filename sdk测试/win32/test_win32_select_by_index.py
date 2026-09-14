r"""验证 ``uiautoma.win32.Win32Element.select_by_index()`` 的全部公开参数。

API 参数（均可按位置或关键字传入）：
    index: int                必填；从 0 开始的 UIA 候选项枚举索引，SDK 会调用 int(index)。
    delay_after: float = 1    选择完成后的等待秒数；None 或 0 不等待。

脚本参数：无。

前置条件：UIAutoma.exe 正在 dev 运行；当前元素库为
``D:\code\元素库\260902_win元素``；Win32 靶场已启动；元素库中存在
``win32靶场_表单控件_下拉框_城市``。

脚本动态读取候选项和原选项，只把 ``select_by_index()`` 作为被测动作。开始修改前必须
读到唯一的原选项，测试结束后恢复原选项、鼠标、前台窗口和 Package 连接。
"""

from __future__ import annotations

from _form_tab import ensure_form_tab

import ctypes
import inspect
import os
import sys
import time
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

import uiautoma
from uiautoma import ActionError, InvalidParamsError, win32
from uiautoma.win32 import Win32Element


LIBRARY_DIR = Path(r"D:\code\元素库\260902_win元素")
TARGET_ELEMENT = "win32靶场_表单控件_下拉框_城市"
TARGET_TITLE = "Win32 靶场 - UIA"
TARGET_CLASS = "XPathWin32ShootingRange"
TARGET_PROCESS = "win32-shooting-range-uia.exe"

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
class SelectionObservation:
    elapsed_ms: float
    strategy: str
    index: int
    selected_item: str
    reported_item: str
    reported_index: int


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


def selected_items(element: Win32Element) -> list[str]:
    return [str(item).strip() for item in element.get_selected_item() if str(item).strip()]


def assert_selected(element: Win32Element, expected_item: str, context: str) -> list[str]:
    actual = selected_items(element)
    if actual != [expected_item]:
        raise AssertionError(f"{context} 后选中项不一致：期望 {[expected_item]!r}，实际 {actual!r}")
    return actual


def observe_selection(
    element: Win32Element,
    call_text: str,
    invoke: Callable[[], Any],
    *,
    expected_index: int,
    expected_item: str,
) -> SelectionObservation:
    started = time.perf_counter()
    returned = invoke()
    elapsed_ms = (time.perf_counter() - started) * 1000.0
    if returned is not None:
        raise AssertionError(f"{call_text} 应返回 None，实际为 {returned!r}")
    result = element.last_result
    if result is None or not result.ok or not str(result.strategy or "").strip():
        raise AssertionError(f"{call_text} 未留下完整的成功 last_result")
    assert_selected(element, expected_item, call_text)
    reported_item = str(result.raw.get("selected_item") or "").strip()
    if reported_item and reported_item != expected_item:
        raise AssertionError(
            f"{call_text} 的 selected_item 应为 {expected_item!r}，实际 {reported_item!r}"
        )
    option = result.raw.get("option")
    if not isinstance(option, dict) or int(option.get("index", -1)) != expected_index:
        raise AssertionError(f"{call_text} 的 option.index 无效：{option!r}")
    return SelectionObservation(
        elapsed_ms,
        str(result.strategy),
        expected_index,
        expected_item,
        reported_item,
        int(option["index"]),
    )


def expected_names(expected: type[BaseException] | tuple[type[BaseException], ...]) -> str:
    types = expected if isinstance(expected, tuple) else (expected,)
    return "/".join(item.__name__ for item in types)


def expect_exception(
    call_text: str,
    expected: type[BaseException] | tuple[type[BaseException], ...],
    invoke: Callable[[], Any],
) -> BaseException:
    try:
        invoke()
    except expected as exc:
        return exc
    except Exception as exc:
        raise AssertionError(
            f"{call_text} 应抛出 {expected_names(expected)}，实际为 {type(exc).__name__}: {exc}"
        ) from exc
    raise AssertionError(f"{call_text} 未抛出 {expected_names(expected)}")


def expect_action_error(
    call_text: str,
    trace_fragment: str,
    invoke: Callable[[], Any],
) -> ActionError:
    error = expect_exception(call_text, ActionError, invoke)
    assert isinstance(error, ActionError)
    if trace_fragment not in error.trace_info:
        raise AssertionError(
            f"{call_text} 的 trace_info 应包含 {trace_fragment!r}，实际 {error.trace_info!r}"
        )
    return error


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
    print("  API     : uiautoma.win32.Win32Element.select_by_index")
    print(f"  元素库  : {LIBRARY_DIR}")
    print(f"  下拉元素: {TARGET_ELEMENT}")
    print(f"  测试窗口: {TARGET_TITLE}")
    print(f"  目标进程: {TARGET_PROCESS}")
    print("  索引规则: 从 0 开始，按运行时读取的候选项顺序选择")
    print("  状态恢复: 测试结束后恢复下拉框运行前的原选项")

    results: list[CaseResult] = []
    package: Any = None
    element: Win32Element | None = None
    candidates: list[str] = []
    original_selection: str | None = None
    original_mouse: tuple[int, int] | None = None
    original_foreground = 0
    default_elapsed_ms = 0.0

    def contract() -> str:
        signature = inspect.signature(Win32Element.select_by_index)
        parameters = list(signature.parameters.values())
        expected_parameter_names = ["self", "index", "delay_after"]
        expected_defaults = [inspect.Parameter.empty, inspect.Parameter.empty, 1]
        if [item.name for item in parameters] != expected_parameter_names:
            raise AssertionError(f"参数顺序变化：{signature}")
        if [item.default for item in parameters] != expected_defaults:
            raise AssertionError(f"参数默认值变化：{signature}")
        if any(item.kind is not inspect.Parameter.POSITIONAL_OR_KEYWORD for item in parameters):
            raise AssertionError(f"参数种类变化：{signature}")
        if str(signature.return_annotation) not in {"None", "<class 'NoneType'>"}:
            raise AssertionError(f"返回注解变化：{signature}")
        return "两个公开参数、默认值和位置/关键字调用规则符合合同"

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
            nonlocal element, candidates, original_selection
            nonlocal original_mouse, original_foreground
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
            raw_candidates = [
                str(item).strip() for item in element.get_all_select_items() if str(item).strip()
            ]
            if len(raw_candidates) < 3:
                raise RuntimeError(f"索引测试至少需要三个候选项，实际为 {raw_candidates!r}")
            normalized = [item.casefold() for item in raw_candidates]
            if len(set(normalized)) != len(normalized):
                raise RuntimeError(f"城市下拉框存在重名候选项，无法唯一验收：{raw_candidates!r}")
            candidates = raw_candidates
            current = selected_items(element)
            if len(current) != 1:
                raise RuntimeError(f"开始测试前必须有且仅有一个选中项，实际为 {current!r}")
            if current[0] not in candidates:
                raise RuntimeError(f"原选项不在候选项中：原选项 {current[0]!r}，候选项 {candidates!r}")
            original_selection = current[0]
            original_mouse = current_cursor()
            original_foreground = current_foreground()
            win32.manual_motion_off()
            return (
                "已定位城市下拉框，候选项顺序和原选项均可读取",
                [
                    f"候选项  : {list(enumerate(candidates))!r}",
                    f"原选项  : {original_selection!r}",
                    f"原索引  : {candidates.index(original_selection)}",
                    f"原鼠标  : {original_mouse}",
                ],
            )

        target_result = run_case("选择目标", acquire_target)
        results.append(target_result)
        if not target_result.passed:
            raise RuntimeError("选择目标准备失败")

        assert element is not None
        assert original_selection is not None

        def defaults() -> tuple[str, list[str]]:
            nonlocal default_elapsed_ms
            index = 1
            observation = observe_selection(
                element,
                f"element.select_by_index({index})",
                lambda: element.select_by_index(index),
                expected_index=index,
                expected_item=candidates[index],
            )
            default_elapsed_ms = observation.elapsed_ms
            if default_elapsed_ms < 900:
                raise AssertionError(f"默认 delay_after=1 等待不足：{default_elapsed_ms:.1f}ms")
            return (
                "仅传必填索引，默认 delay_after=1 生效并返回 None",
                [
                    f"索引    : {index}",
                    f"选中项  : {observation.selected_item!r}",
                    f"策略    : {observation.strategy}",
                ],
            )

        results.append(run_case("全部默认参数", defaults))

        def all_positional() -> tuple[str, list[str]]:
            index = 2
            observation = observe_selection(
                element,
                "两个参数全部按位置传入",
                lambda: element.select_by_index(index, 0),
                expected_index=index,
                expected_item=candidates[index],
            )
            return (
                "index 和 delay_after 均可按位置传入",
                [f"索引    : {index}", f"选中项  : {observation.selected_item!r}"],
            )

        results.append(run_case("全位置参数", all_positional))

        def first_index_case() -> tuple[str, list[str]]:
            observation = observe_selection(
                element,
                "index=0",
                lambda: element.select_by_index(index=0, delay_after=0),
                expected_index=0,
                expected_item=candidates[0],
            )
            return "首个索引 0 选择成功", [f"选中项  : {observation.selected_item!r}"]

        results.append(run_case("首个索引", first_index_case))

        def middle_index_case() -> tuple[str, list[str]]:
            index = len(candidates) // 2
            observation = observe_selection(
                element,
                f"index={index}",
                lambda: element.select_by_index(index=index, delay_after=0),
                expected_index=index,
                expected_item=candidates[index],
            )
            return "中间索引选择成功", [f"索引    : {index}", f"选中项  : {observation.selected_item!r}"]

        results.append(run_case("中间索引", middle_index_case))

        def last_index_case() -> tuple[str, list[str]]:
            index = len(candidates) - 1
            observation = observe_selection(
                element,
                f"index={index}",
                lambda: element.select_by_index(index=index, delay_after=0),
                expected_index=index,
                expected_item=candidates[index],
            )
            return "最后一个有效索引选择成功", [f"索引    : {index}", f"选中项  : {observation.selected_item!r}"]

        results.append(run_case("最后索引", last_index_case))

        def index_conversion_case() -> tuple[str, list[str]]:
            observe_selection(
                element,
                "index='1'",
                lambda: element.select_by_index("1", delay_after=0),  # type: ignore[arg-type]
                expected_index=1,
                expected_item=candidates[1],
            )
            observe_selection(
                element,
                "index=2.9",
                lambda: element.select_by_index(2.9, delay_after=0),  # type: ignore[arg-type]
                expected_index=2,
                expected_item=candidates[2],
            )
            observe_selection(
                element,
                "index=True",
                lambda: element.select_by_index(True, delay_after=0),
                expected_index=1,
                expected_item=candidates[1],
            )
            observe_selection(
                element,
                "index=False",
                lambda: element.select_by_index(False, delay_after=0),
                expected_index=0,
                expected_item=candidates[0],
            )
            return (
                "SDK 的 int(index) 转换接受整数文本、浮点数和布尔值",
                ["'1' -> 1", "2.9 -> 2", "True -> 1", "False -> 0"],
            )

        results.append(run_case("索引转换", index_conversion_case))

        def delay_after_case() -> tuple[str, list[str]]:
            fast_index = min(3, len(candidates) - 1)
            fast = observe_selection(
                element,
                "delay_after=None",
                lambda: element.select_by_index(fast_index, delay_after=None),
                expected_index=fast_index,
                expected_item=candidates[fast_index],
            )
            delayed_index = len(candidates) - 1
            delayed = observe_selection(
                element,
                "delay_after=0.2",
                lambda: element.select_by_index(delayed_index, delay_after=0.2),
                expected_index=delayed_index,
                expected_item=candidates[delayed_index],
            )
            if delayed.elapsed_ms < fast.elapsed_ms + 150:
                raise AssertionError(
                    f"动作后延时差异不足：None={fast.elapsed_ms:.1f}ms，0.2={delayed.elapsed_ms:.1f}ms"
                )
            if default_elapsed_ms < fast.elapsed_ms + 700:
                raise AssertionError(
                    f"默认 1 秒延时差异不足：默认={default_elapsed_ms:.1f}ms，None={fast.elapsed_ms:.1f}ms"
                )
            return (
                "delay_after=None 不等待，0.2 秒和默认 1 秒等待均生效",
                [
                    f"None    : {fast.elapsed_ms:.1f}ms",
                    f"0.2s    : {delayed.elapsed_ms:.1f}ms",
                    f"默认 1s : {default_elapsed_ms:.1f}ms",
                ],
            )

        results.append(run_case("动作后延时", delay_after_case))

        def negative_index_case() -> tuple[str, list[str]]:
            before = selected_items(element)
            error = expect_action_error(
                "index=-1",
                "select_item_not_found",
                lambda: element.select_by_index(-1, delay_after=0),
            )
            if selected_items(element) != before:
                raise AssertionError("负数索引失败后选中状态发生变化")
            return "负数索引被 ActionError 正确拒绝", [f"trace_info: {error.trace_info}"]

        results.append(run_case("负数索引", negative_index_case))

        def out_of_range_case() -> tuple[str, list[str]]:
            before = selected_items(element)
            index = len(candidates)
            error = expect_action_error(
                f"index={index}",
                "select_item_not_found",
                lambda: element.select_by_index(index, delay_after=0),
            )
            if selected_items(element) != before:
                raise AssertionError("越界索引失败后选中状态发生变化")
            return (
                "等于候选项数量的索引被识别为越界",
                [f"候选项数: {len(candidates)}", f"trace_info: {error.trace_info}"],
            )

        results.append(run_case("越界索引", out_of_range_case))

        def invalid_conversion_case() -> str:
            before = selected_items(element)
            expect_exception(
                "index='bad'",
                ValueError,
                lambda: element.select_by_index("bad", delay_after=0),  # type: ignore[arg-type]
            )
            expect_exception(
                "index=None",
                TypeError,
                lambda: element.select_by_index(None, delay_after=0),  # type: ignore[arg-type]
            )
            expect_exception(
                "index=object()",
                TypeError,
                lambda: element.select_by_index(object(), delay_after=0),  # type: ignore[arg-type]
            )
            if selected_items(element) != before:
                raise AssertionError("索引转换失败后选中状态发生变化")
            return "无法转换的字符串、None 和普通对象在 SDK 边界被正确拒绝"

        results.append(run_case("非法索引类型", invalid_conversion_case))

        def invalid_delay_case() -> tuple[str, list[str]]:
            negative_index = 1
            expect_exception(
                "delay_after=-1",
                InvalidParamsError,
                lambda: element.select_by_index(negative_index, delay_after=-1),
            )
            assert_selected(element, candidates[negative_index], "delay_after=-1")
            if element.last_result is None or not element.last_result.ok:
                raise AssertionError("负延时异常前没有保存成功的 last_result")

            text_index = 2
            expect_exception(
                'delay_after="bad"',
                InvalidParamsError,
                lambda: element.select_by_index(
                    text_index,
                    delay_after="bad",  # type: ignore[arg-type]
                ),
            )
            assert_selected(element, candidates[text_index], 'delay_after="bad"')
            if element.last_result is None or not element.last_result.ok:
                raise AssertionError("非数字延时异常前没有保存成功的 last_result")
            return (
                "负数和非数字延时均在选择完成后被 InvalidParamsError 拒绝",
                [
                    f"负延时选中: [{negative_index}] {candidates[negative_index]!r}",
                    f"文本延时选中: [{text_index}] {candidates[text_index]!r}",
                ],
            )

        results.append(run_case("非法延时", invalid_delay_case))

    except Exception as exc:
        if not results or results[-1].passed:
            results.append(
                CaseResult(
                    "测试准备",
                    False,
                    "无法继续执行索引选择用例",
                    0.0,
                    [f"原因    : {exc}"],
                )
            )
    finally:
        def cleanup() -> tuple[str, list[str]]:
            errors: list[str] = []
            restored = False
            if element is not None and original_selection is not None:
                try:
                    restore_index = candidates.index(original_selection)
                    element.select_by_index(restore_index, delay_after=0)
                    restored = selected_items(element) == [original_selection]
                    if not restored:
                        errors.append(
                            f"原选项未恢复：期望 {[original_selection]!r}，实际 {selected_items(element)!r}"
                        )
                except Exception as exc:
                    errors.append(f"恢复下拉框原选项失败：{exc}")
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
            return (
                "下拉框原选项、鼠标和原前台窗口已恢复，Package 已关闭",
                [f"恢复选项: {original_selection!r}" if restored else "未产生待恢复的选项状态"],
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
    print(f"  下拉框  : 已恢复原选项 {original_selection!r}")
    print("  鼠标位置: 已恢复")
    print("  Package : 已关闭")
    print("  靶场程序: 保持运行")
    print("  退出码  : 0")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
