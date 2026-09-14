r"""``uiautoma.win32.Win32Window.close()`` 测试。

API 参数（不是测试脚本参数）::

    Win32Window.close() -> None

``close()`` 没有 API 参数。它向真实顶层窗口异步发送关闭请求并返回 ``None``；
如果应用显示保存确认对话框，窗口可能继续存在。

测试脚本参数::

    --handle HANDLE

``--handle`` 为必填脚本参数，接受十进制或 ``0x`` 十六进制窗口句柄。脚本会真实
关闭该句柄对应的窗口，并通过 Windows ``IsWindow`` 独立确认原句柄失效。该操作
不可恢复，脚本不会重新启动或强制终止目标应用。导入本模块不会连接 Runtime 或
关闭窗口。
"""

from __future__ import annotations

import argparse
import ctypes
import inspect
import os
import re
import sys
import time
import unicodedata
from ctypes import wintypes
from typing import Any, Sequence

from uiautoma import win32
from uiautoma.win32 import Win32Window


__test__ = False

CLOSE_TIMEOUT_SECONDS = 5.0
POLL_INTERVAL_SECONDS = 0.05

_USER32 = ctypes.WinDLL("user32", use_last_error=True)
_USER32.IsWindow.argtypes = [wintypes.HWND]
_USER32.IsWindow.restype = wintypes.BOOL
_USER32.GetWindowTextLengthW.argtypes = [wintypes.HWND]
_USER32.GetWindowTextLengthW.restype = ctypes.c_int
_USER32.GetWindowTextW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
_USER32.GetWindowTextW.restype = ctypes.c_int
_USER32.GetClassNameW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
_USER32.GetClassNameW.restype = ctypes.c_int
_USER32.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
_USER32.GetWindowThreadProcessId.restype = wintypes.DWORD

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
    "handle_validation": "句柄校验",
    "window_binding": "窗口对象绑定",
    "close_request": "关闭请求",
    "window_closed": "窗口关闭确认",
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


def _parse_handle(value: str) -> int:
    text = value.strip()
    try:
        handle = int(text, 0)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("窗口句柄必须是十进制或 0x 十六进制整数") from exc
    if handle <= 0:
        raise argparse.ArgumentTypeError("窗口句柄必须大于 0")
    return handle


def _is_window(handle: int) -> bool:
    return bool(_USER32.IsWindow(wintypes.HWND(handle)))


def _window_metadata(handle: int) -> dict[str, Any]:
    hwnd = wintypes.HWND(handle)
    title_length = max(0, int(_USER32.GetWindowTextLengthW(hwnd)))
    title_buffer = ctypes.create_unicode_buffer(title_length + 1)
    _USER32.GetWindowTextW(hwnd, title_buffer, len(title_buffer))
    class_buffer = ctypes.create_unicode_buffer(512)
    _USER32.GetClassNameW(hwnd, class_buffer, len(class_buffer))
    process_id = wintypes.DWORD()
    _USER32.GetWindowThreadProcessId(hwnd, ctypes.byref(process_id))
    return {
        "title": title_buffer.value,
        "class_name": class_buffer.value,
        "process_id": int(process_id.value),
    }


def _handle_from_window(window: Win32Window) -> int:
    try:
        return int(window.raw.get("handle") or 0)
    except (TypeError, ValueError):
        return 0


def _check_contract() -> dict[str, Any]:
    started = time.perf_counter()
    try:
        signature = inspect.signature(Win32Window.close)
        passed = (
            tuple(signature.parameters) == ("self",)
            and str(signature.return_annotation) in {"None", "<class 'NoneType'>"}
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


def _validate_handle(handle: int) -> tuple[dict[str, Any], dict[str, Any] | None]:
    started = time.perf_counter()
    try:
        if not _is_window(handle):
            return (
                _result(
                    "handle_validation",
                    "BLOCKED",
                    "传入句柄不是当前有效窗口，请重新获取句柄后运行",
                    elapsed_ms=_elapsed(started),
                    handle=handle,
                ),
                None,
            )
        metadata = _window_metadata(handle)
        return (
            _result(
                "handle_validation",
                "PASS",
                f"句柄有效：{metadata['title'] or '<无标题>'}",
                elapsed_ms=_elapsed(started),
                handle=handle,
                **metadata,
            ),
            metadata,
        )
    except Exception as exc:  # noqa: BLE001
        return _error_result("handle_validation", "读取窗口句柄失败", started, exc), None


def _bind_window(handle: int, handle_ready: bool) -> tuple[dict[str, Any], Win32Window | None]:
    started = time.perf_counter()
    if not handle_ready:
        return _blocked("window_binding", "有效窗口句柄不可用"), None
    try:
        window = win32.get_by_handle(handle, timeout=5)
        actual_handle = _handle_from_window(window)
        passed = actual_handle == handle
        return (
            _result(
                "window_binding",
                "PASS" if passed else "FAIL",
                "get_by_handle() 已绑定传入窗口" if passed else "返回窗口句柄与传入值不一致",
                elapsed_ms=_elapsed(started),
                expected_handle=handle,
                actual_handle=actual_handle,
            ),
            window if passed else None,
        )
    except Exception as exc:  # noqa: BLE001
        return _error_result("window_binding", "get_by_handle() 绑定窗口失败", started, exc), None


def _send_close(window: Win32Window | None) -> dict[str, Any]:
    started = time.perf_counter()
    if window is None:
        return _blocked("close_request", "Win32Window 对象不可用")
    try:
        returned = window.close()
        passed = returned is None
        return _result(
            "close_request",
            "PASS" if passed else "FAIL",
            "close() 调用完成并返回 None" if passed else "close() 返回值不是 None",
            elapsed_ms=_elapsed(started),
            returned=returned,
        )
    except Exception as exc:  # noqa: BLE001
        return _error_result("close_request", "close() 调用失败", started, exc)


def _wait_until_closed(handle: int, request_succeeded: bool) -> dict[str, Any]:
    started = time.perf_counter()
    if not request_succeeded:
        return _blocked("window_closed", "关闭请求未成功发送")
    deadline = time.monotonic() + CLOSE_TIMEOUT_SECONDS
    while True:
        if not _is_window(handle):
            return _result(
                "window_closed",
                "PASS",
                "原窗口句柄已失效，窗口关闭完成",
                elapsed_ms=_elapsed(started),
                handle=handle,
            )
        if time.monotonic() >= deadline:
            return _result(
                "window_closed",
                "FAIL",
                "5 秒后句柄仍有效；应用可能显示了保存确认对话框",
                elapsed_ms=_elapsed(started),
                handle=handle,
            )
        time.sleep(POLL_INTERVAL_SECONDS)


def _cleanup(handle: int) -> dict[str, Any]:
    started = time.perf_counter()
    still_exists = _is_window(handle)
    return _result(
        "resource_cleanup",
        "PASS",
        "未创建临时资源；目标窗口已关闭"
        if not still_exists else "未创建临时资源；目标窗口仍存在，脚本未强制终止",
        elapsed_ms=_elapsed(started),
        target_still_exists=still_exists,
        forced_termination=False,
    )


def _print_header(handle: int, metadata: dict[str, Any] | None, *, color: bool) -> None:
    title = f"{CYAN}UIAutoma Win32 API 测试{RESET}" if color else "UIAutoma Win32 API 测试"
    print(title)
    print()
    print("  API     : uiautoma.win32.Win32Window.close")
    print(f"  输入句柄: {hex(handle)}")
    print(f"  十进制  : {handle}")
    if metadata is not None:
        print(f"  窗口标题: {metadata['title'] or '<无标题>'}")
        print(f"  窗口类名: {metadata['class_name'] or '<未知>'}")
        print(f"  PID     : {metadata['process_id']}")
    print("  注意    : 测试会真实关闭此窗口，且无法恢复")
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


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="测试 uiautoma.win32.Win32Window.close()；该操作会真实关闭目标窗口。"
    )
    parser.add_argument(
        "--handle",
        required=True,
        type=_parse_handle,
        help="必填窗口句柄，支持十进制或 0x 十六进制",
    )
    return parser


def run(handle: int) -> tuple[list[dict[str, Any]], dict[str, Any] | None]:
    contract = _check_contract()
    handle_result, metadata = _validate_handle(handle)
    binding, window = _bind_window(handle, handle_result["status"] == "PASS")
    close_request = _send_close(window)
    window_closed = _wait_until_closed(handle, close_request["status"] == "PASS")
    cleanup = _cleanup(handle)
    return [contract, handle_result, binding, close_request, window_closed, cleanup], metadata


def main(argv: Sequence[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    color = "NO_COLOR" not in os.environ and sys.stdout.isatty()
    started = time.perf_counter()
    results, metadata = run(args.handle)
    _print_header(args.handle, metadata, color=color)
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
