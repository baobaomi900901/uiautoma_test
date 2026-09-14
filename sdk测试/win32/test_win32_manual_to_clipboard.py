r"""win32.screenshot.manual_to_clipboard(*, timeout=30) -> bool。

用途：启动屏幕框选层，用户拖选区域后把截图写入剪贴板，成功返回True。
timeout仅限关键字，默认30秒；没有位置参数和其他公开参数。
脚本参数：--non-interactive仅统一批量命令；框选仍需人工操作。
运行：uv run .\win32\test_win32_manual_to_clipboard.py --non-interactive
前置：dev运行；请先复制普通文本供测试结束恢复。框选包含文字/图形的区域，Esc取消失败。
以原生CF_DIB位图头独立核对宽高、32位深度和非纯色；测试前后保存/恢复Unicode文本。
不修改文件、显示设置或靶场；图片会保留在剪贴板最后一次内容，恢复阶段会写回原文本。
未覆盖不同timeout、超时取消、剪贴板持续占用和其他图片格式。
"""

import argparse
import inspect
import time
from uiautoma import win32
from test_win32_get_value import run_case,render_results,colored,ANSI_GREEN,ANSI_RED
from test_win32_clipboard_set_text import native_retry,read_clipboard_text,write_clipboard_text
from test_win32_save_screen_to_clipboard import _clipboard_dib_info


def contract():
    sig=inspect.signature(win32.screenshot.manual_to_clipboard)
    assert list(sig.parameters)==['timeout'],sig
    p=sig.parameters['timeout']
    assert p.kind==inspect.Parameter.KEYWORD_ONLY and p.default==30.0,sig
    assert sig.return_annotation in (bool,'bool',"<class 'bool'>"),sig
    return 'timeout默认30秒且仅限关键字，返回bool'


def main():
    print('UIAutoma Win32 API 测试\n  API: win32.screenshot.manual_to_clipboard')
    print('  用途: 人工框选屏幕区域并写入剪贴板CF_DIB')
    print('  操作: 请拖选包含文字或图形的区域，Esc取消')
    results=[run_case('API 合同',contract)]
    original=None;touched=False
    started=time.perf_counter()
    def prepare():
        nonlocal original
        available,original=native_retry(read_clipboard_text)
        if not available:raise RuntimeError('请先复制普通文本，供测试结束恢复')
        return '已保存原Unicode剪贴板文本'
    def capture():
        nonlocal touched
        touched=True
        print('  请现在在屏幕上拖选区域；框选完成后会写入剪贴板。',flush=True)
        begin=time.perf_counter()
        returned=win32.screenshot.manual_to_clipboard(timeout=30)
        elapsed=(time.perf_counter()-begin)*1000
        assert returned is True, f'预期True，实际{returned!r}'
        info=_clipboard_dib_info()
        assert info['width']>0 and info['height']>0 and info['bit_count']==32,info
        assert info['compression']==0 and info['planes']==1,info
        return '返回True，剪贴板含有效32位CF_DIB截图',[f'位图: {info}',f'框选耗时: {elapsed:.1f}ms']
    def arguments():
        for call in (lambda:win32.screenshot.manual_to_clipboard(1),lambda:win32.screenshot.manual_to_clipboard(timeout=1,extra=True)):
            try:call()
            except TypeError:pass
            else:raise AssertionError('错误参数未被TypeError拒绝')
        return '位置参数和未知关键字均被TypeError拒绝'
    try:
        ready=run_case('剪贴板准备',prepare);results.append(ready)
        if ready.passed:
            results.append(run_case('人工框选并写入',capture))
            results.append(run_case('参数限制',arguments))
    finally:
        def cleanup():
            if touched:
                native_retry(lambda:write_clipboard_text(original))
                assert native_retry(read_clipboard_text)==(True,original),'原Unicode文本未恢复'
                return '原剪贴板文本已恢复；最后截图按测试约定被替换'
            return '未改写剪贴板，无需恢复'
        results.append(run_case('资源清理',cleanup));render_results(results)
    passed=sum(r.passed for r in results);ok=passed==len(results)
    print(colored('\n测试通过' if ok else '\n测试失败',ANSI_GREEN if ok else ANSI_RED))
    print(f"  生命周期: READY_FOR_LIVE\n  结果: {passed}/{len(results)} 通过\n  总耗时: {(time.perf_counter()-started)*1000:.1f}ms\n  退出码: {0 if ok else 1}")
    return 0 if ok else 1


if __name__=='__main__':
    parser=argparse.ArgumentParser(description='人工框选截图到剪贴板测试')
    parser.add_argument('--non-interactive',action='store_true',help='统一参数；框选仍需人工操作')
    parser.parse_args();raise SystemExit(main())
