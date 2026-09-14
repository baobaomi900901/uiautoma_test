"""WebBrowser.id 属性专项验收脚本。"""
from __future__ import annotations

import argparse
import inspect
import os
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


def run(args: argparse.Namespace) -> tuple[list[dict[str, Any]], int]:
    results: list[dict[str, Any]] = []
    prop = getattr(WebBrowser, "id", None)
    getter = getattr(prop, "fget", None)
    signature_ok = isinstance(prop, property) and callable(getter) and tuple(inspect.signature(getter).parameters) == ("self",)
    results.append(result("api_contract", "PASS" if signature_ok else "FAIL",
                          "id 为只读 property，getter 仅接收 self" if signature_ok else "id 属性合同不符"))
    if not signature_ok or args.contract_only:
        return results, 0 if signature_ok else 1
    pages: list[WebBrowser] = []
    try:
        first = web.create(args.target_url, mode=args.mode, load_timeout=args.load_timeout)
        pages.append(first)
        ok = isinstance(first, WebBrowser)
        results.append(result("page_prepare", "PASS" if ok else "FAIL",
                              "已创建 WebBrowser 测试页面" if ok else "create 返回类型错误"))
        if not ok:
            return results, 1
        first_id = first.id
        results.append(result("id_type", "PASS" if isinstance(first_id, str) and bool(first_id) else "FAIL",
                              "id 为非空字符串" if isinstance(first_id, str) and first_id else "id 类型或内容不正确"))
        repeated = [first.id for _ in range(3)]
        results.append(result("repeat_read", "PASS" if len(set(repeated)) == 1 else "FAIL",
                              "连续读取结果稳定" if len(set(repeated)) == 1 else "连续读取结果变化"))
        first.reload(load_timeout=args.load_timeout)
        results.append(result("reload_stability", "PASS" if first.id == first_id else "FAIL",
                              "刷新后 id 保持不变" if first.id == first_id else "刷新后 id 发生变化"))
        second = web.create(args.target_url, mode=args.mode, load_timeout=args.load_timeout)
        pages.append(second)
        distinct = isinstance(second, WebBrowser) and second.id != first_id
        results.append(result("distinct_page", "PASS" if distinct else "FAIL",
                              "两个独立页面 id 不同" if distinct else "独立页面 id 未区分"))
        try:
            first.id = "changed"
        except AttributeError:
            results.append(result("read_only", "PASS", "id 不支持写入"))
        else:
            results.append(result("read_only", "FAIL", "id 意外支持写入"))
    except Exception as exc:  # noqa: BLE001
        results.append(result("scenario", "FAIL", f"id 场景执行失败: {type(exc).__name__}: {exc}"))
    finally:
        cleanup_ok = True
        for page in pages:
            try:
                page.close(ignore_beforeunload=True)
            except Exception:
                cleanup_ok = False
        results.append(result("cleanup", "PASS" if cleanup_ok else "FAIL",
                              "测试页面已关闭" if cleanup_ok else "页面关闭失败"))
    return results, 0 if all(item["status"] == "PASS" for item in results) else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="WebBrowser.id 属性验收")
    parser.add_argument("--target-url", default=DEFAULT_URL)
    parser.add_argument("--mode", choices=("chrome", "edge"), default="chrome")
    parser.add_argument("--load-timeout", type=float, default=20)
    parser.add_argument("--contract-only", action="store_true")
    args = parser.parse_args(argv)
    if args.load_timeout <= 0:
        parser.error("--load-timeout 必须大于 0")
    results, code = run(args)
    print("UIAutoma Web API 测试\n API     : uiautoma.web.WebBrowser.id")
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
