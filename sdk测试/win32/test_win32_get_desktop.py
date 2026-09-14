"""``uiautoma.win32.get_desktop()`` 持久化真实元素库测试。

API 参数（不是本测试脚本的命令行参数）::

    win32.get_desktop(timeout: float = 5) -> Win32Window

参数规则：

* ``timeout``：位置或关键字参数，单位秒；默认 ``5``，``0`` 只查一次，
  ``-1`` 一直等待；小于 ``-1`` 会抛出 ``InvalidParamsError``。

API 总会返回标题为 ``Desktop`` 的伪 ``Win32Window``，不会绑定真实桌面 HWND。
未打开 Package 时，窗口的元素列表为空；打开 Package 后，列表包含当前元素库中的
Win32 元素。脚本会打开 ``D:/code/元素库/260902_win元素`` 并检查
``win32靶场_表单控件_输入框_姓名``，关闭本次打开的 Package 后再验证无 Package 场景。
``timeout=-1`` 不自动执行，避免永久等待。

运行方式::

    uv run ./win32/test_win32_get_desktop.py

导入本模块不会连接 Runtime 或打开 Package。
"""

from __future__ import annotations

from _form_tab import ensure_form_tab

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

import uiautoma
from uiautoma import ping, win32
from uiautoma.win32 import Win32Window


__test__ = False

PRODUCT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_LIBRARY = Path(r"D:\code\元素库\260902_win元素")
DEFAULT_ELEMENT_NAME = "win32靶场_表单控件_输入框_姓名"
EXPECTED_TITLE = "Desktop"

EXPECTED_PARAMETER_ORDER = ("timeout",)
EXPECTED_DEFAULTS: dict[str, Any] = {"timeout": 5}
EXPECTED_KINDS = {"timeout": inspect.Parameter.POSITIONAL_OR_KEYWORD}

LIVE_CASE_IDS = {
    "desktop_no_package_positional",
    "desktop_no_package_keyword",
    "desktop_with_package_default",
    "desktop_with_package_positional",
    "desktop_with_package_keyword",
    "desktop_invalid_timeout",
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
    "desktop_no_package_positional": "无库位置参数",
    "desktop_no_package_keyword": "无库关键字参数",
    "package_open": "打开元素库",
    "desktop_with_package_default": "元素库默认参数",
    "desktop_with_package_positional": "元素库位置参数",
    "desktop_with_package_keyword": "元素库关键字参数",
    "desktop_invalid_timeout": "非法超时",
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
CASE_WIDTH = 20
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
    print(f"  {pad_display('API', 8)}: uiautoma.win32.get_desktop")
    print(f"  {pad_display('元素库', 8)}: {args.library}")
    print(f"  {pad_display('校验元素', 8)}: {args.element}")
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


def _window_snapshot(window: Win32Window) -> dict[str, Any]:
    raw = dict(getattr(window, "raw", None) or {})
    try:
        handle = int(window.get_detail("handle") or 0)
    except (TypeError, ValueError):
        handle = 0
    return {
        "actual_title": str(window.title or window.get_detail("title") or ""),
        "desktop_unverified": bool(raw.get("desktop_unverified")),
        "native_bound": getattr(window, "_native", None) is not None,
        "actual_handle": handle,
        "item_names": [
            str(getattr(item, "name", "") or "")
            for item in list(getattr(window, "_items", []) or [])
        ],
    }


def check_contract() -> dict[str, Any]:
    try:
        signature = inspect.signature(win32.get_desktop)
        parameters = signature.parameters
        order_ok = tuple(parameters) == EXPECTED_PARAMETER_ORDER
        defaults_ok = all(parameters[name].default == value for name, value in EXPECTED_DEFAULTS.items())
        kinds_ok = all(parameters[name].kind == value for name, value in EXPECTED_KINDS.items())
        no_extra_ok = set(parameters) == set(EXPECTED_PARAMETER_ORDER)
        annotation = signature.return_annotation
        annotation_text = str(annotation).replace("typing.", "")
        return_ok = (
            annotation is Win32Window
            or annotation_text in {"Win32Window", "uiautoma.win32.window.Win32Window"}
            or "Win32Window" in annotation_text
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


def run_desktop_case(
    case_id: str,
    detail: str,
    *,
    mode: str,
    timeout: float | None,
    expected_element: str | None,
) -> dict[str, Any]:
    started = time.perf_counter()
    call: dict[str, Any] = {"mode": mode}
    if timeout is not None:
        call["timeout"] = timeout
    try:
        if mode == "default":
            window = win32.get_desktop()
        elif mode == "positional":
            window = win32.get_desktop(timeout)
        elif mode == "keyword":
            window = win32.get_desktop(timeout=timeout)
        else:
            raise ValueError(f"未知调用模式：{mode}")

        snapshot = _window_snapshot(window)
        if expected_element is None:
            items_ok = len(snapshot["item_names"]) == 0
        else:
            items_ok = expected_element in snapshot["item_names"]
        checks = {
            "return_type_ok": isinstance(window, Win32Window),
            "title_ok": snapshot["actual_title"] == EXPECTED_TITLE,
            "desktop_unverified_ok": snapshot["desktop_unverified"],
            "native_unbound_ok": not snapshot["native_bound"],
            "zero_handle_ok": snapshot["actual_handle"] == 0,
            "items_ok": items_ok,
        }
        passed = all(checks.values())
        return _result(
            case_id,
            "PASS" if passed else "FAIL",
            detail if passed else "Desktop 伪窗口内容或绑定状态不符合预期",
            elapsed_ms=round((time.perf_counter() - started) * 1000, 1),
            call=call,
            expected_element=expected_element,
            item_count=len(snapshot["item_names"]),
            **checks,
            **snapshot,
        )
    except Exception as exc:  # noqa: BLE001
        status = _error_status(exc)
        return _result(
            case_id,
            status,
            "调用被环境阻塞" if status == "BLOCKED" else "get_desktop 调用失败",
            elapsed_ms=round((time.perf_counter() - started) * 1000, 1),
            call=call,
            **_error_fields(exc),
        )


def run_invalid_timeout_case() -> dict[str, Any]:
    started = time.perf_counter()
    call = {"mode": "positional", "timeout": -2}
    try:
        win32.get_desktop(-2)
    except Exception as exc:  # noqa: BLE001
        passed = exc.__class__.__name__ == "InvalidParamsError"
        return _result(
            "desktop_invalid_timeout",
            "PASS" if passed else _error_status(exc),
            "小于 -1 的超时值被正确拒绝" if passed else "非法超时抛出的异常类型不正确",
            elapsed_ms=round((time.perf_counter() - started) * 1000, 1),
            call=call,
            expected_exception="InvalidParamsError",
            **_error_fields(exc),
        )
    return _result(
        "desktop_invalid_timeout",
        "FAIL",
        "小于 -1 的超时值未被拒绝",
        elapsed_ms=round((time.perf_counter() - started) * 1000, 1),
        call=call,
        expected_exception="InvalidParamsError",
    )


def open_package(library_dir: Path, *, timeout: float) -> tuple[dict[str, Any], Any | None]:
    started = time.perf_counter()
    if not library_dir.is_dir():
        return (
            _result(
                "package_open",
                "BLOCKED",
                "元素库目录不存在",
                elapsed_ms=round((time.perf_counter() - started) * 1000, 1),
                library_dir=str(library_dir),
            ),
            None,
        )
    try:
        package = uiautoma.open(str(library_dir), timeout=timeout)
        ensure_form_tab(package)
        return (
            _result(
                "package_open",
                "PASS",
                "指定元素库已打开",
                elapsed_ms=round((time.perf_counter() - started) * 1000, 1),
                library_dir=str(library_dir),
            ),
            package,
        )
    except Exception as exc:  # noqa: BLE001
        return (
            _result(
                "package_open",
                _error_status(exc),
                "打开元素库失败",
                elapsed_ms=round((time.perf_counter() - started) * 1000, 1),
                library_dir=str(library_dir),
                **_error_fields(exc),
            ),
            None,
        )


def cleanup_resources(package: Any | None) -> dict[str, Any]:
    if package is None:
        return _result(
            "owned_resources_cleanup",
            "PASS",
            "本次没有已打开的 Package",
            confirmed=True,
            attempted_count=0,
            cleaned_count=0,
            resources=[],
        )
    try:
        package.close()
        return _result(
            "owned_resources_cleanup",
            "PASS",
            "已关闭本次打开的 Package；未关闭靶场窗口",
            confirmed=True,
            attempted_count=1,
            cleaned_count=1,
            resources=[{"kind": "package", "status": "closed"}],
        )
    except Exception as exc:  # noqa: BLE001
        return _result(
            "owned_resources_cleanup",
            "FAIL",
            "Package 关闭失败",
            confirmed=False,
            attempted_count=1,
            cleaned_count=0,
            resources=[{"kind": "package", "status": "failed", **_error_fields(exc)}],
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
            "api": "uiautoma.win32.get_desktop",
            "lifecycle": lifecycle,
            "status": status,
            "exit_code": exit_code,
            "command": command,
            "library_dir": str(args.library),
            "expected_element": args.element,
            "timeout": args.timeout,
            "results": list(results),
            "excluded": [
                "timeout=-1 无限等待（避免元素库状态异常时脚本永久挂起）",
                "desktop.find 等其他 Win32 API",
                "真实桌面 HWND 绑定（本 API 按合同返回伪窗口）",
            ],
            "notes": [
                "无 Package 时分别验证 timeout=0 的位置与关键字调用",
                "打开 Package 后分别验证默认、位置与关键字调用",
                "所有成功调用都校验 Desktop 标题、伪窗口标记、零句柄和原生未绑定状态",
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
    package: Any | None = None
    cleanup_result: dict[str, Any] | None = None

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
        open_result, package = open_package(Path(args.library), timeout=args.timeout)
        record(open_result)
        if package is not None:
            record(
                run_desktop_case(
                    "desktop_with_package_default",
                    "默认 timeout=5 返回含目标元素的 Desktop 伪窗口",
                    mode="default",
                    timeout=None,
                    expected_element=args.element,
                )
            )
            record(
                run_desktop_case(
                    "desktop_with_package_positional",
                    "有限超时位置参数返回含目标元素的 Desktop 伪窗口",
                    mode="positional",
                    timeout=args.timeout,
                    expected_element=args.element,
                )
            )
            record(
                run_desktop_case(
                    "desktop_with_package_keyword",
                    "有限超时关键字参数返回含目标元素的 Desktop 伪窗口",
                    mode="keyword",
                    timeout=args.timeout,
                    expected_element=args.element,
                )
            )

            cleanup_result = cleanup_resources(package)
            package = None
            if cleanup_result["status"] == "PASS":
                record(
                    run_desktop_case(
                        "desktop_no_package_positional",
                        "timeout=0 位置参数返回空 Desktop 伪窗口",
                        mode="positional",
                        timeout=0,
                        expected_element=None,
                    )
                )
                record(
                    run_desktop_case(
                        "desktop_no_package_keyword",
                        "timeout=0 关键字参数返回空 Desktop 伪窗口",
                        mode="keyword",
                        timeout=0,
                        expected_element=None,
                    )
                )
        record(run_invalid_timeout_case())
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
        if cleanup_result is None:
            cleanup_result = cleanup_resources(package)
        record(cleanup_result)
    return _report(args, results, command=command)


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="验证 uiautoma.win32.get_desktop() 的 timeout 参数与 Package 行为。"
    )
    parser.add_argument(
        "--library",
        type=Path,
        default=DEFAULT_LIBRARY,
        help=f"元素库目录，默认 {DEFAULT_LIBRARY}。",
    )
    parser.add_argument(
        "--element",
        default=DEFAULT_ELEMENT_NAME,
        help=f"元素库中必须存在的 Win32 元素名称，默认 {DEFAULT_ELEMENT_NAME}。",
    )
    parser.add_argument("--timeout", type=float, default=5.0, help="有限等待用例超时秒数，默认 5。")
    parser.add_argument("--runtime-timeout", type=float, default=5.0, help="Runtime ping 超时秒数，默认 5。")
    parser.add_argument("--contract-only", action="store_true", help="只检查公开签名，不连接 Runtime 或打开元素库。")
    parser.add_argument("--json", action="store_true", help="只输出无颜色的完整 JSON 结果。")
    parser.add_argument("--no-color", action="store_true", help="显示友好摘要，但关闭状态颜色。")
    args = parser.parse_args(argv)
    args.library = Path(args.library).expanduser().resolve()
    args.element = str(args.element).strip()
    if not args.element:
        parser.error("--element 不能为空")
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
