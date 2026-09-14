r"""``uiautoma.win32.Win32Element.parent()`` 测试。

API 参数（不是测试脚本参数）::

    Win32Element.parent() -> Win32Element

高层 ``parent()`` 没有公开参数，内部使用固定的 5 秒超时。Runtime 通过 UIA
``GetParentControl()`` 获取直接父元素，并返回可继续调用元素 API 的运行时
``Win32Element``。

脚本借用 UIAutoma 当前启用的 ``D:\code\元素库\260902_win元素``，使用
``win32靶场_表单控件_输入框_姓名`` 和 ``win32靶场_表单控件_按钮_保存`` 验证它们的直接父元素均为
“表单控件页” Pane，再对返回的 Pane 调用 ``parent()``，验证链式返回 Tab。

测试结束后关闭借用的 Package 连接，不关闭用户已经启动的 Win32 靶场程序。
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
from typing import Any

import uiautoma
from uiautoma import win32
from uiautoma.win32 import Win32Element


__test__ = False

LIBRARY_DIR = Path(r"D:\code\元素库\260902_win元素")
INPUT_ELEMENT = "win32靶场_表单控件_输入框_姓名"
BUTTON_ELEMENT = "win32靶场_表单控件_按钮_保存"
EXPECTED_PARENT_NAME = "表单控件页"
EXPECTED_PARENT_TYPE = "Pane"
EXPECTED_ANCESTOR_TYPE = "Tab"

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

CASE_LABELS = {
    "api_contract": "API 合同",
    "current_package": "当前元素库",
    "input_parent": "输入框父元素",
    "button_parent": "保存按钮父元素",
    "chained_parent": "链式父元素",
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


def _error_status(exc: BaseException) -> str:
    return "BLOCKED" if exc.__class__.__name__ in BLOCKING_EXCEPTION_NAMES else "FAIL"


def _error_fields(exc: BaseException) -> dict[str, str]:
    return {
        "exception": exc.__class__.__name__,
        "message": str(exc),
    }


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


def _normalized_control_type(value: object) -> str:
    normalized = str(value or "").strip().casefold()
    return normalized.removesuffix("control")


def _element_info(element: Win32Element) -> dict[str, Any]:
    raw = element.raw
    return {
        "id": element.id,
        "name": element.name,
        "control_type": str(raw.get("control_type") or raw.get("controlType") or ""),
        "relation": str(raw.get("relation") or ""),
        "source_element_id": str(raw.get("source_element_id") or ""),
    }


def _runtime_element_ok(info: dict[str, Any], expected_type: str) -> bool:
    return (
        str(info["id"]).startswith("rt:win:")
        and str(info["relation"]).casefold() == "parent"
        and _normalized_control_type(info["control_type"])
        == _normalized_control_type(expected_type)
    )


def _check_contract() -> dict[str, Any]:
    started = time.perf_counter()
    try:
        signature = inspect.signature(Win32Element.parent)
        parameters = signature.parameters
        parameter_names = tuple(parameters)
        self_only = parameter_names == ("self",)
        self_parameter = parameters.get("self")
        self_ok = (
            self_parameter is not None
            and self_parameter.kind is inspect.Parameter.POSITIONAL_OR_KEYWORD
            and self_parameter.default is inspect.Parameter.empty
        )
        return_ok = "Win32Element" in str(signature.return_annotation)
        passed = self_only and self_ok and return_ok
        return _result(
            "api_contract",
            "PASS" if passed else "FAIL",
            "公开签名无参数并返回 Win32Element" if passed else "公开签名与当前合同不一致",
            elapsed_ms=(time.perf_counter() - started) * 1000,
            signature=str(signature),
            parameter_names=list(parameter_names),
            return_annotation=str(signature.return_annotation),
        )
    except Exception as exc:  # noqa: BLE001
        return _result(
            "api_contract",
            "FAIL",
            "无法检查公开签名",
            elapsed_ms=(time.perf_counter() - started) * 1000,
            **_error_fields(exc),
        )


def _current_package() -> tuple[dict[str, Any], Any | None]:
    started = time.perf_counter()
    if not LIBRARY_DIR.is_dir():
        return (
            _result(
                "current_package",
                "BLOCKED",
                "测试元素库目录不存在",
                elapsed_ms=(time.perf_counter() - started) * 1000,
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
                    elapsed_ms=(time.perf_counter() - started) * 1000,
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
                    elapsed_ms=(time.perf_counter() - started) * 1000,
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
                elapsed_ms=(time.perf_counter() - started) * 1000,
                actual_library=str(actual_library),
            ),
            package,
        )
    except Exception as exc:  # noqa: BLE001
        return (
            _result(
                "current_package",
                _error_status(exc),
                "读取 UIAutoma 当前元素库失败",
                elapsed_ms=(time.perf_counter() - started) * 1000,
                **_error_fields(exc),
            ),
            package,
        )


def _run_direct_parent(
    case_id: str,
    element_name: str,
) -> tuple[dict[str, Any], Win32Element | None]:
    started = time.perf_counter()
    try:
        child = win32.find(element_name, timeout=10)
        parent = child.parent()
        info = _element_info(parent)
        passed = (
            isinstance(parent, Win32Element)
            and info["name"] == EXPECTED_PARENT_NAME
            and _runtime_element_ok(info, EXPECTED_PARENT_TYPE)
        )
        return (
            _result(
                case_id,
                "PASS" if passed else "FAIL",
                (
                    f"父元素为 {EXPECTED_PARENT_TYPE}“{EXPECTED_PARENT_NAME}”，Runtime ID 有效"
                    if passed
                    else "返回的直接父元素与元素库层级不一致"
                ),
                elapsed_ms=(time.perf_counter() - started) * 1000,
                child_name=element_name,
                child_id=child.id,
                parent=info,
            ),
            parent,
        )
    except Exception as exc:  # noqa: BLE001
        return (
            _result(
                case_id,
                _error_status(exc),
                "获取直接父元素失败",
                elapsed_ms=(time.perf_counter() - started) * 1000,
                child_name=element_name,
                **_error_fields(exc),
            ),
            None,
        )


def _run_chained_parent(parent: Win32Element | None) -> dict[str, Any]:
    started = time.perf_counter()
    if parent is None:
        return _result(
            "chained_parent",
            "BLOCKED",
            "输入框直接父元素失败，无法继续链式调用",
            elapsed_ms=(time.perf_counter() - started) * 1000,
        )
    try:
        ancestor = parent.parent()
        info = _element_info(ancestor)
        passed = (
            isinstance(ancestor, Win32Element)
            and ancestor.id != parent.id
            and _runtime_element_ok(info, EXPECTED_ANCESTOR_TYPE)
        )
        return _result(
            "chained_parent",
            "PASS" if passed else "FAIL",
            (
                "Pane 返回对象可继续调用 parent()，得到 Tab"
                if passed
                else "链式 parent() 返回的元素层级不符合预期"
            ),
            elapsed_ms=(time.perf_counter() - started) * 1000,
            source_parent=_element_info(parent),
            ancestor=info,
        )
    except Exception as exc:  # noqa: BLE001
        return _result(
            "chained_parent",
            _error_status(exc),
            "链式 parent() 调用失败",
            elapsed_ms=(time.perf_counter() - started) * 1000,
            **_error_fields(exc),
        )


def _cleanup_package(package: Any | None) -> dict[str, Any]:
    started = time.perf_counter()
    if package is None:
        return _result(
            "resource_cleanup",
            "PASS",
            "没有已借用的 Package 连接；靶场保持运行",
            elapsed_ms=(time.perf_counter() - started) * 1000,
        )
    try:
        package.close()
        return _result(
            "resource_cleanup",
            "PASS",
            "已关闭借用的 Package；靶场保持运行",
            elapsed_ms=(time.perf_counter() - started) * 1000,
        )
    except Exception as exc:  # noqa: BLE001
        return _result(
            "resource_cleanup",
            "FAIL",
            "关闭借用的 Package 失败",
            elapsed_ms=(time.perf_counter() - started) * 1000,
            **_error_fields(exc),
        )


def _blocked_case(case_id: str, detail: str) -> dict[str, Any]:
    return _result(case_id, "BLOCKED", detail, elapsed_ms=0.0)


def _print_header(*, color: bool) -> None:
    print(_colorize("UIAutoma Win32 API 测试", "cyan", enabled=color))
    print()
    print("  API     : uiautoma.win32.Win32Element.parent")
    print(f"  元素库  : {LIBRARY_DIR}")
    print(f"  子元素一: {INPUT_ELEMENT}")
    print(f"  子元素二: {BUTTON_ELEMENT}")
    print(f"  预期父级: {EXPECTED_PARENT_TYPE}“{EXPECTED_PARENT_NAME}” -> {EXPECTED_ANCESTOR_TYPE}")
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
    badge = _colorize(
        _pad(f"[{status_text}]", STATUS_WIDTH),
        status_color,
        enabled=color,
    )
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
        print(f"{indent}{_pad('原因', 8)}: {result['message']}")
    if result.get("actual_library"):
        print(f"{indent}{_pad('实际元素库', 12)}: {result['actual_library']}")


def main() -> int:
    color = "NO_COLOR" not in os.environ and sys.stdout.isatty()
    _print_header(color=color)
    started = time.perf_counter()
    results: list[dict[str, Any]] = []

    results.append(_check_contract())
    package_result, package = _current_package()
    results.append(package_result)

    input_parent: Win32Element | None = None
    if package_result["status"] == "PASS":
        input_result, input_parent = _run_direct_parent("input_parent", INPUT_ELEMENT)
        button_result, _ = _run_direct_parent("button_parent", BUTTON_ELEMENT)
        results.append(input_result)
        results.append(button_result)
        results.append(_run_chained_parent(input_parent))
    else:
        detail = "当前测试元素库不可用"
        results.extend(
            [
                _blocked_case("input_parent", detail),
                _blocked_case("button_parent", detail),
                _blocked_case("chained_parent", detail),
            ]
        )

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
    elapsed_ms = (time.perf_counter() - started) * 1000
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
