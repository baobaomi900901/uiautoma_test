r"""win32.get_by_element(element: object) -> Win32Window。

用途：根据已获取的Win32Element取得所属顶层窗口；不是根据元素名称重新查找。
API参数：element必填，支持位置/关键字。公开无timeout，内部窗口解析默认5秒。
无效对象抛InvalidParamsError；当前实现也接受底层RawWinElement，本轮仅测试公开高层对象。
脚本参数：--non-interactive 焦点恢复失败仅警告；默认允许人工恢复焦点。
运行：uv run .\win32\test_win32_get_by_element.py --non-interactive
前置：dev、Win32靶场运行，启用 D:\code\元素库\260902_win元素。
切换表单页，使用姓名输入框和保存按钮；以匹配原生物理边界的子控件GetAncestor(GA_ROOT)
独立核验父窗口句柄，并检查返回标题、类名、PID。不修改控件内容、不关闭靶场。
结束恢复鼠标/前台、释放Package；不覆盖销毁元素、跨进程或底层RawWinElement分支。
"""

import inspect
import time
from ctypes import wintypes
from pathlib import Path
from uiautoma import current, win32, InvalidParamsError
from uiautoma.win32 import Win32Window
import test_win32_get_value as helper
from _form_tab import ensure_form_tab
from test_win32_highlight import restore_focus_for_mode, parse_run_options, focus_api, window_info

NAMES=('win32靶场_表单控件_输入框_姓名','win32靶场_表单控件_按钮_保存')


def contract():
    sig=inspect.signature(win32.get_by_element)
    assert list(sig.parameters)==['element'],sig
    p=sig.parameters['element']
    assert p.default is p.empty and p.kind==p.POSITIONAL_OR_KEYWORD,sig
    assert 'Win32Window' in str(sig.return_annotation),sig
    return 'element必填，支持位置/关键字，返回Win32Window'


def native_root(top,element):
    bounds=element.get_bounding(to96dpi=False,relative_to='screen')
    native=helper._user32()
    matches=[]
    @helper.WNDENUMPROC
    def visit(hwnd,unused):
        if helper.window_rect(hwnd,native)==tuple(bounds): matches.append(int(hwnd))
        return True
    native.EnumChildWindows(top,visit,0)
    assert len(matches)==1,f'原生子控件边界匹配不唯一: {bounds}, {matches}'
    native.GetAncestor.argtypes=[wintypes.HWND,wintypes.UINT]
    native.GetAncestor.restype=wintypes.HWND
    root=int(native.GetAncestor(matches[0],2) or 0)
    assert root==top,f'原生根窗口不符: {root}'
    return root


def main(non_interactive=False):
    print('UIAutoma Win32 API 测试\n  API: win32.get_by_element\n  对象: 姓名输入框与保存按钮')
    print('  原生参照: 子控件GetAncestor(GA_ROOT)，以及顶层窗口标题/类名/PID')
    results=[helper.run_case('API 合同',contract)]
    package=window=None
    elements=[]
    roots=[]
    mouse,foreground=helper.current_cursor(),helper.current_foreground()
    focus_status='未检查'
    started=time.perf_counter()

    def prepare():
        nonlocal package,window,elements,roots
        package=current(required=True,refresh=True,timeout=5)
        assert Path(package.package_dir).resolve()==Path(r'D:\code\元素库\260902_win元素').resolve()
        ensure_form_tab(package)
        window=win32.get(title='Win32 靶场 - UIA',process_name='win32-shooting-range-uia.exe',timeout=5)
        elements=[window.find(package.selector(name,kind='win'),timeout=5) for name in NAMES]
        top=int(window.get_detail('handle'))
        roots=[native_root(top,e) for e in elements]
        return '两个SDK元素及各自原生根窗口已定位',[f'原生根窗口: {roots}']

    def check(index,keyword=False):
        element=elements[index]
        old=element.last_result
        reference=window_info(focus_api(),roots[index])
        assert reference['valid'],'原生窗口已失效'
        result=win32.get_by_element(element=element) if keyword else win32.get_by_element(element)
        assert isinstance(result,Win32Window),type(result)
        details=result.get_detail()
        for actual,expected in [('handle','handle'),('title','title'),('class_name','class_name'),('process_id','pid')]:
            assert details[actual]==reference[expected],f'{actual}: {details[actual]!r}，预期{reference[expected]!r}'
        assert element.last_result is old,'查询改变element.last_result'
        return '返回所属靶场窗口，句柄/标题/类名/PID与原生一致',[f"来源: {NAMES[index]}；窗口: {details['title']}；句柄: {details['handle']}"]

    def repeat():
        for _ in range(3): check(0)
        return '连续三次返回同一所属顶层窗口'

    def rejected(call,error):
        try: call()
        except error: return f'{error.__name__}正确拒绝'
        raise AssertionError(f'未抛出{error.__name__}')

    try:
        ready=helper.run_case('测试准备',prepare)
        results.append(ready)
        if ready.passed:
            results.append(helper.run_case('输入框位置参数',lambda:check(0)))
            results.append(helper.run_case('按钮关键字参数',lambda:check(1,True)))
            results.append(helper.run_case('重复获取',repeat))
            for name,value in [('None',None),('元素名字符串',NAMES[0]),('整数',123),('字典',{'name':NAMES[0]}),
                               ('Selector',package.selector(NAMES[0],kind='win')),('窗口对象',window)]:
                results.append(helper.run_case('拒绝'+name,lambda v=value:rejected(lambda:win32.get_by_element(v),InvalidParamsError)))
            def arguments():
                for call in (lambda:win32.get_by_element(),lambda:win32.get_by_element(elements[0],1),lambda:win32.get_by_element(elements[0],timeout=1)):
                    rejected(call,TypeError)
                return '缺参、多余位置参数及timeout均被TypeError拒绝'
            results.append(helper.run_case('调用参数边界',arguments))
    finally:
        def cleanup():
            nonlocal focus_status
            errors=[]
            def focus():
                nonlocal focus_status
                focus_status=restore_focus_for_mode(foreground,non_interactive)
            actions=[('前台',focus),('鼠标',lambda:helper.restore_cursor(mouse))]
            if package is not None: actions.append(('Package',package.close))
            for name,action in actions:
                try: action()
                except Exception as exc: errors.append(f'{name}: {exc}')
            if errors: raise RuntimeError('；'.join(errors))
            return '鼠标已恢复，Package已释放（如已取得）；靶场保留表单页',[f'焦点: {focus_status}']
        results.append(helper.run_case('资源清理',cleanup))
        helper.render_results(results)
    passed=sum(r.passed for r in results)
    ok=passed==len(results)
    print(helper.colored('\n测试通过' if ok else '\n测试失败',helper.ANSI_GREEN if ok else helper.ANSI_RED))
    print(f"  生命周期: {'VERIFIED' if ok else 'READY_FOR_LIVE'}\n  结果: {passed}/{len(results)} 通过\n  总耗时: {(time.perf_counter()-started)*1000:.1f}ms\n  退出码: {0 if ok else 1}")
    return 0 if ok else 1


if __name__=='__main__':
    raise SystemExit(main(non_interactive=parse_run_options().non_interactive))
