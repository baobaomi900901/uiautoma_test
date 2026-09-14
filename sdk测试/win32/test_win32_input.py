r"""验证 ``uiautoma.win32.Win32Element.input()`` 的公开参数与真实输入行为。

API 参数（均可按位置或关键字传入）：
    text: str
        必填输入内容；实现会先调用 str(text)。
    simulative: bool = True
        True 使用键盘模拟；False 使用自动化输入。contains_hotkey=True 时强制键盘模式。
    append: bool = False
        False 输入前清空，True 在现有值后追加。
    contains_hotkey: bool = False
        是否把 text 解析为 Windows SendKeys 快捷键表达式。
    send_key_delay: int = 50
        键盘模拟时每个按键之间的等待毫秒数。
    focus_timeout: int = 1000
        点击或聚焦元素后到输入前的等待毫秒数。
    delay_after: float = 1
        输入完成后的等待秒数；None 或 0 表示不等待。
    click_before_input: bool = True
        输入前是否点击元素；False 时键盘模式只尝试自动化聚焦。
    anchor: object | None = None
        输入前点击锚点，支持九宫格、random、三元组和字典偏移。
    force_ime_ENG: bool = False
        输入前尝试切换英文键盘布局，输入后尽力恢复。

脚本参数：无。

前置条件：
    1. UIAutoma.exe 正在 dev 运行；
    2. 当前元素库为 D:\code\元素库\260902_win元素；
    3. Win32 靶场正在运行，且元素库中存在“win32靶场_表单控件_输入框_姓名”。

脚本会临时改写输入框，并在结束时恢复原值、鼠标和运行前的前台窗口。
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
from uiautoma import InvalidParamsError, win32
from uiautoma.win32 import Win32Element


LIBRARY_DIR = Path(r"D:\code\元素库\260902_win元素")
TARGET_ELEMENT = "win32靶场_表单控件_输入框_姓名"
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
class InputObservation:
    elapsed_ms: float
    strategy: str
    value: str
    point: tuple[int, int] | None
    log_lines: list[str]


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
    center_x = (left + right) // 2
    center_y = (top + bottom) // 2
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
    rect: tuple[int, int, int, int],
    point_rule: str = "optional",
    expected_point: tuple[int, int] | None = None,
    minimum_elapsed_ms: float = 0.0,
) -> InputObservation:
    started = time.perf_counter()
    returned = invoke()
    elapsed_ms = (time.perf_counter() - started) * 1000.0
    if returned is not None:
        raise AssertionError(f"{call_text} 应返回 None，实际为 {returned!r}")

    result = element.last_result
    if result is None or not result.ok:
        raise AssertionError(f"{call_text} 未留下成功的 last_result")
    strategy = str(result.strategy or "").strip()
    if not strategy:
        raise AssertionError(f"{call_text} 的 last_result.strategy 为空")
    actual_value = element.get_value()
    if actual_value != expected_value:
        raise AssertionError(
            f"{call_text} 输入结果不一致：期望 {expected_value!r}，实际 {actual_value!r}"
        )

    point = point_from_result(result.clicked_point)
    if point_rule == "required":
        if point is None:
            raise AssertionError(f"{call_text} 未返回输入前点击点")
        if not point_inside(point, rect):
            raise AssertionError(f"{call_text} 点击点 {point} 不在元素边界 {rect} 内")
    elif point_rule == "absent" and point is not None:
        raise AssertionError(f"{call_text} 禁用输入前点击后仍返回点击点 {point}")
    if expected_point is not None:
        if point is None or not point_near(point, expected_point):
            raise AssertionError(f"{call_text} 点击点应接近 {expected_point}，实际为 {point}")
    if elapsed_ms < minimum_elapsed_ms:
        raise AssertionError(
            f"{call_text} 等待时间不足：{elapsed_ms:.1f}ms < {minimum_elapsed_ms:.1f}ms"
        )
    return InputObservation(elapsed_ms, strategy, actual_value, point, list(result.log_lines))


def expect_exception(
    call_text: str,
    expected_type: type[BaseException],
    invoke: Callable[[], Any],
) -> None:
    try:
        invoke()
    except expected_type:
        return
    except Exception as exc:
        raise AssertionError(
            f"{call_text} 应抛出 {expected_type.__name__}，实际为 {type(exc).__name__}: {exc}"
        ) from exc
    raise AssertionError(f"{call_text} 未抛出 {expected_type.__name__}")


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
    progress_width = 7
    status_width = 6
    name_width = max(18, max(display_width(item.name) for item in results) + 2)
    detail_width = max(70, max(display_width(item.detail) for item in results) + 2)
    elapsed_width = 9

    print()
    print(
        f"{pad('进度', progress_width)}  {pad('状态', status_width)}  "
        f"{pad('测试项', name_width)}  {pad('测试结果', detail_width)}  {'耗时':>{elapsed_width}}"
    )
    print(
        f"{'─' * progress_width}  {'─' * status_width}  "
        f"{'─' * name_width}  {'─' * detail_width}  {'─' * elapsed_width}"
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
    print("  API     : uiautoma.win32.Win32Element.input")
    print(f"  元素库  : {LIBRARY_DIR}")
    print(f"  输入元素: {TARGET_ELEMENT}")
    print(f"  测试窗口: {TARGET_TITLE}")
    print(f"  目标进程: {TARGET_PROCESS}")
    print("  数据恢复: 测试结束后恢复输入框运行前的原值")
    print("  安全范围: 快捷键只使用 Ctrl+A，不点击保存按钮")

    results: list[CaseResult] = []
    package: Any = None
    element: Win32Element | None = None
    rect: tuple[int, int, int, int] | None = None
    original_value: str | None = None
    original_mouse: tuple[int, int] | None = None
    original_foreground = 0

    def contract() -> str:
        signature = inspect.signature(Win32Element.input)
        parameters = list(signature.parameters.values())
        expected_names = [
            "self",
            "text",
            "simulative",
            "append",
            "contains_hotkey",
            "send_key_delay",
            "focus_timeout",
            "delay_after",
            "click_before_input",
            "anchor",
            "force_ime_ENG",
        ]
        expected_defaults = [
            inspect.Parameter.empty,
            inspect.Parameter.empty,
            True,
            False,
            False,
            50,
            1000,
            1,
            True,
            None,
            False,
        ]
        if [item.name for item in parameters] != expected_names:
            raise AssertionError(f"参数顺序变化：{signature}")
        if [item.default for item in parameters] != expected_defaults:
            raise AssertionError(f"参数默认值变化：{signature}")
        if any(item.kind is not inspect.Parameter.POSITIONAL_OR_KEYWORD for item in parameters):
            raise AssertionError(f"参数种类变化：{signature}")
        if str(signature.return_annotation) not in {"None", "<class 'NoneType'>"}:
            raise AssertionError(f"返回注解变化：{signature}")
        return "十个公开参数、默认值和位置/关键字调用规则符合合同"

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

        def acquire_element() -> tuple[str, list[str]]:
            nonlocal element, rect, original_value, original_mouse, original_foreground
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
                "已定位靶场输入框并记录原值，物理边界有效",
                [
                    f"边界    : {rect}",
                    f"原值    : {preview(original_value)}",
                    f"原鼠标  : {original_mouse}",
                ],
            )

        element_result = run_case("输入目标", acquire_element)
        results.append(element_result)
        if not element_result.passed:
            raise RuntimeError("输入目标准备失败")

        assert element is not None
        assert rect is not None

        def defaults() -> tuple[str, list[str]]:
            value = "UIAutoma_Default_01"
            observation = observe_input(
                element,
                f"element.input({value!r})",
                lambda: element.input(value),
                expected_value=value,
                rect=rect,
                point_rule="required",
                expected_point=anchor_point(rect, "middleCenter"),
                minimum_elapsed_ms=1800,
            )
            return (
                "九项默认值生效，键盘模式覆盖输入并完成默认等待",
                [
                    f"实际值  : {observation.value!r}",
                    f"策略    : {observation.strategy}",
                    f"点击点  : {observation.point}",
                ],
            )

        results.append(run_case("全部默认参数", defaults))

        def all_positional() -> tuple[str, list[str]]:
            value = "UIAutoma_All_02"
            observation = observe_input(
                element,
                "十个参数全部按位置传入",
                lambda: element.input(value, True, False, False, 0, 0, 0, True, "middleCenter", False),
                expected_value=value,
                rect=rect,
                point_rule="required",
                expected_point=anchor_point(rect, "middleCenter"),
            )
            return (
                "十个参数可按位置传入，输入值、返回值和点击点正确",
                [f"实际值  : {observation.value!r}", f"策略    : {observation.strategy}"],
            )

        results.append(run_case("全位置参数", all_positional))

        def input_modes() -> tuple[str, list[str]]:
            keyboard_value = "Keyboard_Mode_03"
            keyboard = observe_input(
                element,
                "element.input(..., simulative=True)",
                lambda: element.input(keyboard_value, True, False, False, 0, 0, 0, True),
                expected_value=keyboard_value,
                rect=rect,
                point_rule="required",
            )
            automation_value = "Automation_Mode_03"
            automation = observe_input(
                element,
                "element.input(..., simulative=False)",
                lambda: element.input(
                    automation_value,
                    False,
                    False,
                    False,
                    0,
                    0,
                    0,
                    False,
                ),
                expected_value=automation_value,
                rect=rect,
                point_rule="absent",
            )
            return (
                "键盘模拟和自动化覆盖输入均成功",
                [f"键盘策略: {keyboard.strategy}", f"自动化策略: {automation.strategy}"],
            )

        results.append(run_case("两种输入模式", input_modes))

        def append_modes() -> tuple[str, list[str]]:
            base = "Append_Base"
            observe_input(
                element,
                "准备追加基值",
                lambda: element.input(base, False, False, False, 0, 0, 0, False),
                expected_value=base,
                rect=rect,
                point_rule="absent",
            )
            keyboard_expected = base + "_K"
            observe_input(
                element,
                "键盘追加",
                lambda: element.input("_K", True, True, False, 0, 0, 0, True),
                expected_value=keyboard_expected,
                rect=rect,
                point_rule="required",
            )
            automation_expected = keyboard_expected + "_A"
            automation = observe_input(
                element,
                "自动化追加",
                lambda: element.input("_A", False, True, False, 0, 0, 0, False),
                expected_value=automation_expected,
                rect=rect,
                point_rule="absent",
            )
            return (
                "append=False 覆盖；键盘和自动化 append=True 均追加成功",
                [f"最终值  : {automation.value!r}", f"追加策略: {automation.strategy}"],
            )

        results.append(run_case("覆盖与追加", append_modes))

        def hotkey_case() -> tuple[str, list[str]]:
            observe_input(
                element,
                "准备快捷键原值",
                lambda: element.input("Before_Hotkey", False, False, False, 0, 0, 0, False),
                expected_value="Before_Hotkey",
                rect=rect,
                point_rule="absent",
            )
            expected = "Hotkey_Result_04"
            observation = observe_input(
                element,
                "contains_hotkey=True",
                lambda: element.input(
                    "^a" + expected,
                    True,
                    True,
                    True,
                    0,
                    0,
                    0,
                    True,
                ),
                expected_value=expected,
                rect=rect,
                point_rule="required",
            )
            return (
                "Ctrl+A 快捷键表达式被解析，随后文本正确替换原值",
                [f"实际值  : {observation.value!r}", f"策略    : {observation.strategy}"],
            )

        results.append(run_case("快捷键输入", hotkey_case))

        def key_delay_case() -> tuple[str, list[str]]:
            fast = observe_input(
                element,
                "send_key_delay=0",
                lambda: element.input("Delay000", True, False, False, 0, 0, 0, True),
                expected_value="Delay000",
                rect=rect,
                point_rule="required",
            )
            delayed = observe_input(
                element,
                "send_key_delay=30",
                lambda: element.input("Delay030", True, False, False, 30, 0, 0, True),
                expected_value="Delay030",
                rect=rect,
                point_rule="required",
            )
            if delayed.elapsed_ms < fast.elapsed_ms + 100:
                raise AssertionError(
                    f"逐键延时差异不足：0ms={fast.elapsed_ms:.1f}ms，30ms={delayed.elapsed_ms:.1f}ms"
                )
            return (
                "send_key_delay=30 相比 0 产生可测逐键等待",
                [f"0ms     : {fast.elapsed_ms:.1f}ms", f"30ms    : {delayed.elapsed_ms:.1f}ms"],
            )

        results.append(run_case("逐键延时", key_delay_case))

        def focus_delay_case() -> tuple[str, list[str]]:
            fast = observe_input(
                element,
                "focus_timeout=0",
                lambda: element.input("Focus000", True, False, False, 0, 0, 0, True),
                expected_value="Focus000",
                rect=rect,
                point_rule="required",
            )
            delayed = observe_input(
                element,
                "focus_timeout=200",
                lambda: element.input("Focus200", True, False, False, 0, 200, 0, True),
                expected_value="Focus200",
                rect=rect,
                point_rule="required",
            )
            if delayed.elapsed_ms < fast.elapsed_ms + 150:
                raise AssertionError(
                    f"聚焦等待差异不足：0ms={fast.elapsed_ms:.1f}ms，200ms={delayed.elapsed_ms:.1f}ms"
                )
            return (
                "focus_timeout=200 相比 0 产生可测输入前等待",
                [f"0ms     : {fast.elapsed_ms:.1f}ms", f"200ms   : {delayed.elapsed_ms:.1f}ms"],
            )

        results.append(run_case("聚焦等待", focus_delay_case))

        def click_before_case() -> str:
            observe_input(
                element,
                "click_before_input=True",
                lambda: element.input("Click_True", True, False, False, 0, 0, 0, True),
                expected_value="Click_True",
                rect=rect,
                point_rule="required",
            )
            observe_input(
                element,
                "click_before_input=False",
                lambda: element.input("Click_False", True, False, False, 0, 0, 0, False),
                expected_value="Click_False",
                rect=rect,
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
                observe_input(
                    element,
                    f'element.input(..., anchor="{anchor}")',
                    lambda value=value, anchor=anchor: element.input(
                        value, True, False, False, 0, 0, 0, True, anchor
                    ),
                    expected_value=value,
                    rect=rect,
                    point_rule="required",
                    expected_point=anchor_point(rect, anchor),
                )
            return "九宫格锚点全部命中对应物理位置，输入值均正确"

        results.append(run_case("九宫格锚点", fixed_anchor_case))

        def random_anchor_case() -> tuple[str, list[str]]:
            observation = observe_input(
                element,
                'element.input(..., anchor="random")',
                lambda: element.input("Anchor_Random", True, False, False, 0, 0, 0, True, "random"),
                expected_value="Anchor_Random",
                rect=rect,
                point_rule="required",
            )
            return "random 点击点位于元素边界内且输入成功", [f"随机点  : {observation.point}"]

        results.append(run_case("随机锚点", random_anchor_case))

        def tuple_anchor_case() -> tuple[str, list[str]]:
            observation = observe_input(
                element,
                "三元组锚点",
                lambda: element.input(
                    "Anchor_Tuple",
                    True,
                    False,
                    False,
                    0,
                    0,
                    0,
                    True,
                    ("middleCenter", 10, 4),
                ),
                expected_value="Anchor_Tuple",
                rect=rect,
                point_rule="required",
                expected_point=anchor_point(rect, "middleCenter", 10, 4),
            )
            return "三元组锚点及 X/Y 偏移量生效", [f"点击点  : {observation.point}"]

        results.append(run_case("三元组锚点", tuple_anchor_case))

        def mapping_anchor_case() -> tuple[str, list[str]]:
            anchor = {"anchor": "middleCenter", "offset_x": -10, "offset_y": -4}
            observation = observe_input(
                element,
                "字典锚点",
                lambda: element.input(
                    "Anchor_Mapping", True, False, False, 0, 0, 0, True, anchor
                ),
                expected_value="Anchor_Mapping",
                rect=rect,
                point_rule="required",
                expected_point=anchor_point(rect, "middleCenter", -10, -4),
            )
            return "字典锚点及 offset_x/offset_y 生效", [f"点击点  : {observation.point}"]

        results.append(run_case("字典锚点", mapping_anchor_case))

        def force_ime_case() -> tuple[str, list[str]]:
            value = "IME_ENG_123"
            observation = observe_input(
                element,
                "force_ime_ENG=True",
                lambda: element.input(value, True, False, False, 0, 0, 0, True, None, True),
                expected_value=value,
                rect=rect,
                point_rule="required",
            )
            switch_logged = any("英文输入布局" in line for line in observation.log_lines)
            restore_logged = any(
                "已恢复输入布局" in line or "输入布局恢复失败" in line
                for line in observation.log_lines
            )
            if not switch_logged or not restore_logged:
                raise AssertionError(f"输入布局切换或恢复诊断缺失：{observation.log_lines!r}")
            return (
                "英文输入布局切换与恢复均留下诊断，ASCII 输入正确",
                [line for line in observation.log_lines if "输入布局" in line],
            )

        results.append(run_case("英文输入布局", force_ime_case))

        def text_conversion_case() -> tuple[str, list[str]]:
            value = 20260906
            observation = observe_input(
                element,
                "element.input(20260906, simulative=False, ...)",
                lambda: element.input(value, False, False, False, 0, 0, 0, False),  # type: ignore[arg-type]
                expected_value=str(value),
                rect=rect,
                point_rule="absent",
            )
            return "非字符串 text 按当前实现转换为字符串后输入", [f"实际值  : {observation.value!r}"]

        results.append(run_case("文本转换", text_conversion_case))

        def delay_after_case() -> str:
            observe_input(
                element,
                "delay_after=None",
                lambda: element.input("After_None", False, False, False, 0, 0, None, False),
                expected_value="After_None",
                rect=rect,
                point_rule="absent",
            )
            observe_input(
                element,
                "delay_after=0.2",
                lambda: element.input("After_200", False, False, False, 0, 0, 0.2, False),
                expected_value="After_200",
                rect=rect,
                point_rule="absent",
                minimum_elapsed_ms=160,
            )
            return "delay_after=None 不等待，0.2 秒等待生效；默认 1 秒亦已覆盖"

        results.append(run_case("动作后延时", delay_after_case))

        def millisecond_boundaries() -> str:
            observe_input(
                element,
                "负数毫秒参数",
                lambda: element.input("Negative_MS", True, False, False, -10, -20, 0, True),
                expected_value="Negative_MS",
                rect=rect,
                point_rule="required",
            )
            expect_exception(
                'send_key_delay="bad"',
                ValueError,
                lambda: element.input("Bad_Key_Delay", send_key_delay="bad"),  # type: ignore[arg-type]
            )
            expect_exception(
                'focus_timeout="bad"',
                ValueError,
                lambda: element.input("Bad_Focus", focus_timeout="bad"),  # type: ignore[arg-type]
            )
            return "负数毫秒值按 0 处理；非整数值在 SDK 转换阶段抛出 ValueError"

        results.append(run_case("毫秒参数边界", millisecond_boundaries))

        def invalid_anchor_case() -> str:
            expect_exception(
                'anchor="center"',
                InvalidParamsError,
                lambda: element.input("Bad_Anchor", anchor="center", delay_after=0),
            )
            expect_exception(
                "anchor=123",
                InvalidParamsError,
                lambda: element.input("Bad_Anchor", anchor=123, delay_after=0),
            )
            return "未知锚点名称和不支持的锚点类型均被 InvalidParamsError 拒绝"

        results.append(run_case("非法锚点", invalid_anchor_case))

        def invalid_delay_case() -> str:
            expect_exception(
                "delay_after=-1",
                InvalidParamsError,
                lambda: element.input(
                    "Invalid_Delay_Negative", False, False, False, 0, 0, -1, False
                ),
            )
            if element.get_value() != "Invalid_Delay_Negative":
                raise AssertionError("负延时异常前的输入动作没有完成")
            expect_exception(
                'delay_after="bad"',
                InvalidParamsError,
                lambda: element.input(
                    "Invalid_Delay_Text", False, False, False, 0, 0, "bad", False
                ),  # type: ignore[arg-type]
            )
            if element.get_value() != "Invalid_Delay_Text":
                raise AssertionError("非数字延时异常前的输入动作没有完成")
            return "负数和非数字延时均在输入完成后被 InvalidParamsError 拒绝"

        results.append(run_case("非法延时", invalid_delay_case))

    except Exception as exc:
        if not results or results[-1].passed:
            results.append(
                CaseResult("测试准备", False, "无法继续执行输入用例", 0.0, [f"原因    : {exc}"])
            )
    finally:
        def cleanup() -> tuple[str, list[str]]:
            errors: list[str] = []
            restored_value = False
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
                "输入框原值、鼠标和原前台窗口已恢复，Package 已关闭",
                [f"恢复值  : {preview(original_value or '')}" if restored_value else "未产生待恢复输入值"],
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
    print("  鼠标位置: 已恢复")
    print("  Package : 已关闭")
    print("  靶场程序: 保持运行")
    print("  退出码  : 0")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
