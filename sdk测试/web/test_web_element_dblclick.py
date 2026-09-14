"""uiautoma.web.WebElement.dblclick() 持久化真实浏览器测试运行器。

导入本模块不会连接 Runtime、访问靶场或操作浏览器。真实场景打开唯一 Chrome
页面并连接指定元素库；目标断言只直接调用 ``WebElement.dblclick()``，每次双击后
通过“复制最近的一条记录”写入剪贴板再对比结果。

本脚本仅覆盖元素库 ``双击触发`` 的后台（非人工）与模拟人工双击。
"""

from __future__ import annotations

import argparse
import ctypes
import inspect
import json
import os
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

DEFAULT_TARGET_URL = "http://localhost:7199/keys-click-test"
DEFAULT_ELEMENT_LIBRARY = Path(__file__).with_name("web测试元素库")
DEFAULT_DBLCLICK_ELEMENT_NAME = "双击触发"
DEFAULT_COPY_ELEMENT_NAME = "复制最近的一条记录"
DEFAULT_PROFILE_DIRECTORY = "Default"
RUN_QUERY_KEY = "uiautoma_element_dblclick_run"

EXPECTED_PARAMETER_ORDER = (
    "self",
    "button",
    "simulative",
    "keys",
    "delay_after",
    "move_mouse",
    "anchor",
    "allow_coord_fallback",
)
EXPECTED_DEFAULTS = {
    "button": "left",
    "simulative": True,
    "keys": "none",
    "delay_after": 1,
    "move_mouse": None,
    "anchor": None,
    "allow_coord_fallback": False,
}
EXPECTED_KINDS = {
    "self": inspect.Parameter.POSITIONAL_OR_KEYWORD,
    "button": inspect.Parameter.KEYWORD_ONLY,
    "simulative": inspect.Parameter.KEYWORD_ONLY,
    "keys": inspect.Parameter.KEYWORD_ONLY,
    "delay_after": inspect.Parameter.KEYWORD_ONLY,
    "move_mouse": inspect.Parameter.KEYWORD_ONLY,
    "anchor": inspect.Parameter.KEYWORD_ONLY,
    "allow_coord_fallback": inspect.Parameter.KEYWORD_ONLY,
}

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

BACKGROUND_DBLCLICK_CASES: tuple[dict[str, Any], ...] = (
    {
        "case_id": "dblclick_background_keys_none",
        "kwargs": {"button": "left", "simulative": False, "keys": "none", "delay_after": 0.2},
        "expected_button_id": "btn-dblclick-target",
        "expected_event_type": "dblclick",
        "expected_keys": "none",
        "expected_source": "background",
        "expected_trusted": False,
    },
)

SIMULATIVE_DBLCLICK_CASES: tuple[dict[str, Any], ...] = (
    {
        "case_id": "dblclick_simulative_keys_none",
        "kwargs": {"button": "left", "simulative": True, "keys": "none", "delay_after": 0.2},
        "expected_button_id": "btn-dblclick-target",
        "expected_event_type": "dblclick",
        "expected_keys": "none",
        "expected_source": "simulative",
        "expected_trusted": True,
    },
)


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


def _clipboard_record() -> dict[str, Any] | None:
    text = clipboard.get_text()
    try:
        payload = json.loads(text)
    except Exception:  # noqa: BLE001
        return None
    return payload if isinstance(payload, dict) else None


def _public_record_fields(record: dict[str, Any] | None, expected_button_id: str) -> dict[str, Any]:
    if not isinstance(record, dict):
        return {
            "button_id_ok": False,
            "event_type": "",
            "detected_keys": "",
            "click_source": "",
            "is_trusted": None,
        }
    return {
        "button_id_ok": str(record.get("buttonId") or "") == expected_button_id,
        "event_type": str(record.get("eventType") or ""),
        "detected_keys": str(record.get("detectedKeys") or ""),
        "click_source": str(record.get("clickSource") or ""),
        "is_trusted": record.get("isTrusted"),
    }


def _source_ok(click_source: str, expected_source: str) -> bool:
    text = str(click_source or "")
    if expected_source == "background":
        return ("JS" in text) or ("插件" in text) or ("模拟" in text)
    if expected_source == "simulative":
        return "真实鼠标" in text
    return False


def check_contract() -> dict[str, Any]:
    try:
        signature = inspect.signature(WebElement.dblclick)
        parameters = signature.parameters
        order_ok = tuple(parameters) == EXPECTED_PARAMETER_ORDER
        defaults_ok = all(parameters[name].default == value for name, value in EXPECTED_DEFAULTS.items())
        kinds_ok = all(parameters[name].kind == value for name, value in EXPECTED_KINDS.items())
        return_ok = signature.return_annotation in {None, "None", type(None)}
        passed = order_ok and defaults_ok and kinds_ok and return_ok
        return _result(
            "api_contract",
            "PASS" if passed else "FAIL",
            "公开签名符合当前合同" if passed else "公开签名与当前合同不一致",
            parameter_order_ok=order_ok,
            defaults_ok=defaults_ok,
            parameter_kinds_ok=kinds_ok,
            return_annotation_ok=return_ok,
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
            "双击测试靶场可访问" if passed else "双击测试靶场未返回成功状态",
            elapsed_ms=round((time.perf_counter() - started) * 1000, 1),
            http_status=status_code,
        )
    except Exception as exc:  # noqa: BLE001
        return _result(
            "target_preflight",
            "BLOCKED",
            "双击测试靶场不可访问",
            elapsed_ms=round((time.perf_counter() - started) * 1000, 1),
            **_error_fields(exc),
        )


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
    dblclick_element_name: str,
    copy_element_name: str,
    target_url: str,
) -> dict[str, Any]:
    started = time.perf_counter()
    try:
        elements_file = library_dir / "elements.json"
        payload = json.loads(elements_file.read_text(encoding="utf-8"))
        dblclick_matches = _library_named_matches(payload, dblclick_element_name)
        copy_matches = _library_named_matches(payload, copy_element_name)
        dblclick_page_ok, dblclick_selector_ok = _library_item_ok(dblclick_matches, target_url)
        copy_page_ok, copy_selector_ok = _library_item_ok(copy_matches, target_url)
        passed = (
            library_dir.is_dir()
            and elements_file.is_file()
            and dblclick_page_ok
            and dblclick_selector_ok
            and copy_page_ok
            and copy_selector_ok
        )
        return _result(
            "element_library_preflight",
            "PASS" if passed else "BLOCKED",
            "元素库包含双击触发与复制记录元素" if passed else "元素库缺少双击触发或复制记录元素",
            elapsed_ms=round((time.perf_counter() - started) * 1000, 1),
            library_dir_exists=library_dir.is_dir(),
            elements_json_exists=elements_file.is_file(),
            dblclick_named_element_count=len(dblclick_matches),
            copy_named_element_count=len(copy_matches),
            dblclick_page_url_matches=dblclick_page_ok,
            copy_page_url_matches=copy_page_ok,
            dblclick_selector_present=dblclick_selector_ok,
            copy_selector_present=copy_selector_ok,
        )
    except Exception as exc:  # noqa: BLE001
        return _result(
            "element_library_preflight",
            "BLOCKED",
            "无法读取或验证元素库",
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
                "已打开本次唯一双击测试页面" if passed else "双击测试页面创建结果不完整",
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
                "无法打开本次双击测试页面",
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


def _focus_window_with_attached_input(user32: Any, hwnd: int) -> tuple[bool, str]:
    if not hwnd or not user32.IsWindow(hwnd):
        return False, "window_unavailable"
    user32.SetForegroundWindow(hwnd)
    deadline = time.monotonic() + 0.3
    while time.monotonic() < deadline:
        if int(user32.GetForegroundWindow() or 0) == hwnd:
            return True, "set_foreground_window"
        time.sleep(0.02)

    kernel32 = ctypes.windll.kernel32
    current_thread_id = int(kernel32.GetCurrentThreadId() or 0)
    foreground_hwnd = int(user32.GetForegroundWindow() or 0)
    foreground_thread_id = int(user32.GetWindowThreadProcessId(foreground_hwnd, None) or 0)
    target_thread_id = int(user32.GetWindowThreadProcessId(hwnd, None) or 0)
    attached_thread_ids: list[int] = []
    try:
        for thread_id in {foreground_thread_id, target_thread_id}:
            if (
                thread_id > 0
                and thread_id != current_thread_id
                and user32.AttachThreadInput(current_thread_id, thread_id, True)
            ):
                attached_thread_ids.append(thread_id)
        user32.BringWindowToTop(hwnd)
        user32.SetForegroundWindow(hwnd)
        user32.SetFocus(hwnd)
        deadline = time.monotonic() + 0.5
        while time.monotonic() < deadline:
            if int(user32.GetForegroundWindow() or 0) == hwnd:
                return True, "attach_thread_input"
            time.sleep(0.02)
        return False, "attach_thread_input_failed"
    finally:
        for thread_id in reversed(attached_thread_ids):
            user32.AttachThreadInput(current_thread_id, thread_id, False)


def prepare_mouse_click_window(page: WebBrowser) -> tuple[dict[str, Any], dict[str, Any] | None]:
    started = time.perf_counter()

    class _Point(ctypes.Structure):
        _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]

    class _Rect(ctypes.Structure):
        _fields_ = [
            ("left", ctypes.c_long),
            ("top", ctypes.c_long),
            ("right", ctypes.c_long),
            ("bottom", ctypes.c_long),
        ]

    class _WindowPlacement(ctypes.Structure):
        _fields_ = [
            ("length", ctypes.c_uint),
            ("flags", ctypes.c_uint),
            ("show_cmd", ctypes.c_uint),
            ("min_position", _Point),
            ("max_position", _Point),
            ("normal_position", _Rect),
        ]

    try:
        if os.name != "nt":
            return (
                _result(
                    "mouse_click_window_setup",
                    "BLOCKED",
                    "真实鼠标双击窗口准备只支持 Windows",
                    elapsed_ms=round((time.perf_counter() - started) * 1000, 1),
                ),
                None,
            )
        user32 = ctypes.windll.user32
        previous_foreground = int(user32.GetForegroundWindow() or 0)
        page_title = str(page.title or "").strip()
        page_host = ""
        try:
            page_host = str(urlsplit(str(page.url or "")).hostname or "").casefold()
        except ValueError:
            page_host = ""

        def window_title(candidate: int) -> str:
            title_buffer = ctypes.create_unicode_buffer(512)
            user32.GetWindowTextW(candidate, title_buffer, len(title_buffer))
            return str(title_buffer.value or "")

        def is_chrome_window(candidate: int) -> bool:
            if not candidate or not user32.IsWindowVisible(candidate):
                return False
            class_buffer = ctypes.create_unicode_buffer(256)
            user32.GetClassNameW(candidate, class_buffer, len(class_buffer))
            title = window_title(candidate)
            return (
                str(class_buffer.value or "") == "Chrome_WidgetWin_1"
                and "google chrome" in title.casefold()
            )

        def title_score(candidate: int) -> int:
            title = window_title(candidate).casefold()
            score = 0
            if page_title and page_title.casefold() in title:
                score += 100
            if "元素点击" in title or "keys-click" in title:
                score += 40
            if page_host and page_host in title:
                score += 20
            if "localhost" in title:
                score += 10
            return score

        hwnd = 0
        selection_method = ""
        for _ in range(8):
            page.activate()
            time.sleep(0.25)
            foreground = int(user32.GetForegroundWindow() or 0)
            if is_chrome_window(foreground):
                hwnd = foreground
                selection_method = "foreground_after_activate"
                break

        if not hwnd:
            candidates: list[int] = []
            enum_proc_type = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)

            def enum_proc(candidate: int, _lparam: int) -> bool:
                candidate_int = int(candidate)
                if is_chrome_window(candidate_int):
                    candidates.append(candidate_int)
                return True

            user32.EnumWindows(enum_proc_type(enum_proc), None)
            if len(candidates) == 1:
                hwnd = candidates[0]
                selection_method = "unique_visible_chrome_window"
            elif candidates:
                ranked = sorted(
                    ((title_score(item), item) for item in candidates),
                    key=lambda pair: pair[0],
                    reverse=True,
                )
                best_score, best_hwnd = ranked[0]
                second_score = ranked[1][0] if len(ranked) > 1 else -1
                if best_score > 0 and best_score > second_score:
                    hwnd = best_hwnd
                    selection_method = "title_matched_chrome_window"

        identity_ok = is_chrome_window(hwnd)
        if not identity_ok:
            return (
                _result(
                    "mouse_click_window_setup",
                    "BLOCKED",
                    "无法从前台或标题匹配安全识别本次 Chrome 页面窗口",
                    elapsed_ms=round((time.perf_counter() - started) * 1000, 1),
                    window_identity_ok=False,
                    selection_method=selection_method,
                ),
                None,
            )

        placement = _WindowPlacement()
        placement.length = ctypes.sizeof(_WindowPlacement)
        if not user32.GetWindowPlacement(hwnd, ctypes.byref(placement)):
            raise OSError("GetWindowPlacement failed")
        initial_state = (
            "minimized"
            if user32.IsIconic(hwnd)
            else "maximized"
            if user32.IsZoomed(hwnd)
            else "normal"
        )
        placement_changed = initial_state != "normal"
        if placement_changed:
            user32.ShowWindow(hwnd, 9)
            deadline = time.monotonic() + 2.0
            while time.monotonic() < deadline:
                if user32.IsWindowVisible(hwnd) and not user32.IsIconic(hwnd) and not user32.IsZoomed(hwnd):
                    break
                time.sleep(0.05)
        user32.ShowWindow(hwnd, 5)
        focused, focus_method = _focus_window_with_attached_input(user32, hwnd)
        normalized = bool(
            user32.IsWindowVisible(hwnd)
            and not user32.IsIconic(hwnd)
            and not user32.IsZoomed(hwnd)
            and focused
        )
        state = {
            "hwnd": hwnd,
            "placement": placement,
            "placement_changed": placement_changed,
            "initial_state": initial_state,
            "previous_foreground": previous_foreground,
            "focus_method": focus_method,
        }
        return (
            _result(
                "mouse_click_window_setup",
                "PASS" if normalized else "BLOCKED",
                "本次 Chrome 页面窗口已处于可执行真实鼠标双击的 normal 状态"
                if normalized
                else "无法将本次 Chrome 页面窗口准备为 normal 状态",
                elapsed_ms=round((time.perf_counter() - started) * 1000, 1),
                window_identity_ok=True,
                window_selection_method=selection_method,
                initial_window_state=initial_state,
                placement_changed=placement_changed,
                normalized_to_normal=normalized,
                focused=focused,
                focus_method=focus_method,
            ),
            state,
        )
    except Exception as exc:  # noqa: BLE001
        return (
            _result(
                "mouse_click_window_setup",
                "BLOCKED",
                "无法准备真实鼠标双击所需的 Chrome 窗口状态",
                elapsed_ms=round((time.perf_counter() - started) * 1000, 1),
                **_error_fields(exc),
            ),
            None,
        )


def _restore_mouse_click_window(state: dict[str, Any] | None) -> dict[str, Any]:
    item: dict[str, Any] = {"resource": "chrome_window_state"}
    if state is None:
        item.update(status="PASS", confirmed=True, cleanup_call_needed=False, prepared=False)
        return item
    changed = bool(state.get("placement_changed"))
    initial_state = str(state.get("initial_state") or "unknown")
    hwnd = int(state.get("hwnd") or 0)
    previous_foreground = int(state.get("previous_foreground") or 0)
    item.update(initial_state=initial_state, prepared=True)
    try:
        user32 = ctypes.windll.user32
        placement_requested = False
        placement_confirmed = True
        window_closed_with_owned_page = False
        if changed and hwnd and user32.IsWindow(hwnd):
            placement = state.get("placement")
            placement_requested = bool(user32.SetWindowPlacement(hwnd, ctypes.byref(placement)))
            deadline = time.monotonic() + 2.0
            placement_confirmed = False
            while time.monotonic() < deadline:
                placement_confirmed = (
                    bool(user32.IsZoomed(hwnd))
                    if initial_state == "maximized"
                    else bool(user32.IsIconic(hwnd))
                    if initial_state == "minimized"
                    else not user32.IsZoomed(hwnd) and not user32.IsIconic(hwnd)
                )
                if placement_confirmed:
                    break
                time.sleep(0.05)
        elif changed:
            window_closed_with_owned_page = True

        focus_restore_needed = bool(
            previous_foreground
            and previous_foreground != hwnd
            and user32.IsWindow(previous_foreground)
        )
        if focus_restore_needed:
            focus_restored, focus_restore_method = _focus_window_with_attached_input(
                user32,
                previous_foreground,
            )
        else:
            focus_restored = True
            focus_restore_method = "not_needed"
        confirmed = placement_confirmed and focus_restored
        item.update(
            status="PASS" if confirmed else "FAIL",
            confirmed=bool(confirmed),
            cleanup_call_needed=changed or focus_restore_needed,
            placement_restore_requested=placement_requested,
            placement_restored=placement_confirmed,
            window_closed_with_owned_page=window_closed_with_owned_page,
            focus_restore_needed=focus_restore_needed,
            focus_restored=focus_restored,
            focus_restore_method=focus_restore_method,
        )
    except Exception as exc:  # noqa: BLE001
        item.update(
            status="FAIL",
            confirmed=False,
            cleanup_call_needed=changed or previous_foreground != hwnd,
            **_error_fields(exc),
        )
    return item


def connect_library_and_find_elements(
    page: WebBrowser,
    library_dir: Path,
    dblclick_element_name: str,
    copy_element_name: str,
    runtime_timeout: float,
    element_timeout: float,
) -> tuple[dict[str, Any], Any | None, WebElement | None, WebElement | None]:
    started = time.perf_counter()
    package = None
    try:
        package = uiautoma.open(
            str(library_dir),
            timeout=runtime_timeout,
            connect_timeout=runtime_timeout,
        )
        dblclick_element = page.find(dblclick_element_name, timeout=element_timeout)
        copy_element = page.find(copy_element_name, timeout=element_timeout)
        dblclick_name_ok = str(dblclick_element.name or "") == dblclick_element_name
        copy_name_ok = str(copy_element.name or "") == copy_element_name
        passed = package.web_count > 0 and dblclick_name_ok and copy_name_ok
        return (
            _result(
                "element_library_setup",
                "PASS" if passed else "FAIL",
                "已连接元素库并绑定双击触发与复制元素"
                if passed
                else "元素库连接或元素绑定结果不符合预期",
                elapsed_ms=round((time.perf_counter() - started) * 1000, 1),
                package_opened=True,
                web_element_count=package.web_count,
                dblclick_element_name_ok=dblclick_name_ok,
                copy_element_name_ok=copy_name_ok,
            ),
            package,
            dblclick_element,
            copy_element,
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
        )


def _copy_latest_record(copy_element: WebElement) -> tuple[dict[str, Any] | None, str]:
    sentinel = f"uiautoma_dblclick_sentinel_{uuid.uuid4().hex}"
    clipboard.set_text(sentinel)
    copy_element.click(simulative=False, delay_after=0.2)
    record = _clipboard_record()
    if record is not None:
        return record, "dom"
    copy_element.click(simulative=True, delay_after=0.25)
    record = _clipboard_record()
    if record is not None:
        return record, "simulative_fallback"
    return None, "failed"


def run_dblclick_case(
    page: WebBrowser,
    dblclick_element: WebElement,
    copy_element: WebElement,
    case: dict[str, Any],
) -> dict[str, Any]:
    started = time.perf_counter()
    case_id = str(case["case_id"])
    kwargs = dict(case["kwargs"])
    expected_keys = str(case["expected_keys"])
    expected_source = str(case["expected_source"])
    expected_event = str(case["expected_event_type"])
    expected_button_id = str(case["expected_button_id"])
    expected_trusted = bool(case["expected_trusted"])
    simulative = bool(kwargs.get("simulative"))
    try:
        page.activate()
        time.sleep(0.1)
        call_started = time.perf_counter()
        returned = dblclick_element.dblclick(**kwargs)
        elapsed_ms = round((time.perf_counter() - call_started) * 1000, 1)
        return_is_none = returned is None
        time.sleep(0.1)
        record, copy_mode = _copy_latest_record(copy_element)
        fields = _public_record_fields(record, expected_button_id)
        source_ok = _source_ok(str(fields["click_source"]), expected_source)
        keys_ok = fields["detected_keys"] == expected_keys
        event_ok = fields["event_type"] == expected_event
        trusted_ok = fields["is_trusted"] is expected_trusted
        passed = (
            return_is_none
            and record is not None
            and fields["button_id_ok"]
            and event_ok
            and keys_ok
            and source_ok
            and trusted_ok
            and copy_mode != "failed"
        )
        detail_prefix = "模拟人工" if simulative else "后台"
        return _result(
            case_id,
            "PASS" if passed else "FAIL",
            f"{detail_prefix} dblclick 与剪贴板记录符合预期"
            if passed
            else f"{detail_prefix} dblclick 返回值或剪贴板记录不符合预期",
            elapsed_ms=round((time.perf_counter() - started) * 1000, 1),
            dblclick_elapsed_ms=elapsed_ms,
            return_is_none=return_is_none,
            copy_mode=copy_mode,
            expected_keys=expected_keys,
            expected_event_type=expected_event,
            expected_button_id=expected_button_id,
            expected_source=expected_source,
            delay_after=kwargs.get("delay_after"),
            event_ok=event_ok,
            keys_ok=keys_ok,
            source_ok=source_ok,
            trusted_ok=trusted_ok,
            simulative=simulative,
            button=kwargs.get("button"),
            **fields,
        )
    except Exception as exc:  # noqa: BLE001
        status = _error_status(exc)
        detail_prefix = "模拟人工" if simulative else "后台"
        return _result(
            case_id,
            status,
            f"{detail_prefix} dblclick 被环境阻塞"
            if status == "BLOCKED"
            else f"{detail_prefix} dblclick 调用失败",
            elapsed_ms=round((time.perf_counter() - started) * 1000, 1),
            simulative=simulative,
            button=kwargs.get("button"),
            **_error_fields(exc),
        )


def cleanup_resources(
    *,
    package: Any | None,
    page: WebBrowser | None,
    click_window_state: dict[str, Any] | None,
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

    items.append(_restore_mouse_click_window(click_window_state))

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
        "本次元素库连接、测试页面、窗口状态和临时库副本已逐项确认清理"
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
        "button=right",
        "辅助键矩阵 keys",
        "move_mouse 鼠标轨迹可见性",
        "anchor 九宫格与偏移",
        "anchor='random'",
        "allow_coord_fallback=True",
        "delay_after=1 默认耗时",
        "double_click 别名单独验收",
        "元素库捕获期 WebSessionId 在不清理时仍可直连当前页面（产品侧会话绑定）",
    ]
    return (
        {
            "api": "uiautoma.web.WebElement.dblclick",
            "status": status,
            "exit_code": exit_code,
            "mode": args.mode,
            "profile_directory": args.profile_directory,
            "contract_only": bool(args.contract_only),
            "dblclick_element_name": args.dblclick_element_name,
            "copy_element_name": args.copy_element_name,
            "results": list(results),
            "excluded": excluded,
        },
        exit_code,
    )


def run(args: argparse.Namespace) -> tuple[dict[str, Any], int]:
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
            args.dblclick_element_name,
            args.copy_element_name,
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
    click_window_state: dict[str, Any] | None = None
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
                (
                    library_result,
                    package,
                    dblclick_element,
                    copy_element,
                ) = connect_library_and_find_elements(
                    page,
                    owned_library_dir,
                    args.dblclick_element_name,
                    args.copy_element_name,
                    args.runtime_timeout,
                    args.element_timeout,
                )
                results.append(library_result)
                if (
                    library_result["status"] == "PASS"
                    and dblclick_element is not None
                    and copy_element is not None
                ):
                    for case in BACKGROUND_DBLCLICK_CASES:
                        results.append(
                            run_dblclick_case(page, dblclick_element, copy_element, case)
                        )
                        if results[-1]["status"] != "PASS":
                            break
                    if results[-1]["status"] == "PASS":
                        window_result, click_window_state = prepare_mouse_click_window(page)
                        results.append(window_result)
                        if window_result["status"] == "PASS":
                            for case in SIMULATIVE_DBLCLICK_CASES:
                                results.append(
                                    run_dblclick_case(page, dblclick_element, copy_element, case)
                                )
                                if results[-1]["status"] != "PASS":
                                    break
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
                click_window_state=click_window_state,
                owned_library_dir=owned_library_dir if owned_library_dir.exists() else None,
            )
        )
    return _report(args, results)


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="运行 uiautoma.web.WebElement.dblclick() 持久化真实浏览器测试。"
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
        help=f"双击测试靶场，默认 {DEFAULT_TARGET_URL}",
    )
    parser.add_argument(
        "--element-library",
        type=Path,
        default=DEFAULT_ELEMENT_LIBRARY,
        help="包含双击与复制元素的元素库目录。",
    )
    parser.add_argument(
        "--dblclick-element-name",
        default=DEFAULT_DBLCLICK_ELEMENT_NAME,
        help=f"双击目标元素名称，默认 {DEFAULT_DBLCLICK_ELEMENT_NAME}。",
    )
    parser.add_argument(
        "--copy-element-name",
        default=DEFAULT_COPY_ELEMENT_NAME,
        help=f"复制最近记录元素名称，默认 {DEFAULT_COPY_ELEMENT_NAME}。",
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
    args.dblclick_element_name = str(args.dblclick_element_name or "").strip()
    args.copy_element_name = str(args.copy_element_name or "").strip()
    args.profile_directory = str(args.profile_directory or "").strip()
    if not args.dblclick_element_name:
        parser.error("--dblclick-element-name 不能为空")
    if not args.copy_element_name:
        parser.error("--copy-element-name 不能为空")
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
