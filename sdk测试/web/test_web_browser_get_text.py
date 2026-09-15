"""WebBrowser.get_text() 页面对象 API 专项验收。"""
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

__test__ = False
DEFAULT_URL = "https://baobaomi900901.github.io/xpath/#/element-html-test"
GREEN, RED, RESET = "\x1b[92m", "\x1b[91m", "\x1b[0m"


def result(case_id: str, status: str, detail: str, **extra):
    return {"case_id": case_id, "status": status, "detail": detail, **extra}


def check_contract():
    method = getattr(WebBrowser, "get_text", None)
    signature = inspect.signature(method) if callable(method) else None
    ok = callable(method) and signature is not None and tuple(signature.parameters) == ("self",)
    return result("api_contract", "PASS" if ok else "FAIL",
                  "get_text 无公开参数，返回整页可见文本字符串" if ok else "get_text 签名不符合合同")


def run(args):
    results = [check_contract()]
    if results[-1]["status"] != "PASS" or args.contract_only:
        return results, 0 if results[-1]["status"] == "PASS" else 1
    page = None
    try:
        page = web.create(args.target_url, mode=args.mode, load_timeout=args.load_timeout)
        if not isinstance(page, WebBrowser):
            results.append(result("page_prepare", "FAIL", "create 返回类型错误"))
            return results, 1
        results.append(result("page_prepare", "PASS", "已创建 WebBrowser 测试页面"))
        actual = page.get_text()
        oracle = page.execute_javascript("function () { return document.body.innerText; }", execution_world="MAIN")
        ok = isinstance(actual, str) and bool(actual.strip()) and actual == str(oracle or "")
        results.append(result("read_page_text", "PASS" if ok else "FAIL",
                              "返回整页文本且与独立 DOM innerText 一致" if ok else "整页文本与 DOM innerText 不一致",
                              text_length=len(actual), oracle_length=len(str(oracle or ""))))
        reads = [page.get_text() for _ in range(3)]
        results.append(result("repeat_read", "PASS" if reads[0] == reads[1] == reads[2] else "FAIL",
                              "连续读取结果稳定" if reads[0] == reads[1] == reads[2] else "连续读取结果变化"))
        page.reload(load_timeout=args.load_timeout)
        after_reload = page.get_text()
        results.append(result("reload_read", "PASS" if after_reload == actual else "FAIL",
                              "刷新后整页文本保持一致" if after_reload == actual else "刷新后整页文本变化"))
        try:
            page.get_text("extra")
        except TypeError:
            results.append(result("argument_rules", "PASS", "额外位置参数被 TypeError 拒绝"))
        else:
            results.append(result("argument_rules", "FAIL", "额外位置参数未被拒绝"))
    except Exception as exc:  # noqa: BLE001
        results.append(result("scenario", "FAIL", f"get_text 场景执行失败: {type(exc).__name__}: {exc}"))
    finally:
        if page is not None:
            try:
                page.close(ignore_beforeunload=True)
                results.append(result("cleanup", "PASS", "测试页面已关闭"))
            except Exception as exc:  # noqa: BLE001
                results.append(result("cleanup", "FAIL", f"页面关闭失败: {type(exc).__name__}: {exc}"))
    return results, 0 if all(item["status"] == "PASS" for item in results) else 1


def main(argv=None):
    parser = argparse.ArgumentParser(description="WebBrowser.get_text() 页面对象 API 验收")
    parser.add_argument("--target-url", default=DEFAULT_URL)
    parser.add_argument("--mode", choices=("chrome", "edge"), default="chrome")
    parser.add_argument("--load-timeout", type=float, default=20)
    parser.add_argument("--contract-only", action="store_true")
    args = parser.parse_args(argv)
    if args.load_timeout <= 0:
        parser.error("--load-timeout 必须大于 0")
    results, code = run(args)
    print("UIAutoma Web API 测试\n API     : uiautoma.web.WebBrowser.get_text")
    print(f" 页面    : {args.target_url}")
    print("进度     状态    测试项                  测试结果")
    print("───────  ──────  ─────────────────────  ─────────────────────────────")
    for i, item in enumerate(results, 1):
        passed = item["status"] == "PASS"
        print(f"{i:02d}/{len(results):02d}    {(GREEN if passed else RED)}[{'通过' if passed else '失败'}]{RESET}  {item['case_id']:<22}  {item['detail']}")
    print("─" * 72)
    print(f"{'测试通过' if code == 0 else '测试失败'} · {sum(i['status']=='PASS' for i in results)}/{len(results)} 通过 · 退出码 {code}")
    return code


if __name__ == "__main__":
    raise SystemExit(main())
