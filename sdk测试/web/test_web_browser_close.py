"""WebBrowser.close() 页面对象 API 专项验收。

说明：
`close()` 是所有验收脚本的清理原语，本脚本对它做独立验收。

「标签页真的关了」不靠命令返回值判定，而是用三项独立观测：
1. `web.get_all()` 中不再包含本次带唯一运行标记（`uiautoma_close_run=<run_id>`）的页面；
2. 关闭后继续使用该页面对象会被拒绝（记录实际 trace）；
3. 收尾时对运行标记做全量扫描，确认零残留。

`beforeunload` 场景使用 `execution_world="MAIN"` 注入处理器，仅覆盖
`ignore_beforeunload=True` 的自动接受路径；`ignore_beforeunload=False` 且存在
`beforeunload` 处理器时会挂起原生对话框，本次不自动触发（见证据文档「明确排除」）。

退出码：0 = 全部 PASS；1 = 存在 FAIL；2 = 无非 FAIL 但存在 BLOCKED。
"""
from __future__ import annotations

import argparse
import inspect
import json
import time
import uuid
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from uiautoma import ActionError, web
from uiautoma.web import WebBrowser

__test__ = False

DEFAULT_URL = "https://baobaomi900901.github.io/xpath/#/iframe-shadow-form"
SECOND_URL = "https://baobaomi900901.github.io/xpath/#/element-html-test"
THIRD_URL = "https://baobaomi900901.github.io/xpath/#/cookie-test"
MARKER_KEY = "uiautoma_close_run"
BEFOREUNLOAD = (
    "function () { window.addEventListener('beforeunload', function (e) "
    "{ e.preventDefault(); e.returnValue = ''; }); return true; }"
)
GREEN, RED, YELLOW, RESET = "\x1b[92m", "\x1b[91m", "\x1b[93m", "\x1b[0m"


def result(case_id: str, status: str, detail: str, **extra):
    return {"case_id": case_id, "status": status, "detail": detail, **extra}


def check_contract():
    method = getattr(WebBrowser, "close", None)
    sig = inspect.signature(method) if callable(method) else None
    if sig is None:
        return result("api_contract", "FAIL", "WebBrowser.close 不存在")
    parameters = list(sig.parameters.values())
    names = tuple(sig.parameters)
    annotation = str(sig.return_annotation)
    ok = (
        names == ("self", "ignore_beforeunload")
        and parameters[1].kind is inspect.Parameter.KEYWORD_ONLY
        and parameters[1].default is False
        and annotation in {"None", "<class 'NoneType'>"}
    )
    detail = (
        "无公开位置参数，ignore_beforeunload 仅限关键字且默认 False，返回 None"
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


def expect_rejected(call, expected_types, label: str):
    try:
        call()
    except expected_types as exc:
        return result(label, "PASS", f"{exception_name(exc)} 正确拒绝")
    except Exception as exc:  # noqa: BLE001
        return result(label, "FAIL", f"拒绝类型错误，应为 {expected_types}: {exception_name(exc)}: {exc}")
    return result(label, "FAIL", "调用未被拒绝")


def marked_url(base: str, run_id: str) -> str:
    parts = urlsplit(base)
    query = [(k, v) for k, v in parse_qsl(parts.query, keep_blank_values=True) if k != MARKER_KEY]
    query.append((MARKER_KEY, run_id))
    return urlunsplit((parts.scheme, parts.netloc, parts.path or "/", urlencode(query), parts.fragment))


def marker_pages(mode: str, run_id: str):
    """返回当前仍存在的、带本次运行标记的页面对象。"""
    try:
        pages = web.get_all(mode)
    except Exception:  # noqa: BLE001
        return []
    return [page for page in pages if run_id in str(getattr(page, "url", "") or "")]


def wait_url_gone(mode: str, run_id: str, url: str, timeout: float = 8.0):
    """等待某个具体 URL 的带标记页面从 web.get_all 中消失。"""
    started = time.perf_counter()
    deadline = time.monotonic() + timeout

    def still_there():
        return [p for p in marker_pages(mode, run_id) if str(getattr(p, "url", "") or "") == url]

    remaining = still_there()
    while time.monotonic() < deadline and remaining:
        time.sleep(0.1)
        remaining = still_there()
    return (not remaining), [str(getattr(p, "url", "")) for p in remaining], round(time.perf_counter() - started, 3)


def run(args):
    results = [check_contract()]
    if results[-1]["status"] != "PASS" or args.contract_only:
        return results, 0 if results[-1]["status"] == "PASS" else 1

    run_id = uuid.uuid4().hex
    created: list[WebBrowser] = []
    try:
        # 用例 1：默认关闭
        try:
            page1 = web.create(marked_url(args.target_url, run_id), mode=args.mode, load_timeout=args.load_timeout)
            created.append(page1)
            page1_id = page1.id
            page1_url = page1.get_url()
            results.append(result(
                "page_prepare",
                "PASS" if isinstance(page1, WebBrowser) and page1_id else "FAIL",
                "已创建带运行标记的测试页面 1",
                run_id=run_id, url=page1_url, page_id=page1_id,
            ))
        except Exception as exc:  # noqa: BLE001
            results.append(result("page_prepare", "BLOCKED", error_detail("无法创建测试页面", exc)))
            return results, 2

        try:
            returned = page1.close()
        except Exception as exc:  # noqa: BLE001
            results.append(result("close_default", "FAIL", error_detail("close() 调用失败", exc)))
        else:
            gone, remaining, waited = wait_url_gone(args.mode, run_id, page1_url)
            ok = returned is None and gone
            results.append(result(
                "close_default",
                "PASS" if ok else "FAIL",
                f"返回 None，且 {waited}s 内该标签页已从 web.get_all 消失" if ok else
                f"结果不符: return={returned!r}, remaining={remaining!r}",
                returned=repr(returned), tab_gone=gone, seconds=waited,
            ))

        # 用例 2：关闭后继续使用该页面对象应被拒绝
        try:
            value = page1.get_url()
        except ActionError as exc:
            trace = str(getattr(exc, "trace_info", "") or "")
            results.append(result(
                "reuse_after_close",
                "PASS",
                f"关闭后复用被 {exception_name(exc)} 拒绝（trace={trace}）",
                trace_info=trace, failure_reason=failure_reason(exc),
            ))
        except Exception as exc:  # noqa: BLE001
            results.append(result("reuse_after_close", "FAIL", error_detail("拒绝类型不是 ActionError", exc)))
        else:
            results.append(result(
                "reuse_after_close",
                "FAIL",
                f"关闭后复用未被拒绝，仍返回 {value!r}",
            ))

        # 用例 3：ignore_beforeunload=True 关闭带 beforeunload 处理器的页面
        try:
            page2 = web.create(marked_url(SECOND_URL, run_id), mode=args.mode, load_timeout=args.load_timeout)
            created.append(page2)
            page2_url = page2.get_url()
            marker_ok = False
            try:
                marker_ok = page2.execute_javascript(BEFOREUNLOAD, execution_world="MAIN") is True
            except Exception as exc:  # noqa: BLE001
                results.append(result(
                    "beforeunload_handler_install", "BLOCKED",
                    error_detail("无法注入 beforeunload 处理器", exc),
                ))
            else:
                results.append(result(
                    "beforeunload_handler_install",
                    "PASS" if marker_ok else "FAIL",
                    "已在 MAIN world 注册 beforeunload 处理器" if marker_ok else "处理器注入未返回 True",
                    installed=marker_ok,
                ))
        except Exception as exc:  # noqa: BLE001
            results.append(result("beforeunload_handler_install", "BLOCKED", error_detail("无法创建测试页面 2", exc)))

        if len(created) > 1:
            try:
                returned = page2.close(ignore_beforeunload=True)
            except Exception as exc:  # noqa: BLE001
                results.append(result("close_ignore_beforeunload_true", "FAIL", error_detail("close(ignore_beforeunload=True) 失败", exc)))
            else:
                gone, remaining, waited = wait_url_gone(args.mode, run_id, page2_url)
                ok = returned is None and gone
                results.append(result(
                    "close_ignore_beforeunload_true",
                    "PASS" if ok else "FAIL",
                    f"返回 None，且带 beforeunload 处理器的页面在 {waited}s 内关闭" if ok else
                    f"结果不符: return={returned!r}, remaining={remaining!r}",
                    returned=repr(returned), tab_gone=gone, seconds=waited,
                ))

        # 用例 4：显式 ignore_beforeunload=False 关闭干净页面
        try:
            page3 = web.create(marked_url(THIRD_URL, run_id), mode=args.mode, load_timeout=args.load_timeout)
            created.append(page3)
            page3_url = page3.get_url()
            returned = page3.close(ignore_beforeunload=False)
        except Exception as exc:  # noqa: BLE001
            results.append(result("close_explicit_false", "FAIL", error_detail("close(ignore_beforeunload=False) 失败", exc)))
        else:
            gone, remaining, waited = wait_url_gone(args.mode, run_id, page3_url)
            ok = returned is None and gone
            results.append(result(
                "close_explicit_false",
                "PASS" if ok else "FAIL",
                f"显式 False 在干净页面上返回 None 且标签页在 {waited}s 内关闭" if ok else
                f"结果不符: return={returned!r}, remaining={remaining!r}",
                returned=repr(returned), tab_gone=gone, seconds=waited,
            ))

        # 参数边界：ignore_beforeunload 仅限关键字
        results.append(expect_rejected(lambda: page1.close(True), (TypeError,), "extra_positional"))
        results.append(expect_rejected(lambda: page1.close(unsupported=True), (TypeError,), "unknown_keyword"))
    except Exception as exc:  # noqa: BLE001
        results.append(result("scenario", "FAIL", error_detail("close 场景执行失败", exc)))
    finally:
        # 收尾：全量扫描运行标记并清理残留
        leftovers = marker_pages(args.mode, run_id)
        cleaned = 0
        errors: list[str] = []
        for page in leftovers:
            try:
                page.close(ignore_beforeunload=True)
                cleaned += 1
            except Exception as exc:  # noqa: BLE001
                errors.append(f"{type(exc).__name__}: {exc}")
        remaining = marker_pages(args.mode, run_id)
        passed = not remaining
        results.append(result(
            "cleanup",
            "PASS" if passed else "FAIL",
            f"本次运行标记零残留（收尾清理 {cleaned} 个遗留页面）" if passed else
            f"仍有 {len(remaining)} 个带运行标记的页面残留",
            leftover_found=len(leftovers), leftover_closed=cleaned, leftover_remaining=len(remaining),
            errors=errors,
        ))

    statuses = {item["status"] for item in results}
    code = 1 if "FAIL" in statuses else (2 if "BLOCKED" in statuses else 0)
    return results, code


def main(argv=None):
    parser = argparse.ArgumentParser(description="WebBrowser.close() 页面对象 API 验收")
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
    print("API     : uiautoma.web.WebBrowser.close")
    print(f"页面    : {args.target_url}")
    print("进度     状态    测试项                  测试结果")
    print("────────────────────────────────────────────────────────────────────────")
    for index, current in enumerate(results, 1):
        status = current["status"]
        color = {"PASS": GREEN, "BLOCKED": YELLOW}.get(status, RED)
        label = {"PASS": "通过", "BLOCKED": "阻塞"}.get(status, "失败")
        print(f"{index:02d}/{len(results):02d}    {color}[{label}]{RESET}  {current['case_id']:<30}  {current['detail']}")
    print("────────────────────────────────────────────────────────────────────────")
    summary = "测试通过" if code == 0 else ("测试阻塞" if code == 2 else "测试失败")
    print(f"{summary} · {sum(item['status'] == 'PASS' for item in results)}/{len(results)} 通过 · 退出码 {code}")
    if args.json:
        print(json.dumps({
            "api": "uiautoma.web.WebBrowser.close",
            "target_url": args.target_url,
            "mode": args.mode,
            "status": "PASS" if code == 0 else ("BLOCKED" if code == 2 else "FAIL"),
            "exit_code": code,
            "results": results,
        }, ensure_ascii=False, indent=2))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
