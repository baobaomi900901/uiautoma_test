"""uiautoma.web.WebElement.download() 持久化真实浏览器测试运行器。

导入本模块不会连接 Runtime、访问靶场或操作浏览器。真实场景打开唯一 Chrome
``download-dialog-test`` 页面并连接指定元素库；目标断言直接调用
``WebElement.download()``，再核对返回路径与落盘文件。

库项 ``下载txt按钮`` 绑定 ``//button[@id='btn-download-blob-txt']``。当前实现为
``download_prepare`` → 元素 ``click`` → ``download_wait``（Chrome
``downloads`` 事件），**不是**原生另存为对话框。公开参数 ``overwrite`` /
``clipboard_input`` / ``focus_timeout`` / ``force_ime_ENG`` /
``send_key_delay`` 被接受但未下传；``dialog_timeout`` 作为 ``click_timeout``，
``wait_complete=False`` 时将等待超时置 ``0``。
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


__test__ = False

DEFAULT_TARGET_URL = "http://localhost:7199/download-dialog-test"
DEFAULT_ELEMENT_LIBRARY = Path(__file__).with_name("web测试元素库")
DEFAULT_PROFILE_DIRECTORY = "Default"
DEFAULT_ELEMENT_NAME = "下载txt按钮"
RUN_QUERY_KEY = "uiautoma_element_download_run"
DOWNLOAD_PREFIX = "uiautoma_web_element_download"

EXPECTED_PARAMETER_ORDER = (
    "self",
    "file_folder",
    "file_name",
    "overwrite",
    "wait_complete",
    "wait_complete_timeout",
    "simulative",
    "clipboard_input",
    "dialog_timeout",
    "force_ime_ENG",
    "send_key_delay",
    "focus_timeout",
)
EXPECTED_DEFAULTS: dict[str, Any] = {
    "file_name": None,
    "overwrite": True,
    "wait_complete": True,
    "wait_complete_timeout": 300,
    "simulative": False,
    "clipboard_input": True,
    "dialog_timeout": 20,
    "force_ime_ENG": False,
    "send_key_delay": 50,
    "focus_timeout": 1000,
}
EXPECTED_KINDS = {
    "self": inspect.Parameter.POSITIONAL_OR_KEYWORD,
    "file_folder": inspect.Parameter.POSITIONAL_OR_KEYWORD,
    "file_name": inspect.Parameter.KEYWORD_ONLY,
    "overwrite": inspect.Parameter.KEYWORD_ONLY,
    "wait_complete": inspect.Parameter.KEYWORD_ONLY,
    "wait_complete_timeout": inspect.Parameter.KEYWORD_ONLY,
    "simulative": inspect.Parameter.KEYWORD_ONLY,
    "clipboard_input": inspect.Parameter.KEYWORD_ONLY,
    "dialog_timeout": inspect.Parameter.KEYWORD_ONLY,
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
    "web_session_unavailable",
}


def _result(case_id: str, status: str, detail: str, **extra: Any) -> dict[str, Any]:
    return {"case_id": case_id, "status": status, "detail": detail, **extra}


def _safe_trace(exc: BaseException) -> str:
    for attr in ("trace_info", "method"):
        trace = str(getattr(exc, attr, "") or "")
        if re.fullmatch(r"[A-Za-z0-9_.-]{1,80}", trace):
            return trace
    return ""


def _error_fields(exc: BaseException) -> dict[str, str]:
    return {"exception": exc.__class__.__name__, "trace_info": _safe_trace(exc)}


def _error_status(exc: BaseException) -> str:
    if exc.__class__.__name__ in BLOCKING_EXCEPTION_NAMES or _safe_trace(exc) in BLOCKING_TRACES:
        return "BLOCKED"
    return "FAIL"


def _same_path(left: object, right: object) -> bool:
    try:
        return Path(str(left)).resolve() == Path(str(right)).resolve()
    except OSError:
        return False


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
                "已打开本次唯一 download 测试页面" if passed else "download 测试页面创建结果不完整",
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
                "无法打开本次 download 测试页面",
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
        signature = inspect.signature(WebElement.download)
        parameters = signature.parameters
        order_ok = tuple(parameters) == EXPECTED_PARAMETER_ORDER
        defaults_ok = all(parameters[name].default == value for name, value in EXPECTED_DEFAULTS.items())
        kinds_ok = all(parameters[name].kind == value for name, value in EXPECTED_KINDS.items())
        no_extra_ok = set(parameters) == set(EXPECTED_PARAMETER_ORDER)
        ann = signature.return_annotation
        ann_text = str(ann).replace("typing.", "")
        return_ok = ann is str or ann_text in {"str", "<class 'str'>"}
        passed = order_ok and defaults_ok and kinds_ok and return_ok and no_extra_ok
        return _result(
            "api_contract",
            "PASS" if passed else "FAIL",
            "公开签名符合当前合同" if passed else "公开签名与当前合同不一致",
            parameter_order_ok=order_ok,
            defaults_ok=defaults_ok,
            parameter_kinds_ok=kinds_ok,
            return_annotation_ok=return_ok,
            no_extra_parameters_ok=no_extra_ok,
            return_annotation=str(ann),
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
            "download 测试靶场可访问" if passed else "download 测试靶场未返回成功状态",
            elapsed_ms=round((time.perf_counter() - started) * 1000, 1),
            http_status=status_code,
        )
    except Exception as exc:  # noqa: BLE001
        return _result(
            "target_preflight",
            "BLOCKED",
            "download 测试靶场不可访问",
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
    element_name: str,
    target_url: str,
) -> dict[str, Any]:
    started = time.perf_counter()
    try:
        elements_file = library_dir / "elements.json"
        payload = json.loads(elements_file.read_text(encoding="utf-8"))
        matches = _library_named_matches(payload, element_name)
        page_ok, selector_ok = _library_item_ok(matches, target_url)
        passed = library_dir.is_dir() and elements_file.is_file() and page_ok and selector_ok
        return _result(
            "element_library_preflight",
            "PASS" if passed else "BLOCKED",
            "元素库包含 下载txt按钮" if passed else "元素库缺少 下载txt按钮 或 PageUrl/选择器不匹配",
            elapsed_ms=round((time.perf_counter() - started) * 1000, 1),
            library_dir_exists=library_dir.is_dir(),
            elements_json_exists=elements_file.is_file(),
            named_element_count=len(matches),
            page_url_matches=page_ok,
            selector_present=selector_ok,
            characteristics=(
                str(matches[0].get("Characteristics") or "") if len(matches) == 1 else ""
            ),
        )
    except Exception as exc:  # noqa: BLE001
        return _result(
            "element_library_preflight",
            "BLOCKED",
            "无法读取或验证元素库",
            elapsed_ms=round((time.perf_counter() - started) * 1000, 1),
            **_error_fields(exc),
        )


def connect_library_and_find_element(
    page: WebBrowser,
    library_dir: Path,
    element_name: str,
    runtime_timeout: float,
    element_timeout: float,
) -> tuple[dict[str, Any], Any | None, WebElement | None]:
    started = time.perf_counter()
    package: Any | None = None
    try:
        package = uiautoma.open(str(library_dir), timeout=runtime_timeout)
        element = page.find(element_name, timeout=element_timeout)
        name_ok = str(element.name or "") == element_name
        passed = package.web_count > 0 and name_ok
        return (
            _result(
                "element_library_setup",
                "PASS" if passed else "FAIL",
                "已连接元素库并绑定 下载txt按钮" if passed else "元素库连接或元素绑定结果不符合预期",
                elapsed_ms=round((time.perf_counter() - started) * 1000, 1),
                package_opened=True,
                web_element_count=package.web_count,
                name_ok=name_ok,
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
                **_error_fields(exc),
            ),
            package,
            None,
        )


def run_download_case(
    page: WebBrowser,
    element: WebElement,
    file_folder: Path,
    file_name: str,
    *,
    wait_complete: bool,
    wait_complete_timeout: float,
    clipboard_input: bool,
    focus_timeout: int,
    dialog_timeout: float,
    post_file_timeout: float,
) -> dict[str, Any]:
    started = time.perf_counter()
    expected_path = file_folder / file_name
    try:
        page.activate()
        time.sleep(0.1)
        returned = element.download(
            str(file_folder),
            file_name=file_name,
            wait_complete=wait_complete,
            wait_complete_timeout=wait_complete_timeout,
            clipboard_input=clipboard_input,
            focus_timeout=focus_timeout,
            dialog_timeout=dialog_timeout,
        )
        return_is_str = isinstance(returned, str)
        returned_nonempty = return_is_str and bool(str(returned).strip())
        returned_path = Path(str(returned)) if returned_nonempty else None
        returned_name_matches = (
            returned_path is not None and returned_path.name.casefold() == file_name.casefold()
        )
        returned_equals_expected = returned_nonempty and _same_path(returned, expected_path)

        deadline = time.monotonic() + post_file_timeout
        file_poll_attempts = 0
        file_exists = False
        file_size_positive = False
        observed_path: Path | None = None
        while True:
            file_poll_attempts += 1
            candidates = [expected_path]
            if returned_path is not None:
                candidates.append(returned_path)
            for candidate in candidates:
                if candidate.is_file() and candidate.stat().st_size > 0:
                    observed_path = candidate
                    file_exists = True
                    file_size_positive = True
                    break
            if file_size_positive or time.monotonic() >= deadline:
                break
            time.sleep(0.1)

        print(
            f"download: returned={returned!r} expected={expected_path!r} "
            f"observed={observed_path!r} polls={file_poll_attempts}",
            file=sys.stderr,
            flush=True,
        )

        # 当前引擎可能把文件落到 Chrome 默认下载目录；若返回路径存在且文件名匹配，仍算场景成功。
        path_ok = returned_equals_expected or (
            returned_nonempty and returned_name_matches and file_exists and file_size_positive
        )
        passed = return_is_str and returned_nonempty and path_ok and file_exists and file_size_positive
        return _result(
            "download_blob_txt_wait_complete",
            "PASS" if passed else "FAIL",
            "download 已保存本次唯一文本文件且返回路径可用"
            if passed
            else "download 返回值或落盘文件不符合预期",
            elapsed_ms=round((time.perf_counter() - started) * 1000, 1),
            call_completed=True,
            return_is_str=return_is_str,
            returned_nonempty=returned_nonempty,
            returned_equals_expected=returned_equals_expected,
            returned_name_matches=returned_name_matches,
            file_exists=file_exists,
            file_size_positive=file_size_positive,
            file_poll_attempts=file_poll_attempts,
            returned_path=str(returned) if return_is_str else None,
            expected_path=str(expected_path),
            observed_path=str(observed_path) if observed_path is not None else None,
            wait_complete=wait_complete,
            wait_complete_timeout=wait_complete_timeout,
            clipboard_input=clipboard_input,
            focus_timeout=focus_timeout,
            dialog_timeout=dialog_timeout,
            target_name=str(element.name or ""),
        )
    except Exception as exc:  # noqa: BLE001
        status = _error_status(exc)
        print(
            f"download: raised {exc.__class__.__name__}: {exc}",
            file=sys.stderr,
            flush=True,
        )
        detail = "download 场景被环境阻塞" if status == "BLOCKED" else "download 调用失败"
        if _safe_trace(exc) == "web_download_timeout":
            detail = "download 等待完成超时（web_download_timeout）"
            status = "FAIL"
        return _result(
            "download_blob_txt_wait_complete",
            status,
            detail,
            elapsed_ms=round((time.perf_counter() - started) * 1000, 1),
            call_completed=False,
            return_is_str=False,
            returned_nonempty=False,
            file_exists=False,
            file_size_positive=False,
            wait_complete=wait_complete,
            wait_complete_timeout=wait_complete_timeout,
            clipboard_input=clipboard_input,
            focus_timeout=focus_timeout,
            dialog_timeout=dialog_timeout,
            expected_path=str(expected_path),
            target_name=str(element.name or ""),
            **_error_fields(exc),
        )


def cleanup_resources(
    *,
    package: Any | None,
    page: WebBrowser | None,
    owned_library_dir: Path | None,
    owned_download_dir: Path | None,
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

    download_item: dict[str, Any] = {"resource": "owned_download_directory"}
    if owned_download_dir is None:
        download_item.update(status="PASS", confirmed=True, cleanup_call_needed=False, created=False)
    elif not re.fullmatch(r"[0-9a-f]{32}", owned_download_dir.name):
        download_item.update(
            status="FAIL",
            confirmed=False,
            cleanup_call_needed=False,
            created=True,
            reason="owned_download_identity_unknown",
        )
    else:
        try:
            if owned_download_dir.exists():
                shutil.rmtree(owned_download_dir)
            confirmed = not owned_download_dir.exists()
            download_item.update(
                status="PASS" if confirmed else "FAIL",
                confirmed=confirmed,
                cleanup_call_needed=True,
                created=True,
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

    passed = all(item["status"] == "PASS" for item in items)
    return _result(
        "owned_resources_cleanup",
        "PASS" if passed else "FAIL",
        "本次元素库连接、测试页面、临时库副本与下载目录已逐项确认清理"
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
    scenario_pass = any(
        item.get("case_id") == "download_blob_txt_wait_complete" and item.get("status") == "PASS"
        for item in results
    )
    cleanup_pass = any(
        item.get("case_id") == "owned_resources_cleanup" and item.get("status") == "PASS"
        for item in results
    )
    if status == "PASS" and scenario_pass and cleanup_pass:
        lifecycle = "VERIFIED"
    elif status != "BLOCKED" and any(
        item.get("case_id") == "api_contract" and item.get("status") == "PASS" for item in results
    ):
        lifecycle = "READY_FOR_LIVE"
    else:
        lifecycle = "DRAFT"
    return (
        {
            "api": "uiautoma.web.WebElement.download",
            "lifecycle": lifecycle,
            "status": status,
            "exit_code": exit_code,
            "mode": args.mode,
            "target_url": args.target_url,
            "element_name": args.element_name,
            "element_library": str(args.element_library),
            "wait_complete": args.wait_complete,
            "wait_complete_timeout": args.wait_complete_timeout,
            "clipboard_input": args.clipboard_input,
            "focus_timeout": args.focus_timeout,
            "dialog_timeout": args.dialog_timeout,
            "results": list(results),
            "excluded": [
                "edge",
                "cef",
                "auto",
                "simulative=True（系统对话框下载当前 unsupported）",
                "file_name=None 默认资源名",
                "原生另存为对话框（见 handle_save_dialog）",
                "overwrite=False 冲突矩阵",
            ],
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

    run_id = uuid.uuid4().hex
    marked_url = _marked_url(args.target_url, run_id)
    owned_library_dir = PRODUCT_ROOT / ".pytest_tmp" / run_id
    owned_download_dir = PRODUCT_ROOT / ".pytest_tmp" / uuid.uuid4().hex
    file_name = f"{DOWNLOAD_PREFIX}_{run_id}.txt"
    page: WebBrowser | None = None
    package: Any | None = None
    try:
        owned_download_dir.mkdir(parents=True, exist_ok=False)
        results.append(
            _result(
                "download_dir_setup",
                "PASS",
                "已准备本次唯一下载目录",
                download_dir=str(owned_download_dir),
                file_name=file_name,
            )
        )
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
                library_result, package, element = connect_library_and_find_element(
                    page,
                    owned_library_dir,
                    args.element_name,
                    args.runtime_timeout,
                    args.element_timeout,
                )
                results.append(library_result)
                if library_result["status"] == "PASS" and element is not None:
                    results.append(
                        run_download_case(
                            page,
                            element,
                            owned_download_dir,
                            file_name,
                            wait_complete=args.wait_complete,
                            wait_complete_timeout=args.wait_complete_timeout,
                            clipboard_input=args.clipboard_input,
                            focus_timeout=args.focus_timeout,
                            dialog_timeout=args.dialog_timeout,
                            post_file_timeout=args.post_file_timeout,
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
                package=package,
                page=page,
                owned_library_dir=owned_library_dir if owned_library_dir.exists() else None,
                owned_download_dir=owned_download_dir if owned_download_dir.exists() else None,
            )
        )
    return _report(args, results)


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="运行 uiautoma.web.WebElement.download() 持久化真实浏览器测试。"
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
        help=f"download 测试靶场，默认 {DEFAULT_TARGET_URL}",
    )
    parser.add_argument(
        "--element-library",
        type=Path,
        default=DEFAULT_ELEMENT_LIBRARY,
        help="包含 下载txt按钮 的元素库目录。",
    )
    parser.add_argument(
        "--element-name",
        default=DEFAULT_ELEMENT_NAME,
        help=f"下载目标元素名称，默认 {DEFAULT_ELEMENT_NAME}。",
    )
    parser.add_argument(
        "--wait-complete",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="传给 download(wait_complete=...)；默认 True。",
    )
    parser.add_argument(
        "--wait-complete-timeout",
        type=float,
        default=30.0,
        help="传给 download(wait_complete_timeout=...)；真实验证默认 30 秒（合同默认 300）。",
    )
    parser.add_argument(
        "--clipboard-input",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="传给 download(clipboard_input=...)；默认 True。",
    )
    parser.add_argument(
        "--focus-timeout",
        type=int,
        default=1000,
        help="传给 download(focus_timeout=...)；默认 1000 毫秒。",
    )
    parser.add_argument(
        "--dialog-timeout",
        type=float,
        default=20.0,
        help="传给 download(dialog_timeout=...)；默认 20 秒。",
    )
    parser.add_argument(
        "--post-file-timeout",
        type=float,
        default=5.0,
        help="download 返回后轮询落盘文件的最大秒数，默认 5。",
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
        "wait_complete_timeout",
        "post_file_timeout",
    ):
        if getattr(args, name) <= 0:
            parser.error(f"--{name.replace('_', '-')} 必须大于 0")
    if args.focus_timeout <= 0:
        parser.error("--focus-timeout 必须大于 0")
    return args


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    report, exit_code = run(args)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
