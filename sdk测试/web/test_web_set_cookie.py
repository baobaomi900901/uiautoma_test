"""uiautoma.web.set_cookie() 独立验收脚本。"""
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
    signature = inspect.signature(web.set_cookie)
    expected = ("url", "mode", "name", "value", "sessionCookie", "expires", "domain", "path", "httpOnly", "secure")
    actual = tuple(signature.parameters)
    kinds_ok = signature.parameters["url"].kind == inspect.Parameter.POSITIONAL_OR_KEYWORD and signature.parameters["mode"].kind == inspect.Parameter.POSITIONAL_OR_KEYWORD and all(signature.parameters[name].kind == inspect.Parameter.KEYWORD_ONLY for name in expected[2:])
    defaults = {"mode": "auto", "name": None, "value": None, "sessionCookie": True, "expires": 100, "domain": None, "path": None, "httpOnly": False, "secure": False}
    defaults_ok = all(signature.parameters[name].default == value for name, value in defaults.items())
    ok = actual == expected and kinds_ok and defaults_ok
    return result("api_contract", "PASS" if ok else "FAIL",
                  "公开签名符合当前合同" if ok else "公开签名、参数顺序或默认值不一致",
                  parameter_order_ok=actual == expected, parameter_kinds_ok=kinds_ok, defaults_ok=defaults_ok)


def run(args: argparse.Namespace) -> tuple[list[dict[str, Any]], int]:
    results = [check_contract()]
    if results[-1]["status"] != "PASS" or args.contract_only:
        return results, 0 if results[-1]["status"] == "PASS" else 1
    page: WebBrowser | None = None
    names = ("uiautoma_set_cookie_session", "uiautoma_set_cookie_persistent", "uiautoma_set_cookie_secure")
    try:
        page = web.create(args.target_url, mode=args.mode, load_timeout=args.load_timeout)
        results.append(result("test_page_prepare", "PASS" if isinstance(page, WebBrowser) else "FAIL",
                              "已打开 Cookie 测试页面" if isinstance(page, WebBrowser) else "返回对象类型错误"))
        returned = web.set_cookie(args.target_url, args.mode, name=names[0], value="session", sessionCookie=True, path="/")
        cookie = web.get_cookie(args.target_url, args.mode, name=names[0])
        ok = returned is None and cookie.get("value") == "session"
        results.append(result("set_session", "PASS" if ok else "FAIL",
                              "设置会话 Cookie 成功并返回 None" if ok else "会话 Cookie 结果不正确"))
        web.set_cookie(args.target_url, args.mode, name=names[1], value="persistent", sessionCookie=False, expires=300, path="/")
        cookie = web.get_cookie(args.target_url, args.mode, name=names[1])
        results.append(result("set_persistent", "PASS" if cookie.get("value") == "persistent" else "FAIL",
                              "设置持久 Cookie 成功" if cookie.get("value") == "persistent" else "持久 Cookie 结果不正确"))
        web.set_cookie(args.target_url, args.mode, name=names[2], value="secure", sessionCookie=True, httpOnly=True, secure=True, path="/")
        cookie = web.get_cookie(args.target_url, args.mode, name=names[2])
        ok = cookie.get("httpOnly") is True and cookie.get("secure") is True
        results.append(result("set_attributes", "PASS" if ok else "FAIL",
                              "httpOnly/secure 属性正确" if ok else "Cookie 属性不正确"))
        before = web.get_cookie(args.target_url, args.mode, name=names[0])
        returned = web.set_cookie(args.target_url, args.mode, name=names[0], value=None)
        after = web.get_cookie(args.target_url, args.mode, name=names[0])
        results.append(result("none_value", "PASS" if returned is None and after == before else "FAIL",
                              "value=None 不修改已有 Cookie" if returned is None and after == before else "value=None 行为不正确"))
        try:
            web.set_cookie(args.target_url, args.mode)
        except ValueError:
            results.append(result("missing_name", "PASS", "缺少 name 被 ValueError 拒绝"))
        else:
            results.append(result("missing_name", "FAIL", "缺少 name 未被拒绝"))
        try:
            web.set_cookie(args.target_url, args.mode, name="uiautoma_invalid_expires", value="x", sessionCookie=False, expires="bad")
        except (ValueError, TypeError):
            results.append(result("invalid_expires", "PASS", "非法 expires 被拒绝"))
        else:
            results.append(result("invalid_expires", "FAIL", "非法 expires 未被拒绝"))
        try:
            web.set_cookie(args.target_url, args.mode, names[0], "x")
        except TypeError:
            results.append(result("keyword_only", "PASS", "name/value 位置传入被 TypeError 拒绝"))
        else:
            results.append(result("keyword_only", "FAIL", "name/value 位置传入未被拒绝"))
    except Exception as exc:  # noqa: BLE001
        results.append(result("scenario", "FAIL", "set_cookie() 场景执行失败",
                              exception=type(exc).__name__, error=str(exc)))
    finally:
        for name in names:
            try:
                web.remove_cookie(args.target_url, name, args.mode)
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
    parser = argparse.ArgumentParser(description="uiautoma.web.set_cookie() Web API 验收")
    parser.add_argument("--target-url", default=DEFAULT_URL)
    parser.add_argument("--mode", choices=("auto", "chrome", "edge"), default="chrome")
    parser.add_argument("--load-timeout", type=float, default=20)
    parser.add_argument("--contract-only", action="store_true")
    args = parser.parse_args(argv)
    results, code = run(args)
    print("UIAutoma Web API 测试")
    print(" API     : uiautoma.web.set_cookie")
    print(f" 页面    : {args.target_url}")
    print("进度     状态    测试项                  测试结果")
    print("───────  ──────  ─────────────────────  ─────────────────────────────")
    for index, item in enumerate(results, 1):
        passed = item["status"] == "PASS"
        print(f"{index:02d}/{len(results):02d}    {(GREEN if passed else RED)}[{'通过' if passed else '失败'}]{RESET}  {item['case_id']:<22}  {item['detail']}")
    print("─" * 72)
    print(f"{'测试通过' if code == 0 else '测试失败'} · {sum(i['status']=='PASS' for i in results)}/{len(results)} 通过 · 退出码 {code}")
    return code


if __name__ == "__main__":
    raise SystemExit(main())
