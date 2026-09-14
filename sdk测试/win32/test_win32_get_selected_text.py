r"""win32.get_selected_text(wait_time=0, **kwargs) -> str。

用途：读取当前前台控件中被选中的文本；内部发送Ctrl+C，并恢复调用前剪贴板文本。
wait_time可位置/关键字，默认0；kwargs当前实现兼容并忽略未知键。返回str，无选中时""。
脚本参数：--non-interactive统一参数；本脚本不等待人工。运行：
uv run .\win32\test_win32_get_selected_text.py --non-interactive
自动启动临时记事本，写入临时文本并用原生EM_SETSEL选择；测试期间不要操作键盘鼠标。
原生通过CF_UNICODETEXT独立核对；记录并恢复原剪贴板文本。结束关闭临时记事本。
不使用靶场、元素库，不覆盖非文本选择、跨进程权限、剪贴板持续占用等场景。
"""

import argparse
import ctypes
import inspect
import argparse
import subprocess
import tempfile
import time
from ctypes import wintypes
from pathlib import Path

from uiautoma import win32
import test_win32_get_value as helper
from test_win32_clipboard_set_text import native_retry,read_clipboard_text,write_clipboard_text

WM_SETTEXT=0x000C
EM_SETSEL=0x00B1


def contract():
    sig=inspect.signature(win32.get_selected_text)
    assert list(sig.parameters)==['wait_time','kwargs'],sig
    assert sig.parameters['wait_time'].default==0 and sig.parameters['wait_time'].kind==inspect.Parameter.POSITIONAL_OR_KEYWORD,sig
    assert sig.parameters['kwargs'].kind==inspect.Parameter.VAR_KEYWORD,sig
    assert str(sig.return_annotation) in ('str',"<class 'str'>"),sig
    return 'wait_time默认0，兼容任意关键字，返回str'


def api():
    u=ctypes.WinDLL('user32',use_last_error=True)
    for name in ('EnumWindows','EnumChildWindows'):
        getattr(u,name).restype=wintypes.BOOL
    u.GetWindowThreadProcessId.argtypes=[wintypes.HWND,ctypes.POINTER(wintypes.DWORD)]
    u.GetWindowThreadProcessId.restype=wintypes.DWORD
    u.GetClassNameW.argtypes=[wintypes.HWND,wintypes.LPWSTR,ctypes.c_int]
    u.GetClassNameW.restype=ctypes.c_int
    u.GetForegroundWindow.restype=wintypes.HWND
    u.SetForegroundWindow.argtypes=[wintypes.HWND]
    u.SetForegroundWindow.restype=wintypes.BOOL
    u.SetFocus.argtypes=[wintypes.HWND]
    u.SetFocus.restype=wintypes.HWND
    u.SendMessageW.argtypes=[wintypes.HWND,wintypes.UINT,wintypes.WPARAM,wintypes.LPARAM]
    u.SendMessageW.restype=wintypes.LPARAM
    u.IsWindow.argtypes=[wintypes.HWND]
    u.IsWindow.restype=wintypes.BOOL
    return u


def find_edit(user32,pid,title_token):
    found=[]
    callback=ctypes.WINFUNCTYPE(wintypes.BOOL,wintypes.HWND,wintypes.LPARAM)
    @callback
    def visit(hwnd,unused):
        owner=wintypes.DWORD();user32.GetWindowThreadProcessId(hwnd,ctypes.byref(owner))
        buf=ctypes.create_unicode_buffer(128); n=user32.GetClassNameW(hwnd,buf,len(buf))
        if buf.value[:n].casefold() in ('edit','richedit50w','richeditd2dpt'):
            found.append(int(hwnd))
        return True
    user32.EnumWindows.argtypes=[callback,wintypes.LPARAM]
    # enumerate all top-level windows, then children of those owned by the process
    user32.GetWindowTextLengthW.argtypes=[wintypes.HWND]
    user32.GetWindowTextLengthW.restype=ctypes.c_int
    user32.GetWindowTextW.argtypes=[wintypes.HWND,wintypes.LPWSTR,ctypes.c_int]
    user32.GetWindowTextW.restype=ctypes.c_int
    @callback
    def tops(hwnd,unused):
        owner=wintypes.DWORD();user32.GetWindowThreadProcessId(hwnd,ctypes.byref(owner))
        length=user32.GetWindowTextLengthW(hwnd)
        title=ctypes.create_unicode_buffer(length+1)
        user32.GetWindowTextW(hwnd,title,len(title))
        # Win11记事本可能由独立进程承载，PID只作优先条件，文件名是稳定识别线索。
        if owner.value==pid or title_token.casefold() in title.value.casefold():
            user32.EnumChildWindows.argtypes=[wintypes.HWND,callback,wintypes.LPARAM]
            user32.EnumChildWindows(hwnd,visit,0)
        return True
    user32.EnumWindows(tops,0)
    if not found:raise RuntimeError('未找到记事本Edit控件')
    return found[0]


def write_and_select(user32,edit,text,start,end):
    buf=ctypes.create_unicode_buffer(text)
    assert user32.SendMessageW(edit,WM_SETTEXT,0,ctypes.cast(buf,ctypes.c_void_p).value)==1
    user32.SetFocus(edit)
    user32.SendMessageW(edit,EM_SETSEL,start,end)


def main():
    print('UIAutoma Win32 API 测试\n  API: win32.get_selected_text\n  对象: 临时记事本Edit')
    print('  原生参照: EM_SETSEL准备选择 + CF_UNICODETEXT读回 + 剪贴板恢复')
    results=[helper.run_case('API 合同',contract)]
    original=None;process=None;edit=0;temporary=None
    user32=api();foreground=int(user32.GetForegroundWindow() or 0)
    started=time.perf_counter()
    def prepare():
        nonlocal original,process,edit,temporary
        available,original=native_retry(read_clipboard_text)
        if not available:raise RuntimeError('请先复制普通文本，供测试结束恢复')
        temporary=tempfile.NamedTemporaryFile(prefix='uiautoma-selected-',suffix='.txt',delete=False,
                                               mode='w',encoding='utf-8',newline='')
        temporary.write('UIAutoma Selected 文本\r\n第二行😀✓')
        temporary.close()
        process=subprocess.Popen(['notepad.exe',temporary.name])
        deadline=time.monotonic()+5
        while time.monotonic()<deadline:
            try:edit=find_edit(user32,process.pid,Path(temporary.name).name);break
            except RuntimeError:time.sleep(0.05)
        if not edit:raise RuntimeError('记事本Edit未就绪')
        return '临时记事本Edit已就绪，文本可独立选择',[f'PID: {process.pid}；Edit: {edit}']
    def selected(start,end,wait=0,kwargs=None):
        text='UIAutoma Selected 文本\r\n第二行😀✓'
        write_and_select(user32,edit,text,start,end)
        before=native_retry(read_clipboard_text)
        value=win32.get_selected_text(wait,**(kwargs or {}))
        after=native_retry(read_clipboard_text)
        expected=text[start:end]
        assert type(value) is str and value==expected,f'预期{expected!r}，实际{value!r}'
        assert after==before,f'API未恢复原剪贴板：{after!r}'
        return f'返回选中文本{value!r}，且剪贴板已恢复'
    def no_selection():
        text='UIAutoma Selected 文本\r\n第二行😀✓';write_and_select(user32,edit,text,0,0)
        before=native_retry(read_clipboard_text);value=win32.get_selected_text();after=native_retry(read_clipboard_text)
        assert value=='' and after==before,f'无选中预期空字符串；实际值={value!r}；调用前剪贴板={before!r}；调用后剪贴板={after!r}'
        return '无选中时返回空字符串，剪贴板恢复'
    def repeated():
        for _ in range(3): selected(0,7)
        return '连续三次读取一致'
    def arguments():
        text='UIAutoma Selected 文本\r\n第二行😀✓'
        write_and_select(user32,edit,text,0,7)
        before=native_retry(read_clipboard_text)
        assert win32.get_selected_text(0,ignored=True)=='UIAutom'
        assert native_retry(read_clipboard_text)==before
        for call in (lambda:win32.get_selected_text('bad'),lambda:win32.get_selected_text(None)):
            try:call()
            except (ValueError,TypeError):pass
            else:raise AssertionError('非法wait_time未拒绝')
        return '未知关键字被兼容忽略；非法wait_time拒绝'
    try:
        ready=helper.run_case('测试准备',prepare);results.append(ready)
        if ready.passed:
            results += [helper.run_case('全文选择',lambda:selected(0,27)),helper.run_case('部分选择',lambda:selected(0,8)),
                        helper.run_case('Unicode选择',lambda:selected(25,29)),helper.run_case('零等待',lambda:selected(0,7,0)),
                        helper.run_case('有限等待',lambda:selected(0,7,0.1)),helper.run_case('无选中',no_selection),
                        helper.run_case('重复读取',repeated),helper.run_case('关键字兼容',arguments)]
    finally:
        def cleanup():
            errors=[]
            if original is not None:
                try: native_retry(lambda:write_clipboard_text(original))
                except Exception as exc:errors.append(f'剪贴板: {exc}')
            if process is not None:
                try: process.terminate();process.wait(timeout=3)
                except Exception as exc:errors.append(f'记事本: {exc}')
            if temporary is not None:
                try:
                    if not temporary.file.closed:
                        temporary.close()
                    Path(temporary.name).unlink(missing_ok=True)
                except Exception as exc:errors.append(f'临时文件: {exc}')
            if errors:raise RuntimeError('；'.join(errors))
            return '原剪贴板、记事本和临时文件已清理'
        results.append(helper.run_case('资源清理',cleanup));helper.render_results(results)
    passed=sum(r.passed for r in results);ok=passed==len(results)
    print(helper.colored('\n测试通过' if ok else '\n测试失败',helper.ANSI_GREEN if ok else helper.ANSI_RED))
    print(f'  生命周期: READY_FOR_LIVE\n  结果: {passed}/{len(results)} 通过\n  总耗时: {(time.perf_counter()-started)*1000:.1f}ms\n  退出码: {0 if ok else 1}')
    return 0 if ok else 1


if __name__=='__main__':
    parser=argparse.ArgumentParser(description='Win32当前选中文本测试')
    parser.add_argument('--non-interactive',action='store_true',help='统一批量参数；始终不等待人工')
    parser.parse_args();raise SystemExit(main())
