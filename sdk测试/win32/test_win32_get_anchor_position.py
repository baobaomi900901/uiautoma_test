r"""Win32Element.get_anchor_position()，使用原生 drag-target 窗口边界独立验算。

API（两个参数均仅限关键字）：
    anchor: object | None = None  默认中心；九宫格、random、(anchor,x,y)、字典偏移。
    to96dpi: bool = True          True 返回96 DPI逻辑坐标；False 返回物理屏幕像素。
返回 tuple[int,int]，不移动鼠标。偏移在返回坐标系中相加。
读取锚点在矩形边缘，例如右下角是(x+w,y+h)，不同于鼠标动作内缩的安全点。

脚本参数：无。运行：uv run .\win32\test_win32_get_anchor_position.py
前置：dev运行、启用 D:\code\元素库\260902_win元素、靶场已启动。
自动切换拖拽页，使用 win32靶场_拖拽测试_可拖拽元素；不拖拽、不重置位置、不用剪贴板。
以 GetWindowRect 获取物理边界，以目标显示器 GetScaleFactorForMonitor 返回值验算96 DPI坐标。
96 DPI预期：分别缩放并取整矩形x/y/w/h，再求锚点。请分别在100%和250%屏幕运行。
借用 get_value 脚本的 DPI、日志、原生窗口和清理辅助；结束后恢复鼠标/前台并关闭Package。
"""

import ctypes
import inspect
from pathlib import Path
from ctypes import wintypes

import test_win32_get_value as helper
from uiautoma import current, win32, InvalidParamsError
from uiautoma.win32 import Win32Element

LIBRARY = Path(r'D:\code\元素库\260902_win元素')
TAB = 'win32靶场_tab_item拖拽测试'
TARGET = 'win32靶场_拖拽测试_可拖拽元素'
ANCHORS = ('topLeft','topCenter','topRight','middleLeft','middleCenter',
           'middleRight','bottomLeft','bottomCenter','bottomRight')


def native_target(parent):
    user32 = helper._user32()
    matches = []
    @helper.WNDENUMPROC
    def visit(hwnd, unused):
        if helper.class_name(hwnd, user32) == 'Button' and helper.get_native_text(hwnd) == 'drag-target':
            matches.append(int(hwnd))
        return True
    user32.EnumChildWindows(parent, visit, 0)
    if len(matches) != 1:
        raise RuntimeError(f'原生 drag-target 不唯一：{matches}')
    return matches[0]


def monitor_scale(hwnd):
    user32 = ctypes.WinDLL('user32', use_last_error=True)
    user32.MonitorFromWindow.argtypes = [wintypes.HWND, wintypes.DWORD]
    user32.MonitorFromWindow.restype = wintypes.HANDLE
    monitor = user32.MonitorFromWindow(hwnd, 2)
    shcore = ctypes.WinDLL('shcore')
    shcore.GetScaleFactorForMonitor.argtypes = [wintypes.HANDLE, ctypes.POINTER(ctypes.c_int)]
    shcore.GetScaleFactorForMonitor.restype = ctypes.c_long
    percent = ctypes.c_int()
    result = shcore.GetScaleFactorForMonitor(monitor, ctypes.byref(percent))
    if result != 0 or percent.value <= 0:
        raise RuntimeError(f'读取目标显示器缩放失败：{result}')
    return percent.value / 100


def expected_point(rect, scale, logical, name='middleCenter', ox=0, oy=0):
    x,y,w,h = (tuple(round(v / scale) for v in rect) if logical else rect)
    index = ANCHORS.index(name)
    col, row = index % 3, index // 3
    return round(x + col*w/2 + ox), round(y + row*h/2 + oy)


def main():
    print('UIAutoma Win32 Element API 测试\n')
    print('  API     : uiautoma.win32.Win32Element.get_anchor_position')
    print(f'  元素库  : {LIBRARY}\n  元素    : {TARGET}\n  DPI 模式: {helper.DPI_AWARENESS_MODE}')
    results = []
    package = element = hwnd = None
    mouse, foreground = helper.current_cursor(), helper.current_foreground()

    def contract():
        sig = inspect.signature(Win32Element.get_anchor_position)
        assert list(sig.parameters) == ['self','anchor','to96dpi'], sig
        for name, default in [('anchor',None),('to96dpi',True)]:
            p = sig.parameters[name]
            assert p.kind == p.KEYWORD_ONLY and p.default is default, sig
        assert str(sig.return_annotation) == 'tuple[int, int]', sig
        return '两个仅限关键字参数、默认值和返回注解符合合同'

    def prepare():
        nonlocal package, element, hwnd
        package = current(required=True, refresh=True, timeout=5)
        assert Path(package.package_dir).resolve() == LIBRARY.resolve(), package.package_dir
        window = win32.get(title='Win32 靶场 - UIA', process_name='win32-shooting-range-uia.exe', timeout=5)
        window.find(package.selector(TAB, kind='win'), timeout=5).click(delay_after=0.2)
        element = window.find(package.selector(TARGET, kind='win'), timeout=5)
        hwnd = native_target(window.get_detail('handle'))
        bounds = helper.window_rect(hwnd, helper._user32())
        scale = monitor_scale(hwnd)
        return 'SDK 元素与原生目标已定位', [f'原生物理边界: {bounds}', f'目标显示器缩放: {scale*100:g}%']

    def check(logical, anchor=None, name='middleCenter', ox=0, oy=0, default=False):
        before = helper.window_rect(hwnd, helper._user32())
        scale = monitor_scale(hwnd)
        old_result, old_mouse = element.last_result, helper.current_cursor()
        actual = element.get_anchor_position() if default else element.get_anchor_position(anchor=anchor, to96dpi=logical)
        assert type(actual) is tuple and len(actual)==2 and all(type(v) is int for v in actual), actual
        assert helper.window_rect(hwnd, helper._user32()) == before, '读取期间窗口发生移动，请保持靶场不动'
        assert helper.current_cursor() == old_mouse, '读取期间鼠标移动，请勿手动移动鼠标'
        assert element.last_result is old_result, '读取改变了 last_result'
        if name == 'random':
            x,y,w,h = tuple(round(v/scale) for v in before) if logical else before
            assert x <= actual[0] <= x+w and y <= actual[1] <= y+h, actual
            expected = f'位于 ({x},{y},{w},{h}) 内'
        else:
            expected = expected_point(before, scale, logical, name, ox, oy)
            assert actual == expected, f'预期 {expected}，实际 {actual}；物理边界 {before}；显示器缩放 {scale*100:g}%'
        return '坐标正确，鼠标、窗口与 last_result 均未改变', [f'预期: {expected}；实际: {actual}']

    def rejected(invoke, error):
        try:
            invoke()
        except error:
            return f'参数被 {error.__name__} 正确拒绝'
        raise AssertionError(f'没有抛出 {error.__name__}')

    try:
        results.append(helper.run_case('API 合同', contract))
        results.append(helper.run_case('拖拽页与原生目标', prepare))
        if all(r.passed for r in results):
            results.append(helper.run_case('全部默认参数', lambda: check(True, default=True)))
            for logical in (False, True):
                mode = '逻辑' if logical else '物理'
                results.append(helper.run_case(mode+' None中心', lambda l=logical: check(l)))
                for anchor in ANCHORS:
                    results.append(helper.run_case(mode+' '+anchor, lambda l=logical,a=anchor: check(l,a,a)))
                results.append(helper.run_case(mode+' 三元组偏移', lambda l=logical: check(l,('middleCenter',6,-4),'middleCenter',6,-4)))
                results.append(helper.run_case(mode+' 字典偏移', lambda l=logical: check(l,dict(anchor='middleCenter',offset_x=-6,offset_y=4),'middleCenter',-6,4)))
                results.append(helper.run_case(mode+' 随机锚点', lambda l=logical: check(l,'random','random')))
            for name, call, error in [
                ('非法锚点', lambda: element.get_anchor_position(anchor='invalid'), InvalidParamsError),
                ('非法锚点类型', lambda: element.get_anchor_position(anchor=123), InvalidParamsError),
                ('禁止位置参数', lambda: element.get_anchor_position('middleCenter'), TypeError),
                ('不支持timeout', lambda: element.get_anchor_position(timeout=1), TypeError),
            ]:
                results.append(helper.run_case(name, lambda f=call,e=error: rejected(f,e)))
    finally:
        def cleanup():
            errors=[]
            actions=[('鼠标',lambda: helper.restore_cursor(mouse)),('前台',lambda: helper.restore_foreground(foreground))]
            if package is not None:
                actions.append(('Package',package.close))
            for name, action in actions:
                try: action()
                except Exception as exc: errors.append(f'{name}: {exc}')
            if errors: raise RuntimeError('；'.join(errors))
            return '鼠标和前台已恢复，Package 已关闭（如已取得），靶场保留拖拽页'
        results.append(helper.run_case('资源清理',cleanup))
        helper.render_results(results)
    passed=sum(r.passed for r in results)
    ok=passed==len(results)
    print(helper.colored('\n测试通过' if ok else '\n测试失败',helper.ANSI_GREEN if ok else helper.ANSI_RED))
    print(f"  生命周期: {'VERIFIED' if ok else 'READY_FOR_LIVE'}\n  结果    : {passed}/{len(results)} 通过\n  退出码  : {0 if ok else 1}")
    return 0 if ok else 1


if __name__ == '__main__':
    raise SystemExit(main())
