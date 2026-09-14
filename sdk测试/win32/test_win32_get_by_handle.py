"""``uiautoma.win32.get_by_handle()`` 持久化真实窗口测试。

API 参数（不是本测试脚本的命令行参数）::

    win32.get_by_handle(
        handle: int | str | None = None,
        *,
        timeout: float = 5,
    ) -> Win32Window

参数规则：

* ``handle``：语义上必填，支持正整数、十进制字符串和 ``0x`` 开头的十六进制
  字符串；``None``、空字符串、非整数、零和负数会抛出 ``InvalidParamsError``。
* ``timeout``：仅限关键字，单位秒；默认 ``5``，``0`` 只查一次，``-1`` 一直等待；
  小于 ``-1`` 会抛出 ``InvalidParamsError``。

有效句柄返回 ``Win32Window``；正数但已失效的句柄在超时后抛出
``ElementNotFoundError``。脚本运行前必须显式传入 ``--handle``，例如::

    uv run ./win32/test_win32_get_by_handle.py --handle 69740

脚本会用同一个有效句柄覆盖整数、十进制字符串、十六进制字符串、默认/零超时和
安全的无效参数矩阵。``timeout=-1`` 不自动执行，避免句柄失效时永久等待。测试只读，
不会激活、关闭或修改目标窗口。导入本模块不会连接 Runtime 或获取窗口。
"""

from __future__ import annotations

import argparse
import inspect
import json
import os
import re
import sys
import time
import unicodedata
from pathlib import Path
from typing import Any, Callable, Sequence

from uiautoma import ping
from uiautoma import win32
from uiautoma.win32 import Win32Window


__test__ = False

PRODUCT_ROOT = Path(__file__).resolve().parents[3]
INVALID_POSITIVE_HANDLES = (0x7FFFFFFF, 0x7FFFFFFE, 0x7FFFFFFD)

EXPECTED_PARAMETER_ORDER = ("handle", "timeout")
EXPECTED_DEFAULTS: dict[str, Any] = {"handle": None, "timeout": 5}
EXPECTED_KINDS = {
    "handle": inspect.Parameter.POSITIONAL_OR_KEYWORD,
    "timeout": inspect.Parameter.KEYWORD_ONLY,
}

LIVE_CASE_IDS = {
    "get_handle_int_default_timeout",
    "get_handle_decimal_string",
    "get_handle_hex_string",
    "get_timeout_zero",
    "get_invalid_handle_none",
    "get_invalid_handle_empty",
    "get_invalid_handle_non_numeric",
    "get_invalid_handle_zero",
    "get_invalid_handle_negative",
    "get_stale_positive_handle",
    "get_invalid_timeout",
}

BLOCKING_EXCEPTION_NAMES = {
    "ConnectionError",
    "EOFError",
    "HostUnavailableError",
    "PipeClosedError",
    "TimeoutError",
    "UnsupportedProtocolError",
}
BLOCKING_TRACES = {
    "native_host_unavailable",
    "web_bridge_unavailable",
    "web_host_unavailable",
    "web_ipc_unreachable",
    "web_runtime_incompatible",
}

CASE_LABELS = {
    "api_contract": "API 合同",
    "runtime_preflight": "Runtime",
    "get_handle_int_default_timeout": "整数句柄",
    "get_handle_decimal_string": "十进制字符串",
    "get_handle_hex_string": "十六进制字符串",
    "get_timeout_zero": "零超时查询",
    "get_invalid_handle_none": "空句柄",
    "get_invalid_handle_empty": "空字符串",
    "get_invalid_handle_non_numeric": "非数字字符串",
    "get_invalid_handle_zero": "零句柄",
    "get_invalid_handle_negative": "负数句柄",
    "get_stale_positive_handle": "失效句柄",
    "get_invalid_timeout": "非法超时",
    "owned_resources_cleanup": "资源清理",
    "scenario_orchestration": "测试编排",
}
STATUS_LABELS = {"PASS": "通过", "FAIL": "失败", "BLOCKED": "阻塞"}
ANSI_COLORS = {
    "green": "\x1b[32m",
    "red": "\x1b[31m",
    "yellow": "\x1b[33m",
    "cyan": "\x1b[36m",
}
ANSI_RESET = "\x1b[0m"

PROGRESS_WIDTH = 7
STATUS_WIDTH = 6
CASE_WIDTH = 16
DETAIL_WIDTH = 54
DURATION_WIDTH = 8
TABLE_WIDTH = PROGRESS_WIDTH + STATUS_WIDTH + CASE_WIDTH + DETAIL_WIDTH + DURATION_WIDTH + 8


def _result(case_id: str, status: str, detail: str, **extra: Any) -> dict[str, Any]:
    return {"case_id": case_id, "status": status, "detail": detail, **extra}


def _safe_trace(exc: BaseException) -> str:
    for attr in ("trace_info", "method"):
        trace = str(getattr(exc, attr, "") or "")
        if re.fullmatch(r"[A-Za-z0-9_.-]{1,80}", trace):
            return trace
    return ""


def _error_fields(exc: BaseException) -> dict[str, str]:
    return {
        "exception": exc.__class__.__name__,
        "trace_info": _safe_trace(exc),
        "message": str(exc),
    }


def _error_status(exc: BaseException) -> str:
    name = exc.__class__.__name__
    if name in BLOCKING_EXCEPTION_NAMES or _safe_trace(exc) in BLOCKING_TRACES:
        return "BLOCKED"
    if name == "UnsupportedActionError" and "Windows" in str(exc):
        return "BLOCKED"
    return "FAIL"


def colorize(text: str, color: str, *, enabled: bool) -> str:
    if not enabled:
        return text
    return f"{ANSI_COLORS[color]}{text}{ANSI_RESET}"


def display_width(text: str) -> int:
    """返回字符串在常见 Windows 终端中的显示宽度。"""

    plain = re.sub(r"\x1b\[[0-9;]*m", "", str(text))
    width = 0
    for character in plain:
        if unicodedata.combining(character):
            continue
        width += 2 if unicodedata.east_asian_width(character) in {"W", "F"} else 1
    return width


def pad_display(text: str, width: int, *, right: bool = False) -> str:
    value = str(text)
    padding = " " * max(0, width - display_width(value))
    return f"{padding}{value}" if right else f"{value}{padding}"


def _color_enabled(args: argparse.Namespace) -> bool:
    return (
        not args.json
        and not args.no_color
        and "NO_COLOR" not in os.environ
        and sys.stdout.isatty()
    )


def _print_header(args: argparse.Namespace, *, color: bool) -> None:
    print(colorize("UIAutoma Win32 API 测试", "cyan", enabled=color))
    print()
    print(f"  {pad_display('API', 8)}: uiautoma.win32.get_by_handle")
    print(f"  {pad_display('输入句柄', 8)}: {args.handle_input}")
    print(f"  {pad_display('十进制', 8)}: {args.handle}")
    print(f"  {pad_display('十六进制', 8)}: {hex(args.handle)}")
    print()
    print(
        f"{pad_display('进度', PROGRESS_WIDTH)}  "
        f"{pad_display('状态', STATUS_WIDTH)}  "
        f"{pad_display('测试项', CASE_WIDTH)}  "
        f"{pad_display('测试结果', DETAIL_WIDTH)}  "
        f"{pad_display('耗时', DURATION_WIDTH, right=True)}"
    )
    print(
        f"{'─' * PROGRESS_WIDTH}  "
        f"{'─' * STATUS_WIDTH}  "
        f"{'─' * CASE_WIDTH}  "
        f"{'─' * DETAIL_WIDTH}  "
        f"{'─' * DURATION_WIDTH}"
    )


def _print_case(result: dict[str, Any], index: int, total: int, *, color: bool) -> None:
    status = str(result.get("status") or "FAIL")
    status_text = STATUS_LABELS.get(status, status)
    status_color = {"PASS": "green", "FAIL": "red", "BLOCKED": "yellow"}.get(status, "red")
    badge = colorize(pad_display(f"[{status_text}]", STATUS_WIDTH), status_color, enabled=color)
    case_id = str(result.get("case_id") or "unknown")
    label = CASE_LABELS.get(case_id, case_id)
    detail = str(result.get("detail") or "")
    elapsed = result.get("elapsed_ms")
    duration = f"{float(elapsed):.1f}ms" if isinstance(elapsed, (int, float)) else "—"
    progress = f"{index:02d}/{total:02d}"
    print(
        f"{pad_display(progress, PROGRESS_WIDTH)}  "
        f"{badge}  "
        f"{pad_display(label, CASE_WIDTH)}  "
        f"{pad_display(detail, DETAIL_WIDTH)}  "
        f"{pad_display(duration, DURATION_WIDTH, right=True)}"
    )
    if status == "PASS":
        return
    indent = " " * (PROGRESS_WIDTH + STATUS_WIDTH + CASE_WIDTH + 6)
    if result.get("message"):
        print(f"{indent}{pad_display('原因', 10)}: {result['message']}")
    if result.get("exception"):
        print(f"{indent}{pad_display('异常', 10)}: {result['exception']}")
    if result.get("trace_info"):
        print(f"{indent}{pad_display('trace', 10)}: {result['trace_info']}")
    if result.get("call"):
        call = json.dumps(result["call"], ensure_ascii=False, separators=(",", ":"))
        print(f"{indent}{pad_display('调用参数', 10)}: {call}")


def _print_summary(report: dict[str, Any], *, color: bool) -> None:
    results = list(report.get("results") or [])
    counts = {
        status: sum(1 for item in results if item.get("status") == status)
        for status in ("PASS", "FAIL", "BLOCKED")
    }
    status = str(report.get("status") or "FAIL")
    title = {"PASS": "测试通过", "FAIL": "测试失败", "BLOCKED": "测试阻塞"}.get(status, "测试失败")
    title_color = {"PASS": "green", "FAIL": "red", "BLOCKED": "yellow"}.get(status, "red")
    parts = [f"{counts['PASS']}/{len(results)} 通过"]
    if counts["FAIL"]:
        parts.append(f"{counts['FAIL']} 失败")
    if counts["BLOCKED"]:
        parts.append(f"{counts['BLOCKED']} 阻塞")
    print("─" * TABLE_WIDTH)
    colored_title = colorize(title, title_color, enabled=color)
    print(
        f"{colored_title}  ·  {report.get('lifecycle', 'DRAFT')}  ·  "
        f"{'，'.join(parts)}  ·  {float(report.get('elapsed_ms') or 0):.1f}ms  ·  "
        f"退出码 {int(report.get('exit_code') or 0)}"
    )


def _window_handle(window: Win32Window) -> int:
    try:
        return int(window.get_detail("handle") or 0)
    except (TypeError, ValueError):
        return 0


def _window_snapshot(window: Win32Window) -> dict[str, Any]:
    return {
        "actual_handle": _window_handle(window),
        "actual_title": str(window.title or window.get_detail("title") or ""),
        "actual_class_name": str(window.class_name or window.get_detail("class_name") or ""),
        "actual_process_name": str(window.get_detail("process_name") or ""),
    }


def check_contract() -> dict[str, Any]:
    try:
        signature = inspect.signature(win32.get_by_handle)
        parameters = signature.parameters
        order_ok = tuple(parameters) == EXPECTED_PARAMETER_ORDER
        defaults_ok = all(parameters[name].default == value for name, value in EXPECTED_DEFAULTS.items())
        kinds_ok = all(parameters[name].kind == value for name, value in EXPECTED_KINDS.items())
        no_extra_ok = set(parameters) == set(EXPECTED_PARAMETER_ORDER)
        ann = signature.return_annotation
        ann_text = str(ann).replace("typing.", "")
        return_ok = (
            ann is Win32Window
            or ann_text in {"Win32Window", "uiautoma.win32.window.Win32Window"}
            or "Win32Window" in ann_text
        )
        passed = order_ok and defaults_ok and kinds_ok and return_ok and no_extra_ok
        return _result(
            "api_contract",
            "PASS" if passed else "FAIL",
            "公开签名符合当前合同" if passed else "公开签名与当前合同不一致",
            signature=str(signature),
            parameter_order_ok=order_ok,
            defaults_ok=defaults_ok,
            parameter_kinds_ok=kinds_ok,
            return_annotation_ok=return_ok,
            no_extra_parameters_ok=no_extra_ok,
            return_annotation=str(ann),
        )
    except Exception as exc:  # noqa: BLE001
        return _result("api_contract", "FAIL", "无法检查公开签名", **_error_fields(exc))


def preflight_runtime(timeout: float) -> dict[str, Any]:
    started = time.perf_counter()
    try:
        ping(timeout=timeout)
        return _result(
            "runtime_preflight",
            "PASS",
            "Runtime 与 Automation Pipe 可响应",
            elapsed_ms=round((time.perf_counter() - started) * 1000, 1),
        )
    except Exception as exc:  # noqa: BLE001
        return _result(
            "runtime_preflight",
            "BLOCKED",
            "Runtime 或 Automation Pipe 不可用",
            elapsed_ms=round((time.perf_counter() - started) * 1000, 1),
            **_error_fields(exc),
        )


def run_valid_handle_case(
    case_id: str,
    detail: str,
    *,
    handle_value: int | str,
    expected_handle: int,
    timeout: float | None,
) -> dict[str, Any]:
    started = time.perf_counter()
    keyword: dict[str, Any] = {}
    if timeout is not None:
        keyword["timeout"] = timeout
    call = {"handle": handle_value, **keyword}
    try:
        window = win32.get_by_handle(handle_value, **keyword)
        snapshot = _window_snapshot(window)
        checks = {
            "return_type_ok": isinstance(window, Win32Window),
            "handle_ok": snapshot["actual_handle"] == expected_handle and snapshot["actual_handle"] > 0,
        }
        passed = all(checks.values())
        return _result(
            case_id,
            "PASS" if passed else "FAIL",
            detail if passed else "返回窗口的类型或句柄不符合预期",
            elapsed_ms=round((time.perf_counter() - started) * 1000, 1),
            call=call,
            expected_handle=expected_handle,
            **checks,
            **snapshot,
        )
    except Exception as exc:  # noqa: BLE001
        status = _error_status(exc)
        return _result(
            case_id,
            status,
            "调用被环境阻塞" if status == "BLOCKED" else "获取有效句柄失败",
            elapsed_ms=round((time.perf_counter() - started) * 1000, 1),
            call=call,
            expected_handle=expected_handle,
            **_error_fields(exc),
        )


def run_expected_error_case(
    case_id: str,
    success_detail: str,
    *,
    handle_value: Any,
    expected_exception: str,
    timeout: float | None,
) -> dict[str, Any]:
    started = time.perf_counter()
    keyword: dict[str, Any] = {}
    if timeout is not None:
        keyword["timeout"] = timeout
    call = {"handle": handle_value, **keyword}
    try:
        win32.get_by_handle(handle_value, **keyword)
    except Exception as exc:  # noqa: BLE001
        passed = exc.__class__.__name__ == expected_exception
        return _result(
            case_id,
            "PASS" if passed else _error_status(exc),
            success_detail if passed else "抛出的异常类型不符合预期",
            elapsed_ms=round((time.perf_counter() - started) * 1000, 1),
            call=call,
            expected_exception=expected_exception,
            **_error_fields(exc),
        )
    return _result(
        case_id,
        "FAIL",
        f"未抛出预期的 {expected_exception}",
        elapsed_ms=round((time.perf_counter() - started) * 1000, 1),
        call=call,
        expected_exception=expected_exception,
    )


def _stale_positive_handle(input_handle: int) -> int:
    return next(candidate for candidate in INVALID_POSITIVE_HANDLES if candidate != input_handle)


def cleanup_resources() -> dict[str, Any]:
    return _result(
        "owned_resources_cleanup",
        "PASS",
        "本次未创建可拥有资源（只读获取，不关闭目标窗口）",
        confirmed=True,
        attempted_count=0,
        cleaned_count=0,
        resources=[],
    )


def _invocation_command(argv: Sequence[str] | None = None) -> str:
    args = list(argv if argv is not None else sys.argv[1:])
    try:
        script = Path(__file__).resolve().relative_to(PRODUCT_ROOT).as_posix()
    except ValueError:
        script = Path(__file__).as_posix()
    quoted = " ".join(_shell_quote(part) for part in args)
    base = f"uv run python -X utf8 {script}"
    return f"{base} {quoted}".rstrip()


def _shell_quote(value: str) -> str:
    if re.fullmatch(r"[A-Za-z0-9_./:\\-]+", value):
        return value
    return json.dumps(value, ensure_ascii=False)


def _exit_code(results: Sequence[dict[str, Any]]) -> int:
    statuses = {str(item.get("status") or "FAIL") for item in results}
    return 1 if "FAIL" in statuses else (2 if "BLOCKED" in statuses else 0)


def _report(
    args: argparse.Namespace,
    results: Sequence[dict[str, Any]],
    *,
    command: str,
) -> tuple[dict[str, Any], int]:
    exit_code = _exit_code(results)
    status = "FAIL" if exit_code == 1 else ("BLOCKED" if exit_code == 2 else "PASS")
    passed_ids = {
        str(item.get("case_id"))
        for item in results
        if item.get("status") == "PASS"
    }
    cleanup_pass = "owned_resources_cleanup" in passed_ids
    if status == "PASS" and LIVE_CASE_IDS <= passed_ids and cleanup_pass:
        lifecycle = "VERIFIED"
    elif "api_contract" in passed_ids:
        lifecycle = "READY_FOR_LIVE"
    else:
        lifecycle = "DRAFT"
    return (
        {
            "api": "uiautoma.win32.get_by_handle",
            "lifecycle": lifecycle,
            "status": status,
            "exit_code": exit_code,
            "command": command,
            "target": {
                "input": args.handle_input,
                "decimal": args.handle,
                "hex": hex(args.handle),
            },
            "timeout": args.timeout,
            "results": list(results),
            "excluded": [
                "timeout=-1 无限等待（避免目标窗口失效时脚本永久挂起）",
                "元素库绑定（窗口级 API 不要求 Package）",
                "关闭、激活或修改目标窗口",
            ],
            "notes": [
                "运行前必须显式传入 --handle",
                "同一有效句柄覆盖整数、十进制字符串和十六进制字符串",
            ],
        },
        exit_code,
    )


def run(
    args: argparse.Namespace,
    *,
    command: str,
    on_result: Callable[[dict[str, Any], int, int], None] | None = None,
) -> tuple[dict[str, Any], int]:
    results: list[dict[str, Any]] = []
    total = 1 if args.contract_only else 14

    def record(result: dict[str, Any]) -> None:
        results.append(result)
        if on_result is not None:
            on_result(result, len(results), total)

    record(check_contract())
    if results[-1]["status"] != "PASS" or args.contract_only:
        return _report(args, results, command=command)

    record(preflight_runtime(args.runtime_timeout))
    if results[-1]["status"] != "PASS":
        return _report(args, results, command=command)

    handle = args.handle
    valid_cases = [
        (
            "get_handle_int_default_timeout",
            "整数句柄及默认超时返回原窗口",
            handle,
            None,
        ),
        (
            "get_handle_decimal_string",
            "十进制字符串句柄返回原窗口",
            str(handle),
            args.timeout,
        ),
        (
            "get_handle_hex_string",
            "十六进制字符串句柄返回原窗口",
            hex(handle),
            args.timeout,
        ),
        (
            "get_timeout_zero",
            "零等待单次查询返回已存在窗口",
            handle,
            0,
        ),
    ]
    invalid_cases = [
        ("get_invalid_handle_none", "None 句柄被正确拒绝", None, "InvalidParamsError", None),
        ("get_invalid_handle_empty", "空字符串句柄被正确拒绝", "", "InvalidParamsError", None),
        (
            "get_invalid_handle_non_numeric",
            "非数字字符串句柄被正确拒绝",
            "not-a-handle",
            "InvalidParamsError",
            None,
        ),
        ("get_invalid_handle_zero", "零句柄被正确拒绝", 0, "InvalidParamsError", None),
        ("get_invalid_handle_negative", "负数句柄被正确拒绝", -1, "InvalidParamsError", None),
        (
            "get_stale_positive_handle",
            "失效正数句柄被识别为未找到窗口",
            _stale_positive_handle(handle),
            "ElementNotFoundError",
            0,
        ),
        (
            "get_invalid_timeout",
            "小于 -1 的超时值被正确拒绝",
            handle,
            "InvalidParamsError",
            -2,
        ),
    ]

    try:
        for case_id, detail, handle_value, timeout in valid_cases:
            record(
                run_valid_handle_case(
                    case_id,
                    detail,
                    handle_value=handle_value,
                    expected_handle=handle,
                    timeout=timeout,
                )
            )
        for case_id, detail, handle_value, expected_exception, timeout in invalid_cases:
            record(
                run_expected_error_case(
                    case_id,
                    detail,
                    handle_value=handle_value,
                    expected_exception=expected_exception,
                    timeout=timeout,
                )
            )
    except Exception as exc:  # noqa: BLE001
        record(_result("scenario_orchestration", "FAIL", "真实场景编排失败", **_error_fields(exc)))
    finally:
        record(cleanup_resources())
    return _report(args, results, command=command)


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="使用必填窗口句柄验证 uiautoma.win32.get_by_handle() 的全部 API 参数。"
    )
    parser.add_argument(
        "--handle",
        dest="handle_input",
        required=True,
        help="当前有效窗口句柄，支持十进制或 0x 十六进制。",
    )
    parser.add_argument("--timeout", type=float, default=5.0, help="有限等待用例超时秒数，默认 5。")
    parser.add_argument("--runtime-timeout", type=float, default=5.0, help="Runtime ping 超时秒数，默认 5。")
    parser.add_argument("--contract-only", action="store_true", help="只检查公开签名，仍必须传入 --handle。")
    parser.add_argument("--json", action="store_true", help="只输出无颜色的完整 JSON 结果。")
    parser.add_argument("--no-color", action="store_true", help="显示友好摘要，但关闭状态颜色。")
    args = parser.parse_args(argv)
    args.handle_input = str(args.handle_input).strip()
    try:
        args.handle = int(args.handle_input, 0)
    except ValueError:
        parser.error(f"--handle 必须是十进制或 0x 十六进制正整数：{args.handle_input!r}")
    if args.handle <= 0:
        parser.error(f"--handle 必须大于 0：{args.handle_input!r}")
    if args.timeout < 0:
        parser.error("--timeout 必须大于或等于 0；本脚本不自动执行无限等待")
    if args.runtime_timeout <= 0:
        parser.error("--runtime-timeout 必须大于 0")
    return args


def main(argv: Sequence[str] | None = None) -> int:
    raw_argv = list(argv) if argv is not None else sys.argv[1:]
    args = parse_args(raw_argv)
    command = _invocation_command(raw_argv)
    color = _color_enabled(args)
    on_result = None
    if not args.json:
        _print_header(args, color=color)
        on_result = lambda result, index, total: _print_case(
            result,
            index,
            total,
            color=color,
        )
    started = time.perf_counter()
    report, exit_code = run(args, command=command, on_result=on_result)
    report["elapsed_ms"] = round((time.perf_counter() - started) * 1000, 1)
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        _print_summary(report, color=color)
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
