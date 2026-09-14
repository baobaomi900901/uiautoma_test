r"""``uiautoma.win32.Win32Window.contains_element()`` 持久化真实元素库测试。

API 参数（不是测试脚本参数）::

    Win32Window.contains_element(
        selector: str | Selector,
    ) -> bool

参数规则：

* ``selector``：唯一必填参数，支持元素名称字符串或 Win32 ``Selector``。
* 找到至少一个匹配元素返回 ``True``，未找到返回 ``False``。
* 方法内部固定使用 ``find_all(selector, timeout=0)``，只查询一次，不等待。
* 列表、整数、``Win32Element`` 和非 Win32 ``Selector`` 会抛出
  ``InvalidParamsError``；额外位置参数或 ``timeout=`` 会抛出 ``TypeError``。

测试脚本参数：无。

脚本借用 UIAutoma 当前启用的 ``D:\code\元素库\260902_win元素``，在用户已经
启动的 Win32 靶场窗口中检查 ``win32靶场_表单控件_输入框_姓名``。测试结束后只关闭借用的
Package 连接，不关闭、激活或修改靶场。导入本模块不会连接 Runtime。

运行方式::

    uv run .\win32\test_win32_contains_element.py
"""

from __future__ import annotations

from _form_tab import ensure_form_tab

import inspect
import os
import re
import sys
import time
import unicodedata
from pathlib import Path
from typing import Any, Callable

import uiautoma
from uiautoma import win32
from uiautoma.package import Selector
from uiautoma.win32 import Win32Element, Win32Window


__test__ = False

LIBRARY_DIR = Path(r"D:\code\元素库\260902_win元素")
TARGET_ELEMENT = "win32靶场_表单控件_输入框_姓名"
TARGET_TITLE = "Win32 靶场 - UIA"
TARGET_CLASS = "XPathWin32ShootingRange"
TARGET_PROCESS = "win32-shooting-range-uia.exe"
MISSING_ELEMENT = "__uiautoma_contains_element_missing__"

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
DETAIL_WIDTH = 72
DURATION_WIDTH = 8
TABLE_WIDTH = (
    PROGRESS_WIDTH
    + STATUS_WIDTH
    + CASE_WIDTH
    + DETAIL_WIDTH
    + DURATION_WIDTH
    + 8
)

CASE_LABELS = {
    "api_contract": "API 合同",
    "current_package": "当前元素库",
    "target_window": "靶场窗口",
    "string_present": "名称存在",
    "selector_present": "Selector 存在",
    "string_missing": "名称不存在",
    "invalid_selector": "非法选择器类型",
    "element_rejected": "Win32Element 被拒绝",
    "wrong_framework": "非 Win Selector",
    "extra_timeout": "不支持 timeout",
    "resource_cleanup": "资源清理",
}

BLOCKING_EXCEPTION_NAMES = {
    "ConnectionError",
    "EOFError",
    "ElementNotFoundError",
    "HostUnavailableError",
    "NoCurrentPackageError",
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


def _error_fields(exc: BaseException) -> dict[str, str]:
    return {"exception": exc.__class__.__name__, "message": str(exc)}


def _error_result(
    case_id: str,
    detail: str,
    started: float,
    exc: BaseException,
    **extra: Any,
) -> dict[str, Any]:
    return _result(
        case_id,
        _error_status(exc),
        detail,
        elapsed_ms=_elapsed(started),
        **_error_fields(exc),
        **extra,
    )


def _blocked_case(case_id: str, detail: str) -> dict[str, Any]:
    return _result(case_id, "BLOCKED", detail, elapsed_ms=0.0)


def _colorize(text: str, color: str, *, enabled: bool) -> str:
    if not enabled:
        return text
    return f"{ANSI_COLORS[color]}{text}{ANSI_RESET}"


def _display_width(text: str) -> int:
    plain = re.sub(r"\x1b\[[0-9;]*m", "", str(text))
    width = 0
    for character in plain:
        if unicodedata.combining(character):
            continue
        width += 2 if unicodedata.east_asian_width(character) in {"W", "F"} else 1
    return width


def _pad(text: str, width: int, *, right: bool = False) -> str:
    value = str(text)
    padding = " " * max(0, width - _display_width(value))
    return f"{padding}{value}" if right else f"{value}{padding}"


def _same_path(left: Path, right: Path) -> bool:
    return os.path.normcase(str(left.resolve())) == os.path.normcase(str(right.resolve()))


def _check_contract() -> dict[str, Any]:
    started = time.perf_counter()
    try:
        signature = inspect.signature(Win32Window.contains_element)
        parameters = signature.parameters
        self_parameter = parameters.get("self")
        selector_parameter = parameters.get("selector")
        annotation = str(selector_parameter.annotation) if selector_parameter is not None else ""
        passed = (
            tuple(parameters) == ("self", "selector")
            and self_parameter is not None
            and self_parameter.kind is inspect.Parameter.POSITIONAL_OR_KEYWORD
            and self_parameter.default is inspect.Parameter.empty
            and selector_parameter is not None
            and selector_parameter.kind is inspect.Parameter.POSITIONAL_OR_KEYWORD
            and selector_parameter.default is inspect.Parameter.empty
            and "str" in annotation
            and "Selector" in annotation
            and "Win32Element" not in annotation
            and str(signature.return_annotation) in {"bool", "<class 'bool'>"}
        )
        return _result(
            "api_contract",
            "PASS" if passed else "FAIL",
            (
                "公开签名只有必填 selector: str | Selector，并返回 bool"
                if passed
                else "公开签名与当前合同不一致"
            ),
            elapsed_ms=_elapsed(started),
            signature=str(signature),
        )
    except Exception as exc:  # noqa: BLE001
        return _error_result("api_contract", "无法检查公开签名", started, exc)


def _current_package() -> tuple[dict[str, Any], Any | None]:
    started = time.perf_counter()
    if not LIBRARY_DIR.is_dir():
        return (
            _result(
                "current_package",
                "BLOCKED",
                "测试元素库目录不存在",
                elapsed_ms=_elapsed(started),
                expected_library=str(LIBRARY_DIR),
            ),
            None,
        )
    package: Any | None = None
    try:
        package = uiautoma.current(required=False, refresh=True, timeout=5)
        ensure_form_tab(package)
        if package is None:
            return (
                _result(
                    "current_package",
                    "BLOCKED",
                    "UIAutoma 当前未启用测试元素库",
                    elapsed_ms=_elapsed(started),
                    expected_library=str(LIBRARY_DIR),
                ),
                None,
            )
        actual_library = Path(package.package_dir)
        if not _same_path(actual_library, LIBRARY_DIR):
            return (
                _result(
                    "current_package",
                    "BLOCKED",
                    "UIAutoma 当前元素库不是测试库",
                    elapsed_ms=_elapsed(started),
                    expected_library=str(LIBRARY_DIR),
                    actual_library=str(actual_library),
                ),
                package,
            )
        return (
            _result(
                "current_package",
                "PASS",
                "当前启用元素库与测试库一致",
                elapsed_ms=_elapsed(started),
                actual_library=str(actual_library),
            ),
            package,
        )
    except Exception as exc:  # noqa: BLE001
        return (
            _error_result("current_package", "读取 UIAutoma 当前元素库失败", started, exc),
            package,
        )


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


def _run_bool_case(
    case_id: str,
    success_detail: str,
    *,
    window: Win32Window,
    selector: str | Selector,
    expected: bool,
) -> dict[str, Any]:
    started = time.perf_counter()
    try:
        returned = window.contains_element(selector)
        passed = returned is expected
        return _result(
            case_id,
            "PASS" if passed else "FAIL",
            success_detail if passed else "返回值与预期不一致",
            elapsed_ms=_elapsed(started),
            returned=returned,
            expected=expected,
            selector_type=type(selector).__name__,
        )
    except Exception as exc:  # noqa: BLE001
        return _error_result(case_id, "contains_element() 调用失败", started, exc)


def _run_expected_errors(
    case_id: str,
    success_detail: str,
    calls: list[tuple[str, Callable[[], object]]],
    *,
    expected_exception: str,
) -> dict[str, Any]:
    started = time.perf_counter()
    outcomes: list[dict[str, Any]] = []
    for label, call in calls:
        try:
            call()
        except Exception as exc:  # noqa: BLE001
            outcomes.append(
                {
                    "label": label,
                    "exception": exc.__class__.__name__,
                    "message": str(exc),
                }
            )
        else:
            outcomes.append({"label": label, "exception": None, "message": "未抛出异常"})
    passed = all(item["exception"] == expected_exception for item in outcomes)
    return _result(
        case_id,
        "PASS" if passed else "FAIL",
        success_detail if passed else f"部分调用未抛出预期的 {expected_exception}",
        elapsed_ms=_elapsed(started),
        expected_exception=expected_exception,
        outcomes=outcomes,
    )


def _run_element_rejected(window: Win32Window, selector: Selector) -> dict[str, Any]:
    started = time.perf_counter()
    try:
        matches = window.find_all(selector, timeout=2)
        if len(matches) != 1 or not isinstance(matches[0], Win32Element):
            return _result(
                "element_rejected",
                "FAIL",
                "准备 Win32Element 时未得到唯一实时元素",
                elapsed_ms=_elapsed(started),
                match_count=len(matches),
            )
        element = matches[0]
        try:
            window.contains_element(element)  # type: ignore[arg-type]
        except Exception as exc:  # noqa: BLE001
            passed = exc.__class__.__name__ == "InvalidParamsError"
            return _result(
                "element_rejected",
                "PASS" if passed else _error_status(exc),
                (
                    "真实 Win32Element 被 InvalidParamsError 正确拒绝"
                    if passed
                    else "Win32Element 抛出的异常类型不符合预期"
                ),
                elapsed_ms=_elapsed(started),
                runtime_id=element.id,
                **_error_fields(exc),
            )
        return _result(
            "element_rejected",
            "FAIL",
            "Win32Element 未被拒绝",
            elapsed_ms=_elapsed(started),
            runtime_id=element.id,
        )
    except Exception as exc:  # noqa: BLE001
        return _error_result("element_rejected", "准备真实 Win32Element 失败", started, exc)


def _cleanup_package(package: Any | None) -> dict[str, Any]:
    started = time.perf_counter()
    if package is None:
        return _result(
            "resource_cleanup",
            "PASS",
            "没有已借用的 Package 连接；靶场保持运行",
            elapsed_ms=_elapsed(started),
        )
    try:
        package.close()
        return _result(
            "resource_cleanup",
            "PASS",
            "已关闭借用的 Package；靶场保持运行且未修改",
            elapsed_ms=_elapsed(started),
        )
    except Exception as exc:  # noqa: BLE001
        return _result(
            "resource_cleanup",
            "FAIL",
            "关闭借用的 Package 失败",
            elapsed_ms=_elapsed(started),
            **_error_fields(exc),
        )


def _print_header(*, color: bool) -> None:
    print(_colorize("UIAutoma Win32 API 测试", "cyan", enabled=color))
    print()
    print("  API     : uiautoma.win32.Win32Window.contains_element")
    print(f"  元素库  : {LIBRARY_DIR}")
    print(f"  检查元素: {TARGET_ELEMENT}")
    print(f"  测试窗口: {TARGET_TITLE}")
    print(f"  目标进程: {TARGET_PROCESS}")
    print("  查询规则: 固定 timeout=0，只检查一次，不等待")
    print("  参数区别: 不接受 Win32Element，也没有 timeout 参数")
    print()
    print(
        f"{_pad('进度', PROGRESS_WIDTH)}  "
        f"{_pad('状态', STATUS_WIDTH)}  "
        f"{_pad('测试项', CASE_WIDTH)}  "
        f"{_pad('测试结果', DETAIL_WIDTH)}  "
        f"{_pad('耗时', DURATION_WIDTH, right=True)}"
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
    badge = _colorize(_pad(f"[{status_text}]", STATUS_WIDTH), status_color, enabled=color)
    case_id = str(result.get("case_id") or "unknown")
    label = CASE_LABELS.get(case_id, case_id)
    elapsed = result.get("elapsed_ms")
    duration = f"{float(elapsed):.1f}ms" if isinstance(elapsed, (int, float)) else "—"
    print(
        f"{_pad(f'{index:02d}/{total:02d}', PROGRESS_WIDTH)}  "
        f"{badge}  "
        f"{_pad(label, CASE_WIDTH)}  "
        f"{_pad(str(result.get('detail') or ''), DETAIL_WIDTH)}  "
        f"{_pad(duration, DURATION_WIDTH, right=True)}"
    )
    if status == "PASS":
        return
    indent = " " * (PROGRESS_WIDTH + STATUS_WIDTH + CASE_WIDTH + 6)
    if result.get("message"):
        print(f"{indent}{_pad('原因', 10)}: {result['message']}")
    if result.get("actual_library"):
        print(f"{indent}{_pad('实际元素库', 10)}: {result['actual_library']}")
    for outcome in result.get("outcomes") or []:
        if outcome.get("exception") != result.get("expected_exception"):
            print(
                f"{indent}{_pad(str(outcome.get('label') or '参数'), 10)}: "
                f"{outcome.get('exception') or '未抛出异常'} {outcome.get('message') or ''}"
            )


def main() -> int:
    color = "NO_COLOR" not in os.environ and sys.stdout.isatty()
    _print_header(color=color)
    started = time.perf_counter()
    results: list[dict[str, Any]] = []
    package: Any | None = None

    results.append(_check_contract())
    package_result, package = _current_package()
    results.append(package_result)

    window: Win32Window | None = None
    selector: Selector | None = None
    if package_result["status"] == "PASS":
        target_result, window = _get_target_window()
        results.append(target_result)
        try:
            selector = package.selector(TARGET_ELEMENT, kind="win")
        except Exception as exc:  # noqa: BLE001
            results[-1] = _result(
                "target_window",
                _error_status(exc),
                "读取测试元素 Selector 失败",
                elapsed_ms=results[-1].get("elapsed_ms", 0.0),
                **_error_fields(exc),
            )
            window = None
    else:
        results.append(_blocked_case("target_window", "当前测试元素库不可用"))

    scenario_ids = [
        "string_present",
        "selector_present",
        "string_missing",
        "invalid_selector",
        "element_rejected",
        "wrong_framework",
        "extra_timeout",
    ]
    if window is not None and selector is not None:
        results.extend(
            [
                _run_bool_case(
                    "string_present",
                    "元素名称存在，单次查询返回 True",
                    window=window,
                    selector=TARGET_ELEMENT,
                    expected=True,
                ),
                _run_bool_case(
                    "selector_present",
                    "Win32 Selector 存在，单次查询返回 True",
                    window=window,
                    selector=selector,
                    expected=True,
                ),
                _run_bool_case(
                    "string_missing",
                    "不存在的元素名称返回 False",
                    window=window,
                    selector=MISSING_ELEMENT,
                    expected=False,
                ),
                _run_expected_errors(
                    "invalid_selector",
                    "列表和整数选择器均被 InvalidParamsError 正确拒绝",
                    [
                        ("列表", lambda: window.contains_element([TARGET_ELEMENT])),  # type: ignore[arg-type]
                        ("整数", lambda: window.contains_element(123)),  # type: ignore[arg-type]
                    ],
                    expected_exception="InvalidParamsError",
                ),
                _run_element_rejected(window, selector),
                _run_expected_errors(
                    "wrong_framework",
                    "Web Selector 被 InvalidParamsError 正确拒绝",
                    [
                        (
                            "Web Selector",
                            lambda: window.contains_element(
                                Selector(
                                    name="web测试选择器",
                                    framework="web",
                                    item_id=selector.id(),
                                )
                            ),
                        )
                    ],
                    expected_exception="InvalidParamsError",
                ),
                _run_expected_errors(
                    "extra_timeout",
                    "额外位置参数和 timeout 关键字均被 TypeError 正确拒绝",
                    [
                        ("额外位置参数", lambda: window.contains_element(TARGET_ELEMENT, 0)),  # type: ignore[call-arg]
                        ("timeout 关键字", lambda: window.contains_element(TARGET_ELEMENT, timeout=0)),  # type: ignore[call-arg]
                    ],
                    expected_exception="TypeError",
                ),
            ]
        )
    else:
        reason = "Win32 靶场窗口或测试 Selector 不可用"
        results.extend(_blocked_case(case_id, reason) for case_id in scenario_ids)

    results.append(_cleanup_package(package))

    total = len(results)
    for index, result in enumerate(results, start=1):
        _print_case(result, index, total, color=color)

    statuses = {str(result["status"]) for result in results}
    exit_code = 1 if "FAIL" in statuses else (2 if "BLOCKED" in statuses else 0)
    lifecycle = (
        "VERIFIED"
        if exit_code == 0
        else ("READY_FOR_LIVE" if results[0]["status"] == "PASS" else "DRAFT")
    )
    elapsed_ms = _elapsed(started)
    passed_count = sum(result["status"] == "PASS" for result in results)
    failed_count = sum(result["status"] == "FAIL" for result in results)
    blocked_count = sum(result["status"] == "BLOCKED" for result in results)
    parts = [f"{passed_count}/{total} 通过"]
    if failed_count:
        parts.append(f"{failed_count} 失败")
    if blocked_count:
        parts.append(f"{blocked_count} 阻塞")

    print("─" * TABLE_WIDTH)
    summary = {0: "测试通过", 1: "测试失败", 2: "测试阻塞"}[exit_code]
    summary_color = {0: "green", 1: "red", 2: "yellow"}[exit_code]
    print(
        f"{_colorize(summary, summary_color, enabled=color)}  ·  {lifecycle}  ·  "
        f"{'，'.join(parts)}  ·  {elapsed_ms:.1f}ms  ·  退出码 {exit_code}"
    )
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
