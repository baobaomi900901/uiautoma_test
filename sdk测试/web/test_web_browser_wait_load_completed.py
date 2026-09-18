"""WebBrowser.wait_load_completed() 页面对象 API 专项验收。

说明：
本 API 只读、不需要导航历史前置，因此不受 issue #58 影响。
`timeout` 是**位置或关键字**参数（与同分支的 `go_back` / `go_forward` 的仅关键字不同），
源码另有等价别名 `wait_ready = wait_load_completed`，本脚本一并核对别名一致性。

「等待」是否真的发生，用零等待刷新制造未完成窗口后再等待来观察：
若等待前 `is_load_completed()` 为 `False`、等待返回后为 `True`，则该次等待确实覆盖了加载过程。

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
from _web_page_identity import count_key, leaked, page_alive, page_key

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
    method = getattr(WebBrowser, "wait_load_completed", None)
    sig = inspect.signature(method) if callable(method) else None
    if sig is None:
        return result("api_contract", "FAIL", "WebBrowser.wait_load_completed 不存在")
    parameters = list(sig.parameters.values())
    names = tuple(sig.parameters)
    annotation = str(sig.return_annotation)
    ok = (
        names == ("self", "timeout")
        and parameters[1].kind is inspect.Parameter.POSITIONAL_OR_KEYWORD
        and parameters[1].default == 20
        and annotation in {"None", "<class 'NoneType'>"}
    )
    alias = getattr(WebBrowser, "wait_ready", None)
    alias_same = alias is not None and getattr(alias, "__func__", None) is getattr(method, "__func__", None)
    detail = (
        "timeout 位置或关键字且默认 20，返回 None" if ok else f"公开签名不符合合同: {sig}"
    )
    if alias_same:
        detail += "；别名 wait_ready 指向同一实现"
    return result("api_contract", "PASS" if ok else "FAIL", detail,
                  return_annotation=annotation, alias_wait_ready_same=alias_same)


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


def timed(call):
    started = time.perf_counter()
    returned = call()
    return returned, round(time.perf_counter() - started, 3)


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
        results.append(result(
            "initial_state",
            "PASS" if same_url(initial_url, args.target_url) and bool(page_id) else "FAIL",
            "初始 URL 可读且页面标识（url|title）非空" if same_url(initial_url, args.target_url) and page_id else
            f"初始状态不符: url={initial_url!r}, page_key={page_id!r}",
        ))

        # 目标用例 1：已加载完成的页面，默认调用应立即返回 None
        try:
            returned, waited = timed(lambda: page.wait_load_completed())
        except Exception as exc:  # noqa: BLE001
            results.append(result("wait_default", "FAIL", error_detail("wait_load_completed() 调用失败", exc)))
        else:
            ok = returned is None
            results.append(result(
                "wait_default",
                "PASS" if ok else "FAIL",
                f"已加载完成的页面返回 None（{waited}s）" if ok else f"返回值不符: {returned!r}",
                returned=repr(returned), elapsed_s=waited,
            ))

        # 目标用例 2：timeout 作为位置参数
        try:
            returned, waited = timed(lambda: page.wait_load_completed(20))
        except Exception as exc:  # noqa: BLE001
            results.append(result("wait_positional", "FAIL", error_detail("位置参数调用失败", exc)))
        else:
            ok = returned is None
            results.append(result(
                "wait_positional",
                "PASS" if ok else "FAIL",
                f"位置参数 20 返回 None（{waited}s）" if ok else f"返回值不符: {returned!r}",
                returned=repr(returned), elapsed_s=waited,
            ))

        # 目标用例 3：真实等待路径——零等待刷新制造未完成窗口后再等待
        page.reload(load_timeout=0)
        pending_before = page.is_load_completed()
        try:
            returned, waited = timed(lambda: page.wait_load_completed(args.load_timeout))
        except Exception as exc:  # noqa: BLE001
            results.append(result(
                "wait_pending_load", "FAIL",
                error_detail("等待未完成页面时调用失败", exc),
                pending_before=repr(pending_before),
            ))
        else:
            after = page.is_load_completed()
            # main 已移除 WebBrowser.id：改为断言对象仍可驱动该标签
            alive, alive_detail = page_alive(page)
            ok = returned is None and after is True and alive
            results.append(result(
                "wait_pending_load",
                "PASS" if ok else "FAIL",
                (
                    f"等待返回 None（{waited}s）：等待前 is_load_completed={pending_before!r}，"
                    f"等待后为 True，页面对象仍可用（{alive_detail}）"
                    if ok
                    else f"结果不符: return={returned!r}, before={pending_before!r}, "
                         f"after={after!r}, alive={alive_detail}"
                ),
                returned=repr(returned),
                pending_before_wait=repr(pending_before),
                loaded_after_wait=repr(after),
                elapsed_s=waited,
            ))

        # 目标用例 4：timeout=0（文档：不等待加载完成）
        try:
            returned, waited = timed(lambda: page.wait_load_completed(timeout=0))
        except Exception as exc:  # noqa: BLE001
            results.append(result(
                "timeout_zero", "FAIL",
                error_detail("timeout=0 应不等待并返回 None", exc),
                elapsed_s=None,
            ))
        else:
            ok = returned is None
            results.append(result(
                "timeout_zero",
                "PASS" if ok else "FAIL",
                f"timeout=0 返回 None（{waited}s，不等待加载完成）" if ok else f"返回值不符: {returned!r}",
                returned=repr(returned), elapsed_s=waited,
            ))

        # 目标用例 5：timeout=-1（一直等待）；页面已加载完成，应立即返回
        try:
            returned, waited = timed(lambda: page.wait_load_completed(timeout=-1))
        except Exception as exc:  # noqa: BLE001
            results.append(result("timeout_minus_one", "FAIL", error_detail("timeout=-1 调用失败", exc)))
        else:
            ok = returned is None and waited < 5.0
            results.append(result(
                "timeout_minus_one",
                "PASS" if ok else "FAIL",
                f"timeout=-1 在已加载完成的页面上立即返回 None（{waited}s）" if ok else
                f"结果不符: return={returned!r}, elapsed={waited}s",
                returned=repr(returned), elapsed_s=waited,
            ))

        # 参数边界
        results.append(expect_rejected(
            lambda: page.wait_load_completed(timeout=-2),
            (ValueError,),
            "invalid_timeout",
        ))
        results.append(expect_rejected(
            lambda: page.wait_load_completed(timeout="bad"),  # type: ignore[arg-type]
            (ValueError,),
            "invalid_timeout_type",
        ))
        results.append(expect_rejected(
            lambda: page.wait_load_completed(unsupported=True),
            (TypeError,),
            "unknown_keyword",
        ))
    except Exception as exc:  # noqa: BLE001
        results.append(result("scenario", "FAIL", error_detail("wait_load_completed 场景执行失败", exc)))
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
    parser = argparse.ArgumentParser(description="WebBrowser.wait_load_completed() 页面对象 API 验收")
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
    print("API     : uiautoma.web.WebBrowser.wait_load_completed")
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
            "api": "uiautoma.web.WebBrowser.wait_load_completed",
            "target_url": args.target_url,
            "mode": args.mode,
            "status": "PASS" if code == 0 else ("BLOCKED" if code == 2 else "FAIL"),
            "exit_code": code,
            "results": results,
        }, ensure_ascii=False, indent=2))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
