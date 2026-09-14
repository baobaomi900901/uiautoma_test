r"""``uiautoma.win32.Win32Window.move()`` 测试。

API 参数（不是测试脚本参数）::

    Win32Window.move(*, x: int = 0, y: int = 0) -> None

``x`` 和 ``y`` 均为仅限关键字参数，默认值为 0，表示窗口外框左上角的
屏幕坐标。调用只改变窗口位置并保持宽高不变，成功返回 ``None``。

脚本移动已经运行的 Win32 靶场，通过 Windows ``GetWindowRect`` 独立验证默认、
仅 X、仅 Y 和完整坐标调用。每次到达目标位置后停留 1 秒，再移回测试开始时记录
的初始位置并校验。测试结束时还会兜底恢复靶场显示状态和运行脚本前的前台窗口。
导入本模块不会连接 Runtime 或移动窗口。
"""

from __future__ import annotations

import ctypes
import inspect
import os
import re
import sys
import time
import unicodedata
from ctypes import wintypes
from typing import Any

from uiautoma import win32
from uiautoma.win32 import Win32Window


__test__ = False

TARGET_TITLE = "Win32 靶场 - UIA"
TARGET_CLASS = "XPathWin32ShootingRange"
TARGET_PROCESS = "win32-shooting-range-uia.exe"
POSITION_TIMEOUT_SECONDS = 2.0
OBSERVATION_DELAY_SECONDS = 1.0

SM_CXSCREEN = 0
SM_CYSCREEN = 1
_USER32 = ctypes.WinDLL("user32", use_last_error=True)
_USER32.GetWindowRect.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.RECT)]
_USER32.GetWindowRect.restype = wintypes.BOOL
_USER32.GetSystemMetrics.argtypes = [ctypes.c_int]
_USER32.GetSystemMetrics.restype = ctypes.c_int
_USER32.IsWindowVisible.argtypes = [wintypes.HWND]
_USER32.IsWindowVisible.restype = wintypes.BOOL
_USER32.IsIconic.argtypes = [wintypes.HWND]
_USER32.IsIconic.restype = wintypes.BOOL
_USER32.IsZoomed.argtypes = [wintypes.HWND]
_USER32.IsZoomed.restype = wintypes.BOOL

STATUS_LABELS = {"PASS": "通过", "FAIL": "失败", "BLOCKED": "阻塞"}
COLORS = {"PASS": "\x1b[32m", "FAIL": "\x1b[31m", "BLOCKED": "\x1b[33m"}
CYAN = "\x1b[36m"
RESET = "\x1b[0m"

PROGRESS_WIDTH = 7
STATUS_WIDTH = 6
CASE_WIDTH = 18
DETAIL_WIDTH = 64
DURATION_WIDTH = 8
TABLE_WIDTH = sum(
    (PROGRESS_WIDTH, STATUS_WIDTH, CASE_WIDTH, DETAIL_WIDTH, DURATION_WIDTH, 8)
)

CASE_LABELS = {
    "api_contract": "API 合同",
    "initial_rect": "靶场初始矩形",
    "default_position": "全部默认参数",
    "x_only": "仅指定 X",
    "y_only": "仅指定 Y",
    "xy_position": "完整坐标",
    "resource_cleanup": "位置与焦点恢复",
}

BLOCKING_EXCEPTION_NAMES = {
    "ConnectionError",
    "EOFError",
    "ElementNotFoundError",
    "HostBusyError",
    "HostUnavailableError",
    "PipeClosedError",
    "TimeoutError",
    "UnsupportedActionError",
    "UnsupportedProtocolError",
}


def _result(case_id: str, status: str, detail: str, **extra: Any) -> dict[str, Any]:
    return {"case_id": case_id, "status": status, "detail": detail, **extra}


def _elapsed(started: float) -> float:
    return (time.perf_counter() - started) * 1000


def _error_status(exc: BaseException) -> str:
    return "BLOCKED" if exc.__class__.__name__ in BLOCKING_EXCEPTION_NAMES else "FAIL"


def _error_result(case_id: str, detail: str, started: float, exc: BaseException) -> dict[str, Any]:
    return _result(
        case_id,
        _error_status(exc),
        detail,
        elapsed_ms=_elapsed(started),
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


def _handle(window: Win32Window) -> int:
    try:
        return int(window.raw.get("handle") or 0)
    except (TypeError, ValueError):
        return 0


def _get_rect(handle: int) -> dict[str, int]:
    rect = wintypes.RECT()
    if not _USER32.GetWindowRect(wintypes.HWND(handle), ctypes.byref(rect)):
        raise OSError(ctypes.get_last_error(), "GetWindowRect failed")
    return {
        "x": int(rect.left),
        "y": int(rect.top),
        "w": int(rect.right - rect.left),
        "h": int(rect.bottom - rect.top),
    }


def _native_state(handle: int) -> dict[str, bool]:
    hwnd = wintypes.HWND(handle)
    return {
        "visible": bool(_USER32.IsWindowVisible(hwnd)),
        "iconic": bool(_USER32.IsIconic(hwnd)),
        "zoomed": bool(_USER32.IsZoomed(hwnd)),
    }


def _wait_rect(handle: int, x: int, y: int) -> dict[str, int] | None:
    deadline = time.monotonic() + POSITION_TIMEOUT_SECONDS
    while True:
        rect = _get_rect(handle)
        if rect["x"] == x and rect["y"] == y:
            return rect
        if time.monotonic() >= deadline:
            return None
        time.sleep(0.05)


def _safe_coordinates(width: int, height: int) -> tuple[int, int]:
    screen_width = max(1, int(_USER32.GetSystemMetrics(SM_CXSCREEN)))
    screen_height = max(1, int(_USER32.GetSystemMetrics(SM_CYSCREEN)))
    x = min(160, max(0, screen_width - width))
    y = min(120, max(0, screen_height - height))
    return x, y


def _check_contract() -> dict[str, Any]:
    started = time.perf_counter()
    try:
        signature = inspect.signature(Win32Window.move)
        parameters = signature.parameters
        x = parameters.get("x")
        y = parameters.get("y")
        passed = (
            tuple(parameters) == ("self", "x", "y")
            and x is not None
            and y is not None
            and x.kind is inspect.Parameter.KEYWORD_ONLY
            and y.kind is inspect.Parameter.KEYWORD_ONLY
            and x.default == 0
            and y.default == 0
            and str(x.annotation) in {"int", "<class 'int'>"}
            and str(y.annotation) in {"int", "<class 'int'>"}
            and str(signature.return_annotation) in {"None", "<class 'NoneType'>"}
        )
        return _result(
            "api_contract",
            "PASS" if passed else "FAIL",
            "x、y 均为默认 0 的仅限关键字整数参数，返回 None" if passed else "公开签名与当前合同不一致",
            elapsed_ms=_elapsed(started),
            signature=str(signature),
        )
    except Exception as exc:  # noqa: BLE001
        return _error_result("api_contract", "无法检查公开签名", started, exc)


def _prepare() -> tuple[
    dict[str, Any],
    Win32Window | None,
    Win32Window | None,
    dict[str, int] | None,
    dict[str, bool] | None,
    tuple[int, int] | None,
]:
    started = time.perf_counter()
    try:
        window = win32.get(
            TARGET_TITLE,
            class_name=TARGET_CLASS,
            process_name=TARGET_PROCESS,
            timeout=5,
        )
        original = win32.get_active(timeout=5)
        handle = _handle(window)
        initial_state = _native_state(handle)
        initial_rect = _get_rect(handle)

        window.set_state("normal")
        deadline = time.monotonic() + POSITION_TIMEOUT_SECONDS
        while True:
            state = _native_state(handle)
            if state["visible"] and not state["iconic"] and not state["zoomed"]:
                break
            if time.monotonic() >= deadline:
                raise RuntimeError("无法将靶场准备为正常显示状态")
            time.sleep(0.05)
        test_rect = _get_rect(handle)
        coordinates = _safe_coordinates(test_rect["w"], test_rect["h"])
        return (
            _result(
                "initial_rect",
                "PASS",
                (
                    f"已记录初始矩形 ({initial_rect['x']}, {initial_rect['y']}, "
                    f"{initial_rect['w']}, {initial_rect['h']})"
                ),
                elapsed_ms=_elapsed(started),
                handle=handle,
                initial_rect=initial_rect,
                test_size={"w": test_rect["w"], "h": test_rect["h"]},
                coordinates=coordinates,
            ),
            window,
            original,
            initial_rect,
            initial_state,
            coordinates,
        )
    except Exception as exc:  # noqa: BLE001
        return (
            _error_result("initial_rect", "获取靶场初始矩形失败", started, exc),
            None,
            None,
            None,
            None,
            None,
        )


def _run_move(
    case_id: str,
    window: Win32Window | None,
    *,
    kwargs: dict[str, int],
    expected_x: int,
    expected_y: int,
    expected_size: tuple[int, int] | None,
    return_position: tuple[int, int] | None,
) -> dict[str, Any]:
    started = time.perf_counter()
    if window is None or expected_size is None or return_position is None:
        return _blocked(case_id, "靶场窗口、初始尺寸或返回位置不可用")
    try:
        returned = window.move(**kwargs)
        target_rect = _wait_rect(_handle(window), expected_x, expected_y)
        target_size_ok = (
            target_rect is not None
            and (target_rect["w"], target_rect["h"]) == expected_size
        )
        if target_rect is not None:
            time.sleep(OBSERVATION_DELAY_SECONDS)

        return_x, return_y = return_position
        return_value = window.move(x=return_x, y=return_y)
        restored_rect = _wait_rect(_handle(window), return_x, return_y)
        restored_size_ok = (
            restored_rect is not None
            and (restored_rect["w"], restored_rect["h"]) == expected_size
        )
        passed = (
            returned is None
            and target_rect is not None
            and target_size_ok
            and return_value is None
            and restored_rect is not None
            and restored_size_ok
        )
        call_args = ", ".join(f"{key}={value}" for key, value in kwargs.items())
        call_text = f"move({call_args})" if call_args else "move()"
        return _result(
            case_id,
            "PASS" if passed else "FAIL",
            (
                f"{call_text} 到达 ({expected_x}, {expected_y})，停留 1 秒后已移回初始位置"
                if passed
                else f"{call_text} 的目标位置、尺寸或返回初始位置不符合预期"
            ),
            elapsed_ms=_elapsed(started),
            returned=returned,
            expected={"x": expected_x, "y": expected_y, "w": expected_size[0], "h": expected_size[1]},
            actual=target_rect,
            observation_delay_seconds=OBSERVATION_DELAY_SECONDS,
            return_position={"x": return_x, "y": return_y},
            return_value=return_value,
            restored=restored_rect,
        )
    except Exception as exc:  # noqa: BLE001
        try:
            return_x, return_y = return_position
            window.move(x=return_x, y=return_y)
        except Exception:  # noqa: BLE001
            pass
        return _error_result(case_id, "move() 调用失败", started, exc)


def _restore(
    window: Win32Window | None,
    original: Win32Window | None,
    initial_rect: dict[str, int] | None,
    initial_state: dict[str, bool] | None,
) -> dict[str, Any]:
    started = time.perf_counter()
    errors: list[str] = []
    try:
        rect_restored = window is None or initial_rect is None
        state_restored = window is None or initial_state is None
        if window is not None and initial_rect is not None and initial_state is not None:
            window.set_state("normal")
            window.move(x=initial_rect["x"], y=initial_rect["y"])
            restored_rect = _wait_rect(_handle(window), initial_rect["x"], initial_rect["y"])
            rect_restored = restored_rect is not None
            if not rect_restored:
                errors.append("靶场初始位置未恢复")

            if not initial_state["visible"]:
                window.set_state("hide")
                predicate = lambda state: not state["visible"]
            elif initial_state["iconic"]:
                window.set_state("minimize")
                predicate = lambda state: state["iconic"]
            elif initial_state["zoomed"]:
                window.set_state("maximize")
                predicate = lambda state: state["zoomed"]
            else:
                window.set_state("normal")
                predicate = lambda state: state["visible"] and not state["iconic"] and not state["zoomed"]
            deadline = time.monotonic() + POSITION_TIMEOUT_SECONDS
            while True:
                if predicate(_native_state(_handle(window))):
                    state_restored = True
                    break
                if time.monotonic() >= deadline:
                    state_restored = False
                    errors.append("靶场初始显示状态未恢复")
                    break
                time.sleep(0.05)

        focus_restored = original is None
        if original is not None:
            original.activate()
            deadline = time.monotonic() + POSITION_TIMEOUT_SECONDS
            while True:
                if original.is_active():
                    focus_restored = True
                    break
                if time.monotonic() >= deadline:
                    errors.append("原前台窗口未恢复")
                    break
                time.sleep(0.05)

        passed = rect_restored and state_restored and focus_restored
        return _result(
            "resource_cleanup",
            "PASS" if passed else "FAIL",
            "靶场初始位置、显示状态和原前台窗口均已恢复" if passed else "；".join(errors),
            elapsed_ms=_elapsed(started),
            rect_restored=rect_restored,
            state_restored=state_restored,
            focus_restored=focus_restored,
        )
    except Exception as exc:  # noqa: BLE001
        return _error_result("resource_cleanup", "恢复靶场位置、状态或焦点失败", started, exc)


def _print_header(*, color: bool) -> None:
    title = f"{CYAN}UIAutoma Win32 API 测试{RESET}" if color else "UIAutoma Win32 API 测试"
    print(title)
    print()
    print("  API     : uiautoma.win32.Win32Window.move")
    print(f"  测试窗口: {TARGET_TITLE}")
    print(f"  窗口类名: {TARGET_CLASS}")
    print(f"  目标进程: {TARGET_PROCESS}")
    print("  观察延迟: 每次移动后停留 1 秒，再移回初始位置")
    print("  位置恢复: 测试结束后恢复靶场初始位置、状态和原前台窗口")
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
    if result.get("message"):
        print(f"{indent}{_pad('原因', 8)}: {result['message']}")
    if result.get("expected"):
        print(f"{indent}{_pad('预期矩形', 10)}: {result['expected']}")
    if result.get("actual"):
        print(f"{indent}{_pad('实际矩形', 10)}: {result['actual']}")


def main() -> int:
    color = "NO_COLOR" not in os.environ and sys.stdout.isatty()
    _print_header(color=color)
    started = time.perf_counter()

    contract = _check_contract()
    initial_result, window, original, initial_rect, initial_state, coordinates = _prepare()
    if window is not None and initial_result["status"] == "PASS" and coordinates is not None:
        test_size_raw = initial_result.get("test_size") or {}
        expected_size = (int(test_size_raw.get("w") or 0), int(test_size_raw.get("h") or 0))
        return_position = (initial_rect["x"], initial_rect["y"]) if initial_rect is not None else None
        x, y = coordinates
        move_results = [
            _run_move("default_position", window, kwargs={}, expected_x=0, expected_y=0, expected_size=expected_size, return_position=return_position),
            _run_move("x_only", window, kwargs={"x": x}, expected_x=x, expected_y=0, expected_size=expected_size, return_position=return_position),
            _run_move("y_only", window, kwargs={"y": y}, expected_x=0, expected_y=y, expected_size=expected_size, return_position=return_position),
            _run_move("xy_position", window, kwargs={"x": x, "y": y}, expected_x=x, expected_y=y, expected_size=expected_size, return_position=return_position),
        ]
    else:
        move_results = [
            _blocked(case_id, "靶场窗口或安全坐标不可用")
            for case_id in ("default_position", "x_only", "y_only", "xy_position")
        ]
    cleanup = _restore(window, original, initial_rect, initial_state)
    results = [contract, initial_result, *move_results, cleanup]

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
