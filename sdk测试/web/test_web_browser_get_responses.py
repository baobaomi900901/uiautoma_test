"""WebBrowser.get_responses() 页面对象 API 专项验收。

说明：
本 API 读取引擎 CDP 监听已记录的响应，不使用元素库、不需要导航历史前置，也不依赖视口。

源码语义要点（本次实测核对）：
- 返回项应包含文档所述 9 个键：`url`、`type`、`headers`、`body`、`status`、
  `base64Encoded`、`requestHeaders`、`requestBody`、`method`；
- 只返回已收到响应的记录（`status` 非空，或 WebSocket 的 `direction` 非空）；
  未收到响应的失败请求不返回；
- **本方法的过滤叠加在 `start_monitor_network()` 的存储级过滤之上**：启动时被排除的类型
  根本不在记录中，事后无法取回；
- `url` 默认精确匹配，`use_wildcard=True` 时 `*` → `.*`、`?` → `.` 并整体锚定；
- 未匹配返回 `[]`；没有活动监听时抛 `ActionError`（trace `web_network_monitor_not_found`）。

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
FETCH_404 = "https://baobaomi900901.github.io/xpath/robots.txt"
DOCUMENT_URL = "https://baobaomi900901.github.io/xpath/"
EXPECTED_KEYS = {"url", "type", "headers", "body", "status", "base64Encoded",
                 "requestHeaders", "requestBody", "method"}
GREEN, RED, YELLOW, RESET = "\x1b[92m", "\x1b[91m", "\x1b[93m", "\x1b[0m"


def fetch_code(url: str) -> str:
    return (f"function () {{ return fetch('{url}', {{cache: 'no-store'}})"
            f".then(function (r) {{ return r.status; }}); }}")


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
    method = getattr(WebBrowser, "get_responses", None)
    sig = inspect.signature(method) if callable(method) else None
    if sig is None:
        return result("api_contract", "FAIL", "WebBrowser.get_responses 不存在")
    parameters = list(sig.parameters.values())
    names = tuple(sig.parameters)
    ok = (
        names == ("self", "url", "use_wildcard", "resource_type")
        and all(p.kind is inspect.Parameter.KEYWORD_ONLY for p in parameters[1:])
        and parameters[1].default == ""
        and parameters[2].default is False
        and parameters[3].default == "All"
        and str(sig.return_annotation) == "list"
    )
    detail = (
        "url / use_wildcard / resource_type 仅限关键字（默认 ''/False/'All'），返回注解 list"
        if ok else f"公开签名不符合合同: {sig}"
    )
    return result("api_contract", "PASS" if ok else "FAIL", detail)


def exception_name(exc: BaseException) -> str:
    return type(exc).__name__


def error_detail(prefix: str, exc: BaseException) -> str:
    trace_info = str(getattr(exc, "trace_info", "") or "")
    suffix = f" [trace={trace_info}]" if trace_info else ""
    return f"{prefix}: {exception_name(exc)}: {exc}{suffix}"


def expect_raises(call, expected_type, label: str, expected_trace: str | None = None):
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
            trace_info=trace,
        )
    except Exception as exc:  # noqa: BLE001
        return result(label, "FAIL", f"拒绝类型错误，应为 {expected_type.__name__}: {exception_name(exc)}: {exc}")
    return result(label, "FAIL", "调用未被拒绝")


def fetch(page: WebBrowser, url: str, settle: float = 0.8):
    status = page.execute_javascript(fetch_code(url))
    time.sleep(settle)
    return status


def filter_case(page: WebBrowser, case_id: str, label: str, kwargs: dict, predicate, **extra):
    try:
        items = page.get_responses(**kwargs)
    except Exception as exc:  # noqa: BLE001
        return result(case_id, "FAIL", error_detail(f"{label} 调用失败", exc))
    urls = [str(item.get("url") or "") for item in items]
    types = sorted({str(item.get("type") or "") for item in items})
    ok = predicate(items, urls, types)
    return result(
        case_id,
        "PASS" if ok else "FAIL",
        f"{label} 命中 {len(items)} 条（types={types}）" if ok else
        f"{label} 结果不符: count={len(items)}, types={types}, urls={urls[:4]}",
        captured=len(items), types=types, **extra,
    )


def run(args):
    results = [check_contract()]
    if results[-1]["status"] != "PASS" or args.contract_only:
        return results, 0 if results[-1]["status"] == "PASS" else 1

    page = None
    monitor_started = False
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

        # 场景准备：启动监听并产生 Fetch(404) 与 Document(200) 两类真实请求
        try:
            page.start_monitor_network()
            monitor_started = True
            fetch_status = fetch(page, FETCH_404)
            page.reload()
            time.sleep(1.2)
            all_items = page.get_responses()
            results.append(result(
                "traffic_prepare",
                "PASS" if all_items else "FAIL",
                f"已产生并捕获 {len(all_items)} 条记录（fetch HTTP {fetch_status} + 页面刷新）"
                if all_items else "未捕获到任何记录，后续断言无意义",
                captured=len(all_items), fetch_status=fetch_status,
            ))
            if not all_items:
                return results, 1
        except Exception as exc:  # noqa: BLE001
            results.append(result("traffic_prepare", "BLOCKED", error_detail("无法准备网络流量", exc)))
            return results, 2

        # 目标用例 1：记录结构包含文档所述全部键
        robots = next((item for item in all_items if item.get("url") == FETCH_404), None)
        if robots is None:
            results.append(result("record_shape", "FAIL", f"未找到 {FETCH_404} 的记录"))
        else:
            missing = sorted(EXPECTED_KEYS - set(robots.keys()))
            type_issues = []
            if not isinstance(robots.get("url"), str):
                type_issues.append("url 非 str")
            if not isinstance(robots.get("type"), str):
                type_issues.append("type 非 str")
            if not isinstance(robots.get("method"), str):
                type_issues.append("method 非 str")
            if not isinstance(robots.get("status"), int):
                type_issues.append("status 非 int")
            if not isinstance(robots.get("base64Encoded"), bool):
                type_issues.append("base64Encoded 非 bool")
            if not isinstance(robots.get("requestHeaders"), dict):
                type_issues.append("requestHeaders 非 dict")
            ok = not missing and not type_issues
            results.append(result(
                "record_shape",
                "PASS" if ok else "FAIL",
                "记录包含 9 个文档所述键且关键字段类型正确" if ok else
                f"缺键={missing}, 类型问题={type_issues}",
                missing_keys=missing, type_issues=type_issues,
                record_keys=sorted(robots.keys()),
            ))

        # 目标用例 2：非 2xx 响应同样被记录且有响应体
        if robots is not None:
            body = robots.get("body")
            ok = robots.get("status") == 404 and isinstance(body, str) and len(body) > 0
            results.append(result(
                "non_2xx_recorded",
                "PASS" if ok else "FAIL",
                f"404 响应被记录：status=404 且 body {len(body) if isinstance(body, str) else '?'} 字符"
                if ok else f"结果不符: status={robots.get('status')!r}, body_type={type(body).__name__}",
                http_status=robots.get("status"), body_length=len(body) if isinstance(body, str) else 0,
            ))
        else:
            results.append(result("non_2xx_recorded", "FAIL", "缺少 404 记录，无法断言"))

        # 目标用例 3：Document 记录（2xx）与 body
        document = next((item for item in all_items if item.get("type") == "Document"), None)
        if document is None:
            results.append(result("document_recorded", "FAIL", "刷新后未记录到 Document 请求"))
        else:
            body = document.get("body")
            ok = (
                document.get("status") == 200
                and isinstance(document.get("base64Encoded"), bool)
                and isinstance(body, str)
                and len(body) > 0
                and str(document.get("url") or "").startswith(DOCUMENT_URL)
            )
            results.append(result(
                "document_recorded",
                "PASS" if ok else "FAIL",
                f"Document 记录 status=200、body {len(body) if isinstance(body, str) else '?'} 字符、"
                f"base64Encoded={document.get('base64Encoded')!r}" if ok else
                f"结果不符: status={document.get('status')!r}, url={document.get('url')!r}",
                http_status=document.get("status"), url=document.get("url"),
                body_length=len(body) if isinstance(body, str) else 0,
            ))

        # 目标用例 4-7：过滤语义
        results.append(filter_case(
            page, "type_filter_fetch", "resource_type='Fetch'", {"resource_type": "Fetch"},
            lambda items, urls, types: bool(items) and types == ["Fetch"],
        ))
        results.append(filter_case(
            page, "type_filter_document", "resource_type='Document'", {"resource_type": "Document"},
            lambda items, urls, types: bool(items) and types == ["Document"],
        ))
        results.append(filter_case(
            page, "type_union", "resource_type='XHR|Fetch'", {"resource_type": "XHR|Fetch"},
            lambda items, urls, types: types in (["Fetch"], ["XHR"], ["Fetch", "XHR"]) and bool(items),
        ))
        results.append(filter_case(
            page, "type_other_empty", "resource_type='Other'（本次无此类流量）", {"resource_type": "Other"},
            lambda items, urls, types: items == [],
        ))
        results.append(filter_case(
            page, "url_exact_match", "url 精确匹配", {"url": FETCH_404},
            lambda items, urls, types: bool(urls) and set(urls) == {FETCH_404},
        ))
        results.append(filter_case(
            page, "url_wildcard_match", "url='*/xpath/*' 通配", {"url": "*/xpath/*", "use_wildcard": True},
            lambda items, urls, types: bool(urls) and all("/xpath/" in u for u in urls),
        ))
        results.append(filter_case(
            page, "url_exact_nonmatch_empty", "url='robots' 精确不匹配", {"url": "robots"},
            lambda items, urls, types: items == [],
        ))

        # 目标用例 8：非法 resource_type
        results.append(expect_raises(
            lambda: page.get_responses(resource_type="Bogus"),
            InvalidParamsError, "invalid_resource_type", expected_trace="invalid_params",
        ))

        # 目标用例 9：没有活动监听时拒绝
        page.stop_monitor_network()
        monitor_started = False
        results.append(expect_raises(
            lambda: page.get_responses(),
            ActionError, "no_monitor_error", expected_trace="web_network_monitor_not_found",
        ))

        # 参数边界
        results.append(expect_raises(lambda: page.get_responses("x"), TypeError, "extra_positional"))
        results.append(expect_raises(
            lambda: page.get_responses(unsupported=True), TypeError, "unknown_keyword",
        ))
    except Exception as exc:  # noqa: BLE001
        results.append(result("scenario", "FAIL", error_detail("get_responses 场景执行失败", exc)))
    finally:
        if page is not None:
            if monitor_started:
                try:
                    page.stop_monitor_network()
                except Exception:  # noqa: BLE001
                    pass
            try:
                page.close(ignore_beforeunload=True)
                results.append(result("cleanup", "PASS", "已停止监听并仅关闭本次创建的测试页面"))
            except Exception as exc:  # noqa: BLE001
                results.append(result("cleanup", "FAIL", error_detail("测试页面关闭失败", exc)))

    statuses = {item["status"] for item in results}
    code = 1 if "FAIL" in statuses else (2 if "BLOCKED" in statuses else 0)
    return results, code


def main(argv=None):
    parser = argparse.ArgumentParser(description="WebBrowser.get_responses() 页面对象 API 验收")
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
    print("API     : uiautoma.web.WebBrowser.get_responses")
    print(f"页面    : {args.target_url}")
    print("进度     状态    测试项                  测试结果")
    print("────────────────────────────────────────────────────────────────────────")
    for index, current in enumerate(results, 1):
        status = current["status"]
        color = {"PASS": GREEN, "BLOCKED": YELLOW}.get(status, RED)
        label = {"PASS": "通过", "BLOCKED": "阻塞"}.get(status, "失败")
        print(f"{index:02d}/{len(results):02d}    {color}[{label}]{RESET}  {current['case_id']:<32}  {current['detail']}")
    print("────────────────────────────────────────────────────────────────────────")
    summary = "测试通过" if code == 0 else ("测试阻塞" if code == 2 else "测试失败")
    print(f"{summary} · {sum(item['status'] == 'PASS' for item in results)}/{len(results)} 通过 · 退出码 {code}")
    if args.json:
        print(json.dumps({
            "api": "uiautoma.web.WebBrowser.get_responses",
            "target_url": args.target_url,
            "mode": args.mode,
            "status": "PASS" if code == 0 else ("BLOCKED" if code == 2 else "FAIL"),
            "exit_code": code,
            "results": results,
        }, ensure_ascii=False, indent=2))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
