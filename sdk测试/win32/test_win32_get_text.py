r"""``uiautoma.win32.Win32Element.get_text()`` 真实 UIA 文本测试。

API 参数（不是测试脚本参数）::

    Win32Element.get_text() -> str

高层 ``get_text()`` 没有公开参数，内部读取超时固定为 5 秒。Runtime 优先读取
元素的 UIA ``Name``；当 ``Name`` 为空时，才回退到控件值。返回值统一为 ``str``。

测试脚本参数：无。

脚本借用 UIAutoma 当前启用的 ``D:\code\元素库\260902_win元素``，使用元素库名称
``win32靶场_表单控件_标题`` 获取靶场标题元素，并验证其实时文本为“用户信息表单”。元素库名称
用于定位元素，不等同于 ``get_text()`` 返回的实时 UIA 文本。

本测试只读，不修改靶场控件；结束时恢复原前台窗口并关闭借用的 Package，Win32 靶场
保持运行。导入本模块不会连接 Runtime。

运行方式::

    uv run .\win32\test_win32_get_text.py
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
TARGET_ELEMENT = "win32靶场_表单控件_标题"
EXPECTED_TEXT = "用户信息表单"
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
CASE_WIDTH = 18
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
    "element_prepare": "标题元素准备",
    "exact_text": "实时文本",
    "return_type": "返回类型",
    "repeat_read": "重复读取",
    "argument_rejection": "参数数量限制",
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
        signature = inspect.signature(Win32Element.get_text)
        parameters = signature.parameters
        self_parameter = parameters.get("self")
        self_ok = (
            self_parameter is not None
            and self_parameter.kind is inspect.Parameter.POSITIONAL_OR_KEYWORD
            and self_parameter.default is inspect.Parameter.empty
        )
        return_ok = str(signature.return_annotation) in {"str", "<class 'str'>"}
        passed = tuple(parameters) == ("self",) and self_ok and return_ok
        return _result(
            "api_contract",
            "PASS" if passed else "FAIL",
            (
                "公开签名无参数并返回 str"
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
                    "已由元素库名称获取标题 Runtime 元素"
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
            _error_result("element_prepare", "获取靶场标题元素失败", started, exc),
            None,
        )


def _read_exact_text(element: Win32Element) -> tuple[dict[str, Any], object | None]:
    started = time.perf_counter()
    try:
        value = element.get_text()
        passed = value == EXPECTED_TEXT
        return (
            _result(
                "exact_text",
                "PASS" if passed else "FAIL",
                (
                    f'get_text() 返回实时文本“{EXPECTED_TEXT}”'
                    if passed
                    else "get_text() 返回的实时文本不符合预期"
                ),
                elapsed_ms=_elapsed(started),
                expected=EXPECTED_TEXT,
                actual=value,
                return_type=type(value).__name__,
            ),
            value,
        )
    except Exception as exc:  # noqa: BLE001
        return (
            _error_result("exact_text", "get_text() 调用失败", started, exc),
            None,
        )


def _check_return_type(value: object | None) -> dict[str, Any]:
    started = time.perf_counter()
    passed = isinstance(value, str)
    return _result(
        "return_type",
        "PASS" if passed else "FAIL",
        "返回值为 str" if passed else "返回值不是 str",
        elapsed_ms=_elapsed(started),
        expected="str",
        actual=type(value).__name__,
    )


def _check_repeat_read(element: Win32Element) -> dict[str, Any]:
    started = time.perf_counter()
    try:
        first = element.get_text()
        second = element.get_text()
        passed = first == second == EXPECTED_TEXT
        return _result(
            "repeat_read",
            "PASS" if passed else "FAIL",
            (
                "连续两次读取均返回相同实时文本"
                if passed
                else "连续读取结果不稳定或不符合预期"
            ),
            elapsed_ms=_elapsed(started),
            expected=EXPECTED_TEXT,
            actual=[first, second],
        )
    except Exception as exc:  # noqa: BLE001
        return _error_result("repeat_read", "重复调用 get_text() 失败", started, exc)


def _check_argument_rejection(element: Win32Element) -> dict[str, Any]:
    started = time.perf_counter()
    calls: list[tuple[str, Callable[[], object]]] = [
        ("位置参数", lambda: element.get_text(1)),  # type: ignore[call-arg]
        (
            "timeout 关键字",
            lambda: element.get_text(timeout=1),  # type: ignore[call-arg]
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
        (
            "位置参数和 timeout 关键字均被 TypeError 正确拒绝"
            if passed
            else "部分参数未按无参数合同被拒绝"
        ),
        elapsed_ms=_elapsed(started),
        expected_exception="TypeError",
        outcomes=outcomes,
    )


def _cleanup(package: Any | None, original_foreground: int) -> dict[str, Any]:
    started = time.perf_counter()
    errors: list[str] = []
    restored_foreground = False
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
            "测试资源未完全恢复",
            elapsed_ms=_elapsed(started),
            message="；".join(errors),
            restored_foreground=restored_foreground,
        )
    return _result(
        "resource_cleanup",
        "PASS",
        "已恢复原前台窗口并关闭借用的 Package；靶场保持运行且未修改",
        elapsed_ms=_elapsed(started),
        restored_foreground=restored_foreground,
    )


def _print_header(*, color: bool) -> None:
    print(_colorize("UIAutoma Win32 API 测试", "cyan", enabled=color))
    print()
    print("  API     : uiautoma.win32.Win32Element.get_text")
    print(f"  元素库  : {LIBRARY_DIR}")
    print(f"  测试元素: {TARGET_ELEMENT}")
    print(f"  预期文本: {EXPECTED_TEXT}")
    print(f"  测试窗口: {TARGET_TITLE}")
    print(f"  目标进程: {TARGET_PROCESS}")
    print("  文本来源: UIA Name；为空时回退到控件值")
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
        print(f"{indent}{_pad('原因', 12)}: {result['message']}")
    if "actual" in result:
        print(f"{indent}{_pad('实际值', 12)}: {result.get('actual')!r}")
    if result.get("expected"):
        print(f"{indent}{_pad('预期值', 12)}: {result['expected']!r}")
    if result.get("actual_library"):
        print(f"{indent}{_pad('实际元素库', 12)}: {result['actual_library']}")
    for outcome in result.get("outcomes") or []:
        if outcome.get("exception") != result.get("expected_exception"):
            print(
                f"{indent}{_pad(str(outcome.get('label') or '参数'), 12)}: "
                f"{outcome.get('exception') or '未抛出异常'} {outcome.get('message') or ''}"
            )


def main() -> int:
    color = "NO_COLOR" not in os.environ and sys.stdout.isatty()
    started = time.perf_counter()
    results: list[dict[str, Any]] = []
    package: Any | None = None
    element: Win32Element | None = None
    original_foreground = _foreground_handle()

    results.append(_check_contract())
    package_result, package = _current_package()
    results.append(package_result)
    if package_result["status"] == "PASS" and package is not None:
        prepare_result, element = _prepare_element(package)
        results.append(prepare_result)
    else:
        results.append(_blocked("element_prepare", "当前测试元素库不可用"))

    value: object | None = None
    if element is not None:
        text_result, value = _read_exact_text(element)
        results.append(text_result)
        results.append(_check_return_type(value))
        results.append(_check_repeat_read(element))
        results.append(_check_argument_rejection(element))
    else:
        results.extend(
            _blocked(case_id, "靶场标题元素不可用")
            for case_id in (
                "exact_text",
                "return_type",
                "repeat_read",
                "argument_rejection",
            )
        )

    results.append(_cleanup(package, original_foreground))

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
    raise SystemExit(main())
