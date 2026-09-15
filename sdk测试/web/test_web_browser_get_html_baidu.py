"""WebBrowser.get_html() 百度页面专项验收。"""
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
BAIDU_URL = "https://www.baidu.com/"
GREEN, RED, RESET = "\x1b[92m", "\x1b[91m", "\x1b[0m"


def result(case_id: str, status: str, detail: str, **extra):
    return {"case_id": case_id, "status": status, "detail": detail, **extra}


def check_contract():
    method = getattr(WebBrowser, "get_html", None)
    signature = inspect.signature(method) if callable(method) else None
    ok = callable(method) and signature is not None and tuple(signature.parameters) == ("self",)
    return result("api_contract", "PASS" if ok else "FAIL",
                  "get_html 无公开参数，返回网页 HTML 字符串" if ok else "get_html 签名不符合合同")


def run(args):
    results = [check_contract()]
    if results[-1]["status"] != "PASS" or args.contract_only:
        return results, 0 if results[-1]["status"] == "PASS" else 1
    page: WebBrowser | None = None
    active: WebBrowser | None = None
    try:
        page = web.create(BAIDU_URL, mode=args.mode, load_timeout=args.load_timeout)
        if not isinstance(page, WebBrowser):
            results.append(result("page_prepare", "FAIL", "create 返回类型错误"))
            return results, 1
        results.append(result("page_prepare", "PASS", "已打开百度测试页面"))
        page.activate()
        active = web.get_active(mode=args.mode, load_timeout=0)
        same = isinstance(active, WebBrowser) and active.id == page.id
        results.append(result("get_active_page", "PASS" if same else "FAIL",
                              "已获取当前百度网页对象" if same else "当前网页对象与创建页面不一致"))
        if not same:
            return results, 1
        html = active.get_html()
        valid = isinstance(html, str) and bool(html.strip()) and "<html" in html.casefold()
        results.append(result("read_html", "PASS" if valid else "FAIL",
                              "返回非空 HTML 且包含 html 根元素" if valid else "HTML 类型或内容不符合预期",
                              html_length=len(html)))
        oracle = active.execute_javascript("function () { return document.documentElement.outerHTML; }", execution_world="MAIN")
        results.append(result("dom_html_compare", "PASS" if html == str(oracle or "") else "FAIL",
                              "get_html 与独立 DOM outerHTML 一致" if html == str(oracle or "") else "get_html 与 DOM outerHTML 不一致",
                              oracle_length=len(str(oracle or ""))))
        reads = [active.get_html() for _ in range(3)]
        valid_reads = all(isinstance(value, str) and "<html" in value.casefold() for value in reads)
        changed = len(set(reads)) > 1
        results.append(result("repeat_read", "PASS" if valid_reads else "FAIL",
                              "连续读取均返回有效 HTML（页面动态内容允许变化）" if valid_reads else "重复读取出现无效 HTML",
                              content_changed=changed, lengths=[len(value) for value in reads]))
        try:
            active.get_html("extra")
        except TypeError:
            results.append(result("argument_rules", "PASS", "额外位置参数被 TypeError 拒绝"))
        else:
            results.append(result("argument_rules", "FAIL", "额外位置参数未被拒绝"))
    except Exception as exc:  # noqa: BLE001
        results.append(result("scenario", "FAIL", f"get_html 场景执行失败: {type(exc).__name__}: {exc}",
                              trace_info=str(getattr(exc, "trace_info", "") or ""),
                              trace_id=str(getattr(exc, "trace_id", "") or "")))
    finally:
        if page is not None:
            try:
                page.close(ignore_beforeunload=True)
                results.append(result("cleanup", "PASS", "百度测试页面已关闭"))
            except Exception as exc:  # noqa: BLE001
                results.append(result("cleanup", "FAIL", f"页面关闭失败: {type(exc).__name__}: {exc}"))
    return results, 0 if all(item["status"] == "PASS" for item in results) else 1


def main(argv=None):
    parser = argparse.ArgumentParser(description="WebBrowser.get_html() 百度页面验收")
    parser.add_argument("--mode", choices=("chrome", "edge"), default="chrome")
    parser.add_argument("--load-timeout", type=float, default=20)
    parser.add_argument("--contract-only", action="store_true")
    args = parser.parse_args(argv)
    if args.load_timeout <= 0:
        parser.error("--load-timeout 必须大于 0")
    results, code = run(args)
    print("UIAutoma Web API 测试\n API     : uiautoma.web.WebBrowser.get_html")
    print(f" 页面    : {BAIDU_URL}")
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
