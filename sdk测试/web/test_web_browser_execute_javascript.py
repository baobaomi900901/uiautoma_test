"""WebBrowser.execute_javascript() 页面对象 API 专项验收。

说明：
本 API 是多个验收脚本的场景准备原语（#58 预热、beforeunload 注入、timeOrigin 与 JS 标记探针），
因此单独验收。它只读页面状态、不需要导航历史前置，不受 issue #58 影响。

覆盖要点来自源码与预探：
- 引擎把 `code` 当函数求值后以 `fn(null, argument)` 调用并 `await` 结果；
- `undefined` / `null` / 无返回值统一映射为 Python `None`；
- `argument` 支持字符串、数字、布尔、列表、字典（无需先转 JSON），`None` 传为 `undefined`；
- `execution_world` 只接受 `ISOLATED` / `MAIN`，非法值在 SDK 侧即被拒绝；
- 两个 world 的 JS 变量互相不可见，但共享同一个 DOM。

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
    method = getattr(WebBrowser, "execute_javascript", None)
    sig = inspect.signature(method) if callable(method) else None
    if sig is None:
        return result("api_contract", "FAIL", "WebBrowser.execute_javascript 不存在")
    parameters = list(sig.parameters.values())
    names = tuple(sig.parameters)
    annotation = str(sig.return_annotation)
    ok = (
        names == ("self", "code", "argument", "execution_world")
        and all(p.kind is inspect.Parameter.POSITIONAL_OR_KEYWORD for p in parameters[1:])
        and parameters[1].default is inspect.Parameter.empty
        and parameters[2].default is None
        and parameters[3].default == "ISOLATED"
        and annotation == "Any"
    )
    detail = (
        "code 必填，argument 默认 None，execution_world 默认 ISOLATED，返回注解 Any"
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


def check_values(page: WebBrowser, case_id: str, code: str, expected, label: str, **extra):
    """执行 code 并断言返回值与 expected 完全一致（含类型）。"""
    try:
        value = page.execute_javascript(code)
    except Exception as exc:  # noqa: BLE001
        return result(case_id, "FAIL", error_detail(f"{label} 调用失败", exc))
    same_type = type(value) is type(expected)
    same_value = value == expected
    ok = same_type and same_value
    return result(
        case_id,
        "PASS" if ok else "FAIL",
        f"{label} 返回 {expected!r}" if ok else
        f"{label} 结果不符: 期望 {expected!r}({type(expected).__name__})，实际 {value!r}({type(value).__name__})",
        actual=repr(value), expected=repr(expected), **extra,
    )


def expect_raises(call, expected_type, label: str, expected_trace: str = ""):
    try:
        call()
    except expected_type as exc:
        trace = str(getattr(exc, "trace_info", "") or "")
        if expected_trace and trace != expected_trace:
            return result(
                label, "FAIL",
                f"{exception_name(exc)} 类型正确但 trace 不符：期望 {expected_trace!r}，实际 {trace!r}",
                trace_info=trace,
            )
        return result(
            label, "PASS",
            f"{exception_name(exc)} 正确拒绝" + (f"（trace={trace}）" if trace else ""),
            trace_info=trace, failure_reason=failure_reason(exc),
        )
    except Exception as exc:  # noqa: BLE001
        return result(
            label, "FAIL",
            f"拒绝类型错误，应为 {expected_type.__name__}: {exception_name(exc)}: {exc}",
        )
    return result(label, "FAIL", "调用未被拒绝")


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

        page_id = page.id
        initial_url = page.get_url()
        results.append(result(
            "initial_state",
            "PASS" if same_url(initial_url, args.target_url) and bool(page_id) else "FAIL",
            "初始 URL 可读且页面 id 非空" if same_url(initial_url, args.target_url) and page_id else
            f"初始状态不符: url={initial_url!r}, id={page_id!r}",
        ))

        # 返回透传：数字 / 字符串 / 布尔 / 列表 / 字典
        samples = [
            ("function () { return 7; }", 7, "数字"),
            ("function () { return 'str'; }", "str", "字符串"),
            ("function () { return true; }", True, "布尔"),
            ("function () { return [1, 2]; }", [1, 2], "列表"),
            ("function () { return {a: 1}; }", {"a": 1}, "字典"),
        ]
        mismatches = []
        for code, expected, label in samples:
            item = check_values(page, "return_passthrough", code, expected, label)
            if item["status"] != "PASS":
                mismatches.append(item["detail"])
        results.append(result(
            "return_passthrough",
            "PASS" if not mismatches else "FAIL",
            f"数字/字符串/布尔/列表/字典 五种返回值均按原类型透传（{len(samples)}/{len(samples)}）"
            if not mismatches else "；".join(mismatches),
            sample_count=len(samples),
        ))

        # undefined / null / 无返回值 统一为 None
        none_mismatches = []
        for code, label in (
            ("function () { return null; }", "null"),
            ("function () { return undefined; }", "undefined"),
            ("function () { }", "无返回值"),
        ):
            item = check_values(page, "return_none", code, None, label)
            if item["status"] != "PASS":
                none_mismatches.append(item["detail"])
        results.append(result(
            "return_none",
            "PASS" if not none_mismatches else "FAIL",
            "null / undefined / 无返回值 三种情形均返回 None" if not none_mismatches else "；".join(none_mismatches),
        ))

        # 异步：返回的 Promise 会被 await
        try:
            value = page.execute_javascript("function () { return Promise.resolve(5); }")
        except Exception as exc:  # noqa: BLE001
            results.append(result("async_awaited", "FAIL", error_detail("Promise 用例调用失败", exc)))
        else:
            ok = value == 5 and type(value) is int
            results.append(result(
                "async_awaited",
                "PASS" if ok else "FAIL",
                "Promise.resolve(5) 被 await 后返回 5" if ok else f"未被 await: 实际 {value!r}({type(value).__name__})",
                actual=repr(value),
            ))

        # 参数传递：数字 / 字符串 / 列表 / 字典 / None
        arg_cases = [
            ("function (el, args) { return args * 2; }", 21, 42, "数字"),
            ("function (el, args) { return args + '!'; }", "hi", "hi!", "字符串"),
            ("function (el, args) { return args.join('-'); }", ["a", "b"], "a-b", "列表"),
            ("function (el, args) { return args.k; }", {"k": "v"}, "v", "字典"),
            ("function (el, args) { return typeof args; }", None, "undefined", "None"),
        ]
        arg_mismatches = []
        for code, argument, expected, label in arg_cases:
            try:
                value = page.execute_javascript(code, argument)
            except Exception as exc:  # noqa: BLE001
                arg_mismatches.append(f"{label}: {exception_name(exc)}: {exc}")
                continue
            if value != expected or type(value) is not type(expected):
                arg_mismatches.append(f"{label}: 期望 {expected!r}，实际 {value!r}")
        results.append(result(
            "argument_passing",
            "PASS" if not arg_mismatches else "FAIL",
            f"数字/字符串/列表/字典/None 五种参数均正确传入（None 传为 undefined）"
            if not arg_mismatches else "；".join(arg_mismatches),
            argument_count=len(arg_cases),
        ))

        # 第一个形参为 null（引擎以 fn(null, argument) 调用）
        try:
            value = page.execute_javascript("function (el) { return el === null; }")
        except Exception as exc:  # noqa: BLE001
            results.append(result("element_param_null", "FAIL", error_detail("调用失败", exc)))
        else:
            ok = value is True
            results.append(result(
                "element_param_null",
                "PASS" if ok else "FAIL",
                "函数第一个形参收到 null" if ok else f"第一个形参不是 null: 实际 {value!r}",
                actual=repr(value),
            ))

        # 双 world：JS 变量互不可见，各自可见
        world_checks = []
        try:
            main_set = page.execute_javascript(
                "function () { window.__uia_world_main = 'M'; return window.__uia_world_main; }",
                execution_world="MAIN",
            )
            main_visible = page.execute_javascript(
                "function () { return window.__uia_world_main; }", execution_world="MAIN")
            iso_reads_main = page.execute_javascript(
                "function () { return typeof window.__uia_world_main; }")
            iso_set = page.execute_javascript(
                "function () { window.__uia_world_iso = 'I'; return window.__uia_world_iso; }")
            iso_visible = page.execute_javascript("function () { return window.__uia_world_iso; }")
            main_reads_iso = page.execute_javascript(
                "function () { return typeof window.__uia_world_iso; }", execution_world="MAIN")
            world_checks = [
                ("MAIN 写入", main_set == "M"),
                ("MAIN 自读", main_visible == "M"),
                ("ISOLATED 读 MAIN", iso_reads_main == "undefined"),
                ("ISOLATED 写入", iso_set == "I"),
                ("ISOLATED 自读", iso_visible == "I"),
                ("MAIN 读 ISOLATED", main_reads_iso == "undefined"),
            ]
        except Exception as exc:  # noqa: BLE001
            results.append(result("world_isolation", "FAIL", error_detail("双 world 用例调用失败", exc)))
        else:
            failed = [name for name, ok in world_checks if not ok]
            results.append(result(
                "world_isolation",
                "PASS" if not failed else "FAIL",
                "MAIN 与 ISOLATED 的 JS 变量互相不可见、各自可见（6/6）" if not failed else
                "以下检查未通过: " + ", ".join(failed),
                checks=len(world_checks),
            ))

        # 双 world 共享同一 DOM：MAIN 改标题后，get_title 与 ISOLATED 都能读到
        try:
            original_title = page.get_title()
            temp_title = f"uiautoma-exec-js-{page_id[:8]}"
            set_result = page.execute_javascript(
                f"function () {{ document.title = {json.dumps(temp_title)}; return document.title; }}",
                execution_world="MAIN",
            )
            sdk_title = page.get_title()
            iso_title = page.execute_javascript("function () { return document.title; }")
            ok = set_result == temp_title and sdk_title == temp_title and iso_title == temp_title
            if original_title and original_title != temp_title:
                page.execute_javascript(
                    f"function () {{ document.title = {json.dumps(original_title)}; return document.title; }}",
                    execution_world="MAIN",
                )
            results.append(result(
                "world_dom_shared",
                "PASS" if ok else "FAIL",
                "MAIN 修改 document.title 后，get_title() 与 ISOLATED 读取结果一致（DOM 共享）" if ok else
                f"结果不符: set={set_result!r}, get_title={sdk_title!r}, isolated={iso_title!r}",
                original_title=original_title, temp_title=temp_title,
            ))
        except Exception as exc:  # noqa: BLE001
            results.append(result("world_dom_shared", "FAIL", error_detail("DOM 共享用例调用失败", exc)))

        # 全部参数位置传入（含 execution_world）
        try:
            value = page.execute_javascript("function (el, args) { return args; }", "pos", "MAIN")
        except Exception as exc:  # noqa: BLE001
            results.append(result("positional_call", "FAIL", error_detail("位置传参调用失败", exc)))
        else:
            ok = value == "pos"
            results.append(result(
                "positional_call",
                "PASS" if ok else "FAIL",
                "code 与 argument、execution_world 均可用位置传入" if ok else f"结果不符: {value!r}",
                actual=repr(value),
            ))

        # 错误形态
        results.append(expect_raises(
            lambda: page.execute_javascript("1 + 1"),
            ActionError, "non_function_code", expected_trace="execute_javascript_failed",
        ))
        results.append(expect_raises(
            lambda: page.execute_javascript("function () { throw new Error('boom'); }"),
            ActionError, "throwing_function", expected_trace="execute_javascript_failed",
        ))
        results.append(expect_raises(
            lambda: page.execute_javascript("function () { return 1; }", execution_world="BOGUS"),
            InvalidParamsError, "invalid_world",
        ))
        results.append(expect_raises(
            lambda: page.execute_javascript("   "),
            InvalidParamsError, "empty_code", expected_trace="invalid_params",
        ))
    except Exception as exc:  # noqa: BLE001
        results.append(result("scenario", "FAIL", error_detail("execute_javascript 场景执行失败", exc)))
    finally:
        if page is not None:
            try:
                page.close(ignore_beforeunload=True)
                results.append(result("cleanup", "PASS", "仅关闭本次创建的测试页面"))
            except Exception as exc:  # noqa: BLE001
                results.append(result("cleanup", "FAIL", error_detail("测试页面关闭失败", exc)))

    statuses = {item["status"] for item in results}
    code = 1 if "FAIL" in statuses else (2 if "BLOCKED" in statuses else 0)
    return results, code


def main(argv=None):
    parser = argparse.ArgumentParser(description="WebBrowser.execute_javascript() 页面对象 API 验收")
    parser.add_argument("--target-url", default=DEFAULT_URL)
    parser.add_argument("--mode", choices=("chrome", "edge"), default="chrome")
    parser.add_argument("--load-timeout", type=float, default=20)
    parser.add_argument("--contract-only", action="store_true")
    parser.add_argument("--json", action="store_true", help="在表格后额外输出 JSON 报告（用于归档验收产物）")
    args = parser.parse_args(argv)
    if args.load_timeout <= 0:
        parser.error("--load-timeout 必须大于 0")

    results, code = run(args)
    print("UIAutoma Web API 测试")
    print("API     : uiautoma.web.WebBrowser.execute_javascript")
    print(f"页面    : {args.target_url}")
    print("进度     状态    测试项                  测试结果")
    print("────────────────────────────────────────────────────────────────────────")
    for index, current in enumerate(results, 1):
        status = current["status"]
        color = {"PASS": GREEN, "BLOCKED": YELLOW}.get(status, RED)
        label = {"PASS": "通过", "BLOCKED": "阻塞"}.get(status, "失败")
        print(f"{index:02d}/{len(results):02d}    {color}[{label}]{RESET}  {current['case_id']:<24}  {current['detail']}")
    print("────────────────────────────────────────────────────────────────────────")
    summary = "测试通过" if code == 0 else ("测试阻塞" if code == 2 else "测试失败")
    print(f"{summary} · {sum(item['status'] == 'PASS' for item in results)}/{len(results)} 通过 · 退出码 {code}")
    if args.json:
        print(json.dumps({
            "api": "uiautoma.web.WebBrowser.execute_javascript",
            "target_url": args.target_url,
            "mode": args.mode,
            "status": "PASS" if code == 0 else ("BLOCKED" if code == 2 else "FAIL"),
            "exit_code": code,
            "results": results,
        }, ensure_ascii=False, indent=2))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
