r"""Win32Element.long_press() 实时测试。

API参数（全部支持位置/关键字）：seconds=1.0 按住秒数；simulative=True 鼠标模式；
delay_after=1 动作后等待秒数；move_mouse=None 使用SDK偏好；anchor=None 默认中心；
timeout=10.0 动作超时秒数。返回None并更新last_result。
seconds非负，可转换数字字符串；非法seconds/timeout在SDK边界拒绝。
anchor支持九宫格、random、三元组和字典偏移。非法delay_after在动作结束后拒绝。
脚本参数：--non-interactive 自动复测；默认人工模式。
运行：uv run .\win32\test_win32_long_press.py [--non-interactive]
自动模式焦点恢复失败仅警告，不等待人工；按键释放、鼠标恢复和连接清理仍严格检查。
前置：dev、靶场运行，启用 D:\code\元素库\260902_win元素。自动切换拖拽页。
原生采样左键按下/抬起和光标位置（2ms间隔）；不使用剪贴板、不拖动元素。
测试期间不要触碰鼠标。零时长允许未捕获瞬时按压；若捕获，必须完整释放且按住不超过80ms。
结束时恢复鼠标/前台、关闭Package；自动切窗失败时30秒内手动切回原Tabby窗口。
复用highlight/get_anchor_position/get_value辅助。未覆盖长按超过timeout的取消行为。
"""

import ctypes
import inspect
import threading
import time
from pathlib import Path
import test_win32_get_value as helper
from test_win32_highlight import restore_focus_for_mode, parse_run_options
from test_win32_get_anchor_position import native_target
from test_win32_clipboard_input import anchor_point
from uiautoma import current, win32, InvalidParamsError
from uiautoma.win32 import Win32Element

ANCHORS=('topLeft','topCenter','topRight','middleLeft','middleCenter','middleRight','bottomLeft','bottomCenter','bottomRight')


def mouse_api():
    user32=ctypes.WinDLL('user32',use_last_error=True)
    user32.GetAsyncKeyState.argtypes=[ctypes.c_int]
    user32.GetAsyncKeyState.restype=ctypes.c_short
    return user32


def contract():
    sig=inspect.signature(Win32Element.long_press)
    defaults=dict(seconds=1.0,simulative=True,delay_after=1,move_mouse=None,anchor=None,timeout=10.0)
    assert list(sig.parameters)==['self',*defaults],sig
    for k,v in defaults.items():
        p=sig.parameters[k]
        assert p.kind==p.POSITIONAL_OR_KEYWORD and p.default==v,sig
    assert sig.return_annotation in (None,'None',type(None)),sig
    return '六个参数、默认值及传参规则符合合同'


def check_zero_hold(events):
    if not events:
        return '零时长未采样到持续按压；调用完成且左键已释放'
    assert len(events)==2 and events[0][0] and not events[1][0], f'零时长采样不完整或包含多次按压：{events}'
    held=(events[1][1]-events[0][1])*1000
    assert 0<=held<=80, f'seconds=0 却实际按住{held:.1f}ms，超出瞬时按压容差80ms'
    return f'零时长原生按住{held:.1f}ms，在80ms容差内且已释放'


def main(non_interactive=False):
    print('UIAutoma Win32 Element API 测试\n  API: Win32Element.long_press')
    print('  目标: win32靶场_拖拽测试_可拖拽元素\n  原生参照: 左键状态/按下位置采样；请勿操作鼠标')
    print('  模式: ' + ('自动复测' if non_interactive else '人工测试'))
    results=[helper.run_case('API 合同',contract)]
    package=element=hwnd=None
    focus_status='未检查'
    mouse,foreground=helper.current_cursor(),helper.current_foreground()
    user32=mouse_api()
    initially_released=not bool(user32.GetAsyncKeyState(1)&0x8000)
    started=time.perf_counter()

    def prepare():
        nonlocal package,element,hwnd
        assert not user32.GetAsyncKeyState(1)&0x8000,'请先松开鼠标左键'
        package=current(required=True,refresh=True,timeout=5)
        assert Path(package.package_dir).resolve()==Path(r'D:\code\元素库\260902_win元素').resolve()
        window=win32.get(title='Win32 靶场 - UIA',process_name='win32-shooting-range-uia.exe',timeout=5)
        window.find(package.selector('win32靶场_tab_item拖拽测试',kind='win'),timeout=5).click(delay_after=0.2)
        element=window.find(package.selector('win32靶场_拖拽测试_可拖拽元素',kind='win'),timeout=5)
        hwnd=native_target(window.get_detail('handle'))
        return '目标已定位，左键处于释放状态',[f'物理边界: {helper.window_rect(hwnd,helper._user32())}']

    def invoke(args=(),kwargs=None,error=None,acted=True):
        kwargs=kwargs or {}
        params=inspect.signature(Win32Element.long_press).bind(element,*args,**kwargs)
        params.apply_defaults()
        p=params.arguments
        before=helper.window_rect(hwnd,helper._user32())
        assert not user32.GetAsyncKeyState(1)&0x8000,'调用前左键未释放'
        old=element.last_result
        events=[]
        failures=[]
        stop=threading.Event()
        ready=threading.Event()
        def sample():
            try:
                last=False
                ready.set()
                while not stop.is_set():
                    down=bool(user32.GetAsyncKeyState(1)&0x8000)
                    if down!=last:
                        events.append((down,time.perf_counter(),helper.current_cursor()))
                        last=down
                    stop.wait(0.002)
            except Exception as exc:
                failures.append(str(exc))
                ready.set()
        worker=threading.Thread(target=sample,daemon=True)
        worker.start()
        ready.wait(1)
        returned=caught=None
        begin=time.perf_counter()
        try:
            returned=element.long_press(*args,**kwargs)
        except Exception as exc:
            caught=exc
        finally:
            elapsed=(time.perf_counter()-begin)*1000
            time.sleep(0.03)
            stop.set()
            worker.join(1)
        assert not worker.is_alive() and not failures,f'采样失败: {failures}'
        assert not user32.GetAsyncKeyState(1)&0x8000,'调用后左键仍按下，已停止后续动作'
        assert helper.window_rect(hwnd,helper._user32())==before,'长按改变了目标位置'
        if error:
            assert isinstance(caught,error),f'预期{error.__name__}，实际{caught!r}'
        elif caught:
            raise caught
        else:
            assert returned is None,returned
        if not acted:
            assert not events and element.last_result is old,'非法参数触发了按压或更新动作结果'
            return elapsed,'非法参数在动作前被拒绝'
        assert element.last_result is not old and element.last_result is not None,'last_result未更新'
        element.last_result.raise_for_error()
        seconds=float(p['seconds'])
        if seconds>0:
            assert len(events)==2 and events[0][0] and not events[1][0],f'预期一次完整按住/释放，实际{events}'
            held=(events[1][1]-events[0][1])*1000
            assert abs(held-seconds*1000)<=max(80,seconds*1000*0.25),f'预期按住{seconds}s，采样{held:.1f}ms'
            anchor=p['anchor']
            name=anchor or 'middleCenter'
            ox=oy=0
            if isinstance(anchor,tuple): name,ox,oy=anchor
            elif isinstance(anchor,dict): name,ox,oy=anchor['anchor'],anchor.get('offset_x',0),anchor.get('offset_y',0)
            actual=events[0][2]
            if name=='random':
                x,y,w,h=before
                assert x<=actual[0]<x+w and y<=actual[1]<y+h,actual
            else:
                expected=anchor_point(before,name,ox,oy)
                assert all(abs(a-b)<=2 for a,b in zip(actual,expected)),f'锚点预期{expected}，实际{actual}'
            return elapsed,f'原生按住{held:.1f}ms；按下点{actual}；最终已释放'
        return elapsed,check_zero_hold(events)

    def check(args=(),kwargs=None,error=None,acted=True):
        elapsed,detail=invoke(args,kwargs,error,acted)
        return detail,[f'调用: long_press{args!r} {kwargs or {}!r}；耗时{elapsed:.1f}ms']

    def delay_pair():
        base,_=invoke(kwargs=dict(seconds=0.2,delay_after=0,move_mouse=False))
        delayed,_=invoke(kwargs=dict(seconds=0.2,delay_after=0.3,move_mouse=False))
        assert 200<=delayed-base<=500,f'延时差值不符: {delayed-base:.1f}ms'
        return f'动作后延时差值{delayed-base:.1f}ms，符合约300ms'

    try:
        results.append(helper.run_case('测试目标',prepare))
        if all(r.passed for r in results):
            cases=[('默认参数',(),{}),('全位置参数',(0.3,True,0,False,'middleCenter',5),{}),
                   ('非模拟模式',(),dict(seconds=0.2,simulative=False,delay_after=0)),
                   ('可见移动',(),dict(seconds=0.2,move_mouse=True,delay_after=0)),
                   ('瞬时移动',(),dict(seconds=0.2,move_mouse=False,delay_after=0)),
                   ('零时长',(),dict(seconds=0,delay_after=0)),
                   ('None延时',(),dict(seconds=0.2,delay_after=None)),
                   ('数字字符串',(),dict(seconds='0.2',delay_after=0)),
                   ('随机锚点',(),dict(seconds=0.2,anchor='random',delay_after=0)),
                   ('三元组锚点',(),dict(seconds=0.2,anchor=('middleCenter',6,4),delay_after=0)),
                   ('字典锚点',(),dict(seconds=0.2,anchor=dict(anchor='middleCenter',offset_x=-6,offset_y=-4),delay_after=0))]
            cases += [('锚点 '+a,(),dict(seconds=0.2,anchor=a,delay_after=0)) for a in ANCHORS]
            for name,args,kwargs in cases:
                results.append(helper.run_case(name,lambda a=args,k=kwargs:check(a,k)))
                if user32.GetAsyncKeyState(1)&0x8000: break
            if not user32.GetAsyncKeyState(1)&0x8000:
                results.append(helper.run_case('配对延时',delay_pair))
                for name,kwargs,acted in [('负数秒数',dict(seconds=-1),False),('非法秒数',dict(seconds='invalid'),False),
                    ('负数超时',dict(timeout=-1),False),('非法超时',dict(timeout='invalid'),False),
                    ('非法锚点',dict(anchor='invalid'),False),
                    ('负数延时',dict(seconds=0.2,delay_after=-1),True),('非法延时',dict(seconds=0.2,delay_after='invalid'),True)]:
                    results.append(helper.run_case(name,lambda k=kwargs,a=acted:check(kwargs=k,error=InvalidParamsError,acted=a)))
                    if user32.GetAsyncKeyState(1)&0x8000: break
    finally:
        def cleanup():
            errors=[]
            def restore_focus():
                nonlocal focus_status
                focus_status=restore_focus_for_mode(foreground,non_interactive)
            if user32.GetAsyncKeyState(1)&0x8000:
                # 确认起始左键未按下；释放本次异常遗留的左键再移动鼠标。
                if initially_released:
                    user32.mouse_event(0x0004,0,0,0,0)
                    errors.append('检测到遗留左键按下，已发送释放；需排查长按清理')
                else:
                    raise RuntimeError('用户左键仍按下，未执行鼠标移动恢复，请先松开左键')
            actions=[('前台',restore_focus),('鼠标',lambda:helper.restore_cursor(mouse))]
            if package is not None: actions.append(('Package',package.close))
            for name,action in actions:
                try: action()
                except Exception as exc: errors.append(f'{name}: {exc}')
            if errors: raise RuntimeError('；'.join(errors))
            return '左键已释放，鼠标已恢复，Package已关闭（如已取得）',[f'焦点: {focus_status}']
        results.append(helper.run_case('资源清理',cleanup))
        helper.render_results(results)
    passed=sum(r.passed for r in results)
    ok=passed==len(results)
    print(helper.colored('\n测试通过' if ok else '\n测试失败',helper.ANSI_GREEN if ok else helper.ANSI_RED))
    print(f"  生命周期: {'VERIFIED' if ok else 'READY_FOR_LIVE'}\n  结果: {passed}/{len(results)} 通过\n  总耗时: {(time.perf_counter()-started)*1000:.1f}ms\n  退出码: {0 if ok else 1}")
    print(f'  焦点恢复: {focus_status}')
    return 0 if ok else 1


if __name__=='__main__':
    raise SystemExit(main(non_interactive=parse_run_options().non_interactive))
