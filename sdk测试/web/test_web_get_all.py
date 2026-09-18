"""uiautoma.web.get_all() 独立验收脚本。"""
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


def result(case_id: str, status: str, detail: str, **extra: Any) -> dict[str, Any]:
    return {"case_id": case_id, "status": status, "detail": detail, **extra}


def check_contract() -> dict[str, Any]:
    signature = inspect.signature(web.get_all)
    expected = ("mode", "title", "url", "use_wildcard", "silent_running")
    actual = tuple(signature.parameters)
    kinds_ok = signature.parameters["mode"].kind == inspect.Parameter.POSITIONAL_OR_KEYWORD and all(
        signature.parameters[name].kind == inspect.Parameter.KEYWORD_ONLY for name in expected[1:]
    )
    defaults = {"mode": "auto", "title": None, "url": None, "use_wildcard": False, "silent_running": False}
    defaults_ok = all(signature.parameters[name].default == value for name, value in defaults.items())
    ok = actual == expected and kinds_ok and defaults_ok
    return result("api_contract", "PASS" if ok else "FAIL",
                  "公开签名符合当前合同" if ok else "公开签名、参数顺序或默认值不一致",
                  parameter_order_ok=actual == expected, parameter_kinds_ok=kinds_ok, defaults_ok=defaults_ok)


def run(args: argparse.Namespace) -> tuple[list[dict[str, Any]], int]:
    results = [check_contract()]
    if results[-1]["status"] != "PASS" or args.contract_only:
        return results, 0 if results[-1]["status"] == "PASS" else 1
    pages: list[WebBrowser] = []
    try:
        page = web.create(args.target_url, mode=args.mode, load_timeout=args.load_timeout)
        pages.append(page)
        results.append(result("test_page_prepare", "PASS" if isinstance(page, WebBrowser) else "FAIL",
                              "已打开测试页面" if isinstance(page, WebBrowser) else "返回对象类型错误"))
        if not isinstance(page, WebBrowser):
            return results, 1
        title, current_url = page.get_title(), page.get_url()
        # main 已移除 WebBrowser.id：改用 (url|title) 组合键识别目标标签
        target_key = page_key(page)
        all_pages = web.get_all(mode=args.mode, url=current_url)
        ok = isinstance(all_pages, list) and any(page_key(p) == target_key for p in all_pages)
        results.append(result("get_all_by_url", "PASS" if ok else "FAIL",
                              "返回列表包含目标页面" if ok else "列表未包含目标页面", count=len(all_pages)))
        by_title = web.get_all(mode=args.mode, title=title)
        ok = isinstance(by_title, list) and any(page_key(p) == target_key for p in by_title)
        results.append(result("get_all_by_title", "PASS" if ok else "FAIL",
                              "标题筛选包含目标页面" if ok else "标题筛选未命中", count=len(by_title)))
        wildcard = web.get_all(mode=args.mode, url=current_url, use_wildcard=True)
        ok = isinstance(wildcard, list) and any(page_key(p) == target_key for p in wildcard)
        results.append(result("get_all_wildcard", "PASS" if ok else "FAIL",
                              "通配符筛选包含目标页面" if ok else "通配符筛选未命中", count=len(wildcard)))
        # 不构造任何域名：改用哨兵标题过滤（只做标签匹配，不打开任何页面）
        missing_title = "__uiautoma_no_such_title__"
        empty = web.get_all(mode=args.mode, title=missing_title)
        results.append(result("not_found_zero", "PASS" if empty == [] else "FAIL",
                              "未命中返回空列表" if empty == [] else "未命中未返回空列表"))
        first = [page_key(p) for p in web.get_all(mode=args.mode, url=current_url)]
        second = [page_key(p) for p in web.get_all(mode=args.mode, url=current_url)]
        results.append(result("repeat_read", "PASS" if first == second else "FAIL",
                              "重复读取顺序稳定" if first == second else "重复读取顺序变化"))
        try:
            web.get_all(args.mode, 0)
        except TypeError:
            results.append(result("keyword_only", "PASS", "额外位置参数被 TypeError 拒绝"))
        else:
            results.append(result("keyword_only", "FAIL", "额外位置参数未被拒绝"))
    except Exception as exc:  # noqa: BLE001
        results.append(result("scenario", "FAIL", "get_all() 场景执行失败",
                              exception=type(exc).__name__, error=str(exc)))
    finally:
        cleanup_ok = True
        for page in pages:
            try:
                page.close(ignore_beforeunload=True)
            except Exception:
                cleanup_ok = False
        results.append(result("cleanup", "PASS" if cleanup_ok else "FAIL",
                              "已关闭测试页面" if cleanup_ok else "页面关闭失败"))
    return results, 0 if all(item["status"] == "PASS" for item in results) else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="uiautoma.web.get_all() Web API 验收")
    parser.add_argument("--target-url", default=DEFAULT_URL)
    parser.add_argument("--mode", choices=("auto", "chrome", "edge"), default="chrome")
    parser.add_argument("--load-timeout", type=float, default=20)
    parser.add_argument("--contract-only", action="store_true")
    args = parser.parse_args(argv)
    results, code = run(args)
    print("UIAutoma Web API 测试")
    print(" API     : uiautoma.web.get_all")
    print(f" 页面    : {args.target_url}")
    print("进度     状态    测试项                  测试结果")
    print("───────  ──────  ─────────────────────  ─────────────────────────────")
    for index, item in enumerate(results, 1):
        passed = item["status"] == "PASS"
        print(f"{index:02d}/{len(results):02d}    {(GREEN if passed else RED)}[{'通过' if passed else '失败'}]{RESET}  "
              f"{item['case_id']:<22}  {item['detail']}")
    print("─" * 72)
    print(f"{'测试通过' if code == 0 else '测试失败'} · {sum(i['status']=='PASS' for i in results)}/{len(results)} 通过 · 退出码 {code}")
    return code


if __name__ == "__main__":
    raise SystemExit(main())
