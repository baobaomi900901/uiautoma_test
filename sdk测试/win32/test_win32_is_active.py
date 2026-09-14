r"""``uiautoma.win32.Win32Window.is_active()`` 测试。

API 参数（不是测试脚本参数）::

    Win32Window.is_active() -> bool

``is_active()`` 没有 API 参数。窗口是系统前台窗口时返回 ``True``，否则返回
``False``。

脚本获取已经运行的 Win32 靶场和运行脚本时的原前台窗口。它先激活靶场并验证
``is_active() is True``，再恢复原前台窗口并验证靶场的 ``is_active() is False``。
两种结果均通过 Windows ``GetForegroundWindow`` 独立核对。测试结束保持靶场运行，
并兜底恢复靶场初始显示状态和原前台窗口。导入本模块不会连接 Runtime 或切换焦点。
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
FOREGROUND_TIMEOUT_SECONDS = 2.0
POLL_INTERVAL_SECONDS = 0.05

_USER32 = ctypes.WinDLL("user32", use_last_error=True)
_USER32.GetForegroundWindow.argtypes = []
_USER32.GetForegroundWindow.restype = wintypes.HWND
_USER32.IsWindow.argtypes = [wintypes.HWND]
_USER32.IsWindow.restype = wintypes.BOOL
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
DETAIL_WIDTH = 68
DURATION_WIDTH = 8
TABLE_WIDTH = sum((PROGRESS_WIDTH, STATUS_WIDTH, CASE_WIDTH, DETAIL_WIDTH, DURATION_WIDTH, 8))

CASE_LABELS = {
    "api_contract": "API 合同",
    "window_setup": "窗口准备",
    "activate_target": "激活靶场",
    "active_true": "前台状态",
    "restore_original": "恢复原窗口",
    "active_false": "非前台状态",
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


def _foreground_handle() -> int:
    return int(_USER32.GetForegroundWindow() or 0)


def _is_window(handle: int) -> bool:
    return bool(_USER32.IsWindow(wintypes.HWND(handle)))


def _native_state(handle: int) -> dict[str, bool]:
    hwnd = wintypes.HWND(handle)
    return {
        "visible": bool(_USER32.IsWindowVisible(hwnd)),
        "iconic": bool(_USER32.IsIconic(hwnd)),
        "zoomed": bool(_USER32.IsZoomed(hwnd)),
    }


def _wait_foreground(expected_handle: int) -> bool:
    deadline = time.monotonic() + FOREGROUND_TIMEOUT_SECONDS
    while True:
        if _foreground_handle() == expected_handle:
            return True
        if time.monotonic() >= deadline:
            return False
        time.sleep(POLL_INTERVAL_SECONDS)


def _check_contract() -> dict[str, Any]:
    started = time.perf_counter()
    try:
        signature = inspect.signature(Win32Window.is_active)
        passed = (
            tuple(signature.parameters) == ("self",)
            and str(signature.return_annotation) in {"bool", "<class 'bool'>"}
        )
        return _result(
            "api_contract",
            "PASS" if passed else "FAIL",
            "公开签名无参数并返回 bool" if passed else "公开签名与当前合同不一致",
            elapsed_ms=_elapsed(started),
            signature=str(signature),
        )
    except Exception as exc:  # noqa: BLE001
        return _error_result("api_contract", "无法检查公开签名", started, exc)


def _prepare() -> tuple[
    dict[str, Any],
    Win32Window | None,
    Win32Window | None,
    dict[str, bool] | None,
    dict[str, int],
]:
    started = time.perf_counter()
    context = {"target_handle": 0, "original_handle": 0}
    try:
        original = win32.get_active(timeout=5)
        target = win32.get(
            TARGET_TITLE,
            class_name=TARGET_CLASS,
            process_name=TARGET_PROCESS,
            timeout=5,
        )
        target_handle = _handle(target)
        original_handle = _handle(original)
        context = {"target_handle": target_handle, "original_handle": original_handle}
        if target_handle <= 0 or original_handle <= 0:
            raise RuntimeError("目标窗口或原前台窗口没有有效句柄")
        if target_handle == original_handle:
            return (
                _result(
                    "window_setup",
                    "BLOCKED",
                    "运行脚本时靶场已是前台窗口，无法准备独立的 False 状态",
                    elapsed_ms=_elapsed(started),
                    **context,
                ),
                target,
                original,
                _native_state(target_handle),
                context,
            )
        target_state = _native_state(target_handle)
        return (
            _result(
                "window_setup",
                "PASS",
                f"已获取靶场 {target_handle} 和原前台窗口 {original_handle}",
                elapsed_ms=_elapsed(started),
                **context,
            ),
            target,
            original,
            target_state,
            context,
        )
    except Exception as exc:  # noqa: BLE001
        return (
            _error_result("window_setup", "获取靶场或原前台窗口失败", started, exc),
            None,
            None,
            None,
            context,
        )


def _activate_target(target: Win32Window | None, target_handle: int, ready: bool) -> dict[str, Any]:
    started = time.perf_counter()
    if not ready or target is None:
        return _blocked("activate_target", "靶场或原前台窗口不可用")
    try:
        returned = target.activate()
        foreground_ok = _wait_foreground(target_handle)
        passed = returned is None and foreground_ok
        return _result(
            "activate_target",
            "PASS" if passed else "FAIL",
            "靶场已成为系统前台窗口" if passed else "靶场未在超时前成为系统前台窗口",
            elapsed_ms=_elapsed(started),
            returned=returned,
            native_foreground=_foreground_handle(),
        )
    except Exception as exc:  # noqa: BLE001
        return _error_result("activate_target", "激活靶场失败", started, exc)


def _check_is_active(
    case_id: str,
    target: Win32Window | None,
    target_handle: int,
    expected: bool,
    ready: bool,
) -> dict[str, Any]:
    started = time.perf_counter()
    if not ready or target is None:
        return _blocked(case_id, "目标窗口或预期前台状态不可用")
    try:
        actual = target.is_active()
        native_foreground = _foreground_handle()
        native_actual = native_foreground == target_handle
        passed = type(actual) is bool and actual is expected and native_actual is expected
        return _result(
            case_id,
            "PASS" if passed else "FAIL",
            f"is_active() 返回 {actual}，与 GetForegroundWindow 一致"
            if passed else "SDK 返回值与预期或 GetForegroundWindow 不一致",
            elapsed_ms=_elapsed(started),
            expected=expected,
            actual=actual,
            native_actual=native_actual,
            native_foreground=native_foreground,
        )
    except Exception as exc:  # noqa: BLE001
        return _error_result(case_id, "is_active() 调用失败", started, exc)


def _restore_original(
    original: Win32Window | None,
    original_handle: int,
    ready: bool,
) -> dict[str, Any]:
    started = time.perf_counter()
    if not ready or original is None or not _is_window(original_handle):
        return _blocked("restore_original", "原前台窗口不可用")
    try:
        returned = original.activate()
        foreground_ok = _wait_foreground(original_handle)
        passed = returned is None and foreground_ok
        return _result(
            "restore_original",
            "PASS" if passed else "FAIL",
            "运行脚本前的前台窗口已恢复" if passed else "原前台窗口未在超时前恢复",
            elapsed_ms=_elapsed(started),
            returned=returned,
            native_foreground=_foreground_handle(),
        )
    except Exception as exc:  # noqa: BLE001
        return _error_result("restore_original", "恢复原前台窗口失败", started, exc)


def _cleanup(
    target: Win32Window | None,
    original: Win32Window | None,
    target_state: dict[str, bool] | None,
    target_handle: int,
    original_handle: int,
) -> dict[str, Any]:
    started = time.perf_counter()
    errors: list[str] = []
    try:
        target_alive = target is not None and _is_window(target_handle)
        state_restored = not target_alive or target_state is None
        if target_alive and target is not None and target_state is not None:
            if not target_state["visible"]:
                target.set_state("hide")
                predicate = lambda state: not state["visible"]
            elif target_state["iconic"]:
                target.set_state("minimize")
                predicate = lambda state: state["iconic"]
            elif target_state["zoomed"]:
                target.set_state("maximize")
                predicate = lambda state: state["zoomed"]
            else:
                target.set_state("normal")
                predicate = lambda state: state["visible"] and not state["iconic"] and not state["zoomed"]
            deadline = time.monotonic() + FOREGROUND_TIMEOUT_SECONDS
            while True:
                if predicate(_native_state(target_handle)):
                    state_restored = True
                    break
                if time.monotonic() >= deadline:
                    errors.append("靶场初始显示状态未恢复")
                    break
                time.sleep(POLL_INTERVAL_SECONDS)

        focus_restored = original is None
        if original is not None and _is_window(original_handle):
            original.activate()
            focus_restored = _wait_foreground(original_handle)
            if not focus_restored:
                errors.append("原前台窗口未恢复")
        elif original is not None:
            errors.append("原前台窗口已失效")

        passed = target_alive and state_restored and focus_restored
        if not target_alive:
            errors.append("靶场窗口已失效")
        return _result(
            "resource_cleanup",
            "PASS" if passed else "FAIL",
            "靶场保持运行，初始显示状态和原前台窗口均已恢复"
            if passed else "；".join(errors),
            elapsed_ms=_elapsed(started),
            target_alive=target_alive,
            state_restored=state_restored,
            focus_restored=focus_restored,
        )
    except Exception as exc:  # noqa: BLE001
        return _error_result("resource_cleanup", "恢复靶场状态或原前台窗口失败", started, exc)


def _print_header(context: dict[str, int], *, color: bool) -> None:
    title = f"{CYAN}UIAutoma Win32 API 测试{RESET}" if color else "UIAutoma Win32 API 测试"
    print(title)
    print()
    print("  API     : uiautoma.win32.Win32Window.is_active")
    print(f"  测试窗口: {TARGET_TITLE}")
    print(f"  窗口类名: {TARGET_CLASS}")
    print(f"  目标进程: {TARGET_PROCESS}")
    if context["target_handle"]:
        print(f"  靶场句柄: {context['target_handle']}")
    if context["original_handle"]:
        print(f"  原前台句柄: {context['original_handle']}")
    print("  焦点恢复: 测试结束后恢复运行脚本前的前台窗口")
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
    if "expected" in result:
        print(f"{indent}{_pad('预期', 8)}: {result['expected']}")
        print(f"{indent}{_pad('SDK 实际', 8)}: {result.get('actual')}")
        print(f"{indent}{_pad('原生实际', 8)}: {result.get('native_actual')}")


def main() -> int:
    color = "NO_COLOR" not in os.environ and sys.stdout.isatty()
    started = time.perf_counter()
    contract = _check_contract()
    setup, target, original, target_state, context = _prepare()
    ready = setup["status"] == "PASS"
    activated = _activate_target(target, context["target_handle"], ready)
    active_true = _check_is_active(
        "active_true",
        target,
        context["target_handle"],
        True,
        activated["status"] == "PASS",
    )
    restored = _restore_original(original, context["original_handle"], ready)
    active_false = _check_is_active(
        "active_false",
        target,
        context["target_handle"],
        False,
        restored["status"] == "PASS",
    )
    cleanup = _cleanup(
        target,
        original,
        target_state,
        context["target_handle"],
        context["original_handle"],
    )
    results = [contract, setup, activated, active_true, restored, active_false, cleanup]

    _print_header(context, color=color)
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
