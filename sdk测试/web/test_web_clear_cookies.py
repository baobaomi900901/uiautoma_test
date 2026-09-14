"""clear_cookies 专项：仅清理随机测试域名；导入或 --contract-only 不操作浏览器。"""
from __future__ import annotations

import argparse
import inspect
import os
import time
import unicodedata
import uuid
from urllib.parse import urlsplit

import uiautoma
from uiautoma import web
from uiautoma.web import WebBrowser

__test__ = False
DEFAULT_URL = "https://baobaomi900901.github.io/xpath/#/cookie-test"


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def check_contract():
    sig = inspect.signature(web.clear_cookies)
    expected = ("url", "mode", "domain", "partition_key")
    require(tuple(sig.parameters) == expected, f"签名不符，实际: {sig}")
    for name, default in zip(expected, ("", "auto", None, None)):
        param = sig.parameters[name]
        kind = inspect.Parameter.KEYWORD_ONLY if name in expected[2:] else inspect.Parameter.POSITIONAL_OR_KEYWORD
        require(param.kind == kind and param.default == default, f"{name} 合同不符: {sig}")
    require(sig.return_annotation in (None, "None", type(None)), f"返回注解不符: {sig}")
    return "url/mode 可位置传参，domain/partition_key 仅限关键字；返回 None"


def make_fixtures():
    token = uuid.uuid4().hex
    host, guard = f"uiautoma-clear-{token}.test", f"uiautoma-keep-{token}.test"
    urls = (f"https://{host}/", f"https://{host}/", f"https://{host}/keep/",
            f"https://child.{host}/", f"https://{guard}/")
    return [{"url": url, "name": f"uiautoma_clear_{i}", "value": f"value-{i}",
             "path": urlsplit(url).path} for i, url in enumerate(urls)]


def verify_state(fixtures, alive, mode):
    for i, item in enumerate(fixtures):
        cookie = web.get_cookie(item["url"], mode, name=item["name"])
        if i in alive:
            require(isinstance(cookie, dict) and cookie.get("name") == item["name"]
                    and cookie.get("value") == item["value"] and cookie.get("path") == item["path"]
                    and cookie.get("domain", "").lstrip(".") == urlsplit(item["url"]).hostname,
                    f"应保留的测试 Cookie 不符: {item['name']}（不输出其他 Cookie 内容）")
        else:
            require(cookie == {}, f"应删除的测试 Cookie 仍存在: {item['name']}")


def clear_and_check(fixtures, alive, mode, **filters):
    require(bool(filters.get("url") or filters.get("domain")), "安全保护：拒绝无筛选清理")
    returned = web.clear_cookies(mode=mode, **filters)
    require(returned is None, f"返回类型应为 None，实际: {type(returned).__name__}")
    verify_state(fixtures, alive, mode)
    return f"返回 None；目标已删除；{len(alive)} 个应保留的测试 Cookie 正确"


def check_parameters(url, mode):
    cases = ((TypeError, lambda: web.clear_cookies(url, mode, "domain")),
             (TypeError, lambda: web.clear_cookies(url, mode, timeout=0)),
             (TypeError, lambda: web.clear_cookies(url, mode, partition_key=[])),
             (ValueError, lambda: web.clear_cookies(url, mode, partition_key={})),
             (TypeError, lambda: web.clear_cookies(url, mode, partition_key={
                 "top_level_site": url, "has_cross_site_ancestor": "false"})))
    for expected, call in cases:
        try:
            call()
        except expected:
            continue
        raise AssertionError(f"预期 {expected.__name__}，实际未抛出异常")
    return "位置/未知参数、非法分区类型/缺少站点/祖先类型均按预期拒绝"


def cleanup(owned, page, mode):
    errors = []
    for item in owned:
        try:
            web.remove_cookie(item["url"], item["name"], mode)
            require(web.get_cookie(item["url"], mode, name=item["name"]) == {}, "删除后仍存在")
        except Exception as exc:
            errors.append(f"{item['name']}: {type(exc).__name__}: {exc}")
    if page is not None:
        try:
            page.close(ignore_beforeunload=True)
        except Exception as exc:
            errors.append(f"页面: {type(exc).__name__}: {exc}")
    require(not errors, "；".join(errors))
    return "逐个删除本次 Cookie 并读回核验；本次页面已关闭（如已创建）"


def run_case(results, name, call):
    started = time.perf_counter()
    try:
        detail, status = call(), "PASS"
    except Exception as exc:
        detail, status = f"{type(exc).__name__}: {exc}", "FAIL"
    results.append((name, status, detail, (time.perf_counter() - started) * 1000))
    return status == "PASS"


def run(args):
    results, owned, page = [], [], None
    if not run_case(results, "API 合同", check_contract) or args.contract_only:
        return results
    fixtures = make_fixtures()
    host = urlsplit(fixtures[0]["url"]).hostname
    guard = urlsplit(fixtures[4]["url"]).hostname
    print(f" 测试域名: {host}；对照域名: {guard}", flush=True)
    try:
        def prepare_page():
            nonlocal page
            page = web.create(args.target_url, mode=args.mode, load_timeout=20)
            require(isinstance(page, WebBrowser), "页面返回类型不是 WebBrowser")
            return "已打开 Cookie 靶场；本次不依赖元素库或网页表单控件"

        def prepare_cookies():
            for domain in (host, guard):
                require(web.get_cookies("", args.mode, domain=domain) == [], "测试域名非空，停止写入")
            for i, item in enumerate(fixtures):
                owned.append(item)  # 先登记，以便写入中途失败也能尝试清理。
                web.set_cookie(item["url"], args.mode, name=item["name"], value=item["value"],
                               path=item["path"], sessionCookie=i != 1, expires=600,
                               secure=True, httpOnly=i == 1)
            verify_state(fixtures, set(range(5)), args.mode)
            return "5 个独立 Cookie 已读回：根路径两项、其他路径、子域名、对照域名"

        if not run_case(results, "页面准备", prepare_page):
            return results
        if not run_case(results, "Cookie 准备", prepare_cookies):
            return results
        steps = (("按 URL 批量清理", {2, 3, 4}, {"url": fixtures[0]["url"]}),
                 ("重复清理空结果", {2, 3, 4}, {"url": fixtures[0]["url"]}),
                 ("URL 与域名不相交", {2, 3, 4}, {"url": fixtures[0]["url"], "domain": guard}),
                 ("域名及子域清理", {4}, {"domain": host}),
                 ("显式非分区清理", set(), {"url": fixtures[4]["url"], "partition_key": None}))
        for label, alive, filters in steps:
            if not run_case(results, label, lambda: clear_and_check(fixtures, alive, args.mode, **filters)):
                return results
        run_case(results, "参数边界", lambda: check_parameters(fixtures[0]["url"], args.mode))
    finally:
        run_case(results, "资源清理", lambda: cleanup(owned, page, args.mode))
    return results


def pad(text, width):
    size = sum(2 if unicodedata.east_asian_width(c) in "WF" else 1 for c in text)
    return text + " " * max(0, width - size)


def main(argv=None):
    parser = argparse.ArgumentParser(description="clear_cookies 专项，仅清理随机测试域名")
    parser.add_argument("--target-url", default=DEFAULT_URL, help="只用于打开靶场，不作为批量清理范围")
    parser.add_argument("--mode", choices=("chrome", "edge"), default="chrome")
    parser.add_argument("--contract-only", action="store_true", help="仅签名检查，不操作浏览器或 Cookie")
    args = parser.parse_args(argv)
    print("UIAutoma Web API 测试\n API     : uiautoma.web.clear_cookies")
    print(f" 页面    : {args.target_url}\n SDK     : {uiautoma.__file__}")
    print(" 范围    : 仅本次随机 .test 域名；不执行无筛选清理", flush=True)
    started = time.perf_counter()
    results = run(args)
    print("进度     状态    测试项                测试结果 / 耗时\n" + "─" * 110)
    for i, (name, status, detail, elapsed) in enumerate(results, 1):
        label = "[通过]" if status == "PASS" else "[失败]"
        if "NO_COLOR" not in os.environ:
            label = ("\x1b[32m" if status == "PASS" else "\x1b[31m") + label + "\x1b[0m"
        print(f"{i:02d}/{len(results):02d}    {label}  {pad(name, 20)}  {detail}  {elapsed:.1f}ms")
    passed = sum(item[1] == "PASS" for item in results)
    code = 0 if passed == len(results) else 1
    print("─" * 110)
    lifecycle = "VERIFIED" if code == 0 else "READY_FOR_LIVE"
    print(f"{'本轮检查通过' if code == 0 else '测试失败'} · {lifecycle} · {passed}/{len(results)} 通过 · "
          f"{(time.perf_counter() - started) * 1000:.1f}ms · 退出码 {code}")
    return code


if __name__ == "__main__":
    raise SystemExit(main())
