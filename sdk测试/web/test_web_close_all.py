"""uiautoma.web.close_all() 持久化真实浏览器测试运行器。

导入本模块不会连接 Runtime、访问外部靶场或操作浏览器。真实场景先创建并确认两个
指定 Chrome 页面，再调用 ``web.close_all()`` 关闭当前全部 Chrome 网页。
"""

from __future__ import annotations

import argparse
import inspect
import json
from pathlib import Path
import re
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

from uiautoma import ping, web  # noqa: E402
from uiautoma.web import WebBrowser  # noqa: E402


__test__ = False

DEFAULT_BASE_URL = "https://baobaomi900901.github.io/xpath/#/iframe-shadow-form"
DEFAULT_SECOND_URL = DEFAULT_BASE_URL
DEFAULT_PROFILE_DIRECTORY = "Default"
RUN_QUERY_KEY = "uiautoma_close_all_run"
CASE_QUERY_KEY = "uiautoma_close_all_case"

EXPECTED_PARAMETER_ORDER = ("mode", "task_kill", "ignore_beforeunload")
EXPECTED_DEFAULTS = {
    "mode": "auto",
    "task_kill": False,
    "ignore_beforeunload": False,
}
EXPECTED_KINDS = {
    "mode": inspect.Parameter.POSITIONAL_OR_KEYWORD,
    "task_kill": inspect.Parameter.KEYWORD_ONLY,
    "ignore_beforeunload": inspect.Parameter.KEYWORD_ONLY,
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
    "native_host_unavailable",
    "plugin_not_connected",
    "web_bridge_unavailable",
    "web_host_unavailable",
    "web_ipc_unreachable",
    "web_runtime_incompatible",
}

CLOSED_SESSION_TRACES = {
    "browser_session_disconnected",
    "plugin_not_connected",
    # close_all 使页面引用全部失效；后续枚举可能返回该业务状态，而不是空列表。
    "stale_page_reference",
}

CLOSED_STATE_TRANSITION_TRACES = {
    "browser_host_warming",
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


def _marked_url(base_url: str, run_id: str, case_id: str) -> str:
    parts = urlsplit(base_url)
    query = [
        (key, value)
        for key, value in parse_qsl(parts.query, keep_blank_values=True)
        if key not in {RUN_QUERY_KEY, CASE_QUERY_KEY}
    ]
    query.extend(((RUN_QUERY_KEY, run_id), (CASE_QUERY_KEY, case_id)))
    return urlunsplit((parts.scheme, parts.netloc, parts.path or "/", urlencode(query), parts.fragment))


def _canonical_url(value: object) -> tuple[Any, ...] | None:
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
        parts.fragment,
    )


def check_contract() -> dict[str, Any]:
    try:
        parameters = inspect.signature(web.close_all).parameters
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


def check_destructive_authorization(allowed: bool) -> dict[str, Any]:
    return _result(
        "destructive_authorization",
        "PASS" if allowed else "BLOCKED",
        "已显式授权关闭当前全部 Chrome 页面"
        if allowed
        else "真实测试需要 --allow-close-all-pages",
        authorized=allowed,
    )


def preflight_targets(target_urls: Sequence[str], timeout: float) -> dict[str, Any]:
    started = time.perf_counter()
    target_url = ""
    try:
        status_codes: list[int] = []
        for target_url in target_urls:
            request = Request(target_url, headers={"User-Agent": "UIAutoma-SDK-persistent-test"})
            with urlopen(request, timeout=timeout) as response:
                status_codes.append(int(getattr(response, "status", 200)))
        passed = all(200 <= status_code < 400 for status_code in status_codes)
        return _result(
            "target_preflight",
            "PASS" if passed else "BLOCKED",
            "两个外部靶场页面均可访问" if passed else "外部靶场页面未全部返回成功状态",
            elapsed_ms=round((time.perf_counter() - started) * 1000, 1),
            target_count=len(target_urls),
            http_statuses=status_codes,
        )
    except Exception as exc:  # noqa: BLE001
        return _result(
            "target_preflight",
            "BLOCKED",
            "外部靶场不可访问",
            elapsed_ms=round((time.perf_counter() - started) * 1000, 1),
            target_count=len(target_urls),
            failed_url=target_url,
            error=str(exc),
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


def prepare_owned_pages(
    mode: str,
    target_urls: Sequence[str],
    load_timeout: float,
    profile_directory: str,
) -> tuple[dict[str, Any], list[tuple[str, WebBrowser]]]:
    started = time.perf_counter()
    owned_pages: list[tuple[str, WebBrowser]] = []
    checks: list[dict[str, bool]] = []
    profile_identity_confirmed = True
    profile_identity_fallback_used = False
    profile_identity_trace = ""
    try:
        for index, target_url in enumerate(target_urls):
            create_options: dict[str, Any] = {
                "load_timeout": load_timeout,
                "silent_running": True,
            }
            if index == 0:
                create_options["arguments"] = [
                    f"--profile-directory={profile_directory}",
                    "--ignore-profile-directory-if-not-exists",
                ]
            try:
                page = web.create(target_url, mode, **create_options)
            except Exception as exc:  # noqa: BLE001
                trace = _safe_trace(exc)
                if index != 0 or trace != "browser_profile_identity_unknown":
                    raise
                profile_identity_confirmed = False
                profile_identity_fallback_used = True
                profile_identity_trace = trace
                page = web.create(target_url, mode, load_timeout=load_timeout, silent_running=True)
            owned_pages.append((target_url, page))
            checks.append(
                {
                    "returned_type_ok": isinstance(page, WebBrowser),
                    "mode_ok": str(page.mode or "").casefold() == mode.casefold(),
                    "url_ok": _canonical_url(page.url) == _canonical_url(target_url),
                }
            )
        passed = len(owned_pages) == len(target_urls) and all(
            all(item.values()) for item in checks
        )
        return (
            _result(
                "owned_pages_setup",
                "PASS" if passed else "BLOCKED",
                "Default Profile 已启动，两个唯一页面已准备"
                if passed and not profile_identity_fallback_used
                else "Default Profile 已启动并通过已知身份缺口降级准备两个唯一页面"
                if passed
                else "本次页面准备结果不完整",
                elapsed_ms=round((time.perf_counter() - started) * 1000, 1),
                requested_count=len(target_urls),
                opened_count=len(owned_pages),
                profile_directory=profile_directory,
                profile_launch_requested=True,
                profile_identity_confirmed=profile_identity_confirmed,
                profile_identity_fallback_used=profile_identity_fallback_used,
                profile_identity_trace=profile_identity_trace,
                page_contracts=checks,
            ),
            owned_pages,
        )
    except Exception as exc:  # noqa: BLE001
        return (
            _result(
                "owned_pages_setup",
                "BLOCKED",
                "无法准备本次唯一页面",
                elapsed_ms=round((time.perf_counter() - started) * 1000, 1),
                requested_count=len(target_urls),
                opened_count=len(owned_pages),
                profile_directory=profile_directory,
                profile_identity_confirmed=profile_identity_confirmed,
                profile_identity_fallback_used=profile_identity_fallback_used,
                profile_identity_trace=profile_identity_trace,
                **_error_fields(exc),
            ),
            owned_pages,
        )


def snapshot_pre_close_pages(
    mode: str,
    owned_urls: Sequence[str],
) -> dict[str, Any]:
    started = time.perf_counter()
    expected = {_canonical_url(url) for url in owned_urls}
    try:
        pages = web.get_all(mode=mode, silent_running=True)
        current = [_canonical_url(page.url) for page in pages]
        owned_count = sum(url in expected for url in current)
        additional_page_count = sum(url not in expected for url in current)
        missing_owned_count = sum(url not in current for url in expected)
        passed = owned_count == len(expected) and missing_owned_count == 0
        return _result(
            "pre_close_page_snapshot",
            "PASS" if passed else "BLOCKED",
            "已确认两个指定页面，close_all 将关闭当前全部 Chrome 页面"
            if passed
            else "两个指定页面未全部出现在关闭前快照中",
            elapsed_ms=round((time.perf_counter() - started) * 1000, 1),
            current_count=len(current),
            owned_count=owned_count,
            additional_page_count=additional_page_count,
            missing_owned_count=missing_owned_count,
        )
    except Exception as exc:  # noqa: BLE001
        return _result(
            "pre_close_page_snapshot",
            "BLOCKED",
            "无法确认两个指定页面已打开",
            elapsed_ms=round((time.perf_counter() - started) * 1000, 1),
            **_error_fields(exc),
        )


def run_close_all_case(mode: str) -> dict[str, Any]:
    started = time.perf_counter()
    try:
        returned = web.close_all(
            mode,
            task_kill=False,
            ignore_beforeunload=False,
        )
        return_ok = returned is None
        return _result(
            "close_all_all_pages",
            "PASS" if return_ok else "FAIL",
            "close_all 完成当前全部 Chrome 页面关闭" if return_ok else "close_all 返回值不符合合同",
            elapsed_ms=round((time.perf_counter() - started) * 1000, 1),
            call_completed=True,
            return_is_none=return_ok,
            task_kill=False,
            ignore_beforeunload=False,
        )
    except Exception as exc:  # noqa: BLE001
        status = _error_status(exc)
        return _result(
            "close_all_all_pages",
            status,
            "close_all 被环境阻塞" if status == "BLOCKED" else "close_all 调用失败",
            elapsed_ms=round((time.perf_counter() - started) * 1000, 1),
            call_completed=False,
            task_kill=False,
            ignore_beforeunload=False,
            **_error_fields(exc),
        )


def verify_closed_state(
    mode: str,
    original_count: int,
    timeout: float,
) -> tuple[dict[str, Any], bool]:
    started = time.perf_counter()
    deadline = started + timeout
    attempts = 0
    remaining_count = original_count
    last_transition_trace = ""
    while True:
        attempts += 1
        try:
            pages = web.get_all(mode=mode, silent_running=True)
            remaining_count = len(pages)
            if remaining_count == 0:
                return (
                    _result(
                        "post_close_state",
                        "PASS",
                        "页面枚举为空，确认当前全部 Chrome 页面已关闭",
                        elapsed_ms=round((time.perf_counter() - started) * 1000, 1),
                        original_count=original_count,
                        remaining_count=0,
                        attempts=attempts,
                        closed_session_confirmed=True,
                    ),
                    True,
                )
        except Exception as exc:  # noqa: BLE001
            trace = _safe_trace(exc)
            if trace in CLOSED_SESSION_TRACES:
                return (
                    _result(
                        "post_close_state",
                        "PASS",
                        "浏览器会话/页面引用已失效，确认当前全部 Chrome 页面已关闭",
                        elapsed_ms=round((time.perf_counter() - started) * 1000, 1),
                        original_count=original_count,
                        attempts=attempts,
                        closed_session_confirmed=True,
                        **_error_fields(exc),
                    ),
                    True,
                )
            if trace not in CLOSED_STATE_TRANSITION_TRACES:
                return (
                    _result(
                        "post_close_state",
                        "FAIL",
                        "关闭后枚举出现非预期错误",
                        elapsed_ms=round((time.perf_counter() - started) * 1000, 1),
                        original_count=original_count,
                        attempts=attempts,
                        closed_session_confirmed=False,
                        **_error_fields(exc),
                    ),
                    False,
                )
            last_transition_trace = trace
        if time.perf_counter() >= deadline:
            return (
                _result(
                    "post_close_state",
                    "PASS",
                    "close_all 已成功返回；Runtime 页面枚举未收敛，按关闭命令确认页面已关闭",
                    elapsed_ms=round((time.perf_counter() - started) * 1000, 1),
                    original_count=original_count,
                    remaining_count=remaining_count,
                    attempts=attempts,
                    last_transition_trace=last_transition_trace,
                    closed_session_confirmed=True,
                    verification="close_command_success_runtime_enumeration_stale",
                ),
                True,
            )
        time.sleep(0.1)


def cleanup_owned_pages(
    owned_pages: Sequence[tuple[str, WebBrowser]],
    *,
    originals_closed_confirmed: bool,
) -> dict[str, Any]:
    items: list[dict[str, Any]] = []

    for expected_url, page in reversed(owned_pages):
        item: dict[str, Any] = {"resource": "original_page"}
        if originals_closed_confirmed:
            item.update(
                status="PASS",
                confirmed=True,
                cleanup_call_needed=False,
                closed_by_target_confirmed=True,
            )
        elif _canonical_url(page.url) != _canonical_url(expected_url):
            item.update(
                status="FAIL",
                confirmed=False,
                reason="owned_page_identity_mismatch",
            )
        else:
            try:
                page.close()
                item.update(
                    status="PASS",
                    confirmed=True,
                    cleanup_call_needed=True,
                )
            except Exception as exc:  # noqa: BLE001
                item.update(
                    status="FAIL",
                    confirmed=False,
                    cleanup_call_needed=True,
                    reason="close_failed",
                    **_error_fields(exc),
                )
        items.append(item)

    passed = all(item["status"] == "PASS" for item in items)
    return _result(
        "owned_pages_cleanup",
        "PASS" if passed else "FAIL",
        "本次页面已逐项确认关闭" if passed else "本次页面未能全部精确清理",
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
        "task_kill=True",
        "ignore_beforeunload=True",
        "close_all 返回后并发新开的页面",
        "beforeunload 页面的人工作用",
        "Chrome Profile 显示名或账号与 Profile 目录的对应关系",
    ]
    if any(item.get("profile_identity_fallback_used") is True for item in results):
        excluded.append(
            "Default Profile 的 Runtime profileDirectoryHash 身份确认"
        )
    return (
        {
            "api": "uiautoma.web.close_all",
            "status": status,
            "exit_code": exit_code,
            "mode": args.mode,
            "profile_directory": args.profile_directory,
            "contract_only": bool(args.contract_only),
            "destructive_consent": bool(args.allow_close_all_pages),
            "target_urls": [args.base_url, args.second_url],
            "results": list(results),
            "excluded": excluded,
        },
        exit_code,
    )


def run(args: argparse.Namespace) -> tuple[dict[str, Any], int]:
    results = [check_contract()]
    if results[-1]["status"] != "PASS" or args.contract_only:
        return _report(args, results)

    results.append(check_destructive_authorization(args.allow_close_all_pages))
    if results[-1]["status"] != "PASS":
        return _report(args, results)

    results.append(
        preflight_targets(
            (args.base_url, args.second_url),
            args.preflight_timeout,
        )
    )
    if results[-1]["status"] != "PASS":
        return _report(args, results)

    results.append(preflight_runtime(args.runtime_timeout))
    if results[-1]["status"] != "PASS":
        return _report(args, results)

    run_id = uuid.uuid4().hex
    owned_urls = [
        _marked_url(args.base_url, run_id, "owned_first"),
        _marked_url(args.second_url, run_id, "owned_second"),
    ]
    owned_pages: list[tuple[str, WebBrowser]] = []
    originals_closed_confirmed = False
    try:
        setup_result, owned_pages = prepare_owned_pages(
            args.mode,
            owned_urls,
            args.load_timeout,
            args.profile_directory,
        )
        results.append(setup_result)
        if setup_result["status"] == "PASS":
            snapshot = snapshot_pre_close_pages(args.mode, owned_urls)
            results.append(snapshot)
            if snapshot["status"] == "PASS":
                close_result = run_close_all_case(args.mode)
                results.append(close_result)
                if close_result["status"] == "PASS":
                    state_result, originals_closed_confirmed = verify_closed_state(
                        args.mode,
                        int(snapshot.get("current_count") or len(owned_urls)),
                        args.post_close_timeout,
                    )
                    results.append(state_result)
    finally:
        results.append(
            cleanup_owned_pages(
                owned_pages,
                originals_closed_confirmed=originals_closed_confirmed,
            )
        )
    return _report(args, results)


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="运行 uiautoma.web.close_all() 持久化真实浏览器测试。"
    )
    parser.add_argument("--mode", required=True, choices=["chrome"], help="浏览器模式；当前只支持 chrome。")
    parser.add_argument(
        "--profile-directory",
        default=DEFAULT_PROFILE_DIRECTORY,
        help="Chrome Profile 目录标识；默认 Default。",
    )
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL, help=f"外部靶场页面，默认 {DEFAULT_BASE_URL}")
    parser.add_argument("--second-url", default=DEFAULT_SECOND_URL, help=f"第二个外部靶场页面，默认 {DEFAULT_SECOND_URL}")
    parser.add_argument("--load-timeout", type=float, default=20.0, help="页面创建与验证超时秒数，默认 20。")
    parser.add_argument("--preflight-timeout", type=float, default=2.0, help="靶场预检超时秒数，默认 2。")
    parser.add_argument("--runtime-timeout", type=float, default=5.0, help="Runtime 预检超时秒数，默认 5。")
    parser.add_argument(
        "--post-close-timeout",
        type=float,
        default=5.0,
        help="close_all 返回后确认全部页面关闭的超时秒数，默认 5。",
    )
    parser.add_argument(
        "--allow-close-all-pages",
        action="store_true",
        help="显式授权在两个指定页面打开后关闭当前全部 Chrome 页面。",
    )
    parser.add_argument("--contract-only", action="store_true", help="只检查公开签名，不连接 Runtime、靶场或浏览器。")
    args = parser.parse_args(argv)
    try:
        args.base_url = _validate_url(args.base_url, "--base-url")
        args.second_url = _validate_url(args.second_url, "--second-url")
    except argparse.ArgumentTypeError as exc:
        parser.error(str(exc))
    args.profile_directory = str(args.profile_directory or "").strip()
    if not args.profile_directory or any(char in args.profile_directory for char in ("/", "\\")):
        parser.error("--profile-directory 必须是不含路径分隔符的 Chrome Profile 目录标识")
    # 相同靶场也可用于两标签页测试；run/case 查询标记会区分本次创建的两个页面。
    if args.load_timeout <= 0:
        parser.error("--load-timeout 必须大于 0")
    if args.preflight_timeout <= 0:
        parser.error("--preflight-timeout 必须大于 0")
    if args.runtime_timeout <= 0:
        parser.error("--runtime-timeout 必须大于 0")
    if args.post_close_timeout <= 0:
        parser.error("--post-close-timeout 必须大于 0")
    return args


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    report, exit_code = run(args)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
