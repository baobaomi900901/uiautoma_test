r"""``uiautoma.win32.Win32Window.set_state()`` 测试。

API 参数（不是测试脚本参数）::

    Win32Window.set_state(flag: str) -> None

``flag`` 支持 ``normal``、``show``、``restore``、``max``、``maximize``、
``maximized``、``min``、``minimize``、``minimized`` 和 ``hide``。参数匹配
忽略首尾空白和大小写；非法值抛出 ``InvalidParamsError``。

脚本对已经运行的 Win32 靶场逐一调用全部状态值，并使用 Windows 原生
``IsWindowVisible``、``IsIconic``、``IsZoomed`` 独立观察结果。测试结束时恢复
靶场初始显示状态和运行脚本前的前台窗口。导入本模块不会连接 Runtime 或改变窗口。
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
STATE_TIMEOUT_SECONDS = 2.0

_USER32 = ctypes.WinDLL("user32", use_last_error=True)
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
DETAIL_WIDTH = 66
DURATION_WIDTH = 8
TABLE_WIDTH = sum(
    (PROGRESS_WIDTH, STATUS_WIDTH, CASE_WIDTH, DETAIL_WIDTH, DURATION_WIDTH, 8)
)

CASE_LABELS = {
    "api_contract": "API 合同",
    "initial_state": "靶场初始状态",
    "display_states": "显示与恢复",
    "maximize_aliases": "最大化及别名",
    "minimize_aliases": "最小化及别名",
    "hide_state": "隐藏状态",
    "invalid_state": "非法状态值",
    "resource_cleanup": "状态与焦点恢复",
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


def _native_state(handle: int) -> dict[str, bool]:
    hwnd = wintypes.HWND(handle)
    return {
        "visible": bool(_USER32.IsWindowVisible(hwnd)),
        "iconic": bool(_USER32.IsIconic(hwnd)),
        "zoomed": bool(_USER32.IsZoomed(hwnd)),
    }


def _state_label(state: dict[str, bool]) -> str:
    if not state["visible"]:
        return "隐藏"
    if state["iconic"]:
        return "最小化"
    if state["zoomed"]:
        return "最大化"
    return "正常显示"


def _wait_state(handle: int, predicate: Callable[[dict[str, bool]], bool]) -> dict[str, bool] | None:
    deadline = time.monotonic() + STATE_TIMEOUT_SECONDS
    while True:
        state = _native_state(handle)
        if predicate(state):
            return state
        if time.monotonic() >= deadline:
            return None
        time.sleep(0.05)


def _normal(state: dict[str, bool]) -> bool:
    return state["visible"] and not state["iconic"] and not state["zoomed"]


def _check_contract() -> dict[str, Any]:
    started = time.perf_counter()
    try:
        signature = inspect.signature(Win32Window.set_state)
        parameters = signature.parameters
        flag = parameters.get("flag")
        passed = (
            tuple(parameters) == ("self", "flag")
            and flag is not None
            and flag.kind is inspect.Parameter.POSITIONAL_OR_KEYWORD
            and flag.default is inspect.Parameter.empty
            and str(flag.annotation) in {"str", "<class 'str'>"}
            and str(signature.return_annotation) in {"None", "<class 'NoneType'>"}
        )
        return _result(
            "api_contract",
            "PASS" if passed else "FAIL",
            "公开签名包含必填 flag: str，并返回 None" if passed else "公开签名与当前合同不一致",
            elapsed_ms=_elapsed(started),
            signature=str(signature),
        )
    except Exception as exc:  # noqa: BLE001
        return _error_result("api_contract", "无法检查公开签名", started, exc)


def _prepare() -> tuple[dict[str, Any], Win32Window | None, Win32Window | None, dict[str, bool] | None]:
    started = time.perf_counter()
    try:
        target = win32.get(
            TARGET_TITLE,
            class_name=TARGET_CLASS,
            process_name=TARGET_PROCESS,
            timeout=5,
        )
        original = win32.get_active(timeout=5)
        handle = _handle(target)
        if handle <= 0:
            return _result("initial_state", "FAIL", "靶场窗口没有真实句柄", elapsed_ms=_elapsed(started)), None, original, None
        state = _native_state(handle)
        return (
            _result(
                "initial_state",
                "PASS",
                f"已记录靶场初始状态：{_state_label(state)}；句柄 {handle}",
                elapsed_ms=_elapsed(started),
                handle=handle,
                initial_state=state,
                original_foreground_handle=_handle(original),
            ),
            target,
            original,
            state,
        )
    except Exception as exc:  # noqa: BLE001
        return _error_result("initial_state", "获取靶场窗口或初始状态失败", started, exc), None, None, None


def _apply(
    window: Win32Window,
    flag: str,
    predicate: Callable[[dict[str, bool]], bool],
) -> tuple[bool, Any, dict[str, bool] | None]:
    returned = window.set_state(flag)
    state = _wait_state(_handle(window), predicate)
    return returned is None and state is not None, returned, state


def _check_display_states(window: Win32Window | None) -> dict[str, Any]:
    started = time.perf_counter()
    if window is None:
        return _blocked("display_states", "靶场窗口不可用")
    try:
        checks: list[dict[str, Any]] = []

        window.set_state("minimize")
        if _wait_state(_handle(window), lambda state: state["iconic"]) is None:
            raise RuntimeError("normal 测试准备最小化失败")
        ok, returned, state = _apply(window, "normal", _normal)
        checks.append({"flag": "normal", "ok": ok, "returned": returned, "state": state})

        window.set_state("hide")
        if _wait_state(_handle(window), lambda state: not state["visible"]) is None:
            raise RuntimeError("show 测试准备隐藏失败")
        ok, returned, state = _apply(window, "show", _normal)
        checks.append({"flag": "show", "ok": ok, "returned": returned, "state": state})

        window.set_state("minimize")
        if _wait_state(_handle(window), lambda state: state["iconic"]) is None:
            raise RuntimeError("restore 测试准备最小化失败")
        ok, returned, state = _apply(
            window,
            "restore",
            lambda current: current["visible"] and not current["iconic"],
        )
        checks.append({"flag": "restore", "ok": ok, "returned": returned, "state": state})

        passed = all(check["ok"] for check in checks)
        return _result(
            "display_states",
            "PASS" if passed else "FAIL",
            "normal、show、restore 均返回 None 且恢复可见窗口" if passed else "显示或恢复状态不符合预期",
            elapsed_ms=_elapsed(started),
            checks=checks,
        )
    except Exception as exc:  # noqa: BLE001
        return _error_result("display_states", "测试显示与恢复状态失败", started, exc)


def _check_alias_group(
    case_id: str,
    window: Win32Window | None,
    flags: tuple[str, ...],
    predicate: Callable[[dict[str, bool]], bool],
    success_detail: str,
) -> dict[str, Any]:
    started = time.perf_counter()
    if window is None:
        return _blocked(case_id, "靶场窗口不可用")
    try:
        checks: list[dict[str, Any]] = []
        for flag in flags:
            window.set_state("normal")
            if _wait_state(_handle(window), _normal) is None:
                raise RuntimeError(f"{flag} 测试准备正常显示失败")
            ok, returned, state = _apply(window, flag, predicate)
            checks.append({"flag": flag, "ok": ok, "returned": returned, "state": state})
        passed = all(check["ok"] for check in checks)
        return _result(
            case_id,
            "PASS" if passed else "FAIL",
            success_detail if passed else "部分状态别名未产生预期窗口状态",
            elapsed_ms=_elapsed(started),
            checks=checks,
        )
    except Exception as exc:  # noqa: BLE001
        return _error_result(case_id, "测试状态别名失败", started, exc)


def _check_hide(window: Win32Window | None) -> dict[str, Any]:
    started = time.perf_counter()
    if window is None:
        return _blocked("hide_state", "靶场窗口不可用")
    try:
        window.set_state("normal")
        if _wait_state(_handle(window), _normal) is None:
            raise RuntimeError("hide 测试准备正常显示失败")
        ok, returned, state = _apply(window, "hide", lambda current: not current["visible"])
        return _result(
            "hide_state",
            "PASS" if ok else "FAIL",
            "hide 返回 None 且窗口不可见" if ok else "hide 后窗口仍然可见",
            elapsed_ms=_elapsed(started),
            returned=returned,
            state=state,
        )
    except Exception as exc:  # noqa: BLE001
        return _error_result("hide_state", "测试隐藏状态失败", started, exc)


def _check_invalid(window: Win32Window | None) -> dict[str, Any]:
    started = time.perf_counter()
    if window is None:
        return _blocked("invalid_state", "靶场窗口不可用")
    try:
        window.set_state("show")
        _wait_state(_handle(window), lambda state: state["visible"])
        window.set_state("unsupported-state")
        return _result(
            "invalid_state",
            "FAIL",
            "非法 flag 未被拒绝",
            elapsed_ms=_elapsed(started),
        )
    except Exception as exc:  # noqa: BLE001
        passed = exc.__class__.__name__ == "InvalidParamsError"
        return _result(
            "invalid_state",
            "PASS" if passed else _error_status(exc),
            "非法 flag 被正确拒绝" if passed else "非法 flag 抛出了非预期异常",
            elapsed_ms=_elapsed(started),
            exception=exc.__class__.__name__,
            message=str(exc),
        )


def _restore(
    window: Win32Window | None,
    original: Win32Window | None,
    initial: dict[str, bool] | None,
) -> dict[str, Any]:
    started = time.perf_counter()
    errors: list[str] = []
    try:
        state_restored = window is None or initial is None
        if window is not None and initial is not None:
            if not initial["visible"]:
                flag = "hide"
                predicate = lambda state: not state["visible"]
            elif initial["iconic"]:
                flag = "minimize"
                predicate = lambda state: state["iconic"]
            elif initial["zoomed"]:
                flag = "maximize"
                predicate = lambda state: state["visible"] and state["zoomed"]
            else:
                flag = "normal"
                predicate = _normal
            window.set_state(flag)
            state_restored = _wait_state(_handle(window), predicate) is not None
            if not state_restored:
                errors.append("靶场初始显示状态未恢复")

        focus_restored = original is None
        if original is not None:
            original.activate()
            deadline = time.monotonic() + STATE_TIMEOUT_SECONDS
            while True:
                if original.is_active():
                    focus_restored = True
                    break
                if time.monotonic() >= deadline:
                    break
                time.sleep(0.05)
            if not focus_restored:
                errors.append("原前台窗口未恢复")

        passed = state_restored and focus_restored
        return _result(
            "resource_cleanup",
            "PASS" if passed else "FAIL",
            "靶场初始状态和原前台窗口均已恢复" if passed else "；".join(errors),
            elapsed_ms=_elapsed(started),
            state_restored=state_restored,
            focus_restored=focus_restored,
        )
    except Exception as exc:  # noqa: BLE001
        return _error_result("resource_cleanup", "恢复靶场状态或原前台窗口失败", started, exc)


def _print_header(*, color: bool) -> None:
    title = f"{CYAN}UIAutoma Win32 API 测试{RESET}" if color else "UIAutoma Win32 API 测试"
    print(title)
    print()
    print("  API     : uiautoma.win32.Win32Window.set_state")
    print(f"  测试窗口: {TARGET_TITLE}")
    print(f"  窗口类名: {TARGET_CLASS}")
    print(f"  目标进程: {TARGET_PROCESS}")
    print("  状态恢复: 测试结束后恢复靶场初始状态和原前台窗口")
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


def main() -> int:
    color = "NO_COLOR" not in os.environ and sys.stdout.isatty()
    _print_header(color=color)
    started = time.perf_counter()

    contract = _check_contract()
    initial_result, window, original, initial = _prepare()
    display_result = _check_display_states(window)
    maximize_result = _check_alias_group(
        "maximize_aliases",
        window,
        ("max", "maximize", "maximized"),
        lambda state: state["visible"] and state["zoomed"],
        "max、maximize、maximized 均返回 None 且窗口最大化",
    )
    minimize_result = _check_alias_group(
        "minimize_aliases",
        window,
        ("min", "minimize", "minimized"),
        lambda state: state["iconic"],
        "min、minimize、minimized 均返回 None 且窗口最小化",
    )
    hide_result = _check_hide(window)
    invalid_result = _check_invalid(window)
    cleanup_result = _restore(window, original, initial)
    results = [
        contract,
        initial_result,
        display_result,
        maximize_result,
        minimize_result,
        hide_result,
        invalid_result,
        cleanup_result,
    ]

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
