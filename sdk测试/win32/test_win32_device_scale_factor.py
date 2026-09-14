r"""win32.GetDeviceScaleFactor(scale_percent) -> float（实际返回类型，源码无注解）。

用途：把百分比除以100，例如225返回2.25；不读取/修改系统显示缩放。
API参数scale_percent必填，支持位置/关键字。正整数、小数、可转换数字字符串可用；
零/负数及不能转换为数字的值应被InvalidParamsError拒绝。没有timeout参数。
脚本参数：--non-interactive统一批量参数；始终无人工交互。
运行：uv run .\win32\test_win32_device_scale_factor.py --non-interactive
无需dev、元素库或靶场，纯数值测试。未覆盖NaN/Infinity、布尔值等非典型输入。
"""

import argparse
import inspect
import math
import time
from uiautoma import win32, InvalidParamsError
from test_win32_get_value import run_case, render_results, colored, ANSI_GREEN, ANSI_RED


def contract():
    sig=inspect.signature(win32.GetDeviceScaleFactor)
    assert list(sig.parameters)==['scale_percent'],sig
    p=sig.parameters['scale_percent']
    assert p.default is p.empty and p.kind==p.POSITIONAL_OR_KEYWORD,sig
    return 'scale_percent必填，支持位置/关键字；返回类型实测核验'


def conversion(value,expected,keyword=False):
    actual=(win32.GetDeviceScaleFactor(scale_percent=value) if keyword
            else win32.GetDeviceScaleFactor(value))
    assert type(actual) is float and math.isclose(actual,expected,rel_tol=1e-12,abs_tol=1e-12),f'输入{value!r}，预期{expected!r}，实际{actual!r}'
    return '返回float，百分比转换正确',[f'输入: {value!r}；预期: {expected}；实际: {actual}']


def rejected(call,error):
    try:call()
    except error:return f'{error.__name__}正确拒绝'
    raise AssertionError(f'未抛出{error.__name__}')


def main():
    print('UIAutoma Win32 API 测试\n  API: win32.GetDeviceScaleFactor')
    print('  用途: 缩放百分比 → 比例因子；不读取或修改系统缩放')
    started=time.perf_counter()
    results=[run_case('API 合同',contract)]
    for value,expected in [(100,1.0),(125,1.25),(150,1.5),(175,1.75),(200,2.0),
                           (225,2.25),(250,2.5),(137.5,1.375),(0.5,0.005),('150',1.5),(' 125 ',1.25)]:
        results.append(run_case(f'转换{value!r}',lambda v=value,e=expected:conversion(v,e)))
    results.append(run_case('关键字参数',lambda:conversion(225,2.25,True)))
    for name,value in [('零',0),('负数',-100),('非数字','bad'),('百分号字符串','125%'),('None',None),('空字符串','')]:
        results.append(run_case('拒绝'+name,lambda v=value:rejected(lambda:win32.GetDeviceScaleFactor(v),InvalidParamsError)))
    def arguments():
        for call in (lambda:win32.GetDeviceScaleFactor(),lambda:win32.GetDeviceScaleFactor(100,200),lambda:win32.GetDeviceScaleFactor(100,timeout=1)):
            rejected(call,TypeError)
        return '缺参、多余位置参数和timeout被TypeError拒绝'
    results.append(run_case('调用参数边界',arguments))
    results.append(run_case('资源清理',lambda:'纯数值测试，无窗口/文件/剪贴板改动，无待清理资源'))
    render_results(results)
    passed=sum(r.passed for r in results)
    ok=passed==len(results)
    print(colored('\n测试通过' if ok else '\n测试失败',ANSI_GREEN if ok else ANSI_RED))
    print(f"  生命周期: {'VERIFIED' if ok else 'READY_FOR_LIVE'}\n  结果: {passed}/{len(results)} 通过\n  总耗时: {(time.perf_counter()-started)*1000:.1f}ms\n  退出码: {0 if ok else 1}")
    return 0 if ok else 1


if __name__=='__main__':
    parser=argparse.ArgumentParser(description='缩放百分比转换测试，无需dev或靶场')
    parser.add_argument('--non-interactive',action='store_true',help='统一批量参数；始终不等待人工')
    parser.parse_args()
    raise SystemExit(main())
