r"""仅测试 uiautoma.win32.clipboard.clear() -> None。

API 参数：无。清空剪贴板内容，返回 None；额外参数应抛出 TypeError。
脚本参数：无。命令：uv run .\win32\test_win32_clipboard_clear.py
前置：UIAutoma dev 正在运行；先复制普通文本，无需元素库或靶场。
原生准备文本，SDK clear 后独立检查 CountClipboardFormats()==0，且无Unicode文本。
覆盖英文、Unicode、空文本、已经为空、重复清空及错误参数。
结束后仅恢复原 Unicode 文本，不保护图片/富文本等其他格式；不打印原文。
被测 SDK 不重试；只对原生辅助 OpenClipboard 失败限时重试。期间请勿复制粘贴。
本轮未准备图片、文件列表或自定义格式，不声称覆盖这些来源的清空场景。
依赖同目录 clipboard_set_text 和 clipboard_get_text 中的原生/日志辅助函数。
"""

import ctypes
import inspect
import time
from uiautoma import win32
from test_win32_clipboard_set_text import (
    native_retry, read_clipboard_text, write_clipboard_text,
    run_case, render_results, colored, ANSI_GREEN, ANSI_RED,
)
from test_win32_clipboard_get_text import native_clear
from test_win32_clipboard_input import _clipboard_api


def native_format_count():
    user32, _ = _clipboard_api()
    user32.CountClipboardFormats.argtypes = []
    user32.CountClipboardFormats.restype = ctypes.c_int
    if not user32.OpenClipboard(None):
        raise OSError(f'OpenClipboard 失败：{ctypes.get_last_error()}')
    try:
        ctypes.set_last_error(0)
        count = user32.CountClipboardFormats()
        error = ctypes.get_last_error()
        if count == 0 and error:
            raise OSError(f'CountClipboardFormats 失败：{error}')
        return count
    finally:
        user32.CloseClipboard()


def contract():
    sig = inspect.signature(win32.clipboard.clear)
    assert not sig.parameters, sig
    assert sig.return_annotation in (None,'None',type(None)), sig
    return '无公开参数，返回 None'


def main():
    print('UIAutoma Win32 Clipboard API 测试\n')
    print('  API     : uiautoma.win32.clipboard.clear')
    print('  原生参照: CountClipboardFormats + CF_UNICODETEXT')
    print('  恢复范围: 原 Unicode 文本（不打印原文）')
    results = [run_case('API 合同', contract)]
    original = None
    touched = False
    started = time.perf_counter()

    def prepare():
        nonlocal original
        available, original = native_retry(read_clipboard_text)
        if not available:
            raise RuntimeError('请先复制一段普通文本再运行')
        return '已保存原剪贴板文本'

    def verify_clear():
        returned = win32.clipboard.clear()
        assert returned is None, f'实际返回 {returned!r}'
        count = native_retry(native_format_count)
        assert count == 0, f'清空后仍有 {count} 种格式'
        assert native_retry(read_clipboard_text) == (False,''), 'Unicode文本格式仍存在'
        return '返回 None；原生确认格式数为0，Unicode文本格式不存在'

    def text_case(value):
        nonlocal touched
        touched = True
        native_retry(lambda: write_clipboard_text(value))
        assert native_retry(read_clipboard_text) == (True,value), '原生文本准备失败'
        assert native_retry(native_format_count) > 0, '准备后没有剪贴板格式'
        return verify_clear()

    def already_empty():
        nonlocal touched
        touched = True
        native_retry(native_clear)
        assert native_retry(native_format_count) == 0
        return verify_clear()

    def repeated():
        text_case('repeat-clear')
        for _ in range(3):
            verify_clear()
        return '首次清空后连续三次调用均返回 None，格式数保持0'

    def arguments():
        nonlocal touched
        touched = True
        sentinel = 'clear-invalid-args-原文应保留'
        native_retry(lambda: write_clipboard_text(sentinel))
        for call in (lambda: win32.clipboard.clear('x'), lambda: win32.clipboard.clear(timeout=1)):
            try:
                call()
            except TypeError:
                pass
            else:
                raise AssertionError('额外参数未被拒绝')
            assert native_retry(read_clipboard_text) == (True,sentinel), '非法调用清除了文本'
        return '位置参数和timeout均被 TypeError 拒绝，原生文本未改变'

    try:
        results.append(run_case('剪贴板准备',prepare))
        if all(r.passed for r in results):
            for name, value in [('英文文本','Clipboard_Clear_123'),('Unicode文本','中文😀✓\r\n第二行'),('空文本格式','')]:
                results.append(run_case(name,lambda v=value: text_case(v)))
            results.append(run_case('已经为空',already_empty))
            results.append(run_case('连续清空',repeated))
            results.append(run_case('调用参数边界',arguments))
    finally:
        def cleanup():
            if touched:
                native_retry(lambda: write_clipboard_text(original))
                assert native_retry(read_clipboard_text) == (True,original), '原文本未恢复'
                return '原文本已恢复并通过原生读回校验'
            return '未改写剪贴板，无需恢复'
        results.append(run_case('资源清理',cleanup))
        render_results(results)
    passed = sum(r.passed for r in results)
    ok = passed == len(results)
    print(colored('\n测试通过' if ok else '\n测试失败',ANSI_GREEN if ok else ANSI_RED))
    print(f"  生命周期: {'VERIFIED' if ok else 'READY_FOR_LIVE'}\n  结果    : {passed}/{len(results)} 通过")
    print(f'  总耗时  : {(time.perf_counter()-started)*1000:.1f}ms\n  退出码  : {0 if ok else 1}')
    return 0 if ok else 1


if __name__ == '__main__':
    raise SystemExit(main())
