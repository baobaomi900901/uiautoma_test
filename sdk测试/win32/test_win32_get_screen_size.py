r"""win32.get_screen_size() -> tuple[int,int]（当前高层函数没有返回注解）。

用途：读取主屏幕像素宽高，不是所有显示器的虚拟桌面宽高，无API参数。
额外位置参数、timeout关键字应抛TypeError。
脚本参数：--non-interactive 接受该参数以统一批量命令；本脚本本身不等待人工。
运行：uv run .\win32\test_win32_get_screen_size.py --non-interactive
无需靶场/元素库；建议dev运行。API可能在Runtime不可用时走原生回退，本轮不强制区分路径。
启用Per-Monitor v2；以EnumDisplayMonitors/GetMonitorInfoW主屏边界和GetSystemMetrics交叉核验。
只读，不修改显示设置、不移动鼠标、不创建窗口；测试期间不要更改显示器配置。
"""

import argparse
import ctypes
import inspect
import time
from ctypes import wintypes
from uiautoma import win32
import test_win32_get_value as helper


class MonitorInfo(ctypes.Structure):
    _fields_=[('cbSize',wintypes.DWORD),('rcMonitor',wintypes.RECT),
              ('rcWork',wintypes.RECT),('dwFlags',wintypes.DWORD)]


def native_sizes():
    user32=ctypes.WinDLL('user32',use_last_error=True)
    callback_type=ctypes.WINFUNCTYPE(wintypes.BOOL,wintypes.HANDLE,wintypes.HDC,ctypes.POINTER(wintypes.RECT),wintypes.LPARAM)
    user32.EnumDisplayMonitors.argtypes=[wintypes.HDC,ctypes.POINTER(wintypes.RECT),callback_type,wintypes.LPARAM]
    user32.EnumDisplayMonitors.restype=wintypes.BOOL
    user32.GetMonitorInfoW.argtypes=[wintypes.HANDLE,ctypes.POINTER(MonitorInfo)]
    user32.GetMonitorInfoW.restype=wintypes.BOOL
    user32.GetSystemMetrics.argtypes=[ctypes.c_int]
    user32.GetSystemMetrics.restype=ctypes.c_int
    monitors=[]
    errors=[]
    @callback_type
    def visit(handle,dc,rect,data):
        info=MonitorInfo()
        info.cbSize=ctypes.sizeof(info)
        if not user32.GetMonitorInfoW(handle,ctypes.byref(info)):
            errors.append(ctypes.get_last_error())
            return False
        r=info.rcMonitor
        monitors.append(dict(primary=bool(info.dwFlags&1),rect=(r.left,r.top,r.right-r.left,r.bottom-r.top)))
        return True
    if not user32.EnumDisplayMonitors(None,None,visit,0) or errors:
        raise OSError(f'原生显示器枚举失败: {errors}')
    primary=[m['rect'][2:] for m in monitors if m['primary']]
    assert len(primary)==1,f'主屏数量不符: {monitors}'
    metrics=(user32.GetSystemMetrics(0),user32.GetSystemMetrics(1))
    virtual=tuple(user32.GetSystemMetrics(i) for i in (76,77,78,79))
    assert all(v>0 for v in primary[0]),primary
    return primary[0],metrics,virtual,monitors


def valid_size(value):
    assert type(value) is tuple and len(value)==2 and all(type(v) is int and v>0 for v in value),f'预期正整数二元组，实际{value!r}'


def contract():
    sig=inspect.signature(win32.get_screen_size)
    assert not sig.parameters,sig
    return '无公开参数，返回类型通过实际调用核验'


def main():
    print('UIAutoma Win32 API 测试\n  API: win32.get_screen_size')
    print(f'  DPI模式: {helper.DPI_AWARENESS_MODE}\n  范围: 主屏，不是虚拟桌面；只读检查')
    results=[helper.run_case('API 合同',contract)]
    reference=None
    returned=None
    started=time.perf_counter()
    def prepare():
        nonlocal reference
        reference=native_sizes()
        primary,metrics,virtual,monitors=reference
        assert primary==metrics,f'原生主屏边界{primary}与系统指标{metrics}不符'
        return '两种原生主屏尺寸一致',[f'主屏: {primary}；虚拟桌面(x,y,w,h): {virtual}',f'显示器: {monitors}']
    def read():
        nonlocal returned
        returned=win32.get_screen_size()
        valid_size(returned)
        return '返回正整数(width,height)元组',[f'实际: {returned}']
    def compare():
        assert native_sizes()==reference,'读取期间显示器配置发生变化'
        assert returned==reference[0],f'主屏预期{reference[0]}，SDK实际{returned}；虚拟桌面{reference[2]}'
        return 'SDK宽高与原生主屏一致',[f'预期: {reference[0]}；实际: {returned}']
    def repeat():
        for _ in range(3):
            value=win32.get_screen_size()
            valid_size(value)
            assert value==reference[0],value
        assert native_sizes()==reference,'重复读取期间显示配置变化'
        return '连续三次均返回原生主屏尺寸'
    def arguments():
        for call in (lambda:win32.get_screen_size(0),lambda:win32.get_screen_size(timeout=1)):
            try:call()
            except TypeError:pass
            else:raise AssertionError('多余参数未被拒绝')
        return '位置参数和timeout关键字被TypeError拒绝'
    ready=helper.run_case('原生显示器参照',prepare)
    results.append(ready)
    if ready.passed:
        read_result=helper.run_case('返回类型',read)
        results.append(read_result)
        if read_result.passed:results.append(helper.run_case('主屏尺寸一致',compare))
        results.append(helper.run_case('重复读取',repeat))
    results.append(helper.run_case('参数限制',arguments))
    results.append(helper.run_case('资源清理',lambda:'只读测试，未创建窗口/文件，无待清理资源'))
    helper.render_results(results)
    passed=sum(r.passed for r in results)
    ok=passed==len(results)
    print(helper.colored('\n测试通过' if ok else '\n测试失败',helper.ANSI_GREEN if ok else helper.ANSI_RED))
    print(f"  生命周期: {'VERIFIED' if ok else 'READY_FOR_LIVE'}\n  结果: {passed}/{len(results)} 通过\n  总耗时: {(time.perf_counter()-started)*1000:.1f}ms\n  退出码: {0 if ok else 1}")
    return 0 if ok else 1


if __name__=='__main__':
    parser=argparse.ArgumentParser(description='只读验证主屏尺寸')
    parser.add_argument('--non-interactive',action='store_true',help='统一批量参数；本脚本始终不等待人工')
    parser.parse_args()
    raise SystemExit(main())
