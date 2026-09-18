"""WebBrowser.navigate() 页面对象 API 专项验收。"""
from __future__ import annotations

import argparse
import inspect
import time
from urllib.parse import urlsplit

from uiautoma import InvalidParamsError, web
from uiautoma.web import WebBrowser
from _web_page_identity import page_alive, tab_count

__test__ = False

DEFAULT_URL = "https://baobaomi900901.github.io/xpath/#/iframe-shadow-form"
SECOND_URL = "https://baobaomi900901.github.io/xpath/#/element-html-test"
GREEN, RED, YELLOW, RESET = "\x1b[92m", "\x1b[91m", "\x1b[93m", "\x1b[0m"


def result(case_id: str, status: str, detail: str, **extra):
    return {"case_id": case_id, "status": status, "detail": detail, **extra}


def same_url(actual: str, expected: str) -> bool:
    """比较导航目标的 URL，允许协议和主机名大小写差异。"""
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
    method = getattr(WebBrowser, "navigate", None)
    sig = inspect.signature(method) if callable(method) else None
    if sig is None:
        return result("api_contract", "FAIL", "WebBrowser.navigate 不存在")
    parameters = list(sig.parameters.values())
    names = tuple(sig.parameters)
    return_annotation = str(sig.return_annotation)
    ok = (
        names == ("self", "url", "load_timeout")
        and parameters[1].kind is inspect.Parameter.POSITIONAL_OR_KEYWORD
        and parameters[1].default is inspect.Parameter.empty
        and parameters[2].kind is inspect.Parameter.KEYWORD_ONLY
        and parameters[2].default == 20
        and return_annotation in {"None", "<class 'NoneType'>"}
    )
    detail = (
        "url 必填，load_timeout 仅限关键字且默认 20，返回 None"
        if ok
        else f"公开签名不符合合同: {sig}"
    )
    return result("api_contract", "PASS" if ok else "FAIL", detail)


def exception_name(exc: BaseException) -> str:
    return type(exc).__name__


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
        # main 已移除 WebBrowser.id：初始状态改为断言对象可驱动该标签
        tabs_before = tab_count()
        initial_alive, initial_alive_detail = page_alive(page)
        initial_ok = same_url(initial_url, args.target_url) and initial_alive
        results.append(result(
            "initial_state",
            "PASS" if initial_ok else "FAIL",
            f"初始 URL 可读且页面对象可用（{initial_alive_detail}）" if initial_ok else
            f"初始状态不符: url={initial_url!r}, {initial_alive_detail}",
        ))

        returned = page.navigate(SECOND_URL, load_timeout=args.load_timeout)
        current = page.get_url()
        # main 已移除 WebBrowser.id：导航必然改组合键，改用「对象仍可用 + 标签数量不变」
        nav_alive, nav_alive_detail = page_alive(page)
        tabs_after = tab_count()
        ok = returned is None and same_url(current, SECOND_URL) and nav_alive and tabs_after == tabs_before
        results.append(result(
            "navigate_default",
            "PASS" if ok else "FAIL",
            "导航到第二页面成功，返回 None、页面对象仍可用且未新开标签" if ok else
            f"导航结果不符: return={returned!r}, url={current!r}, alive={nav_alive_detail}, "
            f"tabs_added={tabs_after - tabs_before}",
            actual_url=current,
        ))

        returned = page.navigate(args.target_url, load_timeout=args.load_timeout)
        current = page.get_url()
        ok = returned is None and same_url(current, args.target_url)
        results.append(result(
            "navigate_keyword",
            "PASS" if ok else "FAIL",
            "使用关键字 load_timeout 导航返回 None" if ok else f"关键字导航结果不符: url={current!r}",
            actual_url=current,
        ))

        schemeless = args.target_url.split("://", 1)[-1]
        returned = page.navigate(schemeless, load_timeout=args.load_timeout)
        current = page.get_url()
        expected_normalized = f"https://{schemeless}"
        ok = returned is None and same_url(current, expected_normalized)
        results.append(result(
            "schemeless_url",
            "PASS" if ok else "FAIL",
            "无协议 URL 自动补充 https 并导航成功" if ok else f"无协议导航结果不符: url={current!r}",
            actual_url=current,
        ))

        returned = page.navigate(args.target_url, load_timeout=0)
        ok, current = wait_for_url(page, args.target_url)
        results.append(result(
            "zero_timeout",
            "PASS" if returned is None and ok else "FAIL",
            "load_timeout=0 返回 None；随后独立轮询确认 URL 到达目标" if returned is None and ok else
            f"零等待导航未收敛: return={returned!r}, url={current!r}",
            actual_url=current,
        ))

        before_invalid = page.get_url()
        results.append(expect_rejected(
            lambda: page.navigate("   "),
            (InvalidParamsError,),
            "invalid_url",
        ))
        try:
            page.navigate(None)  # type: ignore[arg-type]
        except InvalidParamsError:
            none_rejected = True
        except Exception as exc:  # noqa: BLE001
            none_rejected = False
            results[-1]["detail"] += f"；None URL 类型错误，应为 InvalidParamsError，实际 {exception_name(exc)}"
        else:
            none_rejected = False
            results[-1]["detail"] += "；None URL 未被拒绝"
        unchanged = page.get_url() == before_invalid
        if not unchanged:
            results[-1]["status"] = "FAIL"
            results[-1]["detail"] += f"；URL 被意外改变为 {page.get_url()!r}"
        elif results[-1]["status"] == "PASS" and none_rejected:
            results[-1]["detail"] = "空白和 None URL 均被 InvalidParamsError 拒绝"

        before_timeout = page.get_url()
        results.append(expect_rejected(
            lambda: page.navigate(args.target_url, load_timeout=-2),
            (ValueError,),
            "invalid_timeout",
        ))
        results.append(expect_rejected(
            lambda: page.navigate(args.target_url, load_timeout="bad"),  # type: ignore[arg-type]
            (ValueError,),
            "invalid_timeout_type",
        ))
        if page.get_url() != before_timeout:
            results[-2]["status"] = "FAIL"
            results[-2]["detail"] += f"；URL 被意外改变为 {page.get_url()!r}"

        results.append(expect_rejected(lambda: page.navigate(), (TypeError,), "missing_url"))
        results.append(expect_rejected(lambda: page.navigate(args.target_url, 1), (TypeError,), "extra_positional"))
        results.append(expect_rejected(lambda: page.navigate(args.target_url, unsupported=True), (TypeError,), "unknown_keyword"))
    except Exception as exc:  # noqa: BLE001
        results.append(result("scenario", "FAIL", error_detail("navigate 场景执行失败", exc)))
    finally:
        if page is not None:
            try:
                page.close(ignore_beforeunload=True)
                results.append(result("cleanup", "PASS", "仅关闭本次创建的测试页面"))
            except Exception as exc:  # noqa: BLE001
                results.append(result("cleanup", "FAIL", error_detail("测试页面关闭失败", exc)))
    code = 0 if all(item["status"] == "PASS" for item in results) else 1
    return results, code


def main(argv=None):
    parser = argparse.ArgumentParser(description="WebBrowser.navigate() 页面对象 API 验收")
    parser.add_argument("--target-url", default=DEFAULT_URL)
    parser.add_argument("--mode", choices=("chrome", "edge"), default="chrome")
    parser.add_argument("--load-timeout", type=float, default=20)
    parser.add_argument("--contract-only", action="store_true")
    args = parser.parse_args(argv)
    if args.load_timeout <= 0:
        parser.error("--load-timeout 必须大于 0")

    results, code = run(args)
    print("UIAutoma Web API 测试")
    print("API     : uiautoma.web.WebBrowser.navigate")
    print(f"页面    : {args.target_url}")
    print("进度     状态    测试项                  测试结果")
    print("────────────────────────────────────────────────────────────────────────")
    for index, current in enumerate(results, 1):
        status = current["status"]
        color = {"PASS": GREEN, "BLOCKED": YELLOW}.get(status, RED)
        label = {"PASS": "通过", "BLOCKED": "阻塞"}.get(status, "失败")
        print(f"{index:02d}/{len(results):02d}    {color}[{label}]{RESET}  {current['case_id']:<22}  {current['detail']}")
    print("────────────────────────────────────────────────────────────────────────")
    summary = "测试通过" if code == 0 else "测试失败"
    print(f"{summary} · {sum(item['status'] == 'PASS' for item in results)}/{len(results)} 通过 · 退出码 {code}")
    return code


if __name__ == "__main__":
    raise SystemExit(main())
