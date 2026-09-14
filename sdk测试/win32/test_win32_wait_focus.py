r"""``uiautoma.win32.Win32Window.wait_focus()`` 真实窗口焦点测试。

API 参数（不是测试脚本参数）::

    Win32Window.wait_focus(timeout: float = 20) -> bool

参数规则：

* ``timeout``：位置或关键字参数，单位秒；默认 ``20``，``0`` 只检查一次，
  正数在期限内轮询，``-1`` 一直等待。
* 窗口在超时前获得焦点返回 ``True``，超时仍未聚焦返回 ``False``。
* 小于 ``-1`` 或非数字超时抛出 ``InvalidParamsError``。
* 窗口已失效抛出 ``ElementNotFoundError``；没有真实句柄的伪窗口抛出
  ``UnsupportedActionError``。

测试脚本参数：无。

脚本使用用户已经启动的 Win32 靶场和运行脚本时的原前台窗口。先验证靶场未聚焦时
零超时和 0.5 秒有限等待返回 ``False``，再在 0.35 秒后自动激活靶场，验证
``wait_focus(2)`` 真实等待后返回 ``True``。随后覆盖活动状态下的默认、零和无限
等待值，最后恢复原前台窗口。脚本不使用元素库，不关闭或修改靶场。

导入本模块不会连接 Runtime 或切换焦点。

运行方式::

    uv run .\win32\test_win32_wait_focus.py
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
FINITE_INACTIVE_SECONDS = 0.5
POLL_INTERVAL_SECONDS = 0.05

_USER32 = ctypes.WinDLL("user32", use_last_error=True)
_USER32.GetForegroundWindow.argtypes = []
_USER32.GetForegroundWindow.restype = wintypes.HWND
_USER32.IsWindow.argtypes = [wintypes.HWND]
_USER32.IsWindow.restype = wintypes.BOOL

STATUS_LABELS = {"PASS": "通过", "FAIL": "失败", "BLOCKED": "阻塞"}
COLORS = {"PASS": "\x1b[32m", "FAIL": "\x1b[31m", "BLOCKED": "\x1b[33m"}
CYAN = "\x1b[36m"
RESET = "\x1b[0m"

PROGRESS_WIDTH = 7
STATUS_WIDTH = 6
CASE_WIDTH = 20
DETAIL_WIDTH = 74
DURATION_WIDTH = 8
TABLE_WIDTH = sum((PROGRESS_WIDTH, STATUS_WIDTH, CASE_WIDTH, DETAIL_WIDTH, DURATION_WIDTH, 8))

CASE_LABELS = {
    "api_contract": "API 合同",
    "window_setup": "窗口准备",
    "zero_inactive": "零超时未聚焦",
    "finite_inactive": "有限等待未聚焦",
    "positive_wait": "延迟获得焦点",
    "default_active": "默认超时已聚焦",
    "zero_active": "零超时已聚焦",
    "infinite_active": "无限等待值",
    "invalid_timeout": "非法超时",
    "pseudo_window": "伪窗口",
    "restore_original": "恢复原窗口",
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


def _foreground_handle() -> int:
    return int(_USER32.GetForegroundWindow() or 0)


def _is_window(handle: int) -> bool:
    return bool(_USER32.IsWindow(wintypes.HWND(handle)))


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
        signature = inspect.signature(Win32Window.wait_focus)
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
            (
                "timeout 为默认 20 的位置或关键字浮点参数，返回 bool"
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
    Win32Window | None,
    Win32Window | None,
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
                    "运行脚本时靶场已是前台窗口，无法准备未聚焦场景",
                    elapsed_ms=_elapsed(started),
                    **context,
                ),
                target,
                original,
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
            context,
        )
    except Exception as exc:  # noqa: BLE001
        return (
            _error_result("window_setup", "获取靶场或原前台窗口失败", started, exc),
            None,
            None,
            context,
        )


def _wait_inactive(
    case_id: str,
    target: Win32Window | None,
    target_handle: int,
    ready: bool,
    timeout: float,
    *,
    positional: bool,
) -> dict[str, Any]:
    started = time.perf_counter()
    if not ready or target is None:
        return _blocked(case_id, "靶场未处于可测试的非前台状态")
    if _foreground_handle() == target_handle:
        return _result(
            case_id,
            "FAIL",
            "调用前靶场已经成为前台窗口",
            elapsed_ms=_elapsed(started),
        )
    try:
        returned = target.wait_focus(timeout) if positional else target.wait_focus(timeout=timeout)
        elapsed_ms = _elapsed(started)
        minimum = timeout * 800 if timeout > 0 else 0.0
        passed = returned is False and elapsed_ms >= minimum and _foreground_handle() != target_handle
        return _result(
            case_id,
            "PASS" if passed else "FAIL",
            (
                f"wait_focus({timeout:g}) 在未聚焦状态返回 False"
                if passed
                else "返回值、耗时或前台状态不符合预期"
            ),
            elapsed_ms=elapsed_ms,
            returned=returned,
            minimum_elapsed_ms=minimum,
            target_active=_foreground_handle() == target_handle,
        )
    except Exception as exc:  # noqa: BLE001
        return _error_result(case_id, "未聚焦等待调用失败", started, exc)


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
            "有限等待开始前靶场已经是前台窗口",
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
        returned = target.wait_focus(POSITIVE_WAIT_SECONDS)
        wait_elapsed_ms = _elapsed(started)
        timer.join(timeout=FOREGROUND_TIMEOUT_SECONDS)
        if activation_error:
            raise activation_error[0]
        native_active = _foreground_handle() == target_handle
        delayed_enough = wait_elapsed_ms >= DELAYED_ACTIVATION_SECONDS * 1000
        activation_completed = not timer.is_alive()
        passed = returned is True and native_active and delayed_enough and activation_completed
        return _result(
            "positive_wait",
            "PASS" if passed else "FAIL",
            (
                f"wait_focus(2) 等待约 {wait_elapsed_ms:.1f}ms 后返回 True，靶场已聚焦"
                if passed
                else "有限等待的返回值、耗时或前台状态不符合预期"
            ),
            elapsed_ms=_elapsed(started),
            wait_elapsed_ms=wait_elapsed_ms,
            returned=returned,
            native_active=native_active,
            activation_completed=activation_completed,
        )
    except Exception as exc:  # noqa: BLE001
        return _error_result("positive_wait", "wait_focus(2) 延迟聚焦测试失败", started, exc)
    finally:
        timer.cancel()


def _wait_active_case(
    case_id: str,
    target: Win32Window | None,
    target_handle: int,
    call: Callable[[], bool],
    call_text: str,
    ready: bool,
) -> dict[str, Any]:
    started = time.perf_counter()
    if not ready or target is None:
        return _blocked(case_id, "靶场未处于可测试的前台状态")
    try:
        returned = call()
        native_active = _foreground_handle() == target_handle
        passed = returned is True and native_active
        return _result(
            case_id,
            "PASS" if passed else "FAIL",
            (
                f"{call_text} 在已聚焦状态返回 True"
                if passed
                else f"{call_text} 返回值或前台状态不符合预期"
            ),
            elapsed_ms=_elapsed(started),
            returned=returned,
            native_active=native_active,
        )
    except Exception as exc:  # noqa: BLE001
        return _error_result(case_id, f"{call_text} 调用失败", started, exc)


def _check_invalid_timeout(target: Win32Window | None) -> dict[str, Any]:
    started = time.perf_counter()
    if target is None:
        return _blocked("invalid_timeout", "靶场窗口不可用")
    outcomes: list[dict[str, Any]] = []
    for value in (-2, "bad"):
        try:
            target.wait_focus(value)  # type: ignore[arg-type]
            outcomes.append({"timeout": value, "exception": None})
        except Exception as exc:  # noqa: BLE001
            outcomes.append(
                {"timeout": value, "exception": exc.__class__.__name__, "message": str(exc)}
            )
    passed = all(item["exception"] == "InvalidParamsError" for item in outcomes)
    return _result(
        "invalid_timeout",
        "PASS" if passed else "FAIL",
        (
            "timeout=-2 和非数字值均被 InvalidParamsError 正确拒绝"
            if passed
            else "至少一个非法 timeout 未按 InvalidParamsError 拒绝"
        ),
        elapsed_ms=_elapsed(started),
        outcomes=outcomes,
    )


def _check_pseudo_window() -> dict[str, Any]:
    started = time.perf_counter()
    pseudo = Win32Window(title="UIAutoma wait_focus pseudo window")
    try:
        pseudo.wait_focus(0)
    except Exception as exc:  # noqa: BLE001
        passed = exc.__class__.__name__ == "UnsupportedActionError"
        return _result(
            "pseudo_window",
            "PASS" if passed else "FAIL",
            (
                "没有真实句柄的伪窗口被 UnsupportedActionError 正确拒绝"
                if passed
                else "伪窗口抛出的异常类型不符合预期"
            ),
            elapsed_ms=_elapsed(started),
            exception=exc.__class__.__name__,
            message=str(exc),
        )
    return _result(
        "pseudo_window",
        "FAIL",
        "没有真实句柄的伪窗口未抛出异常",
        elapsed_ms=_elapsed(started),
    )


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
        restored = _wait_foreground(original_handle)
        passed = returned is None and restored
        return _result(
            "restore_original",
            "PASS" if passed else "FAIL",
            (
                "运行脚本前的前台窗口已恢复"
                if passed
                else "原前台窗口未在期限内恢复"
            ),
            elapsed_ms=_elapsed(started),
            returned=returned,
            foreground_handle=_foreground_handle(),
        )
    except Exception as exc:  # noqa: BLE001
        return _error_result("restore_original", "恢复原前台窗口失败", started, exc)


def _cleanup(
    target: Win32Window | None,
    original: Win32Window | None,
    target_handle: int,
    original_handle: int,
) -> dict[str, Any]:
    started = time.perf_counter()
    errors: list[str] = []
    try:
        target_alive = target is not None and _is_window(target_handle)
        if not target_alive:
            errors.append("靶场窗口已失效")

        focus_restored = original is None
        if original is not None and _is_window(original_handle):
            if _foreground_handle() != original_handle:
                original.activate()
            focus_restored = _wait_foreground(original_handle)
            if not focus_restored:
                errors.append("原前台窗口未恢复")
        elif original is not None:
            errors.append("原前台窗口已失效")

        passed = target_alive and focus_restored and not errors
        return _result(
            "resource_cleanup",
            "PASS" if passed else "FAIL",
            (
                "靶场保持运行，原前台窗口已恢复"
                if passed
                else "；".join(errors)
            ),
            elapsed_ms=_elapsed(started),
            target_alive=target_alive,
            focus_restored=focus_restored,
        )
    except Exception as exc:  # noqa: BLE001
        return _error_result("resource_cleanup", "最终恢复原前台窗口失败", started, exc)


def _print_header(context: dict[str, int], *, color: bool) -> None:
    title = f"{CYAN}UIAutoma Win32 API 测试{RESET}" if color else "UIAutoma Win32 API 测试"
    print(title)
    print()
    print("  API     : uiautoma.win32.Win32Window.wait_focus")
    print(f"  测试窗口: {TARGET_TITLE}")
    print(f"  窗口类名: {TARGET_CLASS}")
    print(f"  目标进程: {TARGET_PROCESS}")
    if context["target_handle"]:
        print(f"  靶场句柄: {context['target_handle']}")
    if context["original_handle"]:
        print(f"  原前台句柄: {context['original_handle']}")
    print(f"  延迟聚焦: 有限等待用例在 {DELAYED_ACTIVATION_SECONDS:.2f} 秒后激活靶场")
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
    setup, target, original, context = _prepare()
    ready = setup["status"] == "PASS"

    zero_inactive = _wait_inactive(
        "zero_inactive",
        target,
        context["target_handle"],
        ready,
        0,
        positional=False,
    )
    finite_inactive = _wait_inactive(
        "finite_inactive",
        target,
        context["target_handle"],
        ready and zero_inactive["status"] == "PASS",
        FINITE_INACTIVE_SECONDS,
        positional=True,
    )
    positive_wait = _wait_positive_delayed(
        target,
        context["target_handle"],
        ready and finite_inactive["status"] == "PASS",
    )
    target_active = positive_wait["status"] == "PASS"
    default_active = _wait_active_case(
        "default_active",
        target,
        context["target_handle"],
        lambda: target.wait_focus(),  # type: ignore[union-attr]
        "wait_focus()",
        target_active,
    )
    zero_active = _wait_active_case(
        "zero_active",
        target,
        context["target_handle"],
        lambda: target.wait_focus(timeout=0),  # type: ignore[union-attr]
        "wait_focus(timeout=0)",
        target_active,
    )
    infinite_active = _wait_active_case(
        "infinite_active",
        target,
        context["target_handle"],
        lambda: target.wait_focus(timeout=-1),  # type: ignore[union-attr]
        "wait_focus(timeout=-1)",
        target_active,
    )
    invalid_timeout = _check_invalid_timeout(target)
    pseudo_window = _check_pseudo_window()
    restore_original = _restore_original(
        original,
        context["original_handle"],
        ready,
    )
    cleanup = _cleanup(
        target,
        original,
        context["target_handle"],
        context["original_handle"],
    )
    results = [
        contract,
        setup,
        zero_inactive,
        finite_inactive,
        positive_wait,
        default_active,
        zero_active,
        infinite_active,
        invalid_timeout,
        pseudo_window,
        restore_original,
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
