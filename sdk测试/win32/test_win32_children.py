r"""``uiautoma.win32.Win32Element.children()`` 测试。

API 参数（不是测试脚本参数）::

    Win32Element.children() -> list[Win32Element]

高层 ``children()`` 没有公开参数，内部使用固定的 5 秒超时。它只返回当前
元素的直属子元素，不递归获取更深层后代；没有子元素时返回空列表。

脚本借用 UIAutoma 当前启用的 ``D:\code\元素库\260902_win元素``，获取
``win32靶场_表单控件_表单面板`` 的直属子元素，校验返回对象、Runtime 关系以及元素库
中已抓取的 21 个交互控件。随后对叶子元素 ``win32靶场_表单控件_按钮_保存`` 调用
``children()``，校验返回空列表。

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
LEAF_ELEMENT = "win32靶场_表单控件_按钮_保存"

# (UIA 名称, ControlType)。只要求这些元素存在，不锁死 UIA 返回的总数和顺序。
EXPECTED_CHILDREN = {
    ("姓名", "Edit"),
    ("密码", "Edit"),
    ("邮箱", "Edit"),
    ("年龄", "Edit"),
    ("城市（单选）", "ComboBox"),
    ("北京", "CheckBox"),
    ("上海", "CheckBox"),
    ("广州", "CheckBox"),
    ("深圳", "CheckBox"),
    ("杭州", "CheckBox"),
    ("男", "RadioButton"),
    ("女", "RadioButton"),
    ("其他", "RadioButton"),
    ("阅读", "CheckBox"),
    ("运动", "CheckBox"),
    ("音乐", "CheckBox"),
    ("旅行", "CheckBox"),
    ("备注", "Edit"),
    ("同意用户协议", "CheckBox"),
    ("保存", "Button"),
    ("重置", "Button"),
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
DETAIL_WIDTH = 62
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
    "panel_children": "面板直属子元素",
    "runtime_elements": "返回对象",
    "expected_controls": "已抓取控件",
    "leaf_children": "叶子元素",
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
    return {"exception": exc.__class__.__name__, "message": str(exc)}


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


def _check_contract() -> dict[str, Any]:
    started = time.perf_counter()
    try:
        signature = inspect.signature(Win32Element.children)
        parameters = signature.parameters
        parameter_names = tuple(parameters)
        self_parameter = parameters.get("self")
        self_ok = (
            parameter_names == ("self",)
            and self_parameter is not None
            and self_parameter.kind is inspect.Parameter.POSITIONAL_OR_KEYWORD
            and self_parameter.default is inspect.Parameter.empty
        )
        return_annotation = str(signature.return_annotation)
        return_ok = "list" in return_annotation and "Win32Element" in return_annotation
        passed = self_ok and return_ok
        return _result(
            "api_contract",
            "PASS" if passed else "FAIL",
            (
                "公开签名无参数并返回 list[Win32Element]"
                if passed
                else "公开签名与当前合同不一致"
            ),
            elapsed_ms=(time.perf_counter() - started) * 1000,
            signature=str(signature),
            parameter_names=list(parameter_names),
            return_annotation=return_annotation,
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


def _get_panel_children() -> tuple[dict[str, Any], list[Win32Element] | None]:
    started = time.perf_counter()
    try:
        panel = win32.find(PANEL_ELEMENT, timeout=10)
        children = panel.children()
        passed = isinstance(children, list) and len(children) > 0
        return (
            _result(
                "panel_children",
                "PASS" if passed else "FAIL",
                (
                    f"children() 返回 {len(children)} 个直属子元素"
                    if passed
                    else "children() 未返回非空列表"
                ),
                elapsed_ms=(time.perf_counter() - started) * 1000,
                panel_id=panel.id,
                child_count=len(children) if isinstance(children, list) else None,
                return_type=type(children).__name__,
            ),
            children if isinstance(children, list) else None,
        )
    except Exception as exc:  # noqa: BLE001
        return (
            _result(
                "panel_children",
                _error_status(exc),
                "获取面板直属子元素失败",
                elapsed_ms=(time.perf_counter() - started) * 1000,
                **_error_fields(exc),
            ),
            None,
        )


def _check_runtime_elements(children: list[Win32Element] | None) -> dict[str, Any]:
    started = time.perf_counter()
    if children is None:
        return _blocked_case("runtime_elements", "面板直属子元素不可用")
    try:
        wrong_types = [type(child).__name__ for child in children if not isinstance(child, Win32Element)]
        infos = [_element_info(child) for child in children if isinstance(child, Win32Element)]
        invalid_runtime = [
            info
            for info in infos
            if not str(info["id"]).startswith("rt:win:")
            or str(info["relation"]).casefold() != "children"
        ]
        passed = not wrong_types and len(infos) == len(children) and not invalid_runtime
        return _result(
            "runtime_elements",
            "PASS" if passed else "FAIL",
            (
                "所有返回项均为 children 关系的 Runtime Win32Element"
                if passed
                else "返回项的类型或 Runtime 关系不符合合同"
            ),
            elapsed_ms=(time.perf_counter() - started) * 1000,
            wrong_types=wrong_types,
            invalid_runtime=invalid_runtime,
        )
    except Exception as exc:  # noqa: BLE001
        return _result(
            "runtime_elements",
            _error_status(exc),
            "检查返回对象失败",
            elapsed_ms=(time.perf_counter() - started) * 1000,
            **_error_fields(exc),
        )


def _check_expected_controls(children: list[Win32Element] | None) -> dict[str, Any]:
    started = time.perf_counter()
    if children is None:
        return _blocked_case("expected_controls", "面板直属子元素不可用")
    try:
        actual = {
            (child.name, _normalized_control_type(_element_info(child)["control_type"]))
            for child in children
            if isinstance(child, Win32Element)
        }
        expected = {
            (name, _normalized_control_type(control_type))
            for name, control_type in EXPECTED_CHILDREN
        }
        missing = sorted(expected - actual)
        passed = not missing
        return _result(
            "expected_controls",
            "PASS" if passed else "FAIL",
            (
                f"元素库记录的 {len(expected)} 个交互控件均在直属子元素中"
                if passed
                else f"缺少 {len(missing)} 个已抓取的直属控件"
            ),
            elapsed_ms=(time.perf_counter() - started) * 1000,
            expected_count=len(expected),
            actual_count=len(actual),
            missing=[{"name": name, "control_type": control_type} for name, control_type in missing],
        )
    except Exception as exc:  # noqa: BLE001
        return _result(
            "expected_controls",
            _error_status(exc),
            "校验已抓取控件失败",
            elapsed_ms=(time.perf_counter() - started) * 1000,
            **_error_fields(exc),
        )


def _check_leaf_children() -> dict[str, Any]:
    started = time.perf_counter()
    try:
        leaf = win32.find(LEAF_ELEMENT, timeout=10)
        children = leaf.children()
        passed = isinstance(children, list) and not children
        return _result(
            "leaf_children",
            "PASS" if passed else "FAIL",
            (
                "保存按钮没有直属子元素，children() 返回空列表"
                if passed
                else "叶子元素的 children() 未返回空列表"
            ),
            elapsed_ms=(time.perf_counter() - started) * 1000,
            leaf_id=leaf.id,
            child_count=len(children) if isinstance(children, list) else None,
            return_type=type(children).__name__,
        )
    except Exception as exc:  # noqa: BLE001
        return _result(
            "leaf_children",
            _error_status(exc),
            "检查叶子元素的子元素失败",
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
    print("  API     : uiautoma.win32.Win32Element.children")
    print(f"  元素库  : {LIBRARY_DIR}")
    print(f"  面板元素: {PANEL_ELEMENT}")
    print(f"  叶子元素: {LEAF_ELEMENT}")
    print(f"  预期控件: {len(EXPECTED_CHILDREN)} 个已抓取直属交互控件")
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
        print(f"{indent}{_pad('原因', 8)}: {result['message']}")
    if result.get("actual_library"):
        print(f"{indent}{_pad('实际元素库', 12)}: {result['actual_library']}")
    if result.get("missing"):
        missing = ", ".join(
            f"{item['control_type']}“{item['name']}”" for item in result["missing"]
        )
        print(f"{indent}{_pad('缺少控件', 8)}: {missing}")
    if result.get("wrong_types"):
        print(f"{indent}{_pad('错误类型', 8)}: {result['wrong_types']}")
    if result.get("invalid_runtime"):
        print(f"{indent}{_pad('无效对象', 8)}: {len(result['invalid_runtime'])} 个")


def main() -> int:
    color = "NO_COLOR" not in os.environ and sys.stdout.isatty()
    _print_header(color=color)
    started = time.perf_counter()
    results: list[dict[str, Any]] = []

    results.append(_check_contract())
    package_result, package = _current_package()
    results.append(package_result)

    children: list[Win32Element] | None = None
    if package_result["status"] == "PASS":
        children_result, children = _get_panel_children()
        results.append(children_result)
        results.append(_check_runtime_elements(children))
        results.append(_check_expected_controls(children))
        results.append(_check_leaf_children())
    else:
        detail = "当前测试元素库不可用"
        results.extend(
            [
                _blocked_case("panel_children", detail),
                _blocked_case("runtime_elements", detail),
                _blocked_case("expected_controls", detail),
                _blocked_case("leaf_children", detail),
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
