r"""win32.get_ime() -> str，无API参数。

用途：读取调用线程的键盘布局语言；英文(0409)返回en，中文语言ID返回zh，其他返回0x语言ID。
不是前台窗口布局或中文输入法内部中英模式。脚本用原生GetKeyboardLayout核对。
原生ActivateKeyboardLayout仅在当前脚本线程激活已加载布局，结束恢复原HKL，不加载新输入法。
脚本参数：--non-interactive统一批量参数，始终无人工等待。
运行：uv run .\win32\test_win32_get_ime.py --non-interactive
无需dev、靶场、元素库，不用剪贴板。只验证本机已经加载的布局，不假定必有英文或中文。
"""

import argparse
import ctypes
import inspect
import time
from ctypes import wintypes
from uiautoma import win32
from test_win32_get_value import run_case,render_results,colored,ANSI_GREEN,ANSI_RED


def keyboard_api():
    u=ctypes.WinDLL('user32',use_last_error=True)
    u.GetKeyboardLayout.argtypes=[wintypes.DWORD]
    u.GetKeyboardLayout.restype=wintypes.HANDLE
    u.GetKeyboardLayoutList.argtypes=[ctypes.c_int,ctypes.POINTER(wintypes.HANDLE)]
    u.GetKeyboardLayoutList.restype=ctypes.c_int
    u.ActivateKeyboardLayout.argtypes=[wintypes.HANDLE,wintypes.UINT]
    u.ActivateKeyboardLayout.restype=wintypes.HANDLE
    return u


def expected_language(hkl):
    language=hkl&0xffff
    if language==0x0409:return 'en'
    if language in (0x0804,0x0404,0x0c04,0x1004,0x1404):return 'zh'
    return f'0x{language:04x}'


def contract():
    sig=inspect.signature(win32.get_ime)
    assert not sig.parameters,sig
    assert str(sig.return_annotation) in ('str',"<class 'str'>"),sig
    return '无公开参数，返回str'


def main():
    print('UIAutoma Win32 API 测试\n  API: win32.get_ime\n  范围: 当前脚本线程布局，不是前台窗口IME模式')
    native=keyboard_api()
    original=int(native.GetKeyboardLayout(0) or 0)
    layouts=[]
    results=[run_case('API 合同',contract)]
    started=time.perf_counter()
    def prepare():
        assert original,'原线程HKL无效'
        count=native.GetKeyboardLayoutList(0,None)
        assert count>0,'未读到已加载键盘布局'
        buffer=(wintypes.HANDLE*count)()
        actual=native.GetKeyboardLayoutList(count,buffer)
        assert 0<actual<=count,'读取布局列表失败'
        layouts.extend(dict.fromkeys(int(v) for v in buffer[:actual] if v))
        return '原布局及已加载布局已读取',[f'原HKL: 0x{original:x}',f'已加载: {[hex(v) for v in layouts]}']
    def observe():
        before=int(native.GetKeyboardLayout(0) or 0)
        assert before,'当前HKL无效'
        expected=expected_language(before)
        actual=win32.get_ime()
        assert type(actual) is str and actual==expected,f'HKL=0x{before:x}，预期{expected!r}，实际{actual!r}'
        assert int(native.GetKeyboardLayout(0) or 0)==before,'读取改变了线程布局'
        return 'SDK语言与原生HKL一致，读取未改变布局',[f'HKL: 0x{before:x}；预期: {expected}；实际: {actual}']
    def activate(hkl):
        if not native.ActivateKeyboardLayout(hkl,0):raise OSError('激活已加载布局失败')
        assert int(native.GetKeyboardLayout(0) or 0)==hkl,'实际HKL与请求不符'
    def layout_case(hkl):
        activate(hkl)
        return observe()
    def repeated():
        for _ in range(5):observe()
        return '连续五次与原生线程HKL一致'
    def arguments():
        for call in (lambda:win32.get_ime(0),lambda:win32.get_ime(timeout=1)):
            try:call()
            except TypeError:pass
            else:raise AssertionError('额外参数未拒绝')
        return '位置参数和timeout均被TypeError拒绝'
    try:
        ready=run_case('布局准备',prepare)
        results.append(ready)
        if ready.passed:
            results.append(run_case('初始布局读取',observe))
            for hkl in layouts:results.append(run_case(f'布局0x{hkl&0xffff:04x}',lambda h=hkl:layout_case(h)))
            results.append(run_case('重复读取',repeated))
            results.append(run_case('参数限制',arguments))
    finally:
        def cleanup():
            if original:
                activate(original)
                assert int(native.GetKeyboardLayout(0) or 0)==original,'原HKL未恢复'
            return '当前线程原HKL已恢复并核验；未安装或卸载输入法'
        results.append(run_case('资源清理',cleanup))
        render_results(results)
    passed=sum(r.passed for r in results);ok=passed==len(results)
    print(colored('\n测试通过' if ok else '\n测试失败',ANSI_GREEN if ok else ANSI_RED))
    print(f"  生命周期: {'VERIFIED' if ok else 'READY_FOR_LIVE'}\n  结果: {passed}/{len(results)} 通过\n  总耗时: {(time.perf_counter()-started)*1000:.1f}ms\n  退出码: {0 if ok else 1}")
    return 0 if ok else 1


if __name__=='__main__':
    parser=argparse.ArgumentParser(description='当前线程键盘布局读取测试')
    parser.add_argument('--non-interactive',action='store_true',help='统一批量参数；始终不等待人工')
    parser.parse_args();raise SystemExit(main())
