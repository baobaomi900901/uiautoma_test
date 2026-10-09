"""WebElement.input() 原生表单完整验收。

流程：打开靶场 -> 核对输入/提交/重置元素 -> input() -> 提交读取 JSON.text
-> 重置表单。每个用例独立执行，默认使用 Win32 风格终端报告。
源码快照：D:/code/desktop @ c101caa9dcd115a461fc71ecaed351b0dea880b8。
"""
from __future__ import annotations

import argparse
import inspect
import json
import math
import sys
from pathlib import Path
import shutil
import tempfile
import time
from typing import Any, Callable
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

import uiautoma
from uiautoma import ElementNotFoundError, InvalidParamsError, UnsupportedActionError, ping, web
from uiautoma.web import WebBrowser, WebElement
from uiautoma.win32 import clipboard

__test__ = False

LIBRARY = Path(r"D:\code\元素库\260902_web元素")
VARIANTS = {
    "noniframe": {
        "url": "https://baobaomi900901.github.io/xpath/#/form-controls",
        "input": "web靶场_非iframe_非shadow_表单测试_原生_输入框",
        "submit": "web靶场_非iframe_非shadow_表单测试_原生_按钮_提交",
        "reset": "web靶场_非iframe_非shadow_表单测试_原生_按钮_重置",
        "switch": None,
        "probe": "document",
    },
    "iframe": {
        "url": "https://baobaomi900901.github.io/xpath/#/iframe-shadow-form",
        "input": "web靶场_表单测试_原生_输入框",
        "submit": "web靶场_表单测试_原生_按钮_提交",
        "reset": "web靶场_表单测试_原生_重置",
        "switch": "web靶场_表单测试_控制表单组件id是否为动态的开关",
        "probe": "iframe",
    },
}
TARGET_VARIANT = "noniframe"
URL = VARIANTS[TARGET_VARIANT]["url"]
INPUT_NAME = VARIANTS[TARGET_VARIANT]["input"]
SUBMIT_NAME = VARIANTS[TARGET_VARIANT]["submit"]
RESET_NAME = VARIANTS[TARGET_VARIANT]["reset"]
SWITCH_NAME = VARIANTS[TARGET_VARIANT]["switch"]
BASE_TEXT = "测试文本 UIAutoma 123 中文 😀✓"
SIMULATIVE_TEXT = "测试文本 UIAutoma 123 中文"
SPECIAL_TEXT = "!@#$%^&*()_+-=[]{};:'\",.?/\\|~"
GREEN, RED, YELLOW, RESET = "\x1b[92m", "\x1b[91m", "\x1b[93m", "\x1b[0m"


class Blocked(RuntimeError):
    """测试环境阻塞，不代表被测 API 失败。"""


def configure_variant(name: str) -> None:
    global TARGET_VARIANT, URL, INPUT_NAME, SUBMIT_NAME, RESET_NAME, SWITCH_NAME
    config = VARIANTS[name]
    TARGET_VARIANT = name
    URL = config["url"]
    INPUT_NAME = config["input"]
    SUBMIT_NAME = config["submit"]
    RESET_NAME = config["reset"]
    SWITCH_NAME = config["switch"]

EXPECTED_PARAMS = (
    "self", "text", "simulative", "cdp_input", "append", "contains_hotkey",
    "force_ime_eng", "send_key_delay", "focus_timeout", "delay_after",
    "click_before_input", "anchor", "input_check", "retry_times", "check_value",
)

PROBE_DOCUMENT = """function (element, arg) {
  const root = document;
  const ids = [arg.inputId, arg.submitId, arg.resetId];
  const result = {};
  for (const id of ids) {
    const nodes = root.querySelectorAll('[id="' + id + '"]');
    if (nodes.length !== 1) throw new Error(id + ': expected one element, got ' + nodes.length);
    const rect = nodes[0].getBoundingClientRect();
    result[id] = {tag: nodes[0].tagName, visible: rect.width > 0 && rect.height > 0};
  }
  return result;
}"""

PROBE_IFRAME = """function (element, arg) {
  const frame = document.querySelector('#iframe-shadow-form');
  const frameDoc = frame && frame.contentDocument;
  const host = frameDoc && frameDoc.querySelector('#form-shadow-host');
  const root = host && host.shadowRoot;
  if (!root) throw new Error('iframe/open shadow 尚未就绪');
  const ids = [arg.inputId, arg.submitId, arg.resetId];
  const result = {};
  for (const id of ids) {
    const nodes = root.querySelectorAll('[id="' + id + '"]');
    if (nodes.length !== 1) throw new Error(id + ': expected one element, got ' + nodes.length);
    const rect = nodes[0].getBoundingClientRect();
    result[id] = {tag: nodes[0].tagName, visible: rect.width > 0 && rect.height > 0};
  }
  return result;
}"""


def result(case_id: str, status: str, detail: str, elapsed_ms: float = 0, **extra: Any) -> dict[str, Any]:
    return {"case_id": case_id, "status": status, "detail": detail, "elapsed_ms": elapsed_ms, **extra}


def error_detail(exc: BaseException) -> str:
    text = f"{type(exc).__name__}: {exc}"
    trace = str(getattr(exc, "trace_info", "") or "")
    if trace:
        text += f" [trace={trace}]"
    trace_id = str(getattr(exc, "trace_id", "") or "")
    if trace_id:
        text += f" [trace_id={trace_id}]"
    return text


def is_blocked(exc: BaseException) -> bool:
    return isinstance(exc, Blocked) or str(getattr(exc, "trace_info", "") or "") in {
        "browser_launch_timeout", "browser_session_discovery_failed",
        "plugin_not_connected", "native_host_unavailable", "web_bridge_unavailable",
        "web_ipc_unreachable", "activate_tab_failed",
    }


def record(rows: list[dict[str, Any]], case_id: str, action: Callable[[], str]) -> None:
    started = time.perf_counter()
    try:
        detail = action()
        rows.append(result(case_id, "PASS", detail, (time.perf_counter() - started) * 1000))
    except Exception as exc:
        rows.append(result(case_id, "BLOCKED" if is_blocked(exc) else "FAIL",
                            error_detail(exc), (time.perf_counter() - started) * 1000))


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def contract() -> str:
    signature = inspect.signature(WebElement.input)
    params = signature.parameters
    require(tuple(params) == EXPECTED_PARAMS, f"公开签名不符: {signature}")
    require(params["text"].kind is inspect.Parameter.POSITIONAL_OR_KEYWORD
            and params["text"].default is inspect.Parameter.empty, "text 必填")
    for name in EXPECTED_PARAMS[2:]:
        require(params[name].kind is inspect.Parameter.KEYWORD_ONLY, f"{name} 不是关键字参数")
    require(params["simulative"].default is True
            and params["cdp_input"].default is False
            and params["append"].default is False
            and params["contains_hotkey"].default is False
            and params["force_ime_eng"].default is False
            and params["send_key_delay"].default == 50
            and params["focus_timeout"].default == 1000
            and params["delay_after"].default == 1
            and params["click_before_input"].default is True
            and params["anchor"].default is None
            and params["input_check"].default is False
            and params["retry_times"].default == 3
            and params["check_value"].default == "", "默认值不符")
    annotation = str(signature.return_annotation).replace("'", "").replace('"', "").replace(" ", "")
    require(annotation in ("None", "<classNoneType>"), f"返回注解不符: {signature}")
    return "公开签名、参数种类、默认值和 None 返回值符合合同"


def target_preflight(timeout: float) -> str:
    request = Request(URL, headers={"User-Agent": "UIAutoma-SDK-input-test"})
    last_error: BaseException | None = None
    for attempt in range(3):
        try:
            with urlopen(request, timeout=timeout) as response:
                require(response.status == 200, f"靶场 HTTP 状态异常: {response.status}")
            return f"原生表单输入测试靶场可访问；HTTP 预检第 {attempt + 1} 次成功"
        except HTTPError:
            raise
        except (URLError, TimeoutError, OSError) as exc:
            last_error = exc
            if attempt < 2:
                time.sleep(0.5)
    raise Blocked(f"靶场 HTTPS 预检连续 3 次失败；浏览器/API 尚未调用；最后错误: {last_error}")


def runtime_preflight(timeout: float) -> str:
    info = ping(timeout=timeout)
    return (f"Runtime 与 Automation Pipe 可响应；protocol={getattr(info, 'protocol', '?')}；"
            f"runtime={getattr(info, 'runtime_version', '?')}；pid={getattr(info, 'runtime_pid', '?')}")


def find_element(page: WebBrowser, name: str, timeout: float) -> WebElement:
    value = page.find(name, timeout=timeout)
    require(isinstance(value, WebElement), f"{name} 未返回 WebElement")
    return value


def disable_dynamic_ids(page: WebBrowser, captured: WebElement, timeout: float) -> str:
    current = captured
    for _ in range(6):
        if current.get_attribute("role") == "switch":
            break
        current = current.parent(timeout=timeout)
        require(current is not None, '动态 ID 开关父级链已结束')
    else:
        raise AssertionError('未找到 role=switch 的动态 ID 开关')
    state = current.get_attribute("aria-checked")
    require(state in ("true", "false"), f"动态 ID 开关 aria-checked 无效: {state!r}")
    if state == "true":
        current.click(simulative=False, delay_after=0)
        deadline = time.monotonic() + timeout
        while current.get_attribute("aria-checked") == "true":
            require(time.monotonic() < deadline, '动态 ID 开关点击后仍为开启状态')
            time.sleep(0.05)
        return "动态 ID 开关已从 true 关闭为 false"
    return "动态 ID 开关已是 false，未重复点击"


def setup_page(args: argparse.Namespace) -> tuple[WebBrowser, Any, dict[str, WebElement]]:
    if not args.library.is_dir():
        raise FileNotFoundError(f"元素库不存在: {args.library}")
    temp = Path(tempfile.mkdtemp(prefix="uiautoma-input-native-", dir=args.temp_root))
    shutil.copytree(args.library, temp / "library")
    package = None
    page = None
    try:
        package = uiautoma.open(str(temp / "library"), timeout=args.runtime_timeout,
                                connect_timeout=args.runtime_timeout)
        page = web.create(URL, mode=args.mode, load_timeout=args.load_timeout,
                          silent_running=False)
        require(isinstance(page, WebBrowser), f"预期 WebBrowser；实际 {type(page).__name__}")
        page.activate()
        active = web.get_active(args.mode, load_timeout=min(2.0, args.element_timeout))
        require(str(active.get_url()) == str(page.get_url()), "测试靶场已打开，但不是当前活动页面")
        if SWITCH_NAME:
            try:
                switch = find_element(page, SWITCH_NAME, args.element_timeout)
                switch_detail = disable_dynamic_ids(page, switch, args.element_timeout)
            except ElementNotFoundError:
                switch_detail = "iframe 靶场未找到动态 ID 开关"
        else:
            switch_detail = "非 iframe、非 shadow 靶场不需要动态 ID 开关"
        elements = {
            "input": find_element(page, INPUT_NAME, args.element_timeout),
            "submit": find_element(page, SUBMIT_NAME, args.element_timeout),
            "reset": find_element(page, RESET_NAME, args.element_timeout),
        }
        probe_script = PROBE_IFRAME if args.target_variant == "iframe" else PROBE_DOCUMENT
        probe = page.execute_javascript(probe_script, {
            "inputId": "form-controls-native-text",
            "submitId": "form-controls-native-submit",
            "resetId": "form-controls-native-reset",
        })
        require(all(row["visible"] for row in probe.values()), f"目标元素不可见: {probe!r}")
        return page, package, {"elements": elements, "temp": temp, "switch_detail": switch_detail}
    except Exception:
        if page is not None:
            try: page.close(ignore_beforeunload=True)
            except Exception: pass
        if package is not None:
            try: package.close()
            except Exception: pass
        shutil.rmtree(temp, ignore_errors=True)
        raise


def clipboard_payload() -> dict[str, Any] | None:
    try:
        value = json.loads(clipboard.get_text())
    except Exception:
        return None
    return value if isinstance(value, dict) else None


def refresh_elements(page: WebBrowser, timeout: float) -> dict[str, WebElement]:
    """表单提交/重置可能重渲染 iframe shadow 内节点，每轮重新绑定 Runtime 引用。"""
    return {
        "input": find_element(page, INPUT_NAME, timeout),
        "submit": find_element(page, SUBMIT_NAME, timeout),
        "reset": find_element(page, RESET_NAME, timeout),
    }


def submit_and_read(page: WebBrowser, timeout: float, element_timeout: float) -> tuple[dict[str, Any], str]:
    sentinel = f"uiautoma-input-submit-{time.time_ns()}"
    for simulative, mode in ((False, "dom"), (True, "simulative_fallback")):
        submit = find_element(page, SUBMIT_NAME, element_timeout)
        clipboard.set_text(sentinel)
        submit.click(simulative=simulative, delay_after=0)
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            payload = clipboard_payload()
            if payload is not None and str(payload.get("text", "")) != sentinel:
                return payload, mode
            time.sleep(0.05)
    raise AssertionError("提交按钮未将表单 JSON 写入剪贴板")


def reset_form(reset: WebElement) -> str:
    reset.click(simulative=False, delay_after=0)
    time.sleep(0.15)
    return "已点击原生重置按钮"


def check_payload(payload: dict[str, Any], expected: str) -> str:
    actual = str(payload.get("text", ""))
    require(actual == expected, f"提交 JSON text 预期 {expected!r}；实际 {actual!r}")
    return f"提交 JSON text={actual!r}，与输入内容一致"


def cases(base: str) -> list[dict[str, Any]]:
    half = max(1, len(base) // 2)
    return [
        {"id": "background_unicode", "steps": [(base, {"simulative": False, "delay_after": 0.1})], "expected": base},
        {"id": "simulative_unicode", "steps": [(SIMULATIVE_TEXT, {"simulative": True, "delay_after": 0.1})], "expected": SIMULATIVE_TEXT},
        {"id": "special_characters", "steps": [(SPECIAL_TEXT, {"simulative": False, "delay_after": 0.1})], "expected": SPECIAL_TEXT},
        {"id": "append", "steps": [
            (base[:half], {"simulative": False, "append": False, "delay_after": 0.1}),
            (base[half:], {"simulative": False, "append": True, "delay_after": 0.1}),
        ], "expected": base},
        {"id": "input_check", "steps": [(base, {"simulative": False, "input_check": True, "check_value": base, "retry_times": 1, "delay_after": 0.1})], "expected": base},
        {"id": "cdp_input", "steps": [(base, {"simulative": False, "cdp_input": True, "delay_after": 0.1})], "expected": base},
        {"id": "force_ime", "steps": [(SIMULATIVE_TEXT, {"simulative": True, "force_ime_eng": True, "delay_after": 0.1})], "expected": SIMULATIVE_TEXT},
        {"id": "send_key_delay_zero", "steps": [(SIMULATIVE_TEXT, {"simulative": True, "send_key_delay": 0, "delay_after": 0.1})], "expected": SIMULATIVE_TEXT},
        {"id": "focus_timeout_zero", "steps": [(SIMULATIVE_TEXT, {"simulative": True, "focus_timeout": 0, "delay_after": 0.1})], "expected": SIMULATIVE_TEXT},
        {"id": "click_before_input_false", "steps": [(base, {"simulative": False, "click_before_input": False, "delay_after": 0.1})], "expected": base, "focus_first": True},
        {"id": "anchor_string", "steps": [(SIMULATIVE_TEXT, {"simulative": True, "anchor": "middle_center", "delay_after": 0.1})], "expected": SIMULATIVE_TEXT},
        {"id": "anchor_tuple", "steps": [(SIMULATIVE_TEXT, {"simulative": True, "anchor": ("top_left", 5, 5), "delay_after": 0.1})], "expected": SIMULATIVE_TEXT},
        {"id": "anchor_dict", "steps": [(SIMULATIVE_TEXT, {"simulative": True, "anchor": {"anchor": "bottom_right", "offset_x": -5, "offset_y": -5}, "delay_after": 0.1})], "expected": SIMULATIVE_TEXT},
        {"id": "anchor_random", "steps": [(SIMULATIVE_TEXT, {"simulative": True, "anchor": "random", "delay_after": 0.1})], "expected": SIMULATIVE_TEXT},
        {"id": "delay_after_none", "steps": [(base, {"simulative": False, "delay_after": None})], "expected": base},
        {"id": "delay_after_positive", "steps": [(base, {"simulative": False, "delay_after": 0.2})], "expected": base, "min_elapsed": 0.18},
    ]


def run_case(page: WebBrowser, item: dict[str, Any], timeout: float, element_timeout: float) -> str:
    # 提交/重置会导致 iframe shadow 内节点重挂载；每轮从当前活动页面重新绑定。
    page.activate()
    elements = refresh_elements(page, element_timeout)
    reset_form(elements["reset"])
    # 重置本身会重建原生表单节点；输入、提交和后续重置必须使用新的 Runtime 引用。
    elements = refresh_elements(page, element_timeout)
    if item.get("focus_first"):
        elements["input"].focus()
    started = time.perf_counter()
    returned_values = []
    expected_value = ""
    for text_value, kwargs in item["steps"]:
        returned = elements["input"].input(text_value, **kwargs)
        returned_values.append(returned)
        expected_value = expected_value + str(text_value) if kwargs.get("append") else str(text_value)
        actual_value = elements["input"].get_value()
        require(str(actual_value) == expected_value,
                f"input 后元素值预期 {expected_value!r}；实际 {actual_value!r}")
    elapsed = time.perf_counter() - started
    require(all(value is None for value in returned_values), f"input 返回值异常: {returned_values!r}")
    if item.get("min_elapsed") is not None:
        require(elapsed >= item["min_elapsed"], f"delay_after 等待不足: {elapsed:.3f}s")
    payload, mode = submit_and_read(page, timeout, element_timeout)
    detail = check_payload(payload, item["expected"])
    reset_form(refresh_elements(page, element_timeout)["reset"])
    return f"{detail}；提交方式={mode}；输入调用 {elapsed * 1000:.1f}ms"


def cleanup(page, package, resources):
    rows = []
    if page is not None:
        try:
            page.close(ignore_beforeunload=True)
            rows.append(("cleanup_page", "PASS", "本次页面已关闭"))
        except Exception as exc:
            rows.append(("cleanup_page", "FAIL", error_detail(exc)))
    if package is not None:
        try:
            package.close()
            rows.append(("cleanup_package", "PASS", "本次 Package 已关闭"))
        except Exception as exc:
            rows.append(("cleanup_package", "FAIL", error_detail(exc)))
    temp = resources.get("temp")
    if temp is not None:
        try:
            shutil.rmtree(temp, ignore_errors=False)
            rows.append(("cleanup_temp", "PASS", "临时元素库副本已删除"))
        except Exception as exc:
            rows.append(("cleanup_temp", "FAIL", error_detail(exc)))
    return rows


def main(argv=None):
    parser = argparse.ArgumentParser(description="WebElement.input() 原生表单完整验收")
    parser.add_argument("target_variant", nargs="?", choices=("noniframe", "iframe"),
                        default="noniframe", help="靶场模式；默认 noniframe，传 iframe 切换到 iframe/open shadow 靶场")
    parser.add_argument("--mode", choices=("chrome",), default="chrome")
    parser.add_argument("--library", type=Path, default=LIBRARY)
    parser.add_argument("--input-text", default=BASE_TEXT)
    parser.add_argument("--element-timeout", type=float, default=10)
    parser.add_argument("--runtime-timeout", type=float, default=20)
    parser.add_argument("--load-timeout", type=float, default=20)
    parser.add_argument("--wait-timeout", type=float, default=5)
    parser.add_argument("--contract-only", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    configure_variant(args.target_variant)
    args.library = args.library.resolve()
    args.temp_root = Path(__file__).resolve().parents[1] / ".pytest_tmp"
    for name in ("element_timeout", "runtime_timeout", "load_timeout", "wait_timeout"):
        value = getattr(args, name)
        if not math.isfinite(value) or value <= 0:
            parser.error(f"--{name.replace('_', '-')} 必须为正数")
    rows = []
    started = time.perf_counter()
    try:
        record(rows, "api_contract", contract)
        if args.contract_only:
            return print_report(args, rows, 0)
        record(rows, "target_preflight", lambda: target_preflight(10))
        record(rows, "runtime_preflight", lambda: runtime_preflight(args.runtime_timeout))
        if any(row["status"] != "PASS" for row in rows[-2:]):
            return print_report(args, rows, 2)
        record(rows, "library_prepare", lambda: f"元素库存在：{args.library}")
        page = package = None
        resources = {}
        try:
            page, package, resources = setup_page(args)
            rows.append(result("page_and_elements", "PASS", "靶场已打开并激活；输入、提交、重置元素均已核对", 0.0))
            rows.append(result("dynamic_id_switch", "PASS", resources["switch_detail"], 0.0))
            for item in cases(args.input_text):
                record(rows, item["id"], lambda item=item: run_case(page, item, args.wait_timeout, args.element_timeout))
        except Exception as exc:
            rows.append(result("scenario", "BLOCKED" if is_blocked(exc) else "FAIL", error_detail(exc), 0.0))
        finally:
            for case_id, status, detail in cleanup(page, package, resources):
                rows.append(result(case_id, status, detail, 0.0))
    except Exception as exc:
        rows.append(result("setup", "FAIL", error_detail(exc), 0.0))
    return print_report(args, rows, 1 if any(r["status"] == "FAIL" for r in rows) else 2 if any(r["status"] == "BLOCKED" for r in rows) else 0, started)


def print_report(args, rows, code, started=None):
    def line(value=""):
        text = str(value)
        encoding = sys.stdout.encoding or "utf-8"
        safe = text.encode(encoding, errors="replace").decode(encoding, errors="replace")
        sys.stdout.write(safe + "\n")
        sys.stdout.flush()

    if args.json:
        print(json.dumps({"api": "uiautoma.web.WebElement.input", "status": "PASS" if code == 0 else "FAIL", "exit_code": code, "results": rows}, ensure_ascii=False, indent=2))
        return code
    line("UIAutoma Web API 测试")
    line("API     : uiautoma.web.WebElement.input")
    line(f"靶场模式: {args.target_variant}")
    line(f"页面    : {URL}")
    line(f"元素库  : {args.library}")
    line(f"测试元素: {INPUT_NAME}")
    line(f"提交元素: {SUBMIT_NAME}")
    line("参照    : 点击原生提交按钮读取剪贴板 JSON，仅核对 payload.text")
    line("进度     状态    测试项                         测试结果 / 耗时")
    line("─" * 108)
    colors = {"PASS": GREEN, "FAIL": RED, "BLOCKED": YELLOW}
    labels = {"PASS": "通过", "FAIL": "失败", "BLOCKED": "阻塞"}
    for index, row in enumerate(rows, 1):
        line(f"{index:02d}/{len(rows):02d}    {colors.get(row['status'], '')}[{labels.get(row['status'], row['status'])}]{RESET}  "
             f"{row['case_id']:<30} {row['detail']}  {row.get('elapsed_ms', 0):.1f}ms")
    line("─" * 108)
    passed = sum(row["status"] == "PASS" for row in rows)
    total_ms = (time.perf_counter() - started) * 1000 if started else 0
    line(f"{'测试通过' if code == 0 else '测试失败' if code == 1 else '测试阻塞'} · {passed}/{len(rows)} 通过 · {total_ms:.1f}ms · 退出码 {code}")
    return code


if __name__ == "__main__":
    raise SystemExit(main())
