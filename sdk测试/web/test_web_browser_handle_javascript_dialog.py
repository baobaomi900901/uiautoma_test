"""WebBrowser.handle_javascript_dialog() 页面对象 API 专项验收。

说明：
对话框由 Runtime 的原生 UIA 路径处理（在浏览器窗口树中识别
`JavaScriptTabModalDialogViewViews`，再用 Invoke 模式点按钮），不依赖 CDP，也不需要
`.venv` 之外的依赖。实测在**最小化**的浏览器窗口下依然可用（UIA 不需要像素）。

断言方式：对话框的处理结果不只看命令返回 `None`，而是在页面内回读真实语义——
`confirm()` 的返回值、`prompt()` 的返回值都通过 `execute_javascript()` 读回核对。

安全约定：每个用例都会在断言后确保对话框被处理掉（脚本末尾还有一次兜底清扫），
避免留下未处理的模态对话框阻塞页面。

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
DELAY = 300
TRIGGER_ALERT = f"function () {{ setTimeout(function () {{ alert('UIA-alert-msg'); }}, {DELAY}); return true; }}"
TRIGGER_CONFIRM = (f"function () {{ setTimeout(function () {{ window.__confirm_result = "
                   f"confirm('UIA-confirm-msg'); }}, {DELAY}); return true; }}")
TRIGGER_PROMPT = (f"function () {{ setTimeout(function () {{ window.__prompt_result = "
                  f"prompt('UIA-prompt-msg', 'default-value'); }}, {DELAY}); return true; }}")
READ_CONFIRM = "function () { return window.__confirm_result; }"
READ_PROMPT = "function () { return window.__prompt_result; }"
PING = "function () { return 'alive'; }"
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
    method = getattr(WebBrowser, "handle_javascript_dialog", None)
    sig = inspect.signature(method) if callable(method) else None
    if sig is None:
        return result("api_contract", "FAIL", "WebBrowser.handle_javascript_dialog 不存在")
    parameters = list(sig.parameters.values())
    names = tuple(sig.parameters)
    annotation = str(sig.return_annotation)
    ok = (
        names == ("self", "dialog_result", "text", "wait_appear_timeout")
        and parameters[1].kind is inspect.Parameter.POSITIONAL_OR_KEYWORD
        and parameters[1].default == "ok"
        and parameters[2].kind is inspect.Parameter.KEYWORD_ONLY
        and parameters[2].default is None
        and parameters[3].kind is inspect.Parameter.KEYWORD_ONLY
        and parameters[3].default == 20
        and annotation in {"None", "<class 'NoneType'>"}
    )
    detail = (
        "dialog_result 位置或关键字且默认 ok；text / wait_appear_timeout 仅限关键字（默认 None / 20）；返回 None"
        if ok
        else f"公开签名不符合合同: {sig}"
    )
    return result("api_contract", "PASS" if ok else "FAIL", detail, return_annotation=annotation)


def exception_name(exc: BaseException) -> str:
    return type(exc).__name__


def failure_reason(exc: BaseException) -> str:
    raw = getattr(getattr(exc, "result", None), "raw", None)
    while isinstance(raw, dict):
        if raw.get("failure_reason"):
            return str(raw["failure_reason"])
        raw = raw.get("raw")
    return ""


def error_detail(prefix: str, exc: BaseException) -> str:
    trace_info = str(getattr(exc, "trace_info", "") or "")
    suffix = f" [trace={trace_info}]" if trace_info else ""
    return f"{prefix}: {exception_name(exc)}: {exc}{suffix}"


def expect_raises(call, expected_type, label: str, expected_trace: str | None = None):
    started = time.perf_counter()
    try:
        call()
    except expected_type as exc:
        trace = str(getattr(exc, "trace_info", "") or "")
        if expected_trace is not None and trace != expected_trace:
            return result(
                label, "FAIL",
                f"{exception_name(exc)} 类型正确但 trace 不符：期望 {expected_trace!r}，实际 {trace!r}",
                trace_info=trace,
            )
        return result(
            label, "PASS",
            f"{exception_name(exc)} 正确拒绝" + (f"（trace={trace}）" if trace else ""),
            trace_info=trace, failure_reason=failure_reason(exc),
            elapsed_s=round(time.perf_counter() - started, 3),
        )
    except Exception as exc:  # noqa: BLE001
        return result(label, "FAIL", f"拒绝类型错误，应为 {expected_type.__name__}: {exception_name(exc)}: {exc}")
    return result(label, "FAIL", "调用未被拒绝")


def trigger(page: WebBrowser, code: str) -> bool:
    return page.execute_javascript(code) is True


def sweep(page: WebBrowser) -> None:
    """兜底：清掉可能残留的对话框，确保页面恢复响应。"""
    try:
        page.handle_javascript_dialog("ok", wait_appear_timeout=0)
    except Exception:  # noqa: BLE001
        pass


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

        # 目标用例 1：alert 用 ok 关闭，且页面恢复响应
        try:
            trigger(page, TRIGGER_ALERT)
            time.sleep(0.8)
            returned = page.handle_javascript_dialog("ok", wait_appear_timeout=args.wait_timeout)
            alive = page.execute_javascript(PING)
            ok = returned is None and alive == "alive"
            results.append(result(
                "alert_accept",
                "PASS" if ok else "FAIL",
                "alert 被接受（返回 None），且页面恢复响应" if ok else
                f"结果不符: return={returned!r}, alive={alive!r}",
                returned=repr(returned),
            ))
        except Exception as exc:  # noqa: BLE001
            results.append(result("alert_accept", "FAIL", error_detail("alert 处理失败", exc)))
            sweep(page)

        # 目标用例 2：confirm + ok → 页面内 confirm 返回 true
        try:
            trigger(page, TRIGGER_CONFIRM)
            time.sleep(0.8)
            returned = page.handle_javascript_dialog("ok", wait_appear_timeout=args.wait_timeout)
            confirm_value = page.execute_javascript(READ_CONFIRM)
            ok = returned is None and confirm_value is True
            results.append(result(
                "confirm_accept_true",
                "PASS" if ok else "FAIL",
                "confirm 接受后页面内 confirm() 返回 True" if ok else
                f"结果不符: return={returned!r}, confirm={confirm_value!r}",
                returned=repr(returned), confirm_value=repr(confirm_value),
            ))
        except Exception as exc:  # noqa: BLE001
            results.append(result("confirm_accept_true", "FAIL", error_detail("confirm 接受失败", exc)))
            sweep(page)

        # 目标用例 3：confirm + cancel → 页面内 confirm 返回 false
        try:
            trigger(page, TRIGGER_CONFIRM)
            time.sleep(0.8)
            returned = page.handle_javascript_dialog("cancel", wait_appear_timeout=args.wait_timeout)
            confirm_value = page.execute_javascript(READ_CONFIRM)
            ok = returned is None and confirm_value is False
            results.append(result(
                "confirm_cancel_false",
                "PASS" if ok else "FAIL",
                "confirm 取消后页面内 confirm() 返回 False" if ok else
                f"结果不符: return={returned!r}, confirm={confirm_value!r}",
                returned=repr(returned), confirm_value=repr(confirm_value),
            ))
        except Exception as exc:  # noqa: BLE001
            results.append(result("confirm_cancel_false", "FAIL", error_detail("confirm 取消失败", exc)))
            sweep(page)

        # 目标用例 4：prompt + text → 页面内 prompt() 返回所填文本
        typed = "typed-value"
        try:
            trigger(page, TRIGGER_PROMPT)
            time.sleep(0.8)
            returned = page.handle_javascript_dialog("ok", text=typed, wait_appear_timeout=args.wait_timeout)
            prompt_value = page.execute_javascript(READ_PROMPT)
            ok = returned is None and prompt_value == typed
            results.append(result(
                "prompt_accept_text",
                "PASS" if ok else "FAIL",
                f"prompt 填写 {typed!r} 后页面内 prompt() 返回同值" if ok else
                f"结果不符: return={returned!r}, prompt={prompt_value!r}",
                returned=repr(returned), prompt_value=repr(prompt_value),
            ))
        except Exception as exc:  # noqa: BLE001
            results.append(result("prompt_accept_text", "FAIL", error_detail("prompt 填写失败", exc)))
            sweep(page)

        # 目标用例 5：prompt + cancel → 页面内 prompt() 返回 null
        try:
            trigger(page, TRIGGER_PROMPT)
            time.sleep(0.8)
            returned = page.handle_javascript_dialog("cancel", wait_appear_timeout=args.wait_timeout)
            prompt_value = page.execute_javascript(READ_PROMPT)
            ok = returned is None and prompt_value is None
            results.append(result(
                "prompt_cancel_null",
                "PASS" if ok else "FAIL",
                "prompt 取消后页面内 prompt() 返回 null（Python None）" if ok else
                f"结果不符: return={returned!r}, prompt={prompt_value!r}",
                returned=repr(returned), prompt_value=repr(prompt_value),
            ))
        except Exception as exc:  # noqa: BLE001
            results.append(result("prompt_cancel_null", "FAIL", error_detail("prompt 取消失败", exc)))
            sweep(page)

        # 目标用例 6：取消时 text 被忽略（文档约定）
        try:
            trigger(page, TRIGGER_PROMPT)
            time.sleep(0.8)
            returned = page.handle_javascript_dialog("cancel", text="should-be-ignored",
                                                     wait_appear_timeout=args.wait_timeout)
            prompt_value = page.execute_javascript(READ_PROMPT)
            ok = returned is None and prompt_value is None
            results.append(result(
                "cancel_ignores_text",
                "PASS" if ok else "FAIL",
                "取消时 text 被忽略：prompt() 返回 None" if ok else
                f"结果不符: return={returned!r}, prompt={prompt_value!r}",
                returned=repr(returned), prompt_value=repr(prompt_value),
            ))
        except Exception as exc:  # noqa: BLE001
            results.append(result("cancel_ignores_text", "FAIL", error_detail("取消并忽略 text 失败", exc)))
            sweep(page)

        # 目标用例 7：无对话框时按超时拒绝
        results.append(expect_raises(
            lambda: page.handle_javascript_dialog("ok", wait_appear_timeout=0),
            ActionError, "no_dialog_timeout", expected_trace="web_dialog_timeout",
        ))

        # 参数校验
        results.append(expect_raises(
            lambda: page.handle_javascript_dialog("maybe"),
            InvalidParamsError, "invalid_dialog_result", expected_trace="invalid_params",
        ))
        results.append(expect_raises(
            lambda: page.handle_javascript_dialog("ok", wait_appear_timeout=-2),
            InvalidParamsError, "invalid_timeout",
        ))
        results.append(expect_raises(
            lambda: page.handle_javascript_dialog("ok", "positional-text"),
            TypeError, "text_not_keyword_only",
        ))
        results.append(expect_raises(
            lambda: page.handle_javascript_dialog("ok", unsupported=True),
            TypeError, "unknown_keyword",
        ))
    except Exception as exc:  # noqa: BLE001
        results.append(result("scenario", "FAIL", error_detail("handle_javascript_dialog 场景执行失败", exc)))
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
    parser = argparse.ArgumentParser(description="WebBrowser.handle_javascript_dialog() 页面对象 API 验收")
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
    print("API     : uiautoma.web.WebBrowser.handle_javascript_dialog")
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
            "api": "uiautoma.web.WebBrowser.handle_javascript_dialog",
            "target_url": args.target_url,
            "mode": args.mode,
            "status": "PASS" if code == 0 else ("BLOCKED" if code == 2 else "FAIL"),
            "exit_code": code,
            "results": results,
        }, ensure_ascii=False, indent=2))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
