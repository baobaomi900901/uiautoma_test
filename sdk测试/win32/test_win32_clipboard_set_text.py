r"""仅测试 uiautoma.win32.clipboard.set_text(text: str) -> None。

API 参数：text 必填，支持位置或关键字传入；当前实现先执行 str(text)。
返回 None。没有 value 或 timeout 关键字参数。
脚本参数：无。
命令：uv run .\win32\test_win32_clipboard_set_text.py
前置：UIAutoma dev 正在运行，无需元素库或靶场；先复制一段普通文本。
脚本通过原生 CF_UNICODETEXT 独立核验，不调用 SDK get_text/clear/set_files。
结束后原生恢复原文本；仅保护 Unicode 文本，不保存富文本、图片等其他剪贴板格式。
测试期间请勿复制/粘贴。原生辅助流程遇 OpenClipboard 失败时限时重试；被测API不重试。
复用同目录 test_win32_clipboard_input.py 的原生剪贴板与彩色日志辅助函数。
"""

import inspect
import time
import uuid

from uiautoma import win32
from test_win32_clipboard_input import (
    read_clipboard_text, write_clipboard_text, run_case, render_results,
    colored, ANSI_GREEN, ANSI_RED,
)


def native_retry(call):
    deadline = time.monotonic() + 2
    retries = 0
    while True:
        try:
            value = call()
            if retries:
                print(f'  原生辅助: 剪贴板打开重试 {retries} 次后成功')
            return value
        except OSError as exc:
            if 'OpenClipboard' not in str(exc) or time.monotonic() >= deadline:
                raise
            retries += 1
            time.sleep(0.05)


def contract():
    sig = inspect.signature(win32.clipboard.set_text)
    assert list(sig.parameters) == ['text'], sig
    p = sig.parameters['text']
    assert p.kind == p.POSITIONAL_OR_KEYWORD and p.default is p.empty, sig
    assert str(p.annotation) in ('str', "<class 'str'>"), sig
    assert sig.return_annotation in (None, 'None', type(None)), sig
    return 'text 必填，支持位置/关键字传入，返回 None'


def main():
    print('UIAutoma Win32 Clipboard API 测试\n')
    print('  API     : uiautoma.win32.clipboard.set_text')
    print('  原生参照: CF_UNICODETEXT\n  恢复范围: 运行前的 Unicode 文本（不打印原文）')
    results = [run_case('API 合同', contract)]
    original = None
    touched = False
    started = time.perf_counter()

    def prepare():
        nonlocal original
        available, text = native_retry(read_clipboard_text)
        if not available:
            raise RuntimeError('请先复制一段普通文本再运行，当前没有可恢复的 Unicode 文本')
        original = text
        return '已保存原剪贴板文本'

    def check(value, keyword=False):
        nonlocal touched
        touched = True
        native_retry(lambda: write_clipboard_text('set-text-sentinel-' + uuid.uuid4().hex))
        begin = time.perf_counter()
        returned = (win32.clipboard.set_text(text=value) if keyword
                    else win32.clipboard.set_text(value))
        elapsed = (time.perf_counter() - begin) * 1000
        available, actual = native_retry(read_clipboard_text)
        assert returned is None, f'预期返回 None，实际 {returned!r}'
        assert available and actual == str(value), f'预期 {str(value)!r}，实际 {actual!r}；Unicode格式={available}'
        call = f'set_text(text={value!r})' if keyword else f'set_text({value!r})'
        return '返回 None，原生读取与预期文本完全一致', [f'调用: {call}', f'实际: {actual!r}；API耗时: {elapsed:.1f}ms']

    def arguments():
        before = native_retry(read_clipboard_text)
        for call in (lambda: win32.clipboard.set_text(),
                     lambda: win32.clipboard.set_text('x', 'y'),
                     lambda: win32.clipboard.set_text(value='x'),
                     lambda: win32.clipboard.set_text('x', timeout=1)):
            try:
                call()
            except TypeError:
                pass
            else:
                raise AssertionError('错误参数未被 TypeError 拒绝')
            assert native_retry(read_clipboard_text) == before, '参数错误调用改变了剪贴板'
        return '缺参、多余参数、value和timeout关键字均被拒绝，剪贴板未改变'

    try:
        results.append(run_case('剪贴板准备', prepare))
        if all(r.passed for r in results):
            for name, value, keyword in (
                ('英文数字', 'UIAutoma_Clipboard_123', False),
                ('中文文本', '剪贴板中文测试', False),
                ('Unicode与符号', '中文😀✓ {}[] !@#', False),
                ('多行与空白', '  first\r\n第二行\tend  ', False),
                ('空字符串', '', False),
                ('关键字参数', 'keyword_text', True),
                ('整数转换', 20260907, False),
                ('None转换', None, False),
            ):
                results.append(run_case(name, lambda v=value,k=keyword: check(v,k)))
            results.append(run_case('调用参数边界', arguments))
    finally:
        def cleanup():
            if touched:
                native_retry(lambda: write_clipboard_text(original))
                assert native_retry(read_clipboard_text) == (True, original), '剪贴板原文未恢复'
                return '原剪贴板文本已恢复并经原生读回确认'
            return '未改写剪贴板，无需恢复'
        results.append(run_case('资源清理', cleanup))
        render_results(results)
    passed = sum(r.passed for r in results)
    ok = passed == len(results)
    print(colored('\n测试通过' if ok else '\n测试失败', ANSI_GREEN if ok else ANSI_RED))
    print(f"  生命周期: {'VERIFIED' if ok else 'READY_FOR_LIVE'}\n  结果    : {passed}/{len(results)} 通过")
    print(f'  总耗时  : {(time.perf_counter()-started)*1000:.1f}ms\n  退出码  : {0 if ok else 1}')
    return 0 if ok else 1


if __name__ == '__main__':
    raise SystemExit(main())
