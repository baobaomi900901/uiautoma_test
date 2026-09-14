r"""``uiautoma.win32.Win32Element.child_at()`` 测试。

API 参数（不是测试脚本参数）::

    Win32Element.child_at(index: int) -> Win32Element

``index`` 是从 0 开始的直属子元素索引。高层 API 只有这一个必填参数，内部
使用固定的 5 秒超时。有效索引返回可继续执行动作的 ``Win32Element``；负数
或超出范围的索引抛出 ``ElementNotFoundError``。

脚本借用 UIAutoma 当前启用的 ``D:\code\元素库\260902_win元素``，以
``win32靶场_表单控件_表单面板`` 为目标。先通过 ``children()`` 读取参照顺序，再验证
``child_at()`` 的首项、中间项、末项及两个越界场景。

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
PANEL_ELEMENT = "win32靶场_表单控件_表单面板"

STATUS_LABELS = {"PASS": "通过", "FAIL": "失败", "BLOCKED": "阻塞"}
COLORS = {"PASS": "\x1b[32m", "FAIL": "\x1b[31m", "BLOCKED": "\x1b[33m"}
CYAN = "\x1b[36m"
RESET = "\x1b[0m"

PROGRESS_WIDTH = 7
STATUS_WIDTH = 6
CASE_WIDTH = 16
DETAIL_WIDTH = 64
DURATION_WIDTH = 8
TABLE_WIDTH = sum(
    (PROGRESS_WIDTH, STATUS_WIDTH, CASE_WIDTH, DETAIL_WIDTH, DURATION_WIDTH, 8)
)

CASE_LABELS = {
    "api_contract": "API 合同",
    "current_package": "当前元素库",
    "reference_children": "参照子元素",
    "first_index": "首个索引",
    "middle_index": "中间索引",
    "last_index": "最后索引",
    "negative_index": "负数索引",
    "out_of_range": "越界索引",
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


def _normalize_type(value: object) -> str:
    return str(value or "").strip().casefold().removesuffix("control")


def _element_info(element: Win32Element) -> dict[str, Any]:
    raw = element.raw
    nested_raw = raw.get("raw") if isinstance(raw.get("raw"), dict) else {}
    navigation = (
        nested_raw.get("navigation_step")
        if isinstance(nested_raw.get("navigation_step"), dict)
        else {}
    )
    return {
        "id": element.id,
        "name": element.name,
        "control_type": str(raw.get("control_type") or raw.get("controlType") or ""),
        "relation": str(raw.get("relation") or ""),
        "navigation_index": navigation.get("index"),
    }


def _same_element(actual: dict[str, Any], expected: dict[str, Any]) -> bool:
    return (
        actual["name"] == expected["name"]
        and _normalize_type(actual["control_type"])
        == _normalize_type(expected["control_type"])
    )


def _check_contract() -> dict[str, Any]:
    started = time.perf_counter()
    try:
        signature = inspect.signature(Win32Element.child_at)
        parameters = signature.parameters
        index = parameters.get("index")
        annotation = str(signature.return_annotation)
        passed = (
            tuple(parameters) == ("self", "index")
            and index is not None
            and index.kind is inspect.Parameter.POSITIONAL_OR_KEYWORD
            and index.default is inspect.Parameter.empty
            and str(index.annotation) in {"int", "<class 'int'>"}
            and "Win32Element" in annotation
        )
        return _result(
            "api_contract",
            "PASS" if passed else "FAIL",
            (
                "公开签名包含必填 index: int，并返回 Win32Element"
                if passed
                else "公开签名与当前合同不一致"
            ),
            elapsed_ms=_elapsed(started),
            signature=str(signature),
        )
    except Exception as exc:  # noqa: BLE001
        return _result(
            "api_contract",
            "FAIL",
            "无法检查公开签名",
            elapsed_ms=_elapsed(started),
            exception=exc.__class__.__name__,
            message=str(exc),
        )


def _current_package() -> tuple[dict[str, Any], Any | None]:
    started = time.perf_counter()
    package: Any | None = None
    try:
        if not LIBRARY_DIR.is_dir():
            return _blocked("current_package", "测试元素库目录不存在"), None
        package = uiautoma.current(required=False, refresh=True, timeout=5)
        ensure_form_tab(package)
        if package is None:
            return _blocked("current_package", "UIAutoma 当前未启用测试元素库"), None
        actual = Path(package.package_dir)
        same_path = os.path.normcase(str(actual.resolve())) == os.path.normcase(
            str(LIBRARY_DIR.resolve())
        )
        return (
            _result(
                "current_package",
                "PASS" if same_path else "BLOCKED",
                "当前启用元素库与测试库一致" if same_path else "当前元素库不是测试库",
                elapsed_ms=_elapsed(started),
                actual_library=str(actual),
            ),
            package,
        )
    except Exception as exc:  # noqa: BLE001
        return (
            _result(
                "current_package",
                _error_status(exc),
                "读取 UIAutoma 当前元素库失败",
                elapsed_ms=_elapsed(started),
                exception=exc.__class__.__name__,
                message=str(exc),
            ),
            package,
        )


def _prepare_reference() -> tuple[dict[str, Any], Win32Element | None, list[Win32Element] | None]:
    started = time.perf_counter()
    try:
        panel = win32.find(PANEL_ELEMENT, timeout=10)
        children = panel.children()
        passed = isinstance(children, list) and len(children) >= 3
        return (
            _result(
                "reference_children",
                "PASS" if passed else "FAIL",
                (
                    f"已读取 {len(children)} 个直属子元素作为索引参照"
                    if passed
                    else "直属子元素不足，无法覆盖首项、中间项和末项"
                ),
                elapsed_ms=_elapsed(started),
                child_count=len(children) if isinstance(children, list) else None,
            ),
            panel if passed else None,
            children if passed else None,
        )
    except Exception as exc:  # noqa: BLE001
        return (
            _result(
                "reference_children",
                _error_status(exc),
                "读取面板直属子元素失败",
                elapsed_ms=_elapsed(started),
                exception=exc.__class__.__name__,
                message=str(exc),
            ),
            None,
            None,
        )


def _check_valid_index(
    case_id: str,
    panel: Win32Element,
    reference: list[Win32Element],
    index: int,
) -> dict[str, Any]:
    started = time.perf_counter()
    try:
        expected = _element_info(reference[index])
        actual_element = panel.child_at(index)
        actual = _element_info(actual_element)
        relation_ok = actual["relation"].casefold() == "child_at"
        navigation_ok = actual["navigation_index"] in {None, index}
        passed = (
            isinstance(actual_element, Win32Element)
            and str(actual["id"]).startswith("rt:win:")
            and relation_ok
            and navigation_ok
            and _same_element(actual, expected)
        )
        return _result(
            case_id,
            "PASS" if passed else "FAIL",
            (
                f"child_at({index}) 返回 {actual['control_type']}“{actual['name']}”"
                if passed
                else f"child_at({index}) 返回项与参照列表不一致"
            ),
            elapsed_ms=_elapsed(started),
            index=index,
            expected=expected,
            actual=actual,
        )
    except Exception as exc:  # noqa: BLE001
        return _result(
            case_id,
            _error_status(exc),
            f"child_at({index}) 调用失败",
            elapsed_ms=_elapsed(started),
            index=index,
            exception=exc.__class__.__name__,
            message=str(exc),
        )


def _check_invalid_index(
    case_id: str,
    panel: Win32Element,
    index: int,
) -> dict[str, Any]:
    started = time.perf_counter()
    try:
        value = panel.child_at(index)
        return _result(
            case_id,
            "FAIL",
            f"child_at({index}) 应拒绝越界索引但返回了元素",
            elapsed_ms=_elapsed(started),
            actual=_element_info(value),
        )
    except Exception as exc:  # noqa: BLE001
        passed = exc.__class__.__name__ == "ElementNotFoundError"
        return _result(
            case_id,
            "PASS" if passed else _error_status(exc),
            (
                f"child_at({index}) 被正确识别为未找到子元素"
                if passed
                else f"child_at({index}) 抛出了非预期异常"
            ),
            elapsed_ms=_elapsed(started),
            index=index,
            exception=exc.__class__.__name__,
            message=str(exc),
        )


def _cleanup(package: Any | None) -> dict[str, Any]:
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
            "已关闭借用的 Package；靶场保持运行",
            elapsed_ms=_elapsed(started),
        )
    except Exception as exc:  # noqa: BLE001
        return _result(
            "resource_cleanup",
            "FAIL",
            "关闭借用的 Package 失败",
            elapsed_ms=_elapsed(started),
            exception=exc.__class__.__name__,
            message=str(exc),
        )


def _print_header(*, color: bool) -> None:
    title = f"{CYAN}UIAutoma Win32 API 测试{RESET}" if color else "UIAutoma Win32 API 测试"
    print(title)
    print()
    print("  API     : uiautoma.win32.Win32Element.child_at")
    print(f"  元素库  : {LIBRARY_DIR}")
    print(f"  面板元素: {PANEL_ELEMENT}")
    print("  索引规则: 从 0 开始，仅访问直属子元素")
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
    if result.get("expected"):
        expected = result["expected"]
        print(f"{indent}{_pad('预期', 8)}: {expected['control_type']}“{expected['name']}”")
    if result.get("actual"):
        actual = result["actual"]
        print(f"{indent}{_pad('实际', 8)}: {actual['control_type']}“{actual['name']}”")


def main() -> int:
    color = "NO_COLOR" not in os.environ and sys.stdout.isatty()
    _print_header(color=color)
    started = time.perf_counter()
    results = [_check_contract()]

    package_result, package = _current_package()
    results.append(package_result)
    panel: Win32Element | None = None
    reference: list[Win32Element] | None = None

    if package_result["status"] == "PASS":
        reference_result, panel, reference = _prepare_reference()
        results.append(reference_result)
    else:
        results.append(_blocked("reference_children", "当前测试元素库不可用"))

    if panel is not None and reference is not None:
        last = len(reference) - 1
        results.extend(
            [
                _check_valid_index("first_index", panel, reference, 0),
                _check_valid_index("middle_index", panel, reference, len(reference) // 2),
                _check_valid_index("last_index", panel, reference, last),
                _check_invalid_index("negative_index", panel, -1),
                _check_invalid_index("out_of_range", panel, len(reference)),
            ]
        )
    else:
        detail = "面板索引参照不可用"
        results.extend(
            _blocked(case_id, detail)
            for case_id in (
                "first_index",
                "middle_index",
                "last_index",
                "negative_index",
                "out_of_range",
            )
        )

    results.append(_cleanup(package))
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
