"""uiautoma.web.get_cookie() 独立验收脚本。"""
from __future__ import annotations

import argparse
import inspect
import sys
from pathlib import Path
from typing import Any

PRODUCT_ROOT = Path(__file__).resolve().parents[3]
SDK_SRC = PRODUCT_ROOT / "sdk" / "src"
if str(SDK_SRC) not in sys.path:
    sys.path.insert(0, str(SDK_SRC))

from uiautoma import web  # noqa: E402
from uiautoma.web import WebBrowser  # noqa: E402

__test__ = False
DEFAULT_URL = "https://baobaomi900901.github.io/xpath/#/cookie-test"
GREEN, RED, RESET = "\x1b[92m", "\x1b[91m", "\x1b[0m"


def result(case_id: str, status: str, detail: str, **extra: Any) -> dict[str, Any]:
    return {"case_id": case_id, "status": status, "detail": detail, **extra}


def check_contract() -> dict[str, Any]:
    signature = inspect.signature(web.get_cookie)
    expected = ("url", "mode", "name")
    actual = tuple(signature.parameters)
    kinds_ok = signature.parameters["url"].kind == inspect.Parameter.POSITIONAL_OR_KEYWORD and signature.parameters["mode"].kind == inspect.Parameter.POSITIONAL_OR_KEYWORD and signature.parameters["name"].kind == inspect.Parameter.KEYWORD_ONLY
    defaults_ok = signature.parameters["mode"].default == "auto" and signature.parameters["name"].default is None
    ok = actual == expected and kinds_ok and defaults_ok
    return result("api_contract", "PASS" if ok else "FAIL",
                  "公开签名符合当前合同" if ok else "公开签名、参数顺序或默认值不一致",
                  parameter_order_ok=actual == expected, parameter_kinds_ok=kinds_ok, defaults_ok=defaults_ok)


def run(args: argparse.Namespace) -> tuple[list[dict[str, Any]], int]:
    results = [check_contract()]
    if results[-1]["status"] != "PASS" or args.contract_only:
        return results, 0 if results[-1]["status"] == "PASS" else 1
    page: WebBrowser | None = None
    cookie_name = "uiautoma_get_cookie_test"
    try:
        page = web.create(args.target_url, mode=args.mode, load_timeout=args.load_timeout)
        results.append(result("test_page_prepare", "PASS" if isinstance(page, WebBrowser) else "FAIL",
                              "已打开 Cookie 测试页面" if isinstance(page, WebBrowser) else "返回对象类型错误"))
        web.set_cookie(args.target_url, args.mode, name=cookie_name, value="get-cookie-value", sessionCookie=True, path="/")
        cookie = web.get_cookie(args.target_url, args.mode, name=cookie_name)
        ok = isinstance(cookie, dict) and cookie.get("name") == cookie_name and cookie.get("value") == "get-cookie-value"
        results.append(result("get_existing", "PASS" if ok else "FAIL",
                              "返回指定 Cookie 且名称和值正确" if ok else "指定 Cookie 内容不正确"))
        missing = web.get_cookie(args.target_url, args.mode, name="uiautoma_cookie_not_found")
        results.append(result("not_found", "PASS" if missing == {} else "FAIL",
                              "未命中返回空字典" if missing == {} else "未命中未返回空字典"))
        repeated = [web.get_cookie(args.target_url, args.mode, name=cookie_name) for _ in range(3)]
        results.append(result("repeat_read", "PASS" if repeated[0] == repeated[1] == repeated[2] else "FAIL",
                              "连续三次读取结果稳定" if repeated[0] == repeated[1] == repeated[2] else "重复读取结果变化"))
        try:
            web.get_cookie(args.target_url, args.mode)
        except ValueError:
            results.append(result("missing_name", "PASS", "缺少 name 被 ValueError 拒绝"))
        else:
            results.append(result("missing_name", "FAIL", "缺少 name 未被拒绝"))
        try:
            web.get_cookie(args.target_url, args.mode, cookie_name)
        except TypeError:
            results.append(result("keyword_only", "PASS", "name 位置传入被 TypeError 拒绝"))
        else:
            results.append(result("keyword_only", "FAIL", "name 位置传入未被拒绝"))
    except Exception as exc:  # noqa: BLE001
        results.append(result("scenario", "FAIL", "get_cookie() 场景执行失败",
                              exception=type(exc).__name__, error=str(exc)))
    finally:
        try:
            web.remove_cookie(args.target_url, cookie_name, args.mode)
        except Exception:
            pass
        if page is not None:
            try:
                page.close(ignore_beforeunload=True)
                results.append(result("cleanup", "PASS", "测试 Cookie 与页面已清理"))
            except Exception as exc:  # noqa: BLE001
                results.append(result("cleanup", "FAIL", "页面关闭失败", exception=type(exc).__name__))
    return results, 0 if all(item["status"] == "PASS" for item in results) else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="uiautoma.web.get_cookie() Web API 验收")
    parser.add_argument("--target-url", default=DEFAULT_URL)
    parser.add_argument("--mode", choices=("auto", "chrome", "edge"), default="chrome")
    parser.add_argument("--load-timeout", type=float, default=20)
    parser.add_argument("--contract-only", action="store_true")
    args = parser.parse_args(argv)
    results, code = run(args)
    print("UIAutoma Web API 测试")
    print(" API     : uiautoma.web.get_cookie")
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
