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

__test__ = False
DEFAULT_URL = "https://baobaomi900901.github.io/xpath/#/iframe-shadow-form"
GREEN, RED, RESET = "\x1b[92m", "\x1b[91m", "\x1b[0m"


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
                  page_id=getattr(page, "id", ""), actual_type=type(page).__name__)


def run(args: argparse.Namespace) -> tuple[list[dict[str, Any]], int]:
    results = [check_contract()]
    if results[-1]["status"] != "PASS" or args.contract_only:
        return results, 0 if results[-1]["status"] == "PASS" else 1

    page: WebBrowser | None = None
    opened: list[WebBrowser] = []
    try:
        started = time.perf_counter()
        page = web.create(args.target_url, mode=args.mode, load_timeout=args.load_timeout)
        opened.append(page)
        results.append(_expect_browser("test_page_prepare", page, "已打开测试页面并取得 WebBrowser"))
        if not isinstance(page, WebBrowser):
            return results, 1
        title = page.get_title()
        current_url = page.get_url()
        results.append(result("get_by_url", "PASS", "按 URL 获取同一页面",
                              elapsed_ms=round((time.perf_counter() - started) * 1000, 1),
                              matched_url=current_url))
        by_url = web.get(url=current_url, mode=args.mode, load_timeout=0)
        results[-1]["status"] = "PASS" if isinstance(by_url, WebBrowser) else "FAIL"
        by_title = web.get(title=title, mode=args.mode, load_timeout=0)
        results.append(_expect_browser("get_by_title", by_title, "按标题获取页面"))
        by_both = web.get(title=title, url=current_url, mode=args.mode, load_timeout=0)
        results.append(_expect_browser("get_by_title_and_url", by_both, "标题和 URL 同时匹配"))
        wildcard = web.get(url=current_url, mode=args.mode, use_wildcard=True, load_timeout=0)
        results.append(_expect_browser("get_wildcard", wildcard, "通配符筛选成功"))
        missing = f"https://example.invalid/uiautoma-get-{int(time.time() * 1000)}"
        try:
            web.get(url=missing, mode=args.mode, load_timeout=0)
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
        results.append(result("scenario", "FAIL", "get() 场景执行失败",
                              exception=type(exc).__name__, error=str(exc)))
    finally:
        cleanup_ok = True
        for item in opened:
            try:
                item.close(ignore_beforeunload=True)
            except Exception:
                cleanup_ok = False
        results.append(result("cleanup", "PASS" if cleanup_ok else "FAIL",
                              "已关闭测试页面" if cleanup_ok else "页面关闭失败"))
    return results, 0 if all(item["status"] == "PASS" for item in results) else 1


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
        color = GREEN if passed else RED
        print(f"{index:02d}/{len(results):02d}    {color}[{'通过' if passed else '失败'}]{RESET}  "
              f"{item['case_id']:<22}  {item['detail']}")
    print("─" * 72)
    print(f"{'测试通过' if code == 0 else '测试失败'} · {sum(i['status']=='PASS' for i in results)}/{len(results)} 通过 · 退出码 {code}")
    return code


if __name__ == "__main__":
    raise SystemExit(main())
