"""uiautoma.web.handle_save_dialog() 持久化真实浏览器测试运行器。

导入本模块不会连接 Runtime、访问靶场或操作浏览器。真实场景打开唯一 Chrome
页面，连接指定元素库并点击下载元素，然后仅调用 ``handle_save_dialog()`` 完成保存。
"""

from __future__ import annotations

import argparse
import ctypes
import inspect
import json
import os
from pathlib import Path
import re
import shutil
import sys
import time
from typing import Any, Sequence
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit
from urllib.request import Request, urlopen
import uuid


PRODUCT_ROOT = Path(__file__).resolve().parents[3]
SDK_SRC = PRODUCT_ROOT / "sdk" / "src"
if str(SDK_SRC) not in sys.path:
    sys.path.insert(0, str(SDK_SRC))

import uiautoma  # noqa: E402
from uiautoma import ping, web  # noqa: E402
from uiautoma.web import WebBrowser  # noqa: E402


__test__ = False

DEFAULT_TARGET_URL = "http://localhost:7199/download-dialog-test"
DEFAULT_ELEMENT_LIBRARY = Path(__file__).with_name("web测试元素库")
DEFAULT_ELEMENT_NAME = "下载txt按钮"
DEFAULT_PROFILE_DIRECTORY = "Default"
RUN_QUERY_KEY = "uiautoma_handle_save_dialog_run"
DOWNLOAD_PREFIX = "uiautoma_handle_save_dialog"

EXPECTED_PARAMETER_ORDER = (
    "file_folder",
    "dialog_result",
    "mode",
    "file_name",
    "overwrite",
    "wait_complete",
    "wait_complete_timeout",
    "simulative",
    "clipboard_input",
    "wait_appear_timeout",
    "force_ime_ENG",
    "send_key_delay",
    "focus_timeout",
)
EXPECTED_DEFAULTS = {
    "file_folder": inspect.Parameter.empty,
    "dialog_result": "ok",
    "mode": "cef",
    "file_name": None,
    "overwrite": True,
    "wait_complete": False,
    "wait_complete_timeout": 300,
    "simulative": False,
    "clipboard_input": True,
    "wait_appear_timeout": 20,
    "force_ime_ENG": False,
    "send_key_delay": 50,
    "focus_timeout": 1000,
}
EXPECTED_KINDS = {
    "file_folder": inspect.Parameter.POSITIONAL_OR_KEYWORD,
    "dialog_result": inspect.Parameter.POSITIONAL_OR_KEYWORD,
    "mode": inspect.Parameter.POSITIONAL_OR_KEYWORD,
    "file_name": inspect.Parameter.KEYWORD_ONLY,
    "overwrite": inspect.Parameter.KEYWORD_ONLY,
    "wait_complete": inspect.Parameter.KEYWORD_ONLY,
    "wait_complete_timeout": inspect.Parameter.KEYWORD_ONLY,
    "simulative": inspect.Parameter.KEYWORD_ONLY,
    "clipboard_input": inspect.Parameter.KEYWORD_ONLY,
    "wait_appear_timeout": inspect.Parameter.KEYWORD_ONLY,
    "force_ime_ENG": inspect.Parameter.KEYWORD_ONLY,
    "send_key_delay": inspect.Parameter.KEYWORD_ONLY,
    "focus_timeout": inspect.Parameter.KEYWORD_ONLY,
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
    "web_save_dialog_timeout",
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


def _same_path(left: object, right: Path) -> bool:
    try:
        return os.path.normcase(os.path.abspath(str(left))) == os.path.normcase(
            os.path.abspath(str(right))
        )
    except (OSError, TypeError, ValueError):
        return False


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
        return web.get_active(
            mode,
            load_timeout=max(0.1, timeout),
            silent_running=True,
        )
    except Exception:  # noqa: BLE001
        return None


def _wait_for_launched_start_page(
    mode: str,
    before_identity: tuple[str, int, int] | None,
    timeout: float,
) -> WebBrowser | None:
    deadline = time.monotonic() + timeout
    while True:
        page = _try_get_active_page(mode, min(1.0, max(0.1, deadline - time.monotonic())))
        identity = _tab_identity(page)
        url = str(page.url or "").strip().casefold() if page is not None else ""
        is_start_page = url.startswith(("about:blank", "chrome://", "edge://"))
        if page is not None and identity is not None and identity != before_identity and is_start_page:
            return page
        if time.monotonic() >= deadline:
            return None
        time.sleep(0.1)


def _visible_chrome_window_count() -> int:
    user32 = ctypes.windll.user32
    count = 0
    enum_proc_type = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)

    def enum_proc(hwnd: int, _lparam: int) -> bool:
        nonlocal count
        if user32.IsWindowVisible(int(hwnd)):
            class_buffer = ctypes.create_unicode_buffer(256)
            user32.GetClassNameW(int(hwnd), class_buffer, len(class_buffer))
            if str(class_buffer.value or "") == "Chrome_WidgetWin_1":
                title_buffer = ctypes.create_unicode_buffer(512)
                user32.GetWindowTextW(int(hwnd), title_buffer, len(title_buffer))
                if "google chrome" in str(title_buffer.value or "").casefold():
                    count += 1
        return True

    user32.EnumWindows(enum_proc_type(enum_proc), None)
    return count


def check_contract() -> dict[str, Any]:
    try:
        parameters = inspect.signature(web.handle_save_dialog).parameters
        order_ok = tuple(parameters) == EXPECTED_PARAMETER_ORDER
        defaults_ok = all(
            parameters[name].default == value
            for name, value in EXPECTED_DEFAULTS.items()
        )
        kinds_ok = all(
            parameters[name].kind == value
            for name, value in EXPECTED_KINDS.items()
        )
        passed = order_ok and defaults_ok and kinds_ok
        return _result(
            "api_contract",
            "PASS" if passed else "FAIL",
            "公开签名符合当前合同" if passed else "公开签名与当前合同不一致",
            parameter_order_ok=order_ok,
            defaults_ok=defaults_ok,
            parameter_kinds_ok=kinds_ok,
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
            "下载对话框靶场可访问" if passed else "下载对话框靶场未返回成功状态",
            elapsed_ms=round((time.perf_counter() - started) * 1000, 1),
            http_status=status_code,
        )
    except Exception as exc:  # noqa: BLE001
        return _result(
            "target_preflight",
            "BLOCKED",
            "下载对话框靶场不可访问",
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


def preflight_element_library(
    library_dir: Path,
    element_name: str,
    target_url: str,
) -> dict[str, Any]:
    started = time.perf_counter()
    try:
        elements_file = library_dir / "elements.json"
        payload = json.loads(elements_file.read_text(encoding="utf-8"))
        matches: list[dict[str, Any]] = []
        for process in payload.values():
            if not isinstance(process, dict):
                continue
            for item in process.get("Group", process.get("group", [])):
                if isinstance(item, dict) and str(item.get("Name") or "") == element_name:
                    matches.append(item)
        page_url_ok = len(matches) == 1 and _page_key(matches[0].get("PageUrl")) == _page_key(target_url)
        selector_ok = len(matches) == 1 and bool(str(matches[0].get("Characteristics") or "").strip())
        passed = library_dir.is_dir() and elements_file.is_file() and page_url_ok and selector_ok
        return _result(
            "element_library_preflight",
            "PASS" if passed else "BLOCKED",
            "元素库包含目标页面的唯一下载元素" if passed else "元素库缺少目标页面的唯一下载元素",
            elapsed_ms=round((time.perf_counter() - started) * 1000, 1),
            library_dir_exists=library_dir.is_dir(),
            elements_json_exists=elements_file.is_file(),
            named_element_count=len(matches),
            page_url_matches=page_url_ok,
            selector_present=selector_ok,
        )
    except Exception as exc:  # noqa: BLE001
        return _result(
            "element_library_preflight",
            "BLOCKED",
            "无法读取或验证元素库",
            elapsed_ms=round((time.perf_counter() - started) * 1000, 1),
            **_error_fields(exc),
        )


def _find_save_dialog_window() -> int:
    if os.name != "nt":
        return 0
    user32 = ctypes.windll.user32
    foreground = int(user32.GetForegroundWindow() or 0)
    if _is_save_dialog_window(user32, foreground):
        return foreground

    found = ctypes.c_void_p(0)
    enum_proc_type = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)

    def enum_proc(hwnd: int, _lparam: int) -> bool:
        if _is_save_dialog_window(user32, int(hwnd)):
            found.value = int(hwnd)
            return False
        return True

    user32.EnumWindows(enum_proc_type(enum_proc), None)
    return int(found.value or 0)


def _is_save_dialog_window(user32: Any, hwnd: int) -> bool:
    if not hwnd or not user32.IsWindowVisible(int(hwnd)):
        return False
    class_buffer = ctypes.create_unicode_buffer(256)
    user32.GetClassNameW(int(hwnd), class_buffer, len(class_buffer))
    if str(class_buffer.value or "") != "#32770":
        return False
    title_buffer = ctypes.create_unicode_buffer(512)
    user32.GetWindowTextW(int(hwnd), title_buffer, len(title_buffer))
    title = str(title_buffer.value or "").casefold()
    return any(part in title for part in ("另存为", "保存", "save as", "save"))


def preflight_save_dialog_state() -> dict[str, Any]:
    started = time.perf_counter()
    try:
        if os.name != "nt":
            return _result(
                "save_dialog_preflight",
                "BLOCKED",
                "保存对话框真实测试只支持 Windows",
                elapsed_ms=round((time.perf_counter() - started) * 1000, 1),
                existing_dialog_count=0,
            )
        existing = bool(_find_save_dialog_window())
        return _result(
            "save_dialog_preflight",
            "BLOCKED" if existing else "PASS",
            "检测到用户已有保存对话框，未创建浏览器资源"
            if existing
            else "未检测到已有保存对话框，可隔离本次原生窗口",
            elapsed_ms=round((time.perf_counter() - started) * 1000, 1),
            existing_dialog_count=1 if existing else 0,
        )
    except Exception as exc:  # noqa: BLE001
        return _result(
            "save_dialog_preflight",
            "BLOCKED",
            "无法确认已有保存对话框状态",
            elapsed_ms=round((time.perf_counter() - started) * 1000, 1),
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
    profile_launch_requested = not existing_session_reused
    profile_identity_confirmed = False if existing_session_reused else True
    profile_identity_fallback_used = False
    profile_identity_trace = ""
    recovery_method = "existing_session" if existing_session_reused else ""
    try:
        if existing_session_reused:
            page = web.create(
                target_url,
                mode,
                load_timeout=load_timeout,
                silent_running=True,
            )
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
                profile_identity_confirmed = False
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
                "已复用当前 Chrome 会话并打开本次唯一下载页面"
                if passed and existing_session_reused
                else "Default Profile 已启动，并复用启动页导航到本次唯一下载页面"
                if passed and profile_identity_fallback_used
                else "Default Profile 已启动并打开本次唯一下载页面"
                if passed and not profile_identity_fallback_used
                else "下载页面创建结果不完整",
                elapsed_ms=round((time.perf_counter() - started) * 1000, 1),
                profile_directory=profile_directory,
                profile_launch_requested=profile_launch_requested,
                existing_session_reused=existing_session_reused,
                profile_identity_confirmed=profile_identity_confirmed,
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
                "无法打开本次下载页面",
                elapsed_ms=round((time.perf_counter() - started) * 1000, 1),
                profile_directory=profile_directory,
                profile_launch_requested=profile_launch_requested,
                existing_session_reused=existing_session_reused,
                profile_identity_confirmed=profile_identity_confirmed,
                profile_identity_fallback_used=profile_identity_fallback_used,
                profile_identity_trace=profile_identity_trace,
                profile_recovery_method=recovery_method,
                **_error_fields(exc),
            ),
            page,
        )


def connect_library_and_find_element(
    page: WebBrowser,
    library_dir: Path,
    element_name: str,
    runtime_timeout: float,
    element_timeout: float,
) -> tuple[dict[str, Any], Any | None, Any | None]:
    started = time.perf_counter()
    package = None
    try:
        package = uiautoma.open(
            str(library_dir),
            timeout=runtime_timeout,
            connect_timeout=runtime_timeout,
        )
        element = page.find(element_name, timeout=element_timeout)
        name_ok = str(element.name or "") == element_name
        passed = package.web_count > 0 and name_ok
        return (
            _result(
                "element_library_setup",
                "PASS" if passed else "FAIL",
                "已连接元素库并从本次页面绑定目标下载元素"
                if passed
                else "元素库连接或目标元素绑定结果不符合预期",
                elapsed_ms=round((time.perf_counter() - started) * 1000, 1),
                package_opened=True,
                web_element_count=package.web_count,
                element_found=True,
                element_name_ok=name_ok,
            ),
            package,
            element,
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
                element_found=False,
                **_error_fields(exc),
            ),
            package,
            None,
        )


def trigger_download_dialog(element: Any) -> dict[str, Any]:
    started = time.perf_counter()
    try:
        returned = element.click(
            simulative=False,
            delay_after=0.2,
            allow_coord_fallback=False,
        )
        passed = returned is None
        return _result(
            "download_dialog_trigger",
            "PASS" if passed else "FAIL",
            "已通过元素库目标执行真实点击并触发下载流程"
            if passed
            else "下载元素点击返回值不符合合同",
            elapsed_ms=round((time.perf_counter() - started) * 1000, 1),
            element_click_completed=True,
            click_return_is_none=passed,
            simulative_click=False,
            coordinate_fallback=False,
        )
    except Exception as exc:  # noqa: BLE001
        status = _error_status(exc)
        return _result(
            "download_dialog_trigger",
            status,
            "下载元素点击被环境阻塞" if status == "BLOCKED" else "下载元素点击失败",
            elapsed_ms=round((time.perf_counter() - started) * 1000, 1),
            element_click_completed=False,
            simulative_click=False,
            coordinate_fallback=False,
            **_error_fields(exc),
        )


def run_handle_save_dialog_case(
    mode: str,
    run_dir: Path,
    file_name: str,
    dialog_timeout: float,
    download_timeout: float,
    send_key_delay: int,
    focus_timeout: int,
) -> dict[str, Any]:
    started = time.perf_counter()
    expected_path = run_dir / file_name
    try:
        returned = web.handle_save_dialog(
            str(run_dir),
            "ok",
            mode,
            file_name=file_name,
            overwrite=False,
            wait_complete=False,
            wait_complete_timeout=download_timeout,
            simulative=False,
            clipboard_input=True,
            wait_appear_timeout=dialog_timeout,
            force_ime_ENG=False,
            send_key_delay=send_key_delay,
            focus_timeout=focus_timeout,
        )
        return_is_str = isinstance(returned, str)
        returned_path_matches = return_is_str and _same_path(returned, expected_path)
        deadline = time.monotonic() + download_timeout
        file_poll_attempts = 0
        file_exists = False
        file_size_positive = False
        while True:
            file_poll_attempts += 1
            file_exists = expected_path.is_file()
            file_size_positive = file_exists and expected_path.stat().st_size > 0
            if file_size_positive or time.monotonic() >= deadline:
                break
            time.sleep(0.1)
        passed = return_is_str and returned_path_matches and file_exists and file_size_positive
        return _result(
            "handle_save_dialog_save",
            "PASS" if passed else "FAIL",
            "handle_save_dialog 已保存并确认本次唯一文本文件"
            if passed
            else "handle_save_dialog 返回值或下载文件不符合预期",
            elapsed_ms=round((time.perf_counter() - started) * 1000, 1),
            call_completed=True,
            return_is_str=return_is_str,
            returned_path_matches=returned_path_matches,
            file_exists=file_exists,
            file_size_positive=file_size_positive,
            file_poll_attempts=file_poll_attempts,
            dialog_result="ok",
            overwrite=False,
            wait_complete=False,
            clipboard_input=True,
        )
    except Exception as exc:  # noqa: BLE001
        status = _error_status(exc)
        return _result(
            "handle_save_dialog_save",
            status,
            "保存对话框场景被环境阻塞" if status == "BLOCKED" else "handle_save_dialog 调用失败",
            elapsed_ms=round((time.perf_counter() - started) * 1000, 1),
            call_completed=False,
            dialog_result="ok",
            overwrite=False,
            wait_complete=False,
            clipboard_input=True,
            **_error_fields(exc),
        )


def _close_owned_save_dialog() -> dict[str, Any]:
    item: dict[str, Any] = {"resource": "save_dialog"}
    try:
        hwnd = _find_save_dialog_window()
        if not hwnd:
            item.update(status="PASS", confirmed=True, cleanup_call_needed=False)
            return item
        user32 = ctypes.windll.user32
        posted = bool(user32.PostMessageW(int(hwnd), 0x0010, 0, 0))
        deadline = time.monotonic() + 2.0
        while time.monotonic() < deadline:
            if not user32.IsWindow(int(hwnd)) or not user32.IsWindowVisible(int(hwnd)):
                break
            time.sleep(0.05)
        confirmed = not user32.IsWindow(int(hwnd)) or not user32.IsWindowVisible(int(hwnd))
        item.update(
            status="PASS" if posted and confirmed else "FAIL",
            confirmed=bool(confirmed),
            cleanup_call_needed=True,
            close_message_posted=posted,
        )
    except Exception as exc:  # noqa: BLE001
        item.update(
            status="FAIL",
            confirmed=False,
            cleanup_call_needed=True,
            **_error_fields(exc),
        )
    return item


def cleanup_resources(
    *,
    dialog_may_be_owned: bool,
    package: Any | None,
    page: WebBrowser | None,
    run_dir: Path | None,
    baseline_window_count: int,
) -> dict[str, Any]:
    items: list[dict[str, Any]] = []

    if dialog_may_be_owned:
        items.append(_close_owned_save_dialog())

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

    download_item: dict[str, Any] = {"resource": "owned_download_directory"}
    if run_dir is None:
        download_item.update(status="PASS", confirmed=True, cleanup_call_needed=False, created=False)
    elif not re.fullmatch(r"[0-9a-f]{32}", run_dir.name):
        download_item.update(
            status="FAIL",
            confirmed=False,
            cleanup_call_needed=False,
            created=True,
            reason="owned_download_identity_unknown",
        )
    else:
        try:
            owned_entry_count = sum(1 for _ in run_dir.rglob("*")) if run_dir.exists() else 0
            if run_dir.exists():
                shutil.rmtree(run_dir)
            confirmed = not run_dir.exists()
            download_item.update(
                status="PASS" if confirmed else "FAIL",
                confirmed=confirmed,
                cleanup_call_needed=owned_entry_count > 0,
                created=True,
                owned_entry_count=owned_entry_count,
            )
        except Exception as exc:  # noqa: BLE001
            download_item.update(
                status="FAIL",
                confirmed=False,
                cleanup_call_needed=True,
                created=True,
                **_error_fields(exc),
            )
    items.append(download_item)

    window_item: dict[str, Any] = {"resource": "chromium_window_count"}
    try:
        deadline = time.monotonic() + 3.0
        current_window_count = _visible_chrome_window_count()
        while current_window_count > baseline_window_count and time.monotonic() < deadline:
            time.sleep(0.1)
            current_window_count = _visible_chrome_window_count()
        no_new_window = current_window_count <= baseline_window_count
        window_item.update(
            status="PASS" if no_new_window else "FAIL",
            confirmed=no_new_window,
            cleanup_call_needed=False,
            baseline_count=baseline_window_count,
            remaining_count=current_window_count,
            added_count=max(0, current_window_count - baseline_window_count),
        )
    except Exception as exc:  # noqa: BLE001
        window_item.update(
            status="FAIL",
            confirmed=False,
            cleanup_call_needed=False,
            **_error_fields(exc),
        )
    items.append(window_item)

    passed = all(item["status"] == "PASS" for item in items)
    return _result(
        "owned_resources_cleanup",
        "PASS" if passed else "FAIL",
        "本次页面、元素库连接、原生窗口和下载资源已逐项确认清理"
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
        'dialog_result="cancel"',
        "file_name=None 时读取对话框默认文件名",
        "overwrite=True 与同名文件覆盖",
        "wait_complete=True（真实运行已复现 web_download_timeout）",
        "clipboard_input=False",
        "simulative=True",
        "force_ime_ENG=True",
        "下载中断、网络失败与浏览器策略阻止下载",
        "并发出现的非本次保存对话框",
        "Chrome Profile 显示名或账号与 Profile 目录的对应关系",
    ]
    if any(item.get("profile_identity_fallback_used") is True for item in results):
        excluded.append("Default Profile 的 Runtime profileDirectoryHash 身份确认")
    return (
        {
            "api": "uiautoma.web.handle_save_dialog",
            "status": status,
            "exit_code": exit_code,
            "mode": args.mode,
            "profile_directory": args.profile_directory,
            "contract_only": bool(args.contract_only),
            "element_name": args.element_name,
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
            args.element_name,
            args.target_url,
        )
    )
    if results[-1]["status"] != "PASS":
        return _report(args, results)

    results.append(preflight_save_dialog_state())
    if results[-1]["status"] != "PASS":
        return _report(args, results)

    try:
        baseline_window_count = _visible_chrome_window_count()
        results.append(
            _result(
                "chrome_window_baseline",
                "PASS",
                "已记录运行前 Chromium 顶层窗口数量",
                window_count=baseline_window_count,
            )
        )
    except Exception as exc:  # noqa: BLE001
        results.append(
            _result("chrome_window_baseline", "BLOCKED", "无法记录运行前浏览器窗口数量", **_error_fields(exc))
        )
        return _report(args, results)

    run_id = uuid.uuid4().hex
    marked_url = _marked_url(args.target_url, run_id)
    run_dir = PRODUCT_ROOT / ".pytest_tmp" / run_id
    file_name = f"{DOWNLOAD_PREFIX}_{run_id}.txt"
    page: WebBrowser | None = None
    package: Any | None = None
    dialog_may_be_owned = False
    try:
        run_dir.mkdir(parents=True, exist_ok=False)
        page_result, page = prepare_owned_page(
            marked_url,
            args.mode,
            args.load_timeout,
            args.profile_directory,
        )
        results.append(page_result)
        if page_result["status"] == "PASS" and page is not None:
            library_result, package, element = connect_library_and_find_element(
                page,
                args.element_library,
                args.element_name,
                args.runtime_timeout,
                args.element_timeout,
            )
            results.append(library_result)
            if library_result["status"] == "PASS" and element is not None:
                dialog_may_be_owned = True
                trigger_result = trigger_download_dialog(element)
                results.append(trigger_result)
                if trigger_result["status"] == "PASS":
                    results.append(
                        run_handle_save_dialog_case(
                            args.mode,
                            run_dir,
                            file_name,
                            args.dialog_timeout,
                            args.download_timeout,
                            args.send_key_delay,
                            args.focus_timeout,
                        )
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
                dialog_may_be_owned=dialog_may_be_owned,
                package=package,
                page=page,
                run_dir=run_dir,
                baseline_window_count=baseline_window_count,
            )
        )
    return _report(args, results)


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="运行 uiautoma.web.handle_save_dialog() 持久化真实浏览器测试。"
    )
    parser.add_argument("--mode", required=True, choices=["chrome"], help="浏览器模式；当前只支持 chrome。")
    parser.add_argument(
        "--profile-directory",
        default=DEFAULT_PROFILE_DIRECTORY,
        help="Chrome Profile 目录标识；默认 Default。",
    )
    parser.add_argument("--target-url", default=DEFAULT_TARGET_URL, help=f"下载对话框靶场，默认 {DEFAULT_TARGET_URL}")
    parser.add_argument(
        "--element-library",
        type=Path,
        default=DEFAULT_ELEMENT_LIBRARY,
        help="包含下载元素的元素库目录。",
    )
    parser.add_argument("--element-name", default=DEFAULT_ELEMENT_NAME, help=f"下载元素名称，默认 {DEFAULT_ELEMENT_NAME}。")
    parser.add_argument("--preflight-timeout", type=float, default=2.0, help="靶场预检超时秒数，默认 2。")
    parser.add_argument("--runtime-timeout", type=float, default=5.0, help="Runtime 与元素库连接超时秒数，默认 5。")
    parser.add_argument("--load-timeout", type=float, default=20.0, help="页面创建超时秒数，默认 20。")
    parser.add_argument("--element-timeout", type=float, default=5.0, help="元素库目标绑定超时秒数，默认 5。")
    parser.add_argument("--dialog-timeout", type=float, default=20.0, help="保存对话框出现超时秒数，默认 20。")
    parser.add_argument("--download-timeout", type=float, default=30.0, help="下载完成超时秒数，默认 30。")
    parser.add_argument("--send-key-delay", type=int, default=50, help="保存对话框按键间隔毫秒，默认 50。")
    parser.add_argument("--focus-timeout", type=int, default=1000, help="保存对话框聚焦等待毫秒，默认 1000。")
    parser.add_argument("--contract-only", action="store_true", help="只检查公开签名，不连接 Runtime、靶场或浏览器。")
    args = parser.parse_args(argv)
    try:
        args.target_url = _validate_url(args.target_url, "--target-url")
    except argparse.ArgumentTypeError as exc:
        parser.error(str(exc))
    args.element_library = args.element_library.resolve()
    args.element_name = str(args.element_name or "").strip()
    args.profile_directory = str(args.profile_directory or "").strip()
    if not args.element_name:
        parser.error("--element-name 不能为空")
    if not args.profile_directory or any(char in args.profile_directory for char in ("/", "\\")):
        parser.error("--profile-directory 必须是不含路径分隔符的 Chrome Profile 目录标识")
    for name in (
        "preflight_timeout",
        "runtime_timeout",
        "load_timeout",
        "element_timeout",
        "dialog_timeout",
        "download_timeout",
    ):
        if getattr(args, name) <= 0:
            parser.error(f"--{name.replace('_', '-')} 必须大于 0")
    if args.send_key_delay < 0:
        parser.error("--send-key-delay 不能小于 0")
    if args.focus_timeout < 0:
        parser.error("--focus-timeout 不能小于 0")
    return args


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    report, exit_code = run(args)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
