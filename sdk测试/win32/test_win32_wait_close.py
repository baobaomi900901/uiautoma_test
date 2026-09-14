r"""``uiautoma.win32.Win32Window.wait_close()`` 测试。

API 参数（不是测试脚本参数）::

    Win32Window.wait_close(timeout: float = 20) -> bool

``timeout`` 可按位置或关键字传入。默认值为 20 秒；``0`` 只检查一次；``-1``
表示无限等待；小于 ``-1`` 或非数字值会被拒绝。窗口在超时前关闭时返回
``True``，超时仍存在时返回 ``False``。

脚本使用已经运行的 Win32 靶场。先验证零超时和有限超时在窗口仍存在时返回
``False``，再在约 0.35 秒后通过原生 ``PostMessageW(WM_CLOSE)`` 关闭靶场，让
默认 ``wait_close()`` 真实等待并返回 ``True``。最后覆盖已关闭句柄的 ``-1`` 和
非法 timeout。测试会真实关闭靶场，且无法恢复。导入本模块不会连接 Runtime 或
关闭窗口。
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
FINITE_TIMEOUT_SECONDS = 0.5
DELAYED_CLOSE_SECONDS = 0.35
TIMER_JOIN_SECONDS = 2.0
WM_CLOSE = 0x0010

_USER32 = ctypes.WinDLL("user32", use_last_error=True)
_USER32.IsWindow.argtypes = [wintypes.HWND]
_USER32.IsWindow.restype = wintypes.BOOL
_USER32.PostMessageW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
_USER32.PostMessageW.restype = wintypes.BOOL
_USER32.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
_USER32.GetWindowThreadProcessId.restype = wintypes.DWORD

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
    "window_setup": "靶场窗口",
    "zero_timeout": "零超时检查",
    "finite_timeout": "有限超时",
    "default_wait": "默认等待关闭",
    "native_closed": "原生关闭确认",
    "infinite_closed": "无限等待值",
    "invalid_timeout": "非法超时",
    "resource_cleanup": "资源清理",
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


def _is_window(handle: int) -> bool:
    return bool(_USER32.IsWindow(wintypes.HWND(handle)))


def _process_id(handle: int) -> int:
    value = wintypes.DWORD()
    _USER32.GetWindowThreadProcessId(wintypes.HWND(handle), ctypes.byref(value))
    return int(value.value)


def _post_close(handle: int) -> bool:
    return bool(_USER32.PostMessageW(wintypes.HWND(handle), WM_CLOSE, 0, 0))


def _check_contract() -> dict[str, Any]:
    started = time.perf_counter()
    try:
        signature = inspect.signature(Win32Window.wait_close)
        timeout = signature.parameters.get("timeout")
        passed = (
            tuple(signature.parameters) == ("self", "timeout")
            and timeout is not None
            and timeout.kind is inspect.Parameter.POSITIONAL_OR_KEYWORD
            and timeout.default == 20
            and str(timeout.annotation) in {"float", "<class 'float'>"}
            and str(signature.return_annotation) in {"bool", "<class 'bool'>"}
        )
        return _result(
            "api_contract",
            "PASS" if passed else "FAIL",
            "timeout 为默认 20 的位置或关键字浮点参数，返回 bool"
            if passed else "公开签名与当前合同不一致",
            elapsed_ms=_elapsed(started),
            signature=str(signature),
        )
    except Exception as exc:  # noqa: BLE001
        return _error_result("api_contract", "无法检查公开签名", started, exc)


def _prepare() -> tuple[dict[str, Any], Win32Window | None, dict[str, int]]:
    started = time.perf_counter()
    context = {"handle": 0, "process_id": 0}
    try:
        target = win32.get(
            TARGET_TITLE,
            class_name=TARGET_CLASS,
            process_name=TARGET_PROCESS,
            timeout=5,
        )
        handle = _handle(target)
        if handle <= 0 or not _is_window(handle):
            raise RuntimeError("靶场没有有效窗口句柄")
        context = {"handle": handle, "process_id": _process_id(handle)}
        return (
            _result(
                "window_setup",
                "PASS",
                f"已获取仍在运行的靶场窗口，句柄 {handle}",
                elapsed_ms=_elapsed(started),
                **context,
            ),
            target,
            context,
        )
    except Exception as exc:  # noqa: BLE001
        return _error_result("window_setup", "获取靶场窗口失败", started, exc), None, context


def _wait_false(
    case_id: str,
    target: Win32Window | None,
    handle: int,
    call: Callable[[], bool],
    call_text: str,
    minimum_elapsed_ms: float,
) -> dict[str, Any]:
    started = time.perf_counter()
    if target is None or not _is_window(handle):
        return _blocked(case_id, "仍在运行的靶场窗口不可用")
    try:
        returned = call()
        elapsed_ms = _elapsed(started)
        native_exists = _is_window(handle)
        elapsed_ok = elapsed_ms >= minimum_elapsed_ms
        passed = type(returned) is bool and returned is False and native_exists and elapsed_ok
        return _result(
            case_id,
            "PASS" if passed else "FAIL",
            f"{call_text} 返回 False，窗口仍存在"
            if passed else f"{call_text} 的返回值、耗时或窗口状态不符合预期",
            elapsed_ms=elapsed_ms,
            returned=returned,
            native_exists=native_exists,
            minimum_elapsed_ms=minimum_elapsed_ms,
        )
    except Exception as exc:  # noqa: BLE001
        return _error_result(case_id, f"{call_text} 调用失败", started, exc)


def _wait_default_close(
    target: Win32Window | None,
    handle: int,
    ready: bool,
) -> dict[str, Any]:
    started = time.perf_counter()
    if not ready or target is None or not _is_window(handle):
        return _blocked("default_wait", "仍在运行的靶场窗口不可用")

    close_result: list[bool] = []
    close_error: list[BaseException] = []

    def close_after_delay() -> None:
        try:
            close_result.append(_post_close(handle))
        except BaseException as exc:  # noqa: BLE001
            close_error.append(exc)

    timer = threading.Timer(DELAYED_CLOSE_SECONDS, close_after_delay)
    timer.daemon = True
    timer.start()
    try:
        returned = target.wait_close()
        wait_elapsed_ms = _elapsed(started)
        timer.join(timeout=TIMER_JOIN_SECONDS)
        if close_error:
            raise close_error[0]
        native_exists = _is_window(handle)
        posted = close_result == [True]
        delayed_enough = wait_elapsed_ms >= DELAYED_CLOSE_SECONDS * 1000
        timer_completed = not timer.is_alive()
        passed = (
            type(returned) is bool
            and returned is True
            and not native_exists
            and posted
            and delayed_enough
            and timer_completed
        )
        return _result(
            "default_wait",
            "PASS" if passed else "FAIL",
            f"wait_close() 等待约 {wait_elapsed_ms:.1f}ms 后返回 True，靶场已关闭"
            if passed else "默认等待的返回值、耗时、关闭请求或窗口状态不符合预期",
            elapsed_ms=_elapsed(started),
            wait_elapsed_ms=wait_elapsed_ms,
            returned=returned,
            native_exists=native_exists,
            close_posted=posted,
            timer_completed=timer_completed,
        )
    except Exception as exc:  # noqa: BLE001
        return _error_result("default_wait", "wait_close() 延迟关闭测试失败", started, exc)
    finally:
        timer.cancel()


def _confirm_native_closed(handle: int, wait_succeeded: bool) -> dict[str, Any]:
    started = time.perf_counter()
    if not wait_succeeded:
        return _blocked("native_closed", "默认等待关闭用例未通过")
    native_exists = _is_window(handle)
    return _result(
        "native_closed",
        "PASS" if not native_exists else "FAIL",
        "IsWindow 返回 False，原靶场句柄已失效"
        if not native_exists else "IsWindow 仍返回 True，原靶场句柄仍有效",
        elapsed_ms=_elapsed(started),
        native_exists=native_exists,
    )


def _wait_infinite_closed(target: Win32Window | None, handle: int, ready: bool) -> dict[str, Any]:
    started = time.perf_counter()
    if not ready or target is None:
        return _blocked("infinite_closed", "已关闭窗口对象不可用")
    try:
        returned = target.wait_close(timeout=-1)
        native_exists = _is_window(handle)
        passed = type(returned) is bool and returned is True and not native_exists
        return _result(
            "infinite_closed",
            "PASS" if passed else "FAIL",
            "wait_close(timeout=-1) 对已关闭句柄立即返回 True"
            if passed else "无限等待值的返回值或窗口状态不符合预期",
            elapsed_ms=_elapsed(started),
            returned=returned,
            native_exists=native_exists,
        )
    except Exception as exc:  # noqa: BLE001
        return _error_result("infinite_closed", "wait_close(timeout=-1) 调用失败", started, exc)


def _check_invalid_timeout(target: Win32Window | None) -> dict[str, Any]:
    started = time.perf_counter()
    if target is None:
        return _blocked("invalid_timeout", "靶场窗口对象不可用")
    outcomes: list[dict[str, Any]] = []
    for value in (-2, "bad"):
        try:
            target.wait_close(value)  # type: ignore[arg-type]
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


def _cleanup(handle: int) -> dict[str, Any]:
    started = time.perf_counter()
    target_closed = handle > 0 and not _is_window(handle)
    return _result(
        "resource_cleanup",
        "PASS" if target_closed else "FAIL",
        "靶场窗口已关闭；未创建临时资源，未强制终止进程"
        if target_closed else "靶场窗口仍存在；脚本未强制终止进程",
        elapsed_ms=_elapsed(started),
        target_closed=target_closed,
        temporary_resources_created=False,
        forced_termination=False,
    )


def _print_header(context: dict[str, int], *, color: bool) -> None:
    title = f"{CYAN}UIAutoma Win32 API 测试{RESET}" if color else "UIAutoma Win32 API 测试"
    print(title)
    print()
    print("  API     : uiautoma.win32.Win32Window.wait_close")
    print(f"  测试窗口: {TARGET_TITLE}")
    print(f"  窗口类名: {TARGET_CLASS}")
    print(f"  目标进程: {TARGET_PROCESS}")
    if context["handle"]:
        print(f"  靶场句柄: {context['handle']} ({hex(context['handle'])})")
    if context["process_id"]:
        print(f"  PID     : {context['process_id']}")
    print(f"  延迟关闭: 默认等待用例在 {DELAYED_CLOSE_SECONDS:.2f} 秒后发送原生 WM_CLOSE")
    print("  注意    : 测试会真实关闭靶场，且无法恢复")
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
    setup, target, context = _prepare()
    ready = setup["status"] == "PASS"
    zero_timeout = _wait_false(
        "zero_timeout",
        target,
        context["handle"],
        lambda: target.wait_close(0),  # type: ignore[union-attr]
        "wait_close(0)",
        0.0,
    ) if ready else _blocked("zero_timeout", "靶场窗口不可用")
    finite_timeout = _wait_false(
        "finite_timeout",
        target,
        context["handle"],
        lambda: target.wait_close(timeout=FINITE_TIMEOUT_SECONDS),  # type: ignore[union-attr]
        "wait_close(timeout=0.5)",
        FINITE_TIMEOUT_SECONDS * 1000,
    ) if ready else _blocked("finite_timeout", "靶场窗口不可用")
    default_wait = _wait_default_close(
        target,
        context["handle"],
        ready and zero_timeout["status"] == "PASS" and finite_timeout["status"] == "PASS",
    )
    native_closed = _confirm_native_closed(
        context["handle"],
        default_wait["status"] == "PASS",
    )
    infinite_closed = _wait_infinite_closed(
        target,
        context["handle"],
        native_closed["status"] == "PASS",
    )
    invalid_timeout = _check_invalid_timeout(target)
    cleanup = _cleanup(context["handle"])
    results = [
        contract,
        setup,
        zero_timeout,
        finite_timeout,
        default_wait,
        native_closed,
        infinite_closed,
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
