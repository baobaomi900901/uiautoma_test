r"""``uiautoma.win32.Win32Window.get_detail()`` 测试。

API 参数（不是测试脚本参数）::

    Win32Window.get_detail(operation: str = "") -> Any

``operation`` 为空时返回完整详情字典。支持 ``title``、``text``、
``class_name``、``process_name``、``process_id``、``handle``、``rect``，
以及 ``class``/``classname``、``process``、``pid``、``hwnd``、
``bounding`` 别名；未知键返回空字符串。

脚本读取已经运行的 Win32 靶场窗口，只调用 ``get_detail()`` 获取信息，不激活、
移动、关闭或修改靶场程序。导入本模块不会连接 Runtime 或获取窗口。
"""

from __future__ import annotations

import inspect
import os
import re
import sys
import time
import unicodedata
from typing import Any, Callable

from uiautoma import win32
from uiautoma.win32 import Win32Window


__test__ = False

TARGET_TITLE = "Win32 靶场 - UIA"
TARGET_CLASS = "XPathWin32ShootingRange"
TARGET_PROCESS = "win32-shooting-range-uia.exe"

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
    "full_detail": "完整详情",
    "title_text": "标题与文本",
    "class_aliases": "类名及别名",
    "process_aliases": "进程名及别名",
    "pid_aliases": "进程 ID 及别名",
    "handle_aliases": "句柄及别名",
    "rect_aliases": "矩形及别名",
    "unknown_operation": "未知详情键",
    "resource_cleanup": "资源清理",
}

BLOCKING_EXCEPTION_NAMES = {
    "ConnectionError",
    "EOFError",
    "ElementNotFoundError",
    "HostUnavailableError",
    "PipeClosedError",
    "TimeoutError",
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


def _blocked(case_id: str) -> dict[str, Any]:
    return _result(case_id, "BLOCKED", "Win32 靶场窗口不可用", elapsed_ms=0.0)


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


def _rect_size(rect: object) -> tuple[int, int] | None:
    if not isinstance(rect, dict):
        return None
    try:
        width = int(rect.get("w", rect.get("width", 0)) or 0)
        height = int(rect.get("h", rect.get("height", 0)) or 0)
        if width <= 0 and "left" in rect and "right" in rect:
            width = int(rect["right"]) - int(rect["left"])
        if height <= 0 and "top" in rect and "bottom" in rect:
            height = int(rect["bottom"]) - int(rect["top"])
        return (width, height) if width > 0 and height > 0 else None
    except (TypeError, ValueError):
        return None


def _check_contract() -> dict[str, Any]:
    started = time.perf_counter()
    try:
        signature = inspect.signature(Win32Window.get_detail)
        parameters = signature.parameters
        operation = parameters.get("operation")
        passed = (
            tuple(parameters) == ("self", "operation")
            and operation is not None
            and operation.kind is inspect.Parameter.POSITIONAL_OR_KEYWORD
            and operation.default == ""
            and str(operation.annotation) in {"str", "<class 'str'>"}
            and str(signature.return_annotation) in {"Any", "typing.Any"}
        )
        return _result(
            "api_contract",
            "PASS" if passed else "FAIL",
            (
                '公开签名为 get_detail(operation: str = "") -> Any'
                if passed
                else "公开签名与当前合同不一致"
            ),
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
        raw = window.raw
        handle = int(raw.get("handle") or 0)
        process_name = str(raw.get("process_name") or "")
        passed = (
            isinstance(window, Win32Window)
            and window.title == TARGET_TITLE
            and window.class_name == TARGET_CLASS
            and process_name.casefold() == TARGET_PROCESS.casefold()
            and handle > 0
        )
        return (
            _result(
                "target_window",
                "PASS" if passed else "FAIL",
                (
                    f"已获取 Win32 靶场窗口，句柄 {handle}"
                    if passed
                    else "返回窗口与 Win32 靶场身份不一致"
                ),
                elapsed_ms=_elapsed(started),
                handle=handle,
                process_name=process_name,
            ),
            window if passed else None,
        )
    except Exception as exc:  # noqa: BLE001
        return _error_result("target_window", "获取 Win32 靶场窗口失败", started, exc), None


def _run_case(
    case_id: str,
    operation: Callable[[], tuple[bool, str, dict[str, Any]]],
) -> dict[str, Any]:
    started = time.perf_counter()
    try:
        passed, detail, extra = operation()
        return _result(
            case_id,
            "PASS" if passed else "FAIL",
            detail,
            elapsed_ms=_elapsed(started),
            **extra,
        )
    except Exception as exc:  # noqa: BLE001
        return _error_result(case_id, "get_detail() 调用失败", started, exc)


def _full_detail(window: Win32Window) -> tuple[bool, str, dict[str, Any]]:
    default_detail = window.get_detail()
    explicit_empty = window.get_detail("")
    required = {"handle", "title", "text", "class_name", "process_id", "process_name", "rect"}
    missing = sorted(required - set(default_detail)) if isinstance(default_detail, dict) else sorted(required)
    passed = (
        isinstance(default_detail, dict)
        and default_detail == explicit_empty
        and not missing
        and int(default_detail.get("handle") or 0) > 0
        and int(default_detail.get("process_id") or 0) > 0
        and _rect_size(default_detail.get("rect")) is not None
    )
    return (
        passed,
        "默认调用和显式空字符串均返回含 7 个标准字段的详情字典"
        if passed
        else "完整详情字典的字段、类型或值不符合合同",
        {"value": default_detail, "missing": missing},
    )


def _title_text(window: Win32Window, full: dict[str, Any]) -> tuple[bool, str, dict[str, Any]]:
    title = window.get_detail(" TITLE ")
    text = window.get_detail("text")
    passed = (
        title == TARGET_TITLE
        and isinstance(text, str)
        and title == full.get("title")
        and text == full.get("text")
    )
    return passed, "title 支持大小写与空白归一化，text 与完整详情一致", {"title": title, "text": text}


def _equal_aliases(
    window: Win32Window,
    full: dict[str, Any],
    canonical: str,
    aliases: tuple[str, ...],
) -> tuple[Any, dict[str, Any]]:
    values = {name: window.get_detail(name) for name in (canonical, *aliases)}
    expected = full.get(canonical)
    return expected, values


def _class_aliases(window: Win32Window, full: dict[str, Any]) -> tuple[bool, str, dict[str, Any]]:
    expected, values = _equal_aliases(window, full, "class_name", ("class", "classname"))
    passed = expected == TARGET_CLASS and all(value == expected for value in values.values())
    return passed, "class_name、class、classname 均返回靶场窗口类名", {"values": values}


def _process_aliases(window: Win32Window, full: dict[str, Any]) -> tuple[bool, str, dict[str, Any]]:
    expected, values = _equal_aliases(window, full, "process_name", ("process",))
    passed = str(expected).casefold() == TARGET_PROCESS.casefold() and all(
        value == expected for value in values.values()
    )
    return passed, "process_name 与 process 均返回靶场进程名", {"values": values}


def _pid_aliases(window: Win32Window, full: dict[str, Any]) -> tuple[bool, str, dict[str, Any]]:
    expected, values = _equal_aliases(window, full, "process_id", ("pid",))
    passed = isinstance(expected, int) and expected > 0 and all(
        value == expected for value in values.values()
    )
    return passed, f"process_id 与 pid 均返回 {expected}", {"values": values}


def _handle_aliases(window: Win32Window, full: dict[str, Any]) -> tuple[bool, str, dict[str, Any]]:
    expected, values = _equal_aliases(window, full, "handle", ("hwnd",))
    passed = isinstance(expected, int) and expected > 0 and all(
        value == expected for value in values.values()
    )
    return passed, f"handle 与 hwnd 均返回 {expected}", {"values": values}


def _rect_aliases(window: Win32Window, full: dict[str, Any]) -> tuple[bool, str, dict[str, Any]]:
    expected, values = _equal_aliases(window, full, "rect", ("bounding",))
    size = _rect_size(expected)
    passed = size is not None and all(value == expected for value in values.values())
    detail = f"rect 与 bounding 均返回有效矩形 {size[0]} × {size[1]}" if passed else "矩形或别名结果不一致"
    return passed, detail, {"values": values, "size": size}


def _unknown_operation(window: Win32Window) -> tuple[bool, str, dict[str, Any]]:
    value = window.get_detail("uiautoma_unknown_detail_key")
    return value == "", "未知详情键返回空字符串", {"value": value}


def _print_header(*, color: bool) -> None:
    title = f"{CYAN}UIAutoma Win32 API 测试{RESET}" if color else "UIAutoma Win32 API 测试"
    print(title)
    print()
    print("  API     : uiautoma.win32.Win32Window.get_detail")
    print(f"  测试窗口: {TARGET_TITLE}")
    print(f"  窗口类名: {TARGET_CLASS}")
    print(f"  目标进程: {TARGET_PROCESS}")
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
    if result.get("missing"):
        print(f"{indent}{_pad('缺少字段', 8)}: {', '.join(result['missing'])}")
    if "values" in result:
        print(f"{indent}{_pad('实际值', 8)}: {result['values']}")


def main() -> int:
    color = "NO_COLOR" not in os.environ and sys.stdout.isatty()
    _print_header(color=color)
    started = time.perf_counter()
    results = [_check_contract()]
    target_result, window = _get_target_window()
    results.append(target_result)

    if window is None:
        results.extend(_blocked(case_id) for case_id in list(CASE_LABELS)[2:-1])
    else:
        full_result = _run_case("full_detail", lambda: _full_detail(window))
        results.append(full_result)
        full = full_result.get("value") if isinstance(full_result.get("value"), dict) else {}
        operations: tuple[tuple[str, Callable[[], tuple[bool, str, dict[str, Any]]]], ...] = (
            ("title_text", lambda: _title_text(window, full)),
            ("class_aliases", lambda: _class_aliases(window, full)),
            ("process_aliases", lambda: _process_aliases(window, full)),
            ("pid_aliases", lambda: _pid_aliases(window, full)),
            ("handle_aliases", lambda: _handle_aliases(window, full)),
            ("rect_aliases", lambda: _rect_aliases(window, full)),
            ("unknown_operation", lambda: _unknown_operation(window)),
        )
        results.extend(_run_case(case_id, operation) for case_id, operation in operations)

    results.append(
        _result(
            "resource_cleanup",
            "PASS",
            "测试只读；未创建资源，Win32 靶场保持运行",
            elapsed_ms=0.0,
        )
    )
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
