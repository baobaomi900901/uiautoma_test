"""uiautoma.web.get_active() 独立验收脚本。"""
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
DEFAULT_URL = "https://baobaomi900901.github.io/xpath/#/iframe-shadow-form"
GREEN, RED, RESET = "\x1b[92m", "\x1b[91m", "\x1b[0m"


def result(case_id: str, status: str, detail: str, **extra: Any) -> dict[str, Any]:
    return {"case_id": case_id, "status": status, "detail": detail, **extra}


def check_contract() -> dict[str, Any]:
    signature = inspect.signature(web.get_active)
    expected = ("mode", "load_timeout", "stop_if_timeout", "silent_running")
    actual = tuple(signature.parameters)
    kinds_ok = signature.parameters["mode"].kind == inspect.Parameter.POSITIONAL_OR_KEYWORD and all(
        signature.parameters[name].kind == inspect.Parameter.KEYWORD_ONLY for name in expected[1:]
    )
    defaults = {"mode": "auto", "load_timeout": 20, "stop_if_timeout": False, "silent_running": False}
    defaults_ok = all(signature.parameters[name].default == value for name, value in defaults.items())
    ok = actual == expected and kinds_ok and defaults_ok
    return result("api_contract", "PASS" if ok else "FAIL",
                  "公开签名符合当前合同" if ok else "公开签名、参数顺序或默认值不一致",
                  parameter_order_ok=actual == expected, parameter_kinds_ok=kinds_ok,
                  defaults_ok=defaults_ok, return_annotation=str(signature.return_annotation))


def run(args: argparse.Namespace) -> tuple[list[dict[str, Any]], int]:
    results = [check_contract()]
    if results[-1]["status"] != "PASS" or args.contract_only:
        return results, 0 if results[-1]["status"] == "PASS" else 1
    page: WebBrowser | None = None
    try:
        page = web.create(args.target_url, mode=args.mode, load_timeout=args.load_timeout)
        results.append(result("test_page_prepare", "PASS" if isinstance(page, WebBrowser) else "FAIL",
                              "已打开测试页面" if isinstance(page, WebBrowser) else "返回对象类型错误"))
        if not isinstance(page, WebBrowser):
            return results, 1
        page.activate()
        active = web.get_active(mode=args.mode, load_timeout=0)
        same = isinstance(active, WebBrowser) and active.id == page.id
        results.append(result("get_active_default", "PASS" if same else "FAIL",
                              "返回当前活动页面" if same else "未返回当前活动页面", page_id=getattr(active, "id", "")))
        for case_id, timeout in (("zero_timeout", 0), ("none_timeout", None)):
            active = web.get_active(mode=args.mode, load_timeout=timeout)
            ok = isinstance(active, WebBrowser) and active.id == page.id
            results.append(result(case_id, "PASS" if ok else "FAIL",
                                  "活动页面匹配" if ok else "活动页面不匹配"))
        reads = [web.get_active(mode=args.mode, load_timeout=0).id for _ in range(3)]
        results.append(result("repeat_read", "PASS" if len(set(reads)) == 1 else "FAIL",
                              "连续三次返回同一活动页面" if len(set(reads)) == 1 else "重复读取结果变化"))
        try:
            web.get_active(mode=args.mode, load_timeout=-2)
        except Exception as exc:  # noqa: BLE001
            results.append(result("invalid_timeout", "PASS", "非法超时被拒绝", exception=type(exc).__name__))
        else:
            results.append(result("invalid_timeout", "FAIL", "非法超时未被拒绝"))
        try:
            web.get_active(args.mode, 0)
        except TypeError:
            results.append(result("keyword_only", "PASS", "额外位置参数被 TypeError 拒绝"))
        else:
            results.append(result("keyword_only", "FAIL", "额外位置参数未被拒绝"))
    except Exception as exc:  # noqa: BLE001
        results.append(result("scenario", "FAIL", "get_active() 场景执行失败",
                              exception=type(exc).__name__, error=str(exc)))
    finally:
        if page is not None:
            try:
                page.close(ignore_beforeunload=True)
                results.append(result("cleanup", "PASS", "已关闭测试页面"))
            except Exception as exc:  # noqa: BLE001
                results.append(result("cleanup", "FAIL", "页面关闭失败", exception=type(exc).__name__))
    return results, 0 if all(item["status"] == "PASS" for item in results) else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="uiautoma.web.get_active() Web API 验收")
    parser.add_argument("--target-url", default=DEFAULT_URL)
    parser.add_argument("--mode", choices=("auto", "chrome", "edge"), default="chrome")
    parser.add_argument("--load-timeout", type=float, default=20)
    parser.add_argument("--contract-only", action="store_true")
    args = parser.parse_args(argv)
    results, code = run(args)
    print("UIAutoma Web API 测试")
    print(" API     : uiautoma.web.get_active")
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
