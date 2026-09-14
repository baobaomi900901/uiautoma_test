"""``uiautoma.win32.minimize_all()`` 持久化真实桌面测试。

API 参数（不是本测试脚本的命令行参数）::

    win32.minimize_all() -> None

参数规则：

* ``minimize_all()`` 没有 API 参数。
* 成功时返回 ``None``；仅支持 Windows，不支持的平台会抛出
  ``UnsupportedActionError``。
* 实现等价于 ``Win+D``，具有切换语义：第一次显示桌面并最小化窗口，第二次恢复。

本脚本只使用微信窗口作为观测样本。``--title``、``--class-name``、
``--process-name``、``--timeout``、``--settle-seconds`` 和
``--runtime-timeout`` 都是测试脚本参数，不是 ``minimize_all()`` 的 API 参数。
脚本先确保微信未最小化，再验证第一次调用后的最小化状态和第二次调用后的恢复状态；
最终清理会在必要时通过 ``set_state("restore")`` 兜底恢复微信窗口。

运行方式::

    uv run ./win32/test_win32_minimize_all.py

导入本模块不会连接 Runtime、切换桌面或修改窗口状态。
"""

from __future__ import annotations

import argparse
import ctypes
import inspect
import json
import os
import re
import sys
import time
import unicodedata
from ctypes import wintypes
from pathlib import Path
from typing import Any, Callable, Sequence

from uiautoma import ping, win32
from uiautoma.win32 import Win32Window


__test__ = False

PRODUCT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_TITLE = "微信"
DEFAULT_CLASS_NAME = "Qt51514QWindowIcon"
DEFAULT_PROCESS_NAME = "Weixin.exe"
TOTAL_CASES = 6

EXPECTED_PARAMETER_ORDER: tuple[str, ...] = ()
LIVE_CASE_IDS = {"minimize_all_effect", "minimize_all_toggle_restore"}

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
    "sample_setup": "微信窗口准备",
    "minimize_all_effect": "最小化全部",
    "minimize_all_toggle_restore": "切换恢复",
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
DETAIL_WIDTH = 58
DURATION_WIDTH = 8
TABLE_WIDTH = (
    PROGRESS_WIDTH
    + STATUS_WIDTH
    + CASE_WIDTH
    + DETAIL_WIDTH
    + DURATION_WIDTH
    + 8
)

_user32 = ctypes.WinDLL("user32", use_last_error=True)
_user32.IsIconic.argtypes = [wintypes.HWND]
_user32.IsIconic.restype = wintypes.BOOL


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
    print(f"  {pad_display('API', 8)}: uiautoma.win32.minimize_all")
    print(f"  {pad_display('测试对象', 8)}: {args.title}")
    print(f"  {pad_display('类名', 8)}: {args.class_name}")
    print(f"  {pad_display('进程', 8)}: {args.process_name}")
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
    badge = colorize(
        pad_display(f"[{status_text}]", STATUS_WIDTH),
        status_color,
        enabled=color,
    )
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


def _print_summary(report: dict[str, Any], *, color: bool) -> None:
    results = list(report.get("results") or [])
    counts = {
        status: sum(1 for item in results if item.get("status") == status)
        for status in ("PASS", "FAIL", "BLOCKED")
    }
    status = str(report.get("status") or "FAIL")
    title = {
        "PASS": "测试通过",
        "FAIL": "测试失败",
        "BLOCKED": "测试阻塞",
    }.get(status, "测试失败")
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


def _same_text(actual: object, expected: str) -> bool:
    return str(actual or "").strip().casefold() == expected.strip().casefold()


def _window_handle(window: Win32Window) -> int:
    try:
        return int(window.get_detail("handle") or 0)
    except (TypeError, ValueError):
        return 0


def _is_iconic(handle: int) -> bool:
    if handle <= 0:
        return False
    return bool(_user32.IsIconic(wintypes.HWND(handle)))


def check_contract() -> dict[str, Any]:
    try:
        signature = inspect.signature(win32.minimize_all)
        parameters = signature.parameters
        order_ok = tuple(parameters) == EXPECTED_PARAMETER_ORDER
        no_extra_ok = len(parameters) == 0
        annotation = signature.return_annotation
        annotation_text = str(annotation).replace("typing.", "")
        return_ok = annotation is None or annotation_text in {"None", "NoneType"}
        passed = order_ok and no_extra_ok and return_ok
        return _result(
            "api_contract",
            "PASS" if passed else "FAIL",
            "公开签名符合当前合同" if passed else "公开签名与当前合同不一致",
            signature=str(signature),
            parameter_order_ok=order_ok,
            no_extra_parameters_ok=no_extra_ok,
            return_annotation_ok=return_ok,
            return_annotation=str(annotation),
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


def prepare_sample_window(args: argparse.Namespace) -> tuple[dict[str, Any], dict[str, Any] | None]:
    started = time.perf_counter()
    try:
        window = win32.get(
            args.title,
            args.class_name,
            False,
            process_name=args.process_name,
            timeout=args.timeout,
        )
        handle = _window_handle(window)
        if handle <= 0:
            return (
                _result(
                    "sample_setup",
                    "FAIL",
                    "无法解析有效微信窗口句柄",
                    elapsed_ms=round((time.perf_counter() - started) * 1000, 1),
                ),
                None,
            )
        was_iconic = _is_iconic(handle)
        if was_iconic:
            window.set_state("restore")
            time.sleep(args.settle_seconds)
        actual_title = str(window.title or window.get_detail("title") or "")
        actual_class_name = str(window.class_name or window.get_detail("class_name") or "")
        actual_process_name = str(window.get_detail("process_name") or "")
        still_iconic = _is_iconic(handle)
        checks = {
            "return_type_ok": isinstance(window, Win32Window),
            "handle_ok": handle > 0,
            "title_ok": _same_text(actual_title, args.title),
            "class_name_ok": _same_text(actual_class_name, args.class_name),
            "process_name_ok": _same_text(actual_process_name, args.process_name),
            "restored_ok": not still_iconic,
        }
        passed = all(checks.values())
        sample = {
            "window": window,
            "handle": handle,
            "actual_title": actual_title,
            "actual_class_name": actual_class_name,
            "actual_process_name": actual_process_name,
        }
        return (
            _result(
                "sample_setup",
                "PASS" if passed else "FAIL",
                "微信窗口已就绪且未最小化" if passed else "微信窗口准备结果不符合预期",
                elapsed_ms=round((time.perf_counter() - started) * 1000, 1),
                was_iconic=was_iconic,
                is_iconic=still_iconic,
                **checks,
                **{key: value for key, value in sample.items() if key != "window"},
            ),
            sample if passed else None,
        )
    except Exception as exc:  # noqa: BLE001
        status = _error_status(exc)
        if exc.__class__.__name__ == "ElementNotFoundError":
            status = "FAIL"
        return (
            _result(
                "sample_setup",
                status,
                "查找或恢复微信窗口失败",
                elapsed_ms=round((time.perf_counter() - started) * 1000, 1),
                **_error_fields(exc),
            ),
            None,
        )


def run_minimize_all_case(sample: dict[str, Any], *, settle_seconds: float) -> dict[str, Any]:
    started = time.perf_counter()
    try:
        return_value = win32.minimize_all()
        time.sleep(settle_seconds)
        iconic = _is_iconic(int(sample["handle"]))
        return_ok = return_value is None
        passed = return_ok and iconic
        return _result(
            "minimize_all_effect",
            "PASS" if passed else "FAIL",
            "返回 None，微信窗口已最小化" if passed else "返回值或微信最小化状态不符合预期",
            elapsed_ms=round((time.perf_counter() - started) * 1000, 1),
            call_completed=True,
            return_is_none=return_ok,
            is_iconic=iconic,
            handle=int(sample["handle"]),
        )
    except Exception as exc:  # noqa: BLE001
        status = _error_status(exc)
        return _result(
            "minimize_all_effect",
            status,
            "minimize_all 被环境阻塞" if status == "BLOCKED" else "minimize_all 调用失败",
            elapsed_ms=round((time.perf_counter() - started) * 1000, 1),
            call_completed=False,
            **_error_fields(exc),
        )


def run_toggle_restore_case(sample: dict[str, Any], *, settle_seconds: float) -> dict[str, Any]:
    started = time.perf_counter()
    try:
        return_value = win32.minimize_all()
        time.sleep(settle_seconds)
        iconic = _is_iconic(int(sample["handle"]))
        return_ok = return_value is None
        passed = return_ok and not iconic
        return _result(
            "minimize_all_toggle_restore",
            "PASS" if passed else "FAIL",
            "再次返回 None，微信窗口已切换恢复" if passed else "第二次调用未恢复微信窗口",
            elapsed_ms=round((time.perf_counter() - started) * 1000, 1),
            call_completed=True,
            return_is_none=return_ok,
            is_iconic=iconic,
            handle=int(sample["handle"]),
        )
    except Exception as exc:  # noqa: BLE001
        status = _error_status(exc)
        return _result(
            "minimize_all_toggle_restore",
            status,
            "恢复调用被环境阻塞" if status == "BLOCKED" else "第二次 minimize_all 调用失败",
            elapsed_ms=round((time.perf_counter() - started) * 1000, 1),
            call_completed=False,
            **_error_fields(exc),
        )


def cleanup_resources(sample: dict[str, Any] | None, *, settle_seconds: float) -> dict[str, Any]:
    if sample is None:
        return _result(
            "owned_resources_cleanup",
            "PASS",
            "未获取微信样本窗口，无需恢复",
            confirmed=True,
            attempted_count=0,
            cleaned_count=0,
            resources=[],
        )
    handle = int(sample["handle"])
    if not _is_iconic(handle):
        return _result(
            "owned_resources_cleanup",
            "PASS",
            "微信窗口已处于恢复状态",
            confirmed=True,
            attempted_count=0,
            cleaned_count=0,
            resources=[{"kind": "window", "handle": handle, "status": "already_restored"}],
        )
    try:
        window = sample.get("window")
        if window is None:
            window = win32.get_by_handle(handle, timeout=2)
        window.set_state("restore")
        time.sleep(settle_seconds)
        iconic = _is_iconic(handle)
        return _result(
            "owned_resources_cleanup",
            "PASS" if not iconic else "FAIL",
            "已通过 set_state 恢复微信窗口" if not iconic else "微信窗口仍处于最小化",
            confirmed=not iconic,
            attempted_count=1,
            cleaned_count=0 if iconic else 1,
            resources=[
                {
                    "kind": "window",
                    "handle": handle,
                    "status": "still_iconic" if iconic else "restored_by_set_state",
                }
            ],
        )
    except Exception as exc:  # noqa: BLE001
        return _result(
            "owned_resources_cleanup",
            "FAIL",
            "恢复微信窗口失败",
            confirmed=False,
            attempted_count=1,
            cleaned_count=0,
            resources=[{"kind": "window", "handle": handle, "status": "restore_failed"}],
            **_error_fields(exc),
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
            "api": "uiautoma.win32.minimize_all",
            "lifecycle": lifecycle,
            "status": status,
            "exit_code": exit_code,
            "command": command,
            "target": {
                "title": args.title,
                "class_name": args.class_name,
                "process_name": args.process_name,
            },
            "settle_seconds": args.settle_seconds,
            "results": list(results),
            "excluded": [
                "微信以外的桌面窗口枚举与状态断言",
                "用户在两次 Win+D 调用之间主动切换桌面状态",
                "非 Windows 平台",
            ],
            "notes": [
                "minimize_all 没有 API 参数；命令行选项均为测试脚本参数",
                "第一次调用验证最小化，第二次调用验证 Win+D 切换恢复",
                "IsIconic 仅用于观测，不是公开 SDK API",
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
    total = 1 if args.contract_only else TOTAL_CASES
    sample: dict[str, Any] | None = None

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

    try:
        setup_result, sample = prepare_sample_window(args)
        record(setup_result)
        if sample is not None:
            effect = run_minimize_all_case(sample, settle_seconds=args.settle_seconds)
            record(effect)
            if effect["status"] == "PASS":
                record(run_toggle_restore_case(sample, settle_seconds=args.settle_seconds))
    except Exception as exc:  # noqa: BLE001
        record(
            _result(
                "scenario_orchestration",
                "FAIL",
                "真实场景编排失败",
                **_error_fields(exc),
            )
        )
    finally:
        record(cleanup_resources(sample, settle_seconds=args.settle_seconds))
    return _report(args, results, command=command)


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="使用微信窗口验证 uiautoma.win32.minimize_all() 的 Win+D 切换行为。"
    )
    parser.add_argument("--title", default=DEFAULT_TITLE, help=f"微信窗口标题，默认 {DEFAULT_TITLE}。")
    parser.add_argument(
        "--class-name",
        default=DEFAULT_CLASS_NAME,
        help=f"微信窗口类名，默认 {DEFAULT_CLASS_NAME}。",
    )
    parser.add_argument(
        "--process-name",
        default=DEFAULT_PROCESS_NAME,
        help=f"微信进程名，默认 {DEFAULT_PROCESS_NAME}。",
    )
    parser.add_argument("--timeout", type=float, default=5.0, help="查找微信窗口的超时秒数，默认 5。")
    parser.add_argument(
        "--settle-seconds",
        type=float,
        default=0.8,
        help="每次 Win+D 后等待窗口状态稳定的秒数，默认 0.8。",
    )
    parser.add_argument("--runtime-timeout", type=float, default=5.0, help="Runtime ping 超时秒数，默认 5。")
    parser.add_argument("--contract-only", action="store_true", help="只检查公开签名，不连接 Runtime 或切换桌面。")
    parser.add_argument("--json", action="store_true", help="只输出无颜色的完整 JSON 结果。")
    parser.add_argument("--no-color", action="store_true", help="显示友好摘要，但关闭状态颜色。")
    args = parser.parse_args(argv)
    args.title = str(args.title).strip()
    args.class_name = str(args.class_name).strip()
    args.process_name = str(args.process_name).strip()
    if not args.title:
        parser.error("--title 不能为空")
    if not args.class_name:
        parser.error("--class-name 不能为空")
    if not args.process_name:
        parser.error("--process-name 不能为空")
    if args.timeout < 0:
        parser.error("--timeout 必须大于或等于 0")
    if args.settle_seconds < 0:
        parser.error("--settle-seconds 必须大于或等于 0")
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
