"""``uiautoma.win32.get()`` 的微信窗口持久化测试。

API 参数（不是本测试脚本的命令行参数）::

    win32.get(
        title: str | None = None,
        class_name: str | None = None,
        use_wildcard: bool = False,
        *,
        process_name: str | None = None,
        timeout: float = 5,
    ) -> Win32Window

参数规则：

* ``title``：窗口标题或标题片段；``None``/空字符串表示不过滤。
* ``class_name``：Win32 窗口类名或片段；``None``/空字符串表示不过滤。
* ``use_wildcard``：``False`` 时忽略大小写进行包含匹配；``True`` 时
  ``title``、``class_name``、``process_name`` 均按 ``*``/``?`` 通配符匹配。
* ``process_name``：进程名或片段，只能以关键字参数传入；``None`` 表示不过滤。
* ``timeout``：等待窗口出现的秒数；默认 ``5``，``0`` 只查一次，``-1`` 一直等待。

多个过滤条件同时提供时采用 AND 关系。成功返回 ``Win32Window``；超时未找到窗口
抛出 ``ElementNotFoundError``，非法超时抛出 ``InvalidParamsError``。

默认真实测试对象：标题 ``微信``、类名 ``Qt51514QWindowIcon``、进程名
``Weixin.exe``。默认执行标题、类名、进程名、通配符、组合过滤、默认超时、零超时
和非法超时矩阵。``get()`` 不要求打开 Package；本脚本不会打开
``D:\\code\\元素库\\260902_win元素``（该元素库当前为空）。

测试脚本参数仅用于覆盖默认微信信息；它们不属于 ``win32.get()`` 的 API 参数。
导入本模块不会连接 Runtime 或枚举窗口。
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

DEFAULT_TITLE = "微信"
DEFAULT_CLASS_NAME = "Qt51514QWindowIcon"
DEFAULT_PROCESS_NAME = "Weixin.exe"

EXPECTED_PARAMETER_ORDER = (
    "title",
    "class_name",
    "use_wildcard",
    "process_name",
    "timeout",
)
EXPECTED_DEFAULTS: dict[str, Any] = {
    "title": None,
    "class_name": None,
    "use_wildcard": False,
    "process_name": None,
    "timeout": 5,
}
EXPECTED_KINDS = {
    "title": inspect.Parameter.POSITIONAL_OR_KEYWORD,
    "class_name": inspect.Parameter.POSITIONAL_OR_KEYWORD,
    "use_wildcard": inspect.Parameter.POSITIONAL_OR_KEYWORD,
    "process_name": inspect.Parameter.KEYWORD_ONLY,
    "timeout": inspect.Parameter.KEYWORD_ONLY,
}

LIVE_CASE_IDS = {
    "get_title_defaults",
    "get_class_name",
    "get_process_name",
    "get_combined_filters",
    "get_wildcard_filters",
    "get_timeout_zero",
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
    "get_title_defaults": "标题匹配",
    "get_class_name": "类名匹配",
    "get_process_name": "进程名匹配",
    "get_combined_filters": "组合过滤",
    "get_wildcard_filters": "通配符匹配",
    "get_timeout_zero": "零超时查询",
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
CASE_WIDTH = 14
DETAIL_WIDTH = 52
DURATION_WIDTH = 8
TABLE_WIDTH = (
    PROGRESS_WIDTH
    + STATUS_WIDTH
    + CASE_WIDTH
    + DETAIL_WIDTH
    + DURATION_WIDTH
    + 8
)


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
    """按终端显示宽度补空格，而不是按 Python 字符数量补空格。"""

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
    print(f"  {pad_display('API', 8)}: uiautoma.win32.get")
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


def _window_snapshot(window: Win32Window) -> dict[str, Any]:
    actual_title = str(window.title or window.get_detail("title") or "")
    actual_class_name = str(window.class_name or window.get_detail("class_name") or "")
    actual_process_name = str(window.get_detail("process_name") or "")
    try:
        handle = int(window.get_detail("handle") or 0)
    except (TypeError, ValueError):
        handle = 0
    return {
        "actual_title": actual_title,
        "actual_class_name": actual_class_name,
        "actual_process_name": actual_process_name,
        "handle": handle,
    }


def check_contract() -> dict[str, Any]:
    try:
        signature = inspect.signature(win32.get)
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


def run_get_case(
    case_id: str,
    detail: str,
    *,
    positional: tuple[Any, ...],
    keyword: dict[str, Any],
    expected_title: str,
    expected_class_name: str,
    expected_process_name: str,
) -> dict[str, Any]:
    started = time.perf_counter()
    call = {"positional": list(positional), "keyword": dict(keyword)}
    try:
        window = win32.get(*positional, **keyword)
        snapshot = _window_snapshot(window)
        checks = {
            "return_type_ok": isinstance(window, Win32Window),
            "title_ok": _same_text(snapshot["actual_title"], expected_title),
            "class_name_ok": _same_text(snapshot["actual_class_name"], expected_class_name),
            "process_name_ok": _same_text(snapshot["actual_process_name"], expected_process_name),
            "handle_ok": snapshot["handle"] > 0,
        }
        passed = all(checks.values())
        return _result(
            case_id,
            "PASS" if passed else "FAIL",
            detail if passed else "返回的窗口不是预期微信窗口",
            elapsed_ms=round((time.perf_counter() - started) * 1000, 1),
            call=call,
            **checks,
            **snapshot,
        )
    except Exception as exc:  # noqa: BLE001
        status = _error_status(exc)
        return _result(
            case_id,
            status,
            "get 被环境阻塞" if status == "BLOCKED" else "get 调用失败",
            elapsed_ms=round((time.perf_counter() - started) * 1000, 1),
            call=call,
            **_error_fields(exc),
        )


def run_invalid_timeout_case(
    *,
    title: str,
    class_name: str,
    process_name: str,
) -> dict[str, Any]:
    started = time.perf_counter()
    try:
        win32.get(
            title,
            class_name,
            False,
            process_name=process_name,
            timeout=-2,
        )
    except Exception as exc:  # noqa: BLE001
        passed = exc.__class__.__name__ == "InvalidParamsError"
        return _result(
            "get_invalid_timeout",
            "PASS" if passed else _error_status(exc),
            "小于 -1 的超时值被正确拒绝"
            if passed
            else "非法超时值抛出的异常类型不正确",
            elapsed_ms=round((time.perf_counter() - started) * 1000, 1),
            expected_exception="InvalidParamsError",
            **_error_fields(exc),
        )
    return _result(
        "get_invalid_timeout",
        "FAIL",
        "小于 -1 的超时值未被拒绝",
        elapsed_ms=round((time.perf_counter() - started) * 1000, 1),
        expected_exception="InvalidParamsError",
    )


def cleanup_resources() -> dict[str, Any]:
    """get() 只读探测，不创建或关闭微信窗口。"""

    return _result(
        "owned_resources_cleanup",
        "PASS",
        "本次未创建可拥有资源（只读 get，不关闭微信窗口）",
        confirmed=True,
        attempted_count=0,
        cleaned_count=0,
        resources=[],
    )


def _star_pattern(value: str) -> str:
    text = value.strip()
    if len(text) <= 1:
        return text
    return f"{text[0]}*{text[-1]}"


def _question_pattern(value: str) -> str:
    text = value.strip()
    if len(text) <= 1:
        return text
    index = len(text) // 2
    return f"{text[:index]}?{text[index + 1:]}"


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
            "api": "uiautoma.win32.get",
            "lifecycle": lifecycle,
            "status": status,
            "exit_code": exit_code,
            "command": command,
            "target": {
                "title": args.title,
                "class_name": args.class_name,
                "process_name": args.process_name,
            },
            "results": list(results),
            "excluded": [
                "timeout=-1 无限等待（避免目标窗口消失时脚本永久挂起）",
                "元素库绑定（get 不要求 Package，且指定元素库当前为空）",
                "关闭、激活或修改微信窗口",
            ],
            "notes": [
                "默认只读获取微信窗口，不创建或关闭用户应用",
                "通配符用例同时验证 * 和 ?",
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
    total = 1 if args.contract_only else 10

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

    expected = {
        "expected_title": args.title,
        "expected_class_name": args.class_name,
        "expected_process_name": args.process_name,
    }
    cases = [
        (
            "get_title_defaults",
            "使用窗口标题及其余默认参数获取微信成功",
            (args.title,),
            {},
        ),
        (
            "get_class_name",
            "仅使用窗口类名获取微信成功",
            (),
            {"class_name": args.class_name, "timeout": args.timeout},
        ),
        (
            "get_process_name",
            "仅使用进程名获取微信成功",
            (),
            {"process_name": args.process_name, "timeout": args.timeout},
        ),
        (
            "get_combined_filters",
            "全部过滤参数组合获取微信成功",
            (args.title, args.class_name, False),
            {"process_name": args.process_name, "timeout": args.timeout},
        ),
        (
            "get_wildcard_filters",
            "使用 * 与 ? 通配符获取微信成功",
            (_star_pattern(args.title), _star_pattern(args.class_name), True),
            {
                "process_name": _question_pattern(args.process_name),
                "timeout": args.timeout,
            },
        ),
        (
            "get_timeout_zero",
            "零等待单次查询获取已打开微信成功",
            (args.title, args.class_name, False),
            {"process_name": args.process_name, "timeout": 0},
        ),
    ]

    try:
        for case_id, detail, positional, keyword in cases:
            record(
                run_get_case(
                    case_id,
                    detail,
                    positional=positional,
                    keyword=keyword,
                    **expected,
                )
            )
        record(
            run_invalid_timeout_case(
                title=args.title,
                class_name=args.class_name,
                process_name=args.process_name,
            )
        )
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
        record(cleanup_resources())
    return _report(args, results, command=command)


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="使用微信窗口验证 uiautoma.win32.get() 的全部 API 参数。")
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
    parser.add_argument("--timeout", type=float, default=5.0, help="有限等待用例超时秒数，默认 5。")
    parser.add_argument("--runtime-timeout", type=float, default=5.0, help="Runtime ping 超时秒数，默认 5。")
    parser.add_argument("--contract-only", action="store_true", help="只检查公开签名，不连接 Runtime 或枚举窗口。")
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
