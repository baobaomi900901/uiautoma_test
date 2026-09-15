"""WebBrowser.go_back() 页面对象 API 专项验收。"""
from __future__ import annotations

import argparse
import inspect
import time
from urllib.parse import urlsplit

from uiautoma import web
from uiautoma.web import WebBrowser

__test__ = False
DEFAULT_URL = "https://baobaomi900901.github.io/xpath/#/iframe-shadow-form"
SECOND_URL = "https://baobaomi900901.github.io/xpath/#/element-html-test"
THIRD_URL = "https://baobaomi900901.github.io/xpath/#/cookie-test"
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
    method = getattr(WebBrowser, "go_back", None)
    sig = inspect.signature(method) if callable(method) else None
    if sig is None:
        return result("api_contract", "FAIL", "WebBrowser.go_back 不存在")
    params = list(sig.parameters.values())
    names = tuple(sig.parameters)
    annotation = str(sig.return_annotation)
    ok = (
        names == ("self", "load_timeout")
        and params[1].kind is inspect.Parameter.KEYWORD_ONLY
        and params[1].default == 20
        and annotation in {"None", "<class 'NoneType'>"}
    )
    return result(
        "api_contract",
        "PASS" if ok else "FAIL",
        "无公开位置参数，load_timeout 仅限关键字且默认 20，返回 None"
        if ok
        else f"公开签名不符合合同: {sig}",
    )


def error_detail(prefix: str, exc: BaseException) -> str:
    detail = f"{prefix}: {type(exc).__name__}: {exc}"
    trace = str(getattr(exc, "trace_info", "") or "")
    trace_id = str(getattr(exc, "trace_id", "") or "")
    if trace:
        detail += f" [trace={trace}]"
    if trace_id:
        detail += f" [trace_id={trace_id}]"
    return detail


def wait_for_url(page: WebBrowser, expected: str, timeout: float = 8.0):
    deadline = time.monotonic() + timeout
    current = ""
    while time.monotonic() < deadline:
        current = page.get_url()
        if same_url(current, expected):
            return True, current
        time.sleep(0.1)
    return False, current


def expect_value_error(call, case_id: str):
    try:
        call()
    except ValueError as exc:
        return result(case_id, "PASS", f"ValueError 正确拒绝: {exc}")
    except Exception as exc:  # noqa: BLE001
        return result(case_id, "FAIL", f"应拒绝为 ValueError，实际为 {type(exc).__name__}: {exc}")
    return result(case_id, "FAIL", "非法 timeout 未被拒绝")


def expect_type_error(call, case_id: str):
    try:
        call()
    except TypeError as exc:
        return result(case_id, "PASS", f"TypeError 正确拒绝: {exc}")
    except Exception as exc:  # noqa: BLE001
        return result(case_id, "FAIL", f"应拒绝为 TypeError，实际为 {type(exc).__name__}: {exc}")
    return result(case_id, "FAIL", "非法调用参数未被拒绝")


def run(args):
    results = [check_contract()]
    if results[-1]["status"] != "PASS" or args.contract_only:
        return results, 0 if results[-1]["status"] == "PASS" else 1

    page = None
    try:
        page = web.create(args.target_url, mode=args.mode, load_timeout=args.load_timeout)
        if not isinstance(page, WebBrowser):
            results.append(result("page_prepare", "FAIL", "create 返回类型错误"))
        else:
            results.append(result("page_prepare", "PASS", "已创建 WebBrowser 测试页面"))
            initial_id = page.id
            initial_url = page.get_url()
            results.append(result(
                "initial_state",
                "PASS" if initial_id and same_url(initial_url, args.target_url) else "FAIL",
                "初始 URL 可读且页面 id 非空" if initial_id and same_url(initial_url, args.target_url)
                else f"初始状态不符: url={initial_url!r}, id={initial_id!r}",
            ))

            page.navigate(SECOND_URL, load_timeout=args.load_timeout)
            second_ok, second_actual = wait_for_url(page, SECOND_URL)
            page.navigate(THIRD_URL, load_timeout=args.load_timeout)
            third_ok, third_actual = wait_for_url(page, THIRD_URL)
            setup_ok = second_ok and third_ok
            results.append(result(
                "history_prepare",
                "PASS" if setup_ok else "FAIL",
                "已建立三页历史记录 A→B→C" if setup_ok else
                f"历史记录准备失败: B={second_actual!r}, C={third_actual!r}",
            ))

            if setup_ok:
                returned = page.go_back(load_timeout=args.load_timeout)
                back_ok, back_actual = wait_for_url(page, SECOND_URL)
                results.append(result(
                    "go_back_default",
                    "PASS" if returned is None and back_ok and page.id == initial_id else "FAIL",
                    "默认后退返回 None，回到第二页面且 id 保持不变" if returned is None and back_ok and page.id == initial_id
                    else f"后退结果不符: return={returned!r}, url={back_actual!r}, id_changed={page.id != initial_id}",
                    actual_url=back_actual,
                ))

                returned = page.go_back(load_timeout=args.load_timeout)
                back_ok, back_actual = wait_for_url(page, args.target_url)
                results.append(result(
                    "go_back_keyword",
                    "PASS" if returned is None and back_ok else "FAIL",
                    "使用关键字 load_timeout 后退回初始页面" if returned is None and back_ok
                    else f"关键字后退结果不符: return={returned!r}, url={back_actual!r}",
                    actual_url=back_actual,
                ))

                page.navigate(SECOND_URL, load_timeout=args.load_timeout)
                wait_for_url(page, SECOND_URL)
                returned = page.go_back(load_timeout=0)
                zero_ok, zero_actual = wait_for_url(page, args.target_url)
                results.append(result(
                    "zero_timeout",
                    "PASS" if returned is None and zero_ok else "FAIL",
                    "load_timeout=0 返回 None；随后独立轮询确认回退完成" if returned is None and zero_ok
                    else f"零等待后退未收敛: return={returned!r}, url={zero_actual!r}",
                    actual_url=zero_actual,
                ))

                results.append(expect_value_error(lambda: page.go_back(load_timeout=-2), "invalid_timeout"))
                results.append(expect_value_error(lambda: page.go_back(load_timeout="bad"), "invalid_timeout_type"))  # type: ignore[arg-type]
                results.append(expect_type_error(lambda: page.go_back(1), "extra_positional"))
                results.append(expect_type_error(lambda: page.go_back(unsupported=True), "unknown_keyword"))
    except Exception as exc:  # noqa: BLE001
        results.append(result("scenario", "FAIL", error_detail("go_back 场景执行失败", exc)))
    finally:
        if page is not None:
            try:
                page.close(ignore_beforeunload=True)
                results.append(result("cleanup", "PASS", "仅关闭本次创建的测试页面"))
            except Exception as exc:  # noqa: BLE001
                results.append(result("cleanup", "FAIL", error_detail("测试页面关闭失败", exc)))
    return results, 0 if all(item["status"] == "PASS" for item in results) else 1


def main(argv=None):
    parser = argparse.ArgumentParser(description="WebBrowser.go_back() 页面对象 API 验收")
    parser.add_argument("--target-url", default=DEFAULT_URL)
    parser.add_argument("--mode", choices=("chrome", "edge"), default="chrome")
    parser.add_argument("--load-timeout", type=float, default=20)
    parser.add_argument("--contract-only", action="store_true")
    args = parser.parse_args(argv)
    if args.load_timeout <= 0:
        parser.error("--load-timeout 必须大于 0")

    results, code = run(args)
    print("UIAutoma Web API 测试")
    print("API     : uiautoma.web.WebBrowser.go_back")
    print(f"页面    : {args.target_url}")
    print("进度     状态    测试项                  测试结果")
    print("────────────────────────────────────────────────────────────────────────")
    for index, current in enumerate(results, 1):
        status = current["status"]
        color = {"PASS": GREEN, "BLOCKED": YELLOW}.get(status, RED)
        label = {"PASS": "通过", "BLOCKED": "阻塞"}.get(status, "失败")
        print(f"{index:02d}/{len(results):02d}    {color}[{label}]{RESET}  {current['case_id']:<22}  {current['detail']}")
    print("────────────────────────────────────────────────────────────────────────")
    print(f"{'测试通过' if code == 0 else '测试失败'} · {sum(item['status'] == 'PASS' for item in results)}/{len(results)} 通过 · 退出码 {code}")
    return code


if __name__ == "__main__":
    raise SystemExit(main())
