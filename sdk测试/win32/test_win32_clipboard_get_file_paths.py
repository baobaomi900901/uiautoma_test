r"""仅测试 uiautoma.win32.clipboard.get_file_paths() -> list[str]。

API 参数：无；返回剪贴板文件/目录路径列表，没有文件路径时返回[]。
额外位置参数和timeout关键字应抛出TypeError。
脚本参数：无。运行：uv run .\win32\test_win32_clipboard_get_file_paths.py
前置：dev运行、先复制普通文本；无需靶场或元素库。
原生构造CF_HDROP，DragQueryFileW独立核验；不调用SDK set_files、clear或get_text。
自动创建临时文件/目录；结束时恢复原Unicode文本并删除临时目录。
只保护原Unicode文本，不保护富文本、图片等其他格式；测试期间不要复制/粘贴。
原生辅助有限重试，被测SDK不重试。依赖同目录其他clipboard测试中的辅助函数。
"""

import ctypes
import inspect
import tempfile
import time
from pathlib import Path

from uiautoma import win32
from test_win32_clipboard_set_files import native_files
from test_win32_clipboard_get_text import native_clear
from test_win32_clipboard_input import _clipboard_api
from test_win32_clipboard_set_text import (
    native_retry, read_clipboard_text, write_clipboard_text,
    run_case, render_results, colored, ANSI_GREEN, ANSI_RED,
)


def drop_payload(paths):
    # DROPFILES: pFiles=20, POINT=(0,0), fNC=0, fWide=1。
    header = b''.join(v.to_bytes(4,'little') for v in (20,0,0,0,1))
    return header + ('\0'.join(paths)+'\0\0').encode('utf-16le')


def write_native_files(paths):
    user32, kernel32 = _clipboard_api()
    data = drop_payload(paths)
    handle = kernel32.GlobalAlloc(2,len(data))
    if not handle:
        raise OSError('GlobalAlloc失败')
    opened = False
    try:
        pointer = kernel32.GlobalLock(handle)
        if not pointer:
            raise OSError('GlobalLock失败')
        try:
            ctypes.memmove(pointer,data,len(data))
        finally:
            kernel32.GlobalUnlock(handle)
        if not user32.OpenClipboard(None):
            raise OSError(f'OpenClipboard失败：{ctypes.get_last_error()}')
        opened = True
        if not user32.EmptyClipboard():
            raise OSError('EmptyClipboard失败')
        if not user32.SetClipboardData(15,handle):
            raise OSError('SetClipboardData(CF_HDROP)失败')
        handle = None  # 成功后所有权属于系统。
    finally:
        if opened:
            user32.CloseClipboard()
        if handle:
            kernel32.GlobalFree(handle)


def contract():
    sig = inspect.signature(win32.clipboard.get_file_paths)
    assert not sig.parameters and str(sig.return_annotation)=='list[str]', sig
    return '无公开参数，返回list[str]'


def main():
    print('UIAutoma Win32 Clipboard API 测试\n')
    print('  API     : uiautoma.win32.clipboard.get_file_paths')
    print('  原生参照: CF_HDROP + DragQueryFileW\n  测试对象: 临时文件及目录')
    print('  恢复范围: 原Unicode文本；自动清理临时文件')
    results=[run_case('API 合同',contract)]
    original=temporary=None
    touched=False
    paths=[]
    started=time.perf_counter()

    def prepare():
        nonlocal original,temporary,paths
        available,original=native_retry(read_clipboard_text)
        if not available:
            raise RuntimeError('请先复制一段普通文本再运行')
        temporary=tempfile.TemporaryDirectory(prefix='uiautoma-get-file-paths-')
        root=Path(temporary.name)
        a,b,d=root/'english.txt',root/'中文 文件.txt',root/'测试 文件夹'
        a.write_text('test',encoding='utf-8')
        b.write_text('中文',encoding='utf-8')
        d.mkdir()
        paths=list(map(str,(a,b,d)))
        return '原文本已保存，临时文件和目录已创建'

    def observe(expected,available=True):
        assert native_retry(native_files)==(available,expected), '原生文件列表准备不符'
        before_text=native_retry(read_clipboard_text)
        actual=win32.clipboard.get_file_paths()
        assert type(actual) is list and all(type(v) is str for v in actual), type(actual)
        assert actual==expected, f'预期 {expected!r}，实际 {actual!r}'
        assert native_retry(native_files)==(available,expected), '读取改变了文件列表'
        assert native_retry(read_clipboard_text)==before_text, '读取改变了文本内容'
        return actual

    def path_case(expected):
        nonlocal touched
        touched=True
        native_retry(lambda: write_native_files(expected))
        return '返回list[str]，路径、数量、顺序与原生一致', [f'实际: {observe(expected)!r}']

    def no_files(empty):
        nonlocal touched
        touched=True
        native_retry(native_clear if empty else lambda: write_clipboard_text('plain-text-no-files'))
        observe([],available=False)
        return '无CF_HDROP时返回[]，读取未改变剪贴板'

    def repeated():
        path_case(paths)
        for _ in range(3): observe(paths)
        return '连续三次返回相同路径和顺序'

    def isolation():
        path_case(paths)
        returned=observe(paths)
        returned.clear()
        observe(paths)
        return '修改已返回列表不影响剪贴板或后续读取'

    def arguments():
        before=native_retry(native_files)
        for call in (lambda: win32.clipboard.get_file_paths('x'),lambda: win32.clipboard.get_file_paths(timeout=1)):
            try: call()
            except TypeError: pass
            else: raise AssertionError('未拒绝额外参数')
        assert native_retry(native_files)==before, '错误参数调用改变文件列表'
        return '额外位置参数和timeout被TypeError拒绝'

    try:
        results.append(run_case('测试准备',prepare))
        if all(r.passed for r in results):
            for name,expected in [('单文件',[paths[0]]),('单目录',[paths[2]]),('多个文件',paths[:2]),('文件目录混合',[paths[2],paths[1],paths[0]])]:
                results.append(run_case(name,lambda p=expected:path_case(p)))
            results.append(run_case('纯文本剪贴板',lambda:no_files(False)))
            results.append(run_case('空剪贴板',lambda:no_files(True)))
            results.append(run_case('重复读取',repeated))
            results.append(run_case('返回列表隔离',isolation))
            results.append(run_case('调用参数边界',arguments))
    finally:
        def cleanup():
            errors=[]
            if touched:
                try:
                    native_retry(lambda:write_clipboard_text(original))
                    assert native_retry(read_clipboard_text)==(True,original), '原文本未恢复'
                    assert native_retry(native_files)==(False,[]), '临时路径仍在剪贴板'
                except Exception as exc: errors.append(f'剪贴板恢复: {exc}')
            if temporary is not None:
                try:
                    temporary.cleanup()
                    assert not Path(temporary.name).exists(), '临时目录仍存在'
                except Exception as exc: errors.append(f'临时目录清理: {exc}')
            if errors: raise RuntimeError('；'.join(errors))
            return '已清理本次资源；如有改写，原文本已恢复且临时目录已删除'
        results.append(run_case('资源清理',cleanup))
        render_results(results)
    passed=sum(r.passed for r in results)
    ok=passed==len(results)
    print(colored('\n测试通过' if ok else '\n测试失败',ANSI_GREEN if ok else ANSI_RED))
    print(f"  生命周期: {'VERIFIED' if ok else 'READY_FOR_LIVE'}\n  结果    : {passed}/{len(results)} 通过")
    print(f'  总耗时  : {(time.perf_counter()-started)*1000:.1f}ms\n  退出码  : {0 if ok else 1}')
    return 0 if ok else 1


if __name__=='__main__':
    raise SystemExit(main())
