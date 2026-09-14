r"""仅测试 uiautoma.win32.clipboard.set_files(paths) -> None。

API 参数：paths 必填，支持位置/关键字；单个str、list[str]或tuple[str,...]。
文件或文件夹应存在；当前Runtime将路径resolve后写入剪贴板。返回None。
脚本参数：无。运行：uv run .\win32\test_win32_clipboard_set_files.py
前置：dev运行，先复制普通文本；无需元素库或靶场。运行期间不要复制/粘贴。
自动创建临时文件和目录，通过CF_HDROP/DragQueryFileW独立核验路径和顺序。
仅设置剪贴板引用，不执行文件复制/移动；结束时恢复原Unicode文本并删除临时目录。
仅保护原Unicode文本，不保留富文本、图片等格式；不打印原文本。
原生辅助可限时重试，被测SDK调用不重试。
依赖同目录clipboard_set_text的日志/原生辅助及clipboard_input的API配置。
"""

import ctypes
import inspect
import os
import tempfile
import time
from pathlib import Path
from ctypes import wintypes

from uiautoma import win32, InvalidParamsError
from test_win32_clipboard_set_text import (
    native_retry, read_clipboard_text, write_clipboard_text,
    run_case, render_results, colored, ANSI_GREEN, ANSI_RED,
)
from test_win32_clipboard_input import _clipboard_api


def native_files():
    user32, _ = _clipboard_api()
    shell32 = ctypes.WinDLL('shell32', use_last_error=True)
    shell32.DragQueryFileW.argtypes = [wintypes.HANDLE, wintypes.UINT, wintypes.LPWSTR, wintypes.UINT]
    shell32.DragQueryFileW.restype = wintypes.UINT
    if not user32.OpenClipboard(None):
        raise OSError(f'OpenClipboard 失败：{ctypes.get_last_error()}')
    try:
        if not user32.IsClipboardFormatAvailable(15):
            return False, []
        handle = user32.GetClipboardData(15)
        if not handle:
            raise OSError('GetClipboardData(CF_HDROP) 失败')
        count = shell32.DragQueryFileW(handle, 0xFFFFFFFF, None, 0)
        paths = []
        for index in range(count):
            size = shell32.DragQueryFileW(handle, index, None, 0)
            buffer = ctypes.create_unicode_buffer(size + 1)
            copied = shell32.DragQueryFileW(handle, index, buffer, size + 1)
            if copied != size or not size:
                raise OSError('DragQueryFileW 读取路径失败')
            paths.append(buffer.value)
        return True, paths
    finally:
        user32.CloseClipboard()


def contract():
    sig = inspect.signature(win32.clipboard.set_files)
    assert list(sig.parameters) == ['paths'], sig
    p = sig.parameters['paths']
    assert p.default is p.empty and p.kind == p.POSITIONAL_OR_KEYWORD, sig
    assert sig.return_annotation in (None, 'None', type(None)), sig
    return 'paths必填，支持位置/关键字，返回None'


def main():
    print('UIAutoma Win32 Clipboard API 测试\n')
    print('  API     : uiautoma.win32.clipboard.set_files')
    print('  原生参照: CF_HDROP + DragQueryFileW\n  测试对象: 自动创建的临时文件和文件夹')
    print('  恢复范围: 原Unicode文本；临时目录测试结束后删除')
    results = [run_case('API 合同', contract)]
    original = temporary = None
    touched = False
    files = []
    started = time.perf_counter()

    def prepare():
        nonlocal original, temporary, files
        available, original = native_retry(read_clipboard_text)
        if not available:
            raise RuntimeError('请先复制一段普通文本再运行')
        temporary = tempfile.TemporaryDirectory(prefix='uiautoma-clipboard-files-')
        root = Path(temporary.name)
        files = [root/'english.txt', root/'中文 文件.txt', root/'测试 文件夹']
        files[0].write_text('clipboard test', encoding='utf-8')
        files[1].write_text('中文测试', encoding='utf-8')
        files[2].mkdir()
        return '原文本已保存，临时文件及文件夹已创建'

    def check(value, keyword=False):
        nonlocal touched
        touched = True
        native_retry(lambda: write_clipboard_text('set-files-sentinel'))
        returned = win32.clipboard.set_files(paths=value) if keyword else win32.clipboard.set_files(value)
        assert returned is None, returned
        expected = [value] if isinstance(value,str) else list(value)
        expected = [os.path.normcase(str(Path(p).resolve())) for p in expected]
        available, actual = native_retry(native_files)
        assert available and [os.path.normcase(p) for p in actual] == expected, f'预期 {expected!r}，实际 {actual!r}'
        assert all(p.exists() for p in files), '原文件或文件夹不存在'
        return '返回None，原生路径、数量和顺序均一致', [f'实际路径: {actual!r}']

    def rejected(call, error):
        nonlocal touched
        touched = True
        native_retry(lambda: write_clipboard_text('invalid-files-preserve'))
        try:
            call()
        except error:
            pass
        else:
            raise AssertionError(f'没有抛出 {error.__name__}')
        assert native_retry(read_clipboard_text) == (True,'invalid-files-preserve'), '错误参数调用改变剪贴板'
        assert native_retry(native_files) == (False,[]), '错误参数写入了文件列表'
        return f'{error.__name__}正确拒绝，原剪贴板文本保持不变'

    try:
        results.append(run_case('测试准备',prepare))
        if all(r.passed for r in results):
            a,b,d = map(str,files)
            for name,value,keyword in [('单文件字符串',a,False),('单文件夹字符串',d,False),
                                       ('多文件列表',[a,b],False),('文件与目录元组',(b,d,a),False),
                                       ('关键字参数',[d,b],True)]:
                results.append(run_case(name,lambda v=value,k=keyword: check(v,k)))
            for name,call,error in [
                ('空列表',lambda: win32.clipboard.set_files([]),InvalidParamsError),
                ('空字符串',lambda: win32.clipboard.set_files(''),InvalidParamsError),
                ('不存在路径',lambda: win32.clipboard.set_files(str(Path(temporary.name)/'missing.txt')),InvalidParamsError),
                ('混合有效与无效',lambda: win32.clipboard.set_files([a,str(Path(temporary.name)/'missing.txt')]),InvalidParamsError),
                ('缺少参数',lambda: win32.clipboard.set_files(),TypeError),
                ('非法None',lambda: win32.clipboard.set_files(None),TypeError),
                ('不支持timeout',lambda: win32.clipboard.set_files(a,timeout=1),TypeError),
            ]:
                results.append(run_case(name,lambda f=call,e=error: rejected(f,e)))
    finally:
        def cleanup():
            errors=[]
            if touched:
                try:
                    native_retry(lambda: write_clipboard_text(original))
                    assert native_retry(read_clipboard_text) == (True,original), '原文本未恢复'
                    assert native_retry(native_files) == (False,[]), '临时路径仍留在剪贴板'
                except Exception as exc:
                    errors.append(f'剪贴板恢复: {exc}')
            if temporary is not None:
                try:
                    temporary.cleanup()
                    assert not Path(temporary.name).exists(), '临时目录仍存在'
                except Exception as exc:
                    errors.append(f'临时文件清理: {exc}')
            if errors:
                raise RuntimeError('；'.join(errors))
            return '已清理本次资源；如有改写，原文本已恢复，临时目录已删除'
        results.append(run_case('资源清理',cleanup))
        render_results(results)
    passed=sum(r.passed for r in results)
    ok=passed==len(results)
    print(colored('\n测试通过' if ok else '\n测试失败',ANSI_GREEN if ok else ANSI_RED))
    print(f"  生命周期: {'VERIFIED' if ok else 'READY_FOR_LIVE'}\n  结果    : {passed}/{len(results)} 通过")
    print(f'  总耗时  : {(time.perf_counter()-started)*1000:.1f}ms\n  退出码  : {0 if ok else 1}')
    return 0 if ok else 1


if __name__ == '__main__':
    raise SystemExit(main())
