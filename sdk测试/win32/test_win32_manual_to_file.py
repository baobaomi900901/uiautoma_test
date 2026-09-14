r"""win32.screenshot.manual_to_file(image_path, image_format='', *, timeout=30) -> str。

用途：显示全屏框选层，用户拖选区域后保存截图文件，返回实际路径。
image_path、image_format支持位置/关键字；timeout仅限关键字，默认30秒。
image_format支持png/jpg/jpeg/bmp；为空时按路径扩展名推断。必须人工完成一次框选。
脚本参数：--non-interactive仅为统一命令参数；框选本身仍需人工操作，不能无人值守。
运行：uv run .\win32\test_win32_manual_to_file.py --non-interactive
前置：dev运行；请在提示后拖选一块包含文字或图形的屏幕区域，Esc取消会判失败。
测试创建临时PNG，检查返回路径、PNG解码尺寸、非空内容；结束删除临时文件。
不修改显示设置、剪贴板或靶场；未覆盖JPG/BMP、超时取消及框选层并发。
"""

import argparse
import inspect
import tempfile
import time
from pathlib import Path
from uiautoma import win32
from test_win32_get_value import run_case,render_results,colored,ANSI_GREEN,ANSI_RED
from test_win32_save_window_to_file import _read_image_info


def contract():
    sig=inspect.signature(win32.screenshot.manual_to_file)
    assert list(sig.parameters)==['image_path','image_format','timeout'],sig
    assert sig.parameters['image_path'].default is inspect.Parameter.empty,sig
    assert sig.parameters['image_format'].default=='' and sig.parameters['timeout'].default==30.0,sig
    assert sig.parameters['timeout'].kind==inspect.Parameter.KEYWORD_ONLY,sig
    assert str(sig.return_annotation) in ('str',"<class 'str'>"),sig
    return '路径/格式可位置传入，timeout仅限关键字，返回str路径'


def main():
    print('UIAutoma Win32 API 测试\n  API: win32.screenshot.manual_to_file')
    print('  用途: 人工框选屏幕区域并保存PNG\n  操作: 请拖选包含文字或图形的区域，Esc取消')
    results=[run_case('API 合同',contract)]
    temporary=None
    started=time.perf_counter()
    def prepare():
        nonlocal temporary
        temporary=tempfile.TemporaryDirectory(prefix='uiautoma-manual-to-file-')
        return '临时输出路径已准备',[f'输出: {Path(temporary.name)/"selected.png"}']
    def capture():
        path=Path(temporary.name)/'selected.png'
        print('  请现在在屏幕上拖选区域；框选完成后截图会自动保存。',flush=True)
        begin=time.perf_counter()
        returned=win32.screenshot.manual_to_file(str(path), 'png', timeout=30)
        elapsed=(time.perf_counter()-begin)*1000
        actual=Path(returned)
        assert actual.resolve()==path.resolve(),f'返回路径不符: {actual}'
        info=_read_image_info(actual)
        assert info['format']=='PNG' and info['width']>0 and info['height']>0 and info['size_bytes']>0,info
        assert info['non_uniform'],'选区为纯色，请下次框选包含文字或图形的区域'
        return '框选完成，返回路径、PNG格式、尺寸及非纯色检查通过',[f'图片: {info}',f'框选耗时: {elapsed:.1f}ms']
    def arguments():
        for call in (lambda:win32.screenshot.manual_to_file(),lambda:win32.screenshot.manual_to_file(str(Path(temporary.name)/'x.png'),'png',1),lambda:win32.screenshot.manual_to_file(str(Path(temporary.name)/'x.png'),'png',timeout=1,image_format='bmp')):
            try:call()
            except TypeError:pass
            else:raise AssertionError('参数规则未拒绝')
        return '缺参、多余位置参数和重复image_format被TypeError拒绝'
    try:
        results.append(run_case('测试准备',prepare))
        if results[-1].passed:
            results.append(run_case('人工框选并保存',capture))
            results.append(run_case('参数限制',arguments))
    finally:
        def cleanup():
            if temporary is not None:
                path=Path(temporary.name)/'selected.png'
                temporary.cleanup()
                assert not path.exists(),'临时截图未删除'
                return '本次截图和临时目录已删除'
            return '未创建临时目录'
        results.append(run_case('资源清理',cleanup));render_results(results)
    passed=sum(r.passed for r in results);ok=passed==len(results)
    print(colored('\n测试通过' if ok else '\n测试失败',ANSI_GREEN if ok else ANSI_RED))
    print(f"  生命周期: READY_FOR_LIVE\n  结果: {passed}/{len(results)} 通过\n  总耗时: {(time.perf_counter()-started)*1000:.1f}ms\n  退出码: {0 if ok else 1}")
    return 0 if ok else 1


if __name__=='__main__':
    parser=argparse.ArgumentParser(description='人工框选截图测试')
    parser.add_argument('--non-interactive',action='store_true',help='统一参数；框选仍需人工操作')
    parser.parse_args();raise SystemExit(main())
