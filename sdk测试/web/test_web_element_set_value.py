"""`WebElement.set_value()` 验收脚本。

靶场/页面
    `https://baobaomi900901.github.io/xpath/#/iframe-shadow-form`

元素库/元素
    `D:\\code\\元素库\\260902_web元素`（本轮只用副本）：
    主元素 `web靶场_表单测试_原生_输入框`（`input#form-controls-native-text`）、
    对照元素 `web靶场_表单测试_原生_文本域`（`textarea#form-controls-native-remark`）、
    `web靶场_表单测试_原生_radio_label_男`（无 value 属性的非输入元素）、
    `web靶场_表单测试_原生_按钮_提交`（页面自身的表单快照回显）。

前置条件
    靶场「动态 ID」开关默认开启且状态持久化；开启时固定 id 全部失效。脚本先读地面真值，
    只在动态时关闭开关（与 `get_value` 同一套前置条件）。

期望值来源
    1. **独立推导（DOM/HTML 规范）**：
       - docstring 承诺「不改变输入焦点或触发输入事件」→ 事件计数器必须保持 0；
       - `<input type="text">` 的 value sanitization 会**去除换行**，`<textarea>` 保留换行；
       - 覆盖语义来自 SDK 硬编码的 `clear=True`。
    2. **独立确证（跨通道）**：页面侧经 `iframe.contentDocument → #form-shadow-host → shadowRoot`
       直读 `el.value`，与 SDK 返回对照。
    3. **独立确证（页面自身状态）**：点击页面自己的「提交」触发 Ant form 快照并写入
       `#native-result`（不经 SDK）。用它做 A/B：`set_value` 不派发事件 → 快照不变；
       对照路径派发真实 `input` 事件 → 快照更新。

被测源码要点（worktree `D:\\code\\desktop`，基线 `c101caa9`）
    `sdk/src/uiautoma/web/element.py:557` `set_value(self, value: str) -> None` —— **没有自己的 RPC**，
    实现是 `self._raw.type_text(str(value), clear=True, focus=False, mode="set_value")`；
    `sdk/src/uiautoma/_core/client.py:3681` `type_text(...)` 组装 `text`/`clear`/`focus`/`mode`；
    RPC 为 `web.action`（`action="type_text"`）；Runtime
    `runtime/services/action_service.py:2298` `web_type_text_element` → 无 `input_check` 时直接
    `_run_web_dom_action(action="type_text")`（**不校验目标是否可编辑**）；引擎
    `chrome/engine/engine_packages/page_engine_runtime.js:3632-3636`：
    `property = mode === "set_value" ? "value"` → `element.value = text`，只写 IDL。
    另注（源码读得，未作为判据）：`type_text` 不在同文件 `:3502` 的跳过列表里，因此会先执行
    `element.scrollIntoView({block:"center"})`——`set_value` 会滚动到元素，但**不聚焦**。

退出码
    `0` 全部 PASS（允许 KNOWN）；`1` 存在 FAIL；`2` 无 FAIL 但存在 BLOCKED。
"""
from __future__ import annotations

import argparse
import inspect
import json
import shutil
import sys
import tempfile
import time
from pathlib import Path

import uiautoma
from uiautoma import web
from uiautoma.web import WebBrowser, WebElement

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _web_page_identity import tab_count  # noqa: E402

__test__ = False

TARGET_URL = "https://baobaomi900901.github.io/xpath/#/iframe-shadow-form"
DEFAULT_LIBRARY = Path(r"D:\code\元素库\260902_web元素")
EXPECTED_PAGE_TITLE = "iframe + Shadow 表单测试"
P = "web靶场_表单测试_原生_"
TEXT_ELEMENT = P + "输入框"
AREA_ELEMENT = P + "文本域"
LABEL_ELEMENT = P + "radio_label_男"
SUBMIT_ELEMENT = P + "按钮_提交"
SWITCH_ELEMENT = "web靶场_表单测试_控制表单组件id是否为动态的开关"
TEXT_ID = "form-controls-native-text"
AREA_ID = "form-controls-native-remark"
MARKER = "uiautoma-set-value-probe"

GREEN, RED, YELLOW, RESET = "\x1b[92m", "\x1b[91m", "\x1b[93m", "\x1b[0m"

READ_JS = (
    "function (element, ids) {"
    " var d = document.getElementById('iframe-shadow-form');"
    " if (!d) return { stage: 'no_iframe' };"
    " var cd = d.contentDocument; if (!cd) return { stage: 'no_document' };"
    " var h = cd.getElementById('form-shadow-host');"
    " if (!h) return { stage: 'no_host' };"
    " if (!h.shadowRoot) return { stage: 'no_shadow' };"
    " var root = h.shadowRoot; var out = {};"
    " for (var i = 0; i < ids.length; i++) {"
    "   var e = root.getElementById(ids[i]);"
    "   out[ids[i]] = e ? { value: e.value, hasAttr: e.hasAttribute('value'),"
    "     attr: e.getAttribute('value') } : null; }"
    " var any = root.querySelector('[id^=\"form-controls-native-text\"]');"
    " return { stage: 'ok', values: out, textIdSeen: any ? any.id : null,"
    "   active: root.activeElement ? (root.activeElement.id || root.activeElement.tagName) : null,"
    "   evt: (typeof window.__uiautomaEvt === 'number') ? window.__uiautomaEvt : null,"
    "   nativeResult: (function () { var r = root.getElementById('native-result');"
    "     return r ? r.textContent : null; })() }; }"
)

# 装事件计数器并清掉焦点，用于验证 set_value 既不派发事件也不改变焦点
HOOK_JS = (
    "function (element, ids) {"
    " var d = document.getElementById('iframe-shadow-form');"
    " var h = d.contentDocument.getElementById('form-shadow-host');"
    " var root = h.shadowRoot; window.__uiautomaEvt = 0;"
    " ids.forEach(function (id) { var e = root.getElementById(id); if (!e) return;"
    "   ['input', 'change'].forEach(function (name) {"
    "     e.addEventListener(name, function () { window.__uiautomaEvt += 1; }); }); });"
    " if (root.activeElement && root.activeElement.blur) root.activeElement.blur();"
    " return true; }"
)

# 对照路径：原生 setter 写 IDL + 派发真实 input 事件（会让 React 受控状态同步）
DISPATCH_JS = (
    "function (element, payload) {"
    " var d = document.getElementById('iframe-shadow-form');"
    " var h = d.contentDocument.getElementById('form-shadow-host');"
    " var root = h.shadowRoot; var el = root.getElementById(payload.id);"
    " if (!el) return null;"
    " var proto = el.tagName === 'TEXTAREA' ? HTMLTextAreaElement.prototype : HTMLInputElement.prototype;"
    " Object.getOwnPropertyDescriptor(proto, 'value').set.call(el, payload.text);"
    " el.dispatchEvent(new Event('input', { bubbles: true }));"
    " return el.value; }"
)


class Recorder:
    def __init__(self) -> None:
        self.results: list[dict] = []
        self._t0 = time.monotonic()

    def add(self, case_id: str, status: str, detail: str, **extra) -> dict:
        now = time.monotonic()
        elapsed = now - self._t0
        self._t0 = now
        item = {
            "case_id": case_id,
            "status": status,
            "detail": f"{detail}（耗时 {elapsed:.2f}s）",
            "elapsed": round(elapsed, 3),
            **extra,
        }
        self.results.append(item)
        return item


def error_detail(prefix: str, exc: BaseException) -> str:
    detail = f"{prefix}: {type(exc).__name__}: {exc}"
    trace = str(getattr(exc, "trace_info", "") or "")
    if trace:
        detail += f" [trace={trace}]"
    return detail


def check_contract(rec: Recorder) -> bool:
    method = getattr(WebElement, "set_value", None)
    if not callable(method):
        rec.add("api_contract", "FAIL", "WebElement.set_value 不存在")
        return False
    signature = inspect.signature(method)
    parameters = list(signature.parameters.values())
    annotation = str(signature.return_annotation)
    ok = (
        tuple(signature.parameters) == ("self", "value")
        and parameters[1].kind is inspect.Parameter.POSITIONAL_OR_KEYWORD
        and parameters[1].default is inspect.Parameter.empty
        and "None" in annotation
    )
    rec.add(
        "api_contract", "PASS" if ok else "FAIL",
        f"set_value 仅一个必填参数 value、返回 None（签名 {signature}，返回注解 {annotation!r}）" if ok
        else f"公开签名不符合合同: {signature}",
        signature=str(signature), return_annotation=annotation,
    )
    return ok


def read_dom(page: WebBrowser, ids: list[str]) -> dict:
    return page.execute_javascript(READ_JS, ids, execution_world="MAIN") or {}


def run(args):
    rec = Recorder()
    if not check_contract(rec):
        return rec.results, 1
    if args.contract_only:
        return rec.results, 0

    baseline_tabs = tab_count(args.mode)
    work_dir = Path(tempfile.mkdtemp(prefix="uiautoma-set-value-", dir=str(args.temp_root)))
    package = None
    page: WebBrowser | None = None
    page_closed = False

    def cleanup_case() -> None:
        errors: list[str] = []
        if page is not None and not page_closed:
            try:
                page.close(ignore_beforeunload=True)
            except Exception as exc:  # noqa: BLE001
                errors.append(f"page: {type(exc).__name__}: {exc}")
        if package is not None:
            try:
                package.close()
            except Exception as exc:  # noqa: BLE001
                errors.append(f"package: {type(exc).__name__}: {exc}")
        shutil.rmtree(work_dir, ignore_errors=True)
        time.sleep(0.8)
        after_tabs = tab_count(args.mode)
        ok = not errors and not work_dir.exists()
        rec.add(
            "cleanup", "PASS" if ok else "FAIL",
            f"测试页面与 Package 已关闭，元素库副本已删除；标签数 {baseline_tabs} → {after_tabs}"
            f"（用户可能同时浏览，仅作诊断）"
            if ok else
            f"清理不完整：关闭错误={errors or '无'}，临时目录残留={work_dir.exists()}",
            tabs_before=baseline_tabs, tabs_after=after_tabs,
        )

    try:
        # ---- 环境准备 ----
        library_copy = work_dir / "library"
        try:
            shutil.copytree(args.library, library_copy)
        except OSError as exc:
            rec.add("library_prepare", "BLOCKED", f"元素库复制失败：{error_detail('copy', exc)}")
            return rec.results, 2
        package = uiautoma.open(str(library_copy), timeout=args.runtime_timeout,
                                connect_timeout=args.runtime_timeout)
        info = uiautoma.ping()
        rec.add(
            "library_prepare", "PASS",
            f"元素库副本已打开（{args.library.name}），Runtime {info.runtime_version} "
            f"协议 {info.protocol}，进入时 {baseline_tabs} 个标签",
            runtime_version=str(info.runtime_version), tabs_before=baseline_tabs,
        )

        try:
            page = web.create(args.target_url, mode=args.mode, load_timeout=args.load_timeout)
            title = page.get_title()
        except Exception as exc:  # noqa: BLE001
            rec.add("page_prepare", "BLOCKED", f"目标页面准备失败：{error_detail('create', exc)}")
            return rec.results, 2
        rec.add(
            "page_prepare", "PASS" if title == EXPECTED_PAGE_TITLE else "FAIL",
            f"目标页面已打开：title={title!r}（期望 {EXPECTED_PAGE_TITLE!r}）",
            url=page.get_url(), title=title,
        )
        if title != EXPECTED_PAGE_TITLE:
            return rec.results, 1

        # ---- 前置条件：动态 ID 开关 ----
        dom = read_dom(page, [TEXT_ID])
        if dom.get("stage") != "ok":
            rec.add("dynamic_id_precondition", "BLOCKED",
                    f"iframe/open shadow 结构未就绪：stage={dom.get('stage')}")
            return rec.results, 2
        seen = dom.get("textIdSeen")
        turned_off = False
        if seen != TEXT_ID and seen:
            try:
                switch = page.find(SWITCH_ELEMENT, timeout=args.element_timeout)
                node = switch
                for _ in range(5):
                    if node.get_attribute("role") == "switch":
                        break
                    node = node.parent()
                if node.get_attribute("aria-checked") == "true":
                    switch.click(simulative=False, delay_after=0.8)
                    turned_off = True
            except Exception as exc:  # noqa: BLE001
                rec.add("dynamic_id_precondition", "BLOCKED",
                        f"动态 ID 已开启且开关操作失败：{error_detail('switch', exc)}")
                return rec.results, 2
            dom = read_dom(page, [TEXT_ID])
            seen = dom.get("textIdSeen")
        if seen != TEXT_ID:
            rec.add(
                "dynamic_id_precondition", "BLOCKED",
                f"固定 id 不可用：DOM 实际 id={seen!r}，期望 {TEXT_ID!r}",
            )
            return rec.results, 2
        rec.add(
            "dynamic_id_precondition", "PASS",
            f"动态 ID 已关闭，DOM 实际 id={seen!r}（本轮{'曾开启并已关闭' if turned_off else '进入时即为关闭'}）",
            text_id=seen, turned_off=turned_off,
        )

        # ---- 元素绑定 ----
        try:
            hits = page.find_all(args.element, timeout=args.element_timeout)
            text = page.find(args.element, timeout=args.element_timeout)
            area = page.find(AREA_ELEMENT, timeout=args.element_timeout)
            label = page.find(LABEL_ELEMENT, timeout=args.element_timeout)
            submit = page.find(SUBMIT_ELEMENT, timeout=args.element_timeout)
        except Exception as exc:  # noqa: BLE001
            rec.add("element_bind", "BLOCKED", f"库元素无法绑定：{error_detail('find', exc)}")
            return rec.results, 2
        rec.add(
            "element_bind", "PASS",
            f"主元素 find_all 命中 {len(hits)} 个；输入框/文本域/radio label/提交按钮全部绑定成功",
            hits=len(hits), element_id=str(text.id),
        )

        # ---- 返回值 + 回读 + 跨通道 ----
        page.execute_javascript(HOOK_JS, [TEXT_ID, AREA_ID], execution_world="MAIN")
        returned = text.set_value(MARKER)
        readback = text.get_value()
        dom = read_dom(page, [TEXT_ID])
        dom_value = ((dom.get("values") or {}).get(TEXT_ID) or {}).get("value")
        ok = returned is None and readback == MARKER and dom_value == MARKER
        rec.add(
            "return_none_and_roundtrip", "PASS" if ok else "FAIL",
            f"返回 None；get_value 回读 {readback!r}；页面侧 el.value {dom_value!r}——三方一致"
            if ok else
            f"不符：返回={returned!r}，回读={readback!r}，页面侧={dom_value!r}",
            returned=repr(returned), readback=readback, dom_value=dom_value,
        )

        # ---- 核心：不派发 input/change 事件 ----
        evt_after_set = dom.get("evt")
        no_event_ok = evt_after_set == 0
        rec.add(
            "no_input_event", "PASS" if no_event_ok else "FAIL",
            f"写值后 input/change 监听计数仍为 {evt_after_set}，符合 docstring「不触发输入事件」"
            if no_event_ok else
            f"写值后事件计数为 {evt_after_set}，与「不触发输入事件」不符",
            event_count=evt_after_set,
        )

        # ---- 对照：证明计数器本身有效（否则上一条是空断言）----
        page.execute_javascript(
            DISPATCH_JS, {"id": TEXT_ID, "text": f"{MARKER}-dispatch"}, execution_world="MAIN")
        control = read_dom(page, [TEXT_ID])
        control_evt = control.get("evt")
        control_ok = isinstance(control_evt, int) and control_evt >= 1
        rec.add(
            "event_counter_control", "PASS" if control_ok else "FAIL",
            f"对照路径派发真实 input 事件后计数变为 {control_evt}，证明计数器有效、上一条非空断言"
            if control_ok else
            f"对照路径未触发计数（计数={control_evt}），上一条 no_input_event 为空断言",
            event_count=control_evt,
        )

        # ---- 不改变焦点 ----
        page.execute_javascript(HOOK_JS, [TEXT_ID, AREA_ID], execution_world="MAIN")
        focus_before = read_dom(page, [TEXT_ID]).get("active")
        text.set_value(f"{MARKER}-focus")
        focus_after = read_dom(page, [TEXT_ID]).get("active")
        focus_ok = focus_before == focus_after and focus_after != TEXT_ID
        rec.add(
            "no_focus_change", "PASS" if focus_ok else "FAIL",
            f"写值前后 shadow root 的 activeElement 均为 {focus_after!r}，未被聚焦"
            if focus_ok else
            f"焦点发生变化：{focus_before!r} → {focus_after!r}",
            focus_before=focus_before, focus_after=focus_after,
        )

        # ---- 覆盖语义（clear=True）----
        text.set_value("AAA")
        text.set_value("B")
        overwrite = text.get_value()
        rec.add(
            "overwrite_not_append", "PASS" if overwrite == "B" else "FAIL",
            f"连续两次写入后为 {overwrite!r}，是覆盖而不是追加" if overwrite == "B"
            else f"期望 'B'（覆盖），实测 {overwrite!r}",
            value=overwrite,
        )

        # ---- 空字符串 ----
        text.set_value("")
        empty = text.get_value()
        rec.add(
            "empty_string", "PASS" if empty == "" else "FAIL",
            f"写入空串后回读为空字符串 {empty!r}" if empty == ""
            else f"期望 ''，实测 {empty!r}",
            value=empty,
        )

        # ---- 换行净化：input 去换行（规范推导）----
        text.set_value("a\nb")
        input_value = text.get_value()
        rec.add(
            "newline_sanitized_text_input", "PASS" if input_value == "ab" else "FAIL",
            f"<input type=text> 写入 'a\\nb' 回读 {input_value!r}，符合 value sanitization 去换行语义"
            if input_value == "ab" else
            f"期望 'ab'（去换行），实测 {input_value!r}",
            value=input_value,
        )

        # ---- 换行保留：textarea ----
        area.set_value("a\nb")
        area_value = area.get_value()
        rec.add(
            "newline_preserved_textarea", "PASS" if area_value == "a\nb" else "FAIL",
            f"<textarea> 写入 'a\\nb' 回读 {area_value!r}，换行被保留（与 input 形成对照）"
            if area_value == "a\nb" else
            f"期望 'a\\nb'，实测 {area_value!r}",
            value=area_value,
        )

        # ---- 非字符串入参强制转换 ----
        text.set_value(123)
        coerced_int = text.get_value()
        text.set_value(None)
        coerced_none = text.get_value()
        coerce_ok = coerced_int == "123" and coerced_none == "None"
        rec.add(
            "non_string_coerced", "PASS" if coerce_ok else "FAIL",
            f"SDK 侧 str(value) 强制转换：123 → {coerced_int!r}，None → {coerced_none!r}"
            if coerce_ok else
            f"强转不符：123 → {coerced_int!r}，None → {coerced_none!r}",
            coerced_int=coerced_int, coerced_none=coerced_none,
        )

        # ---- 非输入元素：成功但只是 JS expando，不进 DOM ----
        try:
            label.set_value(MARKER)
            label_read = label.get_value()
            label_attr = label.get_attribute("value")
            label_html = label.get_html()
            serialized = f'value="{MARKER}"' in label_html
            expando_ok = label_read == MARKER and not serialized
            rec.add(
                "non_form_element_expando_not_serialized", "PASS" if expando_ok else "FAIL",
                f"非输入元素不报错：get_value 读回 {label_read!r}，但 get_html 中不含该 value 属性——"
                f"说明只是 JS expando，没有进入 DOM"
                if expando_ok else
                f"不符：读回={label_read!r}，序列化出现 value 属性={serialized}",
                label_read=label_read, label_attr=label_attr, serialized=serialized,
            )
        except Exception as exc:  # noqa: BLE001
            rec.add("non_form_element_expando_not_serialized", "FAIL",
                    error_detail("非输入元素 set_value 失败", exc))

        # ---- A/B：set_value 不更新页面表单状态 ----
        try:
            page.execute_javascript(
                DISPATCH_JS, {"id": TEXT_ID, "text": ""}, execution_world="MAIN")
            text.set_value("")
            submit.click(simulative=False, delay_after=1.2)
            baseline_echo = str(read_dom(page, [TEXT_ID]).get("nativeResult") or "")
            baseline_clean = '"text": ""' in baseline_echo

            text.set_value(f"{MARKER}-nosync")
            submit.click(simulative=False, delay_after=1.2)
            after_set_echo = str(read_dom(page, [TEXT_ID]).get("nativeResult") or "")
            set_not_seen = f"{MARKER}-nosync" not in after_set_echo

            page.execute_javascript(
                DISPATCH_JS, {"id": TEXT_ID, "text": f"{MARKER}-sync"}, execution_world="MAIN")
            submit.click(simulative=False, delay_after=1.2)
            after_dispatch_echo = str(read_dom(page, [TEXT_ID]).get("nativeResult") or "")
            dispatch_seen = f"{MARKER}-sync" in after_dispatch_echo

            ab_ok = baseline_clean and set_not_seen and dispatch_seen
            rec.add(
                "form_state_not_synced", "PASS" if ab_ok else "FAIL",
                "A/B 对照成立：基线快照 text 为空；set_value 写入后快照仍不含该值（未触发事件）；"
                "对照路径派发事件后快照立即包含该值"
                if ab_ok else
                f"A/B 不成立：基线为空={baseline_clean}，set_value 后未出现={set_not_seen}，"
                f"派发后出现={dispatch_seen}",
                baseline_clean=baseline_clean, set_not_seen=set_not_seen, dispatch_seen=dispatch_seen,
            )
            text.set_value("")
        except Exception as exc:  # noqa: BLE001
            rec.add("form_state_not_synced", "BLOCKED",
                    f"页面提交回显通道不可用：{error_detail('submit', exc)}")

        # ---- 参数校验 ----
        try:
            text.set_value()  # type: ignore[call-arg]
            rec.add("param_missing", "FAIL", "缺少必填参数未被拒绝")
        except TypeError as exc:
            rec.add("param_missing", "PASS", f"缺少必填参数被 TypeError 拒绝：{exc}")
        except Exception as exc:  # noqa: BLE001
            rec.add("param_missing", "FAIL", error_detail("期望 TypeError", exc))

        try:
            text.set_value("a", "b")  # type: ignore[call-arg]
            rec.add("param_extra_positional", "FAIL", "多余位置参数未被拒绝")
        except TypeError as exc:
            rec.add("param_extra_positional", "PASS", f"多余位置参数被 TypeError 拒绝：{exc}")
        except Exception as exc:  # noqa: BLE001
            rec.add("param_extra_positional", "FAIL", error_detail("期望 TypeError", exc))

        try:
            text.set_value(value=f"{MARKER}-kw")
            keyword_value = text.get_value()
            kw_ok = keyword_value == f"{MARKER}-kw"
            rec.add(
                "param_keyword", "PASS" if kw_ok else "FAIL",
                f"value 可用关键字传入并正确写入（回读 {keyword_value!r}）" if kw_ok
                else f"关键字传参写入不符：回读 {keyword_value!r}",
            )
        except Exception as exc:  # noqa: BLE001
            rec.add("param_keyword", "FAIL", error_detail("关键字传参失败", exc))
        text.set_value("")

        # ---- 生命周期 ----
        page.close(ignore_beforeunload=True)
        page_closed = True
        try:
            text.set_value("after-close")
            rec.add("stale_page_reference", "FAIL", "页面关闭后 set_value 未报错")
        except Exception as exc:  # noqa: BLE001
            trace = str(getattr(exc, "trace_info", "") or "")
            ok = trace == "stale_page_reference" and "失效" in str(exc)
            rec.add(
                "stale_page_reference", "PASS" if ok else "FAIL",
                f"关闭后写入被拒绝：{type(exc).__name__} trace={trace} 消息={exc}"
                if ok else error_detail("关闭后报错语义不符", exc),
            )
    except Exception as exc:  # noqa: BLE001
        rec.add("scenario", "FAIL", error_detail("set_value 场景执行失败", exc))
    finally:
        cleanup_case()

    statuses = {item["status"] for item in rec.results}
    code = 1 if "FAIL" in statuses else (2 if "BLOCKED" in statuses else 0)
    return rec.results, code


def main(argv=None):
    parser = argparse.ArgumentParser(description="WebElement.set_value() 元素对象 API 验收")
    parser.add_argument("--target-url", default=TARGET_URL, help="靶场页面")
    parser.add_argument("--library", type=Path, default=DEFAULT_LIBRARY, help="元素库目录（只读，测试用副本）")
    parser.add_argument("--element", default=TEXT_ELEMENT, help="元素库中的主元素名称")
    parser.add_argument("--mode", choices=("chrome", "edge"), default="chrome")
    parser.add_argument("--load-timeout", type=float, default=30)
    parser.add_argument("--element-timeout", type=float, default=10)
    parser.add_argument("--runtime-timeout", type=float, default=30)
    parser.add_argument("--contract-only", action="store_true")
    parser.add_argument("--json", action="store_true", help="在表格后额外输出 JSON 报告（用于归档验收产物）")
    args = parser.parse_args(argv)
    if min(args.load_timeout, args.element_timeout, args.runtime_timeout) <= 0:
        parser.error("timeout 参数必须大于 0")
    if not args.library.is_dir():
        parser.error(f"元素库不存在: {args.library}")
    args.temp_root = Path(__file__).resolve().parents[1] / ".pytest_tmp"
    args.temp_root.mkdir(parents=True, exist_ok=True)

    results, code = run(args)
    print("UIAutoma Web API 测试")
    print("API     : uiautoma.web.WebElement.set_value")
    print(f"页面    : {args.target_url}")
    print(f"元素库  : {args.library}（元素 {args.element}）")
    print("进度     状态    测试项                  测试结果")
    print("────────────────────────────────────────────────────────────────────────")
    for index, current in enumerate(results, 1):
        status = current["status"]
        color = {"PASS": GREEN, "BLOCKED": YELLOW, "KNOWN": YELLOW}.get(status, RED)
        label = {"PASS": "通过", "BLOCKED": "阻塞", "KNOWN": "已知"}.get(status, "失败")
        print(f"{index:02d}/{len(results):02d}    {color}[{label}]{RESET}  "
              f"{current['case_id']:<38}  {current['detail']}")
    print("────────────────────────────────────────────────────────────────────────")
    summary = "测试通过" if code == 0 else ("测试阻塞" if code == 2 else "测试失败")
    print(f"{summary} · {sum(item['status'] == 'PASS' for item in results)}/{len(results)} 通过 · 退出码 {code}")
    if args.json:
        print(json.dumps({
            "api": "uiautoma.web.WebElement.set_value",
            "target_url": args.target_url,
            "library": str(args.library),
            "element": args.element,
            "mode": args.mode,
            "sdk_path": str(Path(uiautoma.__file__).resolve()),
            "status": "PASS" if code == 0 else ("BLOCKED" if code == 2 else "FAIL"),
            "exit_code": code,
            "results": results,
        }, ensure_ascii=False, indent=2))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
