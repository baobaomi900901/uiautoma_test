r"""win32.set_ime(lang: str) -> None。

用途：切换当前脚本线程的输入布局语言。en/eng/english为英文，zh/cn/chinese为中文。
返回None；非法语言（含空、None、数字）InvalidParamsError。不是前台窗口布局，
不会改变其他线程；实现可能加载对应系统布局。脚本参数：--non-interactive统一参数。
运行：uv run .\win32\test_win32_set_ime.py --non-interactive
无需dev、靶场或元素库。脚本保存原生HKL，逐个测试六个别名，结束精确恢复原HKL。
测试期间不要切换输入法；不会卸载系统布局。只读语言标签外，set_ime本身会改变当前线程状态。
"""

import argparse
import ctypes
import inspect
import time
from ctypes import wintypes
from uiautoma import win32,InvalidParamsError
from test_win32_get_value import run_case,render_results,colored,ANSI_GREEN,ANSI_RED


def keyboard_api():
    u=ctypes.WinDLL('user32',use_last_error=True)
    u.GetKeyboardLayout.argtypes=[wintypes.DWORD];u.GetKeyboardLayout.restype=wintypes.HANDLE
    u.ActivateKeyboardLayout.argtypes=[wintypes.HANDLE,wintypes.UINT];u.ActivateKeyboardLayout.restype=wintypes.HANDLE
    return u


def contract():
    sig=inspect.signature(win32.set_ime)
    assert list(sig.parameters)==['lang'],sig
    p=sig.parameters['lang']
    assert p.default is p.empty and p.kind==p.POSITIONAL_OR_KEYWORD,sig
    assert sig.return_annotation in (None,'None',type(None)),sig
    return 'lang必填，支持位置参数，返回None'


def main():
    print('UIAutoma Win32 API 测试\n  API: win32.set_ime\n  范围: 当前脚本线程输入布局')
    print('  原生参照: GetKeyboardLayout/ActivateKeyboardLayout；测试结束恢复原HKL')
    results=[run_case('API 合同',contract)]
    u=keyboard_api();original=int(u.GetKeyboardLayout(0) or 0)
    started=time.perf_counter()
    def current(expected=None):
        value=win32.get_ime()
        assert type(value) is str and value,f'语言标签无效: {value!r}'
        if expected is not None: assert value==expected,f'预期{expected}，实际{value}'
        return value
    def alias(name,expected):
        returned=win32.set_ime(name)
        assert returned is None,returned
        value=current(expected)
        return f'{name}切换成功，返回None，当前标签为{value}',[f'原生HKL: 0x{int(u.GetKeyboardLayout(0) or 0):x}']
    def invalid(value):
        before=int(u.GetKeyboardLayout(0) or 0)
        try:win32.set_ime(value)
        except InvalidParamsError:pass
        else:raise AssertionError('非法语言未拒绝')
        assert int(u.GetKeyboardLayout(0) or 0)==before,'非法调用改变HKL'
        return 'InvalidParamsError正确拒绝，当前线程HKL未改变'
    def arguments():
        for call in (lambda:win32.set_ime(),lambda:win32.set_ime('en','x'),lambda:win32.set_ime('en',timeout=1)):
            try:call()
            except TypeError:pass
            else:raise AssertionError('参数数量错误未被TypeError拒绝')
        return '缺参、多余位置参数及timeout均TypeError拒绝'
    try:
        results.append(run_case('原始布局',lambda:('原始布局标签有效: '+current())))
        for name,expected in [('en','en'),('eng','en'),('english','en'),('zh','zh'),('cn','zh'),('chinese','zh')]:
            results.append(run_case('别名 '+name,lambda n=name,e=expected:alias(n,e)))
        results.append(run_case('重复切换',lambda:alias('zh','zh')))
        for value in ('', '  ', None, 123, 'jp'):
            results.append(run_case('非法 '+repr(value),lambda v=value:invalid(v)))
        results.append(run_case('调用参数边界',arguments))
    finally:
        def cleanup():
            if not u.ActivateKeyboardLayout(original,0):raise RuntimeError(f'原HKL恢复失败: 0x{original:x}')
            assert int(u.GetKeyboardLayout(0) or 0)==original,'原HKL恢复后核验不一致'
            return '原线程HKL已恢复并核验；未卸载输入法布局',[f'HKL: 0x{original:x}']
        results.append(run_case('资源清理',cleanup));render_results(results)
    passed=sum(r.passed for r in results);ok=passed==len(results)
    print(colored('\n测试通过' if ok else '\n测试失败',ANSI_GREEN if ok else ANSI_RED))
    print(f"  生命周期: {'VERIFIED' if ok else 'READY_FOR_LIVE'}\n  结果: {passed}/{len(results)} 通过\n  总耗时: {(time.perf_counter()-started)*1000:.1f}ms\n  退出码: {0 if ok else 1}")
    return 0 if ok else 1


if __name__=='__main__':
    parser=argparse.ArgumentParser(description='当前线程输入布局切换测试')
    parser.add_argument('--non-interactive',action='store_true',help='统一批量参数；始终不等待人工')
    parser.parse_args()
    raise SystemExit(main())
