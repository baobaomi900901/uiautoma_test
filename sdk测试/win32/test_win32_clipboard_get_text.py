r"""仅测试 uiautoma.win32.clipboard.get_text() -> str。

API 参数：无；返回当前剪贴板文本，没有文本时返回空字符串。
额外位置参数及 timeout 关键字应抛出 TypeError。
脚本参数：无。命令：uv run .\win32\test_win32_clipboard_get_text.py
前置：UIAutoma dev 运行；先复制普通文本，无需元素库或靶场。
使用原生 Windows API 准备/读取 CF_UNICODETEXT，不调用 SDK set_text 或 clear。
区分“已写入空文本”和“剪贴板没有文本格式”。读取前后校验文本未改变。
结束时仅恢复原 Unicode 文本，不保护富文本、图片等其他格式；不打印原文。
原生辅助打开剪贴板限时重试，被测 get_text 不重试；测试期间不要复制/粘贴。
依赖同目录 clipboard_set_text 的辅助函数及 clipboard_input 的原生 API 配置。
"""

import inspect
import time

from uiautoma import win32
from test_win32_clipboard_set_text import (
    native_retry, read_clipboard_text, write_clipboard_text,
    run_case, render_results, colored, ANSI_GREEN, ANSI_RED,
)
from test_win32_clipboard_input import _clipboard_api


def native_clear():
    user32, _ = _clipboard_api()
    if not user32.OpenClipboard(None):
        raise OSError('OpenClipboard 失败')
    try:
        if not user32.EmptyClipboard():
            raise OSError('EmptyClipboard 失败')
    finally:
        user32.CloseClipboard()


def contract():
    sig = inspect.signature(win32.clipboard.get_text)
    assert not sig.parameters, sig
    assert str(sig.return_annotation) in ('str', "<class 'str'>"), sig
    return '无公开参数，返回 str'


def main():
    print('UIAutoma Win32 Clipboard API 测试\n')
    print('  API     : uiautoma.win32.clipboard.get_text')
    print('  原生参照: CF_UNICODETEXT\n  恢复范围: 原 Unicode 文本（不打印原文）')
    results = [run_case('API 合同', contract)]
    original = None
    touched = False
    started = time.perf_counter()

    def prepare():
        nonlocal original
        available, original = native_retry(read_clipboard_text)
        if not available:
            raise RuntimeError('请先复制一段普通文本，再运行测试')
        return '原剪贴板文本已保存'

    def observe(expected, available=True):
        before = native_retry(read_clipboard_text)
        assert before == (available, expected), '原生场景准备或读取失败'
        actual = win32.clipboard.get_text()
        assert type(actual) is str and actual == expected, f'预期 {expected!r}，实际 {actual!r}'
        assert native_retry(read_clipboard_text) == before, '读取改变了剪贴板文本或格式存在状态'
        return actual

    def initial():
        observe(original)
        return 'SDK 与原生初始文本一致，原文未打印'

    def value_case(value):
        nonlocal touched
        touched = True
        native_retry(lambda: write_clipboard_text(value))
        actual = observe(value)
        return '返回 str，与原生文本一致，读取后内容不变', [f'预期: {value!r}；实际: {actual!r}']

    def repeated():
        value = 'repeat_重复读取_123'
        value_case(value)
        for _ in range(3):
            observe(value)
        return '连续三次读取一致，剪贴板内容未改变'

    def no_text():
        nonlocal touched
        touched = True
        native_retry(native_clear)
        observe('', available=False)
        return '无 CF_UNICODETEXT 时返回空字符串，未创建文本格式'

    def arguments():
        before = native_retry(read_clipboard_text)
        for invoke in (lambda: win32.clipboard.get_text('x'),
                       lambda: win32.clipboard.get_text(timeout=1)):
            try:
                invoke()
            except TypeError:
                pass
            else:
                raise AssertionError('未拒绝多余参数')
        assert native_retry(read_clipboard_text) == before, '非法调用改变了剪贴板'
        return '额外位置参数和timeout被 TypeError 拒绝'

    try:
        results.append(run_case('剪贴板准备', prepare))
        if all(r.passed for r in results):
            results.append(run_case('初始文本', initial))
            for name, value in [('英文数字','Clipboard_123'),('中文','剪贴板读取测试'),
                                ('Unicode符号','中文😀✓ {}[] !@#'),
                                ('多行与空白','  first\r\n第二行\tend  '),
                                ('纯空格','   '),('纯换行制表符','\r\n\t'),('空文本','')]:
                results.append(run_case(name, lambda v=value: value_case(v)))
            results.append(run_case('重复读取', repeated))
            results.append(run_case('没有文本格式', no_text))
            results.append(run_case('调用参数边界', arguments))
    finally:
        def cleanup():
            if touched:
                native_retry(lambda: write_clipboard_text(original))
                assert native_retry(read_clipboard_text) == (True, original), '原剪贴板文本未恢复'
                return '原文本已恢复并通过原生读回校验'
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
