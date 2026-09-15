"""WebBrowser.is_load_completed() 页面对象 API 专项验收。

说明：
本 API 只读、无参数、不需要导航历史前置，因此不受 issue #58 影响。
「未加载完成」窗口在静态靶场上极短，本脚本对该路径采取**尽力捕捉 + 恢复必断言**：
零等待刷新后立即取值，记录是否捕捉到 `False`，但只对「随后必然恢复为 True」做强断言；
未捕捉到 `False` 的情形写入证据文档的「明确排除」，不伪装成已覆盖。

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

__test__ = False

DEFAULT_URL = "https://baobaomi900901.github.io/xpath/#/iframe-shadow-form"
SECOND_URL = "https://baobaomi900901.github.io/xpath/#/element-html-test"
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
    method = getattr(WebBrowser, "is_load_completed", None)
    sig = inspect.signature(method) if callable(method) else None
    if sig is None:
        return result("api_contract", "FAIL", "WebBrowser.is_load_completed 不存在")
    parameters = list(sig.parameters.values())
    names = tuple(sig.parameters)
    annotation = str(sig.return_annotation)
    ok = (
        names == ("self",)
        and annotation in {"bool", "<class 'bool'>"}
    )
    detail = "无参数，返回注解 bool" if ok else f"公开签名不符合合同: {sig}"
    return result("api_contract", "PASS" if ok else "FAIL", detail,
                  parameter_count=len(parameters), return_annotation=annotation)


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


def poll_loaded(page: WebBrowser, timeout: float = 10.0):
    """在 timeout 秒内轮询 is_load_completed()，返回 (是否完成, 耗时, 取值序列)。"""
    started = time.perf_counter()
    seen: list[object] = []
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        value = page.is_load_completed()
        seen.append(value)
        if value:
            return True, round(time.perf_counter() - started, 3), seen
        time.sleep(0.1)
    return False, round(time.perf_counter() - started, 3), seen


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

        # 目标用例 1：加载完成后应稳定返回 True（bool 类型）
        samples = [page.is_load_completed() for _ in range(3)]
        type_ok = all(isinstance(item, bool) for item in samples)
        value_ok = all(item is True for item in samples)
        passed = type_ok and value_ok
        results.append(result(
            "loaded_true",
            "PASS" if passed else "FAIL",
            "加载完成后连续三次返回 bool True" if passed else
            f"返回值不符: samples={samples!r}, all_bool={type_ok}",
            samples=[repr(item) for item in samples],
        ))

        # 目标用例 2：零等待刷新后取值（尽力捕捉未完成窗口），随后必须恢复为 True
        page.reload(load_timeout=0)
        immediate = page.is_load_completed()
        type_ok = isinstance(immediate, bool)
        caught_false = immediate is False
        recovered, waited, seen = poll_loaded(page)
        passed = type_ok and recovered and page.id == page_id
        results.append(result(
            "after_zero_wait_reload",
            "PASS" if passed else "FAIL",
            (
                f"零等待刷新后立即取值 {immediate!r}（{'捕捉到未完成窗口' if caught_false else '页面过快，未捕捉到未完成窗口'}），"
                f"并在 {waited}s 内恢复为 True"
                if passed
                else f"结果不符: immediate={immediate!r}, recovered={recovered}, waited={waited}s"
            ),
            immediate_value=repr(immediate),
            caught_false_window=caught_false,
            recovered=recovered,
            recovery_seconds=waited,
            samples_during_poll=len(seen),
        ))

        # 目标用例 3：导航到另一页面后同样为 True
        page.navigate(SECOND_URL, load_timeout=args.load_timeout)
        current = page.get_url()
        value = page.is_load_completed()
        passed = same_url(current, SECOND_URL) and value is True and page.id == page_id
        results.append(result(
            "after_navigate_loaded",
            "PASS" if passed else "FAIL",
            "导航到第二页面后返回 True，页面 id 不变" if passed else
            f"结果不符: url={current!r}, value={value!r}, id_changed={page.id != page_id}",
            value=repr(value),
        ))

        # 参数边界：本 API 无参数
        results.append(expect_rejected(lambda: page.is_load_completed(1), (TypeError,), "extra_positional"))
        results.append(expect_rejected(
            lambda: page.is_load_completed(timeout=1),
            (TypeError,),
            "unknown_keyword",
        ))
    except Exception as exc:  # noqa: BLE001
        results.append(result("scenario", "FAIL", error_detail("is_load_completed 场景执行失败", exc)))
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
    parser = argparse.ArgumentParser(description="WebBrowser.is_load_completed() 页面对象 API 验收")
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
    print("API     : uiautoma.web.WebBrowser.is_load_completed")
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
            "api": "uiautoma.web.WebBrowser.is_load_completed",
            "target_url": args.target_url,
            "mode": args.mode,
            "status": "PASS" if code == 0 else ("BLOCKED" if code == 2 else "FAIL"),
            "exit_code": code,
            "results": results,
        }, ensure_ascii=False, indent=2))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
