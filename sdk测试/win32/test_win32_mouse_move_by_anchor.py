r"""win32.mouse_move_by_anchor(rectangle, anchor=None, relative_to='screen',
move_speed=None, delay_after=1) -> None。

用途：把鼠标移到矩形的指定锚点；不点击。
API五参数均可按位置或关键字传入，rectangle必填：(x,y,w,h)元组/列表，
或x/y/w/h及left/top/width/height字典，或有get_bounding()的对象。
anchor使用下划线名称（如middle_center、top_left），支持中心默认、九宫格、random及偏移。
异常用例打印异常类型、消息、调用参数和移动前后坐标，即使位置断言失败也保留这些诊断。
relative_to为screen/window/position；move_speed为None/instant/fast/middle/slow；
delay_after为动作后秒数，None/0不等待，非法延时可能在移动后才拒绝。
脚本参数：--non-interactive 焦点恢复失败仅警告；默认人工模式。
运行：uv run .\win32\test_win32_mouse_move_by_anchor.py --non-interactive
前置：dev、可见未最小化靶场运行；测试期间不要操作鼠标。无需元素库/剪贴板。
使用屏幕矩形(100,100,120,80)，原生GetCursorPos核验结果；窗口相对场景会激活靶场。
带get_bounding对象使用固定物理矩形，不宣称验证真实元素默认96 DPI边界转换。
结束恢复鼠标和前台，不关闭靶场。复用现有DPI、日志、焦点辅助函数。
"""

import inspect
import time
from types import SimpleNamespace
from uiautoma import win32,InvalidParamsError
import test_win32_get_value as helper
from test_win32_highlight import focus_api,restore_focus_for_mode,parse_run_options

RECT=(100,100,120,80)
ANCHORS=('top_left','top_center','top_right','middle_left','middle_center','middle_right','bottom_left','bottom_center','bottom_right')


def point(name='middle_center',ox=0,oy=0):
    i=ANCHORS.index(name)
    return (round(RECT[0]+(i%3)*RECT[2]/2+ox),round(RECT[1]+(i//3)*RECT[3]/2+oy))


def contract():
    sig=inspect.signature(win32.mouse_move_by_anchor)
    assert list(sig.parameters)==['rectangle','anchor','relative_to','move_speed','delay_after'],sig
    assert sig.parameters['rectangle'].default is inspect.Parameter.empty,sig
    for name,value in [('anchor',None),('relative_to','screen'),('move_speed',None),('delay_after',1)]:
        assert sig.parameters[name].default==value,sig
    assert all(p.kind==p.POSITIONAL_OR_KEYWORD for p in sig.parameters.values()),sig
    assert sig.return_annotation in (None,'None',type(None)),sig
    return '五参数与默认值符合合同，返回None'


def main(non_interactive=False):
    print('UIAutoma Win32 API 测试\n  API: win32.mouse_move_by_anchor')
    print(f'  屏幕矩形: {RECT}\n  原生参照: GetCursorPos；只移动不点击')
    results=[helper.run_case('API 合同',contract)]
    mouse,foreground=helper.current_cursor(),helper.current_foreground()
    focus_status='未检查'
    native=focus_api()
    target=None
    started=time.perf_counter()
    speeds={}

    def prepare():
        nonlocal target
        assert native.GetSystemMetrics(0)>260 and native.GetSystemMetrics(1)>220,'主屏空间不足'
        target=win32.get(title='Win32 靶场 - UIA',process_name='win32-shooting-range-uia.exe',timeout=5)
        handle=target.get_detail('handle')
        assert native.IsWindowVisible(handle) and not native.IsIconic(handle),'请显示并恢复靶场'
        return '屏幕范围和靶场窗口已就绪'

    def move(args=(),kwargs=None,expected=None,random=False,error=None):
        kwargs=kwargs or {}
        helper.restore_cursor((50,50))
        before=helper.current_cursor()
        begin=time.perf_counter()
        caught=None
        returned=None
        try:returned=win32.mouse_move_by_anchor(*args,**kwargs)
        except Exception as exc:caught=exc
        elapsed=(time.perf_counter()-begin)*1000
        actual=helper.current_cursor()
        diagnostic=(f'调用: mouse_move_by_anchor{args!r} {kwargs!r}；'
                    f'异常类型: {type(caught).__name__ if caught is not None else "无"}；'
                    f'异常消息: {str(caught) if caught is not None else "无"}；'
                    f'移动前: {before}；移动后: {actual}；预期: {expected if expected is not None else before}；'
                    f'耗时: {elapsed:.1f}ms')
        if caught is not None or error is not None:
            print('  异常用例诊断: '+diagnostic,flush=True)
        if error:
            assert isinstance(caught,error),f'预期{error.__name__}；{diagnostic}'
        elif caught:raise caught
        else:assert returned is None,returned
        if random:
            assert 100<=actual[0]<220 and 100<=actual[1]<180,actual
        else:
            expected=before if expected is None else expected
            assert actual==expected,diagnostic
        return elapsed,actual

    def check(args=(),kwargs=None,expected=None,random=False,error=None):
        elapsed,actual=move(args,kwargs,expected,random,error)
        return '原生鼠标位置和返回/异常符合预期',[f'调用: mouse_move_by_anchor{args!r} {kwargs or {}!r}',f'实际坐标: {actual}；调用耗时: {elapsed:.1f}ms']

    def window_case():
        target.activate()
        handle=target.get_detail('handle')
        assert native.GetForegroundWindow()==handle,'靶场激活未完成'
        x,y,w,h=helper.window_rect(handle,helper._user32())
        result=check((RECT,'middle_center','window','instant',0),expected=(x+160,y+140))
        assert native.GetForegroundWindow()==handle,'移动期间前台变化'
        return result

    def speed_case(speed):
        elapsed,actual=move((RECT,),dict(move_speed=speed,delay_after=0),point())
        speeds[speed]=elapsed
        return '对应速度移动到中心，原生坐标正确',[f'{speed}: {elapsed:.1f}ms；坐标: {actual}']

    def speed_order():
        assert set(speeds)=={'instant','fast','middle','slow'},'速度用例未全部成功'
        assert speeds['fast']>speeds['instant']+30 and speeds['middle']>speeds['fast']+30 and speeds['slow']>speeds['middle']+30,f'速度耗时未呈阶梯差异: {speeds}；系统忙时复测'
        return '相同起止点的速度耗时呈instant、fast、middle、slow递增'

    def delay_pair():
        base,_=move((RECT,),dict(move_speed='instant',delay_after=0),point())
        extra,_=move((RECT,),dict(move_speed='instant',delay_after=0.3),point())
        assert 220<=extra-base<=450,f'0.3秒延时差值不符: {extra-base:.1f}ms'
        return f'配对延时增加{extra-base:.1f}ms，符合约300ms'

    try:
        ready=helper.run_case('测试准备',prepare)
        results.append(ready)
        if ready.passed:
            results.append(helper.run_case('默认参数',lambda:check((RECT,),expected=point())))
            results.append(helper.run_case('全位置参数',lambda:check((RECT,'middle_center','screen','instant',0),expected=point())))
            results.append(helper.run_case('全关键字',lambda:check(kwargs=dict(rectangle=RECT,anchor='middle_center',relative_to='screen',move_speed='instant',delay_after=0),expected=point())))
            for name,rect in [('列表',list(RECT)),('短字段字典',dict(x=100,y=100,w=120,h=80)),('长字段字典',dict(left=100,top=100,width=120,height=80)),('边界对象',SimpleNamespace(get_bounding=lambda:RECT))]:
                results.append(helper.run_case('矩形'+name,lambda r=rect:check((r,),dict(move_speed='instant',delay_after=0),point())))
            for anchor in ANCHORS:
                results.append(helper.run_case('锚点'+anchor,lambda a=anchor:check((RECT,a),dict(move_speed='instant',delay_after=0),point(a))))
            results.append(helper.run_case('随机锚点',lambda:check((RECT,'random'),dict(move_speed='instant',delay_after=0),random=True)))
            results.append(helper.run_case('三元组偏移',lambda:check((RECT,('middle_center',6,-4)),dict(move_speed='instant',delay_after=0),point(ox=6,oy=-4))))
            results.append(helper.run_case('字典偏移',lambda:check((RECT,dict(anchor='middle_center',offset_x=-6,offset_y=4)),dict(move_speed='instant',delay_after=0),point(ox=-6,oy=4))))
            results.append(helper.run_case('文档下划线锚点',lambda:check((RECT,'top_left'),dict(move_speed='instant',delay_after=0),point('top_left'))))
            results.append(helper.run_case('当前位置相对',lambda:check((RECT,None,'position','instant',0),expected=(210,190))))
            results.append(helper.run_case('活动窗口相对',window_case))
            for speed in ('instant','fast','middle','slow'):
                results.append(helper.run_case('速度'+speed,lambda s=speed:speed_case(s)))
            results.append(helper.run_case('速度差异',speed_order))
            results.append(helper.run_case('None延时',lambda:check((RECT,),dict(move_speed='instant',delay_after=None),point())))
            results.append(helper.run_case('配对延时',delay_pair))
            for name,args,kwargs,expected in [
                ('非法矩形',(None,),{},None),('非正尺寸',((100,100,0,80),),{},None),
                ('非法锚点',(RECT,'invalid'),{},None),('非法坐标系',(RECT,),dict(relative_to='invalid'),None),
                ('非法速度',(RECT,),dict(move_speed='invalid'),None),
                ('负数延时',(RECT,),dict(move_speed='instant',delay_after=-1),point()),
                ('非数字延时',(RECT,),dict(move_speed='instant',delay_after='invalid'),point())]:
                results.append(helper.run_case(name,lambda a=args,k=kwargs,e=expected:check(a,k,e,error=InvalidParamsError)))
    finally:
        def cleanup():
            nonlocal focus_status
            errors=[]
            def focus():
                nonlocal focus_status
                focus_status=restore_focus_for_mode(foreground,non_interactive)
            for name,action in [('前台',focus),('鼠标',lambda:helper.restore_cursor(mouse))]:
                try:action()
                except Exception as exc:errors.append(f'{name}: {exc}')
            if helper.current_cursor()!=mouse:errors.append('原鼠标位置未恢复')
            if errors:raise RuntimeError('；'.join(errors))
            return '原鼠标位置已恢复并核验，靶场保持运行',[f'焦点: {focus_status}']
        results.append(helper.run_case('资源清理',cleanup))
        helper.render_results(results)
    passed=sum(r.passed for r in results)
    ok=passed==len(results)
    print(helper.colored('\n测试通过' if ok else '\n测试失败',helper.ANSI_GREEN if ok else helper.ANSI_RED))
    print(f"  生命周期: {'VERIFIED' if ok else 'READY_FOR_LIVE'}\n  结果: {passed}/{len(results)} 通过\n  总耗时: {(time.perf_counter()-started)*1000:.1f}ms\n  退出码: {0 if ok else 1}")
    return 0 if ok else 1


if __name__=='__main__':
    raise SystemExit(main(non_interactive=parse_run_options().non_interactive))
