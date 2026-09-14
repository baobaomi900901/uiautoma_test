r"""``uiautoma.win32.Win32Window.resize()`` 测试。

API 参数（不是测试脚本参数）::

    Win32Window.resize(*, width: int = 1, height: int = 1) -> None

``width`` 和 ``height`` 均为仅限关键字参数，默认值为 1，表示窗口外框的
目标宽高；两者必须大于 0。调用保持窗口左上角位置不变，成功返回 ``None``。

脚本缩放已经运行的 Win32 靶场，通过 Windows ``GetWindowRect`` 独立验证默认、
仅宽度、仅高度和完整尺寸调用。靶场最小尺寸为 900 x 680；显式尺寸使用
1000 x 800，以区分默认参数和自定义参数。每次有效缩放后停留 1 秒，再恢复测试
开始时的尺寸。测试结束时兜底恢复靶场初始矩形、显示状态和运行脚本前的前台
窗口。导入本模块不会连接 Runtime 或缩放窗口。
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
from typing import Any, Callable

from uiautoma import win32
from uiautoma.win32 import Win32Window


__test__ = False

TARGET_TITLE = "Win32 靶场 - UIA"
TARGET_CLASS = "XPathWin32ShootingRange"
TARGET_PROCESS = "win32-shooting-range-uia.exe"
MIN_WIDTH = 900
MIN_HEIGHT = 680
TEST_WIDTH = 1000
TEST_HEIGHT = 800
RESIZE_TIMEOUT_SECONDS = 2.0
OBSERVATION_DELAY_SECONDS = 1.0

_USER32 = ctypes.WinDLL("user32", use_last_error=True)
_USER32.GetWindowRect.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.RECT)]
_USER32.GetWindowRect.restype = wintypes.BOOL
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
DETAIL_WIDTH = 70
DURATION_WIDTH = 8
TABLE_WIDTH = sum((PROGRESS_WIDTH, STATUS_WIDTH, CASE_WIDTH, DETAIL_WIDTH, DURATION_WIDTH, 8))

CASE_LABELS = {
    "api_contract": "API 合同",
    "initial_rect": "靶场初始矩形",
    "default_size": "全部默认参数",
    "width_only": "仅指定宽度",
    "height_only": "仅指定高度",
    "full_size": "完整尺寸",
    "invalid_sizes": "非法尺寸",
    "resource_cleanup": "尺寸与焦点恢复",
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


def _error_result(case_id: str, detail: str, started: float, exc: BaseException) -> dict[str, Any]:
    status = "BLOCKED" if exc.__class__.__name__ in BLOCKING_EXCEPTION_NAMES else "FAIL"
    return _result(
        case_id,
        status,
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
        0 if unicodedata.combining(char)
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


def _wait_rect(handle: int, predicate: Callable[[dict[str, int]], bool]) -> dict[str, int] | None:
    deadline = time.monotonic() + RESIZE_TIMEOUT_SECONDS
    while True:
        rect = _get_rect(handle)
        if predicate(rect):
            return rect
        if time.monotonic() >= deadline:
            return None
        time.sleep(0.05)


def _check_contract() -> dict[str, Any]:
    started = time.perf_counter()
    try:
        signature = inspect.signature(Win32Window.resize)
        parameters = signature.parameters
        width = parameters.get("width")
        height = parameters.get("height")
        passed = (
            tuple(parameters) == ("self", "width", "height")
            and width is not None
            and height is not None
            and width.kind is inspect.Parameter.KEYWORD_ONLY
            and height.kind is inspect.Parameter.KEYWORD_ONLY
            and width.default == 1
            and height.default == 1
            and str(width.annotation) in {"int", "<class 'int'>"}
            and str(height.annotation) in {"int", "<class 'int'>"}
            and str(signature.return_annotation) in {"None", "<class 'NoneType'>"}
        )
        return _result(
            "api_contract",
            "PASS" if passed else "FAIL",
            "width、height 均为默认 1 的仅限关键字整数参数，返回 None"
            if passed else "公开签名与当前合同不一致",
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
    dict[str, int] | None,
    dict[str, bool] | None,
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
        initial_rect = _get_rect(handle)
        initial_state = _native_state(handle)
        window.set_state("normal")
        baseline = _wait_rect(
            handle,
            lambda rect: (
                _native_state(handle)["visible"]
                and not _native_state(handle)["iconic"]
                and not _native_state(handle)["zoomed"]
                and rect["w"] > 0
                and rect["h"] > 0
            ),
        )
        if baseline is None:
            raise RuntimeError("无法将靶场准备为正常显示状态")
        return (
            _result(
                "initial_rect",
                "PASS",
                f"已记录初始矩形 ({initial_rect['x']}, {initial_rect['y']}, {initial_rect['w']}, {initial_rect['h']})",
                elapsed_ms=_elapsed(started),
                initial_rect=initial_rect,
                baseline=baseline,
            ),
            window,
            original,
            initial_rect,
            baseline,
            initial_state,
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


def _run_resize(
    case_id: str,
    window: Win32Window | None,
    baseline: dict[str, int] | None,
    *,
    kwargs: dict[str, int],
    exact_width: int | None,
    exact_height: int | None,
) -> dict[str, Any]:
    started = time.perf_counter()
    if window is None or baseline is None:
        return _blocked(case_id, "靶场窗口或基准矩形不可用")
    handle = _handle(window)
    try:
        returned = window.resize(**kwargs)
        target = _wait_rect(
            handle,
            lambda rect: (
                rect["x"] == baseline["x"]
                and rect["y"] == baseline["y"]
                and rect["w"] > 0
                and rect["h"] > 0
                and (exact_width is None or rect["w"] == exact_width)
                and (exact_height is None or rect["h"] == exact_height)
            ),
        )
        if target is not None:
            time.sleep(OBSERVATION_DELAY_SECONDS)

        restore_value = window.resize(width=baseline["w"], height=baseline["h"])
        restored = _wait_rect(handle, lambda rect: rect == baseline)
        passed = returned is None and target is not None and restore_value is None and restored is not None
        args = ", ".join(f"{key}={value}" for key, value in kwargs.items())
        call = f"resize({args})" if args else "resize()"
        if passed:
            detail = (
                f"{call} 生效为 {target['w']} × {target['h']}，"
                "左上角不变，停留 1 秒后已恢复原尺寸"
            )
        else:
            detail = f"{call} 的生效尺寸、左上角、返回值或恢复结果不符合预期"
        return _result(
            case_id,
            "PASS" if passed else "FAIL",
            detail,
            elapsed_ms=_elapsed(started),
            expected={"width": exact_width, "height": exact_height, "position": (baseline["x"], baseline["y"])},
            actual=target,
            restored=restored,
        )
    except Exception as exc:  # noqa: BLE001
        try:
            window.resize(width=baseline["w"], height=baseline["h"])
        except Exception:  # noqa: BLE001
            pass
        return _error_result(case_id, "resize() 调用失败", started, exc)


def _check_invalid_sizes(window: Win32Window | None) -> dict[str, Any]:
    started = time.perf_counter()
    if window is None:
        return _blocked("invalid_sizes", "靶场窗口不可用")
    calls = (
        {"width": 0, "height": TEST_HEIGHT},
        {"width": -1, "height": TEST_HEIGHT},
        {"width": TEST_WIDTH, "height": 0},
        {"width": TEST_WIDTH, "height": -1},
    )
    outcomes: list[dict[str, Any]] = []
    for kwargs in calls:
        try:
            window.resize(**kwargs)
            outcomes.append({"args": kwargs, "exception": None})
        except Exception as exc:  # noqa: BLE001
            outcomes.append({"args": kwargs, "exception": exc.__class__.__name__, "message": str(exc)})
    passed = all(item["exception"] == "InvalidParamsError" for item in outcomes)
    return _result(
        "invalid_sizes",
        "PASS" if passed else "FAIL",
        "宽度和高度的零值、负值均被 InvalidParamsError 正确拒绝"
        if passed else "至少一个非正宽高未按 InvalidParamsError 拒绝",
        elapsed_ms=_elapsed(started),
        outcomes=outcomes,
    )


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
            handle = _handle(window)
            window.set_state("normal")
            window.move(x=initial_rect["x"], y=initial_rect["y"])
            window.resize(width=initial_rect["w"], height=initial_rect["h"])
            rect_restored = _wait_rect(handle, lambda rect: rect == initial_rect) is not None
            if not rect_restored:
                errors.append("靶场初始矩形未恢复")

            if not initial_state["visible"]:
                window.set_state("hide")
                state_ok = lambda state: not state["visible"]
            elif initial_state["iconic"]:
                window.set_state("minimize")
                state_ok = lambda state: state["iconic"]
            elif initial_state["zoomed"]:
                window.set_state("maximize")
                state_ok = lambda state: state["zoomed"]
            else:
                window.set_state("normal")
                state_ok = lambda state: state["visible"] and not state["iconic"] and not state["zoomed"]
            deadline = time.monotonic() + RESIZE_TIMEOUT_SECONDS
            while True:
                if state_ok(_native_state(handle)):
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
            deadline = time.monotonic() + RESIZE_TIMEOUT_SECONDS
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
            "靶场初始矩形、显示状态和原前台窗口均已恢复" if passed else "；".join(errors),
            elapsed_ms=_elapsed(started),
        )
    except Exception as exc:  # noqa: BLE001
        return _error_result("resource_cleanup", "恢复靶场矩形、状态或焦点失败", started, exc)


def _print_header(*, color: bool) -> None:
    title = f"{CYAN}UIAutoma Win32 API 测试{RESET}" if color else "UIAutoma Win32 API 测试"
    print(title)
    print()
    print("  API     : uiautoma.win32.Win32Window.resize")
    print(f"  测试窗口: {TARGET_TITLE}")
    print(f"  窗口类名: {TARGET_CLASS}")
    print(f"  目标进程: {TARGET_PROCESS}")
    print(f"  靶场最小: {MIN_WIDTH} × {MIN_HEIGHT}")
    print("  观察延迟: 每次缩放后停留 1 秒，再恢复原尺寸")
    print("  尺寸恢复: 测试结束后恢复靶场初始矩形、状态和原前台窗口")
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
    if result.get("outcomes"):
        for outcome in result["outcomes"]:
            print(f"{indent}{outcome}")


def main() -> int:
    color = "NO_COLOR" not in os.environ and sys.stdout.isatty()
    _print_header(color=color)
    started = time.perf_counter()

    contract = _check_contract()
    initial, window, original, initial_rect, baseline, initial_state = _prepare()
    if window is not None and baseline is not None and initial["status"] == "PASS":
        resize_results = [
            _run_resize("default_size", window, baseline, kwargs={}, exact_width=MIN_WIDTH, exact_height=MIN_HEIGHT),
            _run_resize("width_only", window, baseline, kwargs={"width": TEST_WIDTH}, exact_width=TEST_WIDTH, exact_height=MIN_HEIGHT),
            _run_resize("height_only", window, baseline, kwargs={"height": TEST_HEIGHT}, exact_width=MIN_WIDTH, exact_height=TEST_HEIGHT),
            _run_resize("full_size", window, baseline, kwargs={"width": TEST_WIDTH, "height": TEST_HEIGHT}, exact_width=TEST_WIDTH, exact_height=TEST_HEIGHT),
        ]
        invalid = _check_invalid_sizes(window)
    else:
        resize_results = [
            _blocked(case_id, "靶场窗口或基准矩形不可用")
            for case_id in ("default_size", "width_only", "height_only", "full_size")
        ]
        invalid = _blocked("invalid_sizes", "靶场窗口不可用")

    cleanup = _restore(window, original, initial_rect, initial_state)
    results = [contract, initial, *resize_results, invalid, cleanup]
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
