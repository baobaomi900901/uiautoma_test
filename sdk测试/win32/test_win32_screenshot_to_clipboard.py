r"""Win32Element.screenshot_to_clipboard() 实测。

API 参数（不是脚本参数）::

    element.screenshot_to_clipboard() -> None

无公开参数；不接受 timeout，底层默认预算 5 秒。结果保存在 last_result。
截图替换系统剪贴板内容，格式为 CF_DIB。脚本参数：无。

运行：uv run .\win32\test_win32_screenshot_to_clipboard.py
前提：UIAutoma dev 运行并启用 D:\code\元素库\260902_win元素，靶场已启动。
自动点击“win32靶场_tab_item表单控件”，截图“win32靶场_表单控件_表单面板”。
请保持靶场无遮挡，不要在测试期间复制其他内容。
恢复鼠标与原前台窗口，关闭借用 Package；靶场停留表单页，最后截图保留供粘贴。
复用同目录 test_win32_save_screen_to_clipboard.py 的原生 DIB 读取辅助函数。
导入模块不连接 Runtime、不操作剪贴板或界面。
"""

from __future__ import annotations

import ctypes
from ctypes import wintypes
import inspect
import os
from pathlib import Path
import sys
import time
import unicodedata

import uiautoma
from uiautoma import win32
from uiautoma.win32 import Win32Element
from test_win32_save_screen_to_clipboard import _clipboard_dib_info, _enable_dpi_awareness

__test__ = False
LIBRARY = Path(r"D:\code\元素库\260902_win元素")
TAB = "win32靶场_tab_item表单控件"
PANEL = "win32靶场_表单控件_表单面板"


def pad(text, width):
    length = sum(0 if unicodedata.combining(c) else
                 2 if unicodedata.east_asian_width(c) in {"W", "F"} else 1 for c in text)
    return text + " " * max(0, width - length)


def check_contract():
    sig = inspect.signature(Win32Element.screenshot_to_clipboard)
    assert tuple(sig.parameters) == ("self",), str(sig)
    assert str(sig.return_annotation) in {"None", "<class 'NoneType'>"}, str(sig)
    return "公开签名无参数并返回 None"


def reject_arguments(element):
    for call in (lambda: element.screenshot_to_clipboard(1),
                 lambda: element.screenshot_to_clipboard(timeout=1)):
        try:
            call()
        except TypeError:
            continue
        raise AssertionError("多余参数未被 TypeError 拒绝")
    return "位置参数和 timeout 关键字均被 TypeError 拒绝"


def main():
    _enable_dpi_awareness()
    user32 = ctypes.WinDLL("user32", use_last_error=True)
    user32.GetForegroundWindow.restype = wintypes.HWND
    user32.SetForegroundWindow.argtypes = [wintypes.HWND]
    user32.GetCursorPos.argtypes = [ctypes.POINTER(wintypes.POINT)]
    user32.GetClipboardSequenceNumber.restype = wintypes.DWORD
    original_window = user32.GetForegroundWindow()
    mouse = wintypes.POINT()
    mouse_recorded = bool(user32.GetCursorPos(ctypes.byref(mouse)))
    package, element = None, None
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
        nonlocal package, element
        assert mouse_recorded, "无法记录原始鼠标位置"
        package = uiautoma.current(required=False, refresh=True, timeout=5)
        assert package is not None, "UIAutoma 尚未启用元素库"
        assert Path(package.package_dir).resolve() == LIBRARY.resolve(), "当前元素库不匹配"
        window = win32.get(title="Win32 靶场 - UIA", class_name="XPathWin32ShootingRange",
                           process_name="win32-shooting-range-uia.exe")
        window.activate()
        tab = win32.find(package.selector(TAB, kind="win"), timeout=10)
        tab.click(simulative=True, move_mouse=False, delay_after=0.5)
        tab.last_result.raise_for_error()
        selector = package.selector(PANEL, kind="win")
        candidate = win32.find(selector, timeout=10)
        assert isinstance(candidate, Win32Element)
        assert candidate.raw.get("source_element_id") == selector.id(), "元素身份不匹配"
        rect = candidate.get_bounding(to96dpi=False)
        assert min(rect[2:]) > 0, f"面板边界无效：{rect}"
        element = candidate
        return f"已切换表单页，面板物理尺寸 {rect[2]} × {rect[3]}"

    def capture():
        rect = element.get_bounding(to96dpi=False)
        sequence = user32.GetClipboardSequenceNumber()
        value = element.screenshot_to_clipboard()
        assert value is None, f"预期 None，实际 {value!r}"
        assert element.last_result.ok, str(element.last_result)
        dib = _clipboard_dib_info()
        assert user32.GetClipboardSequenceNumber() != sequence, "剪贴板序号未更新"
        assert element.get_bounding(to96dpi=False) == rect, "截图期间元素矩形变化"
        actual = (dib["width"], dib["height"])
        assert actual == tuple(rect[2:]), f"预期 {rect[2:]}，实际 {actual}"
        assert dib["planes"] == 1 and dib["bit_count"] == 32, f"DIB 格式异常：{dib}"
        return f"返回 None，剪贴板已更新，CF_DIB 32 bit，{actual[0]} × {actual[1]}"

    print("UIAutoma Win32 API 测试\n")
    print(f"  API     : uiautoma.win32.Win32Element.screenshot_to_clipboard\n  元素库  : {LIBRARY}")
    print(f"  自动切页: {TAB}\n  截图元素: {PANEL}\n  剪贴板  : 替换原内容，保留最后截图\n")
    try:
        run("API 合同", check_contract)
        run("元素与页面准备", prepare)
        for label, operation in (("截图到剪贴板", capture), ("重复截图", capture),
                                 ("参数数量限制", lambda: reject_arguments(element))):
            if element is None:
                results.append((label, "BLOCKED", "面板准备失败，未执行", 0.0))
            else:
                run(label, operation)
    finally:
        def cleanup():
            errors = []
            if package is not None:
                try:
                    package.close()
                except Exception as exc:
                    errors.append(f"Package：{exc}")
            if mouse_recorded:
                user32.SetCursorPos(mouse.x, mouse.y)
                actual = wintypes.POINT()
                if not user32.GetCursorPos(ctypes.byref(actual)) or (actual.x, actual.y) != (mouse.x, mouse.y):
                    errors.append("鼠标未恢复")
            if original_window:
                user32.SetForegroundWindow(original_window)
                deadline = time.perf_counter() + 1
                while user32.GetForegroundWindow() != original_window and time.perf_counter() < deadline:
                    time.sleep(0.02)
                if user32.GetForegroundWindow() != original_window:
                    errors.append("原前台窗口未恢复")
            assert not errors, "；".join(errors)
            return "鼠标及原前台窗口已恢复，Package 已关闭；靶场停留表单页"
        run("资源恢复", cleanup)

    print(f"{pad('进度', 7)}  {pad('状态', 6)}  {pad('测试项', 18)}  {pad('测试结果', 76)}  耗时")
    print("─" * 123)
    for i, (label, status, detail, duration) in enumerate(results, 1):
        badge = {"PASS": "[通过]", "FAIL": "[失败]", "BLOCKED": "[阻塞]"}[status]
        if color:
            badge = f"\x1b[{ {'PASS':32, 'FAIL':31, 'BLOCKED':33}[status]}m{badge}\x1b[0m"
        print(f"{i:02d}/{len(results):02d}    {badge}  {pad(label, 18)}  {pad(detail, 76)}  {duration:7.1f}ms")
    code = 1 if any(r[1] == "FAIL" for r in results) else 2 if any(r[1] == "BLOCKED" for r in results) else 0
    passed = sum(r[1] == "PASS" for r in results)
    print("─" * 123)
    print(f"{'测试通过' if code == 0 else '测试未通过'}  ·  {'VERIFIED' if code == 0 else 'READY_FOR_LIVE'}  ·  "
          f"{passed}/{len(results)} 通过  ·  {(time.perf_counter()-started)*1000:.1f}ms  ·  退出码 {code}")
    print("  人工确认: 请粘贴到画图，检查完整表单面板且没有遮挡；本脚本不恢复原剪贴板内容")
    return code


if __name__ == "__main__":
    raise SystemExit(main())
