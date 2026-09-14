"""``uiautoma.win32.get_by_selector()`` 持久化真实元素库测试。

API 参数（不是本测试脚本的命令行参数）::

    win32.get_by_selector(
        selector: object = None,
        *,
        timeout: float = 5,
    ) -> Win32Window

参数规则：

* ``selector``：支持 ``None``、元素名称字符串、``package.Selector`` 和字段过滤
  ``Mapping``。字符串按元素名精确匹配；Mapping 支持 ``name``、``id``、
  ``process_name`` 等字段，字段名以 ``_contains`` 结尾时执行包含匹配。
* ``timeout``：仅限关键字，单位秒；默认 ``5``，``0`` 只查一次，``-1`` 一直等待；
  小于 ``-1`` 会抛出 ``InvalidParamsError``。

API 依赖当前打开的 Package。默认元素库为
``D:/code/元素库/260902_win元素``，默认元素为 ``win32靶场_表单控件_输入框_姓名``，所属窗口为
``Win32 靶场 - UIA``，进程为 ``win32-shooting-range-uia.exe``。脚本覆盖 selector
各支持类型、默认/零超时和安全负例，并在结束时关闭本次打开的 Package；不会关闭、
激活或修改靶场窗口。``timeout=-1`` 不自动执行，避免永久等待。

运行方式::

    uv run ./win32/test_win32_get_by_selector.py

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
from collections.abc import Mapping
from pathlib import Path
from typing import Any, Callable, Sequence

import uiautoma
from uiautoma import package, ping, win32
from uiautoma.package import Selector
from uiautoma.win32 import Win32Window


__test__ = False

PRODUCT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_LIBRARY = Path(r"D:\code\元素库\260902_win元素")
DEFAULT_ELEMENT_NAME = "win32靶场_表单控件_输入框_姓名"
DEFAULT_EXPECTED_TITLE = "Win32 靶场 - UIA"
DEFAULT_EXPECTED_CLASS_NAME = "XPathWin32ShootingRange"
DEFAULT_EXPECTED_PROCESS = "win32-shooting-range-uia.exe"

EXPECTED_PARAMETER_ORDER = ("selector", "timeout")
EXPECTED_DEFAULTS: dict[str, Any] = {"selector": None, "timeout": 5}
EXPECTED_KINDS = {
    "selector": inspect.Parameter.POSITIONAL_OR_KEYWORD,
    "timeout": inspect.Parameter.KEYWORD_ONLY,
}

LIVE_CASE_IDS = {
    "get_selector_string_default_timeout",
    "get_selector_object",
    "get_selector_mapping_name",
    "get_selector_mapping_id",
    "get_selector_mapping_process",
    "get_selector_mapping_contains",
    "get_selector_default_none",
    "get_timeout_zero",
    "get_missing_element",
    "get_invalid_selector_type",
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
    "package_open": "打开元素库",
    "get_selector_string_default_timeout": "元素名称",
    "get_selector_object": "Selector 对象",
    "get_selector_mapping_name": "名称字典",
    "get_selector_mapping_id": "ID 字典",
    "get_selector_mapping_process": "进程名字典",
    "get_selector_mapping_contains": "包含匹配字典",
    "get_selector_default_none": "默认选择器",
    "get_timeout_zero": "零超时查询",
    "get_missing_element": "不存在元素",
    "get_invalid_selector_type": "非法选择器",
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
CASE_WIDTH = 18
DETAIL_WIDTH = 56
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
    print(f"  {pad_display('API', 8)}: uiautoma.win32.get_by_selector")
    print(f"  {pad_display('元素库', 8)}: {args.library}")
    print(f"  {pad_display('元素', 8)}: {args.element}")
    print(f"  {pad_display('目标窗口', 8)}: {args.expected_title}")
    print(f"  {pad_display('目标进程', 8)}: {args.expected_process}")
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
        "native_bound": getattr(window, "_native", None) is not None,
        "item_names": [str(getattr(item, "name", "") or "") for item in getattr(window, "_items", [])],
    }


def _same_text(actual: object, expected: str) -> bool:
    return str(actual or "").strip().casefold() == expected.strip().casefold()


def _selector_call(selector: object, *, provided: bool, timeout: float | None) -> dict[str, Any]:
    if not provided:
        value: Any = "(default None)"
    elif isinstance(selector, Selector):
        value = {"type": "Selector", "name": selector.name(), "id": selector.id()}
    elif isinstance(selector, Mapping):
        value = dict(selector)
    else:
        value = selector
    call: dict[str, Any] = {"selector": value}
    if timeout is not None:
        call["timeout"] = timeout
    return call


def check_contract() -> dict[str, Any]:
    try:
        signature = inspect.signature(win32.get_by_selector)
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
        pkg = uiautoma.open(str(library_dir), timeout=timeout)
        ensure_form_tab(pkg)
        return (
            _result(
                "package_open",
                "PASS",
                "指定元素库已打开",
                elapsed_ms=round((time.perf_counter() - started) * 1000, 1),
                library_dir=str(library_dir),
            ),
            pkg,
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


def run_success_case(
    case_id: str,
    detail: str,
    *,
    selector: object,
    selector_provided: bool,
    timeout: float | None,
    args: argparse.Namespace,
) -> dict[str, Any]:
    started = time.perf_counter()
    keyword: dict[str, Any] = {}
    if timeout is not None:
        keyword["timeout"] = timeout
    call = _selector_call(selector, provided=selector_provided, timeout=timeout)
    try:
        if selector_provided:
            window = win32.get_by_selector(selector, **keyword)
        else:
            window = win32.get_by_selector(**keyword)
        snapshot = _window_snapshot(window)
        checks = {
            "return_type_ok": isinstance(window, Win32Window),
            "element_name_ok": args.element in snapshot["item_names"],
            "title_ok": _same_text(snapshot["actual_title"], args.expected_title),
            "class_name_ok": _same_text(snapshot["actual_class_name"], args.expected_class_name),
            "process_name_ok": _same_text(snapshot["actual_process_name"], args.expected_process),
            "native_bound_ok": snapshot["native_bound"] and snapshot["actual_handle"] > 0,
        }
        passed = all(checks.values())
        return _result(
            case_id,
            "PASS" if passed else "FAIL",
            detail if passed else "返回窗口、元素上下文或原生绑定不符合预期",
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
            "调用被环境阻塞" if status == "BLOCKED" else "获取选择器所属窗口失败",
            elapsed_ms=round((time.perf_counter() - started) * 1000, 1),
            call=call,
            **_error_fields(exc),
        )


def run_expected_error_case(
    case_id: str,
    success_detail: str,
    *,
    selector: object,
    expected_exception: str,
    timeout: float,
) -> dict[str, Any]:
    started = time.perf_counter()
    call = _selector_call(selector, provided=True, timeout=timeout)
    try:
        win32.get_by_selector(selector, timeout=timeout)
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


def cleanup_resources(pkg: Any | None) -> dict[str, Any]:
    if pkg is None:
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
        pkg.close()
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
            "api": "uiautoma.win32.get_by_selector",
            "lifecycle": lifecycle,
            "status": status,
            "exit_code": exit_code,
            "command": command,
            "target": {
                "library": str(args.library),
                "element": args.element,
                "title": args.expected_title,
                "class_name": args.expected_class_name,
                "process_name": args.expected_process,
            },
            "timeout": args.timeout,
            "results": list(results),
            "excluded": [
                "timeout=-1 无限等待（避免元素不存在时脚本永久挂起）",
                "多项命中矩阵（当前元素库只有一个 Win32 元素）",
                "关闭、激活或修改靶场窗口",
            ],
            "notes": [
                "selector 覆盖默认 None、str、Selector 和 Mapping",
                "清理仅关闭本次打开的 Package",
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
    total = 1 if args.contract_only else 15

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

    open_result, pkg = open_package(args.library, timeout=args.timeout)
    record(open_result)
    if pkg is None:
        record(cleanup_resources(pkg))
        return _report(args, results, command=command)

    try:
        selector_object = package.selector(args.element, kind="win")
        element_id = selector_object.id()
        success_cases = [
            (
                "get_selector_string_default_timeout",
                "元素名称及默认超时返回所属窗口",
                args.element,
                True,
                None,
            ),
            ("get_selector_object", "Selector 对象返回所属窗口", selector_object, True, args.timeout),
            (
                "get_selector_mapping_name",
                "名称字段字典返回所属窗口",
                {"name": args.element},
                True,
                args.timeout,
            ),
            (
                "get_selector_mapping_id",
                "元素 ID 字典返回所属窗口",
                {"id": element_id},
                True,
                args.timeout,
            ),
            (
                "get_selector_mapping_process",
                "进程名字段字典返回所属窗口",
                {"process_name": args.expected_process},
                True,
                args.timeout,
            ),
            (
                "get_selector_mapping_contains",
                "进程名包含匹配返回所属窗口",
                {"process_name_contains": "shooting-range"},
                True,
                args.timeout,
            ),
            (
                "get_selector_default_none",
                "默认 None 选择器返回唯一库元素窗口",
                None,
                False,
                args.timeout,
            ),
            (
                "get_timeout_zero",
                "零等待单次查询返回所属窗口",
                {"id": element_id},
                True,
                0,
            ),
        ]
        error_cases = [
            (
                "get_missing_element",
                "不存在元素被识别为未找到",
                "__uiautoma_missing_win32_element__",
                "ElementNotFoundError",
                0,
            ),
            (
                "get_invalid_selector_type",
                "不支持的选择器类型被正确拒绝",
                [args.element],
                "InvalidParamsError",
                0,
            ),
            (
                "get_invalid_timeout",
                "小于 -1 的超时值被正确拒绝",
                args.element,
                "InvalidParamsError",
                -2,
            ),
        ]

        for case_id, detail, selector, provided, timeout in success_cases:
            record(
                run_success_case(
                    case_id,
                    detail,
                    selector=selector,
                    selector_provided=provided,
                    timeout=timeout,
                    args=args,
                )
            )
        for case_id, detail, selector, expected_exception, timeout in error_cases:
            record(
                run_expected_error_case(
                    case_id,
                    detail,
                    selector=selector,
                    expected_exception=expected_exception,
                    timeout=timeout,
                )
            )
    except Exception as exc:  # noqa: BLE001
        record(_result("scenario_orchestration", "FAIL", "真实场景编排失败", **_error_fields(exc)))
    finally:
        record(cleanup_resources(pkg))
    return _report(args, results, command=command)


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="使用指定元素库验证 uiautoma.win32.get_by_selector() 的全部 API 参数。"
    )
    parser.add_argument("--library", type=Path, default=DEFAULT_LIBRARY, help=f"元素库目录，默认 {DEFAULT_LIBRARY}。")
    parser.add_argument("--element", default=DEFAULT_ELEMENT_NAME, help=f"Win32 元素名，默认 {DEFAULT_ELEMENT_NAME}。")
    parser.add_argument(
        "--expected-title",
        default=DEFAULT_EXPECTED_TITLE,
        help=f"预期窗口标题，默认 {DEFAULT_EXPECTED_TITLE}。",
    )
    parser.add_argument(
        "--expected-class-name",
        default=DEFAULT_EXPECTED_CLASS_NAME,
        help=f"预期窗口类名，默认 {DEFAULT_EXPECTED_CLASS_NAME}。",
    )
    parser.add_argument(
        "--expected-process",
        default=DEFAULT_EXPECTED_PROCESS,
        help=f"预期进程名，默认 {DEFAULT_EXPECTED_PROCESS}。",
    )
    parser.add_argument("--timeout", type=float, default=5.0, help="有限等待用例超时秒数，默认 5。")
    parser.add_argument("--runtime-timeout", type=float, default=5.0, help="Runtime ping 超时秒数，默认 5。")
    parser.add_argument("--contract-only", action="store_true", help="只检查公开签名，不打开元素库。")
    parser.add_argument("--json", action="store_true", help="只输出无颜色的完整 JSON 结果。")
    parser.add_argument("--no-color", action="store_true", help="显示友好摘要，但关闭状态颜色。")
    args = parser.parse_args(argv)
    args.library = Path(args.library).expanduser().resolve()
    args.element = str(args.element or "").strip()
    args.expected_title = str(args.expected_title or "").strip()
    args.expected_class_name = str(args.expected_class_name or "").strip()
    args.expected_process = str(args.expected_process or "").strip()
    if not args.element:
        parser.error("--element 不能为空")
    if not args.expected_title:
        parser.error("--expected-title 不能为空")
    if not args.expected_class_name:
        parser.error("--expected-class-name 不能为空")
    if not args.expected_process:
        parser.error("--expected-process 不能为空")
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
