r"""``uiautoma.win32.Win32Element.hover()`` 真实元素悬停测试。

API 参数（不是测试脚本参数）::

    Win32Element.hover(
        simulative: bool | None = None,
        delay_after: float = 1,
        anchor: object | None = None,
    ) -> None

参数规则：

* ``simulative``：``None`` 使用人工轨迹偏好且当前默认显示移动轨迹；``True``
  显示移动轨迹；``False`` 瞬间移动。
* ``delay_after``：默认 ``1`` 秒；``0`` 和 ``None`` 不等待；非负数字按秒等待；
  负数或非数字抛出 ``InvalidParamsError``。当前实现先执行悬停，再校验动作后延时。
* ``anchor``：``None`` 表示中心；支持九宫格锚点和 ``random``，也支持
  ``(anchor, offset_x, offset_y)`` 列表/元组及包含 ``anchor``、``offset_x``、
  ``offset_y`` 的字典。字典同时兼容 ``name``、``x``、``y`` 别名。
* 成功返回 ``None``，动作详情写入元素的 ``last_result``；非法锚点抛出
  ``InvalidParamsError``，Runtime 动作失败抛出 ``ActionError``。

测试脚本参数：无。

脚本借用 UIAutoma.exe 当前启用的 ``D:\code\元素库\260902_win元素``，使用其中的
``win32靶场_表单控件_输入框_姓名``。脚本逐一验证全部十种锚点、结构化偏移、人工轨迹和动作后延时，
同时使用原生 ``GetCursorPos`` 与 ``last_result.clicked_point`` 核对实际落点。结束时恢复
运行脚本前的鼠标位置、关闭借用的 Package，并保持 Win32 靶场运行。

导入本模块不会连接 Runtime 或移动鼠标。

运行方式::

    uv run .\win32\test_win32_hover.py
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
from ctypes import wintypes
from pathlib import Path
from typing import Any, Callable

import uiautoma
from uiautoma import win32
from uiautoma.win32 import Win32Element


__test__ = False

LIBRARY_DIR = Path(r"D:\code\元素库\260902_win元素")
ELEMENT_NAME = "win32靶场_表单控件_输入框_姓名"
START_POINT = (100, 100)
POSITION_TOLERANCE_PX = 3
SIMULATIVE_MIN_MS = 70.0
DEFAULT_DELAY_MIN_MS = 900.0
NO_DELAY_MAX_MS = 800.0
POSITIVE_DELAY_SECONDS = 0.2
POSITIVE_DELAY_MIN_MS = 160.0

_USER32 = ctypes.WinDLL("user32", use_last_error=True)
_USER32.SetCursorPos.argtypes = [ctypes.c_int, ctypes.c_int]
_USER32.SetCursorPos.restype = wintypes.BOOL
_USER32.GetCursorPos.argtypes = [ctypes.POINTER(wintypes.POINT)]
_USER32.GetCursorPos.restype = wintypes.BOOL

STATUS_LABELS = {"PASS": "通过", "FAIL": "失败", "BLOCKED": "阻塞"}
COLORS = {"PASS": "\x1b[32m", "FAIL": "\x1b[31m", "BLOCKED": "\x1b[33m"}
CYAN = "\x1b[36m"
RESET = "\x1b[0m"

PROGRESS_WIDTH = 7
STATUS_WIDTH = 6
CASE_WIDTH = 22
DETAIL_WIDTH = 82
DURATION_WIDTH = 8
TABLE_WIDTH = sum((PROGRESS_WIDTH, STATUS_WIDTH, CASE_WIDTH, DETAIL_WIDTH, DURATION_WIDTH, 8))

CASE_LABELS = {
    "api_contract": "API 合同",
    "element_setup": "靶场元素准备",
    "all_defaults": "全部默认参数",
    "simulative_false": "关闭人工轨迹",
    "simulative_true": "启用人工轨迹",
    "delay_none": "None 动作后延时",
    "delay_positive": "正数动作后延时",
    "anchor_top_left": "锚点 topLeft",
    "anchor_top_center": "锚点 topCenter",
    "anchor_top_right": "锚点 topRight",
    "anchor_middle_left": "锚点 middleLeft",
    "anchor_middle_center": "锚点 middleCenter",
    "anchor_middle_right": "锚点 middleRight",
    "anchor_bottom_left": "锚点 bottomLeft",
    "anchor_bottom_center": "锚点 bottomCenter",
    "anchor_bottom_right": "锚点 bottomRight",
    "anchor_random": "锚点 random",
    "anchor_tuple": "元组锚点偏移",
    "anchor_list": "列表锚点偏移",
    "anchor_mapping": "字典锚点偏移",
    "anchor_alias_mapping": "字典字段别名",
    "anchor_casefold": "锚点大小写兼容",
    "invalid_anchor": "非法锚点",
    "invalid_delay": "非法动作后延时",
    "resource_cleanup": "资源清理",
}

FIXED_ANCHORS = (
    ("anchor_top_left", "topLeft"),
    ("anchor_top_center", "topCenter"),
    ("anchor_top_right", "topRight"),
    ("anchor_middle_left", "middleLeft"),
    ("anchor_middle_center", "middleCenter"),
    ("anchor_middle_right", "middleRight"),
    ("anchor_bottom_left", "bottomLeft"),
    ("anchor_bottom_center", "bottomCenter"),
    ("anchor_bottom_right", "bottomRight"),
)

BLOCKING_EXCEPTION_NAMES = {
    "ConnectionError",
    "EOFError",
    "ElementNotFoundError",
    "HostBusyError",
    "HostUnavailableError",
    "PipeClosedError",
    "StalePackageError",
    "TimeoutError",
    "UnsupportedProtocolError",
}


def _result(case_id: str, status: str, detail: str, **extra: Any) -> dict[str, Any]:
    return {"case_id": case_id, "status": status, "detail": detail, **extra}


def _elapsed(started: float) -> float:
    return (time.perf_counter() - started) * 1000


def _error_result(
    case_id: str,
    detail: str,
    started: float,
    exc: BaseException,
    *,
    call: str = "",
) -> dict[str, Any]:
    status = "BLOCKED" if exc.__class__.__name__ in BLOCKING_EXCEPTION_NAMES else "FAIL"
    return _result(
        case_id,
        status,
        detail,
        elapsed_ms=_elapsed(started),
        call=call,
        exception=exc.__class__.__name__,
        message=str(exc),
    )


def _blocked(case_id: str, detail: str) -> dict[str, Any]:
    return _result(case_id, "BLOCKED", detail, elapsed_ms=0.0)


def _display_width(text: str) -> int:
    plain = re.sub(r"\x1b\[[0-9;]*m", "", str(text))
    return sum(
        0
        if unicodedata.combining(char)
        else (2 if unicodedata.east_asian_width(char) in {"W", "F"} else 1)
        for char in plain
    )


def _pad(text: str, width: int, *, right: bool = False) -> str:
    value = str(text)
    padding = " " * max(0, width - _display_width(value))
    return f"{padding}{value}" if right else f"{value}{padding}"


def _cursor_position() -> tuple[int, int]:
    point = wintypes.POINT()
    if not _USER32.GetCursorPos(ctypes.byref(point)):
        raise ctypes.WinError(ctypes.get_last_error())
    return int(point.x), int(point.y)


def _set_cursor(point: tuple[int, int]) -> None:
    if not _USER32.SetCursorPos(int(point[0]), int(point[1])):
        raise ctypes.WinError(ctypes.get_last_error())
    time.sleep(0.15)


def _near(actual: tuple[int, int] | None, expected: tuple[int, int]) -> bool:
    return actual is not None and (
        abs(actual[0] - expected[0]) <= POSITION_TOLERANCE_PX
        and abs(actual[1] - expected[1]) <= POSITION_TOLERANCE_PX
    )


def _inside_safe(point: tuple[int, int] | None, safe_rect: tuple[int, int, int, int]) -> bool:
    if point is None:
        return False
    left, top, right, bottom = safe_rect
    return left <= point[0] <= right and top <= point[1] <= bottom


def _safe_geometry(
    rect: tuple[int, int, int, int],
) -> tuple[dict[str, tuple[int, int]], tuple[int, int, int, int]]:
    x, y, width, height = rect
    left, right = x + 2, x + width - 2
    top, bottom = y + 2, y + height - 2
    if right <= left:
        left, right = x, x + width
    if bottom <= top:
        top, bottom = y, y + height
    center_x = (left + right) // 2
    center_y = (top + bottom) // 2
    points = {
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
    return points, (left, top, right, bottom)


def _action_point(element: Win32Element) -> tuple[int, int] | None:
    result = element.last_result
    if result is None or not isinstance(result.clicked_point, dict):
        return None
    try:
        return int(result.clicked_point["x"]), int(result.clicked_point["y"])
    except (KeyError, TypeError, ValueError):
        return None


def _action_move_mouse(element: Win32Element) -> bool | None:
    result = element.last_result
    if result is None or not isinstance(result.raw, dict):
        return None
    diagnostics = result.raw.get("mouse_diagnostics")
    if not isinstance(diagnostics, dict) or "move_mouse" not in diagnostics:
        return None
    return bool(diagnostics["move_mouse"])


def _check_contract() -> dict[str, Any]:
    started = time.perf_counter()
    try:
        signature = inspect.signature(Win32Element.hover)
        parameters = signature.parameters
        simulative = parameters.get("simulative")
        delay_after = parameters.get("delay_after")
        anchor = parameters.get("anchor")
        positional = inspect.Parameter.POSITIONAL_OR_KEYWORD
        passed = (
            tuple(parameters) == ("self", "simulative", "delay_after", "anchor")
            and simulative is not None
            and simulative.kind is positional
            and simulative.default is None
            and str(simulative.annotation) in {"bool | None", "bool|None"}
            and delay_after is not None
            and delay_after.kind is positional
            and delay_after.default == 1
            and str(delay_after.annotation) in {"float", "<class 'float'>"}
            and anchor is not None
            and anchor.kind is positional
            and anchor.default is None
            and str(anchor.annotation) in {"object | None", "object|None"}
            and str(signature.return_annotation) in {"None", "<class 'NoneType'>"}
        )
        return _result(
            "api_contract",
            "PASS" if passed else "FAIL",
            (
                "三个参数均为位置或关键字参数，默认值和返回 None 符合合同"
                if passed
                else "公开签名与当前合同不一致"
            ),
            elapsed_ms=_elapsed(started),
            signature=str(signature),
        )
    except Exception as exc:  # noqa: BLE001
        return _error_result("api_contract", "无法检查公开签名", started, exc)


def _prepare() -> tuple[
    dict[str, Any],
    Any | None,
    Win32Element | None,
    tuple[int, int, int, int] | None,
    tuple[int, int] | None,
]:
    started = time.perf_counter()
    package: Any | None = None
    original_cursor: tuple[int, int] | None = None
    try:
        original_cursor = _cursor_position()
        if not LIBRARY_DIR.is_dir():
            raise RuntimeError(f"元素库目录不存在：{LIBRARY_DIR}")
        package = uiautoma.current(required=False, refresh=True, timeout=5)
        ensure_form_tab(package)
        if package is None:
            raise RuntimeError("UIAutoma 当前未启用元素库；请点击“使用当前元素库”后重试")
        actual_library = Path(package.package_dir).resolve()
        if os.path.normcase(str(actual_library)) != os.path.normcase(str(LIBRARY_DIR.resolve())):
            raise RuntimeError(f"UIAutoma 当前元素库不是测试库：{actual_library}")
        element = win32.find(ELEMENT_NAME, timeout=10)
        rect = tuple(
            int(value)
            for value in element.get_bounding(to96dpi=False, relative_to="screen")
        )
        if len(rect) != 4 or rect[2] <= 4 or rect[3] <= 4:
            raise RuntimeError(f"元素边界无效：{rect}")
        return (
            _result(
                "element_setup",
                "PASS",
                f"当前元素库正确，已获取元素及物理像素边界 {rect}",
                elapsed_ms=_elapsed(started),
                rect=rect,
            ),
            package,
            element,
            rect,
            original_cursor,
        )
    except Exception as exc:  # noqa: BLE001
        return (
            _result(
                "element_setup",
                "BLOCKED",
                "无法准备当前元素库或靶场元素",
                elapsed_ms=_elapsed(started),
                exception=exc.__class__.__name__,
                message=str(exc),
            ),
            package,
            None,
            None,
            original_cursor,
        )


def _run_hover_case(
    case_id: str,
    element: Win32Element | None,
    call: Callable[[], None],
    call_text: str,
    success_detail: str,
    *,
    expected: tuple[int, int] | None = None,
    safe_rect: tuple[int, int, int, int] | None = None,
    expected_move_mouse: bool | None = None,
    min_elapsed_ms: float = 0.0,
    max_elapsed_ms: float | None = None,
    start_point: tuple[int, int] | None = None,
) -> dict[str, Any]:
    if element is None:
        return _blocked(case_id, "靶场元素未准备完成")
    started = time.perf_counter()
    try:
        if start_point is not None:
            _set_cursor(start_point)
        started = time.perf_counter()
        returned = call()
        elapsed_ms = _elapsed(started)
        actual = _cursor_position()
        reported = _action_point(element)
        move_mouse = _action_move_mouse(element)
        result_ok = element.last_result is not None and element.last_result.ok
        if expected is not None:
            coordinate_ok = _near(actual, expected) and _near(reported, expected)
        elif safe_rect is not None:
            coordinate_ok = _inside_safe(actual, safe_rect) and _inside_safe(reported, safe_rect)
        else:
            coordinate_ok = False
        motion_ok = expected_move_mouse is None or move_mouse is expected_move_mouse
        duration_ok = elapsed_ms >= min_elapsed_ms and (
            max_elapsed_ms is None or elapsed_ms <= max_elapsed_ms
        )
        passed = returned is None and result_ok and coordinate_ok and motion_ok and duration_ok
        return _result(
            case_id,
            "PASS" if passed else "FAIL",
            success_detail if passed else "返回值、落点、轨迹标记或耗时不符合预期",
            elapsed_ms=elapsed_ms,
            call=call_text,
            returned=returned,
            actual=actual,
            reported=reported,
            expected=expected,
            safe_rect=safe_rect,
            move_mouse=move_mouse,
            min_elapsed_ms=min_elapsed_ms,
            max_elapsed_ms=max_elapsed_ms,
            result_ok=result_ok,
        )
    except Exception as exc:  # noqa: BLE001
        return _error_result(case_id, "hover() 调用失败", started, exc, call=call_text)


def _check_invalid_anchor(element: Win32Element | None) -> dict[str, Any]:
    started = time.perf_counter()
    if element is None:
        return _blocked("invalid_anchor", "靶场元素未准备完成")
    outcomes: list[dict[str, Any]] = []
    for anchor in ("not-an-anchor", 42):
        try:
            _set_cursor(START_POINT)
            element.hover(False, 0, anchor)
            outcomes.append({"anchor": anchor, "exception": None, "cursor": _cursor_position()})
        except Exception as exc:  # noqa: BLE001
            outcomes.append(
                {
                    "anchor": anchor,
                    "exception": exc.__class__.__name__,
                    "message": str(exc),
                    "cursor": _cursor_position(),
                }
            )
    passed = all(
        item["exception"] == "InvalidParamsError" and _near(item["cursor"], START_POINT)
        for item in outcomes
    )
    return _result(
        "invalid_anchor",
        "PASS" if passed else "FAIL",
        (
            "非法名称和非法类型均在移动前被 InvalidParamsError 拒绝"
            if passed
            else "至少一个非法锚点未按预期拒绝或意外移动了鼠标"
        ),
        elapsed_ms=_elapsed(started),
        call='element.hover(False, 0, "not-an-anchor" / 42)',
        outcomes=outcomes,
    )


def _check_invalid_delay(
    element: Win32Element | None,
    center: tuple[int, int],
) -> dict[str, Any]:
    started = time.perf_counter()
    if element is None:
        return _blocked("invalid_delay", "靶场元素未准备完成")
    outcomes: list[dict[str, Any]] = []
    for delay in (-0.1, "bad"):
        try:
            _set_cursor(START_POINT)
            element.hover(False, delay, "middleCenter")  # type: ignore[arg-type]
            outcomes.append({"delay_after": delay, "exception": None, "cursor": _cursor_position()})
        except Exception as exc:  # noqa: BLE001
            outcomes.append(
                {
                    "delay_after": delay,
                    "exception": exc.__class__.__name__,
                    "message": str(exc),
                    "cursor": _cursor_position(),
                }
            )
    passed = all(
        item["exception"] == "InvalidParamsError" and _near(item["cursor"], center)
        for item in outcomes
    )
    return _result(
        "invalid_delay",
        "PASS" if passed else "FAIL",
        (
            "负数和非数字延时均在悬停完成后被 InvalidParamsError 拒绝"
            if passed
            else "至少一个非法延时的异常类型或动作顺序不符合预期"
        ),
        elapsed_ms=_elapsed(started),
        call='element.hover(False, -0.1 / "bad", "middleCenter")',
        outcomes=outcomes,
    )


def _cleanup(
    package: Any | None,
    original_cursor: tuple[int, int] | None,
) -> dict[str, Any]:
    started = time.perf_counter()
    errors: list[str] = []
    cursor_restored = original_cursor is None
    package_closed = package is None
    try:
        if original_cursor is not None:
            _set_cursor(original_cursor)
            cursor_restored = _near(_cursor_position(), original_cursor)
            if not cursor_restored:
                errors.append("鼠标位置未恢复")
    except Exception as exc:  # noqa: BLE001
        errors.append(f"恢复鼠标失败：{exc}")
    try:
        if package is not None:
            package.close()
            package_closed = True
    except Exception as exc:  # noqa: BLE001
        errors.append(f"关闭 Package 失败：{exc}")
    passed = cursor_restored and package_closed and not errors
    return _result(
        "resource_cleanup",
        "PASS" if passed else "FAIL",
        (
            "原始鼠标位置已恢复，借用的 Package 已关闭；靶场保持运行"
            if passed
            else "；".join(errors)
        ),
        elapsed_ms=_elapsed(started),
        cursor_restored=cursor_restored,
        package_closed=package_closed,
    )


def _print_header(
    rect: tuple[int, int, int, int] | None,
    safe_rect: tuple[int, int, int, int] | None,
    *,
    color: bool,
) -> None:
    title = f"{CYAN}UIAutoma Win32 API 测试{RESET}" if color else "UIAutoma Win32 API 测试"
    print(title)
    print()
    print("  API     : uiautoma.win32.Win32Element.hover")
    print(f"  元素库  : {LIBRARY_DIR}")
    print(f"  测试元素: {ELEMENT_NAME}")
    if rect is not None:
        print(f"  元素边界: {rect}")
    if safe_rect is not None:
        print(f"  安全边界: {safe_rect}")
    print("  锚点覆盖: 九宫格、random、元组、列表、字典和字段别名")
    print("  落点校验: Win32 GetCursorPos + ActionResult.clicked_point")
    print("  资源恢复: 测试结束后恢复鼠标并关闭借用的 Package")
    print()
    print(
        f"{_pad('进度', PROGRESS_WIDTH)}  {_pad('状态', STATUS_WIDTH)}  "
        f"{_pad('测试项', CASE_WIDTH)}  {_pad('测试结果', DETAIL_WIDTH)}  "
        f"{_pad('耗时', DURATION_WIDTH, right=True)}"
    )
    print(
        f"{'─' * PROGRESS_WIDTH}  {'─' * STATUS_WIDTH}  {'─' * CASE_WIDTH}  "
        f"{'─' * DETAIL_WIDTH}  {'─' * DURATION_WIDTH}"
    )


def _print_case(result: dict[str, Any], index: int, total: int, *, color: bool) -> None:
    status = str(result["status"])
    badge = _pad(f"[{STATUS_LABELS[status]}]", STATUS_WIDTH)
    if color:
        badge = f"{COLORS[status]}{badge}{RESET}"
    duration = f"{float(result.get('elapsed_ms', 0.0)):.1f}ms"
    print(
        f"{_pad(f'{index:02d}/{total:02d}', PROGRESS_WIDTH)}  {badge}  "
        f"{_pad(CASE_LABELS[result['case_id']], CASE_WIDTH)}  "
        f"{_pad(result['detail'], DETAIL_WIDTH)}  "
        f"{_pad(duration, DURATION_WIDTH, right=True)}"
    )
    if status == "PASS":
        return
    indent = " " * (PROGRESS_WIDTH + STATUS_WIDTH + CASE_WIDTH + 6)
    for key, label in (
        ("call", "调用"),
        ("expected", "预期"),
        ("actual", "鼠标"),
        ("reported", "动作报告"),
        ("move_mouse", "轨迹标记"),
        ("message", "原因"),
    ):
        if result.get(key) not in (None, ""):
            print(f"{indent}{_pad(label, 10)}: {result[key]}")
    if result.get("outcomes"):
        for outcome in result["outcomes"]:
            print(f"{indent}{outcome}")


def main() -> int:
    color = "NO_COLOR" not in os.environ and sys.stdout.isatty()
    started = time.perf_counter()
    contract = _check_contract()
    setup, package, element, rect, original_cursor = _prepare()
    ready = setup["status"] == "PASS" and element is not None and rect is not None

    if rect is None:
        points = {name: (0, 0) for _, name in FIXED_ANCHORS}
        safe_rect = (0, 0, 0, 0)
    else:
        points, safe_rect = _safe_geometry(rect)
    center = points["middleCenter"]

    results: list[dict[str, Any]] = [contract, setup]
    if ready and element is not None:
        results.append(
            _run_hover_case(
                "all_defaults",
                element,
                lambda: element.hover(),
                "element.hover()",
                "默认轨迹、1 秒延时和中心锚点均生效",
                expected=center,
                expected_move_mouse=True,
                min_elapsed_ms=DEFAULT_DELAY_MIN_MS,
                start_point=START_POINT,
            )
        )
        results.append(
            _run_hover_case(
                "simulative_false",
                element,
                lambda: element.hover(False, 0, "middleCenter"),
                'element.hover(False, 0, "middleCenter")',
                "simulative=False 使用瞬时移动并到达中心",
                expected=center,
                expected_move_mouse=False,
                max_elapsed_ms=NO_DELAY_MAX_MS,
                start_point=START_POINT,
            )
        )
        results.append(
            _run_hover_case(
                "simulative_true",
                element,
                lambda: element.hover(True, 0, "middleCenter"),
                'element.hover(True, 0, "middleCenter")',
                "simulative=True 使用人工轨迹并到达中心",
                expected=center,
                expected_move_mouse=True,
                min_elapsed_ms=SIMULATIVE_MIN_MS,
                start_point=START_POINT,
            )
        )
        results.append(
            _run_hover_case(
                "delay_none",
                element,
                lambda: element.hover(False, None, "middleCenter"),  # type: ignore[arg-type]
                'element.hover(False, None, "middleCenter")',
                "delay_after=None 不执行动作后等待",
                expected=center,
                expected_move_mouse=False,
                max_elapsed_ms=NO_DELAY_MAX_MS,
                start_point=START_POINT,
            )
        )
        results.append(
            _run_hover_case(
                "delay_positive",
                element,
                lambda: element.hover(False, POSITIVE_DELAY_SECONDS, "middleCenter"),
                'element.hover(False, 0.2, "middleCenter")',
                "delay_after=0.2 在悬停后完成等待",
                expected=center,
                expected_move_mouse=False,
                min_elapsed_ms=POSITIVE_DELAY_MIN_MS,
                start_point=START_POINT,
            )
        )
        for case_id, anchor in FIXED_ANCHORS:
            expected = points[anchor]
            results.append(
                _run_hover_case(
                    case_id,
                    element,
                    lambda anchor=anchor: element.hover(False, 0, anchor),
                    f'element.hover(False, 0, "{anchor}")',
                    f"{anchor} 落点与元素安全锚点一致",
                    expected=expected,
                    expected_move_mouse=False,
                )
            )
        results.append(
            _run_hover_case(
                "anchor_random",
                element,
                lambda: element.hover(False, 0, "random"),
                'element.hover(False, 0, "random")',
                "random 落点位于元素安全边界内",
                safe_rect=safe_rect,
                expected_move_mouse=False,
            )
        )

        tuple_expected = (center[0] + 12, center[1] - 6)
        results.append(
            _run_hover_case(
                "anchor_tuple",
                element,
                lambda: element.hover(False, 0, ("middleCenter", 12, -6)),
                'element.hover(False, 0, ("middleCenter", 12, -6))',
                "元组锚点及 X/Y 偏移均生效",
                expected=tuple_expected,
                expected_move_mouse=False,
            )
        )
        list_expected = (points["topLeft"][0] + 10, points["topLeft"][1] + 8)
        results.append(
            _run_hover_case(
                "anchor_list",
                element,
                lambda: element.hover(False, 0, ["topLeft", 10, 8]),
                'element.hover(False, 0, ["topLeft", 10, 8])',
                "列表锚点及 X/Y 偏移均生效",
                expected=list_expected,
                expected_move_mouse=False,
            )
        )
        mapping_expected = (
            points["bottomRight"][0] - 10,
            points["bottomRight"][1] - 8,
        )
        results.append(
            _run_hover_case(
                "anchor_mapping",
                element,
                lambda: element.hover(
                    False,
                    0,
                    {"anchor": "bottomRight", "offset_x": -10, "offset_y": -8},
                ),
                'element.hover(False, 0, {"anchor":"bottomRight","offset_x":-10,"offset_y":-8})',
                "字典 anchor/offset_x/offset_y 均生效",
                expected=mapping_expected,
                expected_move_mouse=False,
            )
        )
        alias_expected = (points["topCenter"][0] + 5, points["topCenter"][1] + 7)
        results.append(
            _run_hover_case(
                "anchor_alias_mapping",
                element,
                lambda: element.hover(False, 0, {"name": "topCenter", "x": 5, "y": 7}),
                'element.hover(False, 0, {"name":"topCenter","x":5,"y":7})',
                "字典 name/x/y 别名均生效",
                expected=alias_expected,
                expected_move_mouse=False,
            )
        )
        results.append(
            _run_hover_case(
                "anchor_casefold",
                element,
                lambda: element.hover(False, 0, "MiDdLeRiGhT"),
                'element.hover(False, 0, "MiDdLeRiGhT")',
                "锚点名称大小写归一化生效",
                expected=points["middleRight"],
                expected_move_mouse=False,
            )
        )
        results.append(_check_invalid_anchor(element))
        results.append(_check_invalid_delay(element, center))
    else:
        for case_id in tuple(CASE_LABELS)[2:-1]:
            results.append(_blocked(case_id, "靶场元素准备失败，未执行悬停"))

    results.append(_cleanup(package, original_cursor))

    _print_header(rect, safe_rect if rect is not None else None, color=color)
    for number, result in enumerate(results, start=1):
        _print_case(result, number, len(results), color=color)

    statuses = {result["status"] for result in results}
    exit_code = 1 if "FAIL" in statuses else (2 if "BLOCKED" in statuses else 0)
    lifecycle = "VERIFIED" if exit_code == 0 else "READY_FOR_LIVE"
    passed = sum(result["status"] == "PASS" for result in results)
    failed = sum(result["status"] == "FAIL" for result in results)
    blocked = sum(result["status"] == "BLOCKED" for result in results)
    parts = [f"{passed}/{len(results)} 通过"]
    if failed:
        parts.append(f"{failed} 失败")
    if blocked:
        parts.append(f"{blocked} 阻塞")
    summary = {0: "测试通过", 1: "测试失败", 2: "测试阻塞"}[exit_code]
    if color:
        summary = f"{COLORS[{0: 'PASS', 1: 'FAIL', 2: 'BLOCKED'}[exit_code]]}{summary}{RESET}"

    print("─" * TABLE_WIDTH)
    print(
        f"{summary}  ·  {lifecycle}  ·  {'，'.join(parts)}  ·  "
        f"{_elapsed(started):.1f}ms  ·  退出码 {exit_code}"
    )
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
