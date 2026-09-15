"""WebBrowser.start_monitor_network() 页面对象 API 专项验收。

说明：
监听由引擎通过 CDP 调试器实现（`Network.enable` + iframe 自动附加），不使用元素库、
不需要导航历史前置，也不依赖视口，因此不受 issue #58 与最小化窗口影响。

源码语义要点（本次实测核对）：
- `start` 的 `url` / `use_wildcard` / `resource_type` 是**存储级过滤**：不匹配的请求根本
  不会被记录（引擎在写入前即返回），因此 `get_responses()` 事后无法再取回被排除的类型；
- 重复 `start` 会**停掉旧监听并丢弃其历史记录**；
- 非法 `resource_type` 在 SDK/Runtime 侧即被拒绝（`InvalidParamsError`，trace `invalid_params`）。

「监听确实已启动」不靠命令返回 `None` 判定：脚本在 `start` 之后产生真实请求，再用
`get_responses()` 取回该请求作为独立证据。

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
FETCH_OK = "https://baobaomi900901.github.io/xpath/"
FETCH_404 = "https://baobaomi900901.github.io/xpath/robots.txt"


def fetch_code(url: str) -> str:
    return (f"function () {{ return fetch('{url}', {{cache: 'no-store'}})"
            f".then(function (r) {{ return r.status; }}); }}")


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
    method = getattr(WebBrowser, "start_monitor_network", None)
    sig = inspect.signature(method) if callable(method) else None
    if sig is None:
        return result("api_contract", "FAIL", "WebBrowser.start_monitor_network 不存在")
    parameters = list(sig.parameters.values())
    names = tuple(sig.parameters)
    annotation = str(sig.return_annotation)
    ok = (
        names == ("self", "url", "use_wildcard", "resource_type")
        and all(p.kind is inspect.Parameter.KEYWORD_ONLY for p in parameters[1:])
        and parameters[1].default == ""
        and parameters[2].default is False
        and parameters[3].default == "All"
        and annotation in {"None", "<class 'NoneType'>"}
    )
    detail = (
        "url / use_wildcard / resource_type 仅限关键字（默认 ''/False/'All'），返回 None"
        if ok else f"公开签名不符合合同: {sig}"
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
        )
    except Exception as exc:  # noqa: BLE001
        return result(label, "FAIL", f"拒绝类型错误，应为 {expected_type.__name__}: {exception_name(exc)}: {exc}")
    return result(label, "FAIL", "调用未被拒绝")


def fetch(page: WebBrowser, url: str, settle: float = 0.8):
    """用页面内 fetch 产生真实请求，返回 HTTP 状态码。"""
    status = page.execute_javascript(fetch_code(url))
    time.sleep(settle)
    return status


def response_urls(page: WebBrowser, **kwargs) -> list:
    return [str(item.get("url") or "") for item in page.get_responses(**kwargs)]


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

        # 目标用例 1：默认启动后确实能监听到真实请求
        try:
            returned = page.start_monitor_network()
            status_code = fetch(page, FETCH_404)
            urls = response_urls(page)
            matched = [u for u in urls if u == FETCH_404]
            ok = returned is None and matched and status_code == 404
            results.append(result(
                "start_default_captures",
                "PASS" if ok else "FAIL",
                f"默认启动后捕获到真实请求（HTTP {status_code}，共 {len(urls)} 条）" if ok else
                f"未捕获到目标请求: return={returned!r}, fetch_status={status_code}, urls={urls[:5]}",
                returned=repr(returned), captured=len(urls), fetch_status=status_code,
            ))
        except Exception as exc:  # noqa: BLE001
            results.append(result("start_default_captures", "FAIL", error_detail("默认启动用例失败", exc)))

        # 目标用例 2：重复启动会替换旧监听并丢弃旧记录
        try:
            page.start_monitor_network()
            stale = response_urls(page)
            status_code = fetch(page, FETCH_OK)
            fresh = response_urls(page)
            ok = stale == [] and any(u == FETCH_OK for u in fresh)
            results.append(result(
                "restart_discards_history",
                "PASS" if ok else "FAIL",
                f"重复启动后旧记录被丢弃（重启后即时读取 {len(stale)} 条），新请求正常捕获" if ok else
                f"结果不符: stale={stale[:3]}, fresh={fresh[:5]}, fetch_status={status_code}",
                stale_count=len(stale), fresh_count=len(fresh),
            ))
        except Exception as exc:  # noqa: BLE001
            results.append(result("restart_discards_history", "FAIL", error_detail("重复启动用例失败", exc)))

        # 目标用例 3：resource_type 是存储级过滤
        try:
            page.start_monitor_network(resource_type="Fetch")
            fetch(page, FETCH_OK)
            page.reload()
            time.sleep(1.0)
            all_urls = response_urls(page)
            all_types = {str(item.get("type") or "") for item in page.get_responses()}
            document_urls = response_urls(page, resource_type="Document")
            ok = bool(all_urls) and all_types == {"Fetch"} and document_urls == []
            results.append(result(
                "resource_type_filter_gates_storage",
                "PASS" if ok else "FAIL",
                f"resource_type='Fetch' 只记录 Fetch：{len(all_urls)} 条全为 Fetch，刷新产生的 Document 未被记录" if ok else
                f"结果不符: types={all_types}, count={len(all_urls)}, document={document_urls[:3]}",
                types=sorted(all_types), captured=len(all_urls), document_count=len(document_urls),
            ))
        except Exception as exc:  # noqa: BLE001
            results.append(result("resource_type_filter_gates_storage", "FAIL", error_detail("resource_type 过滤用例失败", exc)))

        # 目标用例 4：url 精确过滤是存储级过滤
        try:
            page.start_monitor_network(url=FETCH_404)
            fetch(page, FETCH_OK)
            fetch(page, FETCH_404)
            urls = response_urls(page)
            ok = bool(urls) and set(urls) == {FETCH_404}
            results.append(result(
                "url_filter_gates_storage",
                "PASS" if ok else "FAIL",
                f"url 精确过滤只记录目标 URL（{len(urls)} 条，其它请求未被记录）" if ok else
                f"结果不符: urls={urls[:5]}",
                captured=len(urls),
            ))
        except Exception as exc:  # noqa: BLE001
            results.append(result("url_filter_gates_storage", "FAIL", error_detail("url 过滤用例失败", exc)))

        # 目标用例 5：通配符过滤是存储级过滤
        try:
            page.start_monitor_network(url="*/xpath/*", use_wildcard=True)
            fetch(page, FETCH_404)
            page.reload()
            time.sleep(1.0)
            urls = response_urls(page)
            ok = len(urls) > 1 and all("/xpath/" in u for u in urls)
            results.append(result(
                "wildcard_filter_gates_storage",
                "PASS" if ok else "FAIL",
                f"通配符过滤生效：{len(urls)} 条 URL 均含 /xpath/" if ok else
                f"结果不符: urls={urls[:5]}",
                captured=len(urls),
            ))
        except Exception as exc:  # noqa: BLE001
            results.append(result("wildcard_filter_gates_storage", "FAIL", error_detail("通配符过滤用例失败", exc)))

        # 目标用例 6：非法 resource_type 被拒绝
        results.append(expect_raises(
            lambda: page.start_monitor_network(resource_type="Bogus"),
            InvalidParamsError, "invalid_resource_type", expected_trace="invalid_params",
        ))

        # 参数边界：全部仅限关键字
        results.append(expect_raises(lambda: page.start_monitor_network("x"), TypeError, "extra_positional"))
        results.append(expect_raises(
            lambda: page.start_monitor_network(unsupported=True), TypeError, "unknown_keyword",
        ))
    except Exception as exc:  # noqa: BLE001
        results.append(result("scenario", "FAIL", error_detail("start_monitor_network 场景执行失败", exc)))
    finally:
        if page is not None:
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
    parser = argparse.ArgumentParser(description="WebBrowser.start_monitor_network() 页面对象 API 验收")
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
    print("API     : uiautoma.web.WebBrowser.start_monitor_network")
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
            "api": "uiautoma.web.WebBrowser.start_monitor_network",
            "target_url": args.target_url,
            "mode": args.mode,
            "status": "PASS" if code == 0 else ("BLOCKED" if code == 2 else "FAIL"),
            "exit_code": code,
            "results": results,
        }, ensure_ascii=False, indent=2))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
