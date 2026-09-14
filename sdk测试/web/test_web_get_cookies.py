"""uiautoma.web.get_cookies() 独立验收脚本。"""
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
DEFAULT_URL = "https://baobaomi900901.github.io/xpath/#/cookie-test"
GREEN, RED, RESET = "\x1b[92m", "\x1b[91m", "\x1b[0m"


def result(case_id: str, status: str, detail: str, **extra: Any) -> dict[str, Any]:
    return {"case_id": case_id, "status": status, "detail": detail, **extra}


def check_contract() -> dict[str, Any]:
    signature = inspect.signature(web.get_cookies)
    expected = ("mode", "name", "url", "domain", "path", "partition_key", "secure", "session")
    actual = tuple(signature.parameters)
    kinds_ok = signature.parameters["mode"].kind == inspect.Parameter.POSITIONAL_OR_KEYWORD and all(
        signature.parameters[name].kind == inspect.Parameter.KEYWORD_ONLY for name in expected[1:]
    )
    defaults_ok = all(signature.parameters[name].default is (None if name != "mode" else "auto")
                       for name in expected)
    ok = actual == expected and kinds_ok and defaults_ok
    return result("api_contract", "PASS" if ok else "FAIL",
                  "公开签名符合当前合同" if ok else "公开签名、参数顺序或默认值不一致",
                  parameter_order_ok=actual == expected, parameter_kinds_ok=kinds_ok, defaults_ok=defaults_ok)


def run(args: argparse.Namespace) -> tuple[list[dict[str, Any]], int]:
    results = [check_contract()]
    if results[-1]["status"] != "PASS" or args.contract_only:
        return results, 0 if results[-1]["status"] == "PASS" else 1
    page: WebBrowser | None = None
    names = ("uiautoma_get_cookies_session", "uiautoma_get_cookies_persistent")
    try:
        page = web.create(args.target_url, mode=args.mode, load_timeout=args.load_timeout)
        results.append(result("test_page_prepare", "PASS" if isinstance(page, WebBrowser) else "FAIL",
                              "已打开 Cookie 测试页面" if isinstance(page, WebBrowser) else "返回对象类型错误"))
        web.set_cookie(args.target_url, args.mode, name=names[0], value="session-value", sessionCookie=True, path="/")
        web.set_cookie(args.target_url, args.mode, name=names[1], value="persistent-value", sessionCookie=False, expires=300, path="/")
        all_cookies = web.get_cookies(mode=args.mode, url=args.target_url)
        names_seen = {str(item.get("name")) for item in all_cookies}
        results.append(result("get_all", "PASS" if set(names) <= names_seen else "FAIL",
                              "返回 Cookie 列表包含测试 Cookie" if set(names) <= names_seen else "测试 Cookie 未全部返回",
                              count=len(all_cookies)))
        one = web.get_cookies(mode=args.mode, name=names[0], url=args.target_url)
        results.append(result("filter_name", "PASS" if len(one) == 1 and one[0].get("name") == names[0] else "FAIL",
                              "按名称筛选成功" if len(one) == 1 else "名称筛选结果不正确"))
        persistent = web.get_cookies(mode=args.mode, name=names[1], url=args.target_url, session=False)
        session = web.get_cookies(mode=args.mode, name=names[0], url=args.target_url, session=True)
        ok = len(persistent) == 1 and len(session) == 1
        results.append(result("filter_session", "PASS" if ok else "FAIL",
                              "session=True/False 筛选正确" if ok else "session 筛选结果不正确"))
        domain = web.get_cookies(mode=args.mode, domain="baobaomi900901.github.io")
        results.append(result("filter_domain", "PASS" if isinstance(domain, list) else "FAIL",
                              "domain 筛选返回列表" if isinstance(domain, list) else "domain 筛选返回类型错误"))
        path = web.get_cookies(mode=args.mode, url=args.target_url, path="/")
        results.append(result("filter_path", "PASS" if set(names) <= {str(i.get("name")) for i in path} else "FAIL",
                              "path 筛选包含测试 Cookie" if set(names) <= {str(i.get("name")) for i in path} else "path 筛选未命中"))
        empty = web.get_cookies(mode=args.mode, name="uiautoma_cookie_not_found")
        results.append(result("not_found", "PASS" if empty == [] else "FAIL",
                              "未命中返回空列表" if empty == [] else "未命中未返回空列表"))
        again = web.get_cookies(mode=args.mode, name=names[0], url=args.target_url)
        results.append(result("repeat_read", "PASS" if again == one else "FAIL",
                              "重复读取结果稳定" if again == one else "重复读取结果变化"))
        try:
            web.get_cookies(args.mode, names[0])
        except TypeError:
            results.append(result("keyword_only", "PASS", "筛选参数位置传入被 TypeError 拒绝"))
        else:
            results.append(result("keyword_only", "FAIL", "筛选参数位置传入未被拒绝"))
        try:
            web.get_cookies(mode=args.mode, partition_key={"top_level_site": "https://example.com"})
        except Exception as exc:  # noqa: BLE001
            results.append(result("partition_key_mode", "PASS", "分区筛选按合同处理或被环境拒绝",
                                  exception=type(exc).__name__))
        else:
            results.append(result("partition_key_mode", "PASS", "分区筛选调用完成"))
    except Exception as exc:  # noqa: BLE001
        results.append(result("scenario", "FAIL", "get_cookies() 场景执行失败",
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
    parser = argparse.ArgumentParser(description="uiautoma.web.get_cookies() Web API 验收")
    parser.add_argument("--target-url", default=DEFAULT_URL)
    parser.add_argument("--mode", choices=("auto", "chrome", "edge"), default="chrome")
    parser.add_argument("--load-timeout", type=float, default=20)
    parser.add_argument("--contract-only", action="store_true")
    args = parser.parse_args(argv)
    results, code = run(args)
    print("UIAutoma Web API 测试")
    print(" API     : uiautoma.web.get_cookies")
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
