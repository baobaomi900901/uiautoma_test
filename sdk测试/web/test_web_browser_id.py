"""WebBrowser.id 成员收敛验收脚本（原名：id 属性专项验收）。

基线变更：`44c8e91f 🦄 refactor: 收敛 SDK 独有公开接口与内部状态` 移除了 `WebBrowser.id`。
本脚本因此从「id 属性专项验收」改写为「成员已移除 + 公开替代方式可用性」契约：

- 契约面：类上不再存在 `id` 成员；dataclass 公开字段仍为 `url` / `title` / `mode`。
- 行为面：改用 `(url, title)` 组合键（`_web_page_identity.page_key`）识别页面，
  并**如实记录**由此产生的能力缺口——两个同 URL、同标题的标签在公开面上无法区分。
"""
from __future__ import annotations

import argparse
import dataclasses
import time
from typing import Any

from uiautoma import web
from uiautoma.web import WebBrowser

from _web_page_identity import count_key, leaked, page_key

__test__ = False
DEFAULT_URL = "https://baobaomi900901.github.io/xpath/#/iframe-shadow-form"
GREEN, RED, RESET = "\x1b[92m", "\x1b[91m", "\x1b[0m"


def result(case_id: str, status: str, detail: str, **extra: Any) -> dict[str, Any]:
    return {"case_id": case_id, "status": status, "detail": detail, **extra}


def check_contract() -> dict[str, Any]:
    """契约面：类上不存在 id 成员，公开身份字段仍齐备。"""
    has_id = hasattr(WebBrowser, "id")
    fields = {item.name for item in dataclasses.fields(WebBrowser)}
    public_ok = {"url", "title", "mode"} <= fields
    id_field = "id" in fields
    ok = not has_id and not id_field and public_ok
    return result(
        "api_contract",
        "PASS" if ok else "FAIL",
        (
            "WebBrowser 上已无 id 成员，公开身份字段 url/title/mode 齐备"
            if ok
            else f"成员收敛结果不符: hasattr(id)={has_id}, dataclass 字段含 id={id_field}, "
                 f"公开字段齐备={public_ok}"
        ),
        has_id_attribute=has_id,
        dataclass_fields=sorted(fields),
    )


def run(args: argparse.Namespace) -> tuple[list[dict[str, Any]], int]:
    results = [check_contract()]
    if results[-1]["status"] != "PASS" or args.contract_only:
        return results, 0 if results[-1]["status"] == "PASS" else 1

    pages: list[WebBrowser] = []
    page_id = ""
    baseline_matches = 0
    try:
        page = web.create(args.target_url, mode=args.mode, load_timeout=args.load_timeout)
        pages.append(page)
        ok = isinstance(page, WebBrowser)
        results.append(result(
            "page_prepare", "PASS" if ok else "FAIL",
            "已创建 WebBrowser 测试页面" if ok else "create 返回类型错误"))
        if not ok:
            return results, 1

        page_id = page_key(page)
        baseline_matches = count_key(page_id, args.mode)
        key_ok = bool(page.get_url()) and "|" in page_id
        results.append(result(
            "identity_via_public_surface", "PASS" if key_ok else "FAIL",
            f"组合键可构成且非空: {page_id!r}" if key_ok else f"组合键构造失败: {page_id!r}",
            page_key=page_id))

        repeated = [page_key(page) for _ in range(3)]
        results.append(result(
            "repeat_read", "PASS" if len(set(repeated)) == 1 else "FAIL",
            "连续三次读取组合键稳定" if len(set(repeated)) == 1 else f"连续读取结果变化: {repeated!r}"))

        text_form = str(page)
        text_ok = "url=" in text_form and "title=" in text_form
        results.append(result(
            "str_form_readable", "PASS" if text_ok else "FAIL",
            "str(page) 可读且包含 url/title" if text_ok else f"str(page) 结构不符: {text_form!r}",
            str_form=text_form))

        page.reload(load_timeout=args.load_timeout)
        after_reload = page_key(page)
        results.append(result(
            "reload_key_stable", "PASS" if after_reload == page_id else "FAIL",
            "刷新后组合键保持不变" if after_reload == page_id else f"刷新后组合键变化: {after_reload!r}",
            page_key_after_reload=after_reload))

        second = web.create(args.target_url, mode=args.mode, load_timeout=args.load_timeout)
        pages.append(second)
        second_ok = isinstance(second, WebBrowser)
        if not second_ok:
            results.append(result("second_page_prepare", "FAIL", "第二个 create 返回类型错误"))
        else:
            second_key = page_key(second)
            matches = count_key(page_id, args.mode)
            gap_ok = second_key == page_id and matches >= 2
            results.append(result(
                "same_url_tabs_not_distinguishable", "PASS" if gap_ok else "FAIL",
                (
                    f"两个同 URL 标签的组合键相同（当前 {matches} 个），"
                    "公开面上无法区分它们是不同标签——移除 id 后的能力缺口，已在证据文档记录"
                    if gap_ok
                    else f"预期两个同 URL 标签同键且计数 >=2，实际 key={second_key!r}, matches={matches}"
                ),
                page_key=page_id, matches=matches))
    except Exception as exc:  # noqa: BLE001
        results.append(result("scenario", "FAIL", f"id 收敛场景执行失败: {type(exc).__name__}: {exc}"))
    finally:
        close_error = ""
        for page in pages:
            try:
                page.close(ignore_beforeunload=True)
            except Exception as exc:  # noqa: BLE001
                close_error = close_error or f"{type(exc).__name__}: {exc}"
        time.sleep(0.5)
        leftover: list = []
        try:
            leftover = leaked(page_id, baseline_matches, args.mode) if page_id else []
        except Exception as exc:  # noqa: BLE001
            close_error = close_error or f"get_all 复核失败: {type(exc).__name__}: {exc}"
        cleaned = not close_error and not leftover
        results.append(result(
            "cleanup", "PASS" if cleaned else "FAIL",
            "已关闭全部测试页面且无残留标签" if cleaned else
            f"收尾异常: {close_error or f'残留标签 {len(leftover)} 个'}",
            leftover_tabs=len(leftover)))
    return results, 0 if all(item["status"] == "PASS" for item in results) else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="WebBrowser.id 成员收敛验收")
    parser.add_argument("--target-url", default=DEFAULT_URL)
    parser.add_argument("--mode", choices=("chrome", "edge"), default="chrome")
    parser.add_argument("--load-timeout", type=float, default=20)
    parser.add_argument("--contract-only", action="store_true")
    args = parser.parse_args(argv)
    if args.load_timeout <= 0:
        parser.error("--load-timeout 必须大于 0")
    results, code = run(args)
    print("UIAutoma Web API 测试\n API     : uiautoma.web.WebBrowser.id（main 已移除，验证收敛与替代方式）")
    print(f" 页面    : {args.target_url}")
    print("进度     状态    测试项                  测试结果")
    print("───────  ──────  ─────────────────────  ─────────────────────────────")
    for index, item in enumerate(results, 1):
        passed = item["status"] == "PASS"
        print(f"{index:02d}/{len(results):02d}    {(GREEN if passed else RED)}[{'通过' if passed else '失败'}]{RESET}  {item['case_id']:<34}  {item['detail']}")
    print("─" * 72)
    print(f"{'测试通过' if code == 0 else '测试失败'} · {sum(i['status']=='PASS' for i in results)}/{len(results)} 通过 · 退出码 {code}")
    return code


if __name__ == "__main__":
    raise SystemExit(main())
