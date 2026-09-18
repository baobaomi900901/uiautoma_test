"""uiautoma.web.get() 独立验收脚本。"""

from __future__ import annotations

import argparse
import inspect
import sys
import time
from pathlib import Path
from typing import Any

PRODUCT_ROOT = Path(__file__).resolve().parents[3]
SDK_SRC = PRODUCT_ROOT / "sdk" / "src"
if str(SDK_SRC) not in sys.path:
    sys.path.insert(0, str(SDK_SRC))

from uiautoma import web  # noqa: E402
from uiautoma.web import WebBrowser  # noqa: E402
from _web_page_identity import page_key  # noqa: E402

__test__ = False
DEFAULT_URL = "https://baobaomi900901.github.io/xpath/#/iframe-shadow-form"
GREEN, RED, RESET = "\x1b[92m", "\x1b[91m", "\x1b[0m"
BLOCKING_TRACES = {"web_browser_command_timeout", "browser_session_disconnected", "web_bridge_unavailable", "native_host_unavailable", "browser_host_window_mismatch", "activate_tab_failed"}


def result(case_id: str, status: str, detail: str, **extra: Any) -> dict[str, Any]:
    return {"case_id": case_id, "status": status, "detail": detail, **extra}


def check_contract() -> dict[str, Any]:
    signature = inspect.signature(web.get)
    expected = ("title", "url", "mode", "load_timeout", "use_wildcard", "stop_if_timeout",
                "open_page", "page_url", "silent_running")
    actual = tuple(signature.parameters)
    kinds_ok = all(
        signature.parameters[name].kind == (inspect.Parameter.POSITIONAL_OR_KEYWORD
                                             if name in {"title", "url", "mode"}
                                             else inspect.Parameter.KEYWORD_ONLY)
        for name in expected if name in signature.parameters
    )
    defaults = {
        "title": None, "url": None, "mode": "auto", "load_timeout": 20,
        "use_wildcard": False, "stop_if_timeout": False, "open_page": False,
        "page_url": None, "silent_running": False,
    }
    defaults_ok = all(signature.parameters[name].default == value for name, value in defaults.items())
    ok = actual == expected and kinds_ok and defaults_ok
    return result("api_contract", "PASS" if ok else "FAIL",
                  "公开签名符合当前合同" if ok else "公开签名、参数顺序或默认值不一致",
                  parameter_order_ok=actual == expected, parameter_kinds_ok=kinds_ok,
                  defaults_ok=defaults_ok, return_annotation=str(signature.return_annotation))


def _expect_browser(case_id: str, page: WebBrowser, detail: str) -> dict[str, Any]:
    return result(case_id, "PASS" if isinstance(page, WebBrowser) else "FAIL", detail,
                  page_key=page_key(page) if isinstance(page, WebBrowser) else "",
                  actual_type=type(page).__name__)


def _exception_status(exc: Exception) -> str:
    trace = str(getattr(exc, "trace_info", "") or "")
    raw = getattr(getattr(exc, "result", None), "raw", {})
    reason = _find_raw_field(raw, "failure_reason")
    return "BLOCKED" if trace in BLOCKING_TRACES or reason in BLOCKING_TRACES else "FAIL"


def _find_raw_field(value: object, field: str) -> str:
    if isinstance(value, dict):
        if value.get(field):
            return str(value[field])
        for child in value.values():
            found = _find_raw_field(child, field)
            if found:
                return found
    return ""


def _exception_details(exc: Exception) -> dict[str, str]:
    raw = getattr(getattr(exc, "result", None), "raw", {})
    return {
        "trace_info": str(getattr(exc, "trace_info", "") or ""),
        "trace_id": str(getattr(exc, "trace_id", "") or ""),
        "failure_reason": _find_raw_field(raw, "failure_reason"),
    }


def run(args: argparse.Namespace) -> tuple[list[dict[str, Any]], int]:
    results = [check_contract()]
    if results[-1]["status"] != "PASS" or args.contract_only:
        return results, 0 if results[-1]["status"] == "PASS" else 1

    page: WebBrowser | None = None
    opened: list[WebBrowser] = []
    try:
        started = time.perf_counter()
        try:
            page = web.create(args.target_url, mode=args.mode, load_timeout=args.load_timeout)
        except Exception as exc:
            status = _exception_status(exc)
            results.append(result("page_prepare", status, f"打开测试页面失败: {type(exc).__name__}: {exc}",
                                  trace_info=str(getattr(exc, "trace_info", "") or "")))
            return results, 2 if status == "BLOCKED" else 1
        opened.append(page)
        results.append(_expect_browser("page_prepare", page, "已打开测试页面并取得 WebBrowser"))
        if not isinstance(page, WebBrowser):
            return results, 1
        title = page.get_title()
        current_url = page.get_url()
        try:
            by_url = web.get(url=current_url, mode=args.mode, load_timeout=0)
        except Exception as exc:
            trace = str(getattr(exc, "trace_info", "") or getattr(exc, "error_code", "") or "")
            status = "BLOCKED" if trace in BLOCKING_TRACES else "FAIL"
            raw = getattr(getattr(exc, "result", None), "raw", None)
            results.append(result("get_by_url", status, f"get_by_url 调用失败: url={current_url!r}; {type(exc).__name__}: {exc}",
                                  **_exception_details(exc),
                                  error_code=str(getattr(exc, "error", "") or ""),
                                  strategy=str(getattr(exc, "strategy", "") or ""),
                                  fallback_reason=str(getattr(exc, "fallback_reason", "") or ""),
                                  log_lines=list(getattr(exc, "log_lines", []) or []), raw=raw if isinstance(raw, dict) else {}))
            return results, 2 if status == "BLOCKED" else 1
        results.append(result("get_by_url", "PASS" if isinstance(by_url, WebBrowser) else "FAIL", "按 URL 获取同一页面",
                              elapsed_ms=round((time.perf_counter() - started) * 1000, 1), matched_url=current_url))
        results[-1]["status"] = "PASS" if isinstance(by_url, WebBrowser) else "FAIL"
        try:
            by_title = web.get(title=title, mode=args.mode, load_timeout=0)
        except Exception as exc:
            raise RuntimeError(f"get_by_title 调用失败: title={title!r}; {type(exc).__name__}: {exc}") from exc
        results.append(_expect_browser("get_by_title", by_title, "按标题获取页面"))
        try:
            by_both = web.get(title=title, url=current_url, mode=args.mode, load_timeout=0)
        except Exception as exc:
            raise RuntimeError(f"get_by_title_and_url 调用失败: title={title!r}, url={current_url!r}; {type(exc).__name__}: {exc}") from exc
        results.append(_expect_browser("get_by_title_and_url", by_both, "标题和 URL 同时匹配"))
        try:
            wildcard = web.get(url=current_url, mode=args.mode, use_wildcard=True, load_timeout=0)
        except Exception as exc:
            raise RuntimeError(f"get_wildcard 调用失败: url={current_url!r}; {type(exc).__name__}: {exc}") from exc
        results.append(_expect_browser("get_wildcard", wildcard, "通配符筛选成功"))
        # 不构造任何域名：改用哨兵标题过滤（只做标签匹配，不打开任何页面）
        missing_title = "__uiautoma_no_such_title__"
        try:
            web.get(title=missing_title, mode=args.mode, load_timeout=0)
        except Exception as exc:  # noqa: BLE001
            results.append(result("not_found", "PASS", "未命中且 open_page=False 正确抛出异常",
                                  exception=type(exc).__name__))
        else:
            results.append(result("not_found", "FAIL", "未命中时未抛出异常"))
        try:
            web.get(url=current_url, page_url=current_url, mode=args.mode, load_timeout=0)
        except Exception as exc:  # noqa: BLE001
            results.append(result("page_url_requires_open", "PASS", "page_url 未启用 open_page 时被拒绝",
                                  exception=type(exc).__name__))
        else:
            results.append(result("page_url_requires_open", "FAIL", "非法 page_url 组合未被拒绝"))
    except Exception as exc:  # noqa: BLE001
        status = _exception_status(exc)
        trace = str(getattr(exc, "trace_info", "") or getattr(exc, "error_code", "") or "")
        results.append(result("scenario", status, f"get() 场景执行失败: {type(exc).__name__}: {exc}",
                              exception=type(exc).__name__, error=str(exc), trace_info=trace,
                              trace_id=str(getattr(exc, "trace_id", "") or "")))
    finally:
        cleanup_ok = True
        for item in opened:
            try:
                item.close(ignore_beforeunload=True)
            except Exception:
                cleanup_ok = False
        results.append(result("cleanup", "PASS" if cleanup_ok else "FAIL",
                              "已关闭测试页面" if cleanup_ok else "页面关闭失败"))
    if all(item["status"] == "PASS" for item in results):
        return results, 0
    return results, 2 if any(item["status"] == "BLOCKED" for item in results) else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="uiautoma.web.get() Web API 验收")
    parser.add_argument("--target-url", default=DEFAULT_URL)
    parser.add_argument("--mode", choices=("auto", "chrome", "edge"), default="chrome")
    parser.add_argument("--load-timeout", type=float, default=20)
    parser.add_argument("--contract-only", action="store_true")
    args = parser.parse_args(argv)
    results, code = run(args)
    print("UIAutoma Web API 测试")
    print(" API     : uiautoma.web.get")
    print(f" 页面    : {args.target_url}")
    print("进度     状态    测试项                  测试结果")
    print("───────  ──────  ─────────────────────  ─────────────────────────────")
    for index, item in enumerate(results, 1):
        passed = item["status"] == "PASS"
        label = {"PASS": "通过", "BLOCKED": "阻塞"}.get(item["status"], "失败")
        color = {"PASS": GREEN, "BLOCKED": "\x1b[93m"}.get(item["status"], RED)
        print(f"{index:02d}/{len(results):02d}    {color}[{label}]{RESET}  "
              f"{item['case_id']:<22}  {item['detail']}")
        if not passed:
            for key, name in (("trace_info", "追踪"), ("failure_reason", "失败原因"), ("trace_id", "追踪ID")):
                if item.get(key):
                    print(f"         {name}: {item[key]}")
    print("─" * 72)
    summary = "测试通过" if code == 0 else ("测试阻塞" if code == 2 else "测试失败")
    print(f"{summary} · {sum(i['status']=='PASS' for i in results)}/{len(results)} 通过 · 退出码 {code}")
    return code


if __name__ == "__main__":
    raise SystemExit(main())
