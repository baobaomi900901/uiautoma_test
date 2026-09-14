r"""Win32Element.get_bounding() 真实坐标测试。

API 参数（不是脚本参数）::

    get_bounding(to96dpi: bool = True, relative_to: str = "screen")
        -> tuple[int, int, int, int]

两个参数均允许位置或关键字传入，返回 (x, y, width, height)。
to96dpi=False 返回物理像素；True 按当前实现的屏幕 DC DPI / 96 换算并取整。
relative_to 支持 screen/window/client，忽略大小写和首尾空格；非法名称
抛出 InvalidParamsError。公开接口没有 timeout，底层读取预算 3 秒。
当前实现未严格校验 to96dpi 的 bool 类型，本轮覆盖正式的 True/False 值。

脚本参数：无。运行：uv run .\win32\test_win32_get_bounding.py
前提：UIAutoma dev 运行且启用 D:\code\元素库\260902_win元素，靶场已启动。
自动点击 win32靶场_tab_item表单控件，读取 win32靶场_表单控件_表单面板。
请保持窗口静止。结束后恢复鼠标与原前台窗口、关闭借用 Package，靶场停留表单页。

物理屏幕矩形作为转换参照；使用原生 GetWindowRect / ClientToScreen / GetDeviceCaps
验证坐标系与缩放关系。该参照不是独立的 UIA 边界测量，本轮不验证跨屏混合 DPI。
当读取 DPI=96 时，两种模式数值相同，不宣称验证了非 100% 缩放换算。
导入模块不会连接 Runtime 或操作界面。
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
from uiautoma._core import InvalidParamsError

__test__ = False
LIBRARY = Path(r"D:\code\元素库\260902_win元素")
TAB = "win32靶场_tab_item表单控件"
PANEL = "win32靶场_表单控件_表单面板"


def pad(text, width):
    length = sum(0 if unicodedata.combining(c) else
                 2 if unicodedata.east_asian_width(c) in {"W", "F"} else 1 for c in text)
    return text + " " * max(0, width - length)


def check_contract():
    sig = inspect.signature(Win32Element.get_bounding)
    assert tuple(sig.parameters) == ("self", "to96dpi", "relative_to"), str(sig)
    for name in ("to96dpi", "relative_to"):
        assert sig.parameters[name].kind is inspect.Parameter.POSITIONAL_OR_KEYWORD, str(sig)
    assert sig.parameters["to96dpi"].default is True
    assert sig.parameters["relative_to"].default == "screen"
    assert str(sig.parameters["to96dpi"].annotation) in {"bool", "<class 'bool'>"}
    assert str(sig.parameters["relative_to"].annotation) in {"str", "<class 'str'>"}
    assert str(sig.return_annotation) == "tuple[int, int, int, int]", str(sig)
    return "to96dpi=True、relative_to=screen，均支持位置及关键字参数"


def validate_rect(value):
    assert isinstance(value, tuple) and len(value) == 4, f"不是四元组：{value!r}"
    assert all(type(v) is int for v in value), f"坐标不是整数：{value!r}"
    assert value[2] > 0 and value[3] > 0, f"宽高无效：{value!r}"
    return value


def expected_rect(screen, origin, dpi, logical):
    x, y, w, h = screen
    values = (x - origin[0], y - origin[1], w, h)
    return tuple(round(v * 96 / dpi) for v in values) if logical else values


def main():
    user = ctypes.WinDLL("user32", use_last_error=True)
    gdi = ctypes.WinDLL("gdi32", use_last_error=True)
    user.GetForegroundWindow.restype = wintypes.HWND
    user.SetForegroundWindow.argtypes = [wintypes.HWND]
    user.GetWindowRect.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.RECT)]
    user.ClientToScreen.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.POINT)]
    user.GetCursorPos.argtypes = [ctypes.POINTER(wintypes.POINT)]
    user.GetDC.argtypes, user.GetDC.restype = [wintypes.HWND], wintypes.HDC
    user.ReleaseDC.argtypes = [wintypes.HWND, wintypes.HDC]
    gdi.GetDeviceCaps.argtypes = [wintypes.HDC, ctypes.c_int]
    # 原生坐标与 SDK 的窗口原点读取都采用物理像素。
    user.SetThreadDpiAwarenessContext.argtypes = [ctypes.c_void_p]
    user.SetThreadDpiAwarenessContext.restype = ctypes.c_void_p
    old_dpi_context = user.SetThreadDpiAwarenessContext(ctypes.c_void_p(-4))
    if not old_dpi_context:
        raise ctypes.WinError(ctypes.get_last_error())
    original_window = user.GetForegroundWindow()
    mouse = wintypes.POINT()
    mouse_recorded = bool(user.GetCursorPos(ctypes.byref(mouse)))
    package, element, baseline, origins = None, None, None, None
    hwnd, dpi = 0, 0
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

    def window_origins():
        rect, client = wintypes.RECT(), wintypes.POINT()
        assert user.GetWindowRect(hwnd, ctypes.byref(rect)), "GetWindowRect 失败"
        assert user.ClientToScreen(hwnd, ctypes.byref(client)), "ClientToScreen 失败"
        return {"screen": (0, 0), "window": (rect.left, rect.top), "client": (client.x, client.y)}

    def prepare():
        nonlocal package, element, baseline, origins, hwnd, dpi
        assert mouse_recorded, "无法记录原始鼠标"
        package = uiautoma.current(required=False, refresh=True, timeout=5)
        assert package is not None, "当前未启用元素库"
        assert Path(package.package_dir).resolve() == LIBRARY.resolve(), "当前元素库不匹配"
        window = win32.get(title="Win32 靶场 - UIA", class_name="XPathWin32ShootingRange",
                           process_name="win32-shooting-range-uia.exe")
        hwnd = int(window.get_detail("handle"))
        window.activate()
        tab = win32.find(package.selector(TAB, kind="win"), timeout=10)
        tab.click(simulative=True, move_mouse=False, delay_after=0.5)
        tab.last_result.raise_for_error()
        selector = package.selector(PANEL, kind="win")
        candidate = win32.find(selector, timeout=10)
        assert isinstance(candidate, Win32Element)
        assert candidate.raw.get("source_element_id") == selector.id(), "元素身份不匹配"
        baseline = validate_rect(candidate.get_bounding(False, "screen"))
        origins = window_origins()
        dc = user.GetDC(None)
        assert dc, "无法读取屏幕 DC"
        try:
            dpi = gdi.GetDeviceCaps(dc, 88)
        finally:
            user.ReleaseDC(None, dc)
        assert dpi > 0, f"屏幕 DPI 无效：{dpi}"
        element = candidate
        print(f"  物理参照: {baseline}\n  窗口原点: {origins['window']}\n  客户原点: {origins['client']}\n  屏幕 DPI: {dpi}\n")
        if dpi == 96:
            print("  覆盖说明: DPI=96，两种模式应相同；未覆盖非 100% 缩放\n")
        return "已切换表单页，记录物理矩形、原生窗口原点与屏幕 DPI"

    def compare(call, logical, mode):
        assert window_origins() == origins, "窗口原点变化，请保持窗口静止"
        before = validate_rect(element.get_bounding(False, "screen"))
        assert before == baseline, "面板位置或尺寸变化，请重试"
        expected = expected_rect(baseline, origins[mode], dpi, logical)
        actual = validate_rect(call())
        assert element.get_bounding(False, "screen") == baseline, "查询期间面板矩形变化"
        assert window_origins() == origins, "查询期间窗口原点变化"
        assert actual == expected, f"预期 {expected}，实际 {actual}"
        return f"预期 {expected}；实际 {actual}"

    def errors():
        for mode in ("desktop", "position", "   ", 123):
            try:
                element.get_bounding(relative_to=mode)
            except InvalidParamsError:
                continue
            raise AssertionError(f"非法坐标系 {mode!r} 未被拒绝")
        return "非法名称、纯空白及整数坐标系均被 InvalidParamsError 拒绝"

    def extra_args():
        for call in (lambda: element.get_bounding(False, "screen", 1),
                     lambda: element.get_bounding(timeout=1)):
            try:
                call()
            except TypeError:
                continue
            raise AssertionError("多余参数未被 TypeError 拒绝")
        return "多余位置参数及 timeout 关键字均被 TypeError 拒绝"

    print("UIAutoma Win32 API 测试\n")
    print(f"  API     : uiautoma.win32.Win32Element.get_bounding\n  元素库  : {LIBRARY}")
    print(f"  自动切页: {TAB}\n  测试元素: {PANEL}\n  返回规则: (x, y, 宽度, 高度)\n")
    try:
        run("API 合同", check_contract)
        run("元素与坐标准备", prepare)
        if element is not None:
            run("全部默认参数", lambda: compare(lambda: element.get_bounding(), True, "screen"))
            for logical in (False, True):
                for mode in ("screen", "window", "client"):
                    run(f"{'96 DPI' if logical else '物理像素'} {mode}",
                        lambda flag=logical, name=mode: compare(
                            lambda: element.get_bounding(to96dpi=flag, relative_to=name), flag, name))
            run("完整位置参数", lambda: compare(lambda: element.get_bounding(False, "client"), False, "client"))
            run("大小写与空格", lambda: compare(lambda: element.get_bounding(False, " WiNdOw "), False, "window"))
            run("非法坐标系", errors)
            run("参数数量限制", extra_args)
        else:
            results.append(("坐标测试", "BLOCKED", "面板准备失败，未执行后续用例", 0.0))
    finally:
        def cleanup():
            failures = []
            try:
                if package is not None:
                    try:
                        package.close()
                    except Exception as exc:
                        failures.append(f"Package：{exc}")
                if mouse_recorded:
                    user.SetCursorPos(mouse.x, mouse.y)
                    actual = wintypes.POINT()
                    if not user.GetCursorPos(ctypes.byref(actual)) or (actual.x, actual.y) != (mouse.x, mouse.y):
                        failures.append("鼠标未恢复")
                if original_window:
                    user.SetForegroundWindow(original_window)
                    deadline = time.perf_counter() + 1
                    while user.GetForegroundWindow() != original_window and time.perf_counter() < deadline:
                        time.sleep(0.02)
                    if user.GetForegroundWindow() != original_window:
                        failures.append("原前台窗口未恢复")
            finally:
                if not user.SetThreadDpiAwarenessContext(old_dpi_context):
                    failures.append("线程 DPI 上下文未恢复")
            assert not failures, "；".join(failures)
            return "鼠标、焦点及 DPI 上下文已恢复，Package 已关闭；靶场停留表单页"
        run("资源恢复", cleanup)

    print(f"{pad('进度', 7)}  {pad('状态', 6)}  {pad('测试项', 20)}  {pad('测试结果', 88)}  耗时")
    print("─" * 137)
    for i, (label, status, detail, duration) in enumerate(results, 1):
        badge = {"PASS": "[通过]", "FAIL": "[失败]", "BLOCKED": "[阻塞]"}[status]
        if color:
            badge = f"\x1b[{ {'PASS':32, 'FAIL':31, 'BLOCKED':33}[status]}m{badge}\x1b[0m"
        print(f"{i:02d}/{len(results):02d}    {badge}  {pad(label, 20)}  {pad(detail, 88)}  {duration:7.1f}ms")
    code = 1 if any(r[1] == "FAIL" for r in results) else 2 if any(r[1] == "BLOCKED" for r in results) else 0
    passed = sum(r[1] == "PASS" for r in results)
    print("─" * 137)
    print(f"{'测试通过' if code == 0 else '测试未通过'}  ·  {'VERIFIED' if code == 0 else 'READY_FOR_LIVE'}  ·  "
          f"{passed}/{len(results)} 通过  ·  {(time.perf_counter()-started)*1000:.1f}ms  ·  退出码 {code}")
    return code


if __name__ == "__main__":
    raise SystemExit(main())
