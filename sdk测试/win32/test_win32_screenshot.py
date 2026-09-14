r"""Win32Element.screenshot() 真实元素截图测试。

API 参数（不是脚本参数）::

    screenshot(folder_path: str, *, filename: str | None = None) -> str

folder_path 必填，支持位置或关键字调用；不存在的目录会自动创建。
filename 仅限关键字；省略、None 或空字符串时自动命名。没有 .png 后缀时
追加 .png（例如 example.jpg -> example.jpg.png）。返回 PNG 文件路径 str。
公开 API 不接受 timeout，底层使用 5 秒读取预算。

脚本参数：无。运行：uv run .\win32\test_win32_screenshot.py

前提：UIAutoma dev 正在运行并启用 D:\code\元素库\260902_win元素，靶场已启动。
自动激活靶场并点击 win32靶场_tab_item表单控件，截图元素
win32靶场_表单控件_表单面板。请在运行期间不要移动窗口或遮挡靶场。
截图保留于本脚本目录 artifacts/screenshot/ 下的独立目录，供人工查看；
只检查 PNG 结构和尺寸，不自动宣称图像内容正确。
结束时恢复鼠标和原前台窗口、关闭借用 Package；靶场保持运行并停留在表单页。
导入模块不会连接 Runtime 或操作界面。
"""

from __future__ import annotations

import ctypes
from ctypes import wintypes
import inspect
import os
from pathlib import Path
import struct
import sys
import tempfile
import time
import unicodedata
import zlib

import uiautoma
from uiautoma import win32
from uiautoma.win32 import Win32Element

__test__ = False
LIBRARY = Path(r"D:\code\元素库\260902_win元素")
TAB = "win32靶场_tab_item表单控件"
PANEL = "win32靶场_表单控件_表单面板"


def png_size(path: Path) -> tuple[int, int]:
    """检查 PNG 签名、完整块及 CRC，返回 IHDR 的像素尺寸。"""
    data = path.read_bytes()
    if data[:8] != b"\x89PNG\r\n\x1a\n":
        raise AssertionError("文件不是 PNG")
    offset, size, has_data = 8, None, False
    while offset + 12 <= len(data):
        length = struct.unpack_from(">I", data, offset)[0]
        end = offset + 12 + length
        if end > len(data):
            raise AssertionError("PNG 数据被截断")
        kind = data[offset + 4:offset + 8]
        payload = data[offset + 8:end - 4]
        crc = struct.unpack_from(">I", data, end - 4)[0]
        assert zlib.crc32(kind + payload) & 0xFFFFFFFF == crc, "PNG CRC 不正确"
        if offset == 8:
            assert kind == b"IHDR" and length == 13, "缺少 PNG IHDR"
            size = struct.unpack_from(">II", payload)
            assert min(size) > 0, "PNG 尺寸无效"
        if kind == b"IDAT" and payload:
            has_data = True
        if kind == b"IEND":
            assert length == 0 and has_data and size and end == len(data), "PNG 结构不完整"
            return size
        offset = end
    raise AssertionError("PNG 缺少结束块")


def pad(text: str, width: int) -> str:
    length = sum(0 if unicodedata.combining(c) else
                 2 if unicodedata.east_asian_width(c) in {"W", "F"} else 1 for c in text)
    return text + " " * max(0, width - length)


def check_contract() -> str:
    sig = inspect.signature(Win32Element.screenshot)
    assert tuple(sig.parameters) == ("self", "folder_path", "filename"), str(sig)
    folder, filename = sig.parameters["folder_path"], sig.parameters["filename"]
    assert folder.default is inspect.Parameter.empty
    assert folder.kind is inspect.Parameter.POSITIONAL_OR_KEYWORD
    assert str(folder.annotation) in {"str", "<class 'str'>"}
    assert filename.kind is inspect.Parameter.KEYWORD_ONLY and filename.default is None
    assert str(filename.annotation) == "str | None"
    assert str(sig.return_annotation) in {"str", "<class 'str'>"}
    return "folder_path 必填，filename 仅限关键字且默认 None，返回 str"


def check_arguments(element, directory: Path) -> str:
    calls = [lambda: element.screenshot(),
             lambda: element.screenshot(str(directory), "extra.png"),
             lambda: element.screenshot(str(directory), timeout=1)]
    for call in calls:
        try:
            call()
        except TypeError:
            continue
        raise AssertionError("无效参数未抛出 TypeError")
    return "缺少目录、多余位置参数和 timeout 均被 TypeError 拒绝"


def main() -> int:
    user32 = ctypes.WinDLL("user32", use_last_error=True)
    user32.GetForegroundWindow.restype = wintypes.HWND
    user32.SetForegroundWindow.argtypes = [wintypes.HWND]
    user32.GetCursorPos.argtypes = [ctypes.POINTER(wintypes.POINT)]
    original_window = user32.GetForegroundWindow()
    original_mouse = wintypes.POINT()
    mouse_recorded = bool(user32.GetCursorPos(ctypes.byref(original_mouse)))
    package, element, output = None, None, None
    results = []
    started = time.perf_counter()
    color = sys.stdout.isatty() and "NO_COLOR" not in os.environ

    def run(label, operation):
        begin = time.perf_counter()
        try:
            detail, status = operation(), "PASS"
        except Exception as exc:
            detail = f"{type(exc).__name__}: {exc}"
            status = "FAIL"
        results.append((label, status, detail, (time.perf_counter() - begin) * 1000))

    def prepare():
        nonlocal package, element, output
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
        assert rect[2] > 0 and rect[3] > 0, f"面板边界无效：{rect}"
        root = Path(__file__).resolve().parent / "artifacts" / "screenshot"
        root.mkdir(parents=True, exist_ok=True)
        output = Path(tempfile.mkdtemp(prefix="run-", dir=root))
        element = candidate
        return f"已切换表单页并获取面板，物理尺寸 {rect[2]} × {rect[3]}"

    def capture(case, kwargs, expected_name=None, keyword_folder=False):
        directory = output / case
        assert not directory.exists(), "用例目录应由 API 创建"
        before = element.get_bounding(to96dpi=False)
        if keyword_folder:
            value = element.screenshot(folder_path=str(directory), **kwargs)
        else:
            value = element.screenshot(str(directory), **kwargs)
        assert isinstance(value, str) and value, f"返回路径无效：{value!r}"
        path = Path(value)
        assert path.is_file() and path.resolve().parent == directory.resolve(), value
        assert path.suffix.lower() == ".png", value
        if expected_name:
            assert path.name == expected_name, f"预期 {expected_name}，实际 {path.name}"
        actual = png_size(path)
        after = element.get_bounding(to96dpi=False)
        assert before == after, "截图期间元素矩形发生变化，请保持窗口静止后重试"
        assert actual == tuple(before[2:]), f"预期 {before[2:]}，实际 {actual}"
        assert element.last_result.ok, str(element.last_result)
        return f"PNG {actual[0]} × {actual[1]}，目录已创建，文件 {path.name}"

    print("UIAutoma Win32 API 测试\n")
    print(f"  API     : uiautoma.win32.Win32Element.screenshot\n  元素库  : {LIBRARY}")
    print(f"  自动切页: {TAB}\n  截图元素: {PANEL}\n  输出策略: 保留截图供人工查看\n")
    try:
        run("API 合同", check_contract)
        run("元素与页面准备", prepare)
        cases = [("省略文件名", "default", {}, None, False),
                 ("None 文件名", "none", {"filename": None}, None, False),
                 ("空文件名", "empty", {"filename": ""}, None, False),
                 ("目录关键字调用", "keyword", {"filename": "表单面板.png"}, "表单面板.png", True),
                 ("自动补齐后缀", "suffix", {"filename": "panel"}, "panel.png", False),
                 ("其他扩展名", "other", {"filename": "panel.jpg"}, "panel.jpg.png", False)]
        for label, case, kwargs, name, keyword in cases:
            if element is None:
                results.append((label, "BLOCKED", "面板准备失败，未执行截图", 0.0))
            else:
                run(label, lambda c=case, k=kwargs, n=name, f=keyword: capture(c, k, n, f))
        if element is not None:
            run("参数数量限制", lambda: check_arguments(element, output))
        else:
            results.append(("参数数量限制", "BLOCKED", "面板准备失败", 0.0))
    finally:
        def cleanup():
            errors = []
            if package is not None:
                try:
                    package.close()
                except Exception as exc:
                    errors.append(f"Package：{exc}")
            if mouse_recorded:
                user32.SetCursorPos(original_mouse.x, original_mouse.y)
                current = wintypes.POINT()
                if not user32.GetCursorPos(ctypes.byref(current)) or (current.x, current.y) != (original_mouse.x, original_mouse.y):
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

    print(f"{pad('进度', 7)}  {pad('状态', 6)}  {pad('测试项', 18)}  测试结果")
    print("─" * 110)
    for i, (label, status, detail, duration) in enumerate(results, 1):
        badge = {"PASS": "[通过]", "FAIL": "[失败]", "BLOCKED": "[阻塞]"}[status]
        if color:
            badge = f"\x1b[{ {'PASS':32, 'FAIL':31, 'BLOCKED':33}[status]}m{badge}\x1b[0m"
        print(f"{i:02d}/{len(results):02d}    {badge}  {pad(label, 18)}  {detail}  {duration:.1f}ms")
    code = 1 if any(r[1] == "FAIL" for r in results) else 2 if any(r[1] == "BLOCKED" for r in results) else 0
    passed = sum(r[1] == "PASS" for r in results)
    print("─" * 110)
    print(f"{'测试通过' if code == 0 else '测试未通过'}  ·  {'VERIFIED' if code == 0 else 'READY_FOR_LIVE'}  ·  "
          f"{passed}/{len(results)} 通过  ·  {(time.perf_counter()-started)*1000:.1f}ms  ·  退出码 {code}")
    if output:
        print(f"  截图目录: {output}\n  人工确认: 请打开 PNG，确认截图内容为表单面板且没有遮挡")
    return code


if __name__ == "__main__":
    raise SystemExit(main())
