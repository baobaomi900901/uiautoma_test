r"""win32.mouse_click_by_anchor(rectangle, anchor=None, relative_to='screen', button='left',
click_type='click', keys='none', delay_after=1, move_mouse=True) -> None。

用途：在矩形指定锚点点击；八参数均可位置/关键字传入，rectangle必填。
矩形支持元组/列表、两种字段字典或get_bounding对象；锚点用snake_case、random及偏移。
relative_to支持screen/window/position；button支持left/right/middle；click_type支持
click/doubleClick/dbclick/dblclick；keys本轮仅none、ctrl、shift、ctrl+shift，不测alt/win。
move_mouse=False用例预先把鼠标放在目标点，不宣称该模式会自动移动。
delay_after是点击后等待，非法延时可能在点击后拒绝。
脚本参数：--non-interactive 自动复测，焦点恢复失败仅警告。
前置：dev、靶场运行，启用 D:\code\元素库\260902_win元素，drag-target可见。
仅点击drag-target内部矩形，不输入数据、不点保存/隐藏/重置。测试期间勿操作鼠标。
检查鼠标位置、返回值、按键释放、目标边界不变；通过只读WH_MOUSE_LL记录按下/抬起，
核对鼠标键、单击/双击次数、事件坐标及按下时修饰键。不证明目标程序已消费这些事件。
结束恢复鼠标/前台、释放Package，保留拖拽页，不使用剪贴板。
"""

import ctypes
import inspect
import time
from pathlib import Path
from types import SimpleNamespace
from uiautoma import current,win32,InvalidParamsError
import test_win32_get_value as helper
from test_win32_get_anchor_position import native_target
from test_win32_highlight import focus_api,restore_focus_for_mode,parse_run_options
from _mouse_event_probe import MouseEventProbe, verify_click_events

ANCHORS=('top_left','top_center','top_right','middle_left','middle_center','middle_right','bottom_left','bottom_center','bottom_right')


def anchor_xy(rect,name='middle_center',ox=0,oy=0):
    x,y,w,h=rect
    i=ANCHORS.index(name)
    return round(x+(i%3)*w/2+ox),round(y+(i//3)*h/2+oy)


def contract():
    sig=inspect.signature(win32.mouse_click_by_anchor)
    defaults=dict(anchor=None,relative_to='screen',button='left',click_type='click',keys='none',delay_after=1,move_mouse=True)
    assert list(sig.parameters)==['rectangle',*defaults],sig
    assert sig.parameters['rectangle'].default is inspect.Parameter.empty,sig
    for k,v in defaults.items(): assert sig.parameters[k].default==v,sig
    assert all(p.kind==p.POSITIONAL_OR_KEYWORD for p in sig.parameters.values()),sig
    assert sig.return_annotation in (None,'None',type(None)),sig
    return '八个参数、默认值及传参规则符合合同'


def main(non_interactive=False):
    print('UIAutoma Win32 API 测试\n  API: win32.mouse_click_by_anchor')
    print('  对象: drag-target内部矩形；原生钩子核验点击键/次数/坐标及按下时修饰键')
    results=[helper.run_case('API 合同',contract)]
    package=window=hwnd=rect=None
    target_bounds=None
    original_mouse,foreground=helper.current_cursor(),helper.current_foreground()
    native=focus_api()
    native.GetAsyncKeyState.argtypes=[ctypes.c_int]
    native.GetAsyncKeyState.restype=ctypes.c_short
    focus_status='未检查'
    started=time.perf_counter()

    def released():
        pressed=[key for key in (1,2,4,16,17,18,91,92) if native.GetAsyncKeyState(key)&0x8000]
        assert not pressed,f'按键仍按下: {pressed}，请松开后复测'

    def prepare():
        nonlocal package,window,hwnd,rect,target_bounds
        released()
        package=current(required=True,refresh=True,timeout=5)
        assert Path(package.package_dir).resolve()==Path(r'D:\code\元素库\260902_win元素').resolve()
        window=win32.get(title='Win32 靶场 - UIA',process_name='win32-shooting-range-uia.exe',timeout=5)
        window.find(package.selector('win32靶场_tab_item拖拽测试',kind='win'),timeout=5).click(delay_after=0.2)
        hwnd=native_target(window.get_detail('handle'))
        target_bounds=helper.window_rect(hwnd,helper._user32())
        x,y,w,h=target_bounds
        assert w>50 and h>50,'目标太小'
        rect=(x+20,y+20,w-40,h-40)
        return '目标已定位，点击范围内缩20物理像素',[f'目标边界: {target_bounds}；测试矩形: {rect}']

    def invoke(args=(),kwargs=None,expected=None,random=False,error=None):
        kwargs=kwargs or {}
        released()
        assert helper.window_rect(hwnd,helper._user32())==target_bounds,'目标发生移动'
        start=anchor_xy(rect)
        helper.restore_cursor(start)
        bound=inspect.signature(win32.mouse_click_by_anchor).bind(*args,**kwargs)
        bound.apply_defaults()
        params=bound.arguments
        probe=MouseEventProbe()
        probe.start()
        begin=time.perf_counter()
        returned=caught=None
        try: returned=win32.mouse_click_by_anchor(*args,**kwargs)
        except Exception as exc:caught=exc
        finally:
            elapsed=(time.perf_counter()-begin)*1000
            time.sleep(0.03)  # 让观察线程处理末尾事件，不计入API耗时。
            probe.close()
        actual=helper.current_cursor()
        diagnostic=f'异常={type(caught).__name__ if caught else None}: {caught}；前={start}；后={actual}；耗时={elapsed:.1f}ms；原生事件={probe.events}'
        if error:
            assert isinstance(caught,error),diagnostic
        elif caught:raise caught
        else:assert returned is None,returned
        if random:
            x,y,w,h=rect
            assert x<=actual[0]<=x+w and y<=actual[1]<=y+h,diagnostic
        else: assert actual==(expected or start),diagnostic
        released()
        assert helper.window_rect(hwnd,helper._user32())==target_bounds,'点击拖动了目标'
        # 本脚本的两个非法延时用例预期先点击，其他非法参数预期不产生点击。
        clicked=error is None or params['delay_after'] in (-1,'bad')
        event_detail=verify_click_events(probe.events,params['button'],params['click_type'],params['keys'],actual,clicked)
        diagnostic += '；'+event_detail
        return elapsed,diagnostic

    def check(args=(),kwargs=None,expected=None,random=False,error=None):
        elapsed,diagnostic=invoke(args,kwargs,expected,random,error)
        return '坐标/点击事件/修饰键符合预期，按键已释放、目标未移动',[f'调用: mouse_click_by_anchor{args!r} {kwargs or {}!r}',diagnostic]

    def window_relative():
        handle=window.get_detail('handle')
        assert native.GetForegroundWindow()==handle,'靶场不是前台，窗口相对场景不成立'
        wx,wy,_,_=helper.window_rect(handle,helper._user32())
        x,y,w,h=rect
        return check(((x-wx,y-wy,w,h),),dict(relative_to='window',delay_after=0),anchor_xy(rect))

    def position_relative():
        x,y,w,h=rect
        sx,sy=anchor_xy(rect)
        return check(((x-sx,y-sy,w,h),),dict(relative_to='position',delay_after=0),anchor_xy(rect))

    def delay_pair():
        base,_=invoke((rect,),dict(delay_after=0))
        extra,_=invoke((rect,),dict(delay_after=0.3))
        assert 200<=extra-base<=500,f'额外延时差值{extra-base:.1f}ms不符'
        return f'相同调用配对增加{extra-base:.1f}ms，符合约300ms'

    try:
        ready=helper.run_case('测试准备',prepare)
        results.append(ready)
        if ready.passed:
            results.append(helper.run_case('默认参数',lambda:check((rect,))))
            results.append(helper.run_case('全位置参数',lambda:check((rect,'middle_center','screen','left','click','none',0,True))))
            results.append(helper.run_case('全关键字',lambda:check(kwargs=dict(rectangle=rect,anchor='middle_center',relative_to='screen',button='left',click_type='click',keys='none',delay_after=0,move_mouse=True))))
            x,y,w,h=rect
            for name,r in [('列表',list(rect)),('短字段',dict(x=x,y=y,w=w,h=h)),('长字段',dict(left=x,top=y,width=w,height=h)),('边界对象',SimpleNamespace(get_bounding=lambda:rect))]:
                results.append(helper.run_case('矩形'+name,lambda r=r:check((r,),dict(delay_after=0))))
            for anchor in ANCHORS:
                results.append(helper.run_case(anchor,lambda a=anchor:check((rect,a),dict(delay_after=0),anchor_xy(rect,a))))
            results.append(helper.run_case('random',lambda:check((rect,'random'),dict(delay_after=0),random=True)))
            results.append(helper.run_case('三元组偏移',lambda:check((rect,('middle_center',4,-3)),dict(delay_after=0),anchor_xy(rect,ox=4,oy=-3))))
            results.append(helper.run_case('字典偏移',lambda:check((rect,dict(anchor='middle_center',offset_x=-4,offset_y=3)),dict(delay_after=0),anchor_xy(rect,ox=-4,oy=3))))
            for button in ('right','middle'):
                results.append(helper.run_case(button+'单击',lambda b=button:check((rect,),dict(button=b,delay_after=0))))
            for kind in ('doubleClick','dbclick','dblclick'):
                results.append(helper.run_case(kind,lambda k=kind:check((rect,),dict(click_type=k,delay_after=0))))
            for keys in ('ctrl','shift','ctrl+shift'):
                results.append(helper.run_case(keys,lambda k=keys:check((rect,),dict(keys=k,delay_after=0))))
            results.append(helper.run_case('不移动鼠标',lambda:check((rect,),dict(move_mouse=False,delay_after=0))))
            results.append(helper.run_case('窗口相对',window_relative))
            results.append(helper.run_case('当前位置相对',position_relative))
            results.append(helper.run_case('None延时',lambda:check((rect,),dict(delay_after=None))))
            results.append(helper.run_case('配对延时',delay_pair))
            for name,k in [('非法键',dict(button='bad')),('非法类型',dict(click_type='bad')),('非法修饰键',dict(keys='bad')),
                           ('非法锚点',dict(anchor='bad')),('非法坐标系',dict(relative_to='bad')),
                           ('负数延时',dict(delay_after=-1)),('非数字延时',dict(delay_after='bad'))]:
                results.append(helper.run_case(name,lambda k=k:check((rect,),k,error=InvalidParamsError)))
    finally:
        def cleanup():
            nonlocal focus_status
            errors=[]
            try:released()
            except Exception as exc:errors.append(str(exc))
            def focus():
                nonlocal focus_status
                focus_status=restore_focus_for_mode(foreground,non_interactive)
            # 按键遗留时不移动鼠标，避免把按住状态变成拖拽。
            actions=[] if errors else [('前台',focus),('鼠标',lambda:helper.restore_cursor(original_mouse))]
            if package is not None:actions.append(('Package',package.close))
            for name,action in actions:
                try:action()
                except Exception as exc:errors.append(f'{name}: {exc}')
            if errors:raise RuntimeError('；'.join(errors))
            return '按键已释放，鼠标恢复，Package释放；靶场保持运行',[f'焦点: {focus_status}']
        results.append(helper.run_case('资源清理',cleanup))
        helper.render_results(results)
    passed=sum(r.passed for r in results)
    ok=passed==len(results)
    print(helper.colored('\n本轮检查通过' if ok else '\n测试失败',helper.ANSI_GREEN if ok else helper.ANSI_RED))
    print(f"  生命周期: READY_FOR_LIVE\n  结果: {passed}/{len(results)} 通过\n  总耗时: {(time.perf_counter()-started)*1000:.1f}ms\n  退出码: {0 if ok else 1}")
    print('  覆盖边界: 已核验系统鼠标事件次数及按下时修饰键；未自动验证靶场应用对事件的业务处理')
    return 0 if ok else 1


if __name__=='__main__':
    raise SystemExit(main(non_interactive=parse_run_options().non_interactive))
