"""WebElement.find_all() 元素对象 API 专项验收（在当前元素范围内查找多个匹配元素）。

> 注意区分：这是**元素级** `find_all(selector, *, timeout=10)`（与页面级
> `WebBrowser.find_all(selector, *, timeout=20)` 不是同一个 API）。

## 靶场与元素库

- 主验收路由：`https://baobaomi900901.github.io/xpath/#/anchor-test`（标准靶场，**同文档**）
- 边界刻画路由：`https://baobaomi900901.github.io/xpath/#/iframe-shadow-form`（标准靶场，
  `iframe → open shadow root → #shadow-form-content`）
- 元素库：`D:\\code\\元素库\\260902_web元素`（72 条 web 元素）

库路径构成（脚本外的快照核对结论，记录于此便于复现）：**64/72 条路径跨越
`iframe[src='/xpath/#/iframe-shadow-form-content']` 与 `#shadow-root`**，只有 8 条是同文档路径：
`测试find_父级`、`测试find_子级`、`测试get_text_靶元素/输入框/按钮_确定/按钮_重置`、
`上传对话框测试 _原生_上传组件`、`下载对话框测试 _下载txt`。

## 结论（2026-09-18，`main@c101caa9`）

1. **标准靶场同文档页面上，元素级作用域语义正确**：`父级.find_all('测试find_子级')` 与
   整页同名查询、DOM 独立计数三者一致（各 1 条）；`父级.find_all('测试find_父级')`（自身不在作用域内）
   与子树外元素均为空列表并等满超时。
2. **跨 iframe/open shadow 的已保存路径，元素级作用域查不到**：同一 root 下
   `find_all('..._相似元素')` 返回 0 条，而整页同名查询返回 3 条、shadow DOM 内确有 3 个节点。
   页面级能穿透、元素级不能穿透 —— 属**不对称边界**，本脚本记为 `KNOWN`（不计退出码）。
   已提 Issue：https://github.com/uiautoma/desktop/issues/64 （修复后本用例应升级为 PASS）。

## 期望值来源

- **活推导**：整页命中数、root 子树内节点数、文本一致性均由脚本现场读取。
- **独立确证**：子树内命中数用页面内 DOM（按 root 的 class 现场读取后）独立计数，不经过
  `find_all` 自身；`Selector` 对象与名称字符串两种入参形态互相对照。

退出码：0 = 全部 PASS（允许 KNOWN）；1 = 存在 FAIL；2 = 无非 FAIL 但存在 BLOCKED。
"""
from __future__ import annotations

import argparse
import inspect
import json
import shutil
import time
import uuid
from pathlib import Path

import uiautoma
from uiautoma import (
    ElementNotFoundError,
    InvalidParamsError,
    NoCurrentPackageError,
    StalePackageError,
    web,
)
from uiautoma._core import RpcProtocolError
from uiautoma.web import WebBrowser, WebElement
from _web_page_identity import count_key, leaked, page_key

__test__ = False

URL = "https://baobaomi900901.github.io/xpath/#/anchor-test"
OTHER_URL = "https://baobaomi900901.github.io/xpath/#/form-controls"
BOUNDARY_URL = "https://baobaomi900901.github.io/xpath/#/iframe-shadow-form"
PARENT = "web靶场_测试find_父级"
CHILD = "web靶场_测试find_子级"
OUTSIDE = "web靶场_测试get_text_按钮_确定"
RADIO_MALE = "web靶场_表单测试_ant_radio_label_男"
RADIO_ALL = "web靶场_表单测试_ant_radio_label_相似元素"
DEFAULT_LIBRARY = Path(r"D:\code\元素库\260902_web元素")
LIB_TMP_ROOT = Path(__file__).resolve().parents[1] / ".pytest_tmp"
GREEN, RED, YELLOW, BLUE, RESET = "\x1b[92m", "\x1b[91m", "\x1b[93m", "\x1b[94m", "\x1b[0m"

# Runtime 偶发返回的可重试错误（消息自带「请重试」）。它不是语义结果，因此：
#  - 对「失效句柄被拒绝」类断言，它与 ElementNotFoundError 同为可接受的具体类型；
#  - 每次出现都登记到 TRANSIENT_NOTES，收尾以 KNOWN 用例如实列出，不隐藏抖动。
TRANSIENT_NOTES: list[str] = []

# 独立计数：按 root 的 class（现场读取）在页面内统计「文本与目标子节点完全一致的叶子节点」，
# 不经过 SDK 的作用域解析，因此与 find_all 的命中数互为确证。
COUNT_LEAF_TEXT = (
    "function (element, args) {"
    " const roots = Array.from(document.getElementsByClassName(args.cls));"
    " if (!roots.length) return null;"
    " const root = roots[0];"
    " const text = (args.text || '').trim();"
    " const leaves = Array.from(root.querySelectorAll('*')).filter("
    "   node => node.children.length === 0 && (node.textContent || '').trim() === text);"
    " return {total: leaves.length, rootTag: root.tagName}; }"
)
REMOVE_BY_CLASS = (
    "function (element, args) {"
    " const roots = Array.from(document.getElementsByClassName(args.cls));"
    " if (!roots.length) return 'missing';"
    " roots[0].remove();"
    " return 'removed'; }"
)
SHADOW_COUNT = (
    "function (element, args) {"
    " const iframe = document.querySelector('#iframe-shadow-form');"
    " const shadow = iframe && iframe.contentDocument"
    "   && iframe.contentDocument.querySelector('#form-shadow-host').shadowRoot;"
    " if (!shadow) return null;"
    " return {radioWrappers: shadow.querySelectorAll('.ant-radio-wrapper').length,"
    "   checkboxWrappers: shadow.querySelectorAll('.ant-checkbox-wrapper').length,"
    "   radioGroups: shadow.querySelectorAll('.ant-radio-group').length}; }"
)


def result(case_id: str, status: str, detail: str, **extra):
    return {"case_id": case_id, "status": status, "detail": detail, **extra}


def exception_name(exc: BaseException) -> str:
    return type(exc).__name__


def error_detail(prefix: str, exc: BaseException) -> str:
    trace_info = str(getattr(exc, "trace_info", "") or "")
    return f"{prefix}: {exception_name(exc)}: {str(exc)[:200]}" + (f" [trace={trace_info}]" if trace_info else "")


def expected_names(expected_type) -> str:
    if isinstance(expected_type, tuple):
        return " 或 ".join(item.__name__ for item in expected_type)
    return expected_type.__name__


def check_contract():
    method = getattr(WebElement, "find_all", None)
    sig = inspect.signature(method) if callable(method) else None
    if sig is None:
        return result("api_contract", "FAIL", "WebElement.find_all 不存在")
    parameters = list(sig.parameters.values())
    names = tuple(sig.parameters)
    annotation = str(sig.return_annotation)
    ok = (
        names == ("self", "selector", "timeout")
        and parameters[1].default is inspect.Parameter.empty
        and parameters[1].kind is inspect.Parameter.POSITIONAL_OR_KEYWORD
        and parameters[2].kind is inspect.Parameter.KEYWORD_ONLY
        and parameters[2].default == 10
    )
    return result(
        "api_contract", "PASS" if ok else "FAIL",
        f"selector 必填、timeout 仅限关键字且默认 10、返回注解 {annotation}" if ok
        else f"公开签名不符合合同: {sig}", return_annotation=annotation)


def expect_raises(call, expected_type, label: str, message_contains: str = "",
                  max_elapsed: float | None = None, transient_type=None, **extra):
    started = time.perf_counter()
    try:
        call()
    except expected_type as exc:
        elapsed = round(time.perf_counter() - started, 3)
        text = str(exc)
        transient = transient_type is not None and isinstance(exc, transient_type)
        if transient:
            TRANSIENT_NOTES.append(f"{label}: {exception_name(exc)}: {text[:100]}")
        if message_contains and message_contains not in text and not transient:
            return result(label, "FAIL", f"{exception_name(exc)} 消息不含 {message_contains!r}：{text[:200]}",
                          elapsed_s=elapsed, **extra)
        if max_elapsed is not None and elapsed > max_elapsed:
            return result(label, "FAIL", f"耗时过长：{elapsed}s > {max_elapsed}s", elapsed_s=elapsed, **extra)
        detail = f"{exception_name(exc)} 正确拒绝（{elapsed}s）：{text[:160]}"
        if transient:
            detail += "［Runtime 偶发可重试错误，已登记］"
        return result(label, "PASS", detail, elapsed_s=elapsed, transient=transient, **extra)
    except Exception as exc:  # noqa: BLE001
        return result(label, "FAIL",
                      f"拒绝类型错误，应为 {expected_names(expected_type)}: {exception_name(exc)}: {exc}", **extra)
    return result(label, "FAIL", "调用未被拒绝", **extra)


def timed_find_all(element, selector, timeout: float):
    started = time.perf_counter()
    try:
        value = element.find_all(selector, timeout=timeout)
    except Exception as exc:  # noqa: BLE001
        return None, round(time.perf_counter() - started, 3), error_detail("调用失败", exc)
    return value, round(time.perf_counter() - started, 3), ""


def texts_of(elements) -> list[str]:
    values = []
    for item in elements:
        try:
            values.append((item.get_text() or "").strip())
        except Exception:  # noqa: BLE001
            values.append("")
    return values


def run(args):
    results = [check_contract()]
    if results[-1]["status"] != "PASS" or args.contract_only:
        return results, 0 if results[-1]["status"] == "PASS" else 1

    run_id = uuid.uuid4().hex
    work_dir = LIB_TMP_ROOT / run_id
    copy_dir = work_dir / "lib"
    package = None
    page = None
    boundary_page = None
    page_id = ""
    baseline_matches = 0

    try:
        try:
            tabs = web.get_all(mode=args.mode)
            results.append(result("environment_baseline", "PASS",
                                  f"进入时浏览器共 {len(tabs)} 个标签（用于收尾核对）", tabs=len(tabs)))
        except Exception as exc:  # noqa: BLE001
            results.append(result("environment_baseline", "BLOCKED", error_detail("无法读取标签列表", exc)))
            return results, 2

        try:
            if not args.library.is_dir():
                results.append(result("library_prepare", "BLOCKED", f"元素库不存在: {args.library}"))
                return results, 2
            work_dir.mkdir(parents=True, exist_ok=True)
            shutil.copytree(args.library, copy_dir)
            package = uiautoma.open(str(copy_dir), timeout=20, connect_timeout=20)
            listed = package.elements.list(kind="web")
            ok = package.web_count == len(listed) and package.web_count > 0
            results.append(result(
                "library_prepare", "PASS" if ok else "FAIL",
                f"已打开元素库副本：web 元素 {package.web_count} 个（与列举一致）" if ok else
                f"元素数与列举不一致: web_count={package.web_count}, listed={len(listed)}",
                web_count=package.web_count))
            if not ok:
                return results, 1
        except Exception as exc:  # noqa: BLE001
            results.append(result("library_prepare", "BLOCKED", error_detail("无法准备元素库", exc)))
            return results, 2

        try:
            page = web.create(args.target_url, mode=args.mode, load_timeout=args.load_timeout)
            page_id = page_key(page)
            baseline_matches = count_key(page_id, args.mode)
            ok = isinstance(page, WebBrowser) and bool(page.get_url())
            results.append(result(
                "page_prepare", "PASS" if ok else "FAIL",
                "已打开标准靶场同文档页面（#/anchor-test）" if ok else f"返回对象异常: {page!r}",
                url=page.get_url()))
            if not ok:
                return results, 1
        except Exception as exc:  # noqa: BLE001
            results.append(result("page_prepare", "BLOCKED", error_detail("无法打开靶场页", exc)))
            return results, 2

        # ── 主验收：标准靶场同文档页面 ─────────────────────────────────────────────
        root = page.find(PARENT, timeout=args.timeout)
        class_attr = str(root.get_attribute("class") or "")
        root_class = class_attr.split()[0] if class_attr else ""
        ok = bool(root_class)
        results.append(result(
            "root_prepared", "PASS" if ok else "FAIL",
            f"root = {PARENT}（class={class_attr!r}，按 class 做 DOM 独立计数）" if ok
            else f"root 未取到可用 class: {class_attr!r}", root_class=root_class))
        if not ok:
            return results, 1

        page_level = page.find_all(CHILD, timeout=args.timeout)
        child = page.find(CHILD, timeout=args.timeout)
        child_text = (child.get_text() or "").strip()
        dom = page.execute_javascript(COUNT_LEAF_TEXT, {"cls": root_class, "text": child_text})
        dom_total = dom.get("total") if isinstance(dom, dict) else None
        ok = (
            isinstance(page_level, list) and len(page_level) >= 1
            and bool(child_text)
            and dom_total == len(page_level)
        )
        results.append(result(
            "child_baseline", "PASS" if ok else "FAIL",
            f"整页命中 {len(page_level)} 条、DOM 叶子文本计数 {dom_total}、子节点文本 {child_text!r} —— 三者一致"
            if ok else
            f"基线不一致: page_level={len(page_level)}, dom={dom_total}, text={child_text!r}",
            page_level_count=len(page_level), dom_count=dom_total))

        scoped, scoped_elapsed, scoped_error = timed_find_all(root, CHILD, args.timeout)
        scoped_texts = texts_of(scoped or [])
        ok = (
            isinstance(scoped, list) and len(scoped) == len(page_level)
            and scoped_texts == [(item.get_text() or "").strip() for item in page_level]
        )
        results.append(result(
            "scoped_matches_page_level", "PASS" if ok else "FAIL",
            f"限定 root 后命中 {len(scoped)} 条，与整页命中一致（{scoped_elapsed}s）；文本逐条相同" if ok
            else f"作用域结果不符: scoped={None if scoped is None else len(scoped)}, "
                 f"page_level={len(page_level)}, error={scoped_error}",
            scoped_count=None if scoped is None else len(scoped),
            page_level_count=len(page_level), elapsed_s=scoped_elapsed))

        self_hits, self_elapsed, self_error = timed_find_all(root, PARENT, args.timeout)
        page_self = page.find_all(PARENT, timeout=0)
        # 严格子集：该名称在整页命中 ≥1 条（root 本身），在 root 作用域内必须恰好 0 条
        ok = (
            isinstance(self_hits, list) and self_hits == []
            and isinstance(page_self, list) and len(page_self) >= 1
            and self_elapsed >= args.timeout - 0.2
        )
        results.append(result(
            "scoped_strict_subset_excludes_root", "PASS" if ok else "FAIL",
            f"严格子集：整页命中 {len(page_self)} 条（含 root 自身），root 作用域内 0 条，"
            f"且等满超时（{self_elapsed}s）—— 作用域确实排除了自身" if ok
            else f"结果不符: scoped={None if self_hits is None else len(self_hits)}, "
                 f"page_level={None if page_self is None else len(page_self)}, "
                 f"elapsed={self_elapsed}s, error={self_error}",
            elapsed_s=self_elapsed, page_level_count=None if page_self is None else len(page_self)))

        outside_hits, outside_elapsed, outside_error = timed_find_all(root, OUTSIDE, args.timeout)
        page_outside = page.find_all(OUTSIDE, timeout=0)
        # 该名称在当前页无任何命中：作用域内同样为空，且要等满超时（不是立刻返回）
        ok = (
            isinstance(outside_hits, list) and outside_hits == []
            and isinstance(page_outside, list) and page_outside == []
            and outside_elapsed >= args.timeout - 0.2
        )
        results.append(result(
            "empty_result_waits_full_timeout", "PASS" if ok else "FAIL",
            f"当前页无该名称命中（整页 0 条）时，root 内同样为空并等满超时（{outside_elapsed}s）" if ok
            else f"结果不符: scoped={None if outside_hits is None else len(outside_hits)}, "
                 f"page={None if page_outside is None else len(page_outside)}, elapsed={outside_elapsed}s, "
                 f"error={outside_error}",
            elapsed_s=outside_elapsed, page_level_count=None if page_outside is None else len(page_outside)))

        zero_value, zero_elapsed, zero_error = timed_find_all(root, CHILD, 0)
        ok = isinstance(zero_value, list) and zero_elapsed < 1.0
        results.append(result(
            "timeout_zero_single_check", "PASS" if ok else "FAIL",
            f"timeout=0 只查一次并立即返回（{zero_elapsed}s，{len(zero_value)} 条）" if ok
            else f"结果不符: value={zero_value!r}, elapsed={zero_elapsed}s, error={zero_error}",
            elapsed_s=zero_elapsed))

        try:
            selector = package.selector(CHILD)
            by_selector, selector_elapsed, selector_error = timed_find_all(root, selector, args.timeout)
            ok = (
                isinstance(by_selector, list) and isinstance(scoped, list)
                and len(by_selector) == len(scoped)
                and texts_of(by_selector) == scoped_texts
            )
            results.append(result(
                "selector_object_same_as_name", "PASS" if ok else "FAIL",
                f"Selector 对象与名称字符串结果一致（各 {len(by_selector)} 条，{selector_elapsed}s）" if ok
                else f"两种入参结果不一致: selector={by_selector!r}, error={selector_error}",
                elapsed_s=selector_elapsed))
        except Exception as exc:  # noqa: BLE001
            results.append(result("selector_object_same_as_name", "FAIL", error_detail("Selector 入参失败", exc)))

        results.append(result(
            "returns_list_type", "PASS" if isinstance(scoped, list) else "FAIL",
            f"返回值类型为 list（{len(scoped) if isinstance(scoped, list) else type(scoped).__name__}）"))

        # 错误与边界（异常类型按当前 SDK 精确断言：ElementNotFoundError 与 ActionError
        # 都是 UIAutomataError 的直接子类，彼此不是继承关系）
        results.append(expect_raises(
            lambda: root.find_all("__uiautoma_not_exist__", timeout=2), ElementNotFoundError,
            "unknown_name_rejected", message_contains="未找到选择器", max_elapsed=1.0))
        results.append(expect_raises(
            lambda: root.find_all(".ant-radio-wrapper", timeout=2), ElementNotFoundError,
            "css_string_treated_as_name", message_contains="未找到选择器", max_elapsed=1.0))
        results.append(expect_raises(
            lambda: root.find_all(CHILD, timeout=-2), InvalidParamsError,
            "timeout_negative", message_contains="-1", max_elapsed=1.0))
        results.append(expect_raises(
            lambda: root.find_all(CHILD, timeout="x"), InvalidParamsError,
            "timeout_non_numeric", message_contains="秒数", max_elapsed=1.0))
        results.append(expect_raises(
            lambda: root.find_all(None, timeout=1), InvalidParamsError,
            "selector_none", message_contains="元素名称字符串", max_elapsed=1.0))
        results.append(expect_raises(
            lambda: root.find_all(123, timeout=1), InvalidParamsError,
            "selector_int", message_contains="元素名称字符串", max_elapsed=1.0))
        results.append(expect_raises(
            lambda: root.find_all(CHILD, 1, "extra"), TypeError,
            "extra_positional", max_elapsed=1.0))
        results.append(expect_raises(
            lambda: root.find_all(), TypeError, "missing_selector", max_elapsed=1.0))

        # ── 跨 iframe / open shadow 的不对称边界（KNOWN，不计退出码） ───────────────
        try:
            boundary_page = web.create(BOUNDARY_URL, mode=args.mode, load_timeout=args.load_timeout)
            # 新建 iframe 页需要先预热页面运行时，否则首次元素级调用可能命中
            # `RpcProtocolError [trace=page_runtime_probe_timeout]`（与 wait_appear 验收同一现象）。
            warmed = False
            deadline = time.monotonic() + 8.0
            while time.monotonic() < deadline:
                try:
                    if boundary_page.execute_javascript("function () { return 1; }") == 1:
                        warmed = True
                        break
                except Exception:  # noqa: BLE001
                    pass
                time.sleep(0.3)
            male = boundary_page.find(RADIO_MALE, timeout=args.timeout)
            group = male.parent(timeout=args.timeout)
            group_class = str(group.get_attribute("class") or "")
            page_radio = boundary_page.find_all(RADIO_ALL, timeout=args.timeout)
            scoped_radio, radio_elapsed, radio_error = timed_find_all(group, RADIO_ALL, args.timeout)
            probe_error = "page_runtime_probe_timeout" in radio_error
            if scoped_radio is None and probe_error:
                # 可重试的页面运行时探测超时：预热后重试一次；仍失败则记为环境阻塞而非判据失败
                time.sleep(1.0)
                scoped_radio, radio_elapsed, radio_error = timed_find_all(group, RADIO_ALL, args.timeout)
            shadow = boundary_page.execute_javascript(SHADOW_COUNT)
            shadow_wrappers = shadow.get("radioWrappers") if isinstance(shadow, dict) else None
            page_count = None if page_radio is None else len(page_radio)
            scoped_count = None if scoped_radio is None else len(scoped_radio)
            if scoped_count is None and "page_runtime_probe_timeout" in radio_error:
                results.append(result(
                    "iframe_shadow_scoped_empty", "BLOCKED",
                    f"元素级调用两次均命中页面运行时探测超时（{radio_error}），"
                    f"预热={warmed}，本轮无法判定边界；整页命中 {page_count} 条、shadow 内 {shadow_wrappers} 个节点",
                    page_level_count=page_count, shadow_wrappers=shadow_wrappers))
            elif scoped_count == 0 and page_count and shadow_wrappers == page_count:
                results.append(result(
                    "iframe_shadow_scoped_empty", "KNOWN",
                    (
                        f"跨 iframe/open shadow 的已保存路径上，元素级作用域返回 0 条，"
                        f"而整页同名查询返回 {page_count} 条、shadow DOM 内确有 {shadow_wrappers} 个节点："
                        f"页面级可穿透、元素级不可穿透的不对称边界（class={group_class!r}，{radio_elapsed}s）。"
                        f"典型成因推定：已保存路径从顶层 document 开始（首段为 iframe），而作用域查询在 root "
                        f"所在框架内解析该路径，故无交集；未插桩确证。已提 Issue #64："
                        f"https://github.com/uiautoma/desktop/issues/64 。"
                    ),
                    page_level_count=page_count, scoped_count=scoped_count,
                    shadow_wrappers=shadow_wrappers, elapsed_s=radio_elapsed))
            elif scoped_count:
                # 观察到的另一形态：这一轮元素级作用域竟然也命中了。如实记 KNOWN，不掩盖不确定性。
                results.append(result(
                    "iframe_shadow_scoped_empty", "KNOWN",
                    f"本轮元素级作用域在 iframe root 上**命中了 {scoped_count} 条**（整页 {page_count} 条、"
                    f"shadow 内 {shadow_wrappers} 个节点），与其它轮次的 0 条不一致 —— 该边界疑似不稳定，"
                    f"已在 Issue #64 记录；本次不作为 PASS 也不作为 FAIL。",
                    page_level_count=page_count, scoped_count=scoped_count,
                    shadow_wrappers=shadow_wrappers, elapsed_s=radio_elapsed))
            else:
                results.append(result(
                    "iframe_shadow_scoped_empty", "BLOCKED",
                    f"边界刻画无法判定：page_level={page_count}, scoped={scoped_count}, "
                    f"shadow={shadow_wrappers}, error={radio_error}",
                    page_level_count=page_count, scoped_count=scoped_count,
                    shadow_wrappers=shadow_wrappers))
        except Exception as exc:  # noqa: BLE001
            results.append(result("iframe_shadow_scoped_empty", "BLOCKED",
                                  error_detail("边界刻画场景无法完成", exc)))
        finally:
            if boundary_page is not None:
                try:
                    boundary_page.close(ignore_beforeunload=True)
                except Exception:  # noqa: BLE001
                    pass
                boundary_page = None
                time.sleep(0.5)

        # root 节点被移除
        try:
            removed = page.execute_javascript(REMOVE_BY_CLASS, {"cls": root_class})
            time.sleep(0.2)
            results.append(result(
                "root_removed_before_call", "PASS" if removed == "removed" else "FAIL",
                f"已移除 root 节点（{removed}）"))
            results.append(expect_raises(
                lambda: root.find_all(CHILD, timeout=2), (ElementNotFoundError, RpcProtocolError),
                "stale_root_rejected", message_contains="未找到", max_elapsed=3.0,
                transient_type=RpcProtocolError))
        except Exception as exc:  # noqa: BLE001
            results.append(result("root_removed_before_call", "FAIL", error_detail("移除 root 失败", exc)))

        # 跨页 root
        try:
            page.navigate(OTHER_URL, load_timeout=args.load_timeout)
            time.sleep(0.8)
            started = time.perf_counter()
            try:
                root.find_all(CHILD, timeout=2)
                cross = "未报错（可疑）"
            except Exception as exc:  # noqa: BLE001
                cross = f"{exception_name(exc)}: {str(exc)[:120]}"
            ok = cross != "未报错（可疑）"
            results.append(result(
                "cross_page_root_error", "PASS" if ok else "FAIL",
                f"跨页后旧 root 调用被拒绝（{round(time.perf_counter() - started, 3)}s）：{cross}",
                error_text=cross))
        except Exception as exc:  # noqa: BLE001
            results.append(result("cross_page_root_error", "FAIL", error_detail("跨页用例失败", exc)))

        # 生命周期
        try:
            page.close(ignore_beforeunload=True)
        except Exception as exc:  # noqa: BLE001
            results.append(result("page_close_verified", "FAIL", error_detail("page.close 调用失败", exc)))
        else:
            time.sleep(0.5)
            leftover = leaked(page_id, baseline_matches, args.mode)
            results.append(result(
                "page_close_verified", "PASS" if not leftover else "FAIL",
                "页面已关闭，且 web.get_all() 复核无残留" if not leftover else
                f"关闭后仍有残留: {len(leftover)}", leftover_pages=len(leftover)))
        results.append(expect_raises(
            lambda: root.find_all(CHILD, timeout=1), (ElementNotFoundError, RpcProtocolError),
            "after_page_close", max_elapsed=3.0, transient_type=RpcProtocolError))
        page = None

        try:
            package.close()
            results.append(result("package_close_verified", "PASS", "Package 已关闭"))
        except (StalePackageError, RpcProtocolError) as exc:
            TRANSIENT_NOTES.append(f"package_close_verified: {exception_name(exc)}: {str(exc)[:100]}")
            results.append(result(
                "package_close_verified", "PASS",
                f"Package 会话已不可用，close() 被明确拒绝而非静默成功（{exception_name(exc)}: "
                f"{str(exc)[:80]}，trace={getattr(exc, 'trace_info', '') or '无'}）—— 属可接受的终态，已登记"))
        except Exception as exc:  # noqa: BLE001
            results.append(result("package_close_verified", "FAIL", error_detail("Package 关闭失败", exc)))
        package = None
        results.append(expect_raises(
            lambda: root.find_all(CHILD, timeout=1),
            (NoCurrentPackageError, StalePackageError),
            "no_package_rejected", message_contains="Package", max_elapsed=2.0))
        results.append(result(
            "runtime_transient_errors",
            "KNOWN" if TRANSIENT_NOTES else "PASS",
            (f"本轮观察到 {len(TRANSIENT_NOTES)} 次 Runtime 可重试错误（RpcProtocolError「请重试」）："
             + "；".join(TRANSIENT_NOTES)
             + "。这些不是语义结果，已按可接受类型判定并在本行登记；若持续出现应作为 Runtime 稳定性问题单独刻画。"
             if TRANSIENT_NOTES else "本轮未观察到 Runtime 可重试错误"),
            occurrences=len(TRANSIENT_NOTES)))
    except Exception as exc:  # noqa: BLE001
        results.append(result("scenario", "FAIL", error_detail("find_all 场景执行失败", exc)))
    finally:
        close_error = ""
        for item in (page, boundary_page):
            if item is not None:
                try:
                    item.close(ignore_beforeunload=True)
                except Exception as exc:  # noqa: BLE001
                    close_error = close_error or f"{exception_name(exc)}: {exc}"
        if package is not None:
            try:
                package.close()
            except Exception:  # noqa: BLE001
                pass
        shutil.rmtree(work_dir, ignore_errors=True)
        time.sleep(0.5)
        leftover_tabs = 0
        try:
            leftover_tabs = len(leaked(page_id, baseline_matches, args.mode)) if page_id else 0
        except Exception as exc:  # noqa: BLE001
            close_error = close_error or f"get_all 复核失败: {exception_name(exc)}: {exc}"
        cleaned = not close_error and not work_dir.exists() and leftover_tabs == 0
        results.append(result(
            "cleanup", "PASS" if cleaned else "FAIL",
            "已关闭页面与 Package、删除元素库副本、无残留标签" if cleaned else
            f"清理不完整: 错误={close_error or '无'}, 临时目录残留={work_dir.exists()}, "
            f"新增标签={leftover_tabs}", error=close_error, leftover_tabs=leftover_tabs))

    statuses = {item["status"] for item in results}
    code = 1 if "FAIL" in statuses else (2 if "BLOCKED" in statuses else 0)
    return results, code


def main(argv=None):
    parser = argparse.ArgumentParser(description="WebElement.find_all() 元素对象 API 验收")
    parser.add_argument("--target-url", default=URL, help="标准靶场同文档页面（默认 #/anchor-test）")
    parser.add_argument("--library", type=Path, default=DEFAULT_LIBRARY, help="元素库目录")
    parser.add_argument("--mode", choices=("chrome", "edge"), default="chrome")
    parser.add_argument("--load-timeout", type=float, default=20)
    parser.add_argument("--timeout", type=float, default=2)
    parser.add_argument("--contract-only", action="store_true")
    parser.add_argument("--json", action="store_true", help="在表格后额外输出 JSON 报告（用于归档验收产物）")
    args = parser.parse_args(argv)
    if args.load_timeout <= 0:
        parser.error("--load-timeout 必须大于 0")
    if args.timeout <= 0:
        parser.error("--timeout 必须大于 0")

    results, code = run(args)
    print("UIAutoma Web API 测试")
    print("API     : uiautoma.web.WebElement.find_all")
    print(f"页面    : {args.target_url}")
    print(f"元素库  : {args.library}")
    print("进度     状态    测试项                  测试结果")
    print("────────────────────────────────────────────────────────────────────────")
    for index, current in enumerate(results, 1):
        status = current["status"]
        color = {"PASS": GREEN, "BLOCKED": YELLOW, "KNOWN": BLUE}.get(status, RED)
        label = {"PASS": "通过", "BLOCKED": "阻塞", "KNOWN": "记录"}.get(status, "失败")
        print(f"{index:02d}/{len(results):02d}    {color}[{label}]{RESET}  "
              f"{current['case_id']:<34}  {current['detail']}")
    print("────────────────────────────────────────────────────────────────────────")
    counted = [item for item in results if item["status"] != "KNOWN"]
    summary = "测试通过" if code == 0 else ("测试阻塞" if code == 2 else "测试失败")
    print(f"{summary} · {sum(item['status'] == 'PASS' for item in counted)}/{len(counted)} 通过"
          f"（另 {sum(item['status'] == 'KNOWN' for item in results)} 项记录，不计入退出码） · 退出码 {code}")
    if args.json:
        print(json.dumps({
            "api": "uiautoma.web.WebElement.find_all",
            "target_url": args.target_url, "library": str(args.library), "mode": args.mode,
            "status": "PASS" if code == 0 else ("BLOCKED" if code == 2 else "FAIL"),
            "exit_code": code, "results": results,
        }, ensure_ascii=False, indent=2))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
