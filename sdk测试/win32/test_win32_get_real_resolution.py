r"""win32.get_real_resolution()：无参数，返回虚拟桌面(width,height)正整数元组。

用途：取得多显示器桌面的整体包围尺寸，不是单个显示器的最高硬件分辨率。
与get_screen_size()的主屏尺寸不同；只返回宽高，不返回虚拟桌面原点。
脚本参数：--non-interactive用于统一批量命令；本脚本始终只读且不等待人工。
运行：uv run .\win32\test_win32_get_real_resolution.py --non-interactive
无需dev、靶场、元素库。当前SDK直接读取Windows指标；测试期间不要调整显示设置。
独立枚举显示器边界取包围矩形，与GetSystemMetrics虚拟桌面指标及SDK结果交叉核验。
Per-Monitor v2，复用get_screen_size的原生枚举和结果格式辅助；不调用其他SDK屏幕API。
"""

import argparse
import inspect
import time
from uiautoma import win32
import test_win32_get_value as helper
from test_win32_get_screen_size import native_sizes,valid_size


def bounding_desktop(monitors):
    rects=[m['rect'] for m in monitors]
    if not rects:raise ValueError('没有显示器')
    left=min(r[0] for r in rects)
    top=min(r[1] for r in rects)
    right=max(r[0]+r[2] for r in rects)
    bottom=max(r[1]+r[3] for r in rects)
    return left,top,right-left,bottom-top


def contract():
    sig=inspect.signature(win32.get_real_resolution)
    assert not sig.parameters,sig
    return '无公开参数，实际返回类型通过调用核验'


def main():
    print('UIAutoma Win32 API 测试\n  API: win32.get_real_resolution')
    print(f'  DPI模式: {helper.DPI_AWARENESS_MODE}\n  范围: 虚拟桌面包围尺寸，包含全部显示器')
    results=[helper.run_case('API 合同',contract)]
    reference=None
    returned=None
    started=time.perf_counter()
    def prepare():
        nonlocal reference
        reference=native_sizes()
        primary,metrics,virtual,monitors=reference
        union=bounding_desktop(monitors)
        assert virtual==union,f'显示器包围边界{union}与虚拟桌面指标{virtual}不符'
        valid_size(union[2:])
        return '显示器包围矩形与原生虚拟桌面指标一致',[f'虚拟桌面(x,y,w,h): {virtual}；主屏: {primary}',f'显示器: {monitors}']
    def read():
        nonlocal returned
        returned=win32.get_real_resolution()
        valid_size(returned)
        return '返回正整数(width,height)元组',[f'实际: {returned}']
    def compare():
        assert native_sizes()==reference,'读取期间显示配置变化'
        expected=bounding_desktop(reference[3])[2:]
        assert returned==expected,f'预期虚拟桌面{expected}，实际{returned}；主屏{reference[0]}'
        return 'SDK结果与全部显示器包围宽高一致',[f'预期: {expected}；实际: {returned}']
    def repeat():
        for _ in range(3):
            value=win32.get_real_resolution()
            valid_size(value)
            assert value==reference[2][2:],value
        assert native_sizes()==reference,'重复读取期间显示配置变化'
        return '连续三次均与虚拟桌面尺寸一致'
    def arguments():
        for call in (lambda:win32.get_real_resolution(0),lambda:win32.get_real_resolution(timeout=1)):
            try:call()
            except TypeError:pass
            else:raise AssertionError('多余参数未被拒绝')
        return '位置参数和timeout均被TypeError拒绝'
    ready=helper.run_case('原生显示器参照',prepare)
    results.append(ready)
    if ready.passed:
        outcome=helper.run_case('返回类型',read)
        results.append(outcome)
        if outcome.passed:results.append(helper.run_case('虚拟桌面一致',compare))
        results.append(helper.run_case('重复读取',repeat))
    results.append(helper.run_case('参数限制',arguments))
    results.append(helper.run_case('资源清理',lambda:'只读，未修改显示设置或创建待清理资源'))
    helper.render_results(results)
    passed=sum(r.passed for r in results)
    ok=passed==len(results)
    print(helper.colored('\n测试通过' if ok else '\n测试失败',helper.ANSI_GREEN if ok else helper.ANSI_RED))
    print(f"  生命周期: {'VERIFIED' if ok else 'READY_FOR_LIVE'}\n  结果: {passed}/{len(results)} 通过\n  总耗时: {(time.perf_counter()-started)*1000:.1f}ms\n  退出码: {0 if ok else 1}")
    return 0 if ok else 1


if __name__=='__main__':
    parser=argparse.ArgumentParser(description='只读验证虚拟桌面分辨率')
    parser.add_argument('--non-interactive',action='store_true',help='统一批量参数；始终不等待人工')
    parser.parse_args()
    raise SystemExit(main())
