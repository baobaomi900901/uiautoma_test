"""WebBrowser.go_forward() 页面对象 API 专项验收。

前置说明（重要）：
`go_forward()` 必须先有「前进历史」，而制造前进历史只能先执行一次后退。
当前 `go_back()` 在特定序列下稳定失败，见
https://github.com/uiautoma/desktop/issues/58 ，实测规律为：

    back/forward 之后再次 navigate，紧跟的 back 必定失败
    （引擎原始原因 `Cannot find a next page in history.`）；
    在该 navigate 之后补一次页面级脚本命令即可恢复。

因此本脚本的每次后退前置都先尝试「直接 back」，失败后补一次
`execute_javascript()` 再重试，并在用例 detail 中记录实际走了哪条路径。
该预热是**已知缺陷的绕行**，属于场景准备动作，不是 `go_forward()` 的验收内容，
也不能被解读为 `go_forward()` 已在冷状态通过验收：**冷状态（不预热）的
`go_forward()` 本次不可达**，见证据文档的「明确排除」。

退出码：0 = 全部 PASS；1 = 存在 FAIL；2 = 无非 FAIL 但存在 BLOCKED（前置不可达）。
"""
from __future__ import annotations

import argparse
import inspect
import json
import time
from urllib.parse import urlsplit

from uiautoma import ActionError, web
from uiautoma.web import WebBrowser
from _web_page_identity import page_alive, tab_count

__test__ = False

DEFAULT_URL = "https://baobaomi900901.github.io/xpath/#/iframe-shadow-form"
SECOND_URL = "https://baobaomi900901.github.io/xpath/#/element-html-test"
THIRD_URL = "https://baobaomi900901.github.io/xpath/#/cookie-test"
FOURTH_URL = "https://baobaomi900901.github.io/xpath/#/form-controls"
FIFTH_URL = "https://baobaomi900901.github.io/xpath/#/keys-click-test"
HISTORY_PROBE = "function () { return history.length; }"
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
    method = getattr(WebBrowser, "go_forward", None)
    sig = inspect.signature(method) if callable(method) else None
    if sig is None:
        return result("api_contract", "FAIL", "WebBrowser.go_forward 不存在")
    parameters = list(sig.parameters.values())
    names = tuple(sig.parameters)
    return_annotation = str(sig.return_annotation)
    ok = (
        names == ("self", "load_timeout")
        and parameters[1].kind is inspect.Parameter.KEYWORD_ONLY
        and parameters[1].default == 20
        and return_annotation in {"None", "<class 'NoneType'>"}
    )
    detail = (
        "无公开位置参数，load_timeout 仅限关键字且默认 20，返回 None"
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
    trace_id = str(getattr(exc, "trace_id", "") or "")
    suffix = ""
    if trace_info:
        suffix += f" [trace={trace_info}]"
    if trace_id:
        suffix += f" [trace_id={trace_id}]"
    return f"{prefix}: {exception_name(exc)}: {exc}{suffix}"


def wait_for_url(page: WebBrowser, expected: str, timeout: float = 8.0):
    deadline = time.monotonic() + timeout
    last = ""
    while time.monotonic() < deadline:
        last = page.get_url()
        if same_url(last, expected):
            return True, last
        time.sleep(0.1)
    return False, last


def expect_rejected(call, expected_types, label: str):
    try:
        call()
    except expected_types as exc:
        return result(label, "PASS", f"{exception_name(exc)} 正确拒绝")
    except Exception as exc:  # noqa: BLE001
        return result(label, "FAIL", f"拒绝类型错误，应为 {expected_types}: {exception_name(exc)}: {exc}")
    return result(label, "FAIL", "调用未被拒绝")


def goto(page: WebBrowser, url: str, load_timeout: float):
    """场景准备：导航并等待 URL 收敛。"""
    page.navigate(url, load_timeout=load_timeout)
    return wait_for_url(page, url)


def warm(page: WebBrowser) -> None:
    """#58 绕行：一次页面级脚本命令，使紧随导航的 back 恢复可用。"""
    page.execute_javascript(HISTORY_PROBE)


def establish_forward_history(page: WebBrowser, target_url: str, back_to_url: str, load_timeout: float):
    """导航到 target_url 后退回 back_to_url，从而制造「可前进」状态。

    先按合同直接后退；命中 #58 时补一次页面级脚本命令再重试，并记录实际路径。
    """
    reached, url = goto(page, target_url, load_timeout)
    if not reached:
        return {"ok": False, "path": "none", "detail": f"导航未到达 {target_url!r}: {url!r}"}

    direct_error = ""
    try:
        returned = page.go_back(load_timeout=load_timeout)
        ok, back_url = wait_for_url(page, back_to_url)
        if returned is None and ok:
            return {"ok": True, "path": "direct", "detail": "直接 go_back 成功", "direct_error": ""}
        direct_error = f"返回 {returned!r} 但 URL 为 {back_url!r}"
    except Exception as exc:  # noqa: BLE001
        direct_error = f"{exception_name(exc)}: {failure_reason(exc) or exc}"

    warm(page)
    try:
        returned = page.go_back(load_timeout=load_timeout)
    except Exception as exc:  # noqa: BLE001
        return {
            "ok": False,
            "path": "warm",
            "detail": error_detail("预热后 go_back 仍失败", exc),
            "direct_error": direct_error,
        }
    ok, back_url = wait_for_url(page, back_to_url)
    return {
        "ok": returned is None and ok,
        "path": "warm",
        "detail": "预热后 go_back 成功" if returned is None and ok else
                  f"预热后返回 {returned!r}，URL 为 {back_url!r}",
        "direct_error": direct_error,
    }


def forward_case(page: WebBrowser, case_id: str, target_url: str, back_to_url: str,
                 load_timeout: float, *, call_load_timeout, poll_timeout: float = 8.0):
    """通用目标用例：建立前进历史 → 调用 go_forward → 校验返回值、URL 与页面对象可用性。"""
    tabs_before = tab_count()
    prep = establish_forward_history(page, target_url, back_to_url, load_timeout)
    if not prep["ok"]:
        return result(
            case_id,
            "BLOCKED",
            f"前进历史不可达（{prep['detail']}）；go_forward 未被验证",
            precond_path=prep["path"],
            precondition_error=prep.get("direct_error", ""),
        ), None

    try:
        returned = page.go_forward() if call_load_timeout is None else page.go_forward(load_timeout=call_load_timeout)
    except Exception as exc:  # noqa: BLE001
        return result(
            case_id,
            "FAIL",
            error_detail("go_forward 调用失败", exc),
            precond_path=prep["path"],
            precondition_direct_error=prep.get("direct_error", ""),
            trace_info=str(getattr(exc, "trace_info", "") or ""),
            failure_reason=failure_reason(exc),
            url_actual=page.get_url(),
        ), None

    ok, url = wait_for_url(page, target_url, poll_timeout)
    # main 已移除 WebBrowser.id：前进必然会改组合键，改用「对象仍可用 + 标签数量不变」
    alive, alive_detail = page_alive(page)
    tabs_after = tab_count()
    passed = returned is None and ok and alive and tabs_after == tabs_before
    return result(
        case_id,
        "PASS" if passed else "FAIL",
        (
            f"前进返回 None、到达 {target_url.rsplit('/', 1)[-1]}，"
            f"页面对象仍可用且未新开标签（前置路径 {prep['path']}）"
            if passed
            else f"前进结果不符: return={returned!r}, url={url!r}, alive={alive_detail}, "
                 f"tabs_added={tabs_after - tabs_before}"
        ),
        precond_path=prep["path"],
        precondition_direct_error=prep.get("direct_error", ""),
        returned=str(returned),
        url_actual=url,
        url_attr=page.url,
        page_alive=alive_detail,
        tabs_before=tabs_before,
        tabs_after=tabs_after,
    ), url


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
        initial_alive, initial_alive_detail = page_alive(page)
        initial_ok = same_url(initial_url, args.target_url) and initial_alive
        results.append(result(
            "initial_state",
            "PASS" if initial_ok else "FAIL",
            f"初始 URL 可读且页面对象可用（{initial_alive_detail}）" if initial_ok else
            f"初始状态不符: url={initial_url!r}, {initial_alive_detail}",
        ))

        reached_b, url_b = goto(page, SECOND_URL, args.load_timeout)
        reached_c, url_c = goto(page, THIRD_URL, args.load_timeout)
        results.append(result(
            "history_prepare",
            "PASS" if reached_b and reached_c else "FAIL",
            "已建立三页历史记录 A→B→C" if reached_b and reached_c else
            f"历史记录准备失败: B={url_b!r}, C={url_c!r}",
        ))
        if not (reached_b and reached_c):
            return results, 1

        # 目标用例 1：默认调用（不传任何参数）
        case, _ = forward_case(
            page, "go_forward_default", FOURTH_URL, THIRD_URL, args.load_timeout,
            call_load_timeout=None,
        )
        results.append(case)
        if case["status"] == "BLOCKED":
            return results, 2

        # 目标用例 2：显式关键字 load_timeout
        case, _ = forward_case(
            page, "go_forward_keyword", FIFTH_URL, FOURTH_URL, args.load_timeout,
            call_load_timeout=args.load_timeout,
        )
        results.append(case)

        # 目标用例 3：load_timeout=0，不等待加载完成，由独立轮询确认收敛
        case, _ = forward_case(
            page, "zero_timeout", SECOND_URL, FIFTH_URL, args.load_timeout,
            call_load_timeout=0,
        )
        results.append(case)

        # 负例：当前已位于历史末端（无前进项），应被明确拒绝且不改变页面
        before_no_entry = page.get_url()
        try:
            page.go_forward(load_timeout=args.load_timeout)
        except ActionError as exc:
            after_no_entry = page.get_url()
            unchanged = same_url(after_no_entry, before_no_entry)
            results.append(result(
                "no_forward_entry",
                "PASS" if unchanged else "FAIL",
                "无前进项时被 ActionError 拒绝，且当前页面未被改变" if unchanged else
                f"被拒绝但页面被改变: {before_no_entry!r} → {after_no_entry!r}",
                trace_info=str(getattr(exc, "trace_info", "") or ""),
                failure_reason=failure_reason(exc),
                url_before=before_no_entry,
                url_after=after_no_entry,
            ))
        except Exception as exc:  # noqa: BLE001
            results.append(result(
                "no_forward_entry",
                "FAIL",
                error_detail("无前进项时的拒绝类型不符，应为 ActionError", exc),
            ))
        else:
            results.append(result("no_forward_entry", "FAIL", "无前进项时调用未被拒绝"))

        # 参数边界
        results.append(expect_rejected(
            lambda: page.go_forward(load_timeout=-2),
            (ValueError,),
            "invalid_timeout",
        ))
        results.append(expect_rejected(
            lambda: page.go_forward(load_timeout="bad"),  # type: ignore[arg-type]
            (ValueError,),
            "invalid_timeout_type",
        ))
        results.append(expect_rejected(lambda: page.go_forward(1), (TypeError,), "extra_positional"))
        results.append(expect_rejected(
            lambda: page.go_forward(unsupported=True),
            (TypeError,),
            "unknown_keyword",
        ))
    except Exception as exc:  # noqa: BLE001
        results.append(result("scenario", "FAIL", error_detail("go_forward 场景执行失败", exc)))
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
    parser = argparse.ArgumentParser(description="WebBrowser.go_forward() 页面对象 API 验收")
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
    print("API     : uiautoma.web.WebBrowser.go_forward")
    print(f"页面    : {args.target_url}")
    print("进度     状态    测试项                  测试结果")
    print("────────────────────────────────────────────────────────────────────────")
    for index, current in enumerate(results, 1):
        status = current["status"]
        color = {"PASS": GREEN, "BLOCKED": YELLOW}.get(status, RED)
        label = {"PASS": "通过", "BLOCKED": "阻塞"}.get(status, "失败")
        print(f"{index:02d}/{len(results):02d}    {color}[{label}]{RESET}  {current['case_id']:<22}  {current['detail']}")
    print("────────────────────────────────────────────────────────────────────────")
    summary = "测试通过" if code == 0 else ("测试阻塞" if code == 2 else "测试失败")
    print(f"{summary} · {sum(item['status'] == 'PASS' for item in results)}/{len(results)} 通过 · 退出码 {code}")
    if args.json:
        print(json.dumps({
            "api": "uiautoma.web.WebBrowser.go_forward",
            "target_url": args.target_url,
            "mode": args.mode,
            "status": "PASS" if code == 0 else ("BLOCKED" if code == 2 else "FAIL"),
            "exit_code": code,
            "results": results,
        }, ensure_ascii=False, indent=2))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
