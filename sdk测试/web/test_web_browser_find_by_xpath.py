"""WebBrowser.find_by_xpath() 页面对象 API 专项验收。

靶场：**本地静态 fixture**（`http://127.0.0.1:18642/index.html`），脚本按需自起自停；
理由与取舍见 `find_by_css.md`。`--target-url` 可换成公开靶场等任意页面。

本次实测的 XPath 特有行为：
- 属性谓词与索引谓词均可用（`//input[@type="password"]`、`//ul[@id="list"]/li[2]`）；
- 多命中抛 `AmbiguousElementError`；未命中等满 timeout 后抛 `ElementNotFoundError`；
- **语法非法**（如 `//[`、`///`）抛的是 `RpcProtocolError`（"Web 元素操作失败，请重试"），
  与「语法合法但匹配不到」的 `ElementNotFoundError` 不同，且**立即返回**。

退出码：0 = 全部 PASS；1 = 存在 FAIL；2 = 无非 FAIL 但存在 BLOCKED。
"""
from __future__ import annotations

import argparse
from contextlib import contextmanager
import inspect
import json
import shutil
import subprocess
import sys
import tempfile
import time
import uuid
from pathlib import Path
from urllib.parse import urlsplit
from urllib.request import urlopen

import uiautoma
from uiautoma import (
    AmbiguousElementError,
    ElementNotFoundError,
    InvalidParamsError,
    NoCurrentPackageError,
    RpcProtocolError,
    web,
)
from uiautoma.web import WebBrowser

__test__ = False

FIXTURE_PORT = 18642
FIXTURE_URL = f"http://127.0.0.1:{FIXTURE_PORT}/index.html"
FIXTURE_HTML = """<!DOCTYPE html>
<html lang="zh"><head><meta charset="utf-8"><title>UIAutoma 本地选择器靶场</title></head>
<body>
  <div id="unique-target">唯一目标</div>
  <div id="wrapper">
    <input class="field" type="text" value="first">
    <input class="field" type="text" value="second">
    <input class="field" type="password" value="secret">
    <input id="solo" type="email" value="solo@example.com">
  </div>
  <ul id="list"><li class="item">alpha</li><li class="item">beta</li><li class="item">gamma</li></ul>
  <button id="submit-button" type="button">提交</button>
</body></html>
"""
DEFAULT_LIBRARY = Path(r"D:\code\元素库\260902_web元素")
LIB_TMP_ROOT = Path(__file__).resolve().parents[1] / ".pytest_tmp"
UNIQUE_XPATH = '//*[@id="unique-target"]'
ATTR_XPATH = '//input[@type="password"]'
INDEX_XPATH = '//ul[@id="list"]/li[2]'
MULTI_XPATH = "//input"
ABSENT_XPATH = '//*[@id="uiautoma-absent"]'
MALFORMED_XPATH = "//["
GREEN, RED, YELLOW, RESET = "\x1b[92m", "\x1b[91m", "\x1b[93m", "\x1b[0m"


def result(case_id: str, status: str, detail: str, **extra):
    return {"case_id": case_id, "status": status, "detail": detail, **extra}


def same_url(actual: str, expected: str) -> bool:
    a, e = urlsplit(str(actual)), urlsplit(str(expected))
    return (
        a.scheme.casefold(), a.netloc.casefold(), a.path or "/", a.query, a.fragment
    ) == (
        e.scheme.casefold(), e.netloc.casefold(), e.path or "/", e.query, e.fragment
    )


def check_contract():
    method = getattr(WebBrowser, "find_by_xpath", None)
    sig = inspect.signature(method) if callable(method) else None
    if sig is None:
        return result("api_contract", "FAIL", "WebBrowser.find_by_xpath 不存在")
    parameters = list(sig.parameters.values())
    names = tuple(sig.parameters)
    ok = (
        names == ("self", "xpath_selector", "timeout")
        and parameters[1].kind is inspect.Parameter.POSITIONAL_OR_KEYWORD
        and parameters[1].default is inspect.Parameter.empty
        and parameters[2].kind is inspect.Parameter.KEYWORD_ONLY
        and parameters[2].default == 20
        and str(sig.return_annotation) == "WebElement"
    )
    detail = (
        "xpath_selector 必填，timeout 仅限关键字且默认 20，返回注解 WebElement"
        if ok else f"公开签名不符合合同: {sig}"
    )
    return result("api_contract", "PASS" if ok else "FAIL", detail)


def exception_name(exc: BaseException) -> str:
    return type(exc).__name__


def error_detail(prefix: str, exc: BaseException) -> str:
    trace_info = str(getattr(exc, "trace_info", "") or "")
    return f"{prefix}: {exception_name(exc)}: {exc}" + (f" [trace={trace_info}]" if trace_info else "")


def expect_raises(call, expected_type, label: str, message_contains: str = "",
                  min_elapsed: float | None = None, max_elapsed: float | None = None):
    started = time.perf_counter()
    try:
        call()
    except expected_type as exc:
        elapsed = round(time.perf_counter() - started, 3)
        text = str(exc)
        if message_contains and message_contains not in text:
            return result(label, "FAIL", f"{exception_name(exc)} 消息不含 {message_contains!r}：{text}", elapsed_s=elapsed)
        if min_elapsed is not None and elapsed < min_elapsed:
            return result(label, "FAIL", f"耗时过短：{elapsed}s < {min_elapsed}s", elapsed_s=elapsed)
        if max_elapsed is not None and elapsed > max_elapsed:
            return result(label, "FAIL", f"耗时过长：{elapsed}s > {max_elapsed}s", elapsed_s=elapsed)
        return result(label, "PASS", f"{exception_name(exc)} 正确拒绝（{elapsed}s）：{text}", elapsed_s=elapsed)
    except Exception as exc:  # noqa: BLE001
        return result(label, "FAIL", f"拒绝类型错误，应为 {expected_type.__name__}: {exception_name(exc)}: {exc}")
    return result(label, "FAIL", "调用未被拒绝")


def unique_case(page: WebBrowser, case_id: str, label: str, xpath: str, expected_name: str, timeout: float):
    try:
        element = page.find_by_xpath(xpath, timeout=timeout)
    except Exception as exc:  # noqa: BLE001
        return result(case_id, "FAIL", error_detail(f"{label} 调用失败", exc))
    ok = str(element.name or "") == expected_name and str(element.id or "").startswith("rt:web:")
    return result(
        case_id, "PASS" if ok else "FAIL",
        f"{xpath} 唯一命中（name={element.name!r}）" if ok else
        f"结果不符: name={element.name!r}, id={element.id!r}",
        element_name=str(element.name or ""),
    )


def reachable(url: str, timeout: float = 2.0) -> bool:
    try:
        with urlopen(url, timeout=timeout) as response:
            return 200 <= int(getattr(response, "status", 200)) < 400
    except Exception:  # noqa: BLE001
        return False


@contextmanager
def local_fixture(port: int, html: str):
    url = f"http://127.0.0.1:{port}/index.html"
    if reachable(url):
        yield url, None
        return
    tmp = Path(tempfile.mkdtemp(prefix="uiautoma_fixture_"))
    (tmp / "index.html").write_text(html, encoding="utf-8")
    proc = subprocess.Popen(
        [sys.executable, "-m", "http.server", str(port), "--bind", "127.0.0.1", "--directory", str(tmp)],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    try:
        deadline = time.monotonic() + 10
        while time.monotonic() < deadline and not reachable(url):
            time.sleep(0.2)
        yield url, proc
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except Exception:  # noqa: BLE001
            proc.kill()
        shutil.rmtree(tmp, ignore_errors=True)


def run(args):
    results = [check_contract()]
    if results[-1]["status"] != "PASS" or args.contract_only:
        return results, 0 if results[-1]["status"] == "PASS" else 1

    run_id = uuid.uuid4().hex
    copy_dir = LIB_TMP_ROOT / run_id
    package = None
    page = None
    managed = args.target_url.startswith(f"http://127.0.0.1:{FIXTURE_PORT}/")
    fixture = local_fixture(FIXTURE_PORT, FIXTURE_HTML) if managed else None
    try:
        target_url = fixture.__enter__()[0] if fixture is not None else args.target_url

        try:
            if not args.library.is_dir():
                results.append(result("library_prepare", "BLOCKED", f"元素库不存在: {args.library}"))
                return results, 2
            shutil.copytree(args.library, copy_dir)
            package = uiautoma.open(str(copy_dir), timeout=20, connect_timeout=20)
            results.append(result(
                "library_prepare", "PASS",
                f"已打开元素库副本：web 元素 {package.web_count} 个", web_count=package.web_count))
        except Exception as exc:  # noqa: BLE001
            results.append(result("library_prepare", "BLOCKED", error_detail("无法准备元素库", exc)))
            return results, 2

        try:
            page = web.create(target_url, mode=args.mode, load_timeout=args.load_timeout)
            current = page.get_url()
            ok = isinstance(page, WebBrowser) and same_url(current, target_url)
            results.append(result(
                "page_prepare", "PASS" if ok else "FAIL",
                "已打开靶场页" if ok else f"URL 不符: {current!r}", url=current))
            if not ok:
                return results, 1
        except Exception as exc:  # noqa: BLE001
            results.append(result("page_prepare", "BLOCKED", error_detail("无法打开靶场页", exc)))
            return results, 2

        # 目标用例 1-3：三种唯一表达式
        results.append(unique_case(page, "unique_by_id", "按 id 谓词", UNIQUE_XPATH, "唯一目标", args.timeout))
        results.append(unique_case(page, "unique_by_attribute", "按属性谓词", ATTR_XPATH, "secret", args.timeout))
        results.append(unique_case(page, "unique_by_index", "按索引谓词", INDEX_XPATH, "beta", args.timeout))

        # 目标用例 4：多命中 → 歧义拒绝
        results.append(expect_raises(
            lambda: page.find_by_xpath(MULTI_XPATH, timeout=args.timeout),
            AmbiguousElementError, "ambiguous_match_rejected", message_contains="不唯一"))

        # 目标用例 5-6：未命中的两种超时行为
        results.append(expect_raises(
            lambda: page.find_by_xpath(ABSENT_XPATH, timeout=3),
            ElementNotFoundError, "not_found_waits_timeout", min_elapsed=2.5))
        results.append(expect_raises(
            lambda: page.find_by_xpath(ABSENT_XPATH, timeout=0),
            ElementNotFoundError, "not_found_timeout_zero_fast", max_elapsed=1.0))

        # 目标用例 7：timeout=0 且存在
        results.append(unique_case(page, "timeout_zero_present", "timeout=0", UNIQUE_XPATH, "唯一目标", 0))

        # 目标用例 8：语法非法 → RpcProtocolError，且页面仍可用
        results.append(expect_raises(
            lambda: page.find_by_xpath(MALFORMED_XPATH, timeout=3),
            RpcProtocolError, "malformed_syntax_rejected", max_elapsed=1.0))
        try:
            alive = page.get_title()
            results.append(result(
                "page_usable_after_malformed", "PASS" if alive else "FAIL",
                f"语法非法后页面仍可用（title={alive!r}）" if alive else "页面不可用"))
        except Exception as exc:  # noqa: BLE001
            results.append(result("page_usable_after_malformed", "FAIL", error_detail("页面不可用", exc)))

        # 参数校验
        results.append(expect_raises(lambda: page.find_by_xpath(""), InvalidParamsError, "empty_selector"))
        results.append(expect_raises(lambda: page.find_by_xpath("   "), InvalidParamsError, "blank_selector"))
        results.append(expect_raises(lambda: page.find_by_xpath(None), InvalidParamsError, "non_str_selector"))
        results.append(expect_raises(
            lambda: page.find_by_xpath(UNIQUE_XPATH, timeout=-2), InvalidParamsError, "invalid_timeout"))
        results.append(expect_raises(
            lambda: page.find_by_xpath(UNIQUE_XPATH, timeout="bad"), InvalidParamsError, "invalid_timeout_type"))
        results.append(expect_raises(lambda: page.find_by_xpath(), TypeError, "missing_selector"))
        results.append(expect_raises(lambda: page.find_by_xpath(UNIQUE_XPATH, 1), TypeError, "positional_timeout"))

        # 未打开 Package
        try:
            package.close()
        except Exception:  # noqa: BLE001
            pass
        results.append(expect_raises(
            lambda: page.find_by_xpath(UNIQUE_XPATH, timeout=1), NoCurrentPackageError,
            "no_package_rejected", message_contains="Package"))
        package = None
    except Exception as exc:  # noqa: BLE001
        results.append(result("scenario", "FAIL", error_detail("find_by_xpath 场景执行失败", exc)))
    finally:
        if page is not None:
            try:
                page.close(ignore_beforeunload=True)
            except Exception:  # noqa: BLE001
                pass
        if package is not None:
            try:
                package.close()
            except Exception:  # noqa: BLE001
                pass
        shutil.rmtree(copy_dir, ignore_errors=True)
        if fixture is not None:
            fixture.__exit__(None, None, None)
        results.append(result(
            "cleanup", "PASS" if not copy_dir.exists() else "FAIL",
            "已关闭页面与 Package，删除元素库副本，并停止本地 fixture 服务",
            library_copy_removed=not copy_dir.exists()))

    statuses = {item["status"] for item in results}
    code = 1 if "FAIL" in statuses else (2 if "BLOCKED" in statuses else 0)
    return results, code


def main(argv=None):
    parser = argparse.ArgumentParser(description="WebBrowser.find_by_xpath() 页面对象 API 验收")
    parser.add_argument("--target-url", default=FIXTURE_URL, help="靶场页；默认本地 fixture")
    parser.add_argument("--mode", choices=("chrome", "edge"), default="chrome")
    parser.add_argument("--load-timeout", type=float, default=20)
    parser.add_argument("--timeout", type=float, default=8, help="find 的 timeout，默认 8")
    parser.add_argument("--library", type=Path, default=DEFAULT_LIBRARY, help="元素库目录")
    parser.add_argument("--contract-only", action="store_true")
    parser.add_argument("--json", action="store_true", help="在表格后额外输出 JSON 报告（用于归档验收产物）")
    args = parser.parse_args(argv)
    if args.load_timeout <= 0:
        parser.error("--load-timeout 必须大于 0")

    results, code = run(args)
    print("UIAutoma Web API 测试")
    print("API     : uiautoma.web.WebBrowser.find_by_xpath")
    print(f"页面    : {args.target_url}")
    print("进度     状态    测试项                  测试结果")
    print("────────────────────────────────────────────────────────────────────────")
    for index, current in enumerate(results, 1):
        status = current["status"]
        color = {"PASS": GREEN, "BLOCKED": YELLOW}.get(status, RED)
        label = {"PASS": "通过", "BLOCKED": "阻塞"}.get(status, "失败")
        print(f"{index:02d}/{len(results):02d}    {color}[{label}]{RESET}  {current['case_id']:<30}  {current['detail']}")
    print("────────────────────────────────────────────────────────────────────────")
    summary = "测试通过" if code == 0 else ("测试阻塞" if code == 2 else "测试失败")
    print(f"{summary} · {sum(item['status'] == 'PASS' for item in results)}/{len(results)} 通过 · 退出码 {code}")
    if args.json:
        print(json.dumps({
            "api": "uiautoma.web.WebBrowser.find_by_xpath",
            "target_url": args.target_url,
            "mode": args.mode,
            "status": "PASS" if code == 0 else ("BLOCKED" if code == 2 else "FAIL"),
            "exit_code": code,
            "results": results,
        }, ensure_ascii=False, indent=2))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
