"""复用用户已打开的靶场，按指定 CSS 复测；保留用户页面和输出文件。"""
from __future__ import annotations

import argparse
import inspect
import os
from pathlib import Path
import time
import unicodedata

import uiautoma
from uiautoma import web

__test__ = False
URL = "https://baobaomi900901.github.io/xpath/#/download-dialog-test"
CSS = "button[id='link-download-txt'] span"
OUTPUT_DIR = Path(r"D:\code\pytest\download")
FILENAME = "123.txt"


def require(ok, message):
    if not ok:
        raise AssertionError(message)


def verify_file(returned, expected, timeout=10):
    require(isinstance(returned, str) and returned, "保存返回值不是非空路径字符串")
    require(Path(returned).resolve() == expected.resolve(), f"返回路径不符: {returned!r}")
    deadline = time.monotonic() + timeout
    while True:
        if expected.is_file() and expected.stat().st_size > 0 and not Path(str(expected) + ".crdownload").exists():
            return f"返回路径正确；本次 TXT 已落盘，{expected.stat().st_size} 字节；保留文件"
        if time.monotonic() >= deadline:
            raise AssertionError(f"文件未就绪（不存在、为空或仍在下载）: {expected}")
        time.sleep(0.1)


def run(contract_only=False):
    results, page = [], None
    expected = OUTPUT_DIR / FILENAME

    def step(label, call):
        started = time.perf_counter()
        try:
            value = call()
            detail = value if isinstance(value, str) else "调用成功，返回 None"
            status = "PASS"
        except Exception as exc:
            status = "FAIL"
            detail = f"{type(exc).__name__}: {exc}"
            for field in ("trace_info", "trace_id", "strategy", "fallback_reason", "log_lines"):
                if getattr(exc, field, None):
                    detail += f"；{field}={getattr(exc, field)}"
        results.append((label, status, str(detail), (time.perf_counter() - started) * 1000))
        return status == "PASS"

    def contract():
        sig = inspect.signature(web.handle_save_dialog)
        bound = sig.bind(str(OUTPUT_DIR), "ok", "chrome", file_name=FILENAME, wait_appear_timeout=20)
        require(bound.arguments["dialog_result"] == "ok" and bound.arguments["mode"] == "chrome", "保存参数绑定不正确")
        inspect.signature(web.WebBrowser.find_by_css).bind(None, CSS)
        inspect.signature(web.WebElement.click).bind(None)
        return "用户调用参数绑定正确；CSS 查找和默认 click() 签名有效"

    if not step("调用合同", contract) or contract_only:
        return results
    if not step("输出保护", lambda: require(not expected.exists(), f"文件已存在，停止以避免覆盖: {expected}")):
        return results
    try:
        def connect():
            nonlocal page
            page = web.get(url=URL, mode="chrome", load_timeout=20)
            require(isinstance(page, web.WebBrowser), "get 返回类型错误")
            return "已连接用户打开的测试标签页，不新建页面"

        if not step("连接现有网页", connect):
            return results
        element = None

        def find():
            nonlocal element
            element = page.find_by_css(CSS)
            require(isinstance(element, web.WebElement), "CSS 查找返回类型错误")
            return f"找到 span 元素；name={element.name!r}"

        if not step("CSS 查找", find):
            return results
        if not step("默认点击", lambda: element.click()):
            return results
        returned = None

        def save():
            nonlocal returned
            # 路径与 'ok' 之间必须有逗号，否则 Python 会拼接两个字符串。
            returned = web.handle_save_dialog(
                str(OUTPUT_DIR), "ok", "chrome", file_name=FILENAME, wait_appear_timeout=20,
            )
            return f"API 返回: {returned!r}"

        if not step("处理保存对话框", save):
            return results
        step("文件读回核验", lambda: verify_file(returned, expected))
    finally:
        if page is not None:
            step("保留用户页面", lambda: "不关闭用户标签页，不发送全局 Esc；若生成文件则保留")
    return results


def main():
    parser = argparse.ArgumentParser(description="handle_save_dialog CSS 指定场景复测")
    parser.add_argument("--contract-only", action="store_true", help="只绑定参数，不连接浏览器或改文件")
    args = parser.parse_args()
    print(f"UIAutoma Web API 测试\n API     : uiautoma.web.handle_save_dialog\n 页面    : {URL}")
    print(f" CSS     : {CSS}\n 输出    : {OUTPUT_DIR / FILENAME}\n SDK     : {uiautoma.__file__}", flush=True)
    started = time.perf_counter()
    results = run(args.contract_only)
    print("进度     状态    测试项                  测试结果 / 耗时\n" + "─" * 110)
    for i, (label, status, detail, elapsed) in enumerate(results, 1):
        text = "[通过]" if status == "PASS" else "[失败]"
        if "NO_COLOR" not in os.environ:
            text = ("\x1b[32m" if status == "PASS" else "\x1b[31m") + text + "\x1b[0m"
        width = sum(2 if unicodedata.east_asian_width(c) in "WF" else 1 for c in label)
        print(f"{i:02d}/{len(results):02d}    {text}  {label}{' ' * max(0, 22 - width)}  {detail}  {elapsed:.1f}ms")
    passed = sum(row[1] == "PASS" for row in results)
    code = 0 if passed == len(results) else 1
    print("─" * 110)
    print(f"{'本场景通过' if code == 0 else '测试失败'} · {passed}/{len(results)} 通过 · "
          f"{(time.perf_counter() - started) * 1000:.1f}ms · 退出码 {code}")
    return code


if __name__ == "__main__":
    raise SystemExit(main())
