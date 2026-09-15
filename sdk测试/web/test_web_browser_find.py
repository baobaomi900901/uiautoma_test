"""WebBrowser.find() 页面对象 API 专项验收。

前置（元素库与靶场）：
- 元素库：`D:\\code\\元素库\\260902_web元素`（Schema2，70 个 web 元素）
- 靶场：`https://baobaomi900901.github.io/xpath/#/iframe-shadow-form`
  （库中 `web靶场_表单测试_*` 元素对应的页面，元素位于该页的 iframe 内）
- 用法：元素库**复制到本工作区 `.pytest_tmp/<run_id>/` 后再打开**，结束时删除，
  绝不写入用户原件。

源码要点（本次实测核对）：
- `_saved_query`：`str` 名称 → `{"type":"saved","name":...}`；`Selector` 必须是 web 框架
  → `{"type":"saved","element_id":...}`；空名称 → `InvalidParamsError`；
- `find` 取 `many=False` 结果的首项，因此**唯一命中**由 Runtime 保证，
  未命中 / 多个命中分别抛 `ElementNotFoundError` / `AmbiguousElementError`；
- 两种未命中的报错语义不同：**库里没有该名称**（立即，"未找到选择器"）
  与**名称存在但当前页面匹配不到**（等满 timeout，"未找到匹配元素"）。

退出码：0 = 全部 PASS；1 = 存在 FAIL；2 = 无非 FAIL 但存在 BLOCKED。
"""
from __future__ import annotations

import argparse
import inspect
import json
import shutil
import tempfile
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
ELEMENT_NAME = "web靶场_表单测试_ant_输入框"
SECOND_ELEMENT_NAME = "web靶场_表单测试_ant_数字输入框"
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
    method = getattr(WebBrowser, "find", None)
    sig = inspect.signature(method) if callable(method) else None
    if sig is None:
        return result("api_contract", "FAIL", "WebBrowser.find 不存在")
    parameters = list(sig.parameters.values())
    names = tuple(sig.parameters)
    annotation = str(sig.return_annotation)
    ok = (
        names == ("self", "selector", "timeout")
        and parameters[1].kind is inspect.Parameter.POSITIONAL_OR_KEYWORD
        and parameters[1].default is inspect.Parameter.empty
        and parameters[2].kind is inspect.Parameter.KEYWORD_ONLY
        and parameters[2].default == 20
        and annotation == "WebElement"
    )
    detail = (
        "selector 必填，timeout 仅限关键字且默认 20，返回注解 WebElement"
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


def prepare_library_copy(source: Path, owner: Path):
    """复制元素库到本工作区的临时目录（不改原件），返回 (副本路径, 元素数)。"""
    shutil.copytree(source, owner)
    return owner


def run(args):
    results = [check_contract()]
    if results[-1]["status"] != "PASS" or args.contract_only:
        return results, 0 if results[-1]["status"] == "PASS" else 1

    run_id = uuid.uuid4().hex
    copy_dir = LIB_TMP_ROOT / run_id
    package = None
    page = None
    try:
        # 场景准备 1：复制并打开元素库
        try:
            if not args.library.is_dir():
                results.append(result("library_prepare", "BLOCKED", f"元素库不存在: {args.library}"))
                return results, 2
            prepare_library_copy(args.library, copy_dir)
            package = uiautoma.open(str(copy_dir), timeout=20, connect_timeout=20)
            web_items = package.elements.list(kind="web")
            ok = package.web_count == len(web_items) and package.web_count > 0
            results.append(result(
                "library_prepare",
                "PASS" if ok else "FAIL",
                f"已打开元素库副本：web 元素 {package.web_count} 个（与列举一致）" if ok else
                f"元素数与列举不一致: web_count={package.web_count}, listed={len(web_items)}",
                web_count=package.web_count, listed=len(web_items),
                library_copy=str(copy_dir),
            ))
            if not ok:
                return results, 1
        except Exception as exc:  # noqa: BLE001
            results.append(result("library_prepare", "BLOCKED", error_detail("无法准备元素库", exc)))
            return results, 2

        # 场景准备 2：打开正确靶场页
        try:
            page = web.create(args.target_url, mode=args.mode, load_timeout=args.load_timeout)
            page_id = page.id
            current = page.get_url()
            results.append(result(
                "page_prepare",
                "PASS" if isinstance(page, WebBrowser) and same_url(current, args.target_url) else "FAIL",
                "已打开元素所属靶场页" if same_url(current, args.target_url) else f"URL 不符: {current!r}",
                url=current, page_id=page_id,
            ))
        except Exception as exc:  # noqa: BLE001
            results.append(result("page_prepare", "BLOCKED", error_detail("无法打开靶场页", exc)))
            return results, 2

        # 目标用例 1：按库中名称定位
        first_id = ""
        first_tag = ""
        try:
            element = page.find(ELEMENT_NAME, timeout=args.timeout)
            first_id = str(element.id or "")
            first_tag = str(element.name or "")
            ok = first_id.startswith("rt:web:") and bool(first_tag)
            results.append(result(
                "find_by_name",
                "PASS" if ok else "FAIL",
                f"按库中名称命中元素（标签 {first_tag}，运行时 id 前缀 rt:web:）" if ok else
                f"返回元素异常: id={first_id!r}, name={first_tag!r}",
                element_id=first_id, tag=first_tag,
            ))
        except Exception as exc:  # noqa: BLE001
            results.append(result("find_by_name", "FAIL", error_detail("按名称定位失败", exc)))

        # 目标用例 2：Selector 对象入参
        try:
            selector = package.selector(ELEMENT_NAME)
            element = page.find(selector, timeout=args.timeout)
            ok = str(element.name or "") == first_tag and str(element.id or "").startswith("rt:web:")
            results.append(result(
                "find_by_selector",
                "PASS" if ok else "FAIL",
                f"以 package.selector() 传入同样命中（标签 {element.name}）" if ok else
                f"Selector 入参结果不符: name={element.name!r}, id={element.id!r}",
                selector_framework=selector.framework(), selector_id=selector.id(),
            ))
        except Exception as exc:  # noqa: BLE001
            results.append(result("find_by_selector", "FAIL", error_detail("Selector 入参定位失败", exc)))

        # 目标用例 3：重复定位的一致性（注意 element_id 每次都会变，故按标签与可用性判定）
        try:
            again = page.find(ELEMENT_NAME, timeout=args.timeout)
            same_tag = str(again.name or "") == first_tag
            id_changed = str(again.id or "") != first_id
            results.append(result(
                "repeated_find_stable",
                "PASS" if same_tag else "FAIL",
                f"重复定位命中同一目标（标签一致 {first_tag}）"
                + ("；注意 element_id 每次都会重新生成" if id_changed else "") if same_tag else
                f"重复定位标签不一致: {again.name!r} != {first_tag!r}",
                tag_again=str(again.name or ""), element_id_changed=id_changed,
            ))
        except Exception as exc:  # noqa: BLE001
            results.append(result("repeated_find_stable", "FAIL", error_detail("重复定位失败", exc)))

        # 目标用例 4：find_all 返回列表且包含同一目标
        try:
            items = page.find_all(ELEMENT_NAME, timeout=args.timeout)
            tags = [str(item.name or "") for item in items]
            ok = isinstance(items, list) and len(items) >= 1 and first_tag in tags
            results.append(result(
                "find_all_contains_target",
                "PASS" if ok else "FAIL",
                f"find_all 返回 {len(items)} 个元素且包含目标（标签 {first_tag}）" if ok else
                f"find_all 结果不符: count={len(items)}, tags={tags[:5]}",
                count=len(items), tags=tags[:5],
            ))
        except Exception as exc:  # noqa: BLE001
            results.append(result("find_all_contains_target", "FAIL", error_detail("find_all 调用失败", exc)))

        # 目标用例 5：另一元素（覆盖库内第二个名称）
        try:
            element = page.find(SECOND_ELEMENT_NAME, timeout=args.timeout)
            ok = bool(str(element.name or "")) and str(element.id or "").startswith("rt:web:")
            results.append(result(
                "find_second_element",
                "PASS" if ok else "FAIL",
                f"库中第二个元素同样可定位（标签 {element.name}）" if ok else
                f"结果不符: name={element.name!r}, id={element.id!r}",
                tag=str(element.name or ""),
            ))
        except Exception as exc:  # noqa: BLE001
            results.append(result("find_second_element", "FAIL", error_detail("第二个元素定位失败", exc)))

        # 目标用例 6：timeout=0（只查一次）在元素存在时仍可命中
        try:
            element = page.find(ELEMENT_NAME, timeout=0)
            ok = bool(str(element.name or ""))
            results.append(result(
                "timeout_zero_present",
                "PASS" if ok else "FAIL",
                "timeout=0 且元素存在时仍命中" if ok else f"结果不符: {element!r}",
                tag=str(element.name or ""),
            ))
        except Exception as exc:  # noqa: BLE001
            results.append(result("timeout_zero_present", "FAIL", error_detail("timeout=0 调用失败", exc)))

        # 目标用例 7：库中不存在的名称 → 立即拒绝
        results.append(expect_raises(
            lambda: page.find("__uiautoma_not_exist__", timeout=args.timeout),
            ElementNotFoundError, "unknown_name_rejected",
            message_contains="未找到选择器", max_elapsed=1.0,
        ))

        # 目标用例 8：名称存在但当前页面匹配不到 → 等满 timeout 后拒绝
        if _switch_to_wrong_page(page, args):
            results.append(expect_raises(
                lambda: page.find(ELEMENT_NAME, timeout=3),
                ElementNotFoundError, "page_mismatch_rejected",
                message_contains="未找到匹配元素", min_elapsed=2.5,
            ))
        else:
            results.append(result("page_mismatch_rejected", "BLOCKED", "无法切换到不匹配的页面"))

        # 参数校验
        results.append(expect_raises(lambda: page.find(""), InvalidParamsError, "empty_name"))
        results.append(expect_raises(lambda: page.find("   "), InvalidParamsError, "blank_name"))
        results.append(expect_raises(
            lambda: page.find(ELEMENT_NAME, timeout=-2), InvalidParamsError, "invalid_timeout",
        ))
        results.append(expect_raises(
            lambda: page.find(ELEMENT_NAME, timeout="bad"), InvalidParamsError, "invalid_timeout_type",
        ))
        results.append(expect_raises(lambda: page.find(), TypeError, "missing_selector"))
        results.append(expect_raises(lambda: page.find(ELEMENT_NAME, 1), TypeError, "positional_timeout"))

        # 目标用例 9：未打开 Package 时拒绝
        try:
            package.close()
        except Exception:  # noqa: BLE001
            pass
        results.append(expect_raises(
            lambda: page.find(ELEMENT_NAME, timeout=1), NoCurrentPackageError, "no_package_rejected",
            message_contains="Package",
        ))
        package = None
    except Exception as exc:  # noqa: BLE001
        results.append(result("scenario", "FAIL", error_detail("find 场景执行失败", exc)))
    finally:
        if page is not None:
            try:
                page.close(ignore_beforeunload=True)
            except Exception:  # noqa: BLE001
                pass
        if package is not None:
            try:
                package.close()
            except Exception:  # noqa: BLE001
                pass
        shutil.rmtree(copy_dir, ignore_errors=True)
        leftover = copy_dir.exists()
        results.append(result(
            "cleanup",
            "PASS" if not leftover else "FAIL",
            "已关闭页面与 Package，并删除元素库副本" if not leftover else "元素库副本未能删除",
            library_copy_removed=not leftover,
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
    parser = argparse.ArgumentParser(description="WebBrowser.find() 页面对象 API 验收")
    parser.add_argument("--target-url", default=DEFAULT_URL)
    parser.add_argument("--mode", choices=("chrome", "edge"), default="chrome")
    parser.add_argument("--load-timeout", type=float, default=20)
    parser.add_argument("--timeout", type=float, default=8, help="find 的 timeout，默认 8")
    parser.add_argument("--library", type=Path, default=DEFAULT_LIBRARY, help="元素库目录")
    parser.add_argument("--contract-only", action="store_true")
    parser.add_argument("--json", action="store_true", help="在表格后额外输出 JSON 报告（用于归档验收产物）")
    args = parser.parse_args(argv)
    if args.load_timeout <= 0:
        parser.error("--load-timeout 必须大于 0")

    results, code = run(args)
    print("UIAutoma Web API 测试")
    print("API     : uiautoma.web.WebBrowser.find")
    print(f"页面    : {args.target_url}")
    print(f"元素库  : {args.library}")
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
            "api": "uiautoma.web.WebBrowser.find",
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
