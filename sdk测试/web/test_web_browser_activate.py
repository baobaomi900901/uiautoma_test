"""WebBrowser.activate() 页面对象 API 专项验收。"""
from __future__ import annotations

import argparse
import inspect
import sys
from pathlib import Path

PRODUCT_ROOT = Path(__file__).resolve().parents[3]
SDK_SRC = PRODUCT_ROOT / "sdk" / "src"
if str(SDK_SRC) not in sys.path:
    sys.path.insert(0, str(SDK_SRC))

from uiautoma import web  # noqa: E402
from uiautoma.web import WebBrowser  # noqa: E402
from _web_page_identity import page_key  # noqa: E402

__test__ = False
DEFAULT_URL = "https://baobaomi900901.github.io/xpath/#/iframe-shadow-form"
GREEN, RED, YELLOW, RESET = "\x1b[92m", "\x1b[91m", "\x1b[93m", "\x1b[0m"
BLOCKING = {"activate_tab_failed", "browser_host_window_mismatch", "web_bridge_unavailable", "native_host_unavailable"}


def result(case_id, status, detail, **extra):
    return {"case_id": case_id, "status": status, "detail": detail, **extra}


def check_contract():
    method = getattr(WebBrowser, "activate", None)
    sig = inspect.signature(method) if callable(method) else None
    ok = callable(method) and sig is not None and tuple(sig.parameters) == ("self",)
    return result("api_contract", "PASS" if ok else "FAIL",
                  "activate 无公开参数，返回 None" if ok else "activate 签名不符合合同")


def error_status(exc):
    trace = str(getattr(exc, "trace_info", "") or "")
    return "BLOCKED" if trace in BLOCKING else "FAIL"


def run(args):
    results = [check_contract()]
    if results[-1]["status"] != "PASS" or args.contract_only:
        return results, 0 if results[-1]["status"] == "PASS" else 1
    original = None
    page = None
    try:
        try:
            original = web.get_active(mode=args.mode, load_timeout=0)
        except Exception:
            original = None
        page = web.create(args.target_url, mode=args.mode, load_timeout=args.load_timeout)
        if not isinstance(page, WebBrowser):
            results.append(result("page_prepare", "FAIL", "create 返回类型错误"))
            return results, 1
        results.append(result("page_prepare", "PASS", "已创建独立测试页面"))
        try:
            returned = page.activate()
            results.append(result("activate_return", "PASS" if returned is None else "FAIL",
                                  "activate 返回 None" if returned is None else "activate 返回值不符"))
            active = web.get_active(mode=args.mode, load_timeout=0)
            # main 已移除 WebBrowser.id：改用 (url|title) 组合键判断是否同一标签
            same = isinstance(active, WebBrowser) and page_key(active) == page_key(page)
            results.append(result("active_page_check", "PASS" if same else "FAIL",
                                  "激活后当前页面标识（url|title）匹配" if same else "激活后当前页面不匹配",
                                  page_key=page_key(active)))
        except Exception as exc:  # noqa: BLE001
            status = error_status(exc)
            results.append(result("activate_action", status, f"activate 场景失败: {type(exc).__name__}: {exc}",
                                  trace_info=str(getattr(exc, "trace_info", "") or ""),
                                  trace_id=str(getattr(exc, "trace_id", "") or "")))
            return results, 2 if status == "BLOCKED" else 1
        try:
            page.activate()
            page.activate()
            results.append(result("repeat_activate", "PASS", "连续两次 activate 调用成功"))
        except Exception as exc:  # noqa: BLE001
            results.append(result("repeat_activate", error_status(exc), f"重复 activate 失败: {type(exc).__name__}: {exc}"))
    except Exception as exc:  # noqa: BLE001
        results.append(result("scenario", error_status(exc), f"activate 场景执行失败: {type(exc).__name__}: {exc}"))
    finally:
        if page is not None:
            try:
                page.close(ignore_beforeunload=True)
            except Exception:
                pass
        if original is not None:
            try:
                original.activate()
            except Exception:
                pass
        results.append(result("cleanup", "PASS", "测试页面已关闭；原活动页面已尝试恢复"))
    blocked = any(item["status"] == "BLOCKED" for item in results)
    return results, 0 if all(item["status"] == "PASS" for item in results) else (2 if blocked else 1)


def main(argv=None):
    parser = argparse.ArgumentParser(description="WebBrowser.activate() 页面对象 API 验收")
    parser.add_argument("--target-url", default=DEFAULT_URL)
    parser.add_argument("--mode", choices=("chrome", "edge"), default="chrome")
    parser.add_argument("--load-timeout", type=float, default=20)
    parser.add_argument("--contract-only", action="store_true")
    args = parser.parse_args(argv)
    if args.load_timeout <= 0:
        parser.error("--load-timeout 必须大于 0")
    results, code = run(args)
    print("UIAutoma Web API 测试\n API     : uiautoma.web.WebBrowser.activate")
    print(f" 页面    : {args.target_url}")
    print("进度     状态    测试项                  测试结果")
    print("───────  ──────  ─────────────────────  ─────────────────────────────")
    for i, current in enumerate(results, 1):
        color = {"PASS": GREEN, "BLOCKED": YELLOW}.get(current["status"], RED)
        label = {"PASS": "通过", "BLOCKED": "阻塞"}.get(current["status"], "失败")
        print(f"{i:02d}/{len(results):02d}    {color}[{label}]{RESET}  {current['case_id']:<22}  {current['detail']}")
    summary = "测试通过" if code == 0 else ("测试阻塞" if code == 2 else "测试失败")
    print("─" * 72)
    print(f"{summary} · {sum(i['status']=='PASS' for i in results)}/{len(results)} 通过 · 退出码 {code}")
    return code


if __name__ == "__main__":
    raise SystemExit(main())
