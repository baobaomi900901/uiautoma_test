"""WebBrowser.get_url() 页面对象 API 专项验收。"""
from __future__ import annotations

import argparse
import inspect
import sys
from pathlib import Path
from urllib.parse import urlsplit

PRODUCT_ROOT = Path(__file__).resolve().parents[3]
SDK_SRC = PRODUCT_ROOT / "sdk" / "src"
if str(SDK_SRC) not in sys.path:
    sys.path.insert(0, str(SDK_SRC))

from uiautoma import web  # noqa: E402
from uiautoma.web import WebBrowser  # noqa: E402

__test__ = False
DEFAULT_URL = "https://baobaomi900901.github.io/xpath/#/iframe-shadow-form"
BAIDU_URL = "https://www.baidu.com/"
GREEN, RED, RESET = "\x1b[92m", "\x1b[91m", "\x1b[0m"


def result(case_id: str, status: str, detail: str, **extra):
    return {"case_id": case_id, "status": status, "detail": detail, **extra}


def same_url(actual: str, expected: str) -> bool:
    a, e = urlsplit(actual), urlsplit(expected)
    return (a.scheme.casefold(), a.netloc.casefold(), a.path or "/", a.query, a.fragment) == (e.scheme.casefold(), e.netloc.casefold(), e.path or "/", e.query, e.fragment)


def check_contract():
    method = getattr(WebBrowser, "get_url", None)
    sig = inspect.signature(method) if callable(method) else None
    ok = callable(method) and sig is not None and tuple(sig.parameters) == ("self",)
    return result("api_contract", "PASS" if ok else "FAIL",
                  "get_url 无公开参数，返回网页地址字符串" if ok else "get_url 签名不符合合同")


def run(args):
    results = [check_contract()]
    if results[-1]["status"] != "PASS" or args.contract_only:
        return results, 0 if results[-1]["status"] == "PASS" else 1
    page = None
    try:
        page = web.create(args.target_url, mode=args.mode, load_timeout=args.load_timeout)
        ok = isinstance(page, WebBrowser)
        results.append(result("page_prepare", "PASS" if ok else "FAIL",
                              "已创建 WebBrowser 测试页面" if ok else "create 返回类型错误"))
        if not ok:
            return results, 1
        current = page.get_url()
        results.append(result("read_target_url", "PASS" if same_url(current, args.target_url) else "FAIL",
                              "返回目标页面 URL" if same_url(current, args.target_url) else "返回 URL 与目标不一致",
                              actual_url=current))
        results.append(result("return_type", "PASS" if isinstance(current, str) else "FAIL",
                              "返回类型为 str" if isinstance(current, str) else "返回类型不是 str"))
        reads = [page.get_url() for _ in range(3)]
        results.append(result("repeat_read", "PASS" if reads[0] == reads[1] == reads[2] else "FAIL",
                              "连续读取 URL 稳定" if reads[0] == reads[1] == reads[2] else "连续读取 URL 变化"))
        page.navigate(BAIDU_URL, load_timeout=args.load_timeout)
        after = page.get_url()
        results.append(result("navigation_reflects", "PASS" if same_url(after, BAIDU_URL) else "FAIL",
                              "导航后 get_url 反映新地址" if same_url(after, BAIDU_URL) else "导航后 URL 不正确",
                              actual_url=after))
    except Exception as exc:  # noqa: BLE001
        results.append(result("scenario", "FAIL", f"get_url 场景执行失败: {type(exc).__name__}: {exc}"))
    finally:
        if page is not None:
            try:
                page.close(ignore_beforeunload=True)
                results.append(result("cleanup", "PASS", "测试页面已关闭"))
            except Exception as exc:  # noqa: BLE001
                results.append(result("cleanup", "FAIL", f"页面关闭失败: {type(exc).__name__}: {exc}"))
    return results, 0 if all(item["status"] == "PASS" for item in results) else 1


def main(argv=None):
    parser = argparse.ArgumentParser(description="WebBrowser.get_url() 页面对象 API 验收")
    parser.add_argument("--target-url", default=DEFAULT_URL)
    parser.add_argument("--mode", choices=("chrome", "edge"), default="chrome")
    parser.add_argument("--load-timeout", type=float, default=20)
    parser.add_argument("--contract-only", action="store_true")
    args = parser.parse_args(argv)
    if args.load_timeout <= 0:
        parser.error("--load-timeout 必须大于 0")
    results, code = run(args)
    print("UIAutoma Web API 测试\n API     : uiautoma.web.WebBrowser.get_url")
    print(f" 页面    : {args.target_url}")
    print("进度     状态    测试项                  测试结果")
    print("───────  ──────  ─────────────────────  ─────────────────────────────")
    for i, current in enumerate(results, 1):
        passed = current["status"] == "PASS"
        print(f"{i:02d}/{len(results):02d}    {(GREEN if passed else RED)}[{'通过' if passed else '失败'}]{RESET}  {current['case_id']:<22}  {current['detail']}")
    print("─" * 72)
    print(f"{'测试通过' if code == 0 else '测试失败'} · {sum(i['status']=='PASS' for i in results)}/{len(results)} 通过 · 退出码 {code}")
    return code


if __name__ == "__main__":
    raise SystemExit(main())
