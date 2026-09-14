r"""``uiautoma.win32.Win32Element.set_value()`` 真实输入框值测试。

API 参数（不是测试脚本参数）::

    Win32Element.set_value(value: str) -> None

参数规则：

* ``value``：必填，可作为位置或关键字参数传入。公开注解为 ``str``，当前实现会先
  调用 ``str(value)``，因此整数等可字符串化对象也会作为对应字符串写入。
* ``set_value`` 使用 automation 模式覆盖元素完整值，不追加内容、不点击元素，且
  没有公开的 ``timeout`` 或 ``delay_after`` 参数。
* 成功返回 ``None``，动作详情写入元素的 ``last_result``；动作失败抛出
  ``ActionError``。

测试脚本参数：无。

脚本借用 UIAutoma 当前启用的 ``D:\code\元素库\260902_win元素``，使用
``win32靶场_表单控件_输入框_姓名`` 验证普通字符串、中文与符号、关键字调用、整数转字符串和空值
清空，并使用 ``win32靶场_表单控件_按钮_保存`` 验证不支持设置值的控件会失败。每次成功写入后
都通过 ``get_value()`` 和 ``last_result`` 校验结果。

测试会真实修改输入框内容。运行前会记录原值和原前台窗口，结束时恢复输入框原值与
前台窗口，只关闭借用的 Package；Win32 靶场保持运行。导入本模块不会连接 Runtime
或修改界面。

运行方式::

    uv run .\win32\test_win32_set_value.py
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


__test__ = False

LIBRARY_DIR = Path(r"D:\code\元素库\260902_win元素")
TARGET_ELEMENT = "win32靶场_表单控件_输入框_姓名"
UNSUPPORTED_ELEMENT = "win32靶场_表单控件_按钮_保存"
TARGET_TITLE = "Win32 靶场 - UIA"
TARGET_PROCESS = "win32-shooting-range-uia.exe"

PLAIN_VALUE = "UIAutoma_SetValue_Alpha_123"
UNICODE_VALUE = "中文_SetValue_Ω_!@#"
KEYWORD_VALUE = "keyword_value_260907"
INTEGER_VALUE = 20260907

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
    "plain_string": "普通字符串",
    "unicode_symbols": "中文与符号",
    "keyword_value": "关键字调用",
    "integer_conversion": "整数转换",
    "empty_string": "空字符串清空",
    "unsupported_control": "不支持的控件",
    "argument_count": "参数数量限制",
    "resource_cleanup": "状态与资源恢复",
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


def _preview(value: object, limit: int = 48) -> str:
    text = repr(str(value))
    return text if len(text) <= limit else f"{text[: limit - 3]}..."


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
        signature = inspect.signature(Win32Element.set_value)
        parameters = signature.parameters
        self_parameter = parameters.get("self")
        value_parameter = parameters.get("value")
        self_ok = (
            self_parameter is not None
            and self_parameter.kind is inspect.Parameter.POSITIONAL_OR_KEYWORD
            and self_parameter.default is inspect.Parameter.empty
        )
        value_ok = (
            value_parameter is not None
            and value_parameter.kind is inspect.Parameter.POSITIONAL_OR_KEYWORD
            and value_parameter.default is inspect.Parameter.empty
            and str(value_parameter.annotation) in {"str", "<class 'str'>"}
        )
        return_ok = str(signature.return_annotation) in {"None", "<class 'NoneType'>"}
        passed = tuple(parameters) == ("self", "value") and self_ok and value_ok and return_ok
        return _result(
            "api_contract",
            "PASS" if passed else "FAIL",
            (
                "公开签名为 set_value(value: str) -> None"
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


def _prepare_elements(
    package: Any,
) -> tuple[dict[str, Any], Win32Element | None, Win32Element | None, str | None]:
    started = time.perf_counter()
    try:
        input_selector = package.selector(TARGET_ELEMENT, kind="win")
        button_selector = package.selector(UNSUPPORTED_ELEMENT, kind="win")
        element = win32.find(input_selector, timeout=10)
        button = win32.find(button_selector, timeout=10)
        original_value = element.get_value()
        passed = (
            isinstance(element, Win32Element)
            and isinstance(button, Win32Element)
            and isinstance(original_value, str)
            and str(element.raw.get("source_element_id") or "") == input_selector.id()
            and str(button.raw.get("source_element_id") or "") == button_selector.id()
        )
        return (
            _result(
                "element_prepare",
                "PASS" if passed else "FAIL",
                (
                    "已获取输入框、保存按钮并记录输入框原值"
                    if passed
                    else "元素类型、元素库身份或原值不符合预期"
                ),
                elapsed_ms=_elapsed(started),
                original_value=original_value,
                input_id=element.id,
                button_id=button.id,
            ),
            element if passed else None,
            button if passed else None,
            original_value if passed else None,
        )
    except Exception as exc:  # noqa: BLE001
        return (
            _error_result("element_prepare", "获取靶场输入框或保存按钮失败", started, exc),
            None,
            None,
            None,
        )


def _run_set_case(
    case_id: str,
    element: Win32Element,
    *,
    invoke: Callable[[], object],
    expected_value: str,
    success_detail: str,
    call_text: str,
) -> dict[str, Any]:
    started = time.perf_counter()
    previous_result = element.last_result
    try:
        returned = invoke()
        actual_value = element.get_value()
        action_result = element.last_result
        passed = (
            returned is None
            and action_result is not None
            and action_result is not previous_result
            and action_result.ok
            and action_result.strategy == "win_value_pattern"
            and action_result.clicked_point is None
            and actual_value == expected_value
        )
        return _result(
            case_id,
            "PASS" if passed else "FAIL",
            success_detail if passed else "返回值、实际值或 last_result 不符合预期",
            elapsed_ms=_elapsed(started),
            call=call_text,
            expected_value=expected_value,
            actual_value=actual_value,
            returned=returned,
            result_ok=action_result.ok if action_result is not None else None,
            strategy=action_result.strategy if action_result is not None else "",
            clicked_point=action_result.clicked_point if action_result is not None else None,
        )
    except Exception as exc:  # noqa: BLE001
        return _error_result(
            case_id,
            "set_value() 调用或结果读取失败",
            started,
            exc,
            call=call_text,
            expected_value=expected_value,
        )


def _check_unsupported_control(button: Win32Element) -> dict[str, Any]:
    started = time.perf_counter()
    try:
        button.set_value("should_not_succeed")
    except Exception as exc:  # noqa: BLE001
        action_result = button.last_result
        passed = (
            exc.__class__.__name__ == "ActionError"
            and action_result is not None
            and not action_result.ok
        )
        return _result(
            "unsupported_control",
            "PASS" if passed else _error_status(exc),
            (
                "保存按钮不支持设置值，正确抛出 ActionError"
                if passed
                else "保存按钮抛出的异常或 last_result 不符合预期"
            ),
            elapsed_ms=_elapsed(started),
            expected_exception="ActionError",
            result_ok=action_result.ok if action_result is not None else None,
            strategy=action_result.strategy if action_result is not None else "",
            **_error_fields(exc),
        )
    return _result(
        "unsupported_control",
        "FAIL",
        "保存按钮意外接受了 set_value()",
        elapsed_ms=_elapsed(started),
        expected_exception="ActionError",
    )


def _check_argument_count(element: Win32Element) -> dict[str, Any]:
    started = time.perf_counter()
    previous_result = element.last_result
    calls: list[tuple[str, Callable[[], object]]] = [
        ("缺少 value", lambda: element.set_value()),  # type: ignore[call-arg]
        ("多余位置参数", lambda: element.set_value("one", "two")),  # type: ignore[call-arg]
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
                    "last_result_unchanged": element.last_result is previous_result,
                }
            )
        else:
            outcomes.append(
                {
                    "label": label,
                    "exception": None,
                    "message": "未抛出异常",
                    "last_result_unchanged": element.last_result is previous_result,
                }
            )
    passed = all(
        item["exception"] == "TypeError" and item["last_result_unchanged"] is True
        for item in outcomes
    )
    return _result(
        "argument_count",
        "PASS" if passed else "FAIL",
        (
            "缺少 value 和传入多余参数均在动作前被 TypeError 拒绝"
            if passed
            else "部分错误调用未按合同被拒绝"
        ),
        elapsed_ms=_elapsed(started),
        expected_exception="TypeError",
        outcomes=outcomes,
    )


def _cleanup(
    package: Any | None,
    element: Win32Element | None,
    original_value: str | None,
    original_foreground: int,
) -> dict[str, Any]:
    started = time.perf_counter()
    errors: list[str] = []
    restored_value = False
    restored_foreground = False

    if element is not None and original_value is not None:
        try:
            element.set_value(original_value)
            restored_value = element.get_value() == original_value
            if not restored_value:
                errors.append(
                    f"输入框原值未恢复：期望 {_preview(original_value)}，实际 {_preview(element.get_value())}"
                )
        except Exception as exc:  # noqa: BLE001
            errors.append(f"恢复输入框原值失败：{exc}")

    if original_foreground > 0:
        try:
            _restore_foreground(original_foreground)
            restored_foreground = _foreground_handle() == original_foreground
        except Exception as exc:  # noqa: BLE001
            errors.append(f"恢复原前台窗口失败：{exc}")

    if package is not None:
        try:
            package.close()
        except Exception as exc:  # noqa: BLE001
            errors.append(f"关闭 Package 失败：{exc}")

    if errors:
        return _result(
            "resource_cleanup",
            "FAIL",
            "输入框状态或测试资源未完全恢复",
            elapsed_ms=_elapsed(started),
            message="；".join(errors),
            restored_value=restored_value,
            restored_foreground=restored_foreground,
        )
    return _result(
        "resource_cleanup",
        "PASS",
        "输入框原值和原前台窗口已恢复，Package 已关闭；靶场保持运行",
        elapsed_ms=_elapsed(started),
        restored_value=restored_value,
        restored_foreground=restored_foreground,
    )


def _print_header(original_value: str | None, *, color: bool) -> None:
    print(_colorize("UIAutoma Win32 API 测试", "cyan", enabled=color))
    print()
    print("  API     : uiautoma.win32.Win32Element.set_value")
    print(f"  元素库  : {LIBRARY_DIR}")
    print(f"  测试元素: {TARGET_ELEMENT}")
    print(f"  异常控件: {UNSUPPORTED_ELEMENT}")
    print(f"  测试窗口: {TARGET_TITLE}")
    print(f"  目标进程: {TARGET_PROCESS}")
    print(f"  原始值  : {_preview(original_value) if original_value is not None else '未读取'}")
    print("  写入校验: get_value() + last_result，且不应产生点击坐标")
    print("  状态恢复: 测试结束后恢复输入框原值和原前台窗口")
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
    if result.get("actual_value") is not None:
        print(f"{indent}{_pad('实际值', 10)}: {_preview(result['actual_value'])}")
    if result.get("strategy"):
        print(f"{indent}{_pad('策略', 10)}: {result['strategy']}")
    for outcome in result.get("outcomes") or []:
        if (
            outcome.get("exception") != result.get("expected_exception")
            or outcome.get("last_result_unchanged") is not True
        ):
            print(
                f"{indent}{_pad(str(outcome.get('label') or '参数'), 10)}: "
                f"{outcome.get('exception') or '未抛出异常'} {outcome.get('message') or ''}"
            )


def main() -> int:
    color = "NO_COLOR" not in os.environ and sys.stdout.isatty()
    started = time.perf_counter()
    results: list[dict[str, Any]] = []
    package: Any | None = None
    element: Win32Element | None = None
    button: Win32Element | None = None
    original_value: str | None = None
    original_foreground = _foreground_handle()

    results.append(_check_contract())
    package_result, package = _current_package()
    results.append(package_result)

    if package_result["status"] == "PASS" and package is not None:
        prepare_result, element, button, original_value = _prepare_elements(package)
        results.append(prepare_result)
    else:
        results.append(_blocked("element_prepare", "当前测试元素库不可用"))

    scenario_ids = [
        "plain_string",
        "unicode_symbols",
        "keyword_value",
        "integer_conversion",
        "empty_string",
        "unsupported_control",
        "argument_count",
    ]
    if element is not None and button is not None:
        results.extend(
            [
                _run_set_case(
                    "plain_string",
                    element,
                    invoke=lambda: element.set_value(PLAIN_VALUE),
                    expected_value=PLAIN_VALUE,
                    success_detail="位置参数已覆盖写入普通字符串",
                    call_text=f"element.set_value({PLAIN_VALUE!r})",
                ),
                _run_set_case(
                    "unicode_symbols",
                    element,
                    invoke=lambda: element.set_value(UNICODE_VALUE),
                    expected_value=UNICODE_VALUE,
                    success_detail="中文、希腊字母和符号均被完整写入",
                    call_text=f"element.set_value({UNICODE_VALUE!r})",
                ),
                _run_set_case(
                    "keyword_value",
                    element,
                    invoke=lambda: element.set_value(value=KEYWORD_VALUE),
                    expected_value=KEYWORD_VALUE,
                    success_detail="value 关键字参数已覆盖写入目标值",
                    call_text=f"element.set_value(value={KEYWORD_VALUE!r})",
                ),
                _run_set_case(
                    "integer_conversion",
                    element,
                    invoke=lambda: element.set_value(INTEGER_VALUE),  # type: ignore[arg-type]
                    expected_value=str(INTEGER_VALUE),
                    success_detail="整数 value 已通过 str() 转换后写入",
                    call_text=f"element.set_value({INTEGER_VALUE})",
                ),
                _run_set_case(
                    "empty_string",
                    element,
                    invoke=lambda: element.set_value(""),
                    expected_value="",
                    success_detail="空字符串已清空输入框完整值",
                    call_text='element.set_value("")',
                ),
                _check_unsupported_control(button),
                _check_argument_count(element),
            ]
        )
    else:
        results.extend(_blocked(case_id, "靶场输入框或保存按钮不可用") for case_id in scenario_ids)

    results.append(_cleanup(package, element, original_value, original_foreground))

    _print_header(original_value, color=color)
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
