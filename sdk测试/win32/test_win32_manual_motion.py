"""``manual_motion_on()`` / ``manual_motion_off()`` 真实效果测试。

API 参数（不是测试脚本参数）::

    win32.manual_motion_on(
        motion_move: bool = True,
        motion_click: bool = True,
        motion_delay: bool = False,
        min_time: float = 0.25,
        max_time: float = 0.65,
    ) -> None

    win32.manual_motion_off() -> None

测试借用 UIAutoma.exe 当前启用的 ``D:\\code\\元素库\\260902_win元素``，并使用其中的
``win32靶场_表单控件_输入框_姓名``。由于这两个 API 只是进程内配置开关，脚本使用
``win32.mouse_move()`` 和元素 ``click`` 作为效果探针；测试结果仍评价人工轨迹开关的
配置、效果和关闭复位行为。

不测试非法参数。结束时始终关闭人工轨迹、恢复鼠标并关闭 Package，不关闭用户已启动
的 Win32 靶场程序。
"""

from __future__ import annotations

from _form_tab import ensure_form_tab

import ctypes
import os
import sys
import time
from ctypes import wintypes
from pathlib import Path
from typing import Any, Callable

import uiautoma
from uiautoma import win32
from uiautoma.win32 import _motion


__test__ = False

LIBRARY_DIR = Path(r"D:\code\元素库\260902_win元素")
ELEMENT_NAME = "win32靶场_表单控件_输入框_姓名"
START_POINT = (100, 100)
POSITION_TOLERANCE_PX = 3
SLOW_MIN_MS = 350.0
INSTANT_MAX_MS = 250.0

ANSI_GREEN = "\x1b[32m"
ANSI_RED = "\x1b[31m"
ANSI_CYAN = "\x1b[36m"
ANSI_RESET = "\x1b[0m"

_user32 = ctypes.WinDLL("user32", use_last_error=True)
_user32.SetCursorPos.argtypes = [ctypes.c_int, ctypes.c_int]
_user32.SetCursorPos.restype = wintypes.BOOL
_user32.GetCursorPos.argtypes = [ctypes.POINTER(wintypes.POINT)]
_user32.GetCursorPos.restype = wintypes.BOOL


def _color(text: str, ansi: str, *, enabled: bool) -> str:
    return f"{ansi}{text}{ANSI_RESET}" if enabled else text


def _state() -> dict[str, Any]:
    return dict(_motion.STATE)


def _defaults() -> dict[str, Any]:
    return dict(_motion.DEFAULTS)


def _cursor_position() -> tuple[int, int]:
    point = wintypes.POINT()
    if not _user32.GetCursorPos(ctypes.byref(point)):
        raise ctypes.WinError(ctypes.get_last_error())
    return int(point.x), int(point.y)


def _set_cursor(point: tuple[int, int]) -> None:
    if not _user32.SetCursorPos(*point):
        raise ctypes.WinError(ctypes.get_last_error())
    time.sleep(0.15)


def _near(actual: tuple[int, int], expected: tuple[int, int]) -> bool:
    return (
        abs(actual[0] - expected[0]) <= POSITION_TOLERANCE_PX
        and abs(actual[1] - expected[1]) <= POSITION_TOLERANCE_PX
    )


def _inside(
    point: tuple[int, int],
    rect: tuple[int, int, int, int],
) -> bool:
    x, y, width, height = rect
    return x <= point[0] < x + width and y <= point[1] < y + height


def _pass(
    label: str,
    call: str,
    detail: str,
    started: float,
    **extra: Any,
) -> dict[str, Any]:
    return {
        "label": label,
        "status": "PASS",
        "call": call,
        "detail": detail,
        "elapsed_ms": (time.perf_counter() - started) * 1000,
        **extra,
    }


def _fail(
    label: str,
    call: str,
    detail: str,
    started: float,
    *,
    exception: BaseException | None = None,
    **extra: Any,
) -> dict[str, Any]:
    result: dict[str, Any] = {
        "label": label,
        "status": "FAIL",
        "call": call,
        "detail": detail,
        "elapsed_ms": (time.perf_counter() - started) * 1000,
        **extra,
    }
    if exception is not None:
        result["exception"] = exception.__class__.__name__
        result["message"] = str(exception)
    return result


def _run_default_on() -> dict[str, Any]:
    label = "默认开启"
    call = "win32.manual_motion_on()"
    started = time.perf_counter()
    expected = {
        "motion_move": True,
        "motion_click": True,
        "motion_delay": False,
        "min_time": 0.25,
        "max_time": 0.65,
    }
    try:
        result = win32.manual_motion_on()
        actual = _state()
        if result is None and actual == expected:
            return _pass(label, call, "默认配置已生效并返回 None", started, state=actual)
        return _fail(
            label,
            call,
            "返回值或默认配置不符合预期",
            started,
            state=actual,
            expected=expected,
        )
    except Exception as exc:  # noqa: BLE001
        return _fail(label, call, "默认开启失败", started, exception=exc)
    finally:
        win32.manual_motion_off()


def _run_custom_on() -> dict[str, Any]:
    label = "自定义参数"
    call = "win32.manual_motion_on(False, False, True, 0.35, 0.70)"
    started = time.perf_counter()
    expected = {
        "motion_move": False,
        "motion_click": False,
        "motion_delay": True,
        "min_time": 0.35,
        "max_time": 0.70,
    }
    try:
        result = win32.manual_motion_on(False, False, True, 0.35, 0.70)
        actual = _state()
        if result is None and actual == expected:
            return _pass(label, call, "五个自定义参数均已生效", started, state=actual)
        return _fail(
            label,
            call,
            "返回值或自定义配置不符合预期",
            started,
            state=actual,
            expected=expected,
        )
    except Exception as exc:  # noqa: BLE001
        return _fail(label, call, "自定义开启失败", started, exception=exc)
    finally:
        win32.manual_motion_off()


def _run_slow_move(target: tuple[int, int]) -> dict[str, Any]:
    label = "开启后慢速移动"
    call = (
        "win32.manual_motion_on(True, True, False, 0.55, 0.80); "
        f"win32.mouse_move({target[0]}, {target[1]}, \"screen\", None, 0)"
    )
    started = time.perf_counter()
    try:
        _set_cursor(START_POINT)
        enabled = win32.manual_motion_on(True, True, False, 0.55, 0.80)
        action_started = time.perf_counter()
        moved = win32.mouse_move(target[0], target[1], "screen", None, 0)
        action_ms = (time.perf_counter() - action_started) * 1000
        actual = _cursor_position()
        passed = (
            enabled is None
            and moved is None
            and _near(actual, target)
            and action_ms >= SLOW_MIN_MS
        )
        if passed:
            return _pass(
                label,
                call,
                "人工轨迹慢速移动已生效",
                started,
                action_ms=action_ms,
                target=target,
                actual=actual,
            )
        return _fail(
            label,
            call,
            "移动落点或耗时不符合慢速轨迹预期",
            started,
            action_ms=action_ms,
            target=target,
            actual=actual,
        )
    except Exception as exc:  # noqa: BLE001
        return _fail(label, call, "慢速移动探针失败", started, exception=exc)
    finally:
        win32.manual_motion_off()


def _run_random_click(
    element: Any,
    rect: tuple[int, int, int, int],
) -> dict[str, Any]:
    label = "开启后随机点击"
    call = (
        "win32.manual_motion_on(True, True, False, 0.55, 0.80); "
        "element.click(\"left\", False, \"none\", 0, None, None)"
    )
    started = time.perf_counter()
    try:
        _set_cursor(START_POINT)
        enabled = win32.manual_motion_on(True, True, False, 0.55, 0.80)
        clicked = element.click("left", False, "none", 0, None, None)
        actual = _cursor_position()
        passed = enabled is None and clicked is None and _inside(actual, rect)
        if passed:
            return _pass(
                label,
                call,
                "人工轨迹点击完成，落点位于目标元素内",
                started,
                rect=rect,
                actual=actual,
            )
        return _fail(
            label,
            call,
            "点击返回值或鼠标落点不符合预期",
            started,
            rect=rect,
            actual=actual,
        )
    except Exception as exc:  # noqa: BLE001
        return _fail(label, call, "人工点击探针失败", started, exception=exc)
    finally:
        win32.manual_motion_off()


def _run_off_and_instant(target: tuple[int, int]) -> dict[str, Any]:
    label = "关闭后恢复瞬移"
    call = (
        "win32.manual_motion_off(); "
        f"win32.mouse_move({target[0]}, {target[1]}, \"screen\", None, 0)"
    )
    started = time.perf_counter()
    try:
        win32.manual_motion_on(True, True, True, 0.55, 0.80)
        disabled = win32.manual_motion_off()
        state = _state()
        _set_cursor(START_POINT)
        action_started = time.perf_counter()
        moved = win32.mouse_move(target[0], target[1], "screen", None, 0)
        action_ms = (time.perf_counter() - action_started) * 1000
        actual = _cursor_position()
        passed = (
            disabled is None
            and moved is None
            and state == _defaults()
            and _near(actual, target)
            and action_ms <= INSTANT_MAX_MS
        )
        if passed:
            return _pass(
                label,
                call,
                "配置已复位，未指定速度时恢复瞬移",
                started,
                action_ms=action_ms,
                state=state,
                target=target,
                actual=actual,
            )
        return _fail(
            label,
            call,
            "关闭后的状态、落点或耗时不符合预期",
            started,
            action_ms=action_ms,
            state=state,
            target=target,
            actual=actual,
        )
    except Exception as exc:  # noqa: BLE001
        return _fail(label, call, "关闭复位探针失败", started, exception=exc)
    finally:
        win32.manual_motion_off()


def _print_result(
    index: int,
    total: int,
    result: dict[str, Any],
    *,
    color: bool,
) -> None:
    passed = result["status"] == "PASS"
    badge = _color(
        "[通过]" if passed else "[失败]",
        ANSI_GREEN if passed else ANSI_RED,
        enabled=color,
    )
    print(f"[{index}/{total}] {badge} {result['label']}")
    print(f"      调用: {result['call']}")
    print(f"      结果: {result['detail']}  {result['elapsed_ms']:.1f}ms")
    if "action_ms" in result:
        print(f"      动作: {result['action_ms']:.1f}ms")
    if "actual" in result:
        print(f"      鼠标: {result['actual']}")
    if result.get("exception"):
        print(f"      异常: {result['exception']}: {result['message']}")


def main() -> int:
    color = "NO_COLOR" not in os.environ and sys.stdout.isatty()
    print(_color("UIAutoma Win32 API 测试", ANSI_CYAN, enabled=color))
    print()
    print("  API   : uiautoma.win32.manual_motion_on / manual_motion_off")
    print(f"  元素库: {LIBRARY_DIR}")
    print(f"  元素  : {ELEMENT_NAME}")
    print()

    if not LIBRARY_DIR.is_dir():
        print(_color("[失败] 元素库不存在", ANSI_RED, enabled=color))
        print(f"  路径: {LIBRARY_DIR}")
        return 1

    original_cursor = _cursor_position()
    package: Any | None = None
    try:
        package = uiautoma.current(required=False, refresh=True, timeout=5)
        ensure_form_tab(package)
        if package is None:
            raise RuntimeError(
                "UIAutoma 当前未启用元素库；请点击“使用当前元素库”后重试"
            )
        actual_library = Path(package.package_dir).resolve()
        if os.path.normcase(str(actual_library)) != os.path.normcase(
            str(LIBRARY_DIR.resolve())
        ):
            raise RuntimeError(
                f"UIAutoma 当前元素库不是测试库：{actual_library}"
            )
        element = win32.find(ELEMENT_NAME, timeout=10)
        rect = tuple(
            int(value)
            for value in element.get_bounding(
                to96dpi=False,
                relative_to="screen",
            )
        )
        if len(rect) != 4 or rect[2] <= 0 or rect[3] <= 0:
            raise RuntimeError(f"元素边界无效：{rect}")
    except Exception as exc:  # noqa: BLE001
        if package is not None:
            package.close()
        print(_color("[失败] 靶场元素准备失败", ANSI_RED, enabled=color))
        print(f"  异常: {exc.__class__.__name__}: {exc}")
        return 1

    target = (rect[0] + rect[2] // 2, rect[1] + rect[3] // 2)
    print(f"  边界  : {rect}")
    print(f"  中心  : {target}")
    print()

    runners: tuple[Callable[[], dict[str, Any]], ...] = (
        _run_default_on,
        _run_custom_on,
        lambda: _run_slow_move(target),
        lambda: _run_random_click(element, rect),
        lambda: _run_off_and_instant(target),
    )

    started = time.perf_counter()
    results: list[dict[str, Any]] = []
    total = len(runners)
    for index, runner in enumerate(runners, start=1):
        result = runner()
        results.append(result)
        _print_result(index, total, result, color=color)

    motion_reset = False
    cursor_restored = False
    package_closed = False
    try:
        motion_reset = win32.manual_motion_off() is None and _state() == _defaults()
    except Exception:  # noqa: BLE001
        motion_reset = False
    try:
        _set_cursor(original_cursor)
        cursor_restored = _near(_cursor_position(), original_cursor)
    except OSError:
        cursor_restored = False
    try:
        package.close()
        package_closed = True
    except Exception:  # noqa: BLE001
        package_closed = False

    passed_count = sum(result["status"] == "PASS" for result in results)
    cleanup_ok = motion_reset and cursor_restored and package_closed
    exit_code = 0 if passed_count == total and cleanup_ok else 1
    elapsed_ms = (time.perf_counter() - started) * 1000
    print()
    summary = "测试通过" if exit_code == 0 else "测试失败"
    print(_color(summary, ANSI_GREEN if exit_code == 0 else ANSI_RED, enabled=color))
    print(f"  结果    : {passed_count}/{total} 通过")
    print(f"  总耗时  : {elapsed_ms:.1f}ms")
    print(f"  人工轨迹: {'已关闭' if motion_reset else '复位失败'}")
    print(f"  鼠标位置: {'已恢复' if cursor_restored else '恢复失败'}")
    print(f"  Package : {'已关闭' if package_closed else '关闭失败'}")
    print("  靶场程序: 保持运行")
    print(f"  退出码  : {exit_code}")
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
