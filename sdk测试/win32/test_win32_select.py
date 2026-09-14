r"""验证 ``uiautoma.win32.Win32Element.select()`` 的全部公开参数。

API 参数（均可按位置或关键字传入）：
    item: str                 必填；目标选项文本，SDK 会先调用 str(item)。
    mode: str = "fuzzy"       匹配模式：exact、contains、fuzzy 或 regex。
    delay_after: float = 1    选择完成后的等待秒数；None 或 0 不等待。

脚本参数：无。

前置条件：UIAutoma.exe 正在 dev 运行；当前元素库为
``D:\code\元素库\260902_win元素``；Win32 靶场已启动；元素库中存在
``win32靶场_表单控件_下拉框_城市``。

脚本使用 ``get_all_select_items()`` 和 ``get_selected_item()`` 观察候选项及选中状态，
只把 ``select()`` 作为被测动作。开始修改前必须读到唯一的原选项，测试结束后恢复原选项、
鼠标、前台窗口和 Package 连接。
"""

from __future__ import annotations

from _form_tab import ensure_form_tab

import ctypes
import inspect
import os
import re
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
    expected_item: str
    selected_items: list[str]
    reported_item: str


class POINT(ctypes.Structure):
    _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]


class ItemText:
    def __init__(self, value: str) -> None:
        self.value = value

    def __str__(self) -> str:
        return self.value


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


def unique_fragment(item: str, candidates: list[str]) -> str:
    normalized_candidates = [candidate.casefold() for candidate in candidates]
    for length in range(1, len(item)):
        for start in range(0, len(item) - length + 1):
            fragment = item[start : start + length]
            wanted = fragment.casefold()
            if sum(wanted in candidate for candidate in normalized_candidates) == 1:
                return fragment
    raise RuntimeError(f"无法为选项 {item!r} 构造唯一的真子串")


def observe_select(
    element: Win32Element,
    call_text: str,
    invoke: Callable[[], Any],
    *,
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
    actual = assert_selected(element, expected_item, call_text)
    reported = str(result.raw.get("selected_item") or "").strip()
    if reported and reported != expected_item:
        raise AssertionError(
            f"{call_text} 的 last_result.selected_item 应为 {expected_item!r}，实际 {reported!r}"
        )
    return SelectionObservation(
        elapsed_ms,
        str(result.strategy),
        expected_item,
        actual,
        reported,
    )


def expect_exception(
    call_text: str,
    expected: type[BaseException],
    invoke: Callable[[], Any],
) -> BaseException:
    try:
        invoke()
    except expected as exc:
        return exc
    except Exception as exc:
        raise AssertionError(
            f"{call_text} 应抛出 {expected.__name__}，实际为 {type(exc).__name__}: {exc}"
        ) from exc
    raise AssertionError(f"{call_text} 未抛出 {expected.__name__}")


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
    print("  API     : uiautoma.win32.Win32Element.select")
    print(f"  元素库  : {LIBRARY_DIR}")
    print(f"  下拉元素: {TARGET_ELEMENT}")
    print(f"  测试窗口: {TARGET_TITLE}")
    print(f"  目标进程: {TARGET_PROCESS}")
    print("  状态恢复: 测试结束后恢复下拉框运行前的原选项")

    results: list[CaseResult] = []
    package: Any = None
    element: Win32Element | None = None
    candidates: list[str] = []
    original_selection: str | None = None
    original_mouse: tuple[int, int] | None = None
    original_foreground = 0

    def contract() -> str:
        signature = inspect.signature(Win32Element.select)
        parameters = list(signature.parameters.values())
        expected_names = ["self", "item", "mode", "delay_after"]
        expected_defaults = [
            inspect.Parameter.empty,
            inspect.Parameter.empty,
            "fuzzy",
            1,
        ]
        if [item.name for item in parameters] != expected_names:
            raise AssertionError(f"参数顺序变化：{signature}")
        if [item.default for item in parameters] != expected_defaults:
            raise AssertionError(f"参数默认值变化：{signature}")
        if any(item.kind is not inspect.Parameter.POSITIONAL_OR_KEYWORD for item in parameters):
            raise AssertionError(f"参数种类变化：{signature}")
        if str(signature.return_annotation) not in {"None", "<class 'NoneType'>"}:
            raise AssertionError(f"返回注解变化：{signature}")
        return "三个公开参数、默认值和位置/关键字调用规则符合合同"

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
            if len(raw_candidates) < 2:
                raise RuntimeError(f"城市下拉框至少需要两个候选项，实际为 {raw_candidates!r}")
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
                "已定位城市下拉框，候选项和原选项均可读取",
                [
                    f"候选项  : {candidates!r}",
                    f"原选项  : {original_selection!r}",
                    f"原鼠标  : {original_mouse}",
                ],
            )

        target_result = run_case("选择目标", acquire_target)
        results.append(target_result)
        if not target_result.passed:
            raise RuntimeError("选择目标准备失败")

        assert element is not None
        assert original_selection is not None

        original_index = candidates.index(original_selection)

        def option(step: int) -> str:
            return candidates[(original_index + step) % len(candidates)]

        def defaults() -> tuple[str, list[str]]:
            target = option(1)
            fragment = unique_fragment(target, candidates)
            observation = observe_select(
                element,
                f"element.select({fragment!r})",
                lambda: element.select(fragment),
                expected_item=target,
            )
            if observation.elapsed_ms < 900:
                raise AssertionError(f"默认 delay_after=1 等待不足：{observation.elapsed_ms:.1f}ms")
            return (
                "默认 fuzzy 真子串匹配成功，并完成默认约 1 秒等待",
                [
                    f"输入文本: {fragment!r}",
                    f"选中项  : {target!r}",
                    f"策略    : {observation.strategy}",
                ],
            )

        results.append(run_case("全部默认参数", defaults))

        def all_positional_exact() -> tuple[str, list[str]]:
            target = option(2)
            observation = observe_select(
                element,
                "三个参数全部按位置传入",
                lambda: element.select(target, "exact", 0),
                expected_item=target,
            )
            return (
                "三个参数可按位置传入，exact 完整匹配并返回 None",
                [f"选中项  : {target!r}", f"策略    : {observation.strategy}"],
            )

        results.append(run_case("全位置与精确匹配", all_positional_exact))

        def contains_case() -> tuple[str, list[str]]:
            target = option(3)
            fragment = unique_fragment(target, candidates)
            observation = observe_select(
                element,
                f"element.select({fragment!r}, mode='contains', delay_after=0)",
                lambda: element.select(fragment, mode="contains", delay_after=0),
                expected_item=target,
            )
            return (
                "contains 使用唯一真子串选择成功",
                [
                    f"输入文本: {fragment!r}",
                    f"选中项  : {target!r}",
                    f"策略    : {observation.strategy}",
                ],
            )

        results.append(run_case("包含匹配", contains_case))

        def regex_case() -> tuple[str, list[str]]:
            target = option(4)
            pattern = f"^{re.escape(target)}$"
            observation = observe_select(
                element,
                f"element.select({pattern!r}, mode='regex', delay_after=0)",
                lambda: element.select(pattern, mode="regex", delay_after=0),
                expected_item=target,
            )
            return (
                "regex 使用完整锚定表达式选择成功",
                [
                    f"正则    : {pattern!r}",
                    f"选中项  : {target!r}",
                    f"策略    : {observation.strategy}",
                ],
            )

        results.append(run_case("正则匹配", regex_case))

        def mode_normalization_case() -> tuple[str, list[str]]:
            target = option(5)
            observe_select(
                element,
                "mode=' ExAcT '",
                lambda: element.select(target, mode=" ExAcT ", delay_after=0),
                expected_item=target,
            )
            return "mode 会去除首尾空白并忽略大小写"

        results.append(run_case("模式规范化", mode_normalization_case))

        def item_whitespace_case() -> tuple[str, list[str]]:
            target = option(6)
            observe_select(
                element,
                "item 含首尾空白",
                lambda: element.select(f"  {target}  ", mode="exact", delay_after=0),
                expected_item=target,
            )
            return "item 的首尾空白被去除后完成精确匹配"

        results.append(run_case("选项文本规范化", item_whitespace_case))

        def text_conversion_case() -> tuple[str, list[str]]:
            target = option(7)
            value = ItemText(target)
            observe_select(
                element,
                "item 为自定义可字符串化对象",
                lambda: element.select(value, mode="exact", delay_after=0),  # type: ignore[arg-type]
                expected_item=target,
            )
            return "非字符串 item 按当前实现调用 str() 后选择成功", [f"转换结果: {str(value)!r}"]

        results.append(run_case("文本转换", text_conversion_case))

        def delay_after_case() -> tuple[str, list[str]]:
            fast_target = option(8)
            fast = observe_select(
                element,
                "delay_after=None",
                lambda: element.select(fast_target, mode="exact", delay_after=None),
                expected_item=fast_target,
            )
            delayed_target = option(9)
            delayed = observe_select(
                element,
                "delay_after=0.2",
                lambda: element.select(delayed_target, mode="exact", delay_after=0.2),
                expected_item=delayed_target,
            )
            if delayed.elapsed_ms < fast.elapsed_ms + 160:
                raise AssertionError(
                    f"动作后延时差异不足：None={fast.elapsed_ms:.1f}ms，0.2={delayed.elapsed_ms:.1f}ms"
                )
            return (
                "delay_after=None 不等待，0.2 秒等待生效；默认 1 秒亦已覆盖",
                [f"None    : {fast.elapsed_ms:.1f}ms", f"0.2s    : {delayed.elapsed_ms:.1f}ms"],
            )

        results.append(run_case("动作后延时", delay_after_case))

        def empty_item_case() -> str:
            before = selected_items(element)
            expect_exception(
                "item=''",
                InvalidParamsError,
                lambda: element.select("", mode="exact", delay_after=0),
            )
            expect_exception(
                "item='   '",
                InvalidParamsError,
                lambda: element.select("   ", mode="exact", delay_after=0),
            )
            if selected_items(element) != before:
                raise AssertionError("空 item 被拒绝后选中状态发生变化")
            return "空字符串和纯空白 item 均被 InvalidParamsError 正确拒绝"

        results.append(run_case("空选项文本", empty_item_case))

        def invalid_mode_case() -> str:
            before = selected_items(element)
            expect_exception(
                "mode='prefix'",
                InvalidParamsError,
                lambda: element.select(option(10), mode="prefix", delay_after=0),
            )
            expect_exception(
                "mode=None",
                InvalidParamsError,
                lambda: element.select(option(10), mode=None, delay_after=0),  # type: ignore[arg-type]
            )
            if selected_items(element) != before:
                raise AssertionError("非法 mode 被拒绝后选中状态发生变化")
            return "未知模式和 None 模式均被 InvalidParamsError 正确拒绝"

        results.append(run_case("非法匹配模式", invalid_mode_case))

        def invalid_regex_case() -> tuple[str, list[str]]:
            before = selected_items(element)
            error = expect_action_error(
                "无效正则 '['",
                "invalid_match_regex",
                lambda: element.select("[", mode="regex", delay_after=0),
            )
            if selected_items(element) != before:
                raise AssertionError("无效正则被拒绝后选中状态发生变化")
            return (
                "无法编译的正则表达式被 ActionError 正确拒绝",
                [f"trace_info: {error.trace_info}"],
            )

        results.append(run_case("非法正则", invalid_regex_case))

        def not_found_case() -> tuple[str, list[str]]:
            before = selected_items(element)
            missing = "__UIAUTOMA_SELECT_NOT_FOUND__"
            error = expect_action_error(
                "不存在选项",
                "select_item_not_found",
                lambda: element.select(missing, mode="exact", delay_after=0),
            )
            if selected_items(element) != before:
                raise AssertionError("未命中选择后选中状态发生变化")
            return "未命中选项被 ActionError 正确报告", [f"trace_info: {error.trace_info}"]

        results.append(run_case("选项未找到", not_found_case))

        def ambiguous_case() -> tuple[str, list[str]]:
            before = selected_items(element)
            error = expect_action_error(
                "regex='.*'",
                "ambiguous_select_item",
                lambda: element.select(".*", mode="regex", delay_after=0),
            )
            if selected_items(element) != before:
                raise AssertionError("多项命中被拒绝后选中状态发生变化")
            return (
                "匹配全部候选项的正则被识别为多项命中",
                [f"候选项数: {len(candidates)}", f"trace_info: {error.trace_info}"],
            )

        results.append(run_case("多项命中", ambiguous_case))

        def invalid_delay_case() -> tuple[str, list[str]]:
            negative_target = option(10)
            expect_exception(
                "delay_after=-1",
                InvalidParamsError,
                lambda: element.select(negative_target, mode="exact", delay_after=-1),
            )
            assert_selected(element, negative_target, "delay_after=-1")
            if element.last_result is None or not element.last_result.ok:
                raise AssertionError("负延时异常前没有保存成功的 last_result")

            text_target = option(11)
            expect_exception(
                'delay_after="bad"',
                InvalidParamsError,
                lambda: element.select(
                    text_target,
                    mode="exact",
                    delay_after="bad",  # type: ignore[arg-type]
                ),
            )
            assert_selected(element, text_target, 'delay_after="bad"')
            if element.last_result is None or not element.last_result.ok:
                raise AssertionError("非数字延时异常前没有保存成功的 last_result")
            return (
                "负数和非数字延时均在选择完成后被 InvalidParamsError 拒绝",
                [f"负延时选中: {negative_target!r}", f"文本延时选中: {text_target!r}"],
            )

        results.append(run_case("非法延时", invalid_delay_case))

    except Exception as exc:
        if not results or results[-1].passed:
            results.append(
                CaseResult(
                    "测试准备",
                    False,
                    "无法继续执行下拉选择用例",
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
                    element.select(original_selection, mode="exact", delay_after=0)
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
