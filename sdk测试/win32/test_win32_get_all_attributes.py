r"""``uiautoma.win32.Win32Element.get_all_attributes()`` 真实 UIA 属性集测试。

API 参数（不是测试脚本参数）::

    Win32Element.get_all_attributes() -> dict[str, Any]

参数规则：

* 公开 API 没有参数；传入位置参数或 ``timeout`` 关键字会抛出 ``TypeError``。
* 返回dict，属性名为非空字符串，值保留原生类型。
* 属性值保留 Runtime 返回的 JSON 安全原生类型，包括字符串、整数、布尔、列表和字典，
  不会像 ``get_attribute()`` 一样统一转成字符串。
* 只返回当前 UIA 控件可读取的属性，不保证精确属性数量。公开 API 没有 ``timeout``，
  底层读取超时固定为 5 秒。

测试脚本参数：--non-interactive 自动模式，焦点恢复失败只警告、不等待人工。

脚本借用 UIAutoma 当前启用的 ``D:\code\元素库\260902_win元素``，使用
``win32靶场_表单控件_输入框_姓名`` 验证返回字典、属性名结构和唯一性，以及 Name、ClassName、
ControlType、ProcessId、IsEnabled、IsPassword、RuntimeId 和 BoundingRectangle 的值与
原生类型。重复调用测试只验证返回对象相互独立，不固化完整属性集合或精确数量。

本测试只读，不修改靶场控件；结束时恢复原前台窗口并关闭借用的 Package，Win32 靶场
保持运行。导入本模块不会连接 Runtime。

运行方式::

    uv run .\win32\test_win32_get_all_attributes.py
"""

from __future__ import annotations

from _form_tab import ensure_form_tab

import ctypes
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
from uiautoma.win32 import Win32Element
import test_win32_get_value as helper
from test_win32_highlight import restore_focus_for_mode, parse_run_options


__test__ = False

LIBRARY_DIR = Path(r"D:\code\元素库\260902_win元素")
TARGET_ELEMENT = "win32靶场_表单控件_输入框_姓名"
TARGET_TITLE = "Win32 靶场 - UIA"
TARGET_PROCESS = "win32-shooting-range-uia.exe"

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
CASE_WIDTH = 22
DETAIL_WIDTH = 82
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
    "element_prepare": "输入元素准备",
    "result_container": "返回容器",
    "tuple_structure": "字典键结构",
    "unique_names": "属性名唯一性",
    "string_attributes": "字符串属性",
    "integer_attributes": "整数属性",
    "boolean_attributes": "布尔属性",
    "runtime_id": "RuntimeId 属性",
    "bounding_rectangle": "BoundingRectangle 属性",
    "independent_results": "重复调用独立性",
    "argument_rejection": "无参数限制",
    "resource_cleanup": "资源清理",
}

BLOCKING_EXCEPTION_NAMES = {
    "ConnectionError",
    "EOFError",
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


def _blocked(case_id: str, detail: str) -> dict[str, Any]:
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


def _foreground_handle() -> int:
    return int(ctypes.windll.user32.GetForegroundWindow())


def _restore_foreground(handle: int) -> None:
    if handle <= 0 or not ctypes.windll.user32.IsWindow(handle):
        return
    ctypes.windll.user32.SetForegroundWindow(handle)
    deadline = time.perf_counter() + 1.0
    while time.perf_counter() < deadline:
        if _foreground_handle() == handle:
            return
        time.sleep(0.02)
    raise RuntimeError(f"原前台窗口未恢复：{handle}")


def _check_contract() -> dict[str, Any]:
    started = time.perf_counter()
    try:
        signature = inspect.signature(Win32Element.get_all_attributes)
        parameters = signature.parameters
        self_parameter = parameters.get("self")
        self_ok = (
            tuple(parameters) == ("self",)
            and self_parameter is not None
            and self_parameter.kind is inspect.Parameter.POSITIONAL_OR_KEYWORD
            and self_parameter.default is inspect.Parameter.empty
        )
        return_annotation = str(signature.return_annotation)
        return_ok = (
            "dict" in return_annotation
            and "str" in return_annotation
            and "Any" in return_annotation
        )
        passed = self_ok and return_ok
        return _result(
            "api_contract",
            "PASS" if passed else "FAIL",
            (
                "公开签名无参数并返回 dict[str, Any]"
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


def _prepare_element(package: Any) -> tuple[dict[str, Any], Win32Element | None]:
    started = time.perf_counter()
    try:
        selector = package.selector(TARGET_ELEMENT, kind="win")
        element = win32.find(selector, timeout=10)
        passed = (
            isinstance(element, Win32Element)
            and element.id.startswith("rt:win:")
            and str(element.raw.get("source_element_id") or "") == selector.id()
        )
        return (
            _result(
                "element_prepare",
                "PASS" if passed else "FAIL",
                "已获取输入框 Runtime 元素" if passed else "元素类型或元素库身份不符合预期",
                elapsed_ms=_elapsed(started),
                element_id=element.id,
                source_element_id=str(element.raw.get("source_element_id") or ""),
            ),
            element if passed else None,
        )
    except Exception as exc:  # noqa: BLE001
        return (
            _error_result("element_prepare", "获取靶场输入框失败", started, exc),
            None,
        )


def _read_attributes(
    element: Win32Element,
) -> tuple[dict[str, Any], dict[str, Any] | None]:
    started = time.perf_counter()
    try:
        old_result = element.last_result
        attributes = element.get_all_attributes()
        passed = isinstance(attributes, dict) and bool(attributes) and element.last_result is old_result
        return (
            _result(
                "result_container",
                "PASS" if passed else "FAIL",
                (
                    f"返回包含 {len(attributes)} 项属性的非空字典，last_result未改变"
                    if passed
                    else "返回值不是非空字典或last_result被改变"
                ),
                elapsed_ms=_elapsed(started),
                return_type=type(attributes).__name__,
                attribute_count=len(attributes) if isinstance(attributes, dict) else None,
            ),
            attributes if passed else None,
        )
    except Exception as exc:  # noqa: BLE001
        return (
            _error_result("result_container", "get_all_attributes() 调用失败", started, exc),
            None,
        )


def _check_tuple_structure(attributes: dict[str, Any]) -> dict[str, Any]:
    started = time.perf_counter()
    invalid = [
        item
        for item in attributes
        if not isinstance(item, str) or not item
    ]
    passed = not invalid
    return _result(
        "tuple_structure",
        "PASS" if passed else "FAIL",
        "字典键均为非空字符串属性名" if passed else "存在无效属性名",
        elapsed_ms=_elapsed(started),
        invalid_count=len(invalid),
        invalid_preview=invalid[:3],
    )


def _check_unique_names(attributes: dict[str, Any]) -> dict[str, Any]:
    started = time.perf_counter()
    names = list(attributes)
    duplicate_names = sorted({name for name in names if names.count(name) > 1})
    passed = len(names) == len(attributes) and not duplicate_names
    return _result(
        "unique_names",
        "PASS" if passed else "FAIL",
        "字典属性名唯一，数量一致" if passed else "返回结果包含重复或无效属性名",
        elapsed_ms=_elapsed(started),
        attribute_count=len(attributes),
        unique_count=len(set(names)),
        duplicate_names=duplicate_names,
    )


def _mapping(attributes: dict[str, Any]) -> dict[str, Any]:
    return dict(attributes)


def _check_string_attributes(attributes: dict[str, Any]) -> dict[str, Any]:
    started = time.perf_counter()
    values = _mapping(attributes)
    name = values.get("Name")
    class_name = values.get("ClassName")
    passed = name == "姓名" and class_name == "Edit"
    return _result(
        "string_attributes",
        "PASS" if passed else "FAIL",
        'Name="姓名" 且 ClassName="Edit"，两项均保持字符串类型' if passed else "字符串属性不符合预期",
        elapsed_ms=_elapsed(started),
        name=name,
        name_type=type(name).__name__,
        class_name=class_name,
        class_name_type=type(class_name).__name__,
    )


def _check_integer_attributes(attributes: dict[str, Any]) -> dict[str, Any]:
    started = time.perf_counter()
    values = _mapping(attributes)
    control_type = values.get("ControlType")
    process_id = values.get("ProcessId")
    passed = (
        isinstance(control_type, int)
        and not isinstance(control_type, bool)
        and control_type == 50004
        and isinstance(process_id, int)
        and not isinstance(process_id, bool)
        and process_id > 0
    )
    return _result(
        "integer_attributes",
        "PASS" if passed else "FAIL",
        "ControlType=50004 且 ProcessId 为正整数，两项均保持整数类型" if passed else "整数属性不符合预期",
        elapsed_ms=_elapsed(started),
        control_type=control_type,
        control_type_type=type(control_type).__name__,
        process_id=process_id,
        process_id_type=type(process_id).__name__,
    )


def _check_boolean_attributes(attributes: dict[str, Any]) -> dict[str, Any]:
    started = time.perf_counter()
    values = _mapping(attributes)
    enabled = values.get("IsEnabled")
    password = values.get("IsPassword")
    passed = enabled is True and password is False
    return _result(
        "boolean_attributes",
        "PASS" if passed else "FAIL",
        "IsEnabled=True 且 IsPassword=False，两项均保持布尔类型" if passed else "布尔属性不符合预期",
        elapsed_ms=_elapsed(started),
        enabled=enabled,
        enabled_type=type(enabled).__name__,
        password=password,
        password_type=type(password).__name__,
    )


def _check_runtime_id(attributes: dict[str, Any]) -> dict[str, Any]:
    started = time.perf_counter()
    value = _mapping(attributes).get("RuntimeId")
    passed = (
        isinstance(value, list)
        and bool(value)
        and all(isinstance(item, int) and not isinstance(item, bool) for item in value)
    )
    return _result(
        "runtime_id",
        "PASS" if passed else "FAIL",
        "RuntimeId 保持为非空整数列表" if passed else "RuntimeId 类型或内容不符合预期",
        elapsed_ms=_elapsed(started),
        value=value,
        value_type=type(value).__name__,
    )


def _check_bounding_rectangle(attributes: dict[str, Any]) -> dict[str, Any]:
    started = time.perf_counter()
    value = _mapping(attributes).get("BoundingRectangle")
    passed = (
        isinstance(value, dict)
        and set(value) == {"x", "y", "w", "h"}
        and all(isinstance(value[key], int) and not isinstance(value[key], bool) for key in value)
        and value["w"] > 0
        and value["h"] > 0
    )
    return _result(
        "bounding_rectangle",
        "PASS" if passed else "FAIL",
        "BoundingRectangle 保持为 x/y/w/h 整数字典且宽高有效" if passed else "矩形属性类型或内容不符合预期",
        elapsed_ms=_elapsed(started),
        value=value,
        value_type=type(value).__name__,
    )


def _check_independent_results(element: Win32Element) -> dict[str, Any]:
    started = time.perf_counter()
    try:
        first = element.get_all_attributes()
        second = element.get_all_attributes()
        distinct_objects = isinstance(first,dict) and isinstance(second,dict) and first is not second
        first.clear()
        third = element.get_all_attributes()
        second_values = dict(second)
        third_values = dict(third)
        stable_keys = ("Name", "ClassName", "ControlType")
        stable_equal = all(second_values.get(key) == third_values.get(key) for key in stable_keys)
        passed = (
            distinct_objects
            and not first
            and bool(second)
            and isinstance(third,dict) and bool(third)
            and second is not third
            and stable_equal
        )
        return _result(
            "independent_results",
            "PASS" if passed else "FAIL",
            "重复调用返回独立字典，清空前次结果不影响后续读取" if passed else "重复调用的结果独立性不符合预期",
            elapsed_ms=_elapsed(started),
            second_count=len(second),
            third_count=len(third),
            stable_equal=stable_equal,
        )
    except Exception as exc:  # noqa: BLE001
        return _error_result("independent_results", "检查重复调用结果失败", started, exc)


def _check_argument_rejection(element: Win32Element) -> dict[str, Any]:
    started = time.perf_counter()
    calls: list[tuple[str, Callable[[], object]]] = [
        ("位置参数", lambda: element.get_all_attributes(1)),  # type: ignore[call-arg]
        (
            "timeout 关键字",
            lambda: element.get_all_attributes(timeout=1),  # type: ignore[call-arg]
        ),
    ]
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
    passed = all(item["exception"] == "TypeError" for item in outcomes)
    return _result(
        "argument_rejection",
        "PASS" if passed else "FAIL",
        "位置参数和 timeout 关键字均被 TypeError 正确拒绝" if passed else "部分参数未按无参数合同被拒绝",
        elapsed_ms=_elapsed(started),
        expected_exception="TypeError",
        outcomes=outcomes,
    )


def _cleanup(package: Any | None, original_foreground: int, original_mouse, non_interactive) -> dict[str, Any]:
    started = time.perf_counter()
    errors: list[str] = []
    restored_foreground = False
    if original_foreground > 0:
        try:
            print('  焦点恢复: ' + restore_focus_for_mode(original_foreground,non_interactive))
            restored_foreground = _foreground_handle() == original_foreground
        except Exception as exc:  # noqa: BLE001
            errors.append(f"恢复原前台窗口失败：{exc}")
    try:
        helper.restore_cursor(original_mouse)
    except Exception as exc:
        errors.append(f'恢复鼠标失败: {exc}')
    if package is not None:
        try:
            package.close()
        except Exception as exc:  # noqa: BLE001
            errors.append(f"关闭 Package 失败：{exc}")
    if errors:
        return _result(
            "resource_cleanup",
            "FAIL",
            "测试资源未完全恢复",
            elapsed_ms=_elapsed(started),
            message="；".join(errors),
            restored_foreground=restored_foreground,
        )
    return _result(
        "resource_cleanup",
        "PASS",
        "鼠标已恢复，Package已关闭（如已取得）；靶场保留表单页，焦点单独报告",
        elapsed_ms=_elapsed(started),
        restored_foreground=restored_foreground,
    )


def _print_header(*, color: bool) -> None:
    print(_colorize("UIAutoma Win32 API 测试", "cyan", enabled=color))
    print()
    print("  API     : uiautoma.win32.Win32Element.get_all_attributes")
    print(f"  元素库  : {LIBRARY_DIR}")
    print(f"  测试元素: {TARGET_ELEMENT}")
    print(f"  测试窗口: {TARGET_TITLE}")
    print(f"  目标进程: {TARGET_PROCESS}")
    print("  返回结构: dict[str, Any]，属性值保留原生类型")
    print("  数量规则: 只要求非空，不固化当前 UIA 属性总数")
    print("  测试性质: 只读，不修改靶场控件")
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
    if result.get("value") is not None:
        print(f"{indent}{_pad('实际值', 10)}: {result['value']!r}")
    for outcome in result.get("outcomes") or []:
        if outcome.get("exception") != result.get("expected_exception"):
            print(
                f"{indent}{_pad(str(outcome.get('label') or '参数'), 10)}: "
                f"{outcome.get('exception') or '未抛出异常'} {outcome.get('message') or ''}"
            )


def main(non_interactive=False) -> int:
    color = "NO_COLOR" not in os.environ and sys.stdout.isatty()
    started = time.perf_counter()
    results: list[dict[str, Any]] = []
    package: Any | None = None
    element: Win32Element | None = None
    attributes: dict[str, Any] | None = None
    original_foreground = _foreground_handle()
    original_mouse = helper.current_cursor()
    print('  运行模式: ' + ('自动复测' if non_interactive else '人工测试'))

    results.append(_check_contract())
    package_result, package = _current_package()
    results.append(package_result)
    if package_result["status"] == "PASS" and package is not None:
        prepare_result, element = _prepare_element(package)
        results.append(prepare_result)
    else:
        results.append(_blocked("element_prepare", "当前测试元素库不可用"))

    if element is not None:
        container_result, attributes = _read_attributes(element)
        results.append(container_result)
    else:
        results.append(_blocked("result_container", "靶场输入框不可用"))

    attribute_case_ids = [
        "tuple_structure",
        "unique_names",
        "string_attributes",
        "integer_attributes",
        "boolean_attributes",
        "runtime_id",
        "bounding_rectangle",
    ]
    if attributes is not None:
        structure_result = _check_tuple_structure(attributes)
        unique_result = _check_unique_names(attributes)
        results.extend([structure_result, unique_result])
        if structure_result["status"] == "PASS" and unique_result["status"] == "PASS":
            results.extend(
                [
                _check_string_attributes(attributes),
                _check_integer_attributes(attributes),
                _check_boolean_attributes(attributes),
                _check_runtime_id(attributes),
                _check_bounding_rectangle(attributes),
                ]
            )
        else:
            results.extend(
                _blocked(case_id, "属性字典键或属性名唯一性不符合合同")
                for case_id in attribute_case_ids[2:]
            )
    else:
        results.extend(_blocked(case_id, "属性字典不可用") for case_id in attribute_case_ids)

    if element is not None:
        results.append(_check_independent_results(element))
        results.append(_check_argument_rejection(element))
    else:
        results.append(_blocked("independent_results", "靶场输入框不可用"))
        results.append(_blocked("argument_rejection", "靶场输入框不可用"))

    results.append(_cleanup(package, original_foreground, original_mouse, non_interactive))

    _print_header(color=color)
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
    raise SystemExit(main(non_interactive=parse_run_options().non_interactive))
