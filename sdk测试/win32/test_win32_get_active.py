r"""win32.get_active(timeout: float=5) -> Win32Window。

用途：取得调用时的前台窗口，不是激活某个窗口。timeout可位置/关键字传入；0单次检查。
当前SDK支持None默认值、数字字符串；-1无限等待；小于-1及非数字拒绝。
脚本参数：--non-interactive 焦点恢复失败仅警告；默认人工模式。
运行：uv run .\win32\test_win32_get_active.py --non-interactive
前置：dev及可见、未最小化Win32靶场运行；从Tabby等不同于靶场的窗口启动测试。
原生GetForegroundWindow在调用前后交叉核验句柄，核对返回窗口标题、类名和PID。
先测试初始前台，再用已验证的activate()准备靶场前台场景；激活失败属于准备失败。
不关闭靶场，不用剪贴板或元素库。清理恢复鼠标/前台；自动模式不会等待手动切窗。
未制造没有前台窗口的场景；-1仅在已确认前台存在时调用，不验证无限等待后出现。
"""

import inspect
import time
from uiautoma import win32, InvalidParamsError
from uiautoma.win32 import Win32Window
import test_win32_get_value as helper
from test_win32_highlight import focus_api, window_info, restore_focus_for_mode, parse_run_options


def contract():
    sig=inspect.signature(win32.get_active)
    assert list(sig.parameters)==['timeout'],sig
    p=sig.parameters['timeout']
    assert p.default==5 and p.kind==p.POSITIONAL_OR_KEYWORD,sig
    assert 'Win32Window' in str(sig.return_annotation),sig
    return 'timeout默认5秒，支持位置/关键字，返回Win32Window'


def main(non_interactive=False):
    print('UIAutoma Win32 API 测试\n  API: win32.get_active\n  场景: 初始前台 → 靶场前台')
    print('  原生参照: GetForegroundWindow及窗口标题/类名/PID；测试中请勿切换窗口')
    results=[helper.run_case('API 合同',contract)]
    native=focus_api()
    original=int(native.GetForegroundWindow() or 0)
    mouse=helper.current_cursor()
    focus_status='未检查'
    started=time.perf_counter()

    def observe(args=(),kwargs=None,expected=None):
        before=int(native.GetForegroundWindow() or 0)
        info=window_info(native,before)
        assert before and info['valid'],'没有可识别的原生前台窗口'
        if expected is not None: assert before==expected,f'准备的前台不是目标：预期{expected}，实际{before}'
        result=win32.get_active(*args,**(kwargs or {}))
        after=int(native.GetForegroundWindow() or 0)
        assert before==after,'调用期间前台改变，请保持前台稳定后复测'
        assert isinstance(result,Win32Window),type(result)
        actual=result.get_detail()
        assert int(native.GetForegroundWindow() or 0)==before,'详情核验期间前台改变'
        assert actual['handle']==before,f"预期句柄{before}，实际{actual.get('handle')}"
        assert actual['class_name']==info['class_name'],actual
        assert actual['process_id']==info['pid'],actual
        # 终端标题可能动态变化，仅在原生前后标题稳定时作精确比较。
        now=window_info(native,before)
        assert now['title']==info['title'],'窗口标题发生变化，请保持终端标题稳定后复测'
        assert actual['title']==info['title'],actual
        return '返回当前前台窗口，句柄/标题/类名/PID与原生一致',[f"窗口: {info['title']}；句柄: {before}；PID: {info['pid']}"]

    def activate_target():
        target=win32.get(title='Win32 靶场 - UIA',process_name='win32-shooting-range-uia.exe',timeout=5)
        handle=int(target.get_detail('handle'))
        assert handle!=original,'请从Tabby等另一窗口启动，确保覆盖前台切换'
        assert native.IsWindowVisible(handle) and not native.IsIconic(handle),'请先恢复并显示靶场'
        target.activate()
        deadline=time.monotonic()+2
        while native.GetForegroundWindow()!=handle and time.monotonic()<deadline: time.sleep(0.02)
        assert native.GetForegroundWindow()==handle,'靶场未激活，场景准备失败'
        return handle

    def rejected(calls,error):
        for call in calls:
            try: call()
            except error: pass
            else: raise AssertionError(f'没有抛出{error.__name__}')
        return f'错误参数被{error.__name__}拒绝'

    try:
        results.append(helper.run_case('初始前台',lambda:observe(expected=original)))
        handles=[]
        def prepare():
            handles.append(activate_target())
            return '靶场已成为原生前台窗口'
        ready=helper.run_case('激活靶场',prepare)
        results.append(ready)
        if ready.passed:
            for name,args,kwargs in [('默认超时',(),{}),('零超时位置参数',(0,),{}),
                ('正数关键字',(),dict(timeout=0.5)),('None超时',(),dict(timeout=None)),
                ('数字字符串',(),dict(timeout='0.5')),('无限值已存在',(),dict(timeout=-1))]:
                results.append(helper.run_case(name,lambda a=args,k=kwargs:observe(a,k,handles[0])))
            def repeat():
                for _ in range(3): observe((0,),expected=handles[0])
                return '连续三次返回同一靶场前台窗口'
            results.append(helper.run_case('重复查询',repeat))
        results.append(helper.run_case('非法超时',lambda:rejected([lambda:win32.get_active(-2),lambda:win32.get_active('bad')],InvalidParamsError)))
        results.append(helper.run_case('多余参数',lambda:rejected([lambda:win32.get_active(0,0),lambda:win32.get_active(unknown=1)],TypeError)))
    finally:
        def cleanup():
            nonlocal focus_status
            errors=[]
            def focus():
                nonlocal focus_status
                focus_status=restore_focus_for_mode(original,non_interactive)
            for name,action in [('前台',focus),('鼠标',lambda:helper.restore_cursor(mouse))]:
                try: action()
                except Exception as exc: errors.append(f'{name}: {exc}')
            if errors: raise RuntimeError('；'.join(errors))
            return '鼠标已恢复，靶场保持运行',[f'焦点: {focus_status}']
        results.append(helper.run_case('资源清理',cleanup))
        helper.render_results(results)
    passed=sum(r.passed for r in results)
    ok=passed==len(results)
    print(helper.colored('\n测试通过' if ok else '\n测试失败',helper.ANSI_GREEN if ok else helper.ANSI_RED))
    print(f"  生命周期: {'VERIFIED' if ok else 'READY_FOR_LIVE'}\n  结果: {passed}/{len(results)} 通过\n  总耗时: {(time.perf_counter()-started)*1000:.1f}ms\n  退出码: {0 if ok else 1}")
    return 0 if ok else 1


if __name__=='__main__':
    raise SystemExit(main(non_interactive=parse_run_options().non_interactive))
