"""WebBrowser.reload() 页面对象 API 专项验收。

说明：
`reload()` 与同分支的 `go_back()` / `go_forward()` 不同，**不需要导航历史前置**，
因此本脚本不调用后退/前进，也不受 issue #58 影响，可作为该分支的对照项。

「真的重新加载了」由两项独立观测确证：
1. `performance.timeOrigin` 变化（文档级身份变化）；
2. 刷新前注入的 JS 标记在刷新后被清除（隔离世界上下文被重建）。
两项只要有一项成立即判定重新加载已发生。

退出码：0 = 全部 PASS；1 = 存在 FAIL；2 = 无非 FAIL 但存在 BLOCKED。
"""
from __future__ import annotations

import argparse
import inspect
import json
import time
from urllib.parse import urlsplit

from uiautoma import web
from uiautoma.web import WebBrowser
from _web_page_identity import count_key, leaked, page_key

__test__ = False

DEFAULT_URL = "https://baobaomi900901.github.io/xpath/#/iframe-shadow-form"
SECOND_URL = "https://baobaomi900901.github.io/xpath/#/element-html-test"
TIME_ORIGIN = "function () { return performance.timeOrigin; }"
MARK = "function () { window.__uiautoma_reload_probe = 42; return window.__uiautoma_reload_probe; }"
MARK_CHECK = "function () { return window.__uiautoma_reload_probe === undefined; }"
GREEN, RED, YELLOW, RESET = "\x1b[92m", "\x1b[91m", "\x1b[93m", "\x1b[0m"


def result(case_id: str, status: str, detail: str, **extra):
    return {"case_id": case_id, "status": status, "detail": detail, **extra}


def same_url(actual: str, expected: str) -> bool:
    """比较 URL，允许协议和主机名大小写差异。"""
    a, e = urlsplit(str(actual)), urlsplit(str(expected))
    return (
        a.scheme.casefold(),
        a.netloc.casefold(),
        a.path or "/",
        a.query,
        a.fragment,
    ) == (
        e.scheme.casefold(),
        e.netloc.casefold(),
        e.path or "/",
        e.query,
        e.fragment,
    )


def check_contract():
    method = getattr(WebBrowser, "reload", None)
    sig = inspect.signature(method) if callable(method) else None
    if sig is None:
        return result("api_contract", "FAIL", "WebBrowser.reload 不存在")
    parameters = list(sig.parameters.values())
    names = tuple(sig.parameters)
    return_annotation = str(sig.return_annotation)
    ok = (
        names == ("self", "ignore_cache", "load_timeout")
        and parameters[1].kind is inspect.Parameter.POSITIONAL_OR_KEYWORD
        and parameters[1].default is False
        and parameters[2].kind is inspect.Parameter.KEYWORD_ONLY
        and parameters[2].default == 20
        and return_annotation in {"None", "<class 'NoneType'>"}
    )
    detail = (
        "ignore_cache 位置或关键字且默认 False，load_timeout 仅限关键字且默认 20，返回 None"
        if ok
        else f"公开签名不符合合同: {sig}"
    )
    return result("api_contract", "PASS" if ok else "FAIL", detail)


def exception_name(exc: BaseException) -> str:
    return type(exc).__name__


def failure_reason(exc: BaseException) -> str:
    """从 ActionError.result.raw 的嵌套原始响应里取出引擎 failure_reason。"""
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


def expect_rejected(call, expected_types, label: str):
    try:
        call()
    except expected_types as exc:
        return result(label, "PASS", f"{exception_name(exc)} 正确拒绝")
    except Exception as exc:  # noqa: BLE001
        return result(label, "FAIL", f"拒绝类型错误，应为 {expected_types}: {exception_name(exc)}: {exc}")
    return result(label, "FAIL", "调用未被拒绝")


def time_origin(page: WebBrowser):
    try:
        return float(page.execute_javascript(TIME_ORIGIN))
    except Exception:  # noqa: BLE001
        return None


def arm_marker(page: WebBrowser) -> bool:
    try:
        return page.execute_javascript(MARK) == 42
    except Exception:  # noqa: BLE001
        return False


def marker_cleared(page: WebBrowser):
    try:
        return bool(page.execute_javascript(MARK_CHECK))
    except Exception:  # noqa: BLE001
        return None


def observe_reload(page: WebBrowser, call, poll_timeout: float = 8.0) -> dict:
    """调用一次 reload，并用两项独立观测确证页面真的重新加载。"""
    before = time_origin(page)
    armed = arm_marker(page)
    started = time.perf_counter()
    try:
        returned = call()
    except Exception as exc:  # noqa: BLE001
        return {
            "ok": False,
            "error": exc,
            "time_origin_before": before,
            "marker_armed": armed,
            "elapsed_s": round(time.perf_counter() - started, 3),
        }

    deadline = time.monotonic() + poll_timeout
    after = before
    while time.monotonic() < deadline:
        after = time_origin(page)
        if before is None or after is None or after != before:
            break
        time.sleep(0.1)
    cleared = marker_cleared(page)
    changed = None if (before is None or after is None) else (after != before)
    confirmed = bool(changed) or cleared is True
    return {
        "ok": True,
        "error": None,
        "returned": returned,
        "elapsed_s": round(time.perf_counter() - started, 3),
        "time_origin_before": before,
        "time_origin_after": after,
        "time_origin_changed": changed,
        "marker_armed": armed,
        "marker_cleared": cleared,
        "reload_confirmed": confirmed,
        "url_after": page.get_url(),
    }


def reload_case(page: WebBrowser, case_id: str, call, expected_url: str, page_id: str):
    observation = observe_reload(page, call)
    if not observation["ok"]:
        exc = observation["error"]
        return result(
            case_id,
            "FAIL",
            error_detail("reload 调用失败", exc),
            trace_info=str(getattr(exc, "trace_info", "") or ""),
            failure_reason=failure_reason(exc),
            **{k: v for k, v in observation.items() if k in {"time_origin_before", "marker_armed", "elapsed_s"}},
        )

    url_ok = same_url(observation["url_after"], expected_url)
    # main 已移除 WebBrowser.id：刷新不改 url/title，组合键不变即等价断言
    id_ok = page_key(page) == page_id
    passed = (
        observation["returned"] is None
        and url_ok
        and id_ok
        and observation["reload_confirmed"]
    )
    if not (observation["time_origin_changed"] or observation["marker_cleared"] is not None):
        status = "BLOCKED"
        detail = "无法独立确证页面已重新加载（timeOrigin 与 JS 标记观测均不可用）"
    else:
        status = "PASS" if passed else "FAIL"
        detail = (
            f"返回 None、URL 与页面 id 不变，且独立确证已重新加载（{observation['elapsed_s']}s）"
            if passed
            else f"结果不符: return={observation['returned']!r}, url_ok={url_ok}, id_ok={id_ok}, "
                 f"time_origin_changed={observation['time_origin_changed']}, marker_cleared={observation['marker_cleared']}"
        )
    return result(case_id, status, detail, **{
        k: v for k, v in observation.items() if k not in {"ok", "error"}
    })


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

        page_id = page_key(page)
        initial_url = page.get_url()
        probe_ok = time_origin(page) is not None
        results.append(result(
            "initial_state",
            "PASS" if same_url(initial_url, args.target_url) and bool(page_id) else "FAIL",
            "初始 URL 可读、页面 id 非空，且 timeOrigin 探针可用" if probe_ok else
            "初始 URL 可读且页面标识（url|title）非空，但 timeOrigin 探针不可用（后续用例改用 JS 标记确证）",
            time_origin_probe_ok=probe_ok,
        ))

        # 目标用例 1：默认调用
        results.append(reload_case(page, "reload_default", lambda: page.reload(), args.target_url, page_id))

        # 目标用例 2：位置参数 ignore_cache=True
        results.append(reload_case(page, "reload_positional_ignore_cache", lambda: page.reload(True), args.target_url, page_id))

        # 目标用例 3：关键字 ignore_cache=False
        results.append(reload_case(
            page, "reload_ignore_cache_keyword",
            lambda: page.reload(ignore_cache=False, load_timeout=args.load_timeout),
            args.target_url, page_id,
        ))

        # 目标用例 4：load_timeout=0（不等待加载完成，由独立观测确认收敛）
        results.append(reload_case(page, "zero_timeout", lambda: page.reload(load_timeout=0), args.target_url, page_id))

        # 刷新后页面对象仍可用：元数据与读取接口正常，页面标识（url|title）不变
        try:
            url_after = page.get_url()
            title_after = page.get_title()
            html_after = page.get_html()
            usable = (
                same_url(url_after, args.target_url)
                and page_key(page) == page_id
                and isinstance(title_after, str)
                and isinstance(html_after, str)
                and len(html_after) > 0
            )
            results.append(result(
                "post_reload_usable",
                "PASS" if usable else "FAIL",
                "刷新后 get_url/get_title/get_html 正常且页面标识（url|title）不变" if usable else
                f"刷新后页面对象不可用: url={url_after!r}, key_changed={page_key(page) != page_id}, "
                f"html_len={len(html_after) if isinstance(html_after, str) else None}",
                title=title_after if isinstance(title_after, str) else "",
                html_length=len(html_after) if isinstance(html_after, str) else 0,
            ))
        except Exception as exc:  # noqa: BLE001
            results.append(result(
                "post_reload_usable",
                "FAIL",
                error_detail("刷新后读取接口失败", exc),
            ))

        # 参数边界
        results.append(expect_rejected(lambda: page.reload(load_timeout=-2), (ValueError,), "invalid_timeout"))
        results.append(expect_rejected(
            lambda: page.reload(load_timeout="bad"),  # type: ignore[arg-type]
            (ValueError,),
            "invalid_timeout_type",
        ))
        results.append(expect_rejected(lambda: page.reload(unsupported=True), (TypeError,), "unknown_keyword"))
    except Exception as exc:  # noqa: BLE001
        results.append(result("scenario", "FAIL", error_detail("reload 场景执行失败", exc)))
    finally:
        if page is not None:
            try:
                page.close(ignore_beforeunload=True)
                results.append(result("cleanup", "PASS", "仅关闭本次创建的测试页面"))
            except Exception as exc:  # noqa: BLE001
                results.append(result("cleanup", "FAIL", error_detail("测试页面关闭失败", exc)))

    statuses = {item["status"] for item in results}
    if "FAIL" in statuses:
        code = 1
    elif "BLOCKED" in statuses:
        code = 2
    else:
        code = 0
    return results, code


def main(argv=None):
    parser = argparse.ArgumentParser(description="WebBrowser.reload() 页面对象 API 验收")
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
    print("API     : uiautoma.web.WebBrowser.reload")
    print(f"页面    : {args.target_url}")
    print("进度     状态    测试项                  测试结果")
    print("────────────────────────────────────────────────────────────────────────")
    for index, current in enumerate(results, 1):
        status = current["status"]
        color = {"PASS": GREEN, "BLOCKED": YELLOW}.get(status, RED)
        label = {"PASS": "通过", "BLOCKED": "阻塞"}.get(status, "失败")
        print(f"{index:02d}/{len(results):02d}    {color}[{label}]{RESET}  {current['case_id']:<26}  {current['detail']}")
    print("────────────────────────────────────────────────────────────────────────")
    summary = "测试通过" if code == 0 else ("测试阻塞" if code == 2 else "测试失败")
    print(f"{summary} · {sum(item['status'] == 'PASS' for item in results)}/{len(results)} 通过 · 退出码 {code}")
    if args.json:
        print(json.dumps({
            "api": "uiautoma.web.WebBrowser.reload",
            "target_url": args.target_url,
            "mode": args.mode,
            "status": "PASS" if code == 0 else ("BLOCKED" if code == 2 else "FAIL"),
            "exit_code": code,
            "results": results,
        }, ensure_ascii=False, indent=2))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
