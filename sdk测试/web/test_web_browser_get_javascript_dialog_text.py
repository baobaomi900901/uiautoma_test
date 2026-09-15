"""WebBrowser.get_javascript_dialog_text() 页面对象 API 专项验收。

说明：
对话框由 Runtime 的原生 UIA 路径识别（浏览器窗口树中的
`JavaScriptTabModalDialogViewViews`），文本取自其中的 `TextControl` 名称。

等待路径的验证方式：触发对话框用 `setTimeout` 延迟（默认 300ms，等待用例 1500ms），
**调用前不 sleep**，由 API 自己等待对话框出现并回读文本；同时记录耗时以证明它确实等待过。

每个用例断言后都会处理掉对话框，脚本末尾还有兜底清扫，避免留下未处理的模态对话框。

退出码：0 = 全部 PASS；1 = 存在 FAIL；2 = 无非 FAIL 但存在 BLOCKED。
"""
from __future__ import annotations

import argparse
import inspect
import json
import time
from urllib.parse import urlsplit

from uiautoma import ActionError, InvalidParamsError, web
from uiautoma.web import WebBrowser

__test__ = False

DEFAULT_URL = "https://baobaomi900901.github.io/xpath/#/iframe-shadow-form"
ALERT_MSG = "UIA-alert-msg"
CONFIRM_MSG = "UIA-confirm-msg"
PROMPT_MSG = "UIA-prompt-msg"


def trigger_alert(delay_ms: int) -> str:
    return f"function () {{ setTimeout(function () {{ alert('{ALERT_MSG}'); }}, {delay_ms}); return true; }}"


def trigger_confirm(delay_ms: int) -> str:
    return f"function () {{ setTimeout(function () {{ window.__confirm_result = confirm('{CONFIRM_MSG}'); }}, {delay_ms}); return true; }}"


def trigger_prompt(delay_ms: int) -> str:
    return f"function () {{ setTimeout(function () {{ window.__prompt_result = prompt('{PROMPT_MSG}', 'dv'); }}, {delay_ms}); return true; }}"


GREEN, RED, YELLOW, RESET = "\x1b[92m", "\x1b[91m", "\x1b[93m", "\x1b[0m"


def result(case_id: str, status: str, detail: str, **extra):
    return {"case_id": case_id, "status": status, "detail": detail, **extra}


def same_url(actual: str, expected: str) -> bool:
    a, e = urlsplit(str(actual)), urlsplit(str(expected))
    return (
        a.scheme.casefold(), a.netloc.casefold(), a.path or "/", a.query, a.fragment
    ) == (
        e.scheme.casefold(), e.netloc.casefold(), e.path or "/", e.query, e.fragment
    )


def check_contract():
    method = getattr(WebBrowser, "get_javascript_dialog_text", None)
    sig = inspect.signature(method) if callable(method) else None
    if sig is None:
        return result("api_contract", "FAIL", "WebBrowser.get_javascript_dialog_text 不存在")
    parameters = list(sig.parameters.values())
    names = tuple(sig.parameters)
    annotation = str(sig.return_annotation)
    ok = (
        names == ("self", "wait_appear_timeout")
        and parameters[1].kind is inspect.Parameter.KEYWORD_ONLY
        and parameters[1].default == 20
        and annotation == "str"
    )
    detail = (
        "wait_appear_timeout 仅限关键字且默认 20，返回注解 str" if ok else f"公开签名不符合合同: {sig}"
    )
    return result("api_contract", "PASS" if ok else "FAIL", detail, return_annotation=annotation)


def exception_name(exc: BaseException) -> str:
    return type(exc).__name__


def error_detail(prefix: str, exc: BaseException) -> str:
    trace_info = str(getattr(exc, "trace_info", "") or "")
    suffix = f" [trace={trace_info}]" if trace_info else ""
    return f"{prefix}: {exception_name(exc)}: {exc}{suffix}"


def expect_raises(call, expected_type, label: str, expected_trace: str | None = None,
                  min_elapsed: float | None = None):
    started = time.perf_counter()
    try:
        call()
    except expected_type as exc:
        elapsed = round(time.perf_counter() - started, 3)
        trace = str(getattr(exc, "trace_info", "") or "")
        if expected_trace is not None and trace != expected_trace:
            return result(
                label, "FAIL",
                f"{exception_name(exc)} 类型正确但 trace 不符：期望 {expected_trace!r}，实际 {trace!r}",
                trace_info=trace, elapsed_s=elapsed,
            )
        if min_elapsed is not None and elapsed < min_elapsed:
            return result(
                label, "FAIL",
                f"按超时等待的耗时过短：{elapsed}s < {min_elapsed}s（可能未真正等待）",
                trace_info=trace, elapsed_s=elapsed,
            )
        return result(
            label, "PASS",
            f"{exception_name(exc)} 正确拒绝" + (f"（trace={trace}）" if trace else "") + f"（{elapsed}s）",
            trace_info=trace, elapsed_s=elapsed,
        )
    except Exception as exc:  # noqa: BLE001
        return result(label, "FAIL", f"拒绝类型错误，应为 {expected_type.__name__}: {exception_name(exc)}: {exc}")
    return result(label, "FAIL", "调用未被拒绝")


def sweep(page: WebBrowser) -> None:
    try:
        page.handle_javascript_dialog("ok", wait_appear_timeout=0)
    except Exception:  # noqa: BLE001
        pass


def read_text_case(page: WebBrowser, case_id: str, trigger_code: str, expected_msg: str,
                   resolve: str, wait_timeout: float, label: str, min_elapsed: float = 0.0):
    """触发对话框（不 sleep）→ 调用被测 API 读取文本 → 处理掉对话框。"""
    try:
        page.execute_javascript(trigger_code)
        started = time.perf_counter()
        value = page.get_javascript_dialog_text(wait_appear_timeout=wait_timeout)
        elapsed = round(time.perf_counter() - started, 3)
    except Exception as exc:  # noqa: BLE001
        sweep(page)
        return result(case_id, "FAIL", error_detail(f"{label} 读取失败", exc))
    finally:
        pass

    type_ok = isinstance(value, str)
    value_ok = value == expected_msg
    waited_ok = elapsed >= min_elapsed
    ok = type_ok and value_ok and waited_ok

    # 无论断言结果如何，先处理掉对话框再继续
    try:
        page.handle_javascript_dialog(resolve, wait_appear_timeout=5)
        resolved = True
    except Exception:  # noqa: BLE001
        resolved = False
        sweep(page)

    detail = (
        f"{label} 读到 {expected_msg!r}（str，等待 {elapsed}s），随后已处理对话框"
        if ok else
        f"{label} 结果不符: value={value!r}({type(value).__name__}), elapsed={elapsed}s, resolved={resolved}"
    )
    return result(case_id, "PASS" if ok else "FAIL", detail,
                  value=repr(value), expected=repr(expected_msg), elapsed_s=elapsed,
                  dialog_resolved=resolved)


def run(args):
    results = [check_contract()]
    if results[-1]["status"] != "PASS" or args.contract_only:
        return results, 0 if results[-1]["status"] == "PASS" else 1

    page = None
    try:
        started = time.perf_counter()
        page = web.create(args.target_url, mode=args.mode, load_timeout=args.load_timeout)
        elapsed = (time.perf_counter() - started) * 1000
        ok = isinstance(page, WebBrowser)
        results.append(result(
            "page_prepare",
            "PASS" if ok else "FAIL",
            f"已创建 WebBrowser 测试页面（{elapsed:.1f}ms）" if ok else "create 返回类型错误",
        ))
        if not ok:
            return results, 1

        initial_url = page.get_url()
        results.append(result(
            "initial_state",
            "PASS" if same_url(initial_url, args.target_url) else "FAIL",
            "初始 URL 可读" if same_url(initial_url, args.target_url) else f"URL 不符: {initial_url!r}",
            url=initial_url,
        ))

        # 目标用例 1-3：alert / confirm / prompt 三种对话框的文本
        results.append(read_text_case(
            page, "alert_text", trigger_alert(300), ALERT_MSG, "ok", args.wait_timeout,
            "alert 文本", min_elapsed=0.15,
        ))
        results.append(read_text_case(
            page, "confirm_text", trigger_confirm(300), CONFIRM_MSG, "cancel", args.wait_timeout,
            "confirm 文本", min_elapsed=0.15,
        ))
        results.append(read_text_case(
            page, "prompt_text", trigger_prompt(300), PROMPT_MSG, "cancel", args.wait_timeout,
            "prompt 文本", min_elapsed=0.15,
        ))

        # 目标用例 4：较晚出现的对话框也必须等到并读到（等待路径）
        results.append(read_text_case(
            page, "waits_for_late_dialog", trigger_alert(1500), ALERT_MSG, "ok", args.wait_timeout,
            "延迟 1.5s 出现的 alert 文本", min_elapsed=1.0,
        ))

        # 目标用例 5：无对话框时不等待，立即按超时拒绝
        results.append(expect_raises(
            lambda: page.get_javascript_dialog_text(wait_appear_timeout=0),
            ActionError, "no_dialog_timeout_zero", expected_trace="web_dialog_timeout",
        ))

        # 目标用例 6：无对话框时按给定超时等待后再拒绝
        results.append(expect_raises(
            lambda: page.get_javascript_dialog_text(wait_appear_timeout=2),
            ActionError, "no_dialog_timeout_positive", expected_trace="web_dialog_timeout",
            min_elapsed=1.5,
        ))

        # 参数校验
        results.append(expect_raises(
            lambda: page.get_javascript_dialog_text(wait_appear_timeout=-2),
            InvalidParamsError, "invalid_timeout",
        ))
        results.append(expect_raises(
            lambda: page.get_javascript_dialog_text(5),
            TypeError, "extra_positional",
        ))
        results.append(expect_raises(
            lambda: page.get_javascript_dialog_text(unsupported=True),
            TypeError, "unknown_keyword",
        ))
    except Exception as exc:  # noqa: BLE001
        results.append(result("scenario", "FAIL", error_detail("get_javascript_dialog_text 场景执行失败", exc)))
    finally:
        if page is not None:
            sweep(page)
            try:
                page.close(ignore_beforeunload=True)
                results.append(result("cleanup", "PASS", "已兜底清扫对话框并仅关闭本次创建的测试页面"))
            except Exception as exc:  # noqa: BLE001
                results.append(result("cleanup", "FAIL", error_detail("测试页面关闭失败", exc)))

    statuses = {item["status"] for item in results}
    code = 1 if "FAIL" in statuses else (2 if "BLOCKED" in statuses else 0)
    return results, code


def main(argv=None):
    parser = argparse.ArgumentParser(description="WebBrowser.get_javascript_dialog_text() 页面对象 API 验收")
    parser.add_argument("--target-url", default=DEFAULT_URL)
    parser.add_argument("--mode", choices=("chrome", "edge"), default="chrome")
    parser.add_argument("--load-timeout", type=float, default=20)
    parser.add_argument("--wait-timeout", type=float, default=5)
    parser.add_argument("--contract-only", action="store_true")
    parser.add_argument("--json", action="store_true", help="在表格后额外输出 JSON 报告（用于归档验收产物）")
    args = parser.parse_args(argv)
    if args.load_timeout <= 0:
        parser.error("--load-timeout 必须大于 0")

    results, code = run(args)
    print("UIAutoma Web API 测试")
    print("API     : uiautoma.web.WebBrowser.get_javascript_dialog_text")
    print(f"页面    : {args.target_url}")
    print("进度     状态    测试项                  测试结果")
    print("────────────────────────────────────────────────────────────────────────")
    for index, current in enumerate(results, 1):
        status = current["status"]
        color = {"PASS": GREEN, "BLOCKED": YELLOW}.get(status, RED)
        label = {"PASS": "通过", "BLOCKED": "阻塞"}.get(status, "失败")
        print(f"{index:02d}/{len(results):02d}    {color}[{label}]{RESET}  {current['case_id']:<28}  {current['detail']}")
    print("────────────────────────────────────────────────────────────────────────")
    summary = "测试通过" if code == 0 else ("测试阻塞" if code == 2 else "测试失败")
    print(f"{summary} · {sum(item['status'] == 'PASS' for item in results)}/{len(results)} 通过 · 退出码 {code}")
    if args.json:
        print(json.dumps({
            "api": "uiautoma.web.WebBrowser.get_javascript_dialog_text",
            "target_url": args.target_url,
            "mode": args.mode,
            "status": "PASS" if code == 0 else ("BLOCKED" if code == 2 else "FAIL"),
            "exit_code": code,
            "results": results,
        }, ensure_ascii=False, indent=2))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
