"""WebBrowser.stop_monitor_network() 页面对象 API 专项验收。

说明：
本 API 无参数，停止当前监听并释放引擎侧的调试器监听；不使用元素库、不需要导航历史前置，
也不依赖视口。

「监听确实停了」不靠命令返回 `None` 判定，而是用两项独立证据：
1. 停止后再调 `get_responses()` 抛 `ActionError`（trace `web_network_monitor_not_found`）；
2. 停止后页面仍可正常使用（`execute_javascript` 正常返回），说明停止监听没有破坏会话。

另外核对两个边界：重复停止是幂等的（无监听时也返回 `None`），停止后可以重新启动监听。

退出码：0 = 全部 PASS；1 = 存在 FAIL；2 = 无非 FAIL 但存在 BLOCKED。
"""
from __future__ import annotations

import argparse
import inspect
import json
import time
from urllib.parse import urlsplit

from uiautoma import ActionError, web
from uiautoma.web import WebBrowser

__test__ = False

DEFAULT_URL = "https://baobaomi900901.github.io/xpath/#/iframe-shadow-form"
FETCH_URL = "https://baobaomi900901.github.io/xpath/robots.txt"
PING = "function () { return 'alive'; }"
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
    method = getattr(WebBrowser, "stop_monitor_network", None)
    sig = inspect.signature(method) if callable(method) else None
    if sig is None:
        return result("api_contract", "FAIL", "WebBrowser.stop_monitor_network 不存在")
    names = tuple(sig.parameters)
    annotation = str(sig.return_annotation)
    ok = names == ("self",) and annotation in {"None", "<class 'NoneType'>"}
    detail = "无参数，返回 None" if ok else f"公开签名不符合合同: {sig}"
    return result("api_contract", "PASS" if ok else "FAIL", detail, return_annotation=annotation)


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

        # 场景准备：启动监听并确认确实捕获到流量
        try:
            page.start_monitor_network()
            monitor_started = True
            status_code = fetch(page, FETCH_URL)
            captured = page.get_responses()
            results.append(result(
                "monitor_prepare",
                "PASS" if captured else "FAIL",
                f"监听已启动并捕获 {len(captured)} 条记录（HTTP {status_code}）" if captured else
                "监听未捕获到任何记录",
                captured=len(captured), fetch_status=status_code,
            ))
            if not captured:
                return results, 1
        except Exception as exc:  # noqa: BLE001
            results.append(result("monitor_prepare", "BLOCKED", error_detail("无法准备监听", exc)))
            return results, 2

        # 目标用例 1：停止后不再可取回响应
        try:
            returned = page.stop_monitor_network()
            monitor_started = False
        except Exception as exc:  # noqa: BLE001
            results.append(result("stop_after_start", "FAIL", error_detail("stop_monitor_network() 调用失败", exc)))
        else:
            results.append(result(
                "stop_after_start",
                "PASS" if returned is None else "FAIL",
                "停止监听返回 None" if returned is None else f"返回值不符: {returned!r}",
                returned=repr(returned),
            ))
        results.append(expect_raises(
            lambda: page.get_responses(),
            ActionError, "stopped_no_events", expected_trace="web_network_monitor_not_found",
        ))

        # 目标用例 2：页面在停止监听后仍然可用
        try:
            alive = page.execute_javascript(PING)
            ok = alive == "alive"
            results.append(result(
                "page_usable_after_stop",
                "PASS" if ok else "FAIL",
                "停止监听后页面脚本仍正常执行（会话未被破坏）" if ok else f"页面不可用: {alive!r}",
                value=repr(alive),
            ))
        except Exception as exc:  # noqa: BLE001
            results.append(result("page_usable_after_stop", "FAIL", error_detail("停止后页面不可用", exc)))

        # 目标用例 3：重复停止是幂等的（此时已无监听）
        results.append(_idempotent_stop(page, "stop_idempotent", "再次停止（已无监听）"))

        # 目标用例 4：从未启动时停止也返回 None
        results.append(_idempotent_stop(page, "stop_without_monitor", "在从未启动监听的页面上停止"))

        # 目标用例 5：停止后可以重新启动监听
        try:
            page.start_monitor_network()
            monitor_started = True
            fetch(page, FETCH_URL)
            captured = page.get_responses()
            ok = bool(captured)
            results.append(result(
                "restart_after_stop",
                "PASS" if ok else "FAIL",
                f"停止后可重新启动监听并再次捕获 {len(captured)} 条记录" if ok else
                "重新启动后未捕获到记录",
                captured=len(captured),
            ))
        except Exception as exc:  # noqa: BLE001
            results.append(result("restart_after_stop", "FAIL", error_detail("停止后重启监听失败", exc)))

        # 参数边界：本 API 无参数
        results.append(expect_raises(lambda: page.stop_monitor_network(1), TypeError, "extra_positional"))
        results.append(expect_raises(
            lambda: page.stop_monitor_network(unsupported=True), TypeError, "unknown_keyword",
        ))
    except Exception as exc:  # noqa: BLE001
        results.append(result("scenario", "FAIL", error_detail("stop_monitor_network 场景执行失败", exc)))
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


def _idempotent_stop(page: WebBrowser, case_id: str, label: str):
    try:
        returned = page.stop_monitor_network()
    except Exception as exc:  # noqa: BLE001
        return result(case_id, "FAIL", error_detail(f"{label} 抛异常", exc))
    ok = returned is None
    return result(
        case_id,
        "PASS" if ok else "FAIL",
        f"{label} 返回 None（幂等，不报错）" if ok else f"返回值不符: {returned!r}",
        returned=repr(returned),
    )


def main(argv=None):
    parser = argparse.ArgumentParser(description="WebBrowser.stop_monitor_network() 页面对象 API 验收")
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
    print("API     : uiautoma.web.WebBrowser.stop_monitor_network")
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
            "api": "uiautoma.web.WebBrowser.stop_monitor_network",
            "target_url": args.target_url,
            "mode": args.mode,
            "status": "PASS" if code == 0 else ("BLOCKED" if code == 2 else "FAIL"),
            "exit_code": code,
            "results": results,
        }, ensure_ascii=False, indent=2))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
