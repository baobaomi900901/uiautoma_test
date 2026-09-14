r"""``uiautoma.win32.Win32Window.wait_active()`` 测试。

API 参数（不是测试脚本参数）::

    Win32Window.wait_active(timeout: float = 20) -> None

``timeout`` 可按位置或关键字传入。默认值为 20 秒；``0`` 只检查一次；``-1``
表示无限等待；小于 ``-1`` 或非数字值会被拒绝。窗口在超时前成为系统前台窗口
时返回 ``None``，超时抛出 ``UIAError``。

脚本使用已经运行的 Win32 靶场和运行脚本时的原前台窗口，覆盖默认、零超时、
有限等待、无限等待值及非法值。有限等待场景会在约 0.35 秒后自动激活靶场，
并通过 Windows ``GetForegroundWindow`` 独立核对。测试结束保持靶场运行，恢复其
初始显示状态和原前台窗口。导入本模块不会连接 Runtime 或切换焦点。
"""

from __future__ import annotations

import ctypes
import inspect
import os
import re
import sys
import threading
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
FOREGROUND_TIMEOUT_SECONDS = 2.0
DELAYED_ACTIVATION_SECONDS = 0.35
POSITIVE_WAIT_SECONDS = 2.0
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
CASE_WIDTH = 20
DETAIL_WIDTH = 72
DURATION_WIDTH = 8
TABLE_WIDTH = sum((PROGRESS_WIDTH, STATUS_WIDTH, CASE_WIDTH, DETAIL_WIDTH, DURATION_WIDTH, 8))

CASE_LABELS = {
    "api_contract": "API 合同",
    "window_setup": "窗口准备",
    "activate_target": "激活靶场",
    "default_timeout": "默认超时",
    "zero_active": "零超时已激活",
    "infinite_active": "无限等待值",
    "restore_original": "恢复原窗口",
    "zero_inactive": "零超时未激活",
    "positive_wait": "有限等待激活",
    "invalid_timeout": "非法超时",
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
        signature = inspect.signature(Win32Window.wait_active)
        timeout = signature.parameters.get("timeout")
        passed = (
            tuple(signature.parameters) == ("self", "timeout")
            and timeout is not None
            and timeout.kind is inspect.Parameter.POSITIONAL_OR_KEYWORD
            and timeout.default == 20
            and str(timeout.annotation) in {"float", "<class 'float'>"}
            and str(signature.return_annotation) in {"None", "<class 'NoneType'>"}
        )
        return _result(
            "api_contract",
            "PASS" if passed else "FAIL",
            "timeout 为默认 20 的位置或关键字浮点参数，返回 None"
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
                    "运行脚本时靶场已是前台窗口，无法准备未激活场景",
                    elapsed_ms=_elapsed(started),
                    **context,
                ),
                target,
                original,
                _native_state(target_handle),
                context,
            )
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
            _native_state(target_handle),
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


def _activate(
    case_id: str,
    window: Win32Window | None,
    expected_handle: int,
    ready: bool,
    success_detail: str,
) -> dict[str, Any]:
    started = time.perf_counter()
    if not ready or window is None or not _is_window(expected_handle):
        return _blocked(case_id, "待激活窗口不可用")
    try:
        returned = window.activate()
        foreground_ok = _wait_foreground(expected_handle)
        passed = returned is None and foreground_ok
        return _result(
            case_id,
            "PASS" if passed else "FAIL",
            success_detail if passed else "窗口未在超时前成为系统前台窗口",
            elapsed_ms=_elapsed(started),
            returned=returned,
            native_foreground=_foreground_handle(),
        )
    except Exception as exc:  # noqa: BLE001
        return _error_result(case_id, "激活窗口失败", started, exc)


def _wait_success(
    case_id: str,
    target: Win32Window | None,
    target_handle: int,
    call: Callable[[], None],
    call_text: str,
    ready: bool,
) -> dict[str, Any]:
    started = time.perf_counter()
    if not ready or target is None:
        return _blocked(case_id, "靶场未处于可测试的前台状态")
    try:
        returned = call()
        native_active = _foreground_handle() == target_handle
        passed = returned is None and native_active
        return _result(
            case_id,
            "PASS" if passed else "FAIL",
            f"{call_text} 在已激活状态返回 None"
            if passed else f"{call_text} 返回值或前台状态不符合预期",
            elapsed_ms=_elapsed(started),
            returned=returned,
            native_active=native_active,
        )
    except Exception as exc:  # noqa: BLE001
        return _error_result(case_id, f"{call_text} 调用失败", started, exc)


def _wait_zero_inactive(target: Win32Window | None, ready: bool) -> dict[str, Any]:
    started = time.perf_counter()
    if not ready or target is None:
        return _blocked("zero_inactive", "靶场未处于可测试的非前台状态")
    try:
        target.wait_active(timeout=0)
    except Exception as exc:  # noqa: BLE001
        passed = exc.__class__.__name__ == "UIAError"
        return _result(
            "zero_inactive",
            "PASS" if passed else "FAIL",
            "wait_active(timeout=0) 未激活时立即抛出 UIAError"
            if passed else "零超时抛出了非预期异常",
            elapsed_ms=_elapsed(started),
            exception=exc.__class__.__name__,
            message=str(exc),
        )
    return _result(
        "zero_inactive",
        "FAIL",
        "wait_active(timeout=0) 在未激活状态未抛出 UIAError",
        elapsed_ms=_elapsed(started),
    )


def _wait_positive_delayed(
    target: Win32Window | None,
    target_handle: int,
    ready: bool,
) -> dict[str, Any]:
    started = time.perf_counter()
    if not ready or target is None:
        return _blocked("positive_wait", "靶场未处于可等待的非前台状态")
    if _foreground_handle() == target_handle:
        return _result(
            "positive_wait",
            "FAIL",
            "有限等待开始前靶场仍是前台窗口，未形成真实等待条件",
            elapsed_ms=_elapsed(started),
        )

    activation_error: list[BaseException] = []

    def activate_after_delay() -> None:
        try:
            target.activate()
        except BaseException as exc:  # noqa: BLE001
            activation_error.append(exc)

    timer = threading.Timer(DELAYED_ACTIVATION_SECONDS, activate_after_delay)
    timer.daemon = True
    timer.start()
    try:
        returned = target.wait_active(POSITIVE_WAIT_SECONDS)
        wait_elapsed_ms = _elapsed(started)
        timer.join(timeout=FOREGROUND_TIMEOUT_SECONDS)
        if activation_error:
            raise activation_error[0]
        total_elapsed_ms = _elapsed(started)
        native_active = _foreground_handle() == target_handle
        delayed_enough = wait_elapsed_ms >= DELAYED_ACTIVATION_SECONDS * 1000
        activation_completed = not timer.is_alive()
        passed = returned is None and native_active and delayed_enough and activation_completed
        return _result(
            "positive_wait",
            "PASS" if passed else "FAIL",
            f"wait_active(2) 等待约 {wait_elapsed_ms:.1f}ms 后返回 None，靶场已激活"
            if passed else "有限等待的返回值、耗时或前台状态不符合预期",
            elapsed_ms=total_elapsed_ms,
            wait_elapsed_ms=wait_elapsed_ms,
            returned=returned,
            native_active=native_active,
            delayed_enough=delayed_enough,
            activation_completed=activation_completed,
        )
    except Exception as exc:  # noqa: BLE001
        return _error_result("positive_wait", "wait_active(2) 延迟激活测试失败", started, exc)
    finally:
        timer.cancel()


def _check_invalid_timeout(target: Win32Window | None) -> dict[str, Any]:
    started = time.perf_counter()
    if target is None:
        return _blocked("invalid_timeout", "靶场窗口不可用")
    outcomes: list[dict[str, Any]] = []
    for value in (-2, "bad"):
        try:
            target.wait_active(value)  # type: ignore[arg-type]
            outcomes.append({"timeout": value, "exception": None})
        except Exception as exc:  # noqa: BLE001
            outcomes.append({"timeout": value, "exception": exc.__class__.__name__, "message": str(exc)})
    passed = all(item["exception"] == "InvalidParamsError" for item in outcomes)
    return _result(
        "invalid_timeout",
        "PASS" if passed else "FAIL",
        "timeout=-2 和非数字值均被 InvalidParamsError 正确拒绝"
        if passed else "至少一个非法 timeout 未按 InvalidParamsError 拒绝",
        elapsed_ms=_elapsed(started),
        outcomes=outcomes,
    )


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
    print("  API     : uiautoma.win32.Win32Window.wait_active")
    print(f"  测试窗口: {TARGET_TITLE}")
    print(f"  窗口类名: {TARGET_CLASS}")
    print(f"  目标进程: {TARGET_PROCESS}")
    if context["target_handle"]:
        print(f"  靶场句柄: {context['target_handle']}")
    if context["original_handle"]:
        print(f"  原前台句柄: {context['original_handle']}")
    print(f"  延迟激活: 有限等待用例在 {DELAYED_ACTIVATION_SECONDS:.2f} 秒后激活靶场")
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
    if result.get("outcomes"):
        for outcome in result["outcomes"]:
            print(f"{indent}{outcome}")


def main() -> int:
    color = "NO_COLOR" not in os.environ and sys.stdout.isatty()
    started = time.perf_counter()
    contract = _check_contract()
    setup, target, original, target_state, context = _prepare()
    ready = setup["status"] == "PASS"

    activated = _activate(
        "activate_target",
        target,
        context["target_handle"],
        ready,
        "靶场已成为系统前台窗口",
    )
    target_active = activated["status"] == "PASS"
    default_timeout = _wait_success(
        "default_timeout",
        target,
        context["target_handle"],
        lambda: target.wait_active(),  # type: ignore[union-attr]
        "wait_active()",
        target_active,
    )
    zero_active = _wait_success(
        "zero_active",
        target,
        context["target_handle"],
        lambda: target.wait_active(0),  # type: ignore[union-attr]
        "wait_active(0)",
        target_active,
    )
    infinite_active = _wait_success(
        "infinite_active",
        target,
        context["target_handle"],
        lambda: target.wait_active(timeout=-1),  # type: ignore[union-attr]
        "wait_active(timeout=-1)",
        target_active,
    )

    restored = _activate(
        "restore_original",
        original,
        context["original_handle"],
        ready,
        "运行脚本前的前台窗口已恢复",
    )
    original_active = restored["status"] == "PASS"
    zero_inactive = _wait_zero_inactive(target, original_active)
    positive_wait = _wait_positive_delayed(
        target,
        context["target_handle"],
        original_active,
    )
    invalid_timeout = _check_invalid_timeout(target)
    cleanup = _cleanup(
        target,
        original,
        target_state,
        context["target_handle"],
        context["original_handle"],
    )
    results = [
        contract,
        setup,
        activated,
        default_timeout,
        zero_active,
        infinite_active,
        restored,
        zero_inactive,
        positive_wait,
        invalid_timeout,
        cleanup,
    ]

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
