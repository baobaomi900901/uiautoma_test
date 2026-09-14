r"""验证 ``uiautoma.win32.Win32Element.dblclick()`` 的公开参数与真实双击行为。

API 参数（均可按位置或关键字传入）：
    simulative: bool = True
        True 使用模拟鼠标双击；False 在当前 Runtime 中回退到可诊断的坐标双击。
    delay_after: float = 1
        双击完成后的等待秒数；None 或 0 表示不等待，不能为负数。
    move_mouse: bool | None = None
        是否把光标移动到双击点；None 使用人工轨迹配置，默认等效为 True。
    anchor: object | None = None
        元素内双击锚点。支持九宫格名称、random、三元组和包含偏移量的字典。

公开别名：``Win32Element.double_click()``，参数与返回值完全相同。
脚本参数：无。

前置条件：
    1. UIAutoma.exe 正在 dev 运行；
    2. 当前元素库为 D:\code\元素库\260902_win元素；
    3. Win32 靶场正在运行，且元素库中存在“win32靶场_表单控件_输入框_姓名”。

测试只双击输入框，不输入或删除内容。结束时恢复鼠标和运行脚本前的前台窗口。
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
class ActionObservation:
    strategy: str
    point: tuple[int, int]
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


def observe_action(
    element: Win32Element,
    call_text: str,
    invoke: Callable[[], Any],
    *,
    rect: tuple[int, int, int, int],
    expected_point: tuple[int, int] | None = None,
    minimum_elapsed_ms: float = 0.0,
) -> ActionObservation:
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
    point = point_from_result(result.clicked_point)
    if point is None:
        raise AssertionError(f"{call_text} 未返回 clicked_point")
    if not point_inside(point, rect):
        raise AssertionError(f"{call_text} 双击点 {point} 不在元素边界 {rect} 内")
    if expected_point is not None and not point_near(point, expected_point):
        raise AssertionError(f"{call_text} 双击点应接近 {expected_point}，实际为 {point}")
    if elapsed_ms < minimum_elapsed_ms:
        raise AssertionError(
            f"{call_text} 等待时间不足：{elapsed_ms:.1f}ms < {minimum_elapsed_ms:.1f}ms"
        )
    return ActionObservation(strategy, point, list(result.log_lines))


def expect_invalid(call_text: str, invoke: Callable[[], Any]) -> None:
    try:
        invoke()
    except InvalidParamsError:
        return
    except Exception as exc:
        raise AssertionError(
            f"{call_text} 应抛出 InvalidParamsError，实际为 {type(exc).__name__}: {exc}"
        ) from exc
    raise AssertionError(f"{call_text} 未抛出 InvalidParamsError")


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
    detail_width = max(66, max(display_width(item.detail) for item in results) + 2)
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
    print("  API     : uiautoma.win32.Win32Element.dblclick")
    print("  别名    : uiautoma.win32.Win32Element.double_click")
    print(f"  元素库  : {LIBRARY_DIR}")
    print(f"  双击元素: {TARGET_ELEMENT}")
    print(f"  测试窗口: {TARGET_TITLE}")
    print(f"  目标进程: {TARGET_PROCESS}")
    print("  安全范围: 不输入或删除内容；固定使用左键双击")

    results: list[CaseResult] = []
    package: Any = None
    element: Win32Element | None = None
    rect: tuple[int, int, int, int] | None = None
    original_mouse: tuple[int, int] | None = None
    original_foreground = 0

    def contract() -> str:
        expected_names = ["self", "simulative", "delay_after", "move_mouse", "anchor"]
        expected_defaults = [inspect.Parameter.empty, True, 1, None, None]
        for method_name in ("dblclick", "double_click"):
            signature = inspect.signature(getattr(Win32Element, method_name))
            parameters = list(signature.parameters.values())
            if [item.name for item in parameters] != expected_names:
                raise AssertionError(f"{method_name} 参数顺序变化：{signature}")
            if [item.default for item in parameters] != expected_defaults:
                raise AssertionError(f"{method_name} 参数默认值变化：{signature}")
            if any(item.kind is not inspect.Parameter.POSITIONAL_OR_KEYWORD for item in parameters):
                raise AssertionError(f"{method_name} 参数种类变化：{signature}")
        return "四个公开参数与 double_click 别名的签名、默认值均符合合同"

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
            nonlocal element, rect, original_mouse, original_foreground
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
            original_mouse = current_cursor()
            original_foreground = current_foreground()
            win32.manual_motion_off()
            return (
                "已定位靶场输入框并关闭人工轨迹，物理边界有效",
                [f"边界    : {rect}", f"原鼠标  : {original_mouse}"],
            )

        element_result = run_case("双击目标", acquire_element)
        results.append(element_result)
        if not element_result.passed:
            raise RuntimeError("双击目标准备失败")

        assert element is not None
        assert rect is not None

        def defaults() -> tuple[str, list[str]]:
            observation = observe_action(
                element,
                "element.dblclick()",
                lambda: element.dblclick(),
                rect=rect,
                expected_point=anchor_point(rect, "middleCenter"),
                minimum_elapsed_ms=800,
            )
            return (
                "四项默认值生效，返回 None，默认等待约 1 秒",
                [
                    "调用    : element.dblclick()",
                    f"策略    : {observation.strategy}",
                    f"双击点  : {observation.point}",
                ],
            )

        results.append(run_case("全部默认参数", defaults))

        def all_positional() -> tuple[str, list[str]]:
            observation = observe_action(
                element,
                'element.dblclick(False, 0, False, "middleCenter")',
                lambda: element.dblclick(False, 0, False, "middleCenter"),
                rect=rect,
                expected_point=anchor_point(rect, "middleCenter"),
            )
            if not any("改用鼠标动作" in line for line in observation.log_lines):
                raise AssertionError("simulative=False 未返回鼠标回退诊断")
            return (
                "四个参数可按位置传入，控件优先模式以鼠标动作成功回退",
                [
                    '调用    : element.dblclick(False, 0, False, "middleCenter")',
                    f"策略    : {observation.strategy}（鼠标回退）",
                ],
            )

        results.append(run_case("全位置参数", all_positional))

        def action_modes() -> tuple[str, list[str]]:
            simulated = observe_action(
                element,
                "element.dblclick(simulative=True, ...)",
                lambda: element.dblclick(True, 0, False, "middleCenter"),
                rect=rect,
            )
            fallback = observe_action(
                element,
                "element.dblclick(simulative=False, ...)",
                lambda: element.dblclick(False, 0, False, "middleCenter"),
                rect=rect,
            )
            if not any("改用鼠标动作" in line for line in fallback.log_lines):
                raise AssertionError("simulative=False 未留下可诊断的鼠标回退日志")
            return (
                "simulative=True 与 False 均成功，False 的回退可诊断",
                [f"模拟策略: {simulated.strategy}", f"回退策略: {fallback.strategy}"],
            )

        results.append(run_case("动作模式", action_modes))

        def mouse_modes() -> str:
            for move_mouse in (False, True):
                observe_action(
                    element,
                    f"element.dblclick(move_mouse={move_mouse}, ...)",
                    lambda move_mouse=move_mouse: element.dblclick(
                        True, 0, move_mouse, "middleCenter"
                    ),
                    rect=rect,
                    expected_point=anchor_point(rect, "middleCenter"),
                )
            return "move_mouse=False 与 True 均成功且双击点位于目标内"

        results.append(run_case("鼠标移动开关", mouse_modes))

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
            for anchor in fixed_anchors:
                observe_action(
                    element,
                    f'element.dblclick(anchor="{anchor}", ...)',
                    lambda anchor=anchor: element.dblclick(True, 0, False, anchor),
                    rect=rect,
                    expected_point=anchor_point(rect, anchor),
                )
            return "九宫格锚点全部命中对应位置，clicked_point 与物理边界一致"

        results.append(run_case("九宫格锚点", fixed_anchor_case))

        def random_anchor_case() -> tuple[str, list[str]]:
            observation = observe_action(
                element,
                'element.dblclick(anchor="random", ...)',
                lambda: element.dblclick(True, 0, False, "random"),
                rect=rect,
            )
            return "random 生成的双击点位于元素边界内", [f"随机点  : {observation.point}"]

        results.append(run_case("随机锚点", random_anchor_case))

        def tuple_anchor_case() -> tuple[str, list[str]]:
            expected = anchor_point(rect, "middleCenter", 10, 4)
            observation = observe_action(
                element,
                'element.dblclick(anchor=("middleCenter", 10, 4), ...)',
                lambda: element.dblclick(True, 0, False, ("middleCenter", 10, 4)),
                rect=rect,
                expected_point=expected,
            )
            return "三元组锚点及 X/Y 偏移量生效", [f"双击点  : {observation.point}"]

        results.append(run_case("三元组锚点", tuple_anchor_case))

        def mapping_anchor_case() -> tuple[str, list[str]]:
            expected = anchor_point(rect, "middleCenter", -10, -4)
            anchor = {"anchor": "middleCenter", "offset_x": -10, "offset_y": -4}
            observation = observe_action(
                element,
                f"element.dblclick(anchor={anchor!r}, ...)",
                lambda: element.dblclick(True, 0, False, anchor),
                rect=rect,
                expected_point=expected,
            )
            return "字典锚点及 offset_x/offset_y 生效", [f"双击点  : {observation.point}"]

        results.append(run_case("字典锚点", mapping_anchor_case))

        def delay_case() -> str:
            observe_action(
                element,
                "element.dblclick(delay_after=None, ...)",
                lambda: element.dblclick(True, None, False, "middleCenter"),
                rect=rect,
            )
            observe_action(
                element,
                "element.dblclick(delay_after=0, ...)",
                lambda: element.dblclick(True, 0, False, "middleCenter"),
                rect=rect,
            )
            observe_action(
                element,
                "element.dblclick(delay_after=0.2, ...)",
                lambda: element.dblclick(True, 0.2, False, "middleCenter"),
                rect=rect,
                minimum_elapsed_ms=160,
            )
            return "delay_after=None、0 和 0.2 秒均生效；默认 1 秒亦已覆盖"

        results.append(run_case("动作后延时", delay_case))

        def alias_case() -> tuple[str, list[str]]:
            observation = observe_action(
                element,
                'element.double_click(True, 0, False, "middleCenter")',
                lambda: element.double_click(True, 0, False, "middleCenter"),
                rect=rect,
                expected_point=anchor_point(rect, "middleCenter"),
            )
            return (
                "double_click() 别名委托成功并更新 last_result",
                [f"策略    : {observation.strategy}", f"双击点  : {observation.point}"],
            )

        results.append(run_case("公开别名", alias_case))

        def invalid_anchor_case() -> str:
            expect_invalid(
                'element.dblclick(anchor="center", ...)',
                lambda: element.dblclick(anchor="center", delay_after=0),
            )
            expect_invalid(
                "element.dblclick(anchor=123, ...)",
                lambda: element.dblclick(anchor=123, delay_after=0),
            )
            return "未知锚点名称和不支持的锚点类型均被正确拒绝"

        results.append(run_case("非法锚点", invalid_anchor_case))

        def invalid_delay_case() -> str:
            expect_invalid(
                "element.dblclick(delay_after=-1, ...)",
                lambda: element.dblclick(delay_after=-1, move_mouse=False),
            )
            if element.last_result is None or not element.last_result.ok:
                raise AssertionError("负延时异常前的双击结果未被保存在 last_result")
            expect_invalid(
                'element.dblclick(delay_after="bad", ...)',
                lambda: element.dblclick(delay_after="bad", move_mouse=False),
            )
            if element.last_result is None or not element.last_result.ok:
                raise AssertionError("非数字延时异常前的双击结果未被保存在 last_result")
            return "负数和非数字延时均在双击完成后被 InvalidParamsError 拒绝"

        results.append(run_case("非法延时", invalid_delay_case))

    except Exception as exc:
        if not results or results[-1].passed:
            results.append(
                CaseResult("测试准备", False, "无法继续执行双击用例", 0.0, [f"原因    : {exc}"])
            )
    finally:
        def cleanup() -> str:
            errors: list[str] = []
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
            return "人工轨迹已关闭，鼠标和原前台窗口已恢复，Package 已关闭"

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
    print("  人工轨迹: 已关闭")
    print("  鼠标位置: 已恢复")
    print("  Package : 已关闭")
    print("  靶场程序: 保持运行")
    print("  退出码  : 0")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
