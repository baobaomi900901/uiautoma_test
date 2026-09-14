"""uiautoma.web.WebElement.drag_to() 持久化真实浏览器测试运行器。

导入本模块不会连接 Runtime、访问靶场或操作浏览器。真实场景打开唯一 Chrome
``drag-to-test`` 页面并连接指定元素库；目标断言直接调用 ``WebElement.drag_to()``，
再用 ``获取拖拽日志`` 复制最近一条记录做副作用验收。

用例（靶场示例）：
- 对 ``拖拽元素`` 调用 ``drag_to(left=100, top=50, delay_after=1)``
- 通过 ``获取拖拽日志`` 读取剪贴板 JSON，期望相对拖拽约 ``Δleft=100``、``Δtop=50``
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

DEFAULT_TARGET_URL = "http://localhost:7199/drag-to-test"
DEFAULT_ELEMENT_LIBRARY = Path(__file__).with_name("web测试元素库")
DEFAULT_PROFILE_DIRECTORY = "Default"
DEFAULT_DRAG_ELEMENT_NAME = "拖拽元素"
DEFAULT_COPY_LOG_ELEMENT_NAME = "获取拖拽日志"
RUN_QUERY_KEY = "uiautoma_element_drag_to_run"

DEFAULT_DRAG_LEFT = 100
DEFAULT_DRAG_TOP = 50
DEFAULT_DELAY_AFTER = 1.0
DELTA_TOLERANCE_PX = 2


EXPECTED_PARAMETER_ORDER = (
    "self",
    "simulative",
    "behavior",
    "top",
    "left",
    "delay_after",
    "anchor",
    "move_speed",
)
EXPECTED_DEFAULTS: dict[str, Any] = {
    "simulative": True,
    "behavior": "smooth",
    "top": 0,
    "left": 0,
    "delay_after": 1,
    "anchor": None,
    "move_speed": "middle",
}
EXPECTED_KINDS = {
    "self": inspect.Parameter.POSITIONAL_OR_KEYWORD,
    "simulative": inspect.Parameter.KEYWORD_ONLY,
    "behavior": inspect.Parameter.KEYWORD_ONLY,
    "top": inspect.Parameter.KEYWORD_ONLY,
    "left": inspect.Parameter.KEYWORD_ONLY,
    "delay_after": inspect.Parameter.KEYWORD_ONLY,
    "anchor": inspect.Parameter.KEYWORD_ONLY,
    "move_speed": inspect.Parameter.KEYWORD_ONLY,
}

# 目标 API：drag_to(*, simulative=True, behavior="smooth", top=0, left=0,
# delay_after=1, anchor=None, move_speed="middle") -> None
# 用户文档写 behavior 默认 instant；当前公开实现默认 smooth。合同以源码为准。

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
            "owned_identity_ok": page.raw.get("created_by")
            in {
                "web.create",
                "profile_launch_recovery",
            },
        }
        passed = all(checks.values())
        return (
            _result(
                "owned_page_setup",
                "PASS" if passed else "BLOCKED",
                "已打开本次唯一 drag_to 测试页面" if passed else "drag_to 测试页面创建结果不完整",
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
                "无法打开本次 drag_to 测试页面",
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
        signature = inspect.signature(WebElement.drag_to)
        parameters = signature.parameters
        order_ok = tuple(parameters) == EXPECTED_PARAMETER_ORDER
        defaults_ok = all(parameters[name].default == value for name, value in EXPECTED_DEFAULTS.items())
        kinds_ok = all(parameters[name].kind == value for name, value in EXPECTED_KINDS.items())
        no_extra_ok = set(parameters) == set(EXPECTED_PARAMETER_ORDER)
        return_ann = signature.return_annotation
        return_ok = return_ann in {None, "None", type(None)}
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
            return_annotation=str(return_ann),
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
            "drag_to 测试靶场可访问" if passed else "drag_to 测试靶场未返回成功状态",
            elapsed_ms=round((time.perf_counter() - started) * 1000, 1),
            http_status=status_code,
        )
    except Exception as exc:  # noqa: BLE001
        return _result(
            "target_preflight",
            "BLOCKED",
            "drag_to 测试靶场不可访问",
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
    names: Sequence[str],
    target_url: str,
) -> dict[str, Any]:
    started = time.perf_counter()
    try:
        elements_file = library_dir / "elements.json"
        payload = json.loads(elements_file.read_text(encoding="utf-8"))
        details: dict[str, Any] = {}
        all_ok = library_dir.is_dir() and elements_file.is_file()
        for name in names:
            matches = _library_named_matches(payload, name)
            page_ok, selector_ok = _library_item_ok(matches, target_url)
            details[f"{name}_count"] = len(matches)
            details[f"{name}_page_url_matches"] = page_ok
            details[f"{name}_selector_present"] = selector_ok
            all_ok = all_ok and page_ok and selector_ok
        return _result(
            "element_library_preflight",
            "PASS" if all_ok else "BLOCKED",
            "元素库包含 drag_to 场景所需库项"
            if all_ok
            else "元素库缺少 drag_to 场景库项或 PageUrl/选择器不匹配",
            elapsed_ms=round((time.perf_counter() - started) * 1000, 1),
            library_dir_exists=library_dir.is_dir(),
            elements_json_exists=elements_file.is_file(),
            **details,
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
    names: Sequence[str],
    runtime_timeout: float,
    element_timeout: float,
) -> tuple[dict[str, Any], Any | None, dict[str, WebElement | None]]:
    started = time.perf_counter()
    package: Any | None = None
    found: dict[str, WebElement | None] = {name: None for name in names}
    try:
        package = uiautoma.open(str(library_dir), timeout=runtime_timeout)
        name_oks: dict[str, bool] = {}
        for name in names:
            element = page.find(name, timeout=element_timeout)
            found[name] = element
            name_oks[f"{name}_name_ok"] = str(element.name or "") == name
        passed = package.web_count > 0 and all(name_oks.values())
        return (
            _result(
                "element_library_setup",
                "PASS" if passed else "FAIL",
                "已连接元素库并绑定 drag_to 场景元素"
                if passed
                else "元素库连接或元素绑定结果不符合预期",
                elapsed_ms=round((time.perf_counter() - started) * 1000, 1),
                package_opened=True,
                web_element_count=package.web_count,
                **name_oks,
            ),
            package,
            found,
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
            found,
        )


def _clipboard_record() -> dict[str, Any] | None:
    text_value = clipboard.get_text()
    try:
        payload = json.loads(text_value)
    except Exception:  # noqa: BLE001
        return None
    return payload if isinstance(payload, dict) else None


def _copy_latest_drag_log(copy_element: WebElement) -> tuple[dict[str, Any] | None, str]:
    sentinel = f"uiautoma_drag_to_sentinel_{uuid.uuid4().hex}"
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


def _within_tolerance(actual: object, expected: int, tol: int) -> bool:
    try:
        return abs(int(actual) - int(expected)) <= int(tol)
    except (TypeError, ValueError):
        return False


def run_drag_to_case(
    *,
    page: WebBrowser,
    drag_element: WebElement,
    copy_element: WebElement,
    left: int,
    top: int,
    delay_after: float,
    tolerance: int,
) -> dict[str, Any]:
    started = time.perf_counter()
    case_id = "drag_to_left_top_with_log"
    kwargs = {
        "simulative": True,
        "behavior": "smooth",
        "top": int(top),
        "left": int(left),
        "delay_after": float(delay_after),
    }
    try:
        page.activate()
        time.sleep(0.1)
        before_delta = {
            "data-delta-left": drag_element.get_attribute("data-delta-left"),
            "data-delta-top": drag_element.get_attribute("data-delta-top"),
        }
        call_started = time.perf_counter()
        returned = drag_element.drag_to(**kwargs)
        call_elapsed_ms = round((time.perf_counter() - call_started) * 1000, 1)
        return_is_none = returned is None
        time.sleep(0.15)
        after_delta = {
            "data-delta-left": drag_element.get_attribute("data-delta-left"),
            "data-delta-top": drag_element.get_attribute("data-delta-top"),
        }
        record, copy_mode = _copy_latest_drag_log(copy_element)
        record_delta_left = None if record is None else record.get("deltaLeft")
        record_delta_top = None if record is None else record.get("deltaTop")
        record_phase = None if record is None else record.get("phase")
        offset = None if record is None else record.get("offsetFromSpawn")
        spawn_left = None if not isinstance(offset, dict) else offset.get("deltaLeft")
        spawn_top = None if not isinstance(offset, dict) else offset.get("deltaTop")

        attr_left_ok = _within_tolerance(after_delta["data-delta-left"], left, tolerance)
        attr_top_ok = _within_tolerance(after_delta["data-delta-top"], top, tolerance)
        # 结束阶段 delta 相对本次拖拽起点；spawn 相对初始 (40,40)。
        log_left_ok = _within_tolerance(record_delta_left, left, tolerance) or _within_tolerance(
            spawn_left, left, tolerance
        )
        log_top_ok = _within_tolerance(record_delta_top, top, tolerance) or _within_tolerance(
            spawn_top, top, tolerance
        )
        delay_ok = call_elapsed_ms >= max(0.0, float(delay_after) * 1000.0 - 50.0)
        moved_ok = attr_left_ok and attr_top_ok
        log_ok = record is not None and log_left_ok and log_top_ok and copy_mode != "failed"
        passed = return_is_none and delay_ok and (moved_ok or log_ok)

        print(
            f"{case_id}: returned={returned!r} elapsed_ms={call_elapsed_ms} "
            f"attr={after_delta!r} log_phase={record_phase!r} "
            f"log_delta=({record_delta_left!r},{record_delta_top!r}) "
            f"spawn=({spawn_left!r},{spawn_top!r}) copy_mode={copy_mode}",
            file=sys.stderr,
            flush=True,
        )
        return _result(
            case_id,
            "PASS" if passed else "FAIL",
            "drag_to 位移与拖拽日志符合预期" if passed else "drag_to 位移或拖拽日志不符合预期",
            elapsed_ms=round((time.perf_counter() - started) * 1000, 1),
            drag_to_elapsed_ms=call_elapsed_ms,
            return_is_none=return_is_none,
            delay_ok=delay_ok,
            moved_ok=moved_ok,
            log_ok=log_ok,
            copy_mode=copy_mode,
            expected_left=left,
            expected_top=top,
            delay_after=delay_after,
            before_delta=before_delta,
            after_delta=after_delta,
            attr_left_ok=attr_left_ok,
            attr_top_ok=attr_top_ok,
            record_phase=record_phase,
            record_delta_left=record_delta_left,
            record_delta_top=record_delta_top,
            spawn_delta_left=spawn_left,
            spawn_delta_top=spawn_top,
            log_left_ok=log_left_ok,
            log_top_ok=log_top_ok,
            record=record,
            kwargs=kwargs,
            target_name=str(drag_element.name or ""),
            copy_name=str(copy_element.name or ""),
        )
    except Exception as exc:  # noqa: BLE001
        status = _error_status(exc)
        return _result(
            case_id,
            status,
            "drag_to 被环境阻塞" if status == "BLOCKED" else "drag_to 调用失败",
            elapsed_ms=round((time.perf_counter() - started) * 1000, 1),
            expected_left=left,
            expected_top=top,
            **_error_fields(exc),
        )


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
    return (
        {
            "api": "uiautoma.web.WebElement.drag_to",
            "status": status,
            "exit_code": exit_code,
            "lifecycle_hint": "VERIFIED_CANDIDATE" if exit_code == 0 else "READY_FOR_LIVE",
            "mode": args.mode,
            "profile_directory": args.profile_directory,
            "contract_only": bool(args.contract_only),
            "drag_element_name": args.drag_element_name,
            "copy_log_element_name": args.copy_log_element_name,
            "drag_left": args.drag_left,
            "drag_top": args.drag_top,
            "delay_after": args.delay_after,
            "results": list(results),
            "excluded": [
                "edge",
                "cef",
                "auto",
                "simulative=False / behavior=instant 完整矩阵",
                "anchor / move_speed 轨迹差异",
                "drag_to_by_cdp",
            ],
            "open_defects": [
                "web.action.drag 同步派发 mousedown/mousemove/mouseup；靶场在 React setState 后才挂 window 监听，"
                "仅产生 phase=start，位移仍为 0（left=100/top=50 未生效）",
                "https://github.com/uiautoma/desktop/issues/26",
            ],
        },
        exit_code,
    )


def run(args: argparse.Namespace) -> tuple[dict[str, Any], int]:
    names = [args.drag_element_name, args.copy_log_element_name]
    results = [check_contract()]
    if results[-1]["status"] != "PASS" or args.contract_only:
        return _report(args, results)

    results.append(preflight_target(args.target_url, args.preflight_timeout))
    if results[-1]["status"] != "PASS":
        return _report(args, results)

    results.append(preflight_runtime(args.runtime_timeout))
    if results[-1]["status"] != "PASS":
        return _report(args, results)

    results.append(preflight_element_library(args.element_library, names, args.target_url))
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
                library_result, package, found = connect_library_and_find_elements(
                    page,
                    owned_library_dir,
                    names,
                    args.runtime_timeout,
                    args.element_timeout,
                )
                results.append(library_result)
                drag_el = found.get(args.drag_element_name)
                copy_el = found.get(args.copy_log_element_name)
                if library_result["status"] == "PASS" and drag_el is not None and copy_el is not None:
                    results.append(
                        run_drag_to_case(
                            page=page,
                            drag_element=drag_el,
                            copy_element=copy_el,
                            left=int(args.drag_left),
                            top=int(args.drag_top),
                            delay_after=float(args.delay_after),
                            tolerance=int(args.delta_tolerance),
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
        description="运行 uiautoma.web.WebElement.drag_to() 持久化真实浏览器测试。"
    )
    parser.add_argument("--mode", default="chrome", choices=["chrome"])
    parser.add_argument("--profile-directory", default=DEFAULT_PROFILE_DIRECTORY)
    parser.add_argument(
        "--target-url",
        default=DEFAULT_TARGET_URL,
        type=lambda value: _validate_url(value, "--target-url"),
    )
    parser.add_argument("--element-library", default=str(DEFAULT_ELEMENT_LIBRARY), type=Path)
    parser.add_argument("--drag-element-name", default=DEFAULT_DRAG_ELEMENT_NAME)
    parser.add_argument("--copy-log-element-name", default=DEFAULT_COPY_LOG_ELEMENT_NAME)
    parser.add_argument("--preflight-timeout", type=float, default=5.0)
    parser.add_argument("--runtime-timeout", type=float, default=5.0)
    parser.add_argument("--load-timeout", type=float, default=20.0)
    parser.add_argument("--element-timeout", type=float, default=10.0)
    parser.add_argument("--drag-left", type=int, default=DEFAULT_DRAG_LEFT)
    parser.add_argument("--drag-top", type=int, default=DEFAULT_DRAG_TOP)
    parser.add_argument("--delay-after", type=float, default=DEFAULT_DELAY_AFTER)
    parser.add_argument("--delta-tolerance", type=int, default=DELTA_TOLERANCE_PX)
    parser.add_argument("--contract-only", action="store_true")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    report, exit_code = run(args)
    sys.stdout.write(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
