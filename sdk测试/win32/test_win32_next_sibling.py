r"""Win32Element.next_sibling() 实测。

API 参数（不是脚本参数）::

    element.next_sibling() -> Win32Element

无公开参数，内部默认预算 5 秒。返回同一父元素下 UIA 顺序中的后一个兄弟，
不是视觉上的右侧控件。无后一个兄弟时预期 ElementNotFoundError。

脚本参数：无。运行：uv run .\win32\test_win32_next_sibling.py
前提：UIAutoma dev 运行、启用 D:\code\元素库\260902_win元素，靶场已启动。
通过 _form_tab.ensure_form_tab 自动切换表单页，读取
win32靶场_表单控件_表单面板.children() 建立当次顺序参照，不调用 child_at()。
比较首项、中间项、倒数第二项的后继，以及首项连续两次调用的结果。
校验返回类型、关系、名称及控件类型；要求被比较的名称/类型组合在参照中唯一。
不固定子元素总数及控件排列，不通过 SDK 的临时元素 ID 相等判断 UIA 身份。
结束时关闭借用 Package，靶场保持运行、停留表单页；不恢复原 Tab 或焦点。
导入时不连接 Runtime、不操作界面。
"""

from __future__ import annotations

import inspect
import os
from pathlib import Path
import sys
import time
import unicodedata

import uiautoma
from uiautoma import win32
from uiautoma.win32 import Win32Element
from uiautoma._core import ElementNotFoundError
from _form_tab import ensure_form_tab

__test__ = False
LIBRARY = Path(r"D:\code\元素库\260902_win元素")
PANEL = "win32靶场_表单控件_表单面板"


def pad(text, width):
    length = sum(0 if unicodedata.combining(c) else
                 2 if unicodedata.east_asian_width(c) in {"W", "F"} else 1 for c in text)
    return text + " " * max(0, width - length)


def check_contract():
    sig = inspect.signature(Win32Element.next_sibling)
    assert tuple(sig.parameters) == ("self",), str(sig)
    assert "Win32Element" in str(sig.return_annotation), str(sig)
    return "公开签名无参数并返回 Win32Element"


def identity(element):
    raw = element.raw
    kind = str(raw.get("control_type") or raw.get("controlType") or "")
    return element.name, kind.casefold().removesuffix("control")


def check_result(actual, expected, reference):
    assert isinstance(actual, Win32Element), f"返回类型错误：{type(actual).__name__}"
    key = identity(expected)
    assert sum(identity(item) == key for item in reference) == 1, f"参照名称/类型不唯一：{key}"
    assert actual.id.startswith("rt:win:"), f"非 Runtime 元素：{actual.id}"
    assert actual.raw.get("relation") == "next_sibling", f"关系错误：{actual.raw.get('relation')}"
    assert identity(actual) == key, f"预期 {key}，实际 {identity(actual)}"
    return f"{key[1]}“{key[0]}”"


def main():
    package, reference = None, None
    results = []
    started = time.perf_counter()
    color = sys.stdout.isatty() and "NO_COLOR" not in os.environ

    def run(label, operation):
        begin = time.perf_counter()
        try:
            detail, status = operation(), "PASS"
        except Exception as exc:
            detail, status = f"{type(exc).__name__}: {exc}", "FAIL"
        results.append((label, status, detail, (time.perf_counter() - begin) * 1000))

    def prepare():
        nonlocal package, reference
        package = uiautoma.current(required=False, refresh=True, timeout=5)
        assert package is not None, "UIAutoma 当前未启用元素库"
        assert Path(package.package_dir).resolve() == LIBRARY.resolve(), "当前元素库不匹配"
        ensure_form_tab(package)
        selector = package.selector(PANEL, kind="win")
        panel = win32.find(selector, timeout=10)
        children = panel.children()
        assert isinstance(children, list) and len(children) >= 4, "参照需要至少四个直属子元素"
        assert all(isinstance(item, Win32Element) for item in children), "参照中存在非 Win32Element"
        reference = children
        return f"表单页已准备，读取 {len(children)} 个直属子元素作为顺序参照"

    def following(index):
        actual = reference[index].next_sibling()
        detail = check_result(actual, reference[index + 1], reference)
        return f"第 {index} 项的后继与第 {index + 1} 项一致：{detail}"

    def chained():
        first = reference[0].next_sibling()
        check_result(first, reference[1], reference)
        second = first.next_sibling()
        detail = check_result(second, reference[2], reference)
        return f"首项连续两次 next_sibling() 返回第三项：{detail}"

    def no_next():
        try:
            result = reference[-1].next_sibling()
        except ElementNotFoundError:
            return "末项无后一个兄弟，正确抛出 ElementNotFoundError"
        raise AssertionError(f"预期 ElementNotFoundError，实际返回 {result!r}")

    def extra_args():
        item = reference[1]
        for call in (lambda: item.next_sibling(1),
                     lambda: item.next_sibling(timeout=1)):
            try:
                call()
            except TypeError:
                continue
            raise AssertionError("多余参数未被 TypeError 拒绝")
        return "位置参数和 timeout 关键字均被 TypeError 拒绝"

    print("UIAutoma Win32 API 测试\n")
    print(f"  API     : uiautoma.win32.Win32Element.next_sibling\n  元素库  : {LIBRARY}")
    print(f"  面板元素: {PANEL}\n  顺序参照: children() 的当次结果，索引从 0 开始\n")
    try:
        run("API 合同", check_contract)
        run("表单页与参照准备", prepare)
        cases = [("首项后继", lambda: following(0)),
                 ("中间项后继", lambda: following(len(reference) // 2)),
                 ("倒数第二项后继", lambda: following(len(reference) - 2)),
                 ("链式后继", chained), ("末项无后继", no_next),
                 ("参数数量限制", extra_args)]
        for label, operation in cases:
            if reference is None:
                results.append((label, "BLOCKED", "表单页或参照准备失败，未执行", 0.0))
            else:
                run(label, operation)
    finally:
        def cleanup():
            if package is not None:
                package.close()
                return "已关闭借用 Package；靶场保持运行、停留表单页"
            return "没有已借用 Package；未关闭靶场"
        run("资源清理", cleanup)

    print(f"{pad('进度', 7)}  {pad('状态', 6)}  {pad('测试项', 18)}  {pad('测试结果', 88)}  耗时")
    print("─" * 135)
    for i, (label, status, detail, duration) in enumerate(results, 1):
        badge = {"PASS": "[通过]", "FAIL": "[失败]", "BLOCKED": "[阻塞]"}[status]
        if color:
            badge = f"\x1b[{ {'PASS':32, 'FAIL':31, 'BLOCKED':33}[status]}m{badge}\x1b[0m"
        print(f"{i:02d}/{len(results):02d}    {badge}  {pad(label, 18)}  {pad(detail, 88)}  {duration:7.1f}ms")
    code = 1 if any(r[1] == "FAIL" for r in results) else 2 if any(r[1] == "BLOCKED" for r in results) else 0
    passed = sum(r[1] == "PASS" for r in results)
    print("─" * 135)
    print(f"{'测试通过' if code == 0 else '测试未通过'}  ·  {'VERIFIED' if code == 0 else 'READY_FOR_LIVE'}  ·  "
          f"{passed}/{len(results)} 通过  ·  {(time.perf_counter()-started)*1000:.1f}ms  ·  退出码 {code}")
    return code


if __name__ == "__main__":
    raise SystemExit(main())
