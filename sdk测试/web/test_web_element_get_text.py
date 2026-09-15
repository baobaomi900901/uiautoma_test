"""WebElement.get_text() 元素对象 API 专项验收。

靶场：维护者的官方靶场（测试侧不自建页面）。
- 主页面：`https://baobaomi900901.github.io/xpath/#/element-html-test`
  页面上有 `#element-html-input`（HTML 输入框）、`#element-html-apply`（确定）、
  `#element-html-reset`（重置）、`#element-html-target`（靶元素，可渲染任意 HTML）、
  `#element-html-result`（回显 innerHTML 的 `<pre>`）。
- 元素库 `260902_web元素` 中为本次验收准备了 4 条 web 元素：
  `web靶场_测试get_text_靶元素` / `_按钮_确定` / `_按钮_重置` / `_输入框`。
  脚本先 `find(名称)` 再用 `get_attribute("id")` 核对它们各自指向哪个 DOM 节点，
  然后**主要走名称目标路线**（文档主用法），另用 CSS 路线对照一次。

## 期望值怎么来（两类，互不依赖）

1. **受控 fixture（独立推导）**：脚本用 `execute_javascript` 往靶元素注入 HTML，
   期望值按 **`innerText` 的公开语义**手写推导——块级元素与 `<br>` 产生换行、连续空白折叠、
   `display:none` 与 `visibility:hidden` 不计入、`<script>`/`<style>` 排除、
   `<input>`/`<textarea>` 取 `value`。**不拿浏览器的 `innerText` 当答案**；
   但会把浏览器自身的 `innerText`/`textContent`/`value` 一并记进报告供对照。
2. **真实页面元素（对齐策略）**：对按钮等无法手推期望值的元素，断言 `get_text()`
   等于浏览器自身的 `innerText` —— 这正是源码声明的 `text_strategy: "innerText"`。

源码要点：`WebElement.get_text()`（无参数，返回 `str`）→ `web.get_text` →
引擎 `String(element.innerText || element.value || "")`；Runtime 侧不截断、不裁剪；
元素无文本时返回空字符串（不是 `None`）。

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

import uiautoma
from uiautoma import ActionError, web
from uiautoma.web import WebBrowser, WebElement

__test__ = False

URL = "https://baobaomi900901.github.io/xpath/#/element-html-test"
TARGET_SELECTOR = "#element-html-target"
LIBRARY_TARGET = "web靶场_测试get_text_靶元素"
LIBRARY_CONFIRM = "web靶场_测试get_text_按钮_确定"
LIBRARY_RESET = "web靶场_测试get_text_按钮_重置"
LIBRARY_INPUT = "web靶场_测试get_text_输入框"
EXPECTED_DOM_IDS = {
    LIBRARY_TARGET: "element-html-target",
    LIBRARY_CONFIRM: "element-html-apply",
    LIBRARY_RESET: "element-html-reset",
    LIBRARY_INPUT: "element-html-input",
}
DEFAULT_LIBRARY = Path(r"D:\code\元素库\260902_web元素")
LIB_TMP_ROOT = Path(__file__).resolve().parents[1] / ".pytest_tmp"
GREEN, RED, YELLOW, RESET = "\x1b[92m", "\x1b[91m", "\x1b[93m", "\x1b[0m"

SET_HTML = (
    "function (element, args) {"
    " const target = document.getElementById('element-html-target');"
    " if (!target) return 'no-target';"
    " target.innerHTML = args.html;"
    " return target.innerHTML; }"
)
BROWSER_VIEW = (
    "function (element, args) {"
    " const el = args.sel ? document.querySelector(args.sel)"
    "   : document.getElementById('element-html-target');"
    " if (!el) return null;"
    " return {innerText: el.innerText, textContent: el.textContent,"
    "   value: ('value' in el ? el.value : null), tag: el.tagName}; }"
)
SET_TEXTAREA = (
    "function (element, args) {"
    " const input = document.querySelector('#element-html-input');"
    " if (!input) return 'no-input';"
    " const setter = Object.getOwnPropertyDescriptor(window.HTMLTextAreaElement.prototype, 'value').set;"
    " setter.call(input, args.value);"
    " input.dispatchEvent(new Event('input', { bubbles: true }));"
    " return input.value; }"
)
CLICK = (
    "function (element, args) {"
    " const el = document.querySelector(args.sel);"
    " if (!el) return 'missing';"
    " el.click();"
    " return true; }"
)

# 受控 fixture：期望值按 innerText 公开语义手写推导（不使用浏览器结果当答案）
FIXTURES = (
    ("plain_text", "<span>str</span>", None, "str", "纯文本 span"),
    ("nested_inline", "<b>加粗</b><i>斜体</i><span>后缀</span>", None, "加粗斜体后缀",
     "行内嵌套不产生分隔符"),
    ("block_lines", "<div>第一行</div><div>第二行</div>", None, "第一行\n第二行",
     "块级元素之间产生换行（textContent 中不存在）"),
    ("br_break", "第一行<br>第二行", None, "第一行\n第二行", "<br> 产生换行"),
    ("hidden_child_display_none", '可见<span style="display:none">隐藏</span>', None, "可见",
     "display:none 的子文本不计入"),
    ("hidden_child_visibility", '可见<span style="visibility:hidden">半隐藏</span>', None, "可见",
     "visibility:hidden 的子文本不计入"),
    ("whitespace_collapse", "a     b\t\tc", None, "a b c", "连续空白折叠为单个空格"),
    ("nbsp_entity", "a&nbsp;b", None, "a\u00a0b", "&nbsp; 保留为 U+00A0"),
    ("script_style_excluded", "<script>var x = 1;</script>正文<style>.a{color:red}</style>", None,
     "正文", "<script>/<style> 内容不计入"),
    ("empty_span", "<span></span>", None, "", "无文本时返回空字符串"),
    ("pre_newlines", "<pre>a\nb</pre>", None, "a\nb", "<pre> 保留换行"),
    ("mixed_nested", "<div>标题<span>后缀</span></div><div>次行</div>", None, "标题后缀\n次行",
     "行内与块级混合"),
    ("input_value_fallback", "<input id='probe-input' value='输入值'>", "#probe-input", "输入值",
     "input 无 innerText 时取 value"),
    ("textarea_value_fallback", "<textarea id='probe-textarea'>多行\n文本</textarea>",
     "#probe-textarea", "多行\n文本", "textarea 取 value"),
    ("button_text", "<button id='probe-button'>确 定</button>", "#probe-button", "确 定",
     "按钮文本原样返回（含空格）"),
)


def result(case_id: str, status: str, detail: str, **extra):
    return {"case_id": case_id, "status": status, "detail": detail, **extra}


def exception_name(exc: BaseException) -> str:
    return type(exc).__name__


def error_detail(prefix: str, exc: BaseException) -> str:
    trace_info = str(getattr(exc, "trace_info", "") or "")
    return f"{prefix}: {exception_name(exc)}: {exc}" + (f" [trace={trace_info}]" if trace_info else "")


def short(value, limit: int = 60) -> str:
    if not isinstance(value, str):
        return repr(value)
    return repr(value) if len(value) <= limit else f"{value[:limit]!r}…(len={len(value)})"


def check_contract():
    method = getattr(WebElement, "get_text", None)
    sig = inspect.signature(method) if callable(method) else None
    if sig is None:
        return result("api_contract", "FAIL", "WebElement.get_text 不存在")
    names = tuple(sig.parameters)
    ok = names == ("self",) and str(sig.return_annotation) == "str"
    return result(
        "api_contract", "PASS" if ok else "FAIL",
        "无任何参数；返回注解 str" if ok else f"公开签名不符合合同: {sig}")


def expect_raises(call, expected_type, label: str, message_contains: str = "",
                  max_elapsed: float | None = None, **extra):
    started = time.perf_counter()
    try:
        call()
    except expected_type as exc:
        elapsed = round(time.perf_counter() - started, 3)
        text = str(exc)
        if message_contains and message_contains not in text:
            return result(label, "FAIL", f"{exception_name(exc)} 消息不含 {message_contains!r}：{text}",
                          elapsed_s=elapsed, **extra)
        if max_elapsed is not None and elapsed > max_elapsed:
            return result(label, "FAIL", f"耗时过长：{elapsed}s > {max_elapsed}s", elapsed_s=elapsed, **extra)
        return result(label, "PASS", f"{exception_name(exc)} 正确拒绝（{elapsed}s）：{text}",
                      elapsed_s=elapsed, **extra)
    except Exception as exc:  # noqa: BLE001
        return result(label, "FAIL",
                      f"拒绝类型错误，应为 {expected_type.__name__}: {exception_name(exc)}: {exc}", **extra)
    return result(label, "FAIL", "调用未被拒绝", **extra)


def fixture_case(case_id: str, page, element, html: str, selector, expected: str, note: str,
                 route: str):
    """注入受控 HTML 后断言 get_text 的结果（element 为已绑定的读取目标）。"""
    try:
        injected = page.execute_javascript(SET_HTML, {"html": html})
        time.sleep(0.05)
    except Exception as exc:  # noqa: BLE001
        return result(case_id, "FAIL", error_detail(f"注入 fixture 失败（{note}）", exc), route=route)
    target = element
    if selector:
        try:
            target = page.find_by_css(selector, timeout=2)
        except Exception as exc:  # noqa: BLE001
            return result(case_id, "FAIL", error_detail(f"子元素查找失败（{note}）", exc), route=route)
    started = time.perf_counter()
    try:
        value = target.get_text()
    except Exception as exc:  # noqa: BLE001
        return result(case_id, "FAIL", error_detail(f"get_text 调用失败（{note}）", exc), route=route)
    elapsed = round(time.perf_counter() - started, 3)
    try:
        view = page.execute_javascript(BROWSER_VIEW, {"sel": selector}) or {}
    except Exception:  # noqa: BLE001
        view = {}
    ok = isinstance(value, str) and value == expected
    detail = (
        f"[{route}] {note}：get_text 返回 {short(value)}，与独立推导的期望值一致"
        if ok else
        f"[{route}] {note}：不符合期望。get_text={short(value)}（type={type(value).__name__}），"
        f"期望={short(expected)}；浏览器 innerText={short(view.get('innerText'))}、"
        f"textContent={short(view.get('textContent'))}、value={short(view.get('value'))}；"
        f"注入内容={injected!r}"
    )
    return result(case_id, "PASS" if ok else "FAIL", detail, elapsed_s=elapsed, route=route,
                  expected=expected, actual=value if isinstance(value, str) else repr(value),
                  browser_inner_text=view.get("innerText"),
                  browser_text_content=view.get("textContent"),
                  browser_value=view.get("value"))


def run(args):
    results = [check_contract()]
    if results[-1]["status"] != "PASS" or args.contract_only:
        return results, 0 if results[-1]["status"] == "PASS" else 1

    run_id = uuid.uuid4().hex
    work_dir = LIB_TMP_ROOT / run_id
    copy_dir = work_dir / "lib"
    package = None
    page = None
    page_id = ""
    try:
        try:
            baseline = web.get_all(mode=args.mode)
            results.append(result(
                "environment_baseline", "PASS",
                f"进入时浏览器共 {len(baseline)} 个标签", tabs=len(baseline)))
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
            page_id = page.id
            ok = isinstance(page, WebBrowser)
            results.append(result(
                "page_prepare", "PASS" if ok else "FAIL",
                "已打开元素 HTML 测试页" if ok else f"返回对象异常: {page!r}", url=page.get_url()))
            if not ok:
                return results, 1
        except Exception as exc:  # noqa: BLE001
            results.append(result("page_prepare", "BLOCKED", error_detail("无法打开靶场页", exc)))
            return results, 2

        # 库元素绑定 + 指向核对
        library_elements = {}
        try:
            mapping, problems = {}, []
            for name, expected_id in EXPECTED_DOM_IDS.items():
                element = page.find(name, timeout=args.timeout)
                actual_id = element.get_attribute("id")
                library_elements[name] = element
                mapping[name] = {"tag": element.name, "id": actual_id}
                if actual_id != expected_id:
                    problems.append(f"{name} 实际指向 id={actual_id!r}，期望 {expected_id!r}")
            ok = not problems
            results.append(result(
                "library_elements_mapping", "PASS" if ok else "FAIL",
                ("4 条库元素均已绑定且指向预期节点：" if ok else "指向不符：")
                + ("；".join(f"{name}→#{info['id']}" for name, info in mapping.items()) if ok
                   else "；".join(problems)),
                mapping=mapping))
            if not ok:
                return results, 1
        except Exception as exc:  # noqa: BLE001
            results.append(result("library_elements_mapping", "FAIL",
                                  error_detail("库元素绑定失败", exc)))
            return results, 1

        target = library_elements[LIBRARY_TARGET]

        # 受控 fixture（主路线：库元素名称目标）
        for case_id, html, selector, expected, note in FIXTURES:
            results.append(fixture_case(case_id, page, target, html, selector, expected, note, "库元素"))

        long_text = "长" * 1200
        results.append(fixture_case(
            "long_text_no_truncation", page, target, f"<span>{long_text}</span>", None, long_text,
            "1200 字符长文本（验证不截断）", "库元素"))

        # CSS 路线对照（证明结果与定位方式无关）
        try:
            css_target = page.find_by_css(TARGET_SELECTOR, timeout=5)
            for case_id, html, expected, note in (
                ("css_route_plain", "<span>css 路线</span>", "css 路线", "纯文本"),
                ("css_route_hidden", '可见<span style="display:none">隐藏</span>', "可见",
                 "隐藏子元素不计入"),
            ):
                results.append(fixture_case(case_id, page, css_target, html, None, expected, note,
                                            "CSS"))
        except Exception as exc:  # noqa: BLE001
            results.append(result("css_route_compare", "FAIL", error_detail("CSS 路线对照失败", exc)))

        # 库元素：按钮与输入框
        try:
            for case_id, name, selector, note in (
                ("library_button_confirm", LIBRARY_CONFIRM, "#element-html-apply", "「确定」按钮"),
                ("library_button_reset", LIBRARY_RESET, "#element-html-reset", "「重置」按钮"),
            ):
                element = library_elements[name]
                value = element.get_text()
                view = page.execute_javascript(BROWSER_VIEW, {"sel": selector}) or {}
                expected = str(view.get("innerText") or view.get("value") or "")
                ok = isinstance(value, str) and value == expected and bool(value)
                results.append(result(
                    case_id, "PASS" if ok else "FAIL",
                    f"{note}（库元素）：get_text={short(value)}，与浏览器 innerText 一致（策略对齐）" if ok
                    else f"{note} 不一致：get_text={short(value)}，浏览器={short(expected)}",
                    actual=value, browser_inner_text=view.get("innerText")))
        except Exception as exc:  # noqa: BLE001
            results.append(result("library_buttons", "FAIL", error_detail("库元素按钮用例失败", exc)))

        try:
            typed = "文本框内容\n第二行"
            page.execute_javascript(SET_TEXTAREA, {"value": typed})
            time.sleep(0.3)
            value = library_elements[LIBRARY_INPUT].get_text()
            ok = value == typed
            results.append(result(
                "library_input_value_fallback", "PASS" if ok else "FAIL",
                f"库元素「输入框」（textarea）：设置值后 get_text 返回该值（{short(value)}）" if ok else
                f"结果不符: get_text={short(value)}，期望={short(typed)}", actual=value))
        except Exception as exc:  # noqa: BLE001
            results.append(result("library_input_value_fallback", "FAIL",
                                  error_detail("库元素输入框用例失败", exc)))

        # 页面自身流程：输入 HTML → 点「确定」→ 经库元素读文本
        try:
            typed_html = "<b>流程</b>验证"
            page.execute_javascript(SET_TEXTAREA, {"value": typed_html})
            time.sleep(0.3)
            page.execute_javascript(CLICK, {"sel": "#element-html-apply"})
            time.sleep(0.4)
            value = library_elements[LIBRARY_TARGET].get_text()
            ok = value == "流程验证"
            results.append(result(
                "real_page_flow", "PASS" if ok else "FAIL",
                f"经页面自身流程（输入 {typed_html!r} → 点「确定」）渲染后，库元素 get_text 返回 {short(value)}" if ok
                else f"结果不符: get_text={short(value)}，期望 '流程验证'", actual=value))
        except Exception as exc:  # noqa: BLE001
            results.append(result("real_page_flow", "FAIL", error_detail("页面流程用例失败", exc)))

        # 节点被移除后
        try:
            results.append(fixture_case(
                "removed_node_before", page, target, "<i id='probe-gone'>临时</i>", "#probe-gone",
                "临时", "移除前可读", "CSS"))
            gone = page.find_by_css("#probe-gone", timeout=3)
            page.execute_javascript(SET_HTML, {"html": "<span>已替换</span>"})
            time.sleep(0.1)
            results.append(expect_raises(
                lambda: gone.get_text(), ActionError, "removed_node_after", max_elapsed=8.0))
        except Exception as exc:  # noqa: BLE001
            results.append(result("removed_node_before", "FAIL", error_detail("节点移除用例失败", exc)))

        # 参数与生命周期
        results.append(expect_raises(
            lambda: target.get_text("extra"), TypeError, "extra_positional", max_elapsed=1.0))
        results.append(expect_raises(
            lambda: target.get_text(timeout=1), TypeError, "unknown_kwarg", max_elapsed=1.0))

        try:
            page.close(ignore_beforeunload=True)
        except Exception as exc:  # noqa: BLE001
            results.append(result("page_close_verified", "FAIL", error_detail("page.close 调用失败", exc)))
        else:
            time.sleep(0.5)
            leftover = [p for p in web.get_all(mode=args.mode)
                        if str(getattr(p, "id", "") or "") == page_id]
            results.append(result(
                "page_close_verified", "PASS" if not leftover else "FAIL",
                "页面已关闭，且 web.get_all() 复核无残留" if not leftover else
                f"关闭后仍有残留: {len(leftover)}", leftover_pages=len(leftover)))
        results.append(expect_raises(
            lambda: target.get_text(), ActionError, "after_page_close", max_elapsed=3.0))
        page = None

        try:
            package.close()
            results.append(result("package_close_verified", "PASS", "Package 已关闭"))
        except Exception as exc:  # noqa: BLE001
            results.append(result("package_close_verified", "FAIL", error_detail("Package 关闭失败", exc)))
        package = None
    except Exception as exc:  # noqa: BLE001
        results.append(result("scenario", "FAIL", error_detail("get_text 场景执行失败", exc)))
    finally:
        close_error = ""
        if page is not None:
            try:
                page.close(ignore_beforeunload=True)
            except Exception as exc:  # noqa: BLE001
                close_error = f"{exception_name(exc)}: {exc}"
        if package is not None:
            try:
                package.close()
            except Exception:  # noqa: BLE001
                pass
        shutil.rmtree(work_dir, ignore_errors=True)
        time.sleep(0.5)
        cleaned = not close_error and not work_dir.exists()
        results.append(result(
            "cleanup", "PASS" if cleaned else "FAIL",
            "已关闭页面与 Package、删除元素库副本" if cleaned else
            f"清理不完整: 错误={close_error or '无'}, 临时目录残留={work_dir.exists()}",
            error=close_error))

    statuses = {item["status"] for item in results}
    code = 1 if "FAIL" in statuses else (2 if "BLOCKED" in statuses else 0)
    return results, code


def main(argv=None):
    parser = argparse.ArgumentParser(description="WebElement.get_text() 元素对象 API 验收")
    parser.add_argument("--target-url", default=URL, help="元素 HTML 测试页")
    parser.add_argument("--library", type=Path, default=DEFAULT_LIBRARY, help="元素库目录")
    parser.add_argument("--mode", choices=("chrome", "edge"), default="chrome")
    parser.add_argument("--load-timeout", type=float, default=20)
    parser.add_argument("--timeout", type=float, default=8, help="find 的 timeout，默认 8")
    parser.add_argument("--contract-only", action="store_true")
    parser.add_argument("--json", action="store_true", help="在表格后额外输出 JSON 报告（用于归档验收产物）")
    args = parser.parse_args(argv)
    if args.load_timeout <= 0:
        parser.error("--load-timeout 必须大于 0")

    results, code = run(args)
    print("UIAutoma Web API 测试")
    print("API     : uiautoma.web.WebElement.get_text")
    print(f"页面    : {args.target_url}")
    print(f"元素库  : {args.library}")
    print("进度     状态    测试项                  测试结果")
    print("────────────────────────────────────────────────────────────────────────")
    for index, current in enumerate(results, 1):
        status = current["status"]
        color = {"PASS": GREEN, "BLOCKED": YELLOW}.get(status, RED)
        label = {"PASS": "通过", "BLOCKED": "阻塞"}.get(status, "失败")
        print(f"{index:02d}/{len(results):02d}    {color}[{label}]{RESET}  "
              f"{current['case_id']:<36}  {current['detail']}")
    print("────────────────────────────────────────────────────────────────────────")
    summary = "测试通过" if code == 0 else ("测试阻塞" if code == 2 else "测试失败")
    print(f"{summary} · {sum(item['status'] == 'PASS' for item in results)}/{len(results)} 通过 · 退出码 {code}")
    if args.json:
        print(json.dumps({
            "api": "uiautoma.web.WebElement.get_text",
            "target_url": args.target_url, "library": str(args.library), "mode": args.mode,
            "status": "PASS" if code == 0 else ("BLOCKED" if code == 2 else "FAIL"),
            "exit_code": code, "results": results,
        }, ensure_ascii=False, indent=2))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
