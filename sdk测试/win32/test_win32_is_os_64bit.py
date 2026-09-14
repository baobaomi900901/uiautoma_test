r"""win32.is_os_64bit() -> bool：判断操作系统而非当前Python进程是否为64位。

无API参数，无副作用。脚本参数：--non-interactive统一批量参数；始终不等待人工。
运行：uv run .\win32\test_win32_is_os_64bit.py --non-interactive
无需dev、靶场或元素库。使用Windows GetNativeSystemInfo独立读取OS架构，并与SDK、
PROCESSOR_ARCHITEW6432及platform信息交叉展示。32位Python运行在64位Windows时，
独立参照仍应为True。重复读取验证稳定性；不修改环境变量或系统设置。
"""

import argparse
import ctypes
import inspect
import os
import platform
import time
from ctypes import wintypes
from uiautoma import win32
from test_win32_get_value import run_case,render_results,colored,ANSI_GREEN,ANSI_RED


class SYSTEM_INFO(ctypes.Structure):
    _fields_=[('wProcessorArchitecture',wintypes.WORD),('wReserved',wintypes.WORD),
              ('dwPageSize',wintypes.DWORD),('lpMinimumApplicationAddress',ctypes.c_void_p),
              ('lpMaximumApplicationAddress',ctypes.c_void_p),('dwActiveProcessorMask',ctypes.c_size_t),
              ('dwNumberOfProcessors',wintypes.DWORD),('dwProcessorType',wintypes.DWORD),
              ('dwAllocationGranularity',wintypes.DWORD),('wProcessorLevel',wintypes.WORD),
              ('wProcessorRevision',wintypes.WORD)]


def native_os_64bit():
    user32=ctypes.WinDLL('kernel32',use_last_error=True)
    user32.GetNativeSystemInfo.argtypes=[ctypes.POINTER(SYSTEM_INFO)]
    user32.GetNativeSystemInfo.restype=None
    info=SYSTEM_INFO();user32.GetNativeSystemInfo(ctypes.byref(info))
    names={0:'INTEL',5:'ARM',6:'IA64',9:'AMD64',12:'ARM64'}
    arch=names.get(info.wProcessorArchitecture,str(info.wProcessorArchitecture))
    return arch in {'AMD64','IA64','ARM64'},arch


def contract():
    sig=inspect.signature(win32.is_os_64bit)
    assert not sig.parameters,sig
    assert str(sig.return_annotation) in ('bool',"<class 'bool'>"),sig
    return '无公开参数，返回bool'


def main():
    print('UIAutoma Win32 API 测试\n  API: win32.is_os_64bit\n  原生参照: GetNativeSystemInfo')
    results=[run_case('API 合同',contract)]
    started=time.perf_counter()
    def read():
        expected,arch=native_os_64bit()
        actual=win32.is_os_64bit()
        assert type(actual) is bool and actual==expected,f'原生架构{arch}预期{expected}，SDK实际{actual}'
        return 'SDK结果与原生OS架构一致',[f'OS架构: {arch}；SDK: {actual}；platform.machine: {platform.machine()!r}',f'PROCESSOR_ARCHITEW6432: {os.environ.get("PROCESSOR_ARCHITEW6432","")!r}']
    results.append(run_case('原生架构交叉校验',read))
    def repeat():
        values=[win32.is_os_64bit() for _ in range(5)]
        assert all(type(v) is bool for v in values) and len(set(values))==1,values
        return '连续五次返回相同bool值',[f'结果: {values[0]}']
    results.append(run_case('重复读取',repeat))
    def arguments():
        for call in (lambda:win32.is_os_64bit(1),lambda:win32.is_os_64bit(timeout=1)):
            try:call()
            except TypeError:pass
            else:raise AssertionError('多余参数未被TypeError拒绝')
        return '位置参数和timeout均TypeError拒绝'
    results.append(run_case('参数限制',arguments))
    results.append(run_case('资源清理',lambda:'纯环境查询，未修改系统或文件'))
    render_results(results)
    passed=sum(r.passed for r in results);ok=passed==len(results)
    print(colored('\n测试通过' if ok else '\n测试失败',ANSI_GREEN if ok else ANSI_RED))
    print(f"  生命周期: {'VERIFIED' if ok else 'READY_FOR_LIVE'}\n  结果: {passed}/{len(results)} 通过\n  总耗时: {(time.perf_counter()-started)*1000:.1f}ms\n  退出码: {0 if ok else 1}")
    return 0 if ok else 1


if __name__=='__main__':
    parser=argparse.ArgumentParser(description='只读验证Windows操作系统架构')
    parser.add_argument('--non-interactive',action='store_true',help='统一批量参数；始终不等待人工')
    parser.parse_args()
    raise SystemExit(main())
