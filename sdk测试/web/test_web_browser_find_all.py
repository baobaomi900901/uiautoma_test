"""WebBrowser.find_all() 页面对象 API 专项验收。

前置（元素库与靶场）：
- 元素库：`D:\\code\\元素库\\260902_web元素`（Schema2，70 个 web 元素）
- 靶场：`https://baobaomi900901.github.io/xpath/#/iframe-shadow-form`
- 用法：元素库**复制到本工作区 `.pytest_tmp/<run_id>/` 后再打开**，结束时删除，不写原件。

与 `find()` 的关键差异（本次实测核对）：
- `find` 唯一命中，未命中抛 `ElementNotFoundError`；
- `find_all` 返回 `list`，**页面匹配不到时等满 timeout 后返回空列表 `[]`，不抛异常**；
- 两者在「库中没有该名称」时都会**立即**抛 `ElementNotFoundError`（"未找到选择器"）。

本库中带 `_相似元素` 后缀的元素会命中多个节点（例如
`web靶场_表单测试_ant_radio_label_相似元素` 命中 男/女/其他 三个），因此可覆盖真正的多命中返回。
同一个元素改用 `find()` 定位会抛 `AmbiguousElementError`（已并入 `find.md` 的验收）。

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
from uiautoma import ElementNotFoundError, InvalidParamsError, NoCurrentPackageError, web
from uiautoma.web import WebBrowser

__test__ = False

DEFAULT_URL = "https://baobaomi900901.github.io/xpath/#/iframe-shadow-form"
WRONG_URL = "https://baobaomi900901.github.io/xpath/#/form-controls"
DEFAULT_LIBRARY = Path(r"D:\code\元素库\260902_web元素")
SINGLE_NAME = "web靶场_表单测试_ant_输入框"
MULTI_NAME = "web靶场_表单测试_ant_radio_label_相似元素"
MULTI_EXPECTED_MIN = 3
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
    method = getattr(WebBrowser, "find_all", None)
    sig = inspect.signature(method) if callable(method) else None
    if sig is None:
        return result("api_contract", "FAIL", "WebBrowser.find_all 不存在")
    parameters = list(sig.parameters.values())
    names = tuple(sig.parameters)
    annotation = str(sig.return_annotation)
    ok = (
        names == ("self", "selector", "timeout")
        and parameters[1].kind is inspect.Parameter.POSITIONAL_OR_KEYWORD
        and parameters[1].default is inspect.Parameter.empty
        and parameters[2].kind is inspect.Parameter.KEYWORD_ONLY
        and parameters[2].default == 20
        and annotation == "list[WebElement]"
    )
    detail = (
        "selector 必填，timeout 仅限关键字且默认 20，返回注解 list[WebElement]"
        if ok else f"公开签名不符合合同: {sig}"
    )
    return result("api_contract", "PASS" if ok else "FAIL", detail, return_annotation=annotation)


def exception_name(exc: BaseException) -> str:
    return type(exc).__name__


def error_detail(prefix: str, exc: BaseException) -> str:
    trace_info = str(getattr(exc, "trace_info", "") or "")
    suffix = f" [trace={trace_info}]" if trace_info else ""
    return f"{prefix}: {exception_name(exc)}: {exc}{suffix}"


def expect_raises(call, expected_type, label: str, message_contains: str = "",
                  min_elapsed: float | None = None, max_elapsed: float | None = None):
    started = time.perf_counter()
    try:
        call()
    except expected_type as exc:
        elapsed = round(time.perf_counter() - started, 3)
        text = str(exc)
        if message_contains and message_contains not in text:
            return result(
                label, "FAIL",
                f"{exception_name(exc)} 类型正确但消息不含 {message_contains!r}：{text}",
                elapsed_s=elapsed,
            )
        if min_elapsed is not None and elapsed < min_elapsed:
            return result(
                label, "FAIL",
                f"耗时过短：{elapsed}s < {min_elapsed}s（可能未真正等待）",
                elapsed_s=elapsed,
            )
        if max_elapsed is not None and elapsed > max_elapsed:
            return result(
                label, "FAIL",
                f"耗时过长：{elapsed}s > {max_elapsed}s（应当立即返回）",
                elapsed_s=elapsed,
            )
        return result(
            label, "PASS",
            f"{exception_name(exc)} 正确拒绝（{elapsed}s）：{text}",
            elapsed_s=elapsed,
        )
    except Exception as exc:  # noqa: BLE001
        return result(label, "FAIL", f"拒绝类型错误，应为 {expected_type.__name__}: {exception_name(exc)}: {exc}")
    return result(label, "FAIL", "调用未被拒绝")


def empty_list_case(page: WebBrowser, case_id: str, label: str, call,
                    min_elapsed: float | None = None, max_elapsed: float | None = None):
    """断言返回空列表（而不是抛异常），并核对耗时。"""
    started = time.perf_counter()
    try:
        items = call()
    except Exception as exc:  # noqa: BLE001
        return result(case_id, "FAIL", error_detail(f"{label} 不应抛异常", exc))
    elapsed = round(time.perf_counter() - started, 3)
    if not isinstance(items, list) or items:
        return result(
            case_id, "FAIL",
            f"{label} 应为空列表，实际 {type(items).__name__} 长度 "
            f"{len(items) if isinstance(items, list) else '?'}",
            elapsed_s=elapsed,
        )
    if min_elapsed is not None and elapsed < min_elapsed:
        return result(case_id, "FAIL", f"{label} 耗时过短：{elapsed}s < {min_elapsed}s", elapsed_s=elapsed)
    if max_elapsed is not None and elapsed > max_elapsed:
        return result(case_id, "FAIL", f"{label} 耗时过长：{elapsed}s > {max_elapsed}s", elapsed_s=elapsed)
    return result(
        case_id, "PASS",
        f"{label} 返回空列表 []（耗时 {elapsed}s，未抛异常）",
        elapsed_s=elapsed,
    )


def run(args):
    results = [check_contract()]
    if results[-1]["status"] != "PASS" or args.contract_only:
        return results, 0 if results[-1]["status"] == "PASS" else 1

    run_id = uuid.uuid4().hex
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
            listed = package.elements.list(kind="web")
            ok = package.web_count == len(listed) and package.web_count > 0
            results.append(result(
                "library_prepare",
                "PASS" if ok else "FAIL",
                f"已打开元素库副本：web 元素 {package.web_count} 个（与列举一致）" if ok else
                f"元素数与列举不一致: web_count={package.web_count}, listed={len(listed)}",
                web_count=package.web_count, listed=len(listed),
            ))
            if not ok:
                return results, 1
        except Exception as exc:  # noqa: BLE001
            results.append(result("library_prepare", "BLOCKED", error_detail("无法准备元素库", exc)))
            return results, 2

        try:
            page = web.create(args.target_url, mode=args.mode, load_timeout=args.load_timeout)
            page_id = page.id
            current = page.get_url()
            results.append(result(
                "page_prepare",
                "PASS" if isinstance(page, WebBrowser) and same_url(current, args.target_url) else "FAIL",
                "已打开元素所属靶场页" if same_url(current, args.target_url) else f"URL 不符: {current!r}",
                url=current,
            ))
        except Exception as exc:  # noqa: BLE001
            results.append(result("page_prepare", "BLOCKED", error_detail("无法打开靶场页", exc)))
            return results, 2

        # 目标用例 1：唯一命中时返回长度为 1 的列表
        try:
            items = page.find_all(SINGLE_NAME, timeout=args.timeout)
            ok = isinstance(items, list) and len(items) == 1 and bool(str(items[0].name or ""))
            results.append(result(
                "single_match_list_of_one",
                "PASS" if ok else "FAIL",
                f"唯一命中返回 list[1]（元素标签 {items[0].name}）" if ok else
                f"结果不符: type={type(items).__name__}, len={len(items) if isinstance(items, list) else '?'}",
                count=len(items) if isinstance(items, list) else -1,
                tags=[str(i.name or "") for i in items] if isinstance(items, list) else [],
            ))
        except Exception as exc:  # noqa: BLE001
            results.append(result("single_match_list_of_one", "FAIL", error_detail("唯一命中用例失败", exc)))

        # 目标用例 2：多命中时返回全部匹配
        try:
            items = page.find_all(MULTI_NAME, timeout=args.timeout)
            labels = [str(i.name or "") for i in items]
            ok = isinstance(items, list) and len(items) >= MULTI_EXPECTED_MIN
            results.append(result(
                "multi_match_returns_all",
                "PASS" if ok else "FAIL",
                f"多命中元素返回 {len(items)} 个（{labels}）" if ok else
                f"多命中数量不足: len={len(items) if isinstance(items, list) else '?'}, labels={labels}",
                count=len(items) if isinstance(items, list) else -1, labels=labels,
            ))
        except Exception as exc:  # noqa: BLE001
            results.append(result("multi_match_returns_all", "FAIL", error_detail("多命中用例失败", exc)))

        # 目标用例 3：Selector 入参
        try:
            items = page.find_all(package.selector(SINGLE_NAME), timeout=args.timeout)
            ok = isinstance(items, list) and len(items) == 1
            results.append(result(
                "selector_input",
                "PASS" if ok else "FAIL",
                "以 package.selector() 传入返回 list[1]" if ok else f"结果不符: len={len(items)}",
                count=len(items),
            ))
        except Exception as exc:  # noqa: BLE001
            results.append(result("selector_input", "FAIL", error_detail("Selector 入参失败", exc)))

        # 目标用例 4：timeout=0 且元素存在
        try:
            items = page.find_all(SINGLE_NAME, timeout=0)
            ok = isinstance(items, list) and len(items) == 1
            results.append(result(
                "timeout_zero_present",
                "PASS" if ok else "FAIL",
                "timeout=0 且元素存在时仍返回 list[1]" if ok else f"结果不符: len={len(items)}",
                count=len(items),
            ))
        except Exception as exc:  # noqa: BLE001
            results.append(result("timeout_zero_present", "FAIL", error_detail("timeout=0 调用失败", exc)))

        # 目标用例 5：页面不匹配 → 等满 timeout 后返回空列表（核心差异）
        if _switch_to_wrong_page(page, args):
            results.append(empty_list_case(
                page, "page_mismatch_empty_list", "名称正确但页面不匹配（timeout=3）",
                lambda: page.find_all(SINGLE_NAME, timeout=3), min_elapsed=2.5,
            ))
            results.append(empty_list_case(
                page, "page_mismatch_timeout_zero_fast", "同样的不匹配但 timeout=0",
                lambda: page.find_all(SINGLE_NAME, timeout=0), max_elapsed=1.0,
            ))
        else:
            results.append(result("page_mismatch_empty_list", "BLOCKED", "无法切换到不匹配的页面"))

        # 目标用例 6：库中不存在的名称 → 立即抛异常（与页面不匹配区分）
        results.append(expect_raises(
            lambda: page.find_all("__uiautoma_not_exist__", timeout=args.timeout),
            ElementNotFoundError, "unknown_name_raises",
            message_contains="未找到选择器", max_elapsed=1.0,
        ))

        # 参数校验
        results.append(expect_raises(lambda: page.find_all(""), InvalidParamsError, "empty_name"))
        results.append(expect_raises(lambda: page.find_all("   "), InvalidParamsError, "blank_name"))
        results.append(expect_raises(
            lambda: page.find_all(SINGLE_NAME, timeout=-2), InvalidParamsError, "invalid_timeout",
        ))
        results.append(expect_raises(
            lambda: page.find_all(SINGLE_NAME, timeout="bad"), InvalidParamsError, "invalid_timeout_type",
        ))
        results.append(expect_raises(lambda: page.find_all(), TypeError, "missing_selector"))
        results.append(expect_raises(lambda: page.find_all(SINGLE_NAME, 1), TypeError, "positional_timeout"))

        # 目标用例 7：未打开 Package
        # 目标用例：关闭页面并复核
        # 顺序关键：**必须先关页面再关 Package**。`Package.close()` 会释放 Package 会话
        # 及其「顶级便利连接」，而页面对象持有同一个 client 实例，之后再调 page.close()
        # 只会得到 HostUnavailableError 并静默泄漏标签页。
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
                "page_close_verified",
                "PASS" if ok else "FAIL",
                "页面已关闭，且 web.get_all() 复核无残留" if ok else
                f"关闭后仍有残留: return={returned!r}, leftover={len(leftover)}",
                returned=repr(returned), leftover_pages=len(leftover),
            ))
        page = None

        # 目标用例：关闭 Package
        try:
            package.close()
            results.append(result("package_close_verified", "PASS", "Package 已关闭"))
        except Exception as exc:  # noqa: BLE001
            results.append(result("package_close_verified", "FAIL", error_detail("Package 关闭失败", exc)))
        package = None

        # 目标用例：未打开 Package 时拒绝
        # 判定发生在 SDK 侧（get_package()），不需要连接，因此可在已关闭的页面对象上验证。
        results.append(expect_raises(
            lambda: closed_page.find_all(SINGLE_NAME, timeout=1), NoCurrentPackageError,
            "no_package_rejected", message_contains="Package",
        ))
    except Exception as exc:  # noqa: BLE001
        results.append(result("scenario", "FAIL", error_detail("find_all 场景执行失败", exc)))
    finally:
        # 兜底：页面与 Package 可能因中途异常仍开着；顺序仍是先页面后 Package。
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
            "cleanup",
            "PASS" if cleaned else "FAIL",
            "已关闭页面（get_all 复核无残留）、关闭 Package、删除元素库副本" if cleaned else
            f"清理不完整: 残留页面={len(leftover)}, close 错误={page_close_error or '无'}, "
            f"副本残留={copy_dir.exists()}",
            leftover_pages=len(leftover),
            page_close_error=page_close_error,
            library_copy_removed=not copy_dir.exists(),
        ))

    statuses = {item["status"] for item in results}
    code = 1 if "FAIL" in statuses else (2 if "BLOCKED" in statuses else 0)
    return results, code


def _switch_to_wrong_page(page: WebBrowser, args) -> bool:
    try:
        page.navigate(WRONG_URL, load_timeout=args.load_timeout)
        time.sleep(0.5)
        return True
    except Exception:  # noqa: BLE001
        return False


def main(argv=None):
    parser = argparse.ArgumentParser(description="WebBrowser.find_all() 页面对象 API 验收")
    parser.add_argument("--target-url", default=DEFAULT_URL)
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
    print("API     : uiautoma.web.WebBrowser.find_all")
    print(f"页面    : {args.target_url}")
    print(f"元素库  : {args.library}")
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
            "api": "uiautoma.web.WebBrowser.find_all",
            "target_url": args.target_url,
            "mode": args.mode,
            "library": str(args.library),
            "status": "PASS" if code == 0 else ("BLOCKED" if code == 2 else "FAIL"),
            "exit_code": code,
            "results": results,
        }, ensure_ascii=False, indent=2))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
