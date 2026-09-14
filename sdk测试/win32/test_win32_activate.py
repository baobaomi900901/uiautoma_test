r"""``uiautoma.win32.Win32Window.activate()`` 测试。

API 参数（不是测试脚本参数）::

    Win32Window.activate() -> None

高层 ``activate()`` 没有公开参数，要求 ``Win32Window`` 绑定真实顶层窗口句柄。
它会恢复被最小化的窗口并尝试将其置于系统前台，成功返回 ``None``。

脚本记录运行前的前台窗口，激活已经运行的 Win32 靶场并校验前台状态，随后
调用原窗口的 ``activate()`` 恢复焦点。最终清理阶段会再次尽力恢复原窗口。
导入本模块不会连接 Runtime 或改变窗口焦点。
"""

from __future__ import annotations

import inspect
import os
import re
import sys
import time
import unicodedata
from typing import Any

from uiautoma import win32
from uiautoma.win32 import Win32Window


__test__ = False

TARGET_TITLE = "Win32 靶场 - UIA"
TARGET_CLASS = "XPathWin32ShootingRange"
TARGET_PROCESS = "win32-shooting-range-uia.exe"
FOCUS_TIMEOUT_SECONDS = 2.0

STATUS_LABELS = {"PASS": "通过", "FAIL": "失败", "BLOCKED": "阻塞"}
COLORS = {"PASS": "\x1b[32m", "FAIL": "\x1b[31m", "BLOCKED": "\x1b[33m"}
CYAN = "\x1b[36m"
RESET = "\x1b[0m"

PROGRESS_WIDTH = 7
STATUS_WIDTH = 6
CASE_WIDTH = 18
DETAIL_WIDTH = 62
DURATION_WIDTH = 8
TABLE_WIDTH = sum(
    (PROGRESS_WIDTH, STATUS_WIDTH, CASE_WIDTH, DETAIL_WIDTH, DURATION_WIDTH, 8)
)

CASE_LABELS = {
    "api_contract": "API 合同",
    "target_window": "靶场窗口",
    "original_foreground": "原前台窗口",
    "activate_target": "激活靶场",
    "target_foreground": "前台状态",
    "restore_original": "恢复原窗口",
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


def _wait_active(window: Win32Window, timeout: float = FOCUS_TIMEOUT_SECONDS) -> bool:
    deadline = time.monotonic() + max(0.0, timeout)
    while True:
        if window.is_active():
            return True
        if time.monotonic() >= deadline:
            return False
        time.sleep(0.05)


def _check_contract() -> dict[str, Any]:
    started = time.perf_counter()
    try:
        signature = inspect.signature(Win32Window.activate)
        parameters = signature.parameters
        self_parameter = parameters.get("self")
        return_annotation = str(signature.return_annotation)
        passed = (
            tuple(parameters) == ("self",)
            and self_parameter is not None
            and self_parameter.kind is inspect.Parameter.POSITIONAL_OR_KEYWORD
            and self_parameter.default is inspect.Parameter.empty
            and return_annotation in {"None", "<class 'NoneType'>"}
        )
        return _result(
            "api_contract",
            "PASS" if passed else "FAIL",
            "公开签名无参数并返回 None" if passed else "公开签名与当前合同不一致",
            elapsed_ms=_elapsed(started),
            signature=str(signature),
        )
    except Exception as exc:  # noqa: BLE001
        return _error_result("api_contract", "无法检查公开签名", started, exc)


def _get_target_window() -> tuple[dict[str, Any], Win32Window | None]:
    started = time.perf_counter()
    try:
        window = win32.get(
            TARGET_TITLE,
            class_name=TARGET_CLASS,
            process_name=TARGET_PROCESS,
            timeout=5,
        )
        handle = _handle(window)
        passed = isinstance(window, Win32Window) and handle > 0
        return (
            _result(
                "target_window",
                "PASS" if passed else "FAIL",
                f"已获取 Win32 靶场窗口，句柄 {handle}" if passed else "靶场窗口没有真实句柄",
                elapsed_ms=_elapsed(started),
                handle=handle,
            ),
            window if passed else None,
        )
    except Exception as exc:  # noqa: BLE001
        return _error_result("target_window", "获取 Win32 靶场窗口失败", started, exc), None


def _get_original_foreground(
    target: Win32Window | None,
) -> tuple[dict[str, Any], Win32Window | None]:
    started = time.perf_counter()
    if target is None:
        return _blocked("original_foreground", "靶场窗口不可用"), None
    try:
        original = win32.get_active(timeout=5)
        original_handle = _handle(original)
        target_handle = _handle(target)
        passed = original_handle > 0 and original_handle != target_handle
        return (
            _result(
                "original_foreground",
                "PASS" if passed else "BLOCKED",
                (
                    f"已记录原前台窗口，句柄 {original_handle}"
                    if passed
                    else "Win32 靶场已是前台，无法验证焦点切换"
                ),
                elapsed_ms=_elapsed(started),
                handle=original_handle,
                title=original.title or "",
            ),
            original if passed else None,
        )
    except Exception as exc:  # noqa: BLE001
        return _error_result("original_foreground", "读取原前台窗口失败", started, exc), None


def _activate_target(target: Win32Window | None, original: Win32Window | None) -> dict[str, Any]:
    started = time.perf_counter()
    if target is None or original is None:
        return _blocked("activate_target", "目标窗口或原前台窗口不可用")
    try:
        returned = target.activate()
        passed = returned is None
        return _result(
            "activate_target",
            "PASS" if passed else "FAIL",
            "target.activate() 调用完成并返回 None" if passed else "activate() 返回值不是 None",
            elapsed_ms=_elapsed(started),
            returned=returned,
        )
    except Exception as exc:  # noqa: BLE001
        return _error_result("activate_target", "target.activate() 调用失败", started, exc)


def _check_target_foreground(target: Win32Window | None, activated: bool) -> dict[str, Any]:
    started = time.perf_counter()
    if target is None or not activated:
        return _blocked("target_foreground", "靶场激活调用未成功")
    try:
        passed = _wait_active(target)
        return _result(
            "target_foreground",
            "PASS" if passed else "FAIL",
            "Win32 靶场已成为系统前台窗口" if passed else "等待 2 秒后靶场仍不是前台窗口",
            elapsed_ms=_elapsed(started),
            target_handle=_handle(target),
        )
    except Exception as exc:  # noqa: BLE001
        return _error_result("target_foreground", "检查靶场前台状态失败", started, exc)


def _restore_original(original: Win32Window | None) -> dict[str, Any]:
    started = time.perf_counter()
    if original is None:
        return _blocked("restore_original", "原前台窗口不可用")
    try:
        returned = original.activate()
        active = _wait_active(original)
        passed = returned is None and active
        return _result(
            "restore_original",
            "PASS" if passed else "FAIL",
            "原前台窗口已恢复且 activate() 返回 None" if passed else "原前台窗口恢复失败",
            elapsed_ms=_elapsed(started),
            returned=returned,
            original_handle=_handle(original),
        )
    except Exception as exc:  # noqa: BLE001
        return _error_result("restore_original", "恢复原前台窗口失败", started, exc)


def _cleanup(original: Win32Window | None) -> dict[str, Any]:
    started = time.perf_counter()
    if original is None:
        return _result(
            "resource_cleanup",
            "PASS",
            "未记录原窗口；测试未创建资源，靶场保持运行",
            elapsed_ms=_elapsed(started),
        )
    try:
        if not original.is_active():
            original.activate()
        restored = _wait_active(original)
        return _result(
            "resource_cleanup",
            "PASS" if restored else "FAIL",
            (
                "原前台窗口已恢复；测试未创建资源，靶场保持运行"
                if restored
                else "最终仍未能恢复原前台窗口"
            ),
            elapsed_ms=_elapsed(started),
        )
    except Exception as exc:  # noqa: BLE001
        return _error_result("resource_cleanup", "最终恢复原前台窗口失败", started, exc)


def _print_header(*, color: bool) -> None:
    title = f"{CYAN}UIAutoma Win32 API 测试{RESET}" if color else "UIAutoma Win32 API 测试"
    print(title)
    print()
    print("  API     : uiautoma.win32.Win32Window.activate")
    print(f"  测试窗口: {TARGET_TITLE}")
    print(f"  窗口类名: {TARGET_CLASS}")
    print(f"  目标进程: {TARGET_PROCESS}")
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


def main() -> int:
    color = "NO_COLOR" not in os.environ and sys.stdout.isatty()
    _print_header(color=color)
    started = time.perf_counter()

    contract = _check_contract()
    target_result, target = _get_target_window()
    original_result, original = _get_original_foreground(target)
    activate_result = _activate_target(target, original)
    active_result = _check_target_foreground(target, activate_result["status"] == "PASS")
    restore_result = _restore_original(original)
    cleanup_result = _cleanup(original)
    results = [
        contract,
        target_result,
        original_result,
        activate_result,
        active_result,
        restore_result,
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
