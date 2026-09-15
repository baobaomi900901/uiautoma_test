"""WebBrowser.is_element_displayed() 页面对象 API 专项验收。

靶场：**维护者的官方靶场** `https://baobaomi900901.github.io/xpath/#/iframe-shadow-form`
（元素库 `260902_web元素` 中 `web靶场_表单测试_*` 元素所属页面；测试侧不自建页面）。

期望值来源：**活推导** —— 脚本先遍历元素库，用 `find_all(name, timeout=0)` 现场把元素分成
「当前页唯一命中 / 多命中 / 本页不存在」三类，再据此断言；**不写死任何元素名或数量**。

源码事实：`is_element_displayed(selector)` 就是 `bool(self.find_all(selector, timeout=0))`，
因此它的口径完全继承 `find_all`：
- 本页有匹配（唯一或多命中）→ `True`（多命中**不会**抛 `AmbiguousElementError`）；
- 本页无匹配 → `False`（内部 `timeout=0`，**不等待**，立即返回）；
- **库中没有该名称 → 抛 `ElementNotFoundError`**（不是返回 `False`）。

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
from uiautoma import (
    ElementNotFoundError,
    InvalidParamsError,
    NoCurrentPackageError,
    web,
)
from uiautoma.web import WebBrowser

__test__ = False

DEFAULT_URL = "https://baobaomi900901.github.io/xpath/#/iframe-shadow-form"
WRONG_URL = "https://baobaomi900901.github.io/xpath/#/form-controls"
DEFAULT_LIBRARY = Path(r"D:\code\元素库\260902_web元素")
LIB_TMP_ROOT = Path(__file__).resolve().parents[1] / ".pytest_tmp"
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
    method = getattr(WebBrowser, "is_element_displayed", None)
    sig = inspect.signature(method) if callable(method) else None
    if sig is None:
        return result("api_contract", "FAIL", "WebBrowser.is_element_displayed 不存在")
    parameters = list(sig.parameters.values())
    names = tuple(sig.parameters)
    ok = (
        names == ("self", "selector")
        and parameters[1].kind is inspect.Parameter.POSITIONAL_OR_KEYWORD
        and parameters[1].default is inspect.Parameter.empty
        and str(sig.return_annotation) == "bool"
    )
    detail = (
        "selector 必填、无 timeout 等额外参数，返回注解 bool"
        if ok else f"公开签名不符合合同: {sig}"
    )
    return result("api_contract", "PASS" if ok else "FAIL", detail,
                  parameter_names=list(names), return_annotation=str(sig.return_annotation))


def exception_name(exc: BaseException) -> str:
    return type(exc).__name__


def error_detail(prefix: str, exc: BaseException) -> str:
    trace_info = str(getattr(exc, "trace_info", "") or "")
    return f"{prefix}: {exception_name(exc)}: {exc}" + (f" [trace={trace_info}]" if trace_info else "")


def expect_raises(call, expected_type, label: str, message_contains: str = "",
                  max_elapsed: float | None = None):
    started = time.perf_counter()
    try:
        call()
    except expected_type as exc:
        elapsed = round(time.perf_counter() - started, 3)
        text = str(exc)
        if message_contains and message_contains not in text:
            return result(label, "FAIL", f"{exception_name(exc)} 消息不含 {message_contains!r}：{text}", elapsed_s=elapsed)
        if max_elapsed is not None and elapsed > max_elapsed:
            return result(label, "FAIL", f"耗时过长：{elapsed}s > {max_elapsed}s", elapsed_s=elapsed)
        return result(label, "PASS", f"{exception_name(exc)} 正确拒绝（{elapsed}s）：{text}", elapsed_s=elapsed)
    except Exception as exc:  # noqa: BLE001
        return result(label, "FAIL", f"拒绝类型错误，应为 {expected_type.__name__}: {exception_name(exc)}: {exc}")
    return result(label, "FAIL", "调用未被拒绝")


def bool_case(page: WebBrowser, case_id: str, label: str, call, expected: bool,
              max_elapsed: float | None = None, **extra):
    started = time.perf_counter()
    try:
        value = call()
    except Exception as exc:  # noqa: BLE001
        return result(case_id, "FAIL", error_detail(f"{label} 不应抛异常", exc))
    elapsed = round(time.perf_counter() - started, 3)
    if not isinstance(value, bool):
        return result(case_id, "FAIL", f"{label} 应返回 bool，实际 {type(value).__name__}", elapsed_s=elapsed)
    if value is not expected:
        return result(case_id, "FAIL", f"{label} 期望 {expected}，实际 {value}", elapsed_s=elapsed, **extra)
    if max_elapsed is not None and elapsed > max_elapsed:
        return result(case_id, "FAIL", f"{label} 耗时过长：{elapsed}s > {max_elapsed}s", elapsed_s=elapsed, **extra)
    return result(case_id, "PASS", f"{label} 返回 {str(value)}（{elapsed}s）", elapsed_s=elapsed, **extra)


def run(args):
    results = [check_contract()]
    if results[-1]["status"] != "PASS" or args.contract_only:
        return results, 0 if results[-1]["status"] == "PASS" else 1

    run_id = uuid.uuid4().hex
    copy_dir = LIB_TMP_ROOT / run_id
    absent_name = f"__uiautomata_absent_{run_id[:8]}__"
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
                "已打开元素所属靶场页" if ok else f"URL 不符: {current!r}", url=current))
            if not ok:
                return results, 1
        except Exception as exc:  # noqa: BLE001
            results.append(result("page_prepare", "BLOCKED", error_detail("无法打开靶场页", exc)))
            return results, 2

        # 活推导：遍历元素库，按 find_all(timeout=0) 现场分类
        try:
            names = [str(item.name) for item in package.elements.list(kind="web")]
            unique_name = multi_name = off_page_name = ""
            multi_count = 0
            counted = {"unique": 0, "multi": 0, "off_page": 0}
            for name in names:
                try:
                    count = len(page.find_all(name, timeout=0))
                except Exception:  # noqa: BLE001
                    continue
                if count == 1:
                    counted["unique"] += 1
                    unique_name = unique_name or name
                elif count > 1:
                    counted["multi"] += 1
                    if not multi_name:
                        multi_name, multi_count = name, count
                else:
                    counted["off_page"] += 1
                    off_page_name = off_page_name or name
            ok = bool(unique_name and multi_name and off_page_name)
            results.append(result(
                "live_classification",
                "PASS" if ok else "FAIL",
                f"库中 {len(names)} 个元素在本页分类：唯一 {counted['unique']}、多命中 {counted['multi']}、"
                f"本页不存在 {counted['off_page']}" if ok else
                f"无法从库中取得三类样本: {counted}",
                library_size=len(names), **counted))
            if not ok:
                return results, 1
        except Exception as exc:  # noqa: BLE001
            results.append(result("live_classification", "BLOCKED", error_detail("无法分类元素库", exc)))
            return results, 2

        # 目标用例 1：本页唯一命中的元素 → True（并与 find_all 数量交叉核对）
        results.append(bool_case(
            page, "displayed_true_unique", "本页唯一命中元素",
            lambda: page.is_element_displayed(unique_name), True,
            element_name=unique_name))

        # 目标用例 2：多命中元素仍为 True（不像 find 那样抛歧义）
        results.append(bool_case(
            page, "displayed_true_multi", f"多命中元素（{multi_count} 个）仍为 True",
            lambda: page.is_element_displayed(multi_name), True,
            element_name=multi_name, matches=multi_count))

        # 目标用例 3：以 Selector 传入
        results.append(bool_case(
            page, "displayed_true_selector", "以 package.selector() 传入唯一元素",
            lambda: page.is_element_displayed(package.selector(unique_name)), True,
            element_name=unique_name))

        # 目标用例 4：本页不存在（库中有）→ False，且不等待
        results.append(bool_case(
            page, "not_on_page_false", "库中有但本页不存在的元素",
            lambda: page.is_element_displayed(off_page_name), False,
            max_elapsed=2.0, element_name=off_page_name))

        # 目标用例 5：页面不对 → False
        try:
            page.navigate(WRONG_URL, load_timeout=args.load_timeout)
            time.sleep(0.5)
            switched = True
        except Exception as exc:  # noqa: BLE001
            switched = False
            results.append(result("wrong_page_false", "BLOCKED", error_detail("无法切换到其它靶场页", exc)))
        if switched:
            results.append(bool_case(
                page, "wrong_page_false", "元素所属页正确但当前页不对",
                lambda: page.is_element_displayed(unique_name), False,
                max_elapsed=2.0, element_name=unique_name))

        # 目标用例 6：库中没有该名称 → 抛 ElementNotFoundError（不是 False）
        results.append(expect_raises(
            lambda: page.is_element_displayed(absent_name),
            ElementNotFoundError, "library_miss_raises",
            message_contains="未找到选择器", max_elapsed=1.0))

        # 参数校验
        results.append(expect_raises(lambda: page.is_element_displayed(""), InvalidParamsError, "empty_name"))
        results.append(expect_raises(lambda: page.is_element_displayed("   "), InvalidParamsError, "blank_name"))
        results.append(expect_raises(lambda: page.is_element_displayed(123), InvalidParamsError, "non_str_name"))
        results.append(expect_raises(lambda: page.is_element_displayed(None), InvalidParamsError, "none_name"))
        results.append(expect_raises(
            lambda: page.is_element_displayed(unique_name, 1), TypeError, "extra_positional"))
        results.append(expect_raises(
            lambda: page.is_element_displayed(unique_name, timeout=1), TypeError, "no_timeout_param"))

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
            lambda: closed_page.is_element_displayed(unique_name), NoCurrentPackageError,
            "no_package_rejected", message_contains="Package"))
    except Exception as exc:  # noqa: BLE001
        results.append(result("scenario", "FAIL", error_detail("is_element_displayed 场景执行失败", exc)))
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
    parser = argparse.ArgumentParser(description="WebBrowser.is_element_displayed() 页面对象 API 验收")
    parser.add_argument("--target-url", default=DEFAULT_URL, help="元素所属靶场页")
    parser.add_argument("--mode", choices=("chrome", "edge"), default="chrome")
    parser.add_argument("--load-timeout", type=float, default=20)
    parser.add_argument("--library", type=Path, default=DEFAULT_LIBRARY, help="元素库目录")
    parser.add_argument("--contract-only", action="store_true")
    parser.add_argument("--json", action="store_true", help="在表格后额外输出 JSON 报告（用于归档验收产物）")
    args = parser.parse_args(argv)
    if args.load_timeout <= 0:
        parser.error("--load-timeout 必须大于 0")

    results, code = run(args)
    print("UIAutoma Web API 测试")
    print("API     : uiautoma.web.WebBrowser.is_element_displayed")
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
            "api": "uiautoma.web.WebBrowser.is_element_displayed",
            "target_url": args.target_url, "mode": args.mode,
            "status": "PASS" if code == 0 else ("BLOCKED" if code == 2 else "FAIL"),
            "exit_code": code, "results": results,
        }, ensure_ascii=False, indent=2))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
