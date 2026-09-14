"""uiautoma.web.set_cookie() 与 get_cookie() 持久化真实浏览器测试运行器。

导入本模块不会连接 Runtime、访问外部靶场或操作浏览器。真实场景使用
``web.create()`` 准备本次唯一页面，直接调用两个目标 API 完成 Cookie 往返，
并使用 ``web.remove_cookie()`` 与 ``WebBrowser.close()`` 精确清理本次资源。
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

DEFAULT_BASE_URL = "http://localhost:7199/"
RUN_QUERY_KEY = "uiautoma_cookie_run"

EXPECTED_CONTRACTS = {
    "set_cookie": {
        "callable": web.set_cookie,
        "parameter_order": (
            "url",
            "mode",
            "name",
            "value",
            "sessionCookie",
            "expires",
            "domain",
            "path",
            "httpOnly",
            "secure",
        ),
        "required": ("url",),
        "defaults": {
            "mode": "cef",
            "name": None,
            "value": None,
            "sessionCookie": True,
            "expires": 100,
            "domain": None,
            "path": None,
            "httpOnly": False,
            "secure": False,
        },
        "kinds": {
            "url": inspect.Parameter.POSITIONAL_OR_KEYWORD,
            "mode": inspect.Parameter.POSITIONAL_OR_KEYWORD,
            "name": inspect.Parameter.KEYWORD_ONLY,
            "value": inspect.Parameter.KEYWORD_ONLY,
            "sessionCookie": inspect.Parameter.KEYWORD_ONLY,
            "expires": inspect.Parameter.KEYWORD_ONLY,
            "domain": inspect.Parameter.KEYWORD_ONLY,
            "path": inspect.Parameter.KEYWORD_ONLY,
            "httpOnly": inspect.Parameter.KEYWORD_ONLY,
            "secure": inspect.Parameter.KEYWORD_ONLY,
        },
    },
    "get_cookie": {
        "callable": web.get_cookie,
        "parameter_order": ("url", "mode", "name"),
        "required": ("url",),
        "defaults": {"mode": "cef", "name": None},
        "kinds": {
            "url": inspect.Parameter.POSITIONAL_OR_KEYWORD,
            "mode": inspect.Parameter.POSITIONAL_OR_KEYWORD,
            "name": inspect.Parameter.KEYWORD_ONLY,
        },
    },
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
    "cookie_api_unavailable",
    "native_host_unavailable",
    "plugin_not_connected",
    "web_bridge_unavailable",
    "web_host_unavailable",
    "web_ipc_unreachable",
    "web_runtime_incompatible",
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


def _marked_url(base_url: str, run_id: str) -> str:
    parts = urlsplit(base_url)
    query = [
        (key, value)
        for key, value in parse_qsl(parts.query, keep_blank_values=True)
        if key != RUN_QUERY_KEY
    ]
    query.append((RUN_QUERY_KEY, run_id))
    return urlunsplit((parts.scheme, parts.netloc, parts.path or "/", urlencode(query), ""))


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
    )


def check_contract() -> dict[str, Any]:
    checks: dict[str, dict[str, bool]] = {}
    try:
        for api_name, expected in EXPECTED_CONTRACTS.items():
            parameters = inspect.signature(expected["callable"]).parameters
            checks[api_name] = {
                "parameter_order_ok": tuple(parameters) == expected["parameter_order"],
                "required_parameters_ok": all(
                    parameters[name].default is inspect.Parameter.empty
                    for name in expected["required"]
                ),
                "defaults_ok": all(
                    parameters[name].default == value
                    for name, value in expected["defaults"].items()
                ),
                "parameter_kinds_ok": all(
                    parameters[name].kind == value
                    for name, value in expected["kinds"].items()
                ),
            }
        passed = all(all(api_checks.values()) for api_checks in checks.values())
        return _result(
            "api_contract",
            "PASS" if passed else "FAIL",
            "两个公开签名符合当前合同" if passed else "公开签名与当前合同不一致",
            contracts=checks,
        )
    except Exception as exc:  # noqa: BLE001
        return _result("api_contract", "FAIL", "无法检查公开签名", **_error_fields(exc))


def preflight_target(base_url: str, timeout: float) -> dict[str, Any]:
    started = time.perf_counter()
    try:
        request = Request(base_url, headers={"User-Agent": "UIAutoma-SDK-persistent-test"})
        with urlopen(request, timeout=timeout) as response:
            status_code = int(getattr(response, "status", 200))
        passed = 200 <= status_code < 400
        return _result(
            "target_preflight",
            "PASS" if passed else "BLOCKED",
            "外部靶场可访问" if passed else "外部靶场未返回成功状态",
            elapsed_ms=round((time.perf_counter() - started) * 1000, 1),
            http_status=status_code,
        )
    except Exception as exc:  # noqa: BLE001
        return _result(
            "target_preflight",
            "BLOCKED",
            "外部靶场不可访问",
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


def prepare_owned_page(
    mode: str,
    target_url: str,
    load_timeout: float,
) -> tuple[dict[str, Any], WebBrowser | None]:
    started = time.perf_counter()
    page: WebBrowser | None = None
    try:
        page = web.create(target_url, mode, load_timeout=load_timeout, silent_running=True)
        type_ok = isinstance(page, WebBrowser)
        mode_ok = str(page.mode or "").casefold() == mode.casefold()
        url_ok = _canonical_url(page.url) == _canonical_url(target_url)
        passed = type_ok and mode_ok and url_ok
        return (
            _result(
                "owned_page_setup",
                "PASS" if passed else "BLOCKED",
                "本次唯一页面已准备" if passed else "本次测试页面准备结果不完整",
                elapsed_ms=round((time.perf_counter() - started) * 1000, 1),
                returned_type_ok=type_ok,
                mode_ok=mode_ok,
                url_ok=url_ok,
            ),
            page,
        )
    except Exception as exc:  # noqa: BLE001
        return (
            _result(
                "owned_page_setup",
                "BLOCKED",
                "无法准备本次唯一页面",
                elapsed_ms=round((time.perf_counter() - started) * 1000, 1),
                **_error_fields(exc),
            ),
            page,
        )


def run_set_cookie_case(
    mode: str,
    target_url: str,
    cookie_name: str,
    cookie_value: str,
) -> dict[str, Any]:
    started = time.perf_counter()
    try:
        returned = web.set_cookie(
            target_url,
            mode,
            name=cookie_name,
            value=cookie_value,
            sessionCookie=True,
            path="/",
            httpOnly=False,
            secure=False,
        )
        return_ok = returned is None
        return _result(
            "set_session_cookie",
            "PASS" if return_ok else "FAIL",
            "set_cookie 完成唯一会话 Cookie 写入" if return_ok else "set_cookie 返回值不符合合同",
            elapsed_ms=round((time.perf_counter() - started) * 1000, 1),
            call_completed=True,
            return_is_none=return_ok,
        )
    except Exception as exc:  # noqa: BLE001
        status = _error_status(exc)
        return _result(
            "set_session_cookie",
            status,
            "set_cookie 被环境阻塞" if status == "BLOCKED" else "set_cookie 调用失败",
            elapsed_ms=round((time.perf_counter() - started) * 1000, 1),
            call_completed=False,
            **_error_fields(exc),
        )


def run_get_cookie_case(
    mode: str,
    target_url: str,
    cookie_name: str,
    cookie_value: str,
) -> dict[str, Any]:
    started = time.perf_counter()
    try:
        cookie = web.get_cookie(target_url, mode, name=cookie_name)
        returned_type_ok = isinstance(cookie, dict)
        name_ok = returned_type_ok and cookie.get("name") == cookie_name
        value_ok = returned_type_ok and cookie.get("value") == cookie_value
        path_ok = returned_type_ok and cookie.get("path") == "/"
        session_ok = returned_type_ok and cookie.get("session") is True
        http_only_ok = returned_type_ok and cookie.get("httpOnly") is False
        secure_ok = returned_type_ok and cookie.get("secure") is False
        passed = all(
            (
                returned_type_ok,
                name_ok,
                value_ok,
                path_ok,
                session_ok,
                http_only_ok,
                secure_ok,
            )
        )
        return _result(
            "get_session_cookie",
            "PASS" if passed else "FAIL",
            "get_cookie 精确取回本次 Cookie" if passed else "get_cookie 返回内容不符合写入合同",
            elapsed_ms=round((time.perf_counter() - started) * 1000, 1),
            returned_type_ok=returned_type_ok,
            name_ok=name_ok,
            value_ok=value_ok,
            path_ok=path_ok,
            session_ok=session_ok,
            http_only_ok=http_only_ok,
            secure_ok=secure_ok,
        )
    except Exception as exc:  # noqa: BLE001
        status = _error_status(exc)
        return _result(
            "get_session_cookie",
            status,
            "get_cookie 被环境阻塞" if status == "BLOCKED" else "get_cookie 调用失败",
            elapsed_ms=round((time.perf_counter() - started) * 1000, 1),
            **_error_fields(exc),
        )


def cleanup_owned_resources(
    page: WebBrowser | None,
    target_url: str,
    mode: str,
    cookie_name: str,
    *,
    cookie_may_exist: bool,
) -> dict[str, Any]:
    items: list[dict[str, Any]] = []

    if cookie_may_exist:
        remove_ok = False
        absent_confirmed = False
        cookie_item: dict[str, Any] = {"resource": "cookie"}
        try:
            web.remove_cookie(target_url, cookie_name, mode)
            remove_ok = True
        except Exception as exc:  # noqa: BLE001
            cookie_item.update(
                remove_exception=exc.__class__.__name__,
                remove_trace_info=_safe_trace(exc),
            )
        try:
            remaining = web.get_cookie(target_url, mode, name=cookie_name)
            absent_confirmed = not remaining
        except Exception as exc:  # noqa: BLE001
            cookie_item.update(
                verify_exception=exc.__class__.__name__,
                verify_trace_info=_safe_trace(exc),
            )
        cookie_status = "PASS" if remove_ok and absent_confirmed else "FAIL"
        cookie_item.update(
            status=cookie_status,
            confirmed=cookie_status == "PASS",
            remove_ok=remove_ok,
            absent_confirmed=absent_confirmed,
        )
        items.append(cookie_item)

    if page is not None:
        page_item: dict[str, Any] = {"resource": "page"}
        if _canonical_url(page.url) != _canonical_url(target_url):
            page_item.update(
                status="FAIL",
                confirmed=False,
                reason="owned_page_identity_mismatch",
            )
        else:
            try:
                page.close()
                page_item.update(status="PASS", confirmed=True)
            except Exception as exc:  # noqa: BLE001
                page_item.update(
                    status="FAIL",
                    confirmed=False,
                    reason="close_failed",
                    **_error_fields(exc),
                )
        items.append(page_item)

    passed = all(item["status"] == "PASS" for item in items)
    return _result(
        "owned_resources_cleanup",
        "PASS" if passed else "FAIL",
        "本次 Cookie 与页面已逐项清理" if passed else "本次资源未能全部精确清理",
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
            "apis": ["uiautoma.web.set_cookie", "uiautoma.web.get_cookie"],
            "status": status,
            "exit_code": exit_code,
            "mode": args.mode,
            "contract_only": bool(args.contract_only),
            "results": list(results),
            "excluded": [
                "edge",
                "cef",
                "auto",
                "sessionCookie=False 与 expires 持久化期限",
                "domain 自定义作用域",
                "httpOnly=True",
                "secure=True 与 HTTPS",
                "空值与 Unicode 值",
                "分区 Cookie",
                "浏览器重启后的持久化保留",
            ],
        },
        exit_code,
    )


def run(args: argparse.Namespace) -> tuple[dict[str, Any], int]:
    results = [check_contract()]
    if results[-1]["status"] != "PASS" or args.contract_only:
        return _report(args, results)

    results.append(preflight_target(args.base_url, args.preflight_timeout))
    if results[-1]["status"] != "PASS":
        return _report(args, results)

    results.append(preflight_runtime(args.runtime_timeout))
    if results[-1]["status"] != "PASS":
        return _report(args, results)

    run_id = uuid.uuid4().hex
    target_url = _marked_url(args.base_url, run_id)
    cookie_name = f"uiautoma_sdk_{run_id}"
    cookie_value = f"value_{run_id}"
    page: WebBrowser | None = None
    cookie_may_exist = False
    try:
        setup_result, page = prepare_owned_page(args.mode, target_url, args.load_timeout)
        results.append(setup_result)
        if setup_result["status"] == "PASS":
            cookie_may_exist = True
            set_result = run_set_cookie_case(
                args.mode,
                target_url,
                cookie_name,
                cookie_value,
            )
            results.append(set_result)
            if set_result.get("call_completed") is True:
                results.append(
                    run_get_cookie_case(
                        args.mode,
                        target_url,
                        cookie_name,
                        cookie_value,
                    )
                )
    finally:
        results.append(
            cleanup_owned_resources(
                page,
                target_url,
                args.mode,
                cookie_name,
                cookie_may_exist=cookie_may_exist,
            )
        )
    return _report(args, results)


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="运行 uiautoma.web.set_cookie() 与 get_cookie() 持久化真实浏览器测试。"
    )
    parser.add_argument("--mode", required=True, choices=["chrome"], help="浏览器模式；当前只支持 chrome。")
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL, help=f"外部靶场页面，默认 {DEFAULT_BASE_URL}")
    parser.add_argument("--load-timeout", type=float, default=20.0, help="准备页面的加载超时秒数，默认 20。")
    parser.add_argument("--preflight-timeout", type=float, default=2.0, help="靶场预检超时秒数，默认 2。")
    parser.add_argument("--runtime-timeout", type=float, default=5.0, help="Runtime 预检超时秒数，默认 5。")
    parser.add_argument("--contract-only", action="store_true", help="只检查公开签名，不连接 Runtime、靶场或浏览器。")
    args = parser.parse_args(argv)
    try:
        args.base_url = _validate_url(args.base_url, "--base-url")
    except argparse.ArgumentTypeError as exc:
        parser.error(str(exc))
    if args.load_timeout <= 0:
        parser.error("--load-timeout 必须大于 0")
    if args.preflight_timeout <= 0:
        parser.error("--preflight-timeout 必须大于 0")
    if args.runtime_timeout <= 0:
        parser.error("--runtime-timeout 必须大于 0")
    return args


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    report, exit_code = run(args)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
