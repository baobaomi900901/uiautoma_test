"""WebBrowser.get_title() 页面对象 API 专项验收。"""
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
DEFAULT_URL = "https://baobaomi900901.github.io/xpath/#/iframe-shadow-form"
BAIDU_URL = "https://www.baidu.com/"
GREEN, RED, RESET = "\x1b[92m", "\x1b[91m", "\x1b[0m"


def result(case_id: str, status: str, detail: str, **extra):
    return {"case_id": case_id, "status": status, "detail": detail, **extra}


def check_contract():
    method = getattr(WebBrowser, "get_title", None)
    signature = inspect.signature(method) if callable(method) else None
    ok = callable(method) and signature is not None and tuple(signature.parameters) == ("self",)
    return result("api_contract", "PASS" if ok else "FAIL",
                  "get_title 无公开参数，返回网页标题字符串" if ok else "get_title 签名不符合合同")


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
        title = page.get_title()
        results.append(result("read_target_title", "PASS" if isinstance(title, str) and bool(title.strip()) else "FAIL",
                              "返回非空页面标题" if isinstance(title, str) and title.strip() else "页面标题为空或类型错误",
                              title=title))
        results.append(result("return_type", "PASS" if isinstance(title, str) else "FAIL",
                              "返回类型为 str" if isinstance(title, str) else "返回类型不是 str"))
        reads = [page.get_title() for _ in range(3)]
        results.append(result("repeat_read", "PASS" if reads[0] == reads[1] == reads[2] else "FAIL",
                              "连续读取标题稳定" if reads[0] == reads[1] == reads[2] else "连续读取标题变化"))
        page.navigate(BAIDU_URL, load_timeout=args.load_timeout)
        after = page.get_title()
        changed = isinstance(after, str) and bool(after.strip()) and after != title
        results.append(result("navigation_reflects", "PASS" if changed else "FAIL",
                              "导航后 get_title 反映新页面标题" if changed else "导航后标题未正确更新",
                              title_before=title, title_after=after))
    except Exception as exc:  # noqa: BLE001
        results.append(result("scenario", "FAIL", f"get_title 场景执行失败: {type(exc).__name__}: {exc}"))
    finally:
        if page is not None:
            try:
                page.close(ignore_beforeunload=True)
                results.append(result("cleanup", "PASS", "测试页面已关闭"))
            except Exception as exc:  # noqa: BLE001
                results.append(result("cleanup", "FAIL", f"页面关闭失败: {type(exc).__name__}: {exc}"))
    return results, 0 if all(item["status"] == "PASS" for item in results) else 1


def main(argv=None):
    parser = argparse.ArgumentParser(description="WebBrowser.get_title() 页面对象 API 验收")
    parser.add_argument("--target-url", default=DEFAULT_URL)
    parser.add_argument("--mode", choices=("chrome", "edge"), default="chrome")
    parser.add_argument("--load-timeout", type=float, default=20)
    parser.add_argument("--contract-only", action="store_true")
    args = parser.parse_args(argv)
    if args.load_timeout <= 0:
        parser.error("--load-timeout 必须大于 0")
    results, code = run(args)
    print("UIAutoma Web API 测试\n API     : uiautoma.web.WebBrowser.get_title")
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
