"""WebElement.focus() keys-click-test 独立验收。"""
from __future__ import annotations
import argparse
import inspect
import json
from pathlib import Path
import shutil
import tempfile
import time
import uuid

import uiautoma
from uiautoma import InvalidParamsError, ping, web
from uiautoma.web import WebBrowser, WebElement
from uiautoma.win32 import clipboard

URL = "https://baobaomi900901.github.io/xpath/#/keys-click-test"
LIBRARY = Path(r"D:\code\元素库\260902_web元素")
TARGET_NAME = "web靶场_测试点击_测试focus"
COPY_NAME = "web靶场_测试点击_读取最近一条点击记录"
TARGET_ID = "focus-target"
COPY_ID = "btn-copy-latest-keys-log"
GREEN, RED, YELLOW, RESET = "\x1b[92m", "\x1b[91m", "\x1b[93m", "\x1b[0m"

PROBE = """function (element, arg) {
  const target = document.querySelector('#focus-target');
  const copy = document.querySelector('#btn-copy-latest-keys-log');
  const clear = document.querySelector('#btn-clear-keys-log');
  if (!target || !copy || !clear) throw new Error('focus/copy/clear DOM element missing');
  const rows = () => Array.from(document.querySelectorAll('#keys-click-log tbody tr[data-row-key]'))
    .map(row => ({key: row.getAttribute('data-row-key'), text: row.innerText}));
  if (arg.op === 'install') {
    const state = {events: [], armed: false};
    state.listen = event => {
      if (!state.armed || event.target !== target) return;
      state.events.push({type: event.type, trusted: event.isTrusted,
        activeId: document.activeElement && document.activeElement.id});
    };
    window[arg.key] = state;
    document.addEventListener('focusin', state.listen, true);
    return {targetId: target.id, copyId: copy.id};
  }
  const state = window[arg.key];
  if (!state) throw new Error('focus observer missing');
  if (arg.op === 'prepare') {
    state.events = [];
    state.armed = false;
    if (!clear.disabled) clear.click();
    if (document.activeElement && document.activeElement.blur) document.activeElement.blur();
    return {rows: rows(), activeId: document.activeElement && document.activeElement.id};
  }
  if (arg.op === 'arm') {
    state.events = [];
    state.armed = true;
    return true;
  }
  if (arg.op === 'read') return {events: state.events.slice(), rows: rows(),
    activeId: document.activeElement && document.activeElement.id};
  if (arg.op === 'remove') {
    document.removeEventListener('focusin', state.listen, true);
    delete window[arg.key];
    return true;
  }
  throw new Error('unknown probe operation');
}"""

class Blocked(RuntimeError):
    pass

def error_detail(exc):
    text = f"{type(exc).__name__}: {exc}"
    if getattr(exc, "trace_info", ""): text += f" [trace={exc.trace_info}]"
    if getattr(exc, "trace_id", ""): text += f" [trace_id={exc.trace_id}]"
    return text

def require(value, message):
    if not value: raise AssertionError(message)

def blocked(exc):
    return isinstance(exc, Blocked) or str(getattr(exc, "trace_info", "")) in {
        "browser_launch_timeout", "plugin_not_connected", "native_host_unavailable",
        "web_bridge_unavailable", "activate_tab_failed"}

def row(rows, name, fn):
    started = time.perf_counter()
    try:
        detail = fn()
        rows.append({"case_id": name, "status": "PASS", "detail": detail,
                     "elapsed_ms": (time.perf_counter()-started)*1000})
    except Exception as exc:
        rows.append({"case_id": name, "status": "BLOCKED" if blocked(exc) else "FAIL",
                     "detail": error_detail(exc), "elapsed_ms": (time.perf_counter()-started)*1000})

def contract():
    sig = inspect.signature(WebElement.focus)
    params = sig.parameters
    require(tuple(params) == ("self", "timeout"), f"签名不符: {sig}")
    require(params["timeout"].kind is inspect.Parameter.KEYWORD_ONLY and params["timeout"].default == 5.0,
            "timeout 必须是关键字参数且默认 5.0")
    require(str(sig.return_annotation).replace("'", "").replace('"', "").replace(" ", "")
            in ("None", "<classNoneType>"), "返回注解不符")
    return "timeout 仅限关键字、默认 5.0；返回 None"

def probe(page, key, op):
    return page.execute_javascript(PROBE, {"key": key, "op": op})

def wait_for(fn, predicate, timeout, message):
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        value = fn()
        if predicate(value): return value
        time.sleep(0.05)
    raise AssertionError(message)


def clipboard_text_retry(timeout: float) -> str:
    deadline = time.monotonic() + timeout
    last = None
    while time.monotonic() < deadline:
        try:
            return clipboard.get_text()
        except Exception as exc:
            last = exc
            time.sleep(0.05)
    raise Blocked(f"剪贴板读取连续重试失败；最后错误: {last}")

def setup(args):
    temp = Path(tempfile.mkdtemp(prefix="uiautoma-focus-", dir=args.temp_root))
    package = page = None
    try:
        package = uiautoma.open(str(args.library), timeout=args.runtime_timeout, connect_timeout=args.runtime_timeout)
        page = web.create(URL, mode="chrome", load_timeout=args.load_timeout, silent_running=False)
        page.activate()
        active = web.get_active("chrome", load_timeout=2)
        require(active.get_url() == page.get_url(), "测试页未成为当前活动页面")
        target = page.find(TARGET_NAME, timeout=args.element_timeout)
        copy = page.find(COPY_NAME, timeout=args.element_timeout)
        require(target.get_attribute("id") == TARGET_ID, "focus 元素 DOM id 不符")
        require(copy.get_attribute("id") == COPY_ID, "复制元素 DOM id 不符")
        return page, package, target, copy, temp
    except Exception:
        if page:
            try: page.close(ignore_beforeunload=True)
            except Exception: pass
        if package:
            try: package.close()
            except Exception: pass
        shutil.rmtree(temp, ignore_errors=True)
        raise

def copy_log(copy, marker, timeout):
    clipboard.set_text(marker)
    copy.click(simulative=False, delay_after=0)
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        try:
            value = clipboard_text_retry(min(0.5, timeout))
            if value and value != marker:
                payload = json.loads(value)
                require(payload.get("buttonId") == TARGET_ID, "日志 buttonId 不符")
                require(payload.get("eventType") == "focus", "日志 eventType 不符")
                require(payload.get("detectedKeys") == "-", "日志 detectedKeys 不符")
                require(isinstance(payload.get("isTrusted"), bool), "日志 isTrusted 类型不符")
                expected_source = "真实鼠标" if payload["isTrusted"] else "JS/插件模拟"
                require(payload.get("clickSource") == expected_source, "日志来源与 isTrusted 不符")
                return f"剪贴板 {payload['buttonId']}/{payload['eventType']}/{payload['clickSource']}/trusted={payload['isTrusted']}"
        except (ValueError, TypeError):
            pass
        time.sleep(0.05)
    raise Blocked("复制按钮未写入有效 focus JSON")

def focus_case(page, target, copy, key, timeout, focus_timeout=5.0):
    page.activate()
    probe(page, key, "prepare")
    probe(page, key, "arm")
    require(target.focus(timeout=focus_timeout) is None, "focus 应返回 None")
    state = wait_for(lambda: probe(page, key, "read"),
        lambda value: any(e["type"] == "focusin" for e in value["events"]),
        timeout, "未观察到 focusin")
    require(state["activeId"] == TARGET_ID, f"activeElement 不符: {state['activeId']!r}")
    require(isinstance(state["events"][-1]["trusted"], bool), "focusin isTrusted 类型不符")
    marker = "uiautoma-focus-" + uuid.uuid4().hex
    return f"返回 None；focusin 1 次；activeElement=#{TARGET_ID}；trusted={state['events'][-1]['trusted']}；{copy_log(copy, marker, timeout)}"

def invalid_case(page, target, key, kind, timeout):
    probe(page, key, "prepare")
    probe(page, key, "arm")
    action = {
        "negative": lambda: target.focus(timeout=-1),
        "fraction": lambda: target.focus(timeout=-0.1),
        "text": lambda: target.focus(timeout="bad"),
        "positional": lambda: target.focus(1),
        "unknown": lambda: target.focus(unsupported=True),
    }[kind]
    expected = TypeError if kind in ("positional", "unknown") else InvalidParamsError
    try:
        action()
    except expected as exc:
        require(not probe(page, key, "read")["events"], "非法 focus 产生事件")
        return f"预期 {expected.__name__}；实际 {type(exc).__name__}: {exc}"
    raise AssertionError(f"预期 {expected.__name__}，实际未抛异常")

def cleanup(page, package, temp, key):
    rows = []
    if page:
        try:
            probe(page, key, "remove")
        except Exception: pass
        try: page.close(ignore_beforeunload=True); rows.append(("cleanup_page", "PASS", "本次页面已关闭"))
        except Exception as exc: rows.append(("cleanup_page", "FAIL", error_detail(exc)))
    if package:
        try: package.close(); rows.append(("cleanup_package", "PASS", "本次 Package 已关闭"))
        except Exception as exc: rows.append(("cleanup_package", "FAIL", error_detail(exc)))
    if temp:
        try: shutil.rmtree(temp); rows.append(("cleanup_temp", "PASS", "临时元素库副本已删除"))
        except Exception as exc: rows.append(("cleanup_temp", "FAIL", error_detail(exc)))
    return rows

def main(argv=None):
    parser = argparse.ArgumentParser(description="WebElement.focus() keys-click-test 独立验收")
    parser.add_argument("--library", type=Path, default=LIBRARY)
    parser.add_argument("--element-timeout", type=float, default=10)
    parser.add_argument("--runtime-timeout", type=float, default=20)
    parser.add_argument("--load-timeout", type=float, default=20)
    parser.add_argument("--wait-timeout", type=float, default=5)
    parser.add_argument("--contract-only", action="store_true")
    args = parser.parse_args(argv)
    args.temp_root = Path(__file__).resolve().parents[1] / ".pytest_tmp"
    rows = []
    row(rows, "api_contract", contract)
    if not args.contract_only:
        page = package = target = copy = temp = None
        key = "__uiautoma_focus_" + uuid.uuid4().hex
        try:
            page, package, target, copy, temp = setup(args)
            probe(page, key, "install")
            row(rows, "page_and_elements", lambda: "靶场、focus 元素和复制元素已准备；DOM id 已核对")
            row(rows, "focus_default", lambda: focus_case(page,target,copy,key,args.wait_timeout))
            row(rows, "focus_keyword", lambda: focus_case(page,target,copy,key,args.wait_timeout,2))
            row(rows, "focus_none_timeout", lambda: focus_case(page,target,copy,key,args.wait_timeout,None))
            row(rows, "focus_repeat", lambda: focus_case(page,target,copy,key,args.wait_timeout))
            for name, kind in (("negative_timeout","negative"),("negative_fraction","fraction"),
                               ("nonnumeric_timeout","text"),("positional_timeout","positional"),
                               ("unknown_keyword","unknown")):
                row(rows, name, lambda kind=kind: invalid_case(page,target,key,kind,args.wait_timeout))
            row(rows, "after_invalid", lambda: focus_case(page,target,copy,key,args.wait_timeout))
        except Exception as exc:
            rows.append({"case_id":"scenario", "status":"BLOCKED" if blocked(exc) else "FAIL",
                         "detail":error_detail(exc), "elapsed_ms":0})
        finally:
            for case_id,status,detail in cleanup(page,package,temp,key):
                rows.append({"case_id":case_id,"status":status,"detail":detail,"elapsed_ms":0})
    code=1 if any(x["status"]=="FAIL" for x in rows) else 2 if any(x["status"]=="BLOCKED" for x in rows) else 0
    print("UIAutoma Web API 测试")
    print("API     : uiautoma.web.WebElement.focus")
    print(f"页面    : {URL}")
    print(f"元素库  : {LIBRARY}")
    print(f"测试元素: {TARGET_NAME}")
    print(f"复制元素: {COPY_NAME}")
    print("参照    : 原生 focusin/activeElement + 靶场剪贴板 JSON")
    print("进度     状态    测试项                         测试结果 / 耗时")
    print("─"*108)
    colors={"PASS":GREEN,"FAIL":RED,"BLOCKED":YELLOW}; labels={"PASS":"通过","FAIL":"失败","BLOCKED":"阻塞"}
    for index,x in enumerate(rows,1):
        print(f"{index:02d}/{len(rows):02d}    {colors.get(x['status'],'')}[{labels[x['status']]}]{RESET}  {x['case_id']:<30} {x['detail']}  {x['elapsed_ms']:.1f}ms")
    print("─"*108)
    passed=sum(x["status"]=="PASS" for x in rows)
    print(f"{'测试通过' if code==0 else '测试失败' if code==1 else '测试阻塞'} · {passed}/{len(rows)} 通过 · 退出码 {code}")
    return code

if __name__=="__main__":
    raise SystemExit(main())
