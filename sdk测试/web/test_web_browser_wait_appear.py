"""WebBrowser.wait_appear() 页面对象 API 专项验收。

靶场：维护者的官方靶场（测试侧不自建页面）。
- 常规页：`https://baobaomi900901.github.io/xpath/`（首页，含标题搜索过滤）
- 库元素所属页：`https://baobaomi900901.github.io/xpath/#/iframe-shadow-form`
- 元素库：`D:\\code\\元素库\\260902_web元素`（70 个 web 元素，全部属于上面那个 iframe 页；
  脚本复制副本后打开，绝不写入用户原件）

## 转变来源（transition source）

`wait_appear()` 的核心语义是「**等待期间**元素出现」，因此必须有一个在等待过程中发生的转变。

- `scheduled`（回退方案）：测试侧用 `execute_javascript` 注入稳定探针节点（挂在
  `window.__uiautomaWaitNode` 上），先移除、再在 1.2s 后**把同一个节点原样插回**。
  节点由浏览器真实渲染，测试侧只决定「何时」发生。
- `delayed-page`（canonical，靶场自计时页已部署）：`public/delayed-element.html`
  每 1.5s 交替插入/移除**同一个** `#delayed-target` 节点，**由页面自己计时，测试侧零调度**。
- `auto`（默认值）：先探测 `delayed-page` 是否可达，可达则用它，否则回退 `scheduled`。

名称/Selector 目标的「等待出现」不走上面两条：在**导航尚未完成时就开始等待**
（`navigate(..., load_timeout=0)` → `wait_appear(name, N)`），元素随路由切换出现，测试侧同样零调度。

## 已实测确立的判据（详见 web/evidence/wait_appear.md）

| 事实 | 结论 |
|---|---|
| `exists` 的语义 | **DOM 存在性**，不区分可见性（`display:none`、`getClientRects()=0` 仍算「存在」） |
| WebElement 目标的重新解析 | 按**节点身份**：同一节点移除后原样插回可以等到；React 销毁重建的新节点**不会**被旧引用认领 |
| 名称/Selector 目标 | 每次轮询都按库里的保存路径重新定位，故可等到「重新出现」 |
| 目标入参 | **只支持库元素名 / Selector / WebElement**，传 CSS 选择器会被当成库名并立即抛 `ActionError` |
| 轮询粒度 | 运行时约 0.1s；实测「出现」到返回的附加延迟约 0.2s |

状态模型：`PASS` / `FAIL` / `BLOCKED` 计入退出码；`KNOWN` 表示已如实刻画、由 API 语义决定的边界
（不计入退出码）。

退出码：0 = 全部 PASS（允许 KNOWN）；1 = 存在 FAIL；2 = 无非 FAIL 但存在 BLOCKED。
"""
from __future__ import annotations

import argparse
import inspect
import json
import shutil
import time
import urllib.error
import urllib.request
import uuid
from pathlib import Path

import uiautoma
from uiautoma import ActionError, InvalidParamsError, NoCurrentPackageError, web
from uiautoma.web import WebBrowser, WebElement
from _web_page_identity import count_key, leaked, page_key

__test__ = False

HOME_URL = "https://baobaomi900901.github.io/xpath/"
ELEMENT_NAME = "web靶场_表单测试_ant_输入框"
DEFAULT_LIBRARY = Path(r"D:\code\元素库\260902_web元素")
DELAYED_PAGE_URL = "https://baobaomi900901.github.io/xpath/delayed-element.html"
DELAYED_TARGET = "#delayed-target"
PROBE_SELECTOR = "#uiautoma-wait-target"
HIDDEN_SELECTOR = "#uiautoma-hidden-target"
CARD_SELECTOR = "#menu-anchor-test"
TRANSITION_DELAY = 1.2
LIB_TMP_ROOT = Path(__file__).resolve().parents[1] / ".pytest_tmp"
GREEN, RED, YELLOW, BLUE, RESET = "\x1b[92m", "\x1b[91m", "\x1b[93m", "\x1b[94m", "\x1b[0m"

# 探针节点挂在 window.__uiautomaWaitNode 上，保证「移除 → 插回」是同一个节点
# （WebElement 目标按节点身份解析，新建节点不会被旧引用认领）。
CREATE_PROBE = (
    "function () {"
    " const old = document.getElementById('uiautoma-wait-target'); if (old) old.remove();"
    " const node = document.createElement('div');"
    " node.id = 'uiautoma-wait-target'; node.textContent = '等待目标';"
    " node.style.cssText = 'padding:8px;border:1px solid #333;width:200px';"
    " document.body.appendChild(node);"
    " window.__uiautomaWaitNode = node;"
    " return !!document.getElementById('uiautoma-wait-target'); }"
)
REMOVE_PROBE = (
    "function () { const node = window.__uiautomaWaitNode;"
    " if (!node) return 'no-node';"
    " if (node.parentNode) node.remove();"
    " return !!document.getElementById('uiautoma-wait-target'); }"
)
SCHEDULE_REINSERT = (
    "function (element, args) {"
    " const node = window.__uiautomaWaitNode;"
    " if (!node) return 'no-node';"
    " const parent = document.body;"
    " node.remove();"
    " setTimeout(function () { parent.appendChild(node); }, args.delay);"
    " return {removed: !document.getElementById('uiautoma-wait-target'), delay: args.delay}; }"
)
CREATE_HIDDEN_PROBE = (
    "function () {"
    " const old = document.getElementById('uiautoma-hidden-target'); if (old) old.remove();"
    " const node = document.createElement('div');"
    " node.id = 'uiautoma-hidden-target'; node.textContent = '隐藏目标';"
    " node.style.cssText = 'display:none';"
    " document.body.appendChild(node);"
    " return {display: getComputedStyle(node).display, clientRects: node.getClientRects().length}; }"
)
CLEANUP_PROBES = (
    "function () {"
    " ['uiautoma-wait-target', 'uiautoma-hidden-target'].forEach(function (id) {"
    "   const node = document.getElementById(id); if (node) node.remove(); });"
    " delete window.__uiautomaWaitNode;"
    " return true; }"
)
SET_SEARCH = (
    "function (element, args) {"
    " const input = document.querySelector('#home-search');"
    " if (!input) return 'no-input';"
    " const setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;"
    " setter.call(input, args.value);"
    " input.dispatchEvent(new Event('input', { bubbles: true }));"
    " return input.value; }"
)
SEARCH_STATE = (
    "function () { return {cards: document.querySelectorAll('[id^=\"menu-\"]').length,"
    "   target: !!document.querySelector('#menu-anchor-test')}; }"
)
DELAYED_STATE = (
    "function () { return {"
    "   state: (document.getElementById('delayed-state') || {}).textContent || null,"
    "   cycles: (document.getElementById('delayed-cycles') || {}).textContent || null,"
    "   created: (document.getElementById('delayed-created-count') || {}).textContent || null,"
    "   createdAttr: (document.getElementById('delayed-host') || {getAttribute: function () { return null; }})"
    "     .getAttribute('data-created-count'),"
    "   inDom: !!document.getElementById('delayed-target')}; }"
)


def presence(page, selector: str) -> bool:
    try:
        return len(page.find_all_by_css(selector, timeout=0)) > 0
    except Exception:  # noqa: BLE001
        return False


def wait_presence(page, selector: str, want: bool, timeout: float):
    """等待（或确认）元素存在性；返回耗时秒数或 None。"""
    started = time.monotonic()
    while time.monotonic() - started < timeout:
        if presence(page, selector) is want:
            return round(time.monotonic() - started, 3)
        time.sleep(0.15)
    return None


def result(case_id: str, status: str, detail: str, **extra):
    return {"case_id": case_id, "status": status, "detail": detail, **extra}


def exception_name(exc: BaseException) -> str:
    return type(exc).__name__


def error_detail(prefix: str, exc: BaseException) -> str:
    trace_info = str(getattr(exc, "trace_info", "") or "")
    return f"{prefix}: {exception_name(exc)}: {exc}" + (f" [trace={trace_info}]" if trace_info else "")


def check_contract():
    method = getattr(WebBrowser, "wait_appear", None)
    sig = inspect.signature(method) if callable(method) else None
    if sig is None:
        return result("api_contract", "FAIL", "WebBrowser.wait_appear 不存在")
    parameters = list(sig.parameters.values())
    names = tuple(sig.parameters)
    ok = (
        names == ("self", "selector_or_element", "timeout")
        and parameters[1].kind is inspect.Parameter.POSITIONAL_OR_KEYWORD
        and parameters[1].default is inspect.Parameter.empty
        and parameters[2].kind is inspect.Parameter.POSITIONAL_OR_KEYWORD
        and parameters[2].default == 20
        and str(sig.return_annotation) == "bool"
    )
    return result(
        "api_contract", "PASS" if ok else "FAIL",
        "selector_or_element 必填、timeout 位置或关键字且默认 20、返回注解 bool" if ok
        else f"公开签名不符合合同: {sig}")


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
            return result(label, "FAIL", f"耗时过长：{elapsed}s > {max_elapsed}s（应当立即拒绝）",
                          elapsed_s=elapsed, **extra)
        return result(label, "PASS", f"{exception_name(exc)} 正确拒绝（{elapsed}s）：{text}",
                      elapsed_s=elapsed, **extra)
    except Exception as exc:  # noqa: BLE001
        return result(label, "FAIL",
                      f"拒绝类型错误，应为 {expected_type.__name__}: {exception_name(exc)}: {exc}", **extra)
    return result(label, "FAIL", "调用未被拒绝", **extra)


def timed_wait(call):
    """执行一次 wait_appear，返回 (结果, 耗时, 异常文本或空)。"""
    started = time.perf_counter()
    try:
        value = call()
    except Exception as exc:  # noqa: BLE001
        return None, round(time.perf_counter() - started, 3), error_detail("调用失败", exc)
    return value, round(time.perf_counter() - started, 3), ""


def reachable(url: str, timeout: float = 8) -> tuple[bool, str]:
    try:
        with urllib.request.urlopen(urllib.request.Request(url, method="GET"), timeout=timeout) as response:
            return response.status == 200, f"HTTP {response.status}"
    except urllib.error.HTTPError as exc:
        return False, f"HTTP {exc.code}"
    except Exception as exc:  # noqa: BLE001
        return False, f"{type(exc).__name__}: {exc}"


def run(args):
    results = [check_contract()]
    if results[-1]["status"] != "PASS" or args.contract_only:
        return results, 0 if results[-1]["status"] == "PASS" else 1

    run_id = uuid.uuid4().hex
    work_dir = LIB_TMP_ROOT / run_id
    copy_dir = work_dir / "lib"
    package = None
    page = None
    extra_page = None
    page_id = ""
    source = args.transition_source
    try:
        try:
            baseline = web.get_all(mode=args.mode)
            results.append(result(
                "environment_baseline", "PASS",
                f"进入时浏览器共 {len(baseline)} 个标签", tabs=len(baseline)))
        except Exception as exc:  # noqa: BLE001
            results.append(result("environment_baseline", "BLOCKED", error_detail("无法读取标签列表", exc)))
            return results, 2

        # 转变来源选择
        available, note = (reachable(args.delayed_page_url)
                           if source in {"auto", "delayed-page"} else (False, "未探测"))
        if source == "auto":
            source = "delayed-page" if available else "scheduled"
            results.append(result(
                "transition_source", "PASS",
                f"自动选择：靶场自计时页 " + (f"可达（{note}）→ 使用 delayed-page（页面自己计时）"
                                             if available
                                             else f"不可用（{note}）→ 回退 scheduled（测试侧调度转变）"),
                delayed_page_available=available, source=source))
        elif source == "delayed-page" and not available:
            results.append(result(
                "transition_source", "BLOCKED",
                f"指定 delayed-page，但 {args.delayed_page_url} 不可用（{note}）；"
                f"请先在靶场部署该页面，或改用 --transition-source scheduled",
                delayed_page_available=False))
            return results, 2
        else:
            results.append(result(
                "transition_source", "PASS", f"使用 {source}（自计时页可达性：{note}）", source=source))

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
            page = web.create(args.home_url, mode=args.mode, load_timeout=args.load_timeout)
            page_id = page_key(page)
            baseline_matches = count_key(page_id, args.mode)
            ok = isinstance(page, WebBrowser)
            results.append(result(
                "page_prepare", "PASS" if ok else "FAIL",
                "已打开靶场首页" if ok else f"返回对象异常: {page!r}", url=page.get_url()))
            if not ok:
                return results, 1
        except Exception as exc:  # noqa: BLE001
            results.append(result("page_prepare", "BLOCKED", error_detail("无法打开靶场首页", exc)))
            return results, 2

        if source == "delayed-page":
            # ---------- 靶场自计时页：页面自己计时，测试侧零调度 ----------
            element = None
            try:
                page.navigate(args.delayed_page_url, load_timeout=args.load_timeout)
                appeared = wait_presence(page, DELAYED_TARGET, True, 8)
                element = page.find_by_css(DELAYED_TARGET, timeout=5)
                results.append(result(
                    "delayed_page_target_bound", "PASS" if (appeared is not None and element) else "FAIL",
                    f"已打开自计时页并绑定 {DELAYED_TARGET}（等出现用了 {appeared}s，{element.id}）"
                    if appeared is not None else
                    f"{DELAYED_TARGET} 未在 8s 内出现，页面可能未按预期自计时"))
                if appeared is None:
                    return results, 1
            except Exception as exc:  # noqa: BLE001
                results.append(result("delayed_page_target_bound", "FAIL",
                                      error_detail("自计时页准备失败", exc)))
                return results, 1

            # 观察页面自己的切换节奏，并用 DOM 计数实证「同一个节点」
            timeline, last = [], presence(page, DELAYED_TARGET)
            started = time.monotonic()
            while time.monotonic() - started < 4.5:
                now = presence(page, DELAYED_TARGET)
                if now != last:
                    timeline.append((round(time.monotonic() - started, 2), "present" if now else "absent"))
                    last = now
                time.sleep(0.15)
            state = page.execute_javascript(DELAYED_STATE)
            ok = len(timeline) >= 2
            results.append(result(
                "delayed_page_self_timed", "PASS" if ok else "FAIL",
                f"页面自己按周期切换（4.5s 内观测到 {len(timeline)} 次变化：{timeline}），测试侧零调度" if ok
                else f"4.5s 内未见切换：timeline={timeline}, state={state!r}"))
            ok_single = str(state.get("created")) == "1" and str(state.get("createdAttr")) == "1"
            results.append(result(
                "delayed_page_single_node", "PASS" if ok_single else "FAIL",
                f"节点只创建过一次（#delayed-created-count={state.get('created')}、"
                f"#delayed-host[data-created-count]={state.get('createdAttr')}、"
                f"已切换 {state.get('cycles')} 轮）——保证旧 element_id 能在重新出现后被认领"
                if ok_single else
                f"节点创建次数异常，可能存在重建：state={state!r}"))

            appeared = wait_presence(page, DELAYED_TARGET, True, 4)
            value, elapsed, error = timed_wait(lambda: page.wait_appear(element, 5))
            ok = value is True and elapsed < 1.0
            results.append(result(
                "present_returns_true_at_once", "PASS" if ok else "FAIL",
                f"元素已存在时返回 True（{elapsed}s，未等待）" if ok else
                f"结果不符: value={value!r}, elapsed={elapsed}s, error={error or '无'}", elapsed_s=elapsed))

            gone = wait_presence(page, DELAYED_TARGET, False, 4)
            value, elapsed, error = timed_wait(lambda: page.wait_appear(element, 1))
            ok = gone is not None and value is False and elapsed >= 0.9
            results.append(result(
                "absent_returns_false_at_timeout", "PASS" if ok else "FAIL",
                f"页面移除元素后（确认 absent 用时 {gone}s）等满 1s 返回 False（实测 {elapsed}s）" if ok else
                f"结果不符: value={value!r}, elapsed={elapsed}s, gone={gone}, error={error or '无'}",
                elapsed_s=elapsed))

            gone = wait_presence(page, DELAYED_TARGET, False, 4)
            value, elapsed, error = timed_wait(lambda: page.wait_appear(element, 0))
            ok = value is False and elapsed < 0.6
            results.append(result(
                "absent_timeout_zero_no_wait", "PASS" if ok else "FAIL",
                f"timeout=0 且元素已被移除时立即返回 False（{elapsed}s，不等待）" if ok else
                f"结果不符: value={value!r}, elapsed={elapsed}s, error={error or '无'}", elapsed_s=elapsed))

            # 核心正向：页面自己让它重新出现，测试侧不做任何调度
            gone = wait_presence(page, DELAYED_TARGET, False, 4)
            value, elapsed, error = timed_wait(lambda: page.wait_appear(element, 6))
            ok = gone is not None and value is True and 0.3 <= elapsed <= 4.0
            results.append(result(
                "appears_during_wait", "PASS" if ok else "FAIL",
                f"等待期间**页面自己**把同一节点重新挂回（确认 absent 用时 {gone}s）：返回 True，"
                f"耗时 {elapsed}s —— 测试侧零调度，这是 canonical 的等待出现路径" if ok else
                f"结果不符: value={value!r}, elapsed={elapsed}s, gone={gone}, error={error or '无'}",
                elapsed_s=elapsed, scheduled_delay=None))

            gone = wait_presence(page, DELAYED_TARGET, False, 4)
            value, elapsed, error = timed_wait(lambda: page.wait_appear(element, -1))
            ok = value is True and elapsed <= 6.0
            results.append(result(
                "infinite_timeout_returns_on_appear", "PASS" if ok else "FAIL",
                f"timeout=-1 在页面自己让它出现后返回 True（{elapsed}s），未无限阻塞" if ok else
                f"结果不符: value={value!r}, elapsed={elapsed}s, error={error or '无'}", elapsed_s=elapsed))

            # 其余用例回到常规页执行
            page.navigate(args.home_url, load_timeout=args.load_timeout)
            time.sleep(0.6)
            try:
                page.execute_javascript(CREATE_PROBE)
                probe_element = page.find_by_css(PROBE_SELECTOR, timeout=5)
                hidden_state = page.execute_javascript(CREATE_HIDDEN_PROBE)
                hidden_element = page.find_by_css(HIDDEN_SELECTOR, timeout=2)
                value, elapsed, error = timed_wait(lambda: page.wait_appear(hidden_element, 1))
                ok = value is True
                results.append(result(
                    "hidden_still_present", "PASS" if ok else "FAIL",
                    f"隐藏节点（{hidden_state!r}）仍判为「存在」：返回 True（{elapsed}s）——"
                    f"本 API 按 DOM 存在性判定，不区分可见性" if ok else
                    f"结果不符: value={value!r}, elapsed={elapsed}s, hidden={hidden_state!r}",
                    elapsed_s=elapsed))
                card = page.find_by_css(CARD_SELECTOR, timeout=5)
                page.execute_javascript(SET_SEARCH, {"value": "坐标"})
                time.sleep(0.4)
                state_absent = page.execute_javascript(SEARCH_STATE)
                value_absent, _, _ = timed_wait(lambda: page.wait_appear(card, 0))
                page.execute_javascript(SET_SEARCH, {"value": ""})
                time.sleep(0.4)
                card_back = page.find_by_css(CARD_SELECTOR, timeout=5)
                value_after, elapsed_after, _err = timed_wait(lambda: page.wait_appear(card, 2))
                results.append(result(
                    "recreated_node_not_matched", "KNOWN",
                    f"React 销毁并重建同形节点后，旧 WebElement 引用仍返回 {value_after!r}"
                    f"（过程：按标题过滤后 {state_absent}，旧引用返回 {value_absent!r}；"
                    f"过滤清除后同形节点重新出现，重新 find 得到新 id={card_back.id} 可用，"
                    f"旧 id={card.id} 不再生效）。即 WebElement 目标按**节点身份**绑定，"
                    f"节点被销毁重建后不会被旧引用认领——属 API 语义边界，不计入退出码。",
                    old_element_id=str(card.id), new_element_id=str(card_back.id),
                    value_after_recreate=value_after, elapsed_s=elapsed_after))
            except Exception as exc:  # noqa: BLE001
                results.append(result("delayed_page_extra_cases", "FAIL",
                                      error_detail("自计时页模式下的附加用例失败", exc)))
            element = None

        # ---------- WebElement 目标（调度式：测试侧注入探针节点） ----------
        element = None
        if source == "scheduled":
            try:
                created = page.execute_javascript(CREATE_PROBE)
                element = page.find_by_css(PROBE_SELECTOR, timeout=5)
                ok = bool(created) and isinstance(element, WebElement)
                results.append(result(
                    "probe_target_bound", "PASS" if ok else "FAIL",
                    f"已注入稳定探针节点 {PROBE_SELECTOR} 并绑定为 WebElement（{element.id}）" if ok else
                    f"注入/绑定失败: created={created!r}, element={element!r}"))
                if not ok:
                    return results, 1
            except Exception as exc:  # noqa: BLE001
                results.append(result("probe_target_bound", "FAIL", error_detail("探针节点准备失败", exc)))
                return results, 1

            value, elapsed, error = timed_wait(lambda: page.wait_appear(element, 5))
            ok = value is True and elapsed < 1.0
            results.append(result(
                "present_returns_true_at_once", "PASS" if ok else "FAIL",
                f"元素已存在时返回 True（{elapsed}s，未等待）" if ok else
                f"结果不符: value={value!r}, elapsed={elapsed}s, error={error or '无'}", elapsed_s=elapsed))

            removed = page.execute_javascript(REMOVE_PROBE)
            value, elapsed, error = timed_wait(lambda: page.wait_appear(element, 2))
            ok = value is False and elapsed >= 1.8
            results.append(result(
                "absent_returns_false_at_timeout", "PASS" if ok else "FAIL",
                f"元素不存在（{removed!r}）时等满 2s 超时返回 False（实测 {elapsed}s）" if ok else
                f"结果不符: value={value!r}, elapsed={elapsed}s, removed={removed!r}, error={error or '无'}",
                elapsed_s=elapsed))

            value, elapsed, error = timed_wait(lambda: page.wait_appear(element, 0))
            ok = value is False and elapsed < 0.6
            results.append(result(
                "absent_timeout_zero_no_wait", "PASS" if ok else "FAIL",
                f"timeout=0 且元素不存在时立即返回 False（{elapsed}s，不等待）" if ok else
                f"结果不符: value={value!r}, elapsed={elapsed}s, error={error or '无'}", elapsed_s=elapsed))

            # 核心正向：等待期间元素出现（同一节点原样插回）
            schedule = page.execute_javascript(SCHEDULE_REINSERT, {"delay": int(TRANSITION_DELAY * 1000)})
            value, elapsed, error = timed_wait(lambda: page.wait_appear(element, 8))
            ok = schedule != "no-node" and value is True and TRANSITION_DELAY - 0.2 <= elapsed <= 4.0
            results.append(result(
                "appears_during_wait", "PASS" if ok else "FAIL",
                f"等待期间元素出现（同一节点在 {TRANSITION_DELAY}s 后插回，调度={schedule!r}）：返回 True，"
                f"耗时 {elapsed}s，确实等到出现才返回" if ok else
                f"结果不符: value={value!r}, elapsed={elapsed}s, schedule={schedule!r}, error={error or '无'}",
                elapsed_s=elapsed, scheduled_delay=TRANSITION_DELAY))

            page.execute_javascript(SCHEDULE_REINSERT, {"delay": int(TRANSITION_DELAY * 1000)})
            value, elapsed, error = timed_wait(lambda: page.wait_appear(element, -1))
            ok = value is True and elapsed <= 5.0
            results.append(result(
                "infinite_timeout_returns_on_appear", "PASS" if ok else "FAIL",
                f"timeout=-1 在元素出现后返回 True（{elapsed}s），未无限阻塞" if ok else
                f"结果不符: value={value!r}, elapsed={elapsed}s, error={error or '无'}", elapsed_s=elapsed))

            # 存在性判定不区分可见性
            hidden_element = None
            hidden_state = None
            try:
                hidden_state = page.execute_javascript(CREATE_HIDDEN_PROBE)
                hidden_element = page.find_by_css(HIDDEN_SELECTOR, timeout=2)
            except Exception as exc:  # noqa: BLE001
                results.append(result("hidden_still_present", "FAIL",
                                      error_detail("隐藏节点绑定失败", exc)))
            if hidden_element is not None:
                value, elapsed, error = timed_wait(lambda: page.wait_appear(hidden_element, 1))
                ok = value is True
                results.append(result(
                    "hidden_still_present", "PASS" if ok else "FAIL",
                    f"隐藏节点（{hidden_state!r}）仍判为「存在」：返回 True（{elapsed}s）——"
                    f"本 API 按 DOM 存在性判定，不区分可见性" if ok else
                    f"结果不符: value={value!r}, elapsed={elapsed}s, hidden={hidden_state!r}",
                    elapsed_s=elapsed))

            # React 销毁重建的节点不会被旧引用认领（语义边界）
            try:
                card = page.find_by_css(CARD_SELECTOR, timeout=5)
                page.execute_javascript(SET_SEARCH, {"value": "坐标"})
                time.sleep(0.4)
                state_absent = page.execute_javascript(SEARCH_STATE)
                value_absent, _, _ = timed_wait(lambda: page.wait_appear(card, 0))
                page.execute_javascript(SET_SEARCH, {"value": ""})
                time.sleep(0.4)
                card_back = page.find_by_css(CARD_SELECTOR, timeout=5)
                value_after, elapsed_after, error_after = timed_wait(lambda: page.wait_appear(card, 2))
                results.append(result(
                    "recreated_node_not_matched", "KNOWN",
                    f"React 销毁并重建同形节点后，旧 WebElement 引用仍返回 {value_after!r}"
                    f"（过程：按标题过滤后 {state_absent}，旧引用返回 {value_absent!r}；"
                    f"过滤清除后同形节点重新出现，重新 find 得到新 id={card_back.id} 可用，"
                    f"旧 id={card.id} 不再生效）。即 WebElement 目标按**节点身份**绑定，"
                    f"节点被销毁重建后不会被旧引用认领——属 API 语义边界，不计入退出码。",
                    old_element_id=str(card.id), new_element_id=str(card_back.id),
                    value_after_recreate=value_after, elapsed_s=elapsed_after))
            except Exception as exc:  # noqa: BLE001
                results.append(result("recreated_node_not_matched", "KNOWN",
                                      f"未能构造该场景：{exception_name(exc)}: {exc}"))

        # ---------- 名称 / Selector 目标 ----------
        page.navigate(args.home_url, load_timeout=args.load_timeout)
        time.sleep(0.5)
        # 预热：导航后页面运行时需要重新安装，否则首次 DOM 查询可能撞上
        # page_runtime_probe_timeout（该瞬时失败会让 wait_appear 直接报错，见 KNOWN 项）。
        warmup_error = ""
        try:
            page.find_all_by_css("html", timeout=8)
        except Exception as exc:  # noqa: BLE001
            warmup_error = error_detail("预热查询失败", exc)
        time.sleep(0.3)

        library_page_url = args.home_url.rstrip("/") + "/#/iframe-shadow-form"

        def reset_page_context(url: str | None = None, settle: float = 0.8):
            """导航到指定页并预热：跨源/路由切换后框架绑定可能失效，需要一次干净导航恢复。"""
            try:
                page.navigate(url or args.home_url, load_timeout=args.load_timeout)
                time.sleep(settle)
                page.find_all_by_css("html", timeout=8)
            except Exception:  # noqa: BLE001
                pass

        if args.skip_name_cases:
            results.append(result(
                "name_cases_skipped", "KNOWN",
                "按 --skip-name-cases 跳过名称/Selector 用例（元素库保存路径绑定部署域名，"
                "本地 localhost 运行无法命中；规范做法是等自计时页部署后用同源运行）。"
                "本行不计入退出码。"))
        else:
            def wait_name_absent(attempts: int = 3):
                """名称在本页不存在 → 期望等满超时返回 False；瞬时轮询错误时重试并记录。"""
                notes = []
                last_elapsed = 0.0
                for index in range(1, attempts + 1):
                    value, last_elapsed, error = timed_wait(lambda: page.wait_appear(ELEMENT_NAME, 2))
                    if error == "":
                        return value, last_elapsed, "", notes
                    notes.append(f"第 {index} 次: {error}（{last_elapsed}s）")
                    reset_page_context()
                return None, last_elapsed, notes[-1], notes

            value, elapsed, error, transient = wait_name_absent()
            ok = value is False and elapsed >= 1.8
            results.append(result(
                "name_on_wrong_page_false", "PASS" if ok else "FAIL",
                (f"库中存在但本页不存在的名称：等满 2s 返回 False（实测 {elapsed}s）"
                 + (f"；期间出现瞬时轮询错误并重试成功：{transient}" if transient else "")) if ok else
                f"结果不符: value={value!r}, elapsed={elapsed}s, error={error or '无'}, "
                f"预热={warmup_error or '正常'}",
                elapsed_s=elapsed, transient_attempts=transient))
            if transient:
                results.append(result(
                    "transient_poll_error_aborts_wait", "KNOWN",
                    f"内部轮询一旦失败，wait_appear 会**立即以错误结束**而不是继续等到超时：本次观测到 "
                    f"{'; '.join(transient)}（trace=page_runtime_probe_timeout，出现在页面刚导航完、"
                    f"页面运行时正在重装时）。此前在路由切换场景还观测到 frame_not_found 同类现象。"
                    f"对调用方而言，超时前的一次瞬时失败会变成异常，属健壮性问题；"
                    f"本行不计入退出码，待维护者决定。",
                    transient_attempts=transient))

            # 名称目标：等待期间由页面自身的路由切换让库元素出现。
            # 用「navigate(load_timeout=0) 不等待加载 → 立刻 wait_appear」这一自然用法，
            # 不依赖测试侧调度 JS（此前用 execute_javascript 调度 hash 切换会在等待中撞坏框架绑定）。
            route_attempts = []
            value, elapsed, error = None, 0.0, ""
            for attempt in range(1, 3):
                if attempt > 1:
                    reset_page_context(1.0)
                try:
                    page.navigate(library_page_url, load_timeout=0)
                except Exception as exc:  # noqa: BLE001
                    route_attempts.append(f"第 {attempt} 次 navigate 失败: {error_detail('', exc)}")
                    continue
                value, elapsed, error = timed_wait(lambda: page.wait_appear(ELEMENT_NAME, 8))
                if error == "":
                    break
                route_attempts.append(f"第 {attempt} 次: {error}（{elapsed}s）")
            ok = value is True and 0.05 <= elapsed <= 4.0
            results.append(result(
                "name_appears_after_route_change", "PASS" if ok else "FAIL",
                (f"库元素所属页尚未加载时即开始等待（navigate load_timeout=0，元素此刻仍不存在）："
                 f"路由切换完成后返回 True，耗时 {elapsed}s，说明真的等到了出现"
                 + (f"；期间重试：{'; '.join(route_attempts)}" if route_attempts else "")) if ok else
                f"结果不符: value={value!r}, elapsed={elapsed}s, error={error or '无'}"
                + (f"，重试记录：{route_attempts}" if route_attempts else ""),
                elapsed_s=elapsed, retry_notes=route_attempts))
            if route_attempts:
                results.append(result(
                    "route_change_frame_flake", "KNOWN",
                    f"路由切换期间等待曾失败并重试：{'; '.join(route_attempts)}；"
                    f"一次干净 navigate 即可恢复，重试后通过。历史记录：用 execute_javascript 调度 "
                    f"hash 切换时更易触发 frame_not_found，故已改为 navigate(load_timeout=0) 的自然写法。"
                    f"本行不计入退出码。",
                    retry_notes=route_attempts))

            reset_page_context(library_page_url, 1.0)
            value, elapsed, error = timed_wait(lambda: page.wait_appear(ELEMENT_NAME, 5))
            ok = value is True and elapsed < 1.5
            results.append(result(
                "name_present_returns_true_at_once", "PASS" if ok else "FAIL",
                f"名称目标已在当前页（库元素所属路由）：返回 True（{elapsed}s）" if ok else
                f"结果不符: value={value!r}, elapsed={elapsed}s, error={error or '无'}", elapsed_s=elapsed))

            try:
                selector = package.selector(ELEMENT_NAME)
                value, elapsed, error = timed_wait(lambda: page.wait_appear(selector, 5))
                ok = value is True
                results.append(result(
                    "selector_target_present", "PASS" if ok else "FAIL",
                    f"Selector 目标（package.selector）返回 True（{elapsed}s）" if ok else
                    f"结果不符: value={value!r}, error={error or '无'}", elapsed_s=elapsed))
            except Exception as exc:  # noqa: BLE001
                results.append(result("selector_target_present", "FAIL",
                                      error_detail("Selector 目标失败", exc)))

            results.append(expect_raises(
                lambda: page.wait_appear(CARD_SELECTOR, 2), ActionError, "css_string_treated_as_name",
                message_contains="未找到选择器", max_elapsed=1.0))
        results.append(expect_raises(
            lambda: page.wait_appear("__uiautoma_not_exist__", 2), ActionError, "unknown_name_rejected",
            message_contains="未找到选择器", max_elapsed=1.0))

        # 参数校验
        results.append(expect_raises(
            lambda: page.wait_appear(ELEMENT_NAME, -2), InvalidParamsError, "timeout_negative",
            message_contains="-1", max_elapsed=1.0))
        results.append(expect_raises(
            lambda: page.wait_appear(ELEMENT_NAME, "x"), InvalidParamsError, "timeout_non_numeric",
            message_contains="秒数", max_elapsed=1.0))
        results.append(expect_raises(
            lambda: page.wait_appear(None, 1), InvalidParamsError, "target_none",
            message_contains="元素名称字符串", max_elapsed=1.0))
        results.append(expect_raises(
            lambda: page.wait_appear(123, 1), InvalidParamsError, "target_int",
            message_contains="元素名称字符串", max_elapsed=1.0))
        results.append(expect_raises(
            lambda: page.wait_appear(ELEMENT_NAME, 1, "extra"), TypeError, "extra_positional",
            max_elapsed=1.0))
        results.append(expect_raises(
            lambda: page.wait_appear(), TypeError, "missing_target", max_elapsed=1.0))

        # 清理探针节点后关闭页面
        try:
            page.execute_javascript(CLEANUP_PROBES)
        except Exception:  # noqa: BLE001
            pass
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
            lambda: page.wait_appear(ELEMENT_NAME, 1), ActionError, "after_page_close",
            max_elapsed=3.0))
        page = None

        # 关闭 Package 后，名称目标应在 SDK 侧被拒绝
        try:
            package.close()
            results.append(result("package_close_verified", "PASS", "Package 已关闭"))
        except Exception as exc:  # noqa: BLE001
            results.append(result("package_close_verified", "FAIL", error_detail("Package 关闭失败", exc)))
        package = None
        try:
            extra_page = web.create(args.home_url, mode=args.mode, load_timeout=args.load_timeout)
        except Exception as exc:  # noqa: BLE001
            results.append(result("no_package_rejected", "BLOCKED", error_detail("无法新建页面", exc)))
        else:
            results.append(expect_raises(
                lambda: extra_page.wait_appear(ELEMENT_NAME, 1), NoCurrentPackageError, "no_package_rejected",
                message_contains="Package", max_elapsed=2.0))
            try:
                extra_page.close(ignore_beforeunload=True)
                extra_page = None
            except Exception:  # noqa: BLE001
                pass
    except Exception as exc:  # noqa: BLE001
        results.append(result("scenario", "FAIL", error_detail("wait_appear 场景执行失败", exc)))
    finally:
        close_error = ""
        for holder in ("page", "extra_page"):
            target = locals().get(holder)
            if target is not None:
                try:
                    target.close(ignore_beforeunload=True)
                    if holder == "extra_page":
                        extra_page = None
                except Exception as exc:  # noqa: BLE001
                    close_error = close_error or f"{exception_name(exc)}: {exc}"
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
    parser = argparse.ArgumentParser(description="WebBrowser.wait_appear() 页面对象 API 验收")
    parser.add_argument("--home-url", default=HOME_URL, help="靶场首页")
    parser.add_argument("--delayed-page-url", default=DELAYED_PAGE_URL,
                        help="靶场自计时页（每 1.5s 交替插入/移除同一个 #delayed-target）")
    parser.add_argument("--library", type=Path, default=DEFAULT_LIBRARY, help="元素库目录")
    parser.add_argument("--mode", choices=("chrome", "edge"), default="chrome")
    parser.add_argument("--load-timeout", type=float, default=20)
    parser.add_argument("--transition-source", choices=("auto", "scheduled", "delayed-page"), default="auto",
                        help="转变来源：auto 先探测靶场自计时页，不可用则回退 scheduled")
    parser.add_argument("--contract-only", action="store_true")
    parser.add_argument("--skip-name-cases", action="store_true",
                        help="跳过名称/Selector 用例（元素库绑定部署域名，本地 localhost 运行无法命中）")
    parser.add_argument("--json", action="store_true", help="在表格后额外输出 JSON 报告（用于归档验收产物）")
    args = parser.parse_args(argv)
    if args.load_timeout <= 0:
        parser.error("--load-timeout 必须大于 0")

    results, code = run(args)
    print("UIAutoma Web API 测试")
    print("API     : uiautoma.web.WebBrowser.wait_appear")
    print(f"页面    : {args.home_url}")
    print(f"元素库  : {args.library}")
    print(f"转变来源: --transition-source {args.transition_source}")
    print("进度     状态    测试项                  测试结果")
    print("────────────────────────────────────────────────────────────────────────")
    for index, current in enumerate(results, 1):
        status = current["status"]
        color = {"PASS": GREEN, "BLOCKED": YELLOW, "KNOWN": BLUE}.get(status, RED)
        label = {"PASS": "通过", "BLOCKED": "阻塞", "KNOWN": "边界"}.get(status, "失败")
        print(f"{index:02d}/{len(results):02d}    {color}[{label}]{RESET}  "
              f"{current['case_id']:<38}  {current['detail']}")
    print("────────────────────────────────────────────────────────────────────────")
    counted = [item for item in results if item["status"] != "KNOWN"]
    summary = "测试通过" if code == 0 else ("测试阻塞" if code == 2 else "测试失败")
    print(f"{summary} · {sum(item['status'] == 'PASS' for item in results)}/{len(counted)} 通过"
          f"（另 {sum(item['status'] == 'KNOWN' for item in results)} 项边界，不计入退出码）"
          f" · 退出码 {code}")
    if args.json:
        print(json.dumps({
            "api": "uiautoma.web.WebBrowser.wait_appear",
            "home_url": args.home_url, "library": str(args.library),
            "delayed_page_url": args.delayed_page_url, "mode": args.mode,
            "transition_source": args.transition_source,
            "status": "PASS" if code == 0 else ("BLOCKED" if code == 2 else "FAIL"),
            "exit_code": code, "results": results,
        }, ensure_ascii=False, indent=2))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
