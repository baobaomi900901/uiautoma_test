"""WebBrowser.find_all_by_css() 页面对象 API 专项验收。

靶场：**维护者的官方靶场** `https://baobaomi900901.github.io/xpath/#/form-controls`
（测试侧不自建页面；靶场由维护者维护，push 后自动部署）。

期望值来源：**活 DOM 推导** —— 先用 `execute_javascript()` 现场读出
`document.querySelectorAll('input').length`，再与该 API 返回的列表长度比对；
「不存在」用每次运行随机生成的 id `#uiautomata-absent-<uuid>`，无需靶场预留类名。

与 `find_by_css()` 的关键差异：本 API 返回 `list`，**未匹配时返回空列表而不抛异常**。

关闭顺序：**先关页面并复核，再关 Package**（`Package.close()` 会释放共享连接）。
退出码：0 = 全部 PASS；1 = 存在 FAIL；2 = 无非 FAIL 但存在 BLOCKED。
"""
from __future__ import annotations

import argparse
import inspect
import json
import shutil
import time
import uuid
from pathlib import Path
from urllib.parse import urlsplit

import uiautoma
from uiautoma import InvalidParamsError, NoCurrentPackageError, RpcProtocolError, web
from uiautoma.web import WebBrowser

__test__ = False

DEFAULT_URL = "https://baobaomi900901.github.io/xpath/#/form-controls"
DEFAULT_LIBRARY = Path(r"D:\code\元素库\260902_web元素")
LIB_TMP_ROOT = Path(__file__).resolve().parents[1] / ".pytest_tmp"
UNIQUE_CSS = "#root"
MULTI_CSS = "input"
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
    method = getattr(WebBrowser, "find_all_by_css", None)
    sig = inspect.signature(method) if callable(method) else None
    if sig is None:
        return result("api_contract", "FAIL", "WebBrowser.find_all_by_css 不存在")
    parameters = list(sig.parameters.values())
    names = tuple(sig.parameters)
    ok = (
        names == ("self", "css_selector", "timeout")
        and parameters[1].kind is inspect.Parameter.POSITIONAL_OR_KEYWORD
        and parameters[1].default is inspect.Parameter.empty
        and parameters[2].kind is inspect.Parameter.KEYWORD_ONLY
        and parameters[2].default == 20
        and str(sig.return_annotation) == "list[WebElement]"
    )
    detail = (
        "css_selector 必填，timeout 仅限关键字且默认 20，返回注解 list[WebElement]"
        if ok else f"公开签名不符合合同: {sig}"
    )
    return result("api_contract", "PASS" if ok else "FAIL", detail)


def exception_name(exc: BaseException) -> str:
    return type(exc).__name__


def error_detail(prefix: str, exc: BaseException) -> str:
    trace_info = str(getattr(exc, "trace_info", "") or "")
    return f"{prefix}: {exception_name(exc)}: {exc}" + (f" [trace={trace_info}]" if trace_info else "")


def expect_raises(call, expected_type, label: str, message_contains: str = "",
                  min_elapsed: float | None = None, max_elapsed: float | None = None):
    started = time.perf_counter()
    try:
        call()
    except expected_type as exc:
        elapsed = round(time.perf_counter() - started, 3)
        text = str(exc)
        if message_contains and message_contains not in text:
            return result(label, "FAIL", f"{exception_name(exc)} 消息不含 {message_contains!r}：{text}", elapsed_s=elapsed)
        if min_elapsed is not None and elapsed < min_elapsed:
            return result(label, "FAIL", f"耗时过短：{elapsed}s < {min_elapsed}s", elapsed_s=elapsed)
        if max_elapsed is not None and elapsed > max_elapsed:
            return result(label, "FAIL", f"耗时过长：{elapsed}s > {max_elapsed}s", elapsed_s=elapsed)
        return result(label, "PASS", f"{exception_name(exc)} 正确拒绝（{elapsed}s）：{text}", elapsed_s=elapsed)
    except Exception as exc:  # noqa: BLE001
        return result(label, "FAIL", f"拒绝类型错误，应为 {expected_type.__name__}: {exception_name(exc)}: {exc}")
    return result(label, "FAIL", "调用未被拒绝")


def list_case(page: WebBrowser, case_id: str, label: str, call,
              expected_count: int | None = None, min_elapsed: float | None = None,
              max_elapsed: float | None = None):
    started = time.perf_counter()
    try:
        items = call()
    except Exception as exc:  # noqa: BLE001
        return result(case_id, "FAIL", error_detail(f"{label} 不应抛异常", exc))
    elapsed = round(time.perf_counter() - started, 3)
    if not isinstance(items, list):
        return result(case_id, "FAIL", f"{label} 应返回 list，实际 {type(items).__name__}", elapsed_s=elapsed)
    if expected_count is not None and len(items) != expected_count:
        return result(
            case_id, "FAIL",
            f"{label} 数量与活 DOM 不一致：期望 {expected_count}，实际 {len(items)}", elapsed_s=elapsed)
    if min_elapsed is not None and elapsed < min_elapsed:
        return result(case_id, "FAIL", f"{label} 耗时过短：{elapsed}s < {min_elapsed}s", elapsed_s=elapsed)
    if max_elapsed is not None and elapsed > max_elapsed:
        return result(case_id, "FAIL", f"{label} 耗时过长：{elapsed}s > {max_elapsed}s", elapsed_s=elapsed)
    if items and not all(str(getattr(i, "id", "") or "").startswith("rt:web:") for i in items):
        return result(case_id, "FAIL", f"{label} 返回元素 id 前缀不是 rt:web:", elapsed_s=elapsed)
    return result(
        case_id, "PASS", f"{label} 返回 list[{len(items)}]（{elapsed}s）",
        count=len(items), elapsed_s=elapsed)


def run(args):
    results = [check_contract()]
    if results[-1]["status"] != "PASS" or args.contract_only:
        return results, 0 if results[-1]["status"] == "PASS" else 1

    run_id = uuid.uuid4().hex
    absent_id = f"uiautomata-absent-{run_id[:12]}"
    copy_dir = LIB_TMP_ROOT / run_id
    package = None
    page = None
    page_id = ""
    try:
        try:
            if not args.library.is_dir():
                results.append(result("library_prepare", "BLOCKED", f"元素库不存在: {args.library}"))
                return results, 2
            shutil.copytree(args.library, copy_dir)
            package = uiautoma.open(str(copy_dir), timeout=20, connect_timeout=20)
            results.append(result(
                "library_prepare", "PASS",
                f"已打开元素库副本：web 元素 {package.web_count} 个", web_count=package.web_count))
        except Exception as exc:  # noqa: BLE001
            results.append(result("library_prepare", "BLOCKED", error_detail("无法准备元素库", exc)))
            return results, 2

        try:
            page = web.create(args.target_url, mode=args.mode, load_timeout=args.load_timeout)
            page_id = page.id
            current = page.get_url()
            ok = isinstance(page, WebBrowser) and same_url(current, args.target_url)
            results.append(result(
                "page_prepare", "PASS" if ok else "FAIL",
                "已打开官方靶场页" if ok else f"URL 不符: {current!r}", url=current))
            if not ok:
                return results, 1
        except Exception as exc:  # noqa: BLE001
            results.append(result("page_prepare", "BLOCKED", error_detail("无法打开靶场页", exc)))
            return results, 2

        try:
            dom = page.execute_javascript(
                "function () { const l = document.querySelectorAll('input');"
                " return {multiCount: l.length,"
                " uniqueOk: document.querySelectorAll('#root').length === 1,"
                f" absentOk: document.querySelectorAll('#{absent_id}').length === 0"
                "}}")
            multi_count = int(dom.get("multiCount") or 0) if isinstance(dom, dict) else 0
            ok = (
                isinstance(dom, dict)
                and multi_count >= 2
                and dom.get("uniqueOk") is True
                and dom.get("absentOk") is True
            )
            results.append(result(
                "dom_expectations", "PASS" if ok else "FAIL",
                f"活 DOM 推导完成：{MULTI_CSS} 匹配 {multi_count} 个，{UNIQUE_CSS} 唯一，随机 id 不存在" if ok else
                f"DOM 前提不满足: {dom}", multi_count=multi_count))
            if not ok:
                return results, 1
        except Exception as exc:  # noqa: BLE001
            results.append(result("dom_expectations", "BLOCKED", error_detail("无法读取 DOM 期望值", exc)))
            return results, 2

        # 目标用例 1：多命中数量与活 DOM 一致
        results.append(list_case(
            page, "multi_count_matches_dom", f"{MULTI_CSS} 多命中（应与 DOM 数量一致）",
            lambda: page.find_all_by_css(MULTI_CSS, timeout=args.timeout), expected_count=multi_count))

        # 目标用例 2：唯一命中返回长度为 1 的列表
        results.append(list_case(
            page, "unique_list_of_one", f"{UNIQUE_CSS} 唯一命中",
            lambda: page.find_all_by_css(UNIQUE_CSS, timeout=args.timeout), expected_count=1))

        # 目标用例 3-4：不存在的选择器
        absent = f"#{absent_id}"
        results.append(list_case(
            page, "not_found_empty_waits", f"{absent} 未匹配（timeout=3）",
            lambda: page.find_all_by_css(absent, timeout=3), expected_count=0, min_elapsed=2.5))
        results.append(list_case(
            page, "not_found_timeout_zero_fast", f"{absent} 未匹配（timeout=0）",
            lambda: page.find_all_by_css(absent, timeout=0), expected_count=0, max_elapsed=1.0))

        # 目标用例 5：timeout=0 且存在
        results.append(list_case(
            page, "timeout_zero_present", f"{UNIQUE_CSS}（timeout=0）",
            lambda: page.find_all_by_css(UNIQUE_CSS, timeout=0), expected_count=1))

        # 目标用例 6：CSS 语法非法 → RpcProtocolError（不返回空列表），页面仍可用
        results.append(expect_raises(
            lambda: page.find_all_by_css("input[", timeout=3),
            RpcProtocolError, "malformed_syntax_rejected", max_elapsed=1.0))
        try:
            alive = page.get_title()
            results.append(result(
                "page_usable_after_malformed", "PASS" if alive else "FAIL",
                f"语法非法后页面仍可用（title={alive!r}）" if alive else "页面不可用"))
        except Exception as exc:  # noqa: BLE001
            results.append(result("page_usable_after_malformed", "FAIL", error_detail("页面不可用", exc)))

        # 参数校验
        results.append(expect_raises(lambda: page.find_all_by_css(""), InvalidParamsError, "empty_selector"))
        results.append(expect_raises(lambda: page.find_all_by_css("   "), InvalidParamsError, "blank_selector"))
        results.append(expect_raises(lambda: page.find_all_by_css(None), InvalidParamsError, "non_str_selector"))
        results.append(expect_raises(
            lambda: page.find_all_by_css(UNIQUE_CSS, timeout=-2), InvalidParamsError, "invalid_timeout"))
        results.append(expect_raises(
            lambda: page.find_all_by_css(UNIQUE_CSS, timeout="bad"), InvalidParamsError, "invalid_timeout_type"))
        results.append(expect_raises(lambda: page.find_all_by_css(), TypeError, "missing_selector"))
        results.append(expect_raises(lambda: page.find_all_by_css(UNIQUE_CSS, 1), TypeError, "positional_timeout"))

        # 关闭页面并复核（必须先关页面再关 Package）
        closed_page = page
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

        try:
            package.close()
            results.append(result("package_close_verified", "PASS", "Package 已关闭"))
        except Exception as exc:  # noqa: BLE001
            results.append(result("package_close_verified", "FAIL", error_detail("Package 关闭失败", exc)))
        package = None

        results.append(expect_raises(
            lambda: closed_page.find_all_by_css(UNIQUE_CSS, timeout=1), NoCurrentPackageError,
            "no_package_rejected", message_contains="Package"))
    except Exception as exc:  # noqa: BLE001
        results.append(result("scenario", "FAIL", error_detail("find_all_by_css 场景执行失败", exc)))
    finally:
        page_close_error = ""
        if page is not None:
            try:
                page.close(ignore_beforeunload=True)
            except Exception as exc:  # noqa: BLE001
                page_close_error = f"{type(exc).__name__}: {exc}"
        if package is not None:
            try:
                package.close()
            except Exception:  # noqa: BLE001
                pass
        shutil.rmtree(copy_dir, ignore_errors=True)
        leftover = []
        try:
            leftover = [p for p in web.get_all(mode=args.mode) if str(getattr(p, "id", "") or "") == page_id]
        except Exception as exc:  # noqa: BLE001
            page_close_error = page_close_error or f"get_all 复核失败: {type(exc).__name__}: {exc}"
        cleaned = not leftover and not page_close_error and not copy_dir.exists()
        results.append(result(
            "cleanup", "PASS" if cleaned else "FAIL",
            "已关闭页面（get_all 复核无残留）、关闭 Package、删除元素库副本" if cleaned else
            f"清理不完整: 残留页面={len(leftover)}, close 错误={page_close_error or '无'}, "
            f"副本残留={copy_dir.exists()}",
            leftover_pages=len(leftover), page_close_error=page_close_error,
            library_copy_removed=not copy_dir.exists()))

    statuses = {item["status"] for item in results}
    code = 1 if "FAIL" in statuses else (2 if "BLOCKED" in statuses else 0)
    return results, code


def main(argv=None):
    parser = argparse.ArgumentParser(description="WebBrowser.find_all_by_css() 页面对象 API 验收")
    parser.add_argument("--target-url", default=DEFAULT_URL, help="靶场页（默认官方靶场 form-controls）")
    parser.add_argument("--mode", choices=("chrome", "edge"), default="chrome")
    parser.add_argument("--load-timeout", type=float, default=20)
    parser.add_argument("--timeout", type=float, default=8, help="find_all 的 timeout，默认 8")
    parser.add_argument("--library", type=Path, default=DEFAULT_LIBRARY, help="元素库目录")
    parser.add_argument("--contract-only", action="store_true")
    parser.add_argument("--json", action="store_true", help="在表格后额外输出 JSON 报告（用于归档验收产物）")
    args = parser.parse_args(argv)
    if args.load_timeout <= 0:
        parser.error("--load-timeout 必须大于 0")

    results, code = run(args)
    print("UIAutoma Web API 测试")
    print("API     : uiautoma.web.WebBrowser.find_all_by_css")
    print(f"页面    : {args.target_url}")
    print("进度     状态    测试项                  测试结果")
    print("────────────────────────────────────────────────────────────────────────")
    for index, current in enumerate(results, 1):
        status = current["status"]
        color = {"PASS": GREEN, "BLOCKED": YELLOW}.get(status, RED)
        label = {"PASS": "通过", "BLOCKED": "阻塞"}.get(status, "失败")
        print(f"{index:02d}/{len(results):02d}    {color}[{label}]{RESET}  {current['case_id']:<28}  {current['detail']}")
    print("────────────────────────────────────────────────────────────────────────")
    summary = "测试通过" if code == 0 else ("测试阻塞" if code == 2 else "测试失败")
    print(f"{summary} · {sum(item['status'] == 'PASS' for item in results)}/{len(results)} 通过 · 退出码 {code}")
    if args.json:
        print(json.dumps({
            "api": "uiautoma.web.WebBrowser.find_all_by_css",
            "target_url": args.target_url, "mode": args.mode,
            "status": "PASS" if code == 0 else ("BLOCKED" if code == 2 else "FAIL"),
            "exit_code": code, "results": results,
        }, ensure_ascii=False, indent=2))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
