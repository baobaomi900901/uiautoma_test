r"""``uiautoma.win32.Win32Element.check()`` 真实复选框状态测试。

API 参数（不是测试脚本参数）::

    Win32Element.check(
        mode: str = "check",
        delay_after: float = 1,
    ) -> None

参数规则：

* ``mode``：``"check"`` 设置选中，``"uncheck"`` 设置未选中，``"toggle"``
  切换状态；会去除首尾空格并忽略大小写。非法模式抛出 ``InvalidParamsError``。
* ``delay_after``：默认 ``1`` 秒；``0`` 和 ``None`` 不等待；非负数字按秒等待；
  负数或非数字抛出 ``InvalidParamsError``。当前实现先执行状态操作并保存
  ``last_result``，再校验动作后延时。
* 成功返回 ``None``，动作前后状态保存在 ``last_result.raw`` 的
  ``before_checked`` 和 ``checked`` 字段中；Runtime 动作失败抛出 ``ActionError``。

测试脚本参数：无。

脚本借用 UIAutoma.exe 当前启用的 ``D:\code\元素库\260902_win元素``，使用其中的
``win32靶场_表单控件_多选_北京``。测试覆盖三种合法模式、幂等调用、大小写与空格归一化、全部
动作后延时形式及非法参数。脚本从首次默认调用的 ``before_checked`` 记录复选框原始
状态，结束时恢复该状态、关闭借用的 Package，并保持 Win32 靶场运行。

导入本模块不会连接 Runtime 或改变复选框状态。

运行方式::

    uv run .\win32\test_win32_check.py
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
from uiautoma.win32 import Win32Element


__test__ = False

LIBRARY_DIR = Path(r"D:\code\元素库\260902_win元素")
ELEMENT_NAME = "win32靶场_表单控件_多选_北京"
DEFAULT_DELAY_MIN_MS = 900.0
NO_DELAY_MAX_MS = 800.0
POSITIVE_DELAY_SECONDS = 0.2
POSITIVE_DELAY_MIN_MS = 160.0

STATUS_LABELS = {"PASS": "通过", "FAIL": "失败", "BLOCKED": "阻塞"}
COLORS = {"PASS": "\x1b[32m", "FAIL": "\x1b[31m", "BLOCKED": "\x1b[33m"}
CYAN = "\x1b[36m"
RESET = "\x1b[0m"

PROGRESS_WIDTH = 7
STATUS_WIDTH = 6
CASE_WIDTH = 22
DETAIL_WIDTH = 82
DURATION_WIDTH = 8
TABLE_WIDTH = sum((PROGRESS_WIDTH, STATUS_WIDTH, CASE_WIDTH, DETAIL_WIDTH, DURATION_WIDTH, 8))

CASE_LABELS = {
    "api_contract": "API 合同",
    "element_setup": "复选框准备",
    "default_check": "默认勾选",
    "idempotent_check": "重复勾选",
    "uncheck": "取消勾选",
    "idempotent_uncheck": "重复取消勾选",
    "toggle_on": "切换为选中",
    "toggle_off": "切换为未选中",
    "normalized_check": "check 归一化",
    "normalized_uncheck": "uncheck 归一化",
    "normalized_toggle": "toggle 归一化",
    "delay_none": "None 动作后延时",
    "delay_positive": "正数动作后延时",
    "invalid_mode": "非法模式",
    "invalid_delay": "非法动作后延时",
    "resource_cleanup": "状态与资源恢复",
}

BLOCKING_EXCEPTION_NAMES = {
    "ConnectionError",
    "EOFError",
    "ElementNotFoundError",
    "HostBusyError",
    "HostUnavailableError",
    "PipeClosedError",
    "StalePackageError",
    "TimeoutError",
    "UnsupportedProtocolError",
}


def _result(case_id: str, status: str, detail: str, **extra: Any) -> dict[str, Any]:
    return {"case_id": case_id, "status": status, "detail": detail, **extra}


def _elapsed(started: float) -> float:
    return (time.perf_counter() - started) * 1000


def _error_result(
    case_id: str,
    detail: str,
    started: float,
    exc: BaseException,
    *,
    call: str = "",
) -> dict[str, Any]:
    status = "BLOCKED" if exc.__class__.__name__ in BLOCKING_EXCEPTION_NAMES else "FAIL"
    return _result(
        case_id,
        status,
        detail,
        elapsed_ms=_elapsed(started),
        call=call,
        exception=exc.__class__.__name__,
        message=str(exc),
    )


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


def _state_label(value: bool | None) -> str:
    if value is True:
        return "已选中"
    if value is False:
        return "未选中"
    return "未知"


def _bool_field(raw: object, key: str) -> bool | None:
    if not isinstance(raw, dict) or key not in raw:
        return None
    value = raw[key]
    if isinstance(value, bool):
        return value
    if value in (0, 1):
        return bool(value)
    return None


def _action_state(element: Win32Element) -> tuple[bool | None, bool | None, str, bool]:
    result = element.last_result
    if result is None:
        return None, None, "", False
    return (
        _bool_field(result.raw, "before_checked"),
        _bool_field(result.raw, "checked"),
        str(result.strategy or ""),
        bool(result.ok),
    )


def _check_contract() -> dict[str, Any]:
    started = time.perf_counter()
    try:
        signature = inspect.signature(Win32Element.check)
        parameters = signature.parameters
        mode = parameters.get("mode")
        delay_after = parameters.get("delay_after")
        positional = inspect.Parameter.POSITIONAL_OR_KEYWORD
        passed = (
            tuple(parameters) == ("self", "mode", "delay_after")
            and mode is not None
            and mode.kind is positional
            and mode.default == "check"
            and str(mode.annotation) in {"str", "<class 'str'>"}
            and delay_after is not None
            and delay_after.kind is positional
            and delay_after.default == 1
            and str(delay_after.annotation) in {"float", "<class 'float'>"}
            and str(signature.return_annotation) in {"None", "<class 'NoneType'>"}
        )
        return _result(
            "api_contract",
            "PASS" if passed else "FAIL",
            (
                "mode 和 delay_after 均为位置或关键字参数，默认值及返回 None 符合合同"
                if passed
                else "公开签名与当前合同不一致"
            ),
            elapsed_ms=_elapsed(started),
            signature=str(signature),
        )
    except Exception as exc:  # noqa: BLE001
        return _error_result("api_contract", "无法检查公开签名", started, exc)


def _prepare() -> tuple[dict[str, Any], Any | None, Win32Element | None]:
    started = time.perf_counter()
    package: Any | None = None
    try:
        if not LIBRARY_DIR.is_dir():
            raise RuntimeError(f"元素库目录不存在：{LIBRARY_DIR}")
        package = uiautoma.current(required=False, refresh=True, timeout=5)
        ensure_form_tab(package)
        if package is None:
            raise RuntimeError("UIAutoma 当前未启用元素库；请点击“使用当前元素库”后重试")
        actual_library = Path(package.package_dir).resolve()
        if os.path.normcase(str(actual_library)) != os.path.normcase(str(LIBRARY_DIR.resolve())):
            raise RuntimeError(f"UIAutoma 当前元素库不是测试库：{actual_library}")
        element = win32.find(ELEMENT_NAME, timeout=10)
        return (
            _result(
                "element_setup",
                "PASS",
                "当前元素库正确，已获取北京复选框",
                elapsed_ms=_elapsed(started),
                element_id=element.id,
            ),
            package,
            element,
        )
    except Exception as exc:  # noqa: BLE001
        return (
            _result(
                "element_setup",
                "BLOCKED",
                "无法准备当前元素库或北京复选框",
                elapsed_ms=_elapsed(started),
                exception=exc.__class__.__name__,
                message=str(exc),
            ),
            package,
            None,
        )


def _run_check_case(
    case_id: str,
    element: Win32Element | None,
    call: Callable[[], None],
    call_text: str,
    success_detail: str,
    *,
    expected_before: bool | None,
    expected_after: bool,
    min_elapsed_ms: float = 0.0,
    max_elapsed_ms: float | None = None,
) -> dict[str, Any]:
    if element is None:
        return _blocked(case_id, "北京复选框未准备完成")
    started = time.perf_counter()
    try:
        returned = call()
        elapsed_ms = _elapsed(started)
        before, checked, strategy, result_ok = _action_state(element)
        before_ok = isinstance(before, bool) if expected_before is None else before is expected_before
        duration_ok = elapsed_ms >= min_elapsed_ms and (
            max_elapsed_ms is None or elapsed_ms <= max_elapsed_ms
        )
        passed = (
            returned is None
            and before_ok
            and checked is expected_after
            and result_ok
            and bool(strategy)
            and duration_ok
        )
        return _result(
            case_id,
            "PASS" if passed else "FAIL",
            success_detail if passed else "返回值、操作前后状态、策略或耗时不符合预期",
            elapsed_ms=elapsed_ms,
            call=call_text,
            returned=returned,
            before_checked=before,
            checked=checked,
            expected_before=expected_before,
            expected_after=expected_after,
            strategy=strategy,
            result_ok=result_ok,
            min_elapsed_ms=min_elapsed_ms,
            max_elapsed_ms=max_elapsed_ms,
        )
    except Exception as exc:  # noqa: BLE001
        return _error_result(case_id, "check() 调用失败", started, exc, call=call_text)


def _check_invalid_mode(element: Win32Element | None) -> dict[str, Any]:
    started = time.perf_counter()
    if element is None:
        return _blocked("invalid_mode", "北京复选框未准备完成")
    previous_result = element.last_result
    outcomes: list[dict[str, Any]] = []
    for mode in ("", "invalid", None, 123):
        try:
            element.check(mode, 0)  # type: ignore[arg-type]
            outcomes.append({"mode": mode, "exception": None})
        except Exception as exc:  # noqa: BLE001
            outcomes.append(
                {
                    "mode": mode,
                    "exception": exc.__class__.__name__,
                    "message": str(exc),
                    "last_result_unchanged": element.last_result is previous_result,
                }
            )
    passed = all(
        item["exception"] == "InvalidParamsError"
        and item.get("last_result_unchanged") is True
        for item in outcomes
    )
    return _result(
        "invalid_mode",
        "PASS" if passed else "FAIL",
        (
            "空值、非法名称、None 和整数均在动作前被 InvalidParamsError 拒绝"
            if passed
            else "至少一个非法 mode 未按预期拒绝或意外更新了动作结果"
        ),
        elapsed_ms=_elapsed(started),
        call='element.check("" / "invalid" / None / 123, 0)',
        outcomes=outcomes,
    )


def _check_invalid_delay(element: Win32Element | None) -> dict[str, Any]:
    started = time.perf_counter()
    if element is None:
        return _blocked("invalid_delay", "北京复选框未准备完成")
    cases = (
        ("uncheck", -0.1, True, False),
        ("check", "bad", False, True),
    )
    outcomes: list[dict[str, Any]] = []
    for mode, delay, expected_before, expected_after in cases:
        try:
            element.check(mode, delay)  # type: ignore[arg-type]
            outcomes.append({"mode": mode, "delay_after": delay, "exception": None})
        except Exception as exc:  # noqa: BLE001
            before, checked, strategy, result_ok = _action_state(element)
            outcomes.append(
                {
                    "mode": mode,
                    "delay_after": delay,
                    "exception": exc.__class__.__name__,
                    "message": str(exc),
                    "before_checked": before,
                    "checked": checked,
                    "strategy": strategy,
                    "result_ok": result_ok,
                    "state_ok": before is expected_before and checked is expected_after,
                }
            )
    passed = all(
        item["exception"] == "InvalidParamsError"
        and item.get("state_ok") is True
        and item.get("result_ok") is True
        for item in outcomes
    )
    return _result(
        "invalid_delay",
        "PASS" if passed else "FAIL",
        (
            "负数和非数字延时均在状态操作完成后被 InvalidParamsError 拒绝"
            if passed
            else "至少一个非法延时的异常类型、动作顺序或状态不符合预期"
        ),
        elapsed_ms=_elapsed(started),
        call='element.check("uncheck", -0.1); element.check("check", "bad")',
        outcomes=outcomes,
    )


def _cleanup(
    package: Any | None,
    element: Win32Element | None,
    initial_state: bool | None,
) -> dict[str, Any]:
    started = time.perf_counter()
    errors: list[str] = []
    state_restored = element is None and initial_state is None
    package_closed = package is None
    if element is not None:
        if initial_state is None:
            errors.append("未能记录复选框初始状态")
        else:
            try:
                restore_mode = "check" if initial_state else "uncheck"
                returned = element.check(restore_mode, 0)
                _before, checked, _strategy, result_ok = _action_state(element)
                state_restored = returned is None and result_ok and checked is initial_state
                if not state_restored:
                    errors.append("复选框初始状态未恢复")
            except Exception as exc:  # noqa: BLE001
                errors.append(f"恢复复选框状态失败：{exc}")
    try:
        if package is not None:
            package.close()
            package_closed = True
    except Exception as exc:  # noqa: BLE001
        errors.append(f"关闭 Package 失败：{exc}")
    passed = state_restored and package_closed and not errors
    return _result(
        "resource_cleanup",
        "PASS" if passed else "FAIL",
        (
            f"复选框已恢复为{_state_label(initial_state)}，借用的 Package 已关闭；靶场保持运行"
            if passed
            else "；".join(errors)
        ),
        elapsed_ms=_elapsed(started),
        initial_state=initial_state,
        state_restored=state_restored,
        package_closed=package_closed,
    )


def _print_header(initial_state: bool | None, *, color: bool) -> None:
    title = f"{CYAN}UIAutoma Win32 API 测试{RESET}" if color else "UIAutoma Win32 API 测试"
    print(title)
    print()
    print("  API     : uiautoma.win32.Win32Element.check")
    print(f"  元素库  : {LIBRARY_DIR}")
    print(f"  测试元素: {ELEMENT_NAME}")
    print("  控件类型: CheckBox")
    print(f"  初始状态: {_state_label(initial_state)}")
    print("  状态校验: ActionResult.before_checked + checked")
    print("  状态恢复: 测试结束后恢复复选框初始状态并关闭借用的 Package")
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
    for key, label in (
        ("call", "调用"),
        ("expected_before", "预期操作前"),
        ("before_checked", "实际操作前"),
        ("expected_after", "预期操作后"),
        ("checked", "实际操作后"),
        ("strategy", "执行策略"),
        ("message", "原因"),
    ):
        if result.get(key) not in (None, ""):
            print(f"{indent}{_pad(label, 12)}: {result[key]}")
    if result.get("outcomes"):
        for outcome in result["outcomes"]:
            print(f"{indent}{outcome}")


def main() -> int:
    color = "NO_COLOR" not in os.environ and sys.stdout.isatty()
    started = time.perf_counter()
    contract = _check_contract()
    setup, package, element = _prepare()
    ready = setup["status"] == "PASS" and element is not None

    results: list[dict[str, Any]] = [contract, setup]
    initial_state: bool | None = None
    if ready and element is not None:
        default_check = _run_check_case(
            "default_check",
            element,
            lambda: element.check(),
            "element.check()",
            "默认 mode=check、delay_after=1 生效，结果为选中",
            expected_before=None,
            expected_after=True,
            min_elapsed_ms=DEFAULT_DELAY_MIN_MS,
        )
        results.append(default_check)
        before = default_check.get("before_checked")
        if isinstance(before, bool):
            initial_state = before

        state_ready = default_check["status"] == "PASS"
        cases: tuple[
            tuple[
                str,
                Callable[[], None],
                str,
                str,
                bool,
                bool,
                float,
                float | None,
            ],
            ...,
        ] = (
            (
                "idempotent_check",
                lambda: element.check("check", 0),
                'element.check("check", 0)',
                "已选中状态重复 check 保持选中",
                True,
                True,
                0.0,
                NO_DELAY_MAX_MS,
            ),
            (
                "uncheck",
                lambda: element.check("uncheck", 0),
                'element.check("uncheck", 0)',
                "uncheck 将复选框设置为未选中",
                True,
                False,
                0.0,
                NO_DELAY_MAX_MS,
            ),
            (
                "idempotent_uncheck",
                lambda: element.check("uncheck", 0),
                'element.check("uncheck", 0)',
                "未选中状态重复 uncheck 保持未选中",
                False,
                False,
                0.0,
                NO_DELAY_MAX_MS,
            ),
            (
                "toggle_on",
                lambda: element.check("toggle", 0),
                'element.check("toggle", 0)',
                "toggle 将未选中状态切换为选中",
                False,
                True,
                0.0,
                NO_DELAY_MAX_MS,
            ),
            (
                "toggle_off",
                lambda: element.check("toggle", 0),
                'element.check("toggle", 0)',
                "toggle 将选中状态切换为未选中",
                True,
                False,
                0.0,
                NO_DELAY_MAX_MS,
            ),
            (
                "normalized_check",
                lambda: element.check("  CHECK  ", 0),
                'element.check("  CHECK  ", 0)',
                "check 忽略首尾空格和大小写并设置为选中",
                False,
                True,
                0.0,
                NO_DELAY_MAX_MS,
            ),
            (
                "normalized_uncheck",
                lambda: element.check("  UnChEcK  ", 0),
                'element.check("  UnChEcK  ", 0)',
                "uncheck 忽略首尾空格和大小写并设置为未选中",
                True,
                False,
                0.0,
                NO_DELAY_MAX_MS,
            ),
            (
                "normalized_toggle",
                lambda: element.check("  ToGgLe  ", 0),
                'element.check("  ToGgLe  ", 0)',
                "toggle 忽略首尾空格和大小写并切换为选中",
                False,
                True,
                0.0,
                NO_DELAY_MAX_MS,
            ),
            (
                "delay_none",
                lambda: element.check("uncheck", None),  # type: ignore[arg-type]
                'element.check("uncheck", None)',
                "delay_after=None 不等待并设置为未选中",
                True,
                False,
                0.0,
                NO_DELAY_MAX_MS,
            ),
            (
                "delay_positive",
                lambda: element.check("check", POSITIVE_DELAY_SECONDS),
                'element.check("check", 0.2)',
                "delay_after=0.2 在勾选后完成等待",
                False,
                True,
                POSITIVE_DELAY_MIN_MS,
                None,
            ),
        )
        for (
            case_id,
            call,
            call_text,
            detail,
            expected_before,
            expected_after,
            min_elapsed_ms,
            max_elapsed_ms,
        ) in cases:
            if not state_ready:
                results.append(_blocked(case_id, "上一状态操作未通过，避免继续改变复选框"))
                continue
            result = _run_check_case(
                case_id,
                element,
                call,
                call_text,
                detail,
                expected_before=expected_before,
                expected_after=expected_after,
                min_elapsed_ms=min_elapsed_ms,
                max_elapsed_ms=max_elapsed_ms,
            )
            results.append(result)
            state_ready = result["status"] == "PASS"

        if state_ready:
            invalid_mode = _check_invalid_mode(element)
            results.append(invalid_mode)
            invalid_delay = (
                _check_invalid_delay(element)
                if invalid_mode["status"] == "PASS"
                else _blocked("invalid_delay", "非法模式测试未通过，避免继续改变复选框")
            )
            results.append(invalid_delay)
        else:
            results.append(_blocked("invalid_mode", "前置状态操作未通过"))
            results.append(_blocked("invalid_delay", "前置状态操作未通过"))
    else:
        for case_id in tuple(CASE_LABELS)[2:-1]:
            results.append(_blocked(case_id, "复选框准备失败，未执行状态操作"))

    results.append(_cleanup(package, element, initial_state))

    _print_header(initial_state, color=color)
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
