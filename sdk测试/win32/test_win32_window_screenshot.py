r"""Win32Window.screenshot(folder_path: str|None=None, *, filename: str|None=None) -> str。

用途：把当前真实顶层窗口截图保存为PNG，返回文件路径。
folder_path可位置/关键字传入；None使用Runtime默认截图目录。
filename仅限关键字；None自动命名，没有.png后缀时当前实现追加.png。
脚本参数：--non-interactive 焦点恢复失败仅警告；默认允许人工切回原终端。
--keep-images 保留本次截图和输出目录供人工查看；不传时仍自动删除。
运行：uv run .\win32\test_win32_window_screenshot.py --non-interactive
前置：dev与可见、未最小化的Win32靶场运行；无需元素库。测试中不要移动/缩放窗口。
检查返回路径、PNG解码尺寸与原生GetWindowRect一致、图片非纯色。非纯色不等于完整视觉验收。
未使用--keep-images时自动删除截图；默认目录只删除本次返回的自动命名文件，不删除目录。
不关闭靶场。复用既有GDI+图像解码和焦点/鼠标辅助；不覆盖最小化、遮挡和无原生句柄对象。
"""

import inspect
import argparse
import re
import tempfile
import time
import uuid
from pathlib import Path
from uiautoma import win32
from uiautoma.win32 import Win32Window
import test_win32_get_value as helper
from test_win32_highlight import restore_focus_for_mode, focus_api
from test_win32_save_window_to_file import _read_image_info


def contract():
    sig=inspect.signature(Win32Window.screenshot)
    assert list(sig.parameters)==['self','folder_path','filename'],sig
    assert sig.parameters['folder_path'].kind==inspect.Parameter.POSITIONAL_OR_KEYWORD,sig
    assert sig.parameters['filename'].kind==inspect.Parameter.KEYWORD_ONLY,sig
    assert all(sig.parameters[k].default is None for k in ('folder_path','filename')),sig
    assert str(sig.return_annotation) in ('str',"<class 'str'>"),sig
    return '目录可选、filename仅限关键字，返回str路径'


def main(non_interactive=False, keep_images=False):
    print('UIAutoma Win32 Window API 测试\n  API: Win32Window.screenshot')
    print('  窗口: Win32 靶场 - UIA\n  检查: PNG、原生尺寸、非纯色')
    print('  图片处理: '+('保留本次截图供查看' if keep_images else '本次截图结束后删除'))
    results=[helper.run_case('API 合同',contract)]
    target=hwnd=temporary=None
    output_root=None
    generated=[]
    mouse,foreground=helper.current_cursor(),helper.current_foreground()
    focus_status='未检查'
    started=time.perf_counter()

    def prepare():
        nonlocal target,hwnd,temporary,output_root
        target=win32.get(title='Win32 靶场 - UIA',process_name='win32-shooting-range-uia.exe',timeout=5)
        hwnd=int(target.get_detail('handle'))
        native=focus_api()
        assert native.IsWindowVisible(hwnd) and not native.IsIconic(hwnd),'请先显示并恢复靶场窗口'
        if keep_images:
            output_root=Path(tempfile.mkdtemp(prefix='uiautoma-window-screenshot-'))
        else:
            temporary=tempfile.TemporaryDirectory(prefix='uiautoma-window-screenshot-')
            output_root=Path(temporary.name)
        return '靶场已定位，临时输出目录已准备',[f'原生边界: {helper.window_rect(hwnd,helper._user32())}']

    def capture(args=(),kwargs=None,expected_name=None,expected_dir=None):
        kwargs=kwargs or {}
        before=helper.window_rect(hwnd,helper._user32())
        earliest=int(time.time()*1000)
        returned=target.screenshot(*args,**kwargs)
        latest=int(time.time()*1000)
        assert type(returned) is str and returned,returned
        path=Path(returned).resolve()
        if expected_dir is not None:
            assert path.parent==Path(expected_dir).resolve(),f'返回目录不符: {path}'
        if expected_name:
            assert path.name==expected_name,f'文件名不符: {path.name}'
        else:
            match=re.fullmatch(r'window_'+str(hwnd)+r'_(\d+)\.png',path.name)
            assert match and earliest<=int(match.group(1))<=latest,f'无法确认本次自动命名文件: {path}'
        # 仅登记本次调用返回、命名与目录均已验证的文件。
        generated.append(path)
        info=_read_image_info(path)
        assert helper.window_rect(hwnd,helper._user32())==before,'截图期间窗口尺寸/位置变化'
        assert info['format']=='PNG' and (info['width'],info['height'])==before[2:],f'图片信息: {info}；预期尺寸: {before[2:]}'
        assert info['non_uniform'] and info['size_bytes']>0,'截图为空或纯色'
        return '返回路径、PNG格式、原生尺寸及非纯色检查通过',[f'路径: {path}',f'图片: {info}']

    def arguments():
        for call in (lambda:target.screenshot(str(output_root),'extra.png'),lambda:target.screenshot(timeout=1)):
            try: call()
            except TypeError: pass
            else: raise AssertionError('错误参数未被拒绝')
        return 'filename位置传参及timeout关键字均被TypeError拒绝'

    try:
        results.append(helper.run_case('测试准备',prepare))
        if all(r.passed for r in results):
            root=output_root
            results.append(helper.run_case('全部默认参数',lambda:capture()))
            results.append(helper.run_case('位置目录参数',lambda:capture((str(root),),expected_dir=root)))
            results.append(helper.run_case('显式None',lambda:capture(kwargs=dict(folder_path=None,filename=None))))
            name='中文 截图-'+uuid.uuid4().hex+'.png'
            results.append(helper.run_case('全关键字PNG',lambda:capture(kwargs=dict(folder_path=str(root),filename=name),expected_name=name,expected_dir=root)))
            results.append(helper.run_case('自动追加扩展名',lambda:capture((str(root),),dict(filename='no-extension'),expected_name='no-extension.png',expected_dir=root)))
            sub=root/'nested'/'output'
            results.append(helper.run_case('创建保存目录',lambda:capture(kwargs=dict(folder_path=str(sub),filename='nested.png'),expected_name='nested.png',expected_dir=sub)))
            results.append(helper.run_case('参数规则',arguments))
    finally:
        def cleanup():
            nonlocal focus_status
            errors=[]
            for path in ([] if keep_images else generated):
                try: path.unlink(missing_ok=True)
                except Exception as exc: errors.append(f'删除截图{path}: {exc}')
            if temporary is not None:
                try: temporary.cleanup()
                except Exception as exc: errors.append(f'清理临时目录: {exc}')
            def focus():
                nonlocal focus_status
                focus_status=restore_focus_for_mode(foreground,non_interactive)
            for name,action in [('前台',focus),('鼠标',lambda:helper.restore_cursor(mouse))]:
                try: action()
                except Exception as exc: errors.append(f'{name}: {exc}')
            if errors: raise RuntimeError('；'.join(errors))
            detail='按参数保留本次截图和输出目录' if keep_images else '本次登记的截图及临时目录已清理'
            return detail+'，鼠标恢复；靶场保持运行',[f'焦点: {focus_status}']
        results.append(helper.run_case('资源清理',cleanup))
        helper.render_results(results)
    passed=sum(r.passed for r in results)
    ok=passed==len(results)
    print(helper.colored('\n测试通过' if ok else '\n测试失败',helper.ANSI_GREEN if ok else helper.ANSI_RED))
    print(f"  生命周期: {'VERIFIED' if ok else 'READY_FOR_LIVE'}\n  结果: {passed}/{len(results)} 通过\n  总耗时: {(time.perf_counter()-started)*1000:.1f}ms\n  退出码: {0 if ok else 1}")
    if keep_images:
        print(f'  保留输出目录: {output_root}')
        print('  保留图片（含默认目录中的截图）:')
        for path in generated:
            print(f'    {path}')
    return 0 if ok else 1


if __name__=='__main__':
    parser=argparse.ArgumentParser(description='Win32Window.screenshot 实时测试')
    parser.add_argument('--non-interactive',action='store_true',help='焦点恢复失败仅警告，不等待人工')
    parser.add_argument('--keep-images',action='store_true',help='保留本次截图和输出目录供人工查看')
    options=parser.parse_args()
    raise SystemExit(main(non_interactive=options.non_interactive,keep_images=options.keep_images))
