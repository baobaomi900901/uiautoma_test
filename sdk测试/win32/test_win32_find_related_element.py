r"""``uiautoma.win32.Win32Element.find_related_element()`` 持久化真实元素库测试。

API 参数（不是测试脚本参数）::

    Win32Element.find_related_element(
        selector: str | Selector,
        *,
        timeout: float = 20,
    ) -> Win32Element

参数规则：

* ``selector``：必填，可作为位置或关键字参数传入；支持元素名称字符串或 Win32
  ``Selector``，不接受字典、``Win32Element``、其他类型或 Web ``Selector``。
* ``timeout``：仅限关键字，单位秒；默认 ``20``，``0`` 只查一次，正数在期限内
  查找；负数或非数字值会抛出 ``InvalidParamsError``。
* 搜索范围：先在当前 Package 中把 ``selector`` 解析为唯一的已保存 Win32 元素，
  再把搜索范围限制到调用元素的 UIA 子树。
* 返回值：子树中唯一命中时返回 ``Win32Element``；未找到抛出
  ``ElementNotFoundError``；命中多个元素抛出 ``AmbiguousElementError``。

测试脚本参数：--non-interactive 自动模式，焦点恢复失败只警告、不等待人工。
timeout=None使用底层默认值，数字字符串按当前SDK转换为秒数；包含对应调用检查。

脚本借用 UIAutoma 当前启用的 ``D:\code\元素库\260902_win元素``，使用
``win32靶场_表单控件_表单面板`` 作为来源元素，查找其子树中的 ``win32靶场_表单控件_输入框_姓名`` 和
``win32靶场_表单控件_按钮_保存``。另外使用输入框查找同级保存按钮，验证目标虽然存在于
Package 中，但不属于调用元素子树时会报告未找到。

当前测试元素名称均唯一，因此本轮不修改元素库制造重复项，也不宣称已经验证
``AmbiguousElementError``。准备阶段切换表单页；查询不修改控件内容。结束恢复鼠标及
前台并关闭借用的 Package；自动模式前台未恢复记录警告。Win32靶场保留表单页。
导入本模块不会连接 Runtime。

运行方式::

    uv run .\win32\test_win32_find_related_element.py
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
from uiautoma.win32 import Win32Element
import test_win32_get_value as helper
from test_win32_highlight import restore_focus_for_mode, parse_run_options


__test__ = False

LIBRARY_DIR = Path(r"D:\code\元素库\260902_win元素")
SOURCE_ELEMENT = "win32靶场_表单控件_表单面板"
INPUT_ELEMENT = "win32靶场_表单控件_输入框_姓名"
SAVE_ELEMENT = "win32靶场_表单控件_按钮_保存"
TARGET_TITLE = "Win32 靶场 - UIA"
TARGET_PROCESS = "win32-shooting-range-uia.exe"
MISSING_ELEMENT = "__uiautoma_find_related_element_missing__"

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
DETAIL_WIDTH = 76
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
    "source_elements": "来源元素准备",
    "string_default": "名称与默认超时",
    "selector_zero": "Selector 与零超时",
    "keyword_positive": "关键字与正数超时",
    "timeout_none": "None 超时",
    "timeout_string": "数字字符串超时",
    "outside_subtree": "子树外目标",
    "missing_package": "Package 缺失目标",
    "invalid_selector": "非法选择器类型",
    "element_selector": "Win32Element 被拒绝",
    "wrong_framework": "非 Win Selector",
    "keyword_only_timeout": "timeout 仅限关键字",
    "invalid_timeout": "非法超时",
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
        signature = inspect.signature(Win32Element.find_related_element)
        parameters = signature.parameters
        self_parameter = parameters.get("self")
        selector_parameter = parameters.get("selector")
        timeout_parameter = parameters.get("timeout")
        order_ok = tuple(parameters) == ("self", "selector", "timeout")
        self_ok = (
            self_parameter is not None
            and self_parameter.kind is inspect.Parameter.POSITIONAL_OR_KEYWORD
            and self_parameter.default is inspect.Parameter.empty
        )
        selector_annotation = str(selector_parameter.annotation) if selector_parameter else ""
        selector_ok = (
            selector_parameter is not None
            and selector_parameter.kind is inspect.Parameter.POSITIONAL_OR_KEYWORD
            and selector_parameter.default is inspect.Parameter.empty
            and "str" in selector_annotation
            and "Selector" in selector_annotation
        )
        timeout_ok = (
            timeout_parameter is not None
            and timeout_parameter.kind is inspect.Parameter.KEYWORD_ONLY
            and timeout_parameter.default == 20
        )
        return_ok = "Win32Element" in str(signature.return_annotation)
        passed = order_ok and self_ok and selector_ok and timeout_ok and return_ok
        return _result(
            "api_contract",
            "PASS" if passed else "FAIL",
            (
                "公开签名为 find_related_element(selector: str | Selector, *, timeout=20)"
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
) -> tuple[
    dict[str, Any],
    Win32Element | None,
    Win32Element | None,
    dict[str, Selector],
]:
    started = time.perf_counter()
    try:
        selectors = {
            "source": package.selector(SOURCE_ELEMENT, kind="win"),
            "input": package.selector(INPUT_ELEMENT, kind="win"),
            "save": package.selector(SAVE_ELEMENT, kind="win"),
        }
        panel = win32.find(SOURCE_ELEMENT, timeout=10)
        input_element = win32.find(INPUT_ELEMENT, timeout=10)
        panel_source_id = str(panel.raw.get("source_element_id") or "")
        input_source_id = str(input_element.raw.get("source_element_id") or "")
        passed = (
            isinstance(panel, Win32Element)
            and isinstance(input_element, Win32Element)
            and panel.id.startswith("rt:win:")
            and input_element.id.startswith("rt:win:")
            and panel_source_id == selectors["source"].id()
            and input_source_id == selectors["input"].id()
        )
        return (
            _result(
                "source_elements",
                "PASS" if passed else "FAIL",
                (
                    "已获取表单面板和输入框 Runtime 元素"
                    if passed
                    else "来源元素类型或元素库身份不符合预期"
                ),
                elapsed_ms=_elapsed(started),
                panel_id=panel.id,
                input_id=input_element.id,
                panel_source_id=panel_source_id,
                input_source_id=input_source_id,
            ),
            panel if passed else None,
            input_element if passed else None,
            selectors if passed else {},
        )
    except Exception as exc:  # noqa: BLE001
        return (
            _error_result("source_elements", "准备来源元素和目标 Selector 失败", started, exc),
            None,
            None,
            {},
        )


def _element_info(element: object) -> dict[str, Any]:
    if not isinstance(element, Win32Element):
        return {
            "is_element": False,
            "id": "",
            "source_element_id": "",
            "relation": "",
            "name": "",
        }
    return {
        "is_element": True,
        "id": str(element.id),
        "source_element_id": str(element.raw.get("source_element_id") or ""),
        "relation": str(element.raw.get("relation") or ""),
        "name": str(element.name or ""),
    }


def _run_success_case(
    case_id: str,
    success_detail: str,
    *,
    call: Callable[[], object],
    expected_name: str,
    expected_source_id: str,
) -> dict[str, Any]:
    started = time.perf_counter()
    try:
        related = call()
        info = _element_info(related)
        passed = (
            info["is_element"]
            and info["id"].startswith("rt:win:")
            and info["source_element_id"] == expected_source_id
            and info["relation"].casefold() == "find_related"
            and info["name"] == expected_name
        )
        return _result(
            case_id,
            "PASS" if passed else "FAIL",
            success_detail if passed else "返回类型、目标身份或关联关系不符合预期",
            elapsed_ms=_elapsed(started),
            **info,
        )
    except Exception as exc:  # noqa: BLE001
        return _error_result(case_id, "find_related_element() 调用失败", started, exc)


def _run_expected_error(
    case_id: str,
    success_detail: str,
    *,
    call: Callable[[], object],
    expected_exception: str,
) -> dict[str, Any]:
    started = time.perf_counter()
    try:
        call()
    except Exception as exc:  # noqa: BLE001
        passed = exc.__class__.__name__ == expected_exception
        return _result(
            case_id,
            "PASS" if passed else _error_status(exc),
            success_detail if passed else "抛出的异常类型不符合预期",
            elapsed_ms=_elapsed(started),
            expected_exception=expected_exception,
            **_error_fields(exc),
        )
    return _result(
        case_id,
        "FAIL",
        f"未抛出预期的 {expected_exception}",
        elapsed_ms=_elapsed(started),
        expected_exception=expected_exception,
    )


def _run_expected_errors(
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
        success_detail if passed else f"部分参数未抛出预期的 {expected_exception}",
        elapsed_ms=_elapsed(started),
        expected_exception=expected_exception,
        outcomes=outcomes,
    )


def _cleanup_package(package: Any | None, mouse, foreground, non_interactive) -> dict[str, Any]:
    started = time.perf_counter()
    errors = []
    def focus():
        status = restore_focus_for_mode(foreground, non_interactive)
        print(f"  焦点恢复: {status}")
    actions = [('前台', focus), ('鼠标', lambda: helper.restore_cursor(mouse))]
    if package is not None:
        actions.append(('Package', package.close))
    for name, action in actions:
        try:
            action()
        except Exception as exc:
            errors.append(f'{name}: {type(exc).__name__}: {exc}')
    return _result('resource_cleanup', 'FAIL' if errors else 'PASS',
                   '必要清理失败' if errors else '鼠标已恢复，Package已释放（如已取得），靶场保持运行',
                   elapsed_ms=_elapsed(started), message='；'.join(errors))


def _print_header(*, color: bool) -> None:
    print(_colorize("UIAutoma Win32 API 测试", "cyan", enabled=color))
    print()
    print("  API     : uiautoma.win32.Win32Element.find_related_element")
    print(f"  元素库  : {LIBRARY_DIR}")
    print(f"  来源元素: {SOURCE_ELEMENT}")
    print(f"  目标一  : {INPUT_ELEMENT}")
    print(f"  目标二  : {SAVE_ELEMENT}")
    print(f"  测试窗口: {TARGET_TITLE}")
    print(f"  目标进程: {TARGET_PROCESS}")
    print("  搜索范围: 仅限调用元素的 UIA 子树")
    print("  覆盖说明: 元素名称唯一；本轮不验证 AmbiguousElementError")
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
        if result.get('source_element_id'):
            indent = ' ' * (PROGRESS_WIDTH + STATUS_WIDTH + CASE_WIDTH + 6)
            print(f"{indent}返回元素: {result.get('name')}；source_id={result['source_element_id']}；relation={result.get('relation')}")
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


def main(non_interactive=False) -> int:
    color = "NO_COLOR" not in os.environ and sys.stdout.isatty()
    _print_header(color=color)
    started = time.perf_counter()
    results: list[dict[str, Any]] = []
    package: Any | None = None
    mouse, foreground = helper.current_cursor(), helper.current_foreground()
    print('  运行模式: ' + ('自动复测' if non_interactive else '人工测试'))

    results.append(_check_contract())
    package_result, package = _current_package()
    results.append(package_result)

    panel: Win32Element | None = None
    input_element: Win32Element | None = None
    selectors: dict[str, Selector] = {}
    if package_result["status"] == "PASS" and package is not None:
        source_result, panel, input_element, selectors = _prepare_elements(package)
        results.append(source_result)
    else:
        results.append(_blocked_case("source_elements", "当前测试元素库不可用"))

    scenario_ids = [
        "string_default",
        "selector_zero",
        "keyword_positive",
        "timeout_none",
        "timeout_string",
        "outside_subtree",
        "missing_package",
        "invalid_selector",
        "element_selector",
        "wrong_framework",
        "keyword_only_timeout",
        "invalid_timeout",
    ]
    if panel is not None and input_element is not None and selectors:
        input_selector = selectors["input"]
        save_selector = selectors["save"]
        results.extend(
            [
                _run_success_case(
                    "string_default",
                    "名称字符串与默认 timeout=20 返回输入框关联元素",
                    call=lambda: panel.find_related_element(INPUT_ELEMENT),
                    expected_name=INPUT_ELEMENT,
                    expected_source_id=input_selector.id(),
                ),
                _run_success_case(
                    "selector_zero",
                    "Win32 Selector 与 timeout=0 单次查询返回输入框",
                    call=lambda: panel.find_related_element(input_selector, timeout=0),
                    expected_name=INPUT_ELEMENT,
                    expected_source_id=input_selector.id(),
                ),
                _run_success_case(
                    "keyword_positive",
                    "selector 关键字与 timeout=2 返回保存按钮关联元素",
                    call=lambda: panel.find_related_element(selector=save_selector, timeout=2),
                    expected_name=SAVE_ELEMENT,
                    expected_source_id=save_selector.id(),
                ),
                _run_expected_error(
                    "outside_subtree",
                    "保存按钮存在于 Package，但不在输入框子树中，正确报告未找到",
                    call=lambda: input_element.find_related_element(save_selector, timeout=0),
                    expected_exception="ElementNotFoundError",
                ),
                _run_expected_error(
                    "missing_package",
                    "Package 中不存在的元素名称被正确识别为未找到",
                    call=lambda: panel.find_related_element(MISSING_ELEMENT, timeout=0),
                    expected_exception="ElementNotFoundError",
                ),
                _run_expected_errors(
                    "invalid_selector",
                    "列表和整数 selector 均被 InvalidParamsError 正确拒绝",
                    calls=[
                        ("字典", lambda: panel.find_related_element({'name': INPUT_ELEMENT}, timeout=0)),
                        ("None", lambda: panel.find_related_element(None, timeout=0)),
                        (
                            "列表",
                            lambda: panel.find_related_element([INPUT_ELEMENT], timeout=0),  # type: ignore[arg-type]
                        ),
                        (
                            "整数",
                            lambda: panel.find_related_element(123, timeout=0),  # type: ignore[arg-type]
                        ),
                    ],
                    expected_exception="InvalidParamsError",
                ),
                _run_expected_error(
                    "element_selector",
                    "真实 Win32Element 被 InvalidParamsError 正确拒绝",
                    call=lambda: panel.find_related_element(input_element, timeout=0),  # type: ignore[arg-type]
                    expected_exception="InvalidParamsError",
                ),
                _run_expected_error(
                    "wrong_framework",
                    "Web Selector 被 InvalidParamsError 正确拒绝",
                    call=lambda: panel.find_related_element(
                        Selector(
                            name="web测试选择器",
                            framework="web",
                            item_id=input_selector.id(),
                        ),
                        timeout=0,
                    ),
                    expected_exception="InvalidParamsError",
                ),
                _run_expected_error(
                    "keyword_only_timeout",
                    "timeout 作为额外位置参数时被 TypeError 正确拒绝",
                    call=lambda: panel.find_related_element(input_selector, 0),  # type: ignore[misc]
                    expected_exception="TypeError",
                ),
                _run_expected_errors(
                    "invalid_timeout",
                    "负数和非数字 timeout 均被 InvalidParamsError 正确拒绝",
                    calls=[
                        (
                            "负数",
                            lambda: panel.find_related_element(input_selector, timeout=-1),
                        ),
                        (
                            "非数字",
                            lambda: panel.find_related_element(input_selector, timeout="bad"),  # type: ignore[arg-type]
                        ),
                    ],
                    expected_exception="InvalidParamsError",
                ),
            ]
        )
        # 正常路径新增两种当前SDK支持的超时转换；不固化实际耗时。
        for case_id, timeout in [('timeout_none', None), ('timeout_string', '0.5')]:
            result = _run_success_case(
                case_id, f'timeout={timeout!r} 返回输入框关联元素',
                call=lambda value=timeout: panel.find_related_element(input_selector, timeout=value),
                expected_name=INPUT_ELEMENT, expected_source_id=input_selector.id(),
            )
            # 与表头顺序保持一致，放在三项标准成功调用之后。
            results.insert(6 if case_id == 'timeout_none' else 7, result)
    else:
        reason = "来源元素或测试 Selector 不可用"
        results.extend(_blocked_case(case_id, reason) for case_id in scenario_ids)

    results.append(_cleanup_package(package, mouse, foreground, non_interactive))

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
