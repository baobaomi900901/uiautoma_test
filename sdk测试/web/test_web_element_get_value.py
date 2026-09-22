"""`WebElement.get_value()` 验收脚本。

靶场/页面
    `https://baobaomi900901.github.io/xpath/#/iframe-shadow-form`
    （该页把全部原生控件的库元素都采集齐了：输入框 / 密码 / 邮件 / 数字 / 文本域 /
    select 单选 / 滑块 / radio label / 提交按钮。）

元素库/元素
    `D:\\code\\元素库\\260902_web元素`（本轮只用副本），主元素
    `web靶场_表单测试_原生_输入框` —— iframe → open shadow DOM 内的
    `<input type="text" id="form-controls-native-text">`。

前置条件（会翻转，必须每次检查）
    靶场 `FormControlsPage` 的 `readDynamicIdsPreference()` **默认开启动态 ID**，状态持久化在
    `localStorage['form-controls-dynamic-ids']`。开启时 id 变成 `form-controls-native-text_<随机>`，
    而库元素路径**必需**固定 id → 全部相关库元素同时失效。脚本按
    `web/表单元素复测清单.md` 的规则处理：先读地面真值（DOM 实际 id），仅在动态时点一次开关关闭。

期望值来源
    1. **独立推导**：空输入框的 IDL `value` 是空字符串 `""`；没有 `value` 属性的节点返回 `None`。
    2. **独立确证（跨通道）**：页面侧经 `iframe.contentDocument → #form-shadow-host → shadowRoot`
       直读 `el.value`（CDP 通道），与 SDK（`chrome.scripting` 通道）返回对照。
    3. **独立确证（页面自身状态）**：点击页面自己的「提交」后，`#native-result` 会显示由
       Ant form 实例生成的表单快照 JSON 并同时写剪贴板；该通道完全不经过 SDK，用于确认
       写入的值确实被**页面自己**认可。

被测源码要点（worktree `D:\\code\\desktop`，基线 `c101caa9`）
    `sdk/src/uiautoma/web/element.py:548` `get_value(self) -> str | None`，无参数；
    `sdk/src/uiautoma/_core/client.py:3944` `get_value(*, timeout: float = 5.0) -> str | None`
    （docstring：读取当前 **value property**；`None` 原样透出，其余转 `str`）；
    RPC `web.get_value`（`runtime/services/capabilities.py:274`，必填
    `package_token`/`element_id`/`timeout_ms`）；Runtime `action_service.web_get_value_element`
    （`:2489`）→ `_run_web_value(op="get_value")`（`:6102`，要求 `locator_kind == "runtime_ref"`，
    即必须由实时 `find` 取得）；引擎 `chrome/engine/engine_packages/page_engine_runtime.js:3669`
    取 `element.value`，`null` 原样返回。

注意：`get_attribute("value")` **不能**当 content attribute 的对照。引擎
`page_engine_runtime.js:3688` 是 `element.getAttribute(name) ?? element[name]`，属性缺失时会
回退到 IDL 属性，两者被混同。

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
from _web_env import (  # noqa: E402
    check_web_channel,
    list_chrome_profiles,
    pin_environment,
    safe_tab_count,
)

__test__ = False

TARGET_URL = "https://baobaomi900901.github.io/xpath/#/iframe-shadow-form"
DEFAULT_LIBRARY = Path(r"D:\code\元素库\260902_web元素")
EXPECTED_PAGE_TITLE = "iframe + Shadow 表单测试"
P = "web靶场_表单测试_原生_"
TEXT_ELEMENT = P + "输入框"
SWITCH_ELEMENT = "web靶场_表单测试_控制表单组件id是否为动态的开关"
SUBMIT_ELEMENT = P + "按钮_提交"
LABEL_ELEMENT = P + "radio_label_男"
FIXED_TEXT_ID = "form-controls-native-text"
MARKER = "uiautoma-get-value-probe"

# 控件矩阵：库元素名 -> (DOM 固定 id 或 None, 说明)
MATRIX = (
    (P + "密码输入框", "form-controls-native-password"),
    (P + "邮件输入框", "form-controls-native-email"),
    (P + "数字输入框", "form-controls-native-number"),
    (P + "文本域", "form-controls-native-remark"),
    (P + "select单选", "form-controls-native-city"),
    (P + "滑块", "form-controls-native-range"),
    (SUBMIT_ELEMENT, "form-controls-native-submit"),
)

GREEN, RED, YELLOW, RESET = "\x1b[92m", "\x1b[91m", "\x1b[93m", "\x1b[0m"

# 页面侧读取：iframe -> open shadow root 内的 id -> {value, hasValue, attr, hasAttr}
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
    "   out[ids[i]] = e ? { value: e.value, hasValue: ('value' in e),"
    "     attr: e.getAttribute('value'), hasAttr: e.hasAttribute('value') } : null; }"
    " var res = root.getElementById('native-result');"
    " var any = root.querySelector('[id^=\"form-controls-native-text\"]');"
    " return { stage: 'ok', values: out, nativeResult: res ? res.textContent : null,"
    "   textIdSeen: any ? any.id : null }; }"
)

# 页面侧写入：原生 setter 改 IDL，再派发真实 input 事件，让 React 受控状态同步
WRITE_JS = (
    "function (element, payload) {"
    " var d = document.getElementById('iframe-shadow-form');"
    " var cd = d.contentDocument; var h = cd.getElementById('form-shadow-host');"
    " var root = h.shadowRoot; var el = root.getElementById(payload.id);"
    " if (!el) return { ok: false, reason: 'no_element' };"
    " var proto = el.tagName === 'TEXTAREA' ? HTMLTextAreaElement.prototype : HTMLInputElement.prototype;"
    " var setter = Object.getOwnPropertyDescriptor(proto, 'value').set;"
    " setter.call(el, payload.text);"
    " el.dispatchEvent(new Event('input', { bubbles: true }));"
    " return { ok: true, idl: el.value, hasAttr: el.hasAttribute('value'), attr: el.getAttribute('value') }; }"
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
    method = getattr(WebElement, "get_value", None)
    if not callable(method):
        rec.add("api_contract", "FAIL", "WebElement.get_value 不存在")
        return False
    signature = inspect.signature(method)
    parameters = list(signature.parameters.values())
    names = tuple(signature.parameters)
    annotation = str(signature.return_annotation)
    ok = (
        names == ("self",)
        and parameters[0].kind is inspect.Parameter.POSITIONAL_OR_KEYWORD
        and "None" in annotation
    )
    rec.add(
        "api_contract",
        "PASS" if ok else "FAIL",
        f"get_value 无参数、返回注解含 None（签名 {signature}，返回注解 {annotation!r}）" if ok
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

    baseline_tabs = safe_tab_count(args.mode)
    work_dir = Path(tempfile.mkdtemp(prefix="uiautoma-get-value-", dir=str(args.temp_root)))
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
        after_tabs = safe_tab_count(args.mode)
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
        # ---- 浏览器通道前置检查 ----
        # 一次连着多个 Chrome 用户环境/插件时，Runtime 会拒绝所有 web.* 调用
        # （trace web_environment_ambiguous），get_all 与 create 都不可用。
        # 这不是产品缺陷、也不是判据问题：按产品提示固定目标用户环境即可继续。
        channel = check_web_channel(args.mode)
        pinned_note = ""
        profiles: list[str] = []
        profile_error = ""
        if not channel["ok"]:
            profiles, profile_error = list_chrome_profiles(args.chrome_user_data_dir)
            if args.profile or args.chrome_user_data_dir:
                ok, pinned_note = pin_environment(args.mode, args.profile, args.chrome_user_data_dir)
                if ok:
                    channel = check_web_channel(args.mode)
        if not channel["ok"]:
            if profiles:
                hint = "；可选用户环境：" + "、".join(profiles)
            elif profile_error:
                hint = f"；无法读取 Chrome Local State（{profile_error}）"
            else:
                hint = ""
            rec.add(
                "env_prepare", "BLOCKED",
                f"浏览器通道不可用（{channel['exception']} trace={channel['trace'] or '无'}）："
                f"{channel['message']}{hint}"
                + (f"；{pinned_note}" if pinned_note else "")
                + "；可用 --profile <名称> 指定目标用户环境后重试",
                trace=channel["trace"], profiles=profiles,
            )
            return rec.results, 2
        baseline_tabs = channel["tabs"]
        rec.add(
            "env_prepare", "PASS",
            f"浏览器通道可用，进入时 {baseline_tabs} 个标签"
            + (f"（{pinned_note}）" if pinned_note else ""),
            tabs_before=baseline_tabs,
        )

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

        # ---- 前置条件：动态 ID 开关（地面真值）----
        dom = read_dom(page, [FIXED_TEXT_ID])
        if dom.get("stage") != "ok":
            rec.add("dynamic_id_precondition", "BLOCKED",
                    f"iframe/open shadow 结构未就绪：stage={dom.get('stage')}")
            return rec.results, 2
        seen = dom.get("textIdSeen")
        turned_off = False
        if seen != FIXED_TEXT_ID and seen:
            # 动态 ID 已开启：按测试清单只点击一次开关关闭
            try:
                switch = page.find(SWITCH_ELEMENT, timeout=args.element_timeout)
                node = switch
                for _ in range(5):
                    if node.get_attribute("role") == "switch":
                        break
                    node = node.parent()
                state = node.get_attribute("aria-checked")
                if state == "true":
                    switch.click(simulative=False, delay_after=0.8)
                    turned_off = True
            except Exception as exc:  # noqa: BLE001
                rec.add("dynamic_id_precondition", "BLOCKED",
                        f"动态 ID 已开启且开关操作失败：{error_detail('switch', exc)}")
                return rec.results, 2
            dom = read_dom(page, [FIXED_TEXT_ID])
            seen = dom.get("textIdSeen")
        if seen != FIXED_TEXT_ID:
            rec.add(
                "dynamic_id_precondition", "BLOCKED",
                f"固定 id 不可用：DOM 中实际 id={seen!r}，期望 {FIXED_TEXT_ID!r}；"
                f"库元素路径依赖固定 id，需先关闭靶场「动态 ID」开关",
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
            element = page.find(args.element, timeout=args.element_timeout)
        except Exception as exc:  # noqa: BLE001
            rec.add("element_bind", "BLOCKED",
                    f"库元素 {args.element} 无法绑定：{error_detail('find', exc)}")
            return rec.results, 2
        rec.add(
            "element_bind", "PASS",
            f"库元素绑定成功：find_all 命中 {len(hits)} 个，返回单一 WebElement（id={element.id}）",
            hits=len(hits), element_id=str(element.id),
        )

        initial = element.get_value()

        # ---- 空值语义：空字符串而非 None ----
        empty_ok = initial == "" and type(initial) is str
        rec.add(
            "empty_value_is_empty_string", "PASS" if empty_ok else "FAIL",
            f"空输入框返回空字符串（type={type(initial).__name__}），不是 None" if empty_ok
            else f"期望空字符串 str，实测 {initial!r} type={type(initial).__name__}",
            initial=initial,
        )

        # ---- 独立确证：与页面侧 IDL value 跨通道一致 ----
        dom = read_dom(page, [FIXED_TEXT_ID])
        dom_value = ((dom.get("values") or {}).get(FIXED_TEXT_ID) or {}).get("value")
        rec.add(
            "dom_idl_agrees", "PASS" if dom_value == initial else "FAIL",
            f"与页面侧直读 IDL value 一致（均为 {dom_value!r}）" if dom_value == initial
            else f"不一致：SDK={initial!r}，页面侧 el.value={dom_value!r}",
            dom_value=dom_value,
        )

        # ---- 正向：页面侧写入已知值后必须读回 ----
        wrote = page.execute_javascript(
            WRITE_JS, {"id": FIXED_TEXT_ID, "text": MARKER}, execution_world="MAIN")
        after = element.get_value()
        write_ok = bool((wrote or {}).get("ok")) and after == MARKER
        rec.add(
            "live_write_visible", "PASS" if write_ok else "FAIL",
            f"页面侧写入 {MARKER!r} 后 get_value 精确读回（写入回执 idl={((wrote or {}).get('idl'))!r}）"
            if write_ok else
            f"写入未被读回：写入回执={wrote}，get_value={after!r}",
            written=MARKER, read=after, write_receipt=wrote,
        )

        # ---- 独立确证：页面自身提交回显（不经 SDK）----
        try:
            page.find(SUBMIT_ELEMENT, timeout=args.element_timeout).click(
                simulative=False, delay_after=1.2)
            echo = read_dom(page, [FIXED_TEXT_ID])
            echo_text = str(echo.get("nativeResult") or "")
            echo_ok = MARKER in echo_text
            rec.add(
                "page_form_state_agrees", "PASS" if echo_ok else "FAIL",
                f"页面自身提交回显的表单快照 JSON 含 {MARKER!r}，页面认可该值"
                if echo_ok else
                f"页面回显未含写入值；回显片段={echo_text[:160]!r}",
                echo_head=echo_text[:160],
            )
        except Exception as exc:  # noqa: BLE001
            rec.add("page_form_state_agrees", "BLOCKED",
                    f"页面提交回显通道不可用：{error_detail('submit', exc)}")

        # ---- 重复读取 ----
        reads = [element.get_value() for _ in range(3)]
        stable = len(set(reads)) == 1 and reads[0] == MARKER
        rec.add(
            "repeat_read_stable", "PASS" if stable else "FAIL",
            f"连续 3 次读取一致且等于写入值，均为 {MARKER!r}"
            if stable else f"重复读取不一致：{reads!r}",
            reads=reads,
        )

        # ---- 还原并复核 ----
        page.execute_javascript(
            WRITE_JS, {"id": FIXED_TEXT_ID, "text": ""}, execution_world="MAIN")
        restored = element.get_value()
        restore_ok = restored == ""
        rec.add(
            "restore_verified", "PASS" if restore_ok else "FAIL",
            f"页面侧写回空串后 get_value 返回空字符串，控件已还原"
            if restore_ok else f"还原失败：get_value={restored!r}",
            restored=restored,
        )

        # ---- 负例：没有 value 属性的节点必须返回 None ----
        try:
            label = page.find(LABEL_ELEMENT, timeout=args.element_timeout)
            label_value = label.get_value()
            none_ok = label_value is None
            rec.add(
                "no_value_property_is_none", "PASS" if none_ok else "FAIL",
                f"无 value 属性的元素（{label.name!r}）返回 None，覆盖 str | None 的 None 分支"
                if none_ok else
                f"期望 None，实测 {label_value!r} type={type(label_value).__name__}",
                label_value=label_value,
            )
        except Exception as exc:  # noqa: BLE001
            rec.add("no_value_property_is_none", "BLOCKED",
                    f"负例元素绑定失败：{error_detail('find', exc)}")

        # ---- 控件矩阵：各控件 get_value 与页面侧 IDL 一致 ----
        rows: list[str] = []
        disagreements: list[str] = []
        missing: list[str] = []
        for name, dom_id in MATRIX:
            try:
                control = page.find(name, timeout=args.element_timeout)
            except Exception as exc:  # noqa: BLE001
                missing.append(f"{name}({type(exc).__name__})")
                continue
            try:
                sdk_value = control.get_value()
            except Exception as exc:  # noqa: BLE001
                disagreements.append(f"{name}:get_value {type(exc).__name__}")
                continue
            dom_now = read_dom(page, [dom_id])
            dom_control = ((dom_now.get("values") or {}).get(dom_id) or {})
            dom_control_value = dom_control.get("value", "<no-node>")
            rows.append(f"{name.rsplit('_', 1)[-1]}={sdk_value!r}/dom={dom_control_value!r}")
            if dom_control_value != "<no-node>" and sdk_value != dom_control_value:
                disagreements.append(f"{name}:{sdk_value!r}!={dom_control_value!r}")
        matrix_status = "FAIL" if disagreements else ("KNOWN" if missing else "PASS")
        rec.add(
            "control_matrix", matrix_status,
            (f"{len(rows)} 个控件的 get_value 与页面侧 IDL value 全部一致："
             + "；".join(rows)
             + (f"；另有 {len(missing)} 个未能绑定：{missing}" if missing else ""))
            if not disagreements else
            f"存在不一致：{disagreements}；明细={'；'.join(rows)}",
            rows=rows, disagreements=disagreements, missing=missing,
        )

        # ---- 参数校验：零参数合同 ----
        try:
            element.get_value("extra")  # type: ignore[call-arg]
            rec.add("param_positional", "FAIL", "额外位置参数未被拒绝")
        except TypeError as exc:
            rec.add("param_positional", "PASS", f"多余位置参数被 TypeError 拒绝：{exc}")
        except Exception as exc:  # noqa: BLE001
            rec.add("param_positional", "FAIL", error_detail("期望 TypeError", exc))

        try:
            element.get_value(timeout=1)  # type: ignore[call-arg]
            rec.add("param_keyword", "FAIL", "未声明的 timeout 关键字未被拒绝")
        except TypeError as exc:
            rec.add("param_keyword", "PASS", f"未声明关键字被 TypeError 拒绝：{exc}")
        except Exception as exc:  # noqa: BLE001
            rec.add("param_keyword", "FAIL", error_detail("期望 TypeError", exc))

        # ---- 生命周期 ----
        page.close(ignore_beforeunload=True)
        page_closed = True
        try:
            element.get_value()
            rec.add("stale_page_reference", "FAIL", "页面关闭后 get_value 未报错")
        except Exception as exc:  # noqa: BLE001
            trace = str(getattr(exc, "trace_info", "") or "")
            ok = trace == "stale_page_reference" and "失效" in str(exc)
            rec.add(
                "stale_page_reference", "PASS" if ok else "FAIL",
                f"关闭后读取被拒绝：{type(exc).__name__} trace={trace} 消息={exc}"
                if ok else error_detail("关闭后报错语义不符", exc),
            )
    except Exception as exc:  # noqa: BLE001
        rec.add("scenario", "FAIL", error_detail("get_value 场景执行失败", exc))
    finally:
        cleanup_case()

    statuses = {item["status"] for item in rec.results}
    code = 1 if "FAIL" in statuses else (2 if "BLOCKED" in statuses else 0)
    return rec.results, code


def main(argv=None):
    parser = argparse.ArgumentParser(description="WebElement.get_value() 元素对象 API 验收")
    parser.add_argument("--target-url", default=TARGET_URL, help="靶场页面")
    parser.add_argument("--library", type=Path, default=DEFAULT_LIBRARY, help="元素库目录（只读，测试用副本）")
    parser.add_argument("--element", default=TEXT_ELEMENT, help="元素库中的主元素名称")
    parser.add_argument("--mode", choices=("chrome", "edge"), default="chrome")
    parser.add_argument("--load-timeout", type=float, default=30)
    parser.add_argument("--element-timeout", type=float, default=10)
    parser.add_argument("--runtime-timeout", type=float, default=30)
    parser.add_argument("--contract-only", action="store_true")
    parser.add_argument("--profile", default=None,
                        help="Chrome 用户环境目录名或显示名；浏览器通道报环境歧义时用它固定目标环境")
    parser.add_argument("--chrome-user-data-dir", default=None,
                        help="Chrome 用户数据目录，用于读取可选用户环境列表")
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
    print("API     : uiautoma.web.WebElement.get_value")
    print(f"页面    : {args.target_url}")
    print(f"元素库  : {args.library}（元素 {args.element}）")
    print("进度     状态    测试项                  测试结果")
    print("────────────────────────────────────────────────────────────────────────")
    for index, current in enumerate(results, 1):
        status = current["status"]
        color = {"PASS": GREEN, "BLOCKED": YELLOW, "KNOWN": YELLOW}.get(status, RED)
        label = {"PASS": "通过", "BLOCKED": "阻塞", "KNOWN": "已知"}.get(status, "失败")
        print(f"{index:02d}/{len(results):02d}    {color}[{label}]{RESET}  "
              f"{current['case_id']:<26}  {current['detail']}")
    print("────────────────────────────────────────────────────────────────────────")
    summary = "测试通过" if code == 0 else ("测试阻塞" if code == 2 else "测试失败")
    print(f"{summary} · {sum(item['status'] == 'PASS' for item in results)}/{len(results)} 通过 · 退出码 {code}")
    if args.json:
        print(json.dumps({
            "api": "uiautoma.web.WebElement.get_value",
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
