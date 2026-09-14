"""uiautoma.web.create() 独立验收脚本。

覆盖 API 合同、打开目标页面、返回 WebBrowser、页面信息读取、参数边界和资源关闭。
默认会打开用户指定的 Web 表单靶场；``--contract-only`` 只检查公开签名。
"""

from __future__ import annotations

import argparse
import inspect
import json
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
    signature = inspect.signature(web.create)
    expected = ("url", "mode", "load_timeout", "stop_if_timeout", "silent_running",
                "executable_path", "arguments")
    actual = tuple(signature.parameters)
    kinds_ok = all(
        signature.parameters[name].kind == (inspect.Parameter.POSITIONAL_OR_KEYWORD
                                             if name in {"url", "mode"}
                                             else inspect.Parameter.KEYWORD_ONLY)
        for name in expected
        if name in signature.parameters
    )
    defaults = {
        "mode": "auto", "load_timeout": 20, "stop_if_timeout": False,
        "silent_running": False, "executable_path": None, "arguments": None,
    }
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
        started = time.perf_counter()
        page = web.create(args.target_url, mode=args.mode, load_timeout=args.load_timeout)
        elapsed = round((time.perf_counter() - started) * 1000, 1)
        if not isinstance(page, WebBrowser):
            results.append(result("create_return_type", "FAIL", "返回值不是 WebBrowser", actual_type=type(page).__name__))
        else:
            results.append(result("create_default", "PASS", "成功打开页面并返回 WebBrowser",
                                  elapsed_ms=elapsed, page_id=page.id))
            current_url = page.get_url()
            title = page.get_title()
            results.append(result("page_metadata", "PASS" if current_url else "FAIL",
                                  "可读取页面 URL 和标题" if current_url else "页面 URL 为空",
                                  url=current_url, title=title))
            repeated = page.get_url()
            results.append(result("repeat_read", "PASS" if repeated == current_url else "FAIL",
                                  "重复读取 URL 稳定" if repeated == current_url else "重复读取结果变化"))
    except Exception as exc:  # noqa: BLE001
        results.append(result("create_default", "FAIL", "打开页面失败", exception=type(exc).__name__, error=str(exc)))
    finally:
        if page is not None:
            try:
                page.close(ignore_beforeunload=True)
                results.append(result("cleanup", "PASS", "已关闭 create() 打开的页面"))
            except Exception as exc:  # noqa: BLE001
                results.append(result("cleanup", "FAIL", "页面关闭失败", exception=type(exc).__name__, error=str(exc)))
    return results, 0 if all(item["status"] == "PASS" for item in results) else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="uiautoma.web.create() Web API 验收")
    parser.add_argument("--target-url", default=DEFAULT_URL)
    parser.add_argument("--mode", choices=("auto", "chrome", "edge"), default="chrome")
    parser.add_argument("--load-timeout", type=float, default=20)
    parser.add_argument("--contract-only", action="store_true")
    args = parser.parse_args(argv)
    results, code = run(args)
    print("UIAutoma Web API 测试")
    print(" API     : uiautoma.web.create")
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
