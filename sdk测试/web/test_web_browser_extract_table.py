"""WebBrowser.extract_table() 页面对象 API 专项验收（按合同拒绝）。

本 API 在当前源码中是**尚未实现的桩**：

```python
def extract_table(self, table_selector, *, exclude_thead=False, timeout=20) -> list[list[str]]:
    raise unsupported("web.browser.extract_table")
```

因此本次验收的目标不是「能否提取表格」，而是**核对它按合同拒绝**：
1. 公开签名与文档一致；
2. 抛出的是 `UnsupportedActionError`，消息与 `method` 正确；
3. **零 Runtime 交互** —— 在手工构造的 `WebBrowser`（假页面引用、无 Package、无页面、不连
   Runtime）上调用同样抛该异常，说明拒绝发生在 SDK 侧、早于任何参数校验与 RPC；
4. 任何参数形态（含非法类型）都得到同一异常，因为桩在参数校验之前即返回；
5. Python 层参数绑定仍然生效（缺参、多余位置参数、未知关键字 → `TypeError`）；
6. 在**确实存在 `<table>` 的靶场页**上调用仍然拒绝 —— 证明这是「未实现」而不是「找不到表格」。

靶场：维护者的官方靶场 `.../xpath/#/table-test`（该页含真实表格，用于第 6 点）。
退出码：0 = 全部 PASS；1 = 存在 FAIL；2 = 无非 FAIL 但存在 BLOCKED。
"""
from __future__ import annotations

import argparse
import inspect
import json
import time
import uuid
from pathlib import Path
from urllib.parse import urlsplit

from uiautoma import UnsupportedActionError, web
from uiautoma.web import WebBrowser

__test__ = False

DEFAULT_URL = "https://baobaomi900901.github.io/xpath/#/table-test"
FAKE_REF = {"id": "contract-stub-page", "session": ""}
EXPECTED_METHOD = "web.browser.extract_table"
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
    method = getattr(WebBrowser, "extract_table", None)
    sig = inspect.signature(method) if callable(method) else None
    if sig is None:
        return result("api_contract", "FAIL", "WebBrowser.extract_table 不存在")
    parameters = list(sig.parameters.values())
    names = tuple(sig.parameters)
    annotation = str(sig.return_annotation)
    ok = (
        names == ("self", "table_selector", "exclude_thead", "timeout")
        and parameters[1].kind is inspect.Parameter.POSITIONAL_OR_KEYWORD
        and parameters[1].default is inspect.Parameter.empty
        and parameters[2].kind is inspect.Parameter.KEYWORD_ONLY
        and parameters[2].default is False
        and parameters[3].kind is inspect.Parameter.KEYWORD_ONLY
        and parameters[3].default == 20
        and annotation == "list[list[str]]"
    )
    detail = (
        "table_selector 必填（位置或关键字），exclude_thead / timeout 仅限关键字（默认 False / 20），"
        "返回注解 list[list[str]]" if ok else f"公开签名不符合合同: {sig}"
    )
    return result("api_contract", "PASS" if ok else "FAIL", detail, return_annotation=annotation)


def exception_name(exc: BaseException) -> str:
    return type(exc).__name__


def error_detail(prefix: str, exc: BaseException) -> str:
    return f"{prefix}: {exception_name(exc)}: {exc}"


def unsupported_case(case_id: str, label: str, call, **extra):
    """断言调用抛出 UnsupportedActionError，且 method 与消息符合合同。"""
    started = time.perf_counter()
    try:
        call()
    except UnsupportedActionError as exc:
        elapsed = round(time.perf_counter() - started, 3)
        got_method = str(getattr(exc, "method", "") or "")
        ok = got_method == EXPECTED_METHOD and "暂不支持" in str(exc)
        return result(
            case_id, "PASS" if ok else "FAIL",
            f"{label} 抛 UnsupportedActionError（method={got_method}，{elapsed}s）：{exc}" if ok else
            f"{label} 异常内容不符: method={got_method!r}, message={str(exc)!r}",
            method=got_method, message=str(exc), elapsed_s=elapsed, **extra)
    except Exception as exc:  # noqa: BLE001
        return result(
            case_id, "FAIL",
            f"{label} 应抛 UnsupportedActionError，实际 {exception_name(exc)}: {exc}", **extra)
    return result(case_id, "FAIL", f"{label} 未抛异常（预期按合同拒绝）", **extra)


def type_error_case(case_id: str, label: str, call):
    try:
        call()
    except TypeError as exc:
        return result(case_id, "PASS", f"{label} → TypeError（{exc}）")
    except Exception as exc:  # noqa: BLE001
        return result(case_id, "FAIL", f"{label} 应抛 TypeError，实际 {exception_name(exc)}: {exc}")
    return result(case_id, "FAIL", f"{label} 未被拒绝")


def run(args):
    results = [check_contract()]
    if results[-1]["status"] != "PASS" or args.contract_only:
        return results, 0 if results[-1]["status"] == "PASS" else 1

    page = None
    page_id = ""
    try:
        # 目标用例 1：零 Runtime 交互 —— 手工构造页面对象，不连 Package / 页面 / Runtime
        try:
            stub_page = WebBrowser(dict(FAKE_REF), url="", title="", mode="chrome")
            results.append(unsupported_case(
                "zero_runtime_rejection", "无 Package / 无页面 / 不连 Runtime 时",
                lambda: stub_page.extract_table("anything"), fake_page_ref=True))
        except Exception as exc:  # noqa: BLE001
            results.append(result("zero_runtime_rejection", "FAIL", error_detail("构造桩页面对象失败", exc)))

        # 目标用例 2：拒绝类型不是「没有打开 Package」
        try:
            stub_page = WebBrowser(dict(FAKE_REF), url="", title="", mode="chrome")
            stub_page.extract_table("x")
            results.append(result("not_no_package_error", "FAIL", "未抛异常"))
        except UnsupportedActionError:
            results.append(result(
                "not_no_package_error", "PASS",
                "拒绝形态是 UnsupportedActionError，而非 NoCurrentPackageError（未走到 Package 检查）"))
        except Exception as exc:  # noqa: BLE001
            results.append(result("not_no_package_error", "FAIL", error_detail("异常类型不符", exc)))

        # 目标用例 3：任何参数形态都得到同一异常（桩在参数校验之前拒绝）
        stub_page = WebBrowser(dict(FAKE_REF), url="", title="", mode="chrome")
        shapes = [
            ("正常字符串选择器", lambda: stub_page.extract_table("table")),
            ("空字符串", lambda: stub_page.extract_table("")),
            ("None", lambda: stub_page.extract_table(None)),
            ("数字 123", lambda: stub_page.extract_table(123)),
            ("exclude_thead=True", lambda: stub_page.extract_table("x", exclude_thead=True)),
            ("timeout=0", lambda: stub_page.extract_table("x", timeout=0)),
            ("exclude_thead 传非法类型", lambda: stub_page.extract_table("x", exclude_thead="not-bool")),
        ]
        mismatches = []
        for label, call in shapes:
            item = unsupported_case("any_arguments_rejected", label, call)
            if item["status"] != "PASS":
                mismatches.append(item["detail"])
        results.append(result(
            "any_arguments_rejected",
            "PASS" if not mismatches else "FAIL",
            f"{len(shapes)} 种参数形态（含非法类型）均抛同一 UnsupportedActionError" if not mismatches
            else "；".join(mismatches),
            shapes=len(shapes)))

        # 目标用例 4：Python 层参数绑定仍生效
        results.append(type_error_case(
            "arg_binding_missing_selector", "缺少 table_selector",
            lambda: stub_page.extract_table()))
        results.append(type_error_case(
            "arg_binding_extra_positional", "多余位置参数（exclude_thead 仅限关键字）",
            lambda: stub_page.extract_table("x", 1)))
        results.append(type_error_case(
            "arg_binding_unknown_keyword", "未知关键字",
            lambda: stub_page.extract_table("x", unsupported=True)))

        # 目标用例 5：在确实存在 <table> 的靶场页上仍然拒绝
        try:
            page = web.create(args.target_url, mode=args.mode, load_timeout=args.load_timeout)
            page_id = page.id
            current = page.get_url()
            table_count = page.execute_javascript(
                "function () { return document.querySelectorAll('table').length }")
            prepared = isinstance(page, WebBrowser) and same_url(current, args.target_url)
            results.append(result(
                "table_page_prepare",
                "PASS" if prepared and int(table_count or 0) > 0 else "FAIL",
                f"靶场页存在 {table_count} 个 <table>（用于证明拒绝不是「找不到表格」）"
                if prepared and int(table_count or 0) > 0 else
                f"页面准备失败: url={current!r}, table_count={table_count!r}",
                url=current, table_count=table_count))
            if prepared and int(table_count or 0) > 0:
                results.append(unsupported_case(
                    "rejected_on_real_table_page", "在含真实表格的靶场页上",
                    lambda: page.extract_table("#root"), table_count=table_count))
        except Exception as exc:  # noqa: BLE001
            results.append(result("table_page_prepare", "BLOCKED", error_detail("无法准备含表格的靶场页", exc)))

        # 页面关闭并复核
        if page is not None:
            try:
                returned = page.close(ignore_beforeunload=True)
            except Exception as exc:  # noqa: BLE001
                results.append(result("page_close_verified", "FAIL", error_detail("page.close 调用失败", exc)))
            else:
                time.sleep(0.5)
                leftover = [p for p in web.get_all(mode=args.mode)
                            if str(getattr(p, "id", "") or "") == page_id]
                ok = returned is None and not leftover
                results.append(result(
                    "page_close_verified", "PASS" if ok else "FAIL",
                    "页面已关闭，且 web.get_all() 复核无残留" if ok else
                    f"关闭后仍有残留: return={returned!r}, leftover={len(leftover)}",
                    leftover_pages=len(leftover)))
            page = None
    except Exception as exc:  # noqa: BLE001
        results.append(result("scenario", "FAIL", error_detail("extract_table 场景执行失败", exc)))
    finally:
        page_close_error = ""
        if page is not None:
            try:
                page.close(ignore_beforeunload=True)
            except Exception as exc:  # noqa: BLE001
                page_close_error = f"{type(exc).__name__}: {exc}"
        leftover = []
        try:
            leftover = [p for p in web.get_all(mode=args.mode) if str(getattr(p, "id", "") or "") == page_id]
        except Exception as exc:  # noqa: BLE001
            page_close_error = page_close_error or f"get_all 复核失败: {type(exc).__name__}: {exc}"
        cleaned = not leftover and not page_close_error
        results.append(result(
            "cleanup", "PASS" if cleaned else "FAIL",
            "已关闭页面（get_all 复核无残留）；本 API 为桩，未创建 Package 与其它资源" if cleaned else
            f"清理不完整: 残留页面={len(leftover)}, close 错误={page_close_error or '无'}",
            leftover_pages=len(leftover), page_close_error=page_close_error))

    statuses = {item["status"] for item in results}
    code = 1 if "FAIL" in statuses else (2 if "BLOCKED" in statuses else 0)
    return results, code


def main(argv=None):
    parser = argparse.ArgumentParser(description="WebBrowser.extract_table() 页面对象 API 验收（按合同拒绝）")
    parser.add_argument("--target-url", default=DEFAULT_URL, help="含表格的靶场页")
    parser.add_argument("--mode", choices=("chrome", "edge"), default="chrome")
    parser.add_argument("--load-timeout", type=float, default=20)
    parser.add_argument("--contract-only", action="store_true")
    parser.add_argument("--json", action="store_true", help="在表格后额外输出 JSON 报告（用于归档验收产物）")
    args = parser.parse_args(argv)
    if args.load_timeout <= 0:
        parser.error("--load-timeout 必须大于 0")

    results, code = run(args)
    print("UIAutoma Web API 测试")
    print("API     : uiautoma.web.WebBrowser.extract_table")
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
            "api": "uiautoma.web.WebBrowser.extract_table",
            "target_url": args.target_url, "mode": args.mode,
            "status": "PASS" if code == 0 else ("BLOCKED" if code == 2 else "FAIL"),
            "exit_code": code, "results": results,
        }, ensure_ascii=False, indent=2))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
