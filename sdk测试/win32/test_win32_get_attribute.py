r"""``uiautoma.win32.Win32Element.get_attribute()`` 真实 UIA 属性测试。

API 参数（不是测试脚本参数）::

    Win32Element.get_attribute(name: str) -> str | None

参数规则：

* ``name``：必填，可作为位置或关键字参数；调用前会转换为字符串并去除首尾空格，
  UIA 属性名匹配忽略大小写。
* 空字符串、纯空格、``None`` 和 ``0`` 会抛出 ``InvalidParamsError``；包含
  ``< > \" ' ` ( ) ;`` 的属性名也会被 Runtime 拒绝。
* 非零整数会转换为字符串属性名；未知或控件不提供的属性返回None。
* 已有属性返回str；不存在时返回None。公开API没有timeout参数，底层读取超时固定为5秒。

测试脚本参数：--non-interactive 自动复测，焦点未恢复只警告、不等待人工。
默认人工模式，允许切回原Tabby窗口；恢复鼠标并释放Package。

脚本借用 UIAutoma 当前启用的 ``D:\code\元素库\260902_win元素``，使用
``win32靶场_表单控件_输入框_姓名`` 读取 Name、ClassName、ControlType、IsEnabled、IsPassword、
ProcessId、RuntimeId 和 BoundingRectangle，并覆盖关键字调用、属性名大小写与首尾空格、
未知属性、整数转换和非法参数。

本测试只读，不修改靶场控件；结束时恢复原前台窗口并关闭借用的 Package，Win32 靶场
保持运行。导入本模块不会连接 Runtime。

运行方式::

    uv run .\win32\test_win32_get_attribute.py
"""

from __future__ import annotations

from _form_tab import ensure_form_tab

import ctypes
import inspect
import json
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
UNKNOWN_ATTRIBUTE = "__uiautoma_missing_attribute__"

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
DETAIL_WIDTH = 80
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
    "name_attribute": "Name 属性",
    "class_keyword": "ClassName 关键字",
    "normalized_name": "大小写与空格",
    "control_type": "ControlType 属性",
    "boolean_attributes": "布尔属性",
    "process_id": "ProcessId 属性",
    "runtime_id": "RuntimeId 属性",
    "bounding_rectangle": "BoundingRectangle 属性",
    "unknown_attribute": "未知属性",
    "integer_name": "整数属性名",
    "empty_name": "空属性名",
    "invalid_characters": "非法字符",
    "argument_count": "参数数量限制",
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
        signature = inspect.signature(Win32Element.get_attribute)
        parameters = signature.parameters
        self_parameter = parameters.get("self")
        name_parameter = parameters.get("name")
        self_ok = (
            self_parameter is not None
            and self_parameter.kind is inspect.Parameter.POSITIONAL_OR_KEYWORD
            and self_parameter.default is inspect.Parameter.empty
        )
        name_ok = (
            name_parameter is not None
            and name_parameter.kind is inspect.Parameter.POSITIONAL_OR_KEYWORD
            and name_parameter.default is inspect.Parameter.empty
            and str(name_parameter.annotation) in {"str", "<class 'str'>"}
        )
        return_ok = str(signature.return_annotation) == "str | None"
        passed = tuple(parameters) == ("self", "name") and self_ok and name_ok and return_ok
        return _result(
            "api_contract",
            "PASS" if passed else "FAIL",
            (
                "公开签名为 get_attribute(name: str) -> str | None"
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
                (
                    "已获取输入框 Runtime 元素"
                    if passed
                    else "元素类型或元素库身份不符合预期"
                ),
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


def _read_case(
    case_id: str,
    element: Win32Element,
    *,
    invoke: Callable[[], object],
    validate: Callable[[str | None], bool],
    success_detail: str,
    call_text: str,
    expected: str,
    allow_none: bool = False,
) -> dict[str, Any]:
    started = time.perf_counter()
    try:
        old_result = element.last_result
        value = invoke()
        passed = (isinstance(value, str) or (allow_none and value is None)) and validate(value)
        passed = passed and element.last_result is old_result
        return _result(
            case_id,
            "PASS" if passed else "FAIL",
            success_detail if passed else "属性返回类型或属性值不符合预期",
            elapsed_ms=_elapsed(started),
            call=call_text,
            expected=expected,
            actual=value,
            return_type=type(value).__name__,
        )
    except Exception as exc:  # noqa: BLE001
        return _error_result(
            case_id,
            "get_attribute() 调用失败",
            started,
            exc,
            call=call_text,
            expected=expected,
        )


def _boolean_attributes(element: Win32Element) -> dict[str, Any]:
    started = time.perf_counter()
    try:
        enabled = element.get_attribute("IsEnabled")
        password = element.get_attribute("IsPassword")
        passed = enabled == "True" and password == "False"
        return _result(
            "boolean_attributes",
            "PASS" if passed else "FAIL",
            (
                "IsEnabled=True 且 IsPassword=False"
                if passed
                else "输入框布尔属性值不符合预期"
            ),
            elapsed_ms=_elapsed(started),
            enabled=enabled,
            password=password,
        )
    except Exception as exc:  # noqa: BLE001
        return _error_result("boolean_attributes", "读取输入框布尔属性失败", started, exc)


def _runtime_id_is_valid(value: str) -> bool:
    try:
        decoded = json.loads(value)
    except (TypeError, ValueError, json.JSONDecodeError):
        return False
    return (
        isinstance(decoded, list)
        and bool(decoded)
        and all(isinstance(item, int) and not isinstance(item, bool) for item in decoded)
    )


def _bounding_is_valid(value: str) -> bool:
    try:
        decoded = json.loads(value)
    except (TypeError, ValueError, json.JSONDecodeError):
        return False
    if not isinstance(decoded, dict) or set(decoded) != {"x", "y", "w", "h"}:
        return False
    return (
        all(isinstance(decoded[key], int) and not isinstance(decoded[key], bool) for key in decoded)
        and decoded["w"] > 0
        and decoded["h"] > 0
    )


def _expected_errors(
    case_id: str,
    success_detail: str,
    *,
    calls: list[tuple[str, Callable[[], object]]],
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


def _cleanup(package: Any | None, original_foreground: int, original_mouse, non_interactive) -> dict[str, Any]:
    started = time.perf_counter()
    errors: list[str] = []
    restored_foreground = False
    if original_foreground > 0:
        try:
            status = restore_focus_for_mode(original_foreground, non_interactive)
            print(f'  焦点恢复: {status}')
            restored_foreground = _foreground_handle() == original_foreground
        except Exception as exc:  # noqa: BLE001
            errors.append(f"恢复原前台窗口失败：{exc}")
    try:
        helper.restore_cursor(original_mouse)
    except Exception as exc:
        errors.append(f'恢复鼠标失败：{exc}')
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
        "鼠标已恢复，Package已关闭（如已取得）；靶场保留表单页，焦点状态单独报告",
        elapsed_ms=_elapsed(started),
        restored_foreground=restored_foreground,
    )


def _print_header(*, color: bool) -> None:
    print(_colorize("UIAutoma Win32 API 测试", "cyan", enabled=color))
    print()
    print("  API     : uiautoma.win32.Win32Element.get_attribute")
    print(f"  元素库  : {LIBRARY_DIR}")
    print(f"  测试元素: {TARGET_ELEMENT}")
    print(f"  测试窗口: {TARGET_TITLE}")
    print(f"  目标进程: {TARGET_PROCESS}")
    print("  属性范围: 字符串、数字、布尔、列表和矩形代表属性")
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
        if 'actual' in result:
            indent = ' ' * (PROGRESS_WIDTH + STATUS_WIDTH + CASE_WIDTH + 6)
            print(f"{indent}实际值: {result['actual']!r}；类型: {result.get('return_type')}")
        return
    indent = " " * (PROGRESS_WIDTH + STATUS_WIDTH + CASE_WIDTH + 6)
    if result.get("message"):
        print(f"{indent}{_pad('原因', 10)}: {result['message']}")
    if "actual" in result:
        print(f"{indent}{_pad('实际值', 10)}: {result.get('actual')!r}")
    if result.get("expected"):
        print(f"{indent}{_pad('预期', 10)}: {result['expected']}")
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

    scenario_ids = [
        "name_attribute",
        "class_keyword",
        "normalized_name",
        "control_type",
        "boolean_attributes",
        "process_id",
        "runtime_id",
        "bounding_rectangle",
        "unknown_attribute",
        "integer_name",
        "empty_name",
        "invalid_characters",
        "argument_count",
    ]
    if element is not None:
        results.extend(
            [
                _read_case(
                    "name_attribute",
                    element,
                    invoke=lambda: element.get_attribute("Name"),
                    validate=lambda value: value == "姓名",
                    success_detail='Name 返回 "姓名"',
                    call_text='element.get_attribute("Name")',
                    expected='"姓名"',
                ),
                _read_case(
                    "class_keyword",
                    element,
                    invoke=lambda: element.get_attribute(name="ClassName"),
                    validate=lambda value: value == "Edit",
                    success_detail='关键字参数 ClassName 返回 "Edit"',
                    call_text='element.get_attribute(name="ClassName")',
                    expected='"Edit"',
                ),
                _read_case(
                    "normalized_name",
                    element,
                    invoke=lambda: element.get_attribute("  classname  "),
                    validate=lambda value: value == "Edit",
                    success_detail="属性名首尾空格和大小写已正确归一化",
                    call_text='element.get_attribute("  classname  ")',
                    expected='"Edit"',
                ),
                _read_case(
                    "control_type",
                    element,
                    invoke=lambda: element.get_attribute("ControlType"),
                    validate=lambda value: value == "50004",
                    success_detail="ControlType 返回 Edit 控件的 UIA 属性 ID 50004",
                    call_text='element.get_attribute("ControlType")',
                    expected='"50004"',
                ),
                _boolean_attributes(element),
                _read_case(
                    "process_id",
                    element,
                    invoke=lambda: element.get_attribute("ProcessId"),
                    validate=lambda value: value.isdecimal() and int(value) > 0,
                    success_detail="ProcessId 返回有效的正整数文本",
                    call_text='element.get_attribute("ProcessId")',
                    expected="正整数文本",
                ),
                _read_case(
                    "runtime_id",
                    element,
                    invoke=lambda: element.get_attribute("RuntimeId"),
                    validate=_runtime_id_is_valid,
                    success_detail="RuntimeId 返回可解析的非空整数数组文本",
                    call_text='element.get_attribute("RuntimeId")',
                    expected="JSON 整数数组",
                ),
                _read_case(
                    "bounding_rectangle",
                    element,
                    invoke=lambda: element.get_attribute("BoundingRectangle"),
                    validate=_bounding_is_valid,
                    success_detail="BoundingRectangle 返回宽高有效的 JSON 矩形文本",
                    call_text='element.get_attribute("BoundingRectangle")',
                    expected='{"x":int,"y":int,"w":正整数,"h":正整数}',
                ),
                _read_case(
                    "unknown_attribute",
                    element,
                    invoke=lambda: element.get_attribute(UNKNOWN_ATTRIBUTE),
                    validate=lambda value: value is None,
                    allow_none=True,
                    success_detail="未知属性返回None",
                    call_text=f"element.get_attribute({UNKNOWN_ATTRIBUTE!r})",
                    expected='None',
                ),
                _read_case(
                    "integer_name",
                    element,
                    invoke=lambda: element.get_attribute(123),  # type: ignore[arg-type]
                    validate=lambda value: value is None,
                    allow_none=True,
                    success_detail="非零整数转换为未知属性名，返回None",
                    call_text="element.get_attribute(123)",
                    expected='None',
                ),
                _expected_errors(
                    "empty_name",
                    "空字符串、纯空格、None 和 0 均被 InvalidParamsError 正确拒绝",
                    calls=[
                        ("空字符串", lambda: element.get_attribute("")),
                        ("纯空格", lambda: element.get_attribute("   ")),
                        ("None", lambda: element.get_attribute(None)),  # type: ignore[arg-type]
                        ("0", lambda: element.get_attribute(0)),  # type: ignore[arg-type]
                    ],
                    expected_exception="InvalidParamsError",
                ),
                _expected_errors(
                    "invalid_characters",
                    "八种脚本特殊字符均被 InvalidParamsError 正确拒绝",
                    calls=[
                        (
                            repr(character),
                            lambda character=character: element.get_attribute(
                                f"Name{character}"
                            ),
                        )
                        for character in ("<", ">", '"', "'", "`", "(", ")", ";")
                    ],
                    expected_exception="InvalidParamsError",
                ),
                _expected_errors(
                    "argument_count",
                    "缺少 name、多余位置参数和 timeout 关键字均被 TypeError 正确拒绝",
                    calls=[
                        ("缺少 name", lambda: element.get_attribute()),  # type: ignore[call-arg]
                        (
                            "多余位置参数",
                            lambda: element.get_attribute("Name", 1),  # type: ignore[call-arg]
                        ),
                        (
                            "不支持 timeout",
                            lambda: element.get_attribute("Name", timeout=1),  # type: ignore[call-arg]
                        ),
                    ],
                    expected_exception="TypeError",
                ),
            ]
        )
    else:
        results.extend(_blocked(case_id, "靶场输入框不可用") for case_id in scenario_ids)

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
