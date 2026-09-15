"""WebBrowser.stop_load() 页面对象 API 专项验收。

靶场：维护者的官方靶场（测试侧不自建页面）。
- 常规页：`https://baobaomi900901.github.io/xpath/#/form-controls`
- 阻塞页：`https://baobaomi900901.github.io/xpath/slow-load-30s.html`
  （首次加载即进入同步 JS 死循环 `while(true)`，永远不会加载完成；默认不跑，见 `--include-hung-page`）

「停止加载成功」不能靠返回值判定（本 API 返回 `None`），因此脚本用**可观测状态**确证。
关键前提（本轮实测确立的判据区分）：

| 页面状态 | `is_load_completed()` | `execute_javascript()` | `close()` |
|---|---|---|---|
| 正常加载完成 | `True` | 正常返回 | 成功 |
| **待处理导航（加载中）** | `False` | **失败** | **失败** |
| Chrome 错误页 | `False`（见「已知发现」） | 正常返回（`readyState=complete`） | 成功 |

所以「`is_load_completed()=False`」不足以说明页面在加载中，必须同时要求
`execute_javascript()` 失败；反过来，「挂起已中止」也不能只看 `is_load_completed()`，
而应要求**页面重新可用**（`execute_javascript()` 恢复、`readyState` 回到 `complete`）。

核心正向场景：把页面**导航到连接永久挂起的地址**（保留地址 `10.255.255.1` /
`192.0.2.1`，不会应答），制造真实的「待处理网络请求」：`navigate` 必然超时、
`execute_javascript()` 失败、`close()` 也会失败；此时调用 `stop_load()`，要求挂起被中止、
页面恢复可用。该场景不修改靶场，中止后 Chrome 落到自身错误页，标签可正常回收，可重复运行。

状态模型：`PASS` / `FAIL` / `BLOCKED` 计入退出码；`KNOWN` 表示已如实刻画、但**不由本 API 负责**
的边界或发现（不计入退出码）。

退出码：0 = 全部 PASS（允许 KNOWN）；1 = 存在 FAIL；2 = 无非 FAIL 但存在 BLOCKED。
"""
from __future__ import annotations

import argparse
import inspect
import json
import time

from uiautoma import ActionError, UIAError, web
from uiautoma.web import WebBrowser

__test__ = False

DEFAULT_URL = "https://baobaomi900901.github.io/xpath/#/form-controls"
HUNG_PAGE_URL = "https://baobaomi900901.github.io/xpath/slow-load-30s.html"
HANG_URLS = ("http://10.255.255.1/uiautoma-slow.html", "http://192.0.2.1/uiautoma-slow.html")
REFUSED_URL = "http://127.0.0.1:9/uiautoma-error-page.html"
GREEN, RED, YELLOW, BLUE, RESET = "\x1b[92m", "\x1b[91m", "\x1b[93m", "\x1b[94m", "\x1b[0m"

READY_STATE_JS = (
    "function () { const list = performance.getEntriesByType('navigation') || [];"
    " const nav = list[0] || {};"
    " return {readyState: document.readyState, href: location.href,"
    "   loadEventEnd: Math.round(nav.loadEventEnd || 0), navCount: list.length}; }"
)


def result(case_id: str, status: str, detail: str, **extra):
    return {"case_id": case_id, "status": status, "detail": detail, **extra}


def exception_name(exc: BaseException) -> str:
    return type(exc).__name__


def error_detail(prefix: str, exc: BaseException) -> str:
    trace_info = str(getattr(exc, "trace_info", "") or "")
    return f"{prefix}: {exception_name(exc)}: {exc}" + (f" [trace={trace_info}]" if trace_info else "")


def check_contract():
    method = getattr(WebBrowser, "stop_load", None)
    sig = inspect.signature(method) if callable(method) else None
    if sig is None:
        return result("api_contract", "FAIL", "WebBrowser.stop_load 不存在")
    names = tuple(sig.parameters)
    ok = names == ("self",) and str(sig.return_annotation) == "None"
    return result(
        "api_contract", "PASS" if ok else "FAIL",
        "无任何参数；返回注解 None" if ok else f"公开签名不符合合同: {sig}")


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


def probe(page):
    """采集 (is_load_completed, JS 是否可用, readyState, url)。"""
    try:
        loaded = page.is_load_completed()
    except Exception as exc:  # noqa: BLE001
        loaded = f"{exception_name(exc)}"
    js_ok, ready_state = False, ""
    try:
        value = page.execute_javascript(READY_STATE_JS)
        js_ok = isinstance(value, dict)
        ready_state = str(value.get("readyState") or "") if js_ok else ""
    except Exception:  # noqa: BLE001
        js_ok = False
    try:
        url = str(page.get_url())
    except Exception as exc:  # noqa: BLE001
        url = f"<{exception_name(exc)}>"
    return loaded, js_ok, ready_state, url


def wait_usable(page, timeout: float):
    """等待页面重新可用（JS 可调用且 readyState=complete）。"""
    started = time.monotonic()
    deadline = started + timeout
    state = probe(page)
    while time.monotonic() < deadline:
        state = probe(page)
        if state[1] and state[2] == "complete":
            return True, round(time.monotonic() - started, 2), state
        time.sleep(0.25)
    return False, round(time.monotonic() - started, 2), state


def wait_loaded(page, timeout: float):
    """等待 is_load_completed() 变为 True。"""
    started = time.monotonic()
    deadline = started + timeout
    state = probe(page)
    while time.monotonic() < deadline:
        state = probe(page)
        if state[0] is True:
            return True, round(time.monotonic() - started, 2), state
        time.sleep(0.25)
    return False, round(time.monotonic() - started, 2), state


def wait_stopped(page, timeout: float):
    """等待「加载不再进行」。

    首选 is_load_completed() 转为 True；若导航已落到 Chrome 错误页，该值恒为 False（见已知发现），
    此时退化为「页面已就绪（JS 可调用且 readyState=complete）」，同样说明挂起已结束。
    """
    stopped, waited, state = wait_loaded(page, timeout)
    if stopped:
        return True, waited, state, "is_load_completed() 转为 True"
    ready_ok, ready_waited, state = wait_usable(page, min(timeout, 4))
    if ready_ok:
        return True, round(waited + ready_waited, 2), state, \
            "页面已就绪（导航落到 Chrome 错误页，is_load_completed() 恒为 False，见已知发现）"
    return False, round(waited + ready_waited, 2), state, "既未转为 True，页面也不可用"


def new_tab_ids():
    try:
        return {str(getattr(item, "id", "") or "") for item in web.get_all(mode="chrome")}
    except Exception:  # noqa: BLE001
        return set()


def run(args):
    results = [check_contract()]
    if results[-1]["status"] != "PASS" or args.contract_only:
        return results, 0 if results[-1]["status"] == "PASS" else 1

    baseline_ids: set[str] = set()
    page = None
    page_id = ""
    try:
        try:
            baseline = web.get_all(mode=args.mode)
            baseline_ids = {str(getattr(item, "id", "") or "") for item in baseline}
            results.append(result(
                "environment_baseline", "PASS",
                f"进入时浏览器共 {len(baseline)} 个标签（用于收尾核对是否有孤儿标签）",
                tabs=len(baseline)))
        except Exception as exc:  # noqa: BLE001
            results.append(result("environment_baseline", "BLOCKED", error_detail("无法读取标签列表", exc)))
            return results, 2

        try:
            page = web.create(args.target_url, mode=args.mode, load_timeout=args.load_timeout)
            page_id = page.id
            ok = isinstance(page, WebBrowser)
            results.append(result(
                "page_prepare", "PASS" if ok else "FAIL",
                "已打开官方靶场页" if ok else f"返回对象异常: {page!r}", url=page.get_url()))
            if not ok:
                return results, 1
        except Exception as exc:  # noqa: BLE001
            results.append(result("page_prepare", "BLOCKED", error_detail("无法打开靶场页", exc)))
            return results, 2

        loaded, js_ok, ready_state, url = probe(page)
        ok = loaded is True and js_ok and ready_state == "complete"
        results.append(result(
            "baseline_load_completed", "PASS" if ok else "FAIL",
            f"基线：is_load_completed()=True、readyState=complete、JS 可用（{url}）" if ok else
            f"基线异常: loaded={loaded!r}, js_ok={js_ok}, readyState={ready_state!r}, url={url}"))
        if not ok:
            return results, 1

        # 目标用例 1：已加载完成的页面上调用 stop_load（应为无害幂等）
        started = time.perf_counter()
        try:
            returned = page.stop_load()
            elapsed = round(time.perf_counter() - started, 3)
            loaded, js_ok, ready_state, _url = probe(page)
            ok = returned is None and loaded is True and js_ok and ready_state == "complete"
            results.append(result(
                "noop_on_completed_page", "PASS" if ok else "FAIL",
                f"已加载完成的页面上 stop_load() 返回 None（{elapsed}s），页面状态不变"
                f"（is_load_completed()=True、readyState=complete、JS 可用）" if ok else
                f"结果不符: return={returned!r}, loaded={loaded!r}, readyState={ready_state!r}",
                elapsed_s=elapsed))
        except Exception as exc:  # noqa: BLE001
            results.append(result("noop_on_completed_page", "FAIL", error_detail("stop_load 调用失败", exc)))

        # 目标用例 2：连续多次调用
        try:
            values = [page.stop_load() for _ in range(3)]
            ok = all(value is None for value in values)
            results.append(result(
                "repeated_calls", "PASS" if ok else "FAIL",
                "连续 3 次 stop_load() 均返回 None" if ok else f"返回值异常: {values!r}"))
        except Exception as exc:  # noqa: BLE001
            results.append(result("repeated_calls", "FAIL", error_detail("连续调用失败", exc)))

        # 目标用例 3（核心正向）：挂起导航 → stop_load 中止 → 页面恢复可用
        # 待处理导航未释放时连 close() 都会失败，因此任何路径下都要先 stop_load 兜底。
        established = False
        try:
            hang_url = ""
            for candidate in HANG_URLS:
                started = time.perf_counter()
                try:
                    page.navigate(candidate, load_timeout=args.hang_timeout)
                    navigate_note = "navigate 意外成功"
                except Exception as exc:  # noqa: BLE001
                    navigate_note = f"{exception_name(exc)}: {exc}"
                hang_url, navigate_elapsed = candidate, round(time.perf_counter() - started, 3)
                loaded, js_ok, ready_state, url = probe(page)
                if loaded is False and not js_ok:
                    established = True
                    break
                if loaded is False and js_ok:
                    navigate_note += "（已落到错误页，非待处理导航）"
            if not established:
                results.append(result(
                    "abort_pending_navigation", "BLOCKED",
                    f"挂起地址 {hang_url} 未能制造「待处理导航」状态（navigate {navigate_elapsed}s："
                    f"{navigate_note}；is_load_completed={loaded!r}, js_ok={js_ok}）",
                    hang_url=hang_url))
            else:
                results.append(result(
                    "pending_navigation_established", "PASS",
                    f"已制造待处理网络请求：导航 {hang_url} 超时（{navigate_elapsed}s，{navigate_note}），"
                    f"is_load_completed()=False 且 execute_javascript() 失败（URL 仍为 {url!r}）",
                    hang_url=hang_url, elapsed_s=navigate_elapsed))
                started = time.perf_counter()
                try:
                    returned = page.stop_load()
                    stop_elapsed = round(time.perf_counter() - started, 3)
                except Exception as exc:  # noqa: BLE001
                    results.append(result("abort_pending_navigation", "FAIL",
                                          error_detail("stop_load 调用失败", exc)))
                else:
                    usable, waited, state = wait_usable(page, args.settle_timeout)
                    results.append(result(
                        "abort_pending_navigation", "PASS" if (returned is None and usable) else "FAIL",
                        f"stop_load() 返回 None（{stop_elapsed}s）后挂起导航被中止：页面在 {waited}s 内恢复可用"
                        f"（execute_javascript() 恢复、readyState=complete）"
                        f"；此时 is_load_completed()={state[0]!r}"
                        + ("（导航已落到 Chrome 错误页，该值恒为 False，见下方已知发现）"
                           if state[0] is False else "")
                        if (returned is None and usable) else
                        f"中止后未恢复可用: return={returned!r}, is_load_completed={state[0]!r}, "
                        f"js_ok={state[1]}, readyState={state[2]!r}",
                        elapsed_s=stop_elapsed, recovered=usable))
        finally:
            if established:
                try:
                    page.stop_load()
                except Exception:  # noqa: BLE001
                    pass

        # 目标用例 4：中止后页面仍可正常使用
        try:
            page.navigate(args.target_url, load_timeout=args.load_timeout)
            loaded, js_ok, ready_state, _url = probe(page)
            title = page.execute_javascript("function () { return document.title; }")
            ok = loaded is True and isinstance(title, str) and bool(title)
            results.append(result(
                "usable_after_stop", "PASS" if ok else "FAIL",
                f"中止后可正常导航回靶场页并读取标题（{title!r}），is_load_completed()=True" if ok else
                f"恢复异常: loaded={loaded!r}, js_ok={js_ok}, readyState={ready_state!r}, title={title!r}"))
        except Exception as exc:  # noqa: BLE001
            results.append(result("usable_after_stop", "FAIL", error_detail("中止后恢复失败", exc)))

        # 目标用例 5：create 超时后的标签状态（stop_if_timeout True / False）与 stop_load 的作用
        for stop_if_timeout in (True, False):
            case_id = ("create_stop_if_timeout_true" if stop_if_timeout
                       else "create_stop_if_timeout_false_then_stop")
            before_ids = new_tab_ids()
            started = time.perf_counter()
            try:
                web.create(hang_url, mode=args.mode, load_timeout=3, stop_if_timeout=stop_if_timeout)
                create_error = "create 意外成功"
            except UIAError as exc:
                create_error = f"{exception_name(exc)}: {exc}"
            except Exception as exc:  # noqa: BLE001
                create_error = f"{exception_name(exc)}: {exc}"
            create_elapsed = round(time.perf_counter() - started, 3)
            time.sleep(1.0)
            fresh = [item for item in web.get_all(mode=args.mode)
                     if str(getattr(item, "id", "") or "") not in before_ids]
            if len(fresh) != 1:
                results.append(result(
                    case_id, "FAIL",
                    f"应以 1 个新标签承载该地址，实际新增 {len(fresh)} 个（create {create_elapsed}s 报错：{create_error}）"))
                continue
            tab = fresh[0]
            loaded, js_ok, ready_state, url = probe(tab)
            if stop_if_timeout:
                # 引擎侧的停载可能晚于 SDK 的 3s 超时返回，因此等待而不是只探一次。
                stopped, waited, state, branch = wait_stopped(tab, args.settle_timeout)
                results.append(result(
                    case_id, "PASS" if stopped else "FAIL",
                    f"create(load_timeout=3, stop_if_timeout=True) 超时抛错（{create_error}）后，"
                    f"新标签在 {waited}s 内不再处于加载中（{branch}）：超时后确实自动停止了加载" if stopped else
                    f"超时后仍在加载: is_load_completed()={state[0]!r}, js_ok={state[1]}, "
                    f"readyState={state[2]!r}（create 报错：{create_error}）",
                    loaded=state[0], url=state[3]))
            else:
                pending = loaded is False and not js_ok
                stop_error = ""
                returned = None
                try:
                    returned = tab.stop_load()
                except Exception as exc:  # noqa: BLE001
                    stop_error = error_detail("stop_load 调用失败", exc)
                if stop_error:
                    results.append(result(case_id, "FAIL", stop_error))
                else:
                    # 该标签的首次导航被中止后可能落在新标签页 / about:blank（产品对这类页面
                    # 不支持脚本执行）或 Chrome 错误页（is_load_completed() 恒为 False），
                    # 因此统一用 wait_stopped() 判定「加载不再进行」，再要求标签可正常关闭。
                    stopped, waited, state, branch = wait_stopped(tab, args.settle_timeout)
                    closed = False
                    close_note = ""
                    try:
                        tab.close(ignore_beforeunload=True)
                        closed = True
                    except Exception as exc:  # noqa: BLE001
                        close_note = f"{exception_name(exc)}: {exc}"
                        stopped, waited, state, branch = wait_stopped(tab, args.settle_timeout)
                        try:
                            tab.close(ignore_beforeunload=True)
                            closed = True
                            close_note = ""
                        except Exception:  # noqa: BLE001
                            pass
                    ok = returned is None and stopped and closed
                    results.append(result(
                        case_id, "PASS" if ok else "FAIL",
                        f"默认 stop_if_timeout=False：create 超时（{create_error}）后标签"
                        + ("处于待处理导航（is_load_completed()=False、JS 不可用）" if pending
                           else "处于错误页")
                        + f"；stop_load() 返回 None，{waited}s 内加载不再进行（{branch}），标签可正常关闭"
                        if ok else
                        f"结果不符: pending={pending}, return={returned!r}, stopped={stopped}, "
                        f"closed={closed}, close_note={close_note or '无'}, branch={branch}, "
                        f"js_ok={state[1]}, is_load_completed={state[0]!r}",
                        loaded=state[0], pending=pending, usable=state[1], closed=closed))
                continue
            try:
                tab.close(ignore_beforeunload=True)
            except Exception as exc:  # noqa: BLE001
                results.append(result(case_id, "FAIL", error_detail("标签无法关闭", exc)))

        # 目标用例 6：页面关闭后立即拒绝
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
            lambda: page.stop_load(), ActionError, "stale_after_close",
            message_contains="失效", max_elapsed=3.0))
        page = None

        # 已知发现（不计入退出码）：Chrome 错误页上 is_load_completed() 恒为 False
        error_page = None
        try:
            error_page = web.create(args.target_url, mode=args.mode, load_timeout=args.load_timeout)
            try:
                error_page.navigate(REFUSED_URL, load_timeout=3)
            except Exception:  # noqa: BLE001
                pass
            time.sleep(1.0)
            loaded, js_ok, ready_state, url = probe(error_page)
            detail = error_page.execute_javascript(READY_STATE_JS)
            results.append(result(
                "error_page_is_load_completed_false", "KNOWN",
                f"Chrome 错误页（{url}）上页面实际 readyState={detail.get('readyState')!r}、"
                f"loadEventEnd={detail.get('loadEventEnd')}、navCount={detail.get('navCount')}、JS 可执行、标签可关闭，"
                f"但 is_load_completed() 仍为 {loaded!r} —— 该值在错误页上恒为 False；"
                f"这属于 is_load_completed()/wait_load_completed() 的问题，不由 stop_load 负责，"
                f"详见证据文档「已知发现」。此行不计入退出码。",
                ready_state=detail.get("readyState"), load_event_end=detail.get("loadEventEnd"),
                is_load_completed=loaded))
        except Exception as exc:  # noqa: BLE001
            results.append(result("error_page_is_load_completed_false", "KNOWN",
                                  f"未能构造错误页场景：{exception_name(exc)}: {exc}"))
        finally:
            if error_page is not None:
                try:
                    error_page.close(ignore_beforeunload=True)
                except Exception:  # noqa: BLE001
                    pass

        # 可选：同步 JS 死循环阻塞页（默认不跑；跑完需人工在 Chrome 点「退出网页」）
        if args.include_hung_page:
            try:
                web.create(args.hung_page_url, mode=args.mode, load_timeout=5)
                results.append(result("hung_page_create_timeout", "FAIL", "阻塞页竟然创建成功（预期超时）"))
            except UIAError as exc:
                results.append(result("hung_page_create_timeout", "PASS",
                                      f"阻塞页创建按预期超时抛错：{exception_name(exc)}: {exc}"))
            except Exception as exc:  # noqa: BLE001
                results.append(result("hung_page_create_timeout", "FAIL",
                                      error_detail("阻塞页创建异常类型不符", exc)))
            time.sleep(1.5)
            tabs = [p for p in web.get_all(mode=args.mode) if "slow-load-30s" in str(p.get_url())]
            if tabs:
                hung = tabs[0]
                loaded, js_ok, ready_state, _url = probe(hung)
                started = time.perf_counter()
                try:
                    returned = hung.stop_load()
                    stop_note = f"stop_load() 返回 {returned!r}（{time.perf_counter() - started:.2f}s）"
                except Exception as exc:  # noqa: BLE001
                    stop_note = f"stop_load() 抛错 {exception_name(exc)}: {exc}"
                loaded2, js_ok2, _state, _url = probe(hung)
                results.append(result(
                    "hung_page_stop_load_ineffective", "KNOWN",
                    f"同步 JS 死循环页面：{stop_note}（不报错），但页面状态未变——"
                    f"is_load_completed() {loaded!r}→{loaded2!r}、execute_javascript() 仍不可用"
                    f"（js_ok={js_ok2}）。CDP Page.stopLoading 无法中断正在执行的同步 JS；"
                    f"该状态下 navigate/close 也会失败，唯一出口是 Chrome 的"
                    f"「页面无响应 → 退出网页」对话框。此行不计入退出码。",
                    loaded_before=loaded, loaded_after=loaded2))
                try:
                    hung.close(ignore_beforeunload=True)
                    results.append(result("hung_page_cleanup", "PASS", "阻塞页标签已关闭"))
                except Exception as exc:  # noqa: BLE001
                    results.append(result(
                        "hung_page_cleanup", "KNOWN",
                        f"无响应标签无法通过 SDK 关闭（{exception_name(exc)}: {exc}）；"
                        f"请手动点击 Chrome 的「页面无响应 → 退出网页」。此行不计入退出码。"))
    except Exception as exc:  # noqa: BLE001
        results.append(result("scenario", "FAIL", error_detail("stop_load 场景执行失败", exc)))
    finally:
        close_error = ""
        if page is not None:
            # 待处理导航未释放时 close() 会失败，重试一次前先 stop_load 兜底。
            for _attempt in (1, 2):
                try:
                    page.close(ignore_beforeunload=True)
                    close_error = ""
                    break
                except Exception as exc:  # noqa: BLE001
                    close_error = f"{exception_name(exc)}: {exc}"
                    try:
                        page.stop_load()
                    except Exception:  # noqa: BLE001
                        pass
                    time.sleep(0.5)
        time.sleep(0.5)
        leftover = []
        try:
            remaining = web.get_all(mode=args.mode)
            leftover = [p for p in remaining if str(getattr(p, "id", "") or "") not in baseline_ids]
        except Exception as exc:  # noqa: BLE001
            close_error = close_error or f"get_all 复核失败: {exception_name(exc)}: {exc}"
        hung_left = [p for p in leftover if "slow-load-30s" in str(p.get_url())]
        known_left = bool(hung_left) and args.include_hung_page
        cleaned = not close_error and (not leftover or known_left)
        results.append(result(
            "cleanup", "PASS" if cleaned else "FAIL",
            f"已关闭本次页面；与进入时相比新增标签 {len(leftover)} 个"
            + ("（其中无响应标签由 --include-hung-page 场景产生，属已知边界，需人工退出网页）"
               if known_left else "") if cleaned else
            f"清理不完整: 新增标签={len(leftover)}, 错误={close_error or '无'}",
            new_tabs=len(leftover), hung_tabs=len(hung_left), error=close_error))

    statuses = {item["status"] for item in results}
    code = 1 if "FAIL" in statuses else (2 if "BLOCKED" in statuses else 0)
    return results, code


def main(argv=None):
    parser = argparse.ArgumentParser(description="WebBrowser.stop_load() 页面对象 API 验收")
    parser.add_argument("--target-url", default=DEFAULT_URL, help="常规靶场页")
    parser.add_argument("--hung-page-url", default=HUNG_PAGE_URL, help="同步 JS 死循环阻塞页")
    parser.add_argument("--mode", choices=("chrome", "edge"), default="chrome")
    parser.add_argument("--load-timeout", type=float, default=20)
    parser.add_argument("--hang-timeout", type=float, default=3, help="导航到挂起地址时的等待秒数")
    parser.add_argument("--settle-timeout", type=float, default=8, help="stop_load 后等待页面恢复可用的秒数")
    parser.add_argument("--contract-only", action="store_true")
    parser.add_argument("--include-hung-page", action="store_true",
                        help="额外刻画「同步 JS 死循环页面」边界：跑完需人工在 Chrome 点「退出网页」")
    parser.add_argument("--json", action="store_true", help="在表格后额外输出 JSON 报告（用于归档验收产物）")
    args = parser.parse_args(argv)
    for name in ("load_timeout", "hang_timeout", "settle_timeout"):
        if getattr(args, name) <= 0:
            parser.error(f"--{name.replace('_', '-')} 必须大于 0")

    results, code = run(args)
    print("UIAutoma Web API 测试")
    print("API     : uiautoma.web.WebBrowser.stop_load")
    print(f"页面    : {args.target_url}")
    print(f"挂起目标: {', '.join(HANG_URLS)}")
    print("进度     状态    测试项                  测试结果")
    print("────────────────────────────────────────────────────────────────────────")
    for index, current in enumerate(results, 1):
        status = current["status"]
        color = {"PASS": GREEN, "BLOCKED": YELLOW, "KNOWN": BLUE}.get(status, RED)
        label = {"PASS": "通过", "BLOCKED": "阻塞", "KNOWN": "记录"}.get(status, "失败")
        print(f"{index:02d}/{len(results):02d}    {color}[{label}]{RESET}  "
              f"{current['case_id']:<38}  {current['detail']}")
    print("────────────────────────────────────────────────────────────────────────")
    counted = [item for item in results if item["status"] != "KNOWN"]
    summary = "测试通过" if code == 0 else ("测试阻塞" if code == 2 else "测试失败")
    print(f"{summary} · {sum(item['status'] == 'PASS' for item in results)}/{len(counted)} 通过"
          f"（另 {sum(item['status'] == 'KNOWN' for item in results)} 项记录，不计入退出码）"
          f" · 退出码 {code}")
    if args.json:
        print(json.dumps({
            "api": "uiautoma.web.WebBrowser.stop_load",
            "target_url": args.target_url, "hung_page_url": args.hung_page_url,
            "hang_urls": list(HANG_URLS), "refused_url": REFUSED_URL, "mode": args.mode,
            "status": "PASS" if code == 0 else ("BLOCKED" if code == 2 else "FAIL"),
            "exit_code": code, "results": results,
        }, ensure_ascii=False, indent=2))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
