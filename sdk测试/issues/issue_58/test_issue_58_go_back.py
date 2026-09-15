"""issue #58 复现脚本：WebBrowser.go_back() 首次调用稳定失败。

https://github.com/uiautoma/desktop/issues/58

用实测目录的 venv 运行（SDK 为 editable 安装）：

    cd D:\\code\\元素库\\sdk测试
    uv run .\\issues\\issue_58\\test_issue_58_go_back.py

脚本自己开页、自己关页；每个用例使用独立页面。
退出码：0 = 缺陷按文档稳定复现，1 = 与文档不一致（可能已修复或环境不符）。
"""

from __future__ import annotations

import argparse
import json
import time
from typing import Any

from uiautoma import web

__test__ = False

PAGE_A = "https://baobaomi900901.github.io/xpath/#/iframe-shadow-form"
PAGE_B = "https://baobaomi900901.github.io/xpath/#/element-html-test"
PAGE_C = "https://baobaomi900901.github.io/xpath/#/cookie-test"
CROSS = "https://example.com/"
PROBE = "function () { return history.length; }"
GREEN, RED, YELLOW, RESET = "\x1b[92m", "\x1b[91m", "\x1b[93m", "\x1b[0m"


def result(case_id: str, status: str, detail: str, **extra: Any) -> dict[str, Any]:
    return {"case_id": case_id, "status": status, "detail": detail, **extra}


def failure_reason(exc: BaseException) -> str:
    result_obj = getattr(exc, "result", None)
    raw = getattr(result_obj, "raw", None)
    while isinstance(raw, dict):
        if raw.get("failure_reason"):
            return str(raw["failure_reason"])
        raw = raw.get("raw")
    return ""


def history_length(page) -> Any:
    try:
        return page.execute_javascript(PROBE)
    except Exception as exc:  # noqa: BLE001
        return f"<{type(exc).__name__}>"


def navigate_all(page, targets: list[str], load_timeout: float) -> str:
    last = ""
    for target in targets:
        page.navigate(target, load_timeout=load_timeout)
        last = page.get_url()
    return last


def case_first_call(name: str, targets: list[str], expect_fail: bool, load_timeout: float) -> dict[str, Any]:
    """导航 targets 后直接 go_back；不执行任何页面级脚本命令。"""
    page = web.create(PAGE_A, mode="chrome", load_timeout=load_timeout)
    try:
        url = navigate_all(page, targets, load_timeout)
        started = time.perf_counter()
        try:
            returned = page.go_back(load_timeout=load_timeout)
            elapsed = time.perf_counter() - started
            detail = (
                f"go_back 成功且预期应失败: returned={returned!r} url={page.get_url()!r}"
                if expect_fail
                else f"go_back 成功: returned={returned!r} url={page.get_url()!r}"
            )
            return result(
                name,
                "FAIL" if expect_fail else "PASS",
                detail,
                elapsed_s=round(elapsed, 3),
                url_after=page.get_url(),
            )
        except Exception as exc:  # noqa: BLE001
            elapsed = time.perf_counter() - started
            reason = failure_reason(exc)
            reproduced = expect_fail and reason == "Cannot find a next page in history."
            return result(
                name,
                "PASS" if reproduced else "FAIL",
                (
                    f"缺陷复现: {reason!r} elapsed={elapsed:.3f}s"
                    if reproduced
                    else f"与文档不一致: {type(exc).__name__}: {exc} reason={reason!r}"
                ),
                elapsed_s=round(elapsed, 3),
                failure_reason=reason,
                trace_info=str(getattr(exc, "trace_info", "") or ""),
                url_after=page.get_url(),
                history_length=history_length(page),
            )
    finally:
        try:
            page.close(ignore_beforeunload=True)
        except Exception:  # noqa: BLE001
            pass


def case_after_page_script(load_timeout: float) -> dict[str, Any]:
    """同一序列，但在 go_back 之前先执行一次页面级脚本命令。"""
    page = web.create(PAGE_A, mode="chrome", load_timeout=load_timeout)
    try:
        navigate_all(page, [PAGE_B, PAGE_C], load_timeout)
        before = history_length(page)
        started = time.perf_counter()
        try:
            returned = page.go_back(load_timeout=load_timeout)
            return result(
                "after_page_script",
                "PASS" if returned is None else "FAIL",
                f"预热后 go_back 成功: returned={returned!r} url={page.get_url()!r}",
                elapsed_s=round(time.perf_counter() - started, 3),
                history_before_back=before,
                url_after=page.get_url(),
            )
        except Exception as exc:  # noqa: BLE001
            return result(
                "after_page_script",
                "FAIL",
                f"预热后仍失败: {type(exc).__name__}: {exc}",
                elapsed_s=round(time.perf_counter() - started, 3),
                failure_reason=failure_reason(exc),
                history_before_back=before,
            )
    finally:
        try:
            page.close(ignore_beforeunload=True)
        except Exception:  # noqa: BLE001
            pass


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="issue #58：go_back() 首次调用失败的复现脚本")
    parser.add_argument("--load-timeout", type=float, default=20)
    parser.add_argument("--json", action="store_true", help="只输出 JSON 报告")
    args = parser.parse_args(argv)

    cases = [
        case_first_call("first_call_hash_1", [PAGE_B], expect_fail=True, load_timeout=args.load_timeout),
        case_first_call("first_call_hash_2", [PAGE_B, PAGE_C], expect_fail=True, load_timeout=args.load_timeout),
        case_first_call("first_call_cross", [CROSS], expect_fail=True, load_timeout=args.load_timeout),
        case_after_page_script(args.load_timeout),
    ]

    report = {
        "issue": "https://github.com/uiautoma/desktop/issues/58",
        "api": "uiautoma.web.WebBrowser.go_back",
        "status": "PASS" if all(item["status"] == "PASS" for item in cases) else "FAIL",
        "cases": cases,
    }
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print("issue #58 · WebBrowser.go_back() 首次调用失败复现")
        print("────────────────────────────────────────────────────────────────────────")
        for index, current in enumerate(cases, 1):
            color = GREEN if current["status"] == "PASS" else RED
            label = "复现" if current["status"] == "PASS" else "不一致"
            print(f"{index:02d}/{len(cases):02d}  {color}[{label}]{RESET}  {current['case_id']:<22}  {current['detail']}")
        print("────────────────────────────────────────────────────────────────────────")
        print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
