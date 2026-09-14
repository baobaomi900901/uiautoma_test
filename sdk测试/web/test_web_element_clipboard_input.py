"""uiautoma.web.WebElement.clipboard_input() 持久化真实浏览器测试运行器。

导入本模块不会连接 Runtime、访问靶场或操作浏览器。真实场景打开唯一 Chrome
``form-controls`` 页面并连接指定元素库；目标断言只对 ``input元素`` 直接调用
``WebElement.clipboard_input(...)``（后台 / 剪贴板模拟粘贴 / append / delay_after），
再点击 ``提交_html`` 从剪贴板读取表单 JSON 验收；用例间通过 ``重置_html`` 清空表单。
"""

from __future__ import annotations

import argparse
import inspect
import json
import re
import shutil
import sys
import time
import uuid
from pathlib import Path
from typing import Any, Sequence
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit
from urllib.request import Request, urlopen

PRODUCT_ROOT = Path(__file__).resolve().parents[3]
SDK_SRC = PRODUCT_ROOT / "sdk" / "src"
if str(SDK_SRC) not in sys.path:
    sys.path.insert(0, str(SDK_SRC))

import uiautoma  # noqa: E402
from uiautoma import ping, web  # noqa: E402
from uiautoma.web import WebBrowser, WebElement  # noqa: E402
from uiautoma.win32 import clipboard  # noqa: E402


__test__ = False

DEFAULT_TARGET_URL = "http://localhost:7199/form-controls"
DEFAULT_ELEMENT_LIBRARY = Path(__file__).with_name("web测试元素库")
DEFAULT_INPUT_ELEMENT_NAME = "input元素"
DEFAULT_PROFILE_DIRECTORY = "Default"
DEFAULT_SUBMIT_ELEMENT_NAME = "提交_html"
DEFAULT_RESET_ELEMENT_NAME = "重置_html"
DEFAULT_INPUT_TEXT = "123"
RUN_QUERY_KEY = "uiautoma_element_clipboard_input_run"

EXPECTED_PARAMETER_ORDER = (
    "self",
    "text",
    "simulative",
    "append",
    "focus_timeout",
    "delay_after",
    "send_key_delay",
    "click_before_input",
    "anchor",
    "input_check",
    "retry_times",
    "check_value",
)
EXPECTED_DEFAULTS = {
    "simulative": True,
    "append": False,
    "focus_timeout": 1000,
    "delay_after": 1,
    "send_key_delay": 50,
    "click_before_input": True,
    "anchor": None,
    "input_check": False,
    "retry_times": 3,
    "check_value": "",
}
EXPECTED_KINDS = {
    "self": inspect.Parameter.POSITIONAL_OR_KEYWORD,
    "text": inspect.Parameter.POSITIONAL_OR_KEYWORD,
    "simulative": inspect.Parameter.KEYWORD_ONLY,
    "append": inspect.Parameter.KEYWORD_ONLY,
    "focus_timeout": inspect.Parameter.KEYWORD_ONLY,
    "delay_after": inspect.Parameter.KEYWORD_ONLY,
    "send_key_delay": inspect.Parameter.KEYWORD_ONLY,
    "click_before_input": inspect.Parameter.KEYWORD_ONLY,
    "anchor": inspect.Parameter.KEYWORD_ONLY,
    "input_check": inspect.Parameter.KEYWORD_ONLY,
    "retry_times": inspect.Parameter.KEYWORD_ONLY,
    "check_value": inspect.Parameter.KEYWORD_ONLY,
}

# 基础路径：后台 DOM、剪贴板模拟粘贴、append、delay_after=1。
CLIPBOARD_INPUT_CASES: tuple[dict[str, Any], ...] = (
    {
        "case_id": "clipboard_input_background_basic",
        "steps": (
            {
                "text": DEFAULT_INPUT_TEXT,
                "kwargs": {"simulative": False, "delay_after": 0.2},
            },
        ),
        "expected_text": DEFAULT_INPUT_TEXT,
    },
    {
        "case_id": "clipboard_input_simulative_basic",
        "steps": (
            {
                "text": DEFAULT_INPUT_TEXT,
                "kwargs": {"simulative": True, "delay_after": 0.2},
            },
        ),
        "expected_text": DEFAULT_INPUT_TEXT,
    },
    {
        "case_id": "clipboard_input_simulative_append",
        "steps": (
            {
                "text": "12",
                "kwargs": {"simulative": True, "append": False, "delay_after": 0.2},
            },
            {
                "text": "3",
                "kwargs": {"simulative": True, "append": True, "delay_after": 0.2},
            },
        ),
        "expected_text": "123",
    },
    {
        "case_id": "clipboard_input_simulative_delay_after",
        "steps": (
            {
                "text": DEFAULT_INPUT_TEXT,
                "kwargs": {"simulative": True, "delay_after": 1},
            },
        ),
        "expected_text": DEFAULT_INPUT_TEXT,
        "min_input_elapsed_ms": 900,
    },
)

BLOCKING_EXCEPTION_NAMES = {
    "ConnectionError",
    "EOFError",
    "HostUnavailableError",
    "PipeClosedError",
    "TimeoutError",
    "UnsupportedProtocolError",
}
BLOCKING_TRACES = {
    "browser_executable_not_found",
    "browser_launch_timeout",
    "browser_session_discovery_failed",
    "browser_session_disconnected",
    "native_host_unavailable",
    "plugin_not_connected",
    "web_bridge_unavailable",
    "web_host_unavailable",
    "web_ipc_unreachable",
    "web_runtime_incompatible",
    "web_session_unavailable",
}

def _result(case_id: str, status: str, detail: str, **extra: Any) -> dict[str, Any]:
    return {"case_id": case_id, "status": status, "detail": detail, **extra}

def _safe_trace(exc: BaseException) -> str:
    trace = str(getattr(exc, "trace_info", "") or "")
    return trace if re.fullmatch(r"[A-Za-z0-9_.-]{1,80}", trace) else ""

def _error_fields(exc: BaseException) -> dict[str, str]:
    return {"exception": exc.__class__.__name__, "trace_info": _safe_trace(exc)}

def _error_status(exc: BaseException) -> str:
    if exc.__class__.__name__ in BLOCKING_EXCEPTION_NAMES or _safe_trace(exc) in BLOCKING_TRACES:
        return "BLOCKED"
    return "FAIL"

def _validate_url(value: str, option: str) -> str:
    text = str(value or "").strip()
    try:
        parts = urlsplit(text)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"{option} 不是有效 URL") from exc
    if (
        parts.scheme.casefold() not in {"http", "https"}
        or not parts.hostname
        or parts.username is not None
        or parts.password is not None
    ):
        raise argparse.ArgumentTypeError(f"{option} 必须是不含凭据的绝对 HTTP/HTTPS URL")
    return text

def _marked_url(target_url: str, run_id: str) -> str:
    parts = urlsplit(target_url)
    query = [
        (key, value)
        for key, value in parse_qsl(parts.query, keep_blank_values=True)
        if key != RUN_QUERY_KEY
    ]
    query.append((RUN_QUERY_KEY, run_id))
    return urlunsplit((parts.scheme, parts.netloc, parts.path or "/", urlencode(query), ""))

def _page_key(value: object) -> tuple[Any, ...] | None:
    try:
        parts = urlsplit(str(value or "").strip())
        port = parts.port
    except ValueError:
        return None
    scheme = parts.scheme.casefold()
    hostname = (parts.hostname or "").casefold()
    if scheme not in {"http", "https"} or not hostname:
        return None
    if port == (443 if scheme == "https" else 80):
        port = None
    return scheme, hostname, port, parts.path or "/"

def _exact_url_key(value: object) -> tuple[Any, ...] | None:
    try:
        parts = urlsplit(str(value or "").strip())
        port = parts.port
    except ValueError:
        return None
    scheme = parts.scheme.casefold()
    hostname = (parts.hostname or "").casefold()
    if scheme not in {"http", "https"} or not hostname:
        return None
    if port == (443 if scheme == "https" else 80):
        port = None
    return (
        scheme,
        hostname,
        port,
        parts.path or "/",
        tuple(sorted(parse_qsl(parts.query, keep_blank_values=True))),
    )

def _tab_identity(page: WebBrowser | None) -> tuple[str, int, int] | None:
    if page is None:
        return None
    raw = page.raw if isinstance(page.raw, dict) else {}
    tab = raw.get("tab") if isinstance(raw.get("tab"), dict) else raw
    try:
        tab_id = int(tab.get("tabId", tab.get("id", 0)) or 0)
        window_id = int(tab.get("windowId", tab.get("window_id", 0)) or 0)
    except (TypeError, ValueError):
        return None
    session_id = str(
        raw.get("target_session_id")
        or raw.get("targetSessionId")
        or raw.get("sessionId")
        or tab.get("target_session_id")
        or tab.get("targetSessionId")
        or tab.get("sessionId")
        or ""
    )
    return (session_id, window_id, tab_id) if tab_id > 0 else None

def _try_get_active_page(mode: str, timeout: float) -> WebBrowser | None:
    try:
        return web.get_active(mode, load_timeout=max(0.1, timeout))
    except Exception:  # noqa: BLE001
        return None

def _wait_for_launched_start_page(
    mode: str,
    before_identity: tuple[str, int, int] | None,
    timeout: float,
) -> WebBrowser | None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        page = _try_get_active_page(mode, min(1.0, timeout))
        identity = _tab_identity(page)
        if page is not None and identity is not None and identity != before_identity:
            return page
        time.sleep(0.1)
    return None

def preflight_runtime(timeout: float) -> dict[str, Any]:
    started = time.perf_counter()
    try:
        ping(timeout=timeout)
        return _result(
            "runtime_preflight",
            "PASS",
            "Runtime 与 Automation Pipe 可响应",
            elapsed_ms=round((time.perf_counter() - started) * 1000, 1),
        )
    except Exception as exc:  # noqa: BLE001
        return _result(
            "runtime_preflight",
            "BLOCKED",
            "Runtime 或 Automation Pipe 不可用",
            elapsed_ms=round((time.perf_counter() - started) * 1000, 1),
            **_error_fields(exc),
        )

def prepare_scrubbed_library(source_library: Path, owned_dir: Path) -> dict[str, Any]:
    """复制元素库并清空捕获期 WebSessionId，避免陈旧会话拦截当前页面绑定。"""

    started = time.perf_counter()
    scrubbed_fields = 0
    try:
        shutil.copytree(source_library, owned_dir)
        elements_file = owned_dir / "elements.json"
        payload = json.loads(elements_file.read_text(encoding="utf-8"))
        for process in payload.values():
            if not isinstance(process, dict):
                continue
            for item in process.get("Group", process.get("group", [])):
                if not isinstance(item, dict):
                    continue
                for key in list(item):
                    if "session" in key.casefold() and item.get(key):
                        item[key] = ""
                        scrubbed_fields += 1
                if item.get("BrowserPid"):
                    item["BrowserPid"] = 0
                    scrubbed_fields += 1
        elements_file.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

        snapshot_dir = owned_dir / "snapshot"
        if snapshot_dir.is_dir():
            for snap in snapshot_dir.glob("*.json"):
                data = json.loads(snap.read_text(encoding="utf-8"))
                stack: list[Any] = [data]
                local = 0
                while stack:
                    obj = stack.pop()
                    if isinstance(obj, dict):
                        for key, value in list(obj.items()):
                            if isinstance(key, str) and "session" in key.casefold() and value:
                                obj[key] = ""
                                local += 1
                            elif isinstance(value, (dict, list)):
                                stack.append(value)
                    elif isinstance(obj, list):
                        stack.extend(obj)
                if local:
                    snap.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
                    scrubbed_fields += local

        passed = (owned_dir / "elements.json").is_file()
        return _result(
            "scrubbed_library_setup",
            "PASS" if passed else "FAIL",
            "已准备清空捕获会话后的本次元素库副本" if passed else "本次元素库副本不可用",
            elapsed_ms=round((time.perf_counter() - started) * 1000, 1),
            scrubbed_fields=scrubbed_fields,
            owned_library_exists=passed,
        )
    except Exception as exc:  # noqa: BLE001
        return _result(
            "scrubbed_library_setup",
            "FAIL",
            "无法准备本次元素库副本",
            elapsed_ms=round((time.perf_counter() - started) * 1000, 1),
            scrubbed_fields=scrubbed_fields,
            **_error_fields(exc),
        )

def prepare_owned_page(
    target_url: str,
    mode: str,
    load_timeout: float,
    profile_directory: str,
) -> tuple[dict[str, Any], WebBrowser | None]:
    started = time.perf_counter()
    page: WebBrowser | None = None
    before_active = _try_get_active_page(mode, min(1.0, load_timeout))
    before_identity = _tab_identity(before_active)
    existing_session_reused = before_active is not None
    profile_identity_fallback_used = False
    profile_identity_trace = ""
    recovery_method = "existing_session" if existing_session_reused else ""
    try:
        if existing_session_reused:
            page = web.create(target_url, mode, load_timeout=load_timeout, silent_running=True)
        else:
            try:
                page = web.create(
                    target_url,
                    mode,
                    load_timeout=load_timeout,
                    silent_running=True,
                    arguments=[
                        f"--profile-directory={profile_directory}",
                        "--ignore-profile-directory-if-not-exists",
                    ],
                )
            except Exception as exc:  # noqa: BLE001
                trace = _safe_trace(exc)
                if trace != "browser_profile_identity_unknown":
                    raise
                profile_identity_fallback_used = True
                profile_identity_trace = trace
                page = _wait_for_launched_start_page(
                    mode,
                    before_identity,
                    min(5.0, max(1.0, load_timeout)),
                )
                if page is None:
                    raise RuntimeError("launched Chrome start page is not safely identifiable")
                page.raw["created_by"] = "profile_launch_recovery"
                recovery_method = "navigate_launched_start_page"
                page.navigate(target_url, load_timeout=load_timeout)
        checks = {
            "returned_type_ok": isinstance(page, WebBrowser),
            "mode_ok": str(page.mode or "").casefold() == mode.casefold(),
            "url_ok": _exact_url_key(page.url) == _exact_url_key(target_url),
            "owned_identity_ok": page.raw.get("created_by") in {
                "web.create",
                "profile_launch_recovery",
            },
        }
        passed = all(checks.values())
        return (
            _result(
                "owned_page_setup",
                "PASS" if passed else "BLOCKED",
                "已打开本次唯一表单输入测试页面" if passed else "表单输入测试页面创建结果不完整",
                elapsed_ms=round((time.perf_counter() - started) * 1000, 1),
                profile_directory=profile_directory,
                existing_session_reused=existing_session_reused,
                profile_identity_fallback_used=profile_identity_fallback_used,
                profile_identity_trace=profile_identity_trace,
                profile_recovery_method=recovery_method,
                **checks,
            ),
            page,
        )
    except Exception as exc:  # noqa: BLE001
        return (
            _result(
                "owned_page_setup",
                "BLOCKED",
                "无法打开本次表单输入测试页面",
                elapsed_ms=round((time.perf_counter() - started) * 1000, 1),
                profile_directory=profile_directory,
                existing_session_reused=existing_session_reused,
                profile_identity_fallback_used=profile_identity_fallback_used,
                profile_identity_trace=profile_identity_trace,
                profile_recovery_method=recovery_method,
                **_error_fields(exc),
            ),
            page,
        )



def check_contract() -> dict[str, Any]:
    try:
        signature = inspect.signature(WebElement.clipboard_input)
        parameters = signature.parameters
        order_ok = tuple(parameters) == EXPECTED_PARAMETER_ORDER
        defaults_ok = all(parameters[name].default == value for name, value in EXPECTED_DEFAULTS.items())
        kinds_ok = all(parameters[name].kind == value for name, value in EXPECTED_KINDS.items())
        text_required_ok = parameters["text"].default is inspect.Parameter.empty
        return_ok = signature.return_annotation in {None, "None", type(None)}
        passed = order_ok and defaults_ok and kinds_ok and return_ok and text_required_ok
        return _result(
            "api_contract",
            "PASS" if passed else "FAIL",
            "公开签名符合当前合同" if passed else "公开签名与当前合同不一致",
            parameter_order_ok=order_ok,
            defaults_ok=defaults_ok,
            parameter_kinds_ok=kinds_ok,
            return_annotation_ok=return_ok,
            text_required_ok=text_required_ok,
            return_annotation=str(signature.return_annotation),
        )
    except Exception as exc:  # noqa: BLE001
        return _result("api_contract", "FAIL", "无法检查公开签名", **_error_fields(exc))


def preflight_target(target_url: str, timeout: float) -> dict[str, Any]:
    started = time.perf_counter()
    try:
        request = Request(target_url, headers={"User-Agent": "UIAutoma-SDK-persistent-test"})
        with urlopen(request, timeout=timeout) as response:
            status_code = int(getattr(response, "status", 200))
        passed = 200 <= status_code < 400
        return _result(
            "target_preflight",
            "PASS" if passed else "BLOCKED",
            "表单输入测试靶场可访问" if passed else "表单输入测试靶场未返回成功状态",
            elapsed_ms=round((time.perf_counter() - started) * 1000, 1),
            http_status=status_code,
        )
    except Exception as exc:  # noqa: BLE001
        return _result(
            "target_preflight",
            "BLOCKED",
            "表单输入测试靶场不可访问",
            elapsed_ms=round((time.perf_counter() - started) * 1000, 1),
            **_error_fields(exc),
        )


def _library_named_matches(payload: dict[str, Any], element_name: str) -> list[dict[str, Any]]:
    matches: list[dict[str, Any]] = []
    for process in payload.values():
        if not isinstance(process, dict):
            continue
        for item in process.get("Group", process.get("group", [])):
            if isinstance(item, dict) and str(item.get("Name") or "") == element_name:
                matches.append(item)
    return matches


def _library_item_ok(matches: list[dict[str, Any]], target_url: str) -> tuple[bool, bool]:
    page_ok = len(matches) == 1 and _page_key(matches[0].get("PageUrl")) == _page_key(target_url)
    selector_ok = len(matches) == 1 and bool(str(matches[0].get("Characteristics") or "").strip())
    return page_ok, selector_ok


def preflight_element_library(
    library_dir: Path,
    input_element_name: str,
    submit_element_name: str,
    reset_element_name: str,
    target_url: str,
) -> dict[str, Any]:
    started = time.perf_counter()
    try:
        elements_file = library_dir / "elements.json"
        payload = json.loads(elements_file.read_text(encoding="utf-8"))
        input_matches = _library_named_matches(payload, input_element_name)
        submit_matches = _library_named_matches(payload, submit_element_name)
        reset_matches = _library_named_matches(payload, reset_element_name)
        input_page_ok, input_selector_ok = _library_item_ok(input_matches, target_url)
        submit_page_ok, submit_selector_ok = _library_item_ok(submit_matches, target_url)
        reset_page_ok, reset_selector_ok = _library_item_ok(reset_matches, target_url)
        passed = (
            library_dir.is_dir()
            and elements_file.is_file()
            and input_page_ok
            and input_selector_ok
            and submit_page_ok
            and submit_selector_ok
            and reset_page_ok
            and reset_selector_ok
        )
        return _result(
            "element_library_preflight",
            "PASS" if passed else "BLOCKED",
            "元素库包含 input元素、提交_html 与 重置_html"
            if passed
            else "元素库缺少 input元素、提交_html 或 重置_html",
            elapsed_ms=round((time.perf_counter() - started) * 1000, 1),
            library_dir_exists=library_dir.is_dir(),
            elements_json_exists=elements_file.is_file(),
            input_named_element_count=len(input_matches),
            input_page_url_matches=input_page_ok,
            input_selector_present=input_selector_ok,
            submit_named_element_count=len(submit_matches),
            submit_page_url_matches=submit_page_ok,
            submit_selector_present=submit_selector_ok,
            reset_named_element_count=len(reset_matches),
            reset_page_url_matches=reset_page_ok,
            reset_selector_present=reset_selector_ok,
        )
    except Exception as exc:  # noqa: BLE001
        return _result(
            "element_library_preflight",
            "BLOCKED",
            "无法读取或验证元素库",
            elapsed_ms=round((time.perf_counter() - started) * 1000, 1),
            **_error_fields(exc),
        )


def connect_library_and_find_elements(
    page: WebBrowser,
    library_dir: Path,
    input_element_name: str,
    submit_element_name: str,
    reset_element_name: str,
    runtime_timeout: float,
    element_timeout: float,
) -> tuple[dict[str, Any], Any | None, WebElement | None, WebElement | None, WebElement | None]:
    started = time.perf_counter()
    package: Any | None = None
    try:
        package = uiautoma.open(str(library_dir), timeout=runtime_timeout)
        input_element = page.find(input_element_name, timeout=element_timeout)
        submit_element = page.find(submit_element_name, timeout=element_timeout)
        reset_element = page.find(reset_element_name, timeout=element_timeout)
        input_name_ok = str(input_element.name or "") == input_element_name
        submit_name_ok = str(submit_element.name or "") == submit_element_name
        reset_name_ok = str(reset_element.name or "") == reset_element_name
        passed = package.web_count > 0 and input_name_ok and submit_name_ok and reset_name_ok
        return (
            _result(
                "element_library_setup",
                "PASS" if passed else "FAIL",
                "已连接元素库并绑定 input元素、提交_html 与 重置_html"
                if passed
                else "元素库连接或元素绑定结果不符合预期",
                elapsed_ms=round((time.perf_counter() - started) * 1000, 1),
                package_opened=True,
                web_element_count=package.web_count,
                input_element_name_ok=input_name_ok,
                submit_element_name_ok=submit_name_ok,
                reset_element_name_ok=reset_name_ok,
            ),
            package,
            input_element,
            submit_element,
            reset_element,
        )
    except Exception as exc:  # noqa: BLE001
        status = _error_status(exc)
        return (
            _result(
                "element_library_setup",
                status,
                "元素库连接被环境阻塞" if status == "BLOCKED" else "无法连接元素库或绑定目标元素",
                elapsed_ms=round((time.perf_counter() - started) * 1000, 1),
                package_opened=package is not None,
                **_error_fields(exc),
            ),
            package,
            None,
            None,
            None,
        )


def _clipboard_form_payload() -> dict[str, Any] | None:
    text_value = clipboard.get_text()
    try:
        payload = json.loads(text_value)
    except Exception:  # noqa: BLE001
        return None
    return payload if isinstance(payload, dict) else None


def _submit_form(submit_element: WebElement) -> tuple[dict[str, Any] | None, str]:
    sentinel = f"uiautoma_clipboard_input_sentinel_{uuid.uuid4().hex}"
    clipboard.set_text(sentinel)
    submit_element.click(simulative=False, delay_after=0.2)
    payload = _clipboard_form_payload()
    if payload is not None:
        return payload, "dom"
    submit_element.click(simulative=True, delay_after=0.25)
    payload = _clipboard_form_payload()
    if payload is not None:
        return payload, "simulative_fallback"
    return None, "failed"


def _reset_form(reset_element: WebElement) -> str:
    reset_element.click(simulative=False, delay_after=0.2)
    return "dom"


def run_clipboard_input_cases(
    page: WebBrowser,
    input_element: WebElement,
    submit_element: WebElement,
    reset_element: WebElement,
) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for case in CLIPBOARD_INPUT_CASES:
        started = time.perf_counter()
        case_id = str(case["case_id"])
        steps = tuple(case.get("steps") or ())
        expected_text = str(case["expected_text"])
        min_input_elapsed_ms = case.get("min_input_elapsed_ms")
        step_logs: list[dict[str, Any]] = []
        try:
            page.activate()
            time.sleep(0.1)
            reset_mode = _reset_form(reset_element)
            return_is_none = True
            input_elapsed_ms = 0.0
            for step in steps:
                text_value = str(step["text"])
                kwargs = dict(step.get("kwargs") or {})
                call_started = time.perf_counter()
                returned = input_element.clipboard_input(text_value, **kwargs)
                step_elapsed_ms = round((time.perf_counter() - call_started) * 1000, 1)
                input_elapsed_ms += step_elapsed_ms
                return_is_none = return_is_none and returned is None
                print(
                    f"{case_id}: clipboard_input({text_value!r}, {kwargs}) -> {returned!r} ({step_elapsed_ms}ms)",
                    file=sys.stderr,
                    flush=True,
                )
                step_logs.append(
                    {
                        "text": text_value,
                        "kwargs": kwargs,
                        "return_is_none": returned is None,
                        "elapsed_ms": step_elapsed_ms,
                    }
                )
            input_elapsed_ms = round(input_elapsed_ms, 1)
            payload, submit_mode = _submit_form(submit_element)
            clipboard_text = "" if payload is None else str(payload.get("text") or "")
            text_ok = clipboard_text == expected_text
            payload_ok = isinstance(payload, dict)
            delay_ok = True
            if min_input_elapsed_ms is not None:
                delay_ok = input_elapsed_ms >= float(min_input_elapsed_ms)
            passed = (
                return_is_none
                and payload_ok
                and text_ok
                and delay_ok
                and submit_mode != "failed"
            )
            results.append(
                _result(
                    case_id,
                    "PASS" if passed else "FAIL",
                    "clipboard_input 后提交剪贴板 JSON 符合预期"
                    if passed
                    else "clipboard_input 返回值或剪贴板 JSON 不符合预期",
                    elapsed_ms=round((time.perf_counter() - started) * 1000, 1),
                    input_elapsed_ms=input_elapsed_ms,
                    return_is_none=return_is_none,
                    reset_mode=reset_mode,
                    submit_mode=submit_mode,
                    expected_text=expected_text,
                    clipboard_text=clipboard_text,
                    text_ok=text_ok,
                    payload_ok=payload_ok,
                    delay_ok=delay_ok,
                    min_input_elapsed_ms=min_input_elapsed_ms,
                    steps=step_logs,
                    clipboard_payload=payload,
                )
            )
        except Exception as exc:  # noqa: BLE001
            status = _error_status(exc)
            results.append(
                _result(
                    case_id,
                    status,
                    "clipboard_input 被环境阻塞" if status == "BLOCKED" else "clipboard_input 调用失败",
                    elapsed_ms=round((time.perf_counter() - started) * 1000, 1),
                    steps=step_logs,
                    **_error_fields(exc),
                )
            )
    return results


def cleanup_resources(
    *,
    package: Any | None,
    page: WebBrowser | None,
    owned_library_dir: Path | None,
) -> dict[str, Any]:
    items: list[dict[str, Any]] = []

    package_item: dict[str, Any] = {"resource": "element_library_connection"}
    if package is None:
        package_item.update(status="PASS", confirmed=True, cleanup_call_needed=False, created=False)
    else:
        try:
            package.close()
            package_item.update(status="PASS", confirmed=True, cleanup_call_needed=True, created=True)
        except Exception as exc:  # noqa: BLE001
            package_item.update(
                status="FAIL",
                confirmed=False,
                cleanup_call_needed=True,
                created=True,
                **_error_fields(exc),
            )
    items.append(package_item)

    page_item: dict[str, Any] = {"resource": "owned_page"}
    if page is None:
        page_item.update(status="PASS", confirmed=True, cleanup_call_needed=False, created=False)
    elif page.raw.get("created_by") not in {"web.create", "profile_launch_recovery"}:
        page_item.update(
            status="FAIL",
            confirmed=False,
            cleanup_call_needed=False,
            created=True,
            reason="owned_page_identity_unknown",
        )
    else:
        try:
            page.close()
            page_item.update(status="PASS", confirmed=True, cleanup_call_needed=True, created=True)
        except Exception as exc:  # noqa: BLE001
            page_item.update(
                status="FAIL",
                confirmed=False,
                cleanup_call_needed=True,
                created=True,
                **_error_fields(exc),
            )
    items.append(page_item)

    library_item: dict[str, Any] = {"resource": "owned_scrubbed_library"}
    if owned_library_dir is None:
        library_item.update(status="PASS", confirmed=True, cleanup_call_needed=False, created=False)
    elif not re.fullmatch(r"[0-9a-f]{32}", owned_library_dir.name):
        library_item.update(
            status="FAIL",
            confirmed=False,
            cleanup_call_needed=False,
            created=True,
            reason="owned_library_identity_unknown",
        )
    else:
        try:
            if owned_library_dir.exists():
                shutil.rmtree(owned_library_dir)
            confirmed = not owned_library_dir.exists()
            library_item.update(
                status="PASS" if confirmed else "FAIL",
                confirmed=confirmed,
                cleanup_call_needed=True,
                created=True,
            )
        except Exception as exc:  # noqa: BLE001
            library_item.update(
                status="FAIL",
                confirmed=False,
                cleanup_call_needed=True,
                created=True,
                **_error_fields(exc),
            )
    items.append(library_item)

    passed = all(item["status"] == "PASS" for item in items)
    return _result(
        "owned_resources_cleanup",
        "PASS" if passed else "FAIL",
        "本次元素库连接、测试页面和临时库副本已逐项确认清理"
        if passed
        else "本次资源未能全部精确清理",
        confirmed=passed,
        attempted_count=len(items),
        cleaned_count=sum(item["status"] == "PASS" for item in items),
        resources=items,
    )


def _exit_code(results: Sequence[dict[str, Any]]) -> int:
    statuses = {str(item.get("status") or "FAIL") for item in results}
    return 1 if "FAIL" in statuses else (2 if "BLOCKED" in statuses else 0)


def _report(args: argparse.Namespace, results: Sequence[dict[str, Any]]) -> tuple[dict[str, Any], int]:
    exit_code = _exit_code(results)
    status = "FAIL" if exit_code == 1 else ("BLOCKED" if exit_code == 2 else "PASS")
    excluded = [
        "edge",
        "cef",
        "auto",
        "anchor / focus_timeout / send_key_delay 单独验收",
        "input_check",
        "后台 append 与 delay_after=1",
        "元素库捕获期 WebSessionId 在不清理时仍可直连当前页面（产品侧会话绑定）",
    ]
    return (
        {
            "api": "uiautoma.web.WebElement.clipboard_input",
            "status": status,
            "exit_code": exit_code,
            "mode": args.mode,
            "profile_directory": args.profile_directory,
            "contract_only": bool(args.contract_only),
            "input_element_name": args.input_element_name,
            "submit_element_name": args.submit_element_name,
            "reset_element_name": args.reset_element_name,
            "input_text": args.input_text,
            "results": list(results),
            "excluded": excluded,
        },
        exit_code,
    )


def _build_clipboard_input_cases(input_text: str) -> tuple[dict[str, Any], ...]:
    base = str(input_text)
    append_prefix = base[: max(1, len(base) // 2)]
    append_suffix = base[len(append_prefix) :] or "X"
    return (
        {
            "case_id": "clipboard_input_background_basic",
            "steps": (
                {
                    "text": base,
                    "kwargs": {"simulative": False, "delay_after": 0.2},
                },
            ),
            "expected_text": base,
        },
        {
            "case_id": "clipboard_input_simulative_basic",
            "steps": (
                {
                    "text": base,
                    "kwargs": {"simulative": True, "delay_after": 0.2},
                },
            ),
            "expected_text": base,
        },
        {
            "case_id": "clipboard_input_simulative_append",
            "steps": (
                {
                    "text": append_prefix,
                    "kwargs": {"simulative": True, "append": False, "delay_after": 0.2},
                },
                {
                    "text": append_suffix,
                    "kwargs": {"simulative": True, "append": True, "delay_after": 0.2},
                },
            ),
            "expected_text": append_prefix + append_suffix,
        },
        {
            "case_id": "clipboard_input_simulative_delay_after",
            "steps": (
                {
                    "text": base,
                    "kwargs": {"simulative": True, "delay_after": 1},
                },
            ),
            "expected_text": base,
            "min_input_elapsed_ms": 900,
        },
    )


def run(args: argparse.Namespace) -> tuple[dict[str, Any], int]:
    global CLIPBOARD_INPUT_CASES
    CLIPBOARD_INPUT_CASES = _build_clipboard_input_cases(args.input_text)
    results = [check_contract()]
    if results[-1]["status"] != "PASS" or args.contract_only:
        return _report(args, results)

    results.append(preflight_target(args.target_url, args.preflight_timeout))
    if results[-1]["status"] != "PASS":
        return _report(args, results)

    results.append(preflight_runtime(args.runtime_timeout))
    if results[-1]["status"] != "PASS":
        return _report(args, results)

    results.append(
        preflight_element_library(
            args.element_library,
            args.input_element_name,
            args.submit_element_name,
            args.reset_element_name,
            args.target_url,
        )
    )
    if results[-1]["status"] != "PASS":
        return _report(args, results)

    run_id = uuid.uuid4().hex
    marked_url = _marked_url(args.target_url, run_id)
    owned_library_dir = PRODUCT_ROOT / ".pytest_tmp" / run_id
    page: WebBrowser | None = None
    package: Any | None = None
    try:
        scrub_result = prepare_scrubbed_library(args.element_library, owned_library_dir)
        results.append(scrub_result)
        if scrub_result["status"] == "PASS":
            page_result, page = prepare_owned_page(
                marked_url,
                args.mode,
                args.load_timeout,
                args.profile_directory,
            )
            results.append(page_result)
            if page_result["status"] == "PASS" and page is not None:
                library_result, package, input_element, submit_element, reset_element = (
                    connect_library_and_find_elements(
                        page,
                        owned_library_dir,
                        args.input_element_name,
                        args.submit_element_name,
                        args.reset_element_name,
                        args.runtime_timeout,
                        args.element_timeout,
                    )
                )
                results.append(library_result)
                if (
                    library_result["status"] == "PASS"
                    and input_element is not None
                    and submit_element is not None
                    and reset_element is not None
                ):
                    results.extend(
                        run_clipboard_input_cases(page, input_element, submit_element, reset_element)
                    )
    except Exception as exc:  # noqa: BLE001
        results.append(
            _result(
                "scenario_orchestration",
                "FAIL",
                "真实场景编排失败",
                **_error_fields(exc),
            )
        )
    finally:
        results.append(
            cleanup_resources(
                package=package,
                page=page,
                owned_library_dir=owned_library_dir if owned_library_dir.exists() else None,
            )
        )
    return _report(args, results)


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="运行 uiautoma.web.WebElement.clipboard_input() 持久化真实浏览器测试。"
    )
    parser.add_argument(
        "--mode",
        default="chrome",
        choices=["chrome"],
        help="用什么浏览器打开测试页面；默认 chrome。",
    )
    parser.add_argument(
        "--profile-directory",
        default=DEFAULT_PROFILE_DIRECTORY,
        help="Chrome Profile 目录标识；默认 Default。",
    )
    parser.add_argument(
        "--target-url",
        default=DEFAULT_TARGET_URL,
        help=f"表单输入测试靶场，默认 {DEFAULT_TARGET_URL}",
    )
    parser.add_argument(
        "--element-library",
        type=Path,
        default=DEFAULT_ELEMENT_LIBRARY,
        help="包含 input元素、提交_html 与 重置_html 的元素库目录。",
    )
    parser.add_argument(
        "--input-element-name",
        default=DEFAULT_INPUT_ELEMENT_NAME,
        help=f"输入目标元素名称，默认 {DEFAULT_INPUT_ELEMENT_NAME}。",
    )
    parser.add_argument(
        "--submit-element-name",
        default=DEFAULT_SUBMIT_ELEMENT_NAME,
        help=f"提交按钮元素名称，默认 {DEFAULT_SUBMIT_ELEMENT_NAME}。",
    )
    parser.add_argument(
        "--reset-element-name",
        default=DEFAULT_RESET_ELEMENT_NAME,
        help=f"重置按钮元素名称，默认 {DEFAULT_RESET_ELEMENT_NAME}。",
    )
    parser.add_argument(
        "--input-text",
        default=DEFAULT_INPUT_TEXT,
        help=f"基础示例输入文本，默认 {DEFAULT_INPUT_TEXT}。",
    )
    parser.add_argument("--preflight-timeout", type=float, default=2.0, help="靶场预检超时秒数，默认 2。")
    parser.add_argument("--runtime-timeout", type=float, default=5.0, help="Runtime 与元素库连接超时秒数，默认 5。")
    parser.add_argument("--load-timeout", type=float, default=20.0, help="页面创建超时秒数，默认 20。")
    parser.add_argument("--element-timeout", type=float, default=5.0, help="元素库目标绑定超时秒数，默认 5。")
    parser.add_argument("--contract-only", action="store_true", help="只检查公开签名，不连接 Runtime、靶场或浏览器。")
    args = parser.parse_args(argv)
    try:
        args.target_url = _validate_url(args.target_url, "--target-url")
    except argparse.ArgumentTypeError as exc:
        parser.error(str(exc))
    args.element_library = args.element_library.resolve()
    args.input_element_name = str(args.input_element_name or "").strip()
    args.submit_element_name = str(args.submit_element_name or "").strip()
    args.reset_element_name = str(args.reset_element_name or "").strip()
    args.input_text = str(args.input_text if args.input_text is not None else "")
    args.profile_directory = str(args.profile_directory or "").strip()
    if not args.input_element_name:
        parser.error("--input-element-name 不能为空")
    if not args.submit_element_name:
        parser.error("--submit-element-name 不能为空")
    if not args.reset_element_name:
        parser.error("--reset-element-name 不能为空")
    if args.input_text == "":
        parser.error("--input-text 不能为空")
    if not args.profile_directory or any(char in args.profile_directory for char in ("/", "\\")):
        parser.error("--profile-directory 必须是不含路径分隔符的 Chrome Profile 目录标识")
    for name in ("preflight_timeout", "runtime_timeout", "load_timeout", "element_timeout"):
        if getattr(args, name) <= 0:
            parser.error(f"--{name.replace('_', '-')} 必须大于 0")
    return args


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    report, exit_code = run(args)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
