r"""顶层win32.find(selector: str|Selector, *, timeout=20, session=None) -> Win32Element。

用途：在当前或指定Package中查找唯一Win32元素，无需先构造所属窗口。
selector必填，可位置/关键字；timeout/session仅限关键字。timeout=0单次，-1无限等待；
None默认20秒、数字字符串可转换。无匹配ElementNotFoundError，多项AmbiguousElementError。
session=None使用当前上下文；显式uiautoma.current()的返回对象按文档作为正常用例。
脚本参数：--non-interactive 不等待人工恢复焦点；默认人工模式。
运行：uv run .\win32\test_win32_module_find.py --non-interactive
前置：dev及靶场运行，启用 D:\code\元素库\260902_win元素。
切换表单页，以姓名输入框、保存按钮验证返回对象及来源ID。无需点击目标或输入文本。
不制造多项命中，不验证AmbiguousElementError；不测试目标销毁或无限等待后出现。
结束恢复鼠标/前台、释放Package，靶场保留表单页。不会使用内部session绕过公开入参校验。
"""

import inspect
import time
import uuid
from pathlib import Path
from uiautoma import current,win32,InvalidParamsError,ElementNotFoundError
from uiautoma.selector import Selector
from uiautoma.win32 import Win32Element
from _form_tab import ensure_form_tab
import test_win32_get_value as helper
from test_win32_highlight import restore_focus_for_mode,parse_run_options

INPUT='win32靶场_表单控件_输入框_姓名'
SAVE='win32靶场_表单控件_按钮_保存'


def contract():
    sig=inspect.signature(win32.find)
    assert list(sig.parameters)==['selector','timeout','session'],sig
    p=sig.parameters['selector']
    assert p.default is p.empty and p.kind==p.POSITIONAL_OR_KEYWORD,sig
    for name,value in [('timeout',20),('session',None)]:
        p=sig.parameters[name]
        assert p.kind==p.KEYWORD_ONLY and p.default==value,sig
    assert 'Win32Element' in str(sig.return_annotation),sig
    return 'selector必填，timeout/session仅限关键字，返回Win32Element'


def main(non_interactive=False):
    print('UIAutoma Win32 API 测试\n  API: 顶层win32.find\n  目标: 姓名输入框、保存按钮')
    print('  覆盖: 唯一命中及参数规则；不覆盖多项命中')
    results=[helper.run_case('API 合同',contract)]
    package=None
    selectors={}
    mouse,foreground=helper.current_cursor(),helper.current_foreground()
    focus_status='未检查'
    started=time.perf_counter()

    def prepare():
        nonlocal package,selectors
        package=current(required=True,refresh=True,timeout=5)
        assert Path(package.package_dir).resolve()==Path(r'D:\code\元素库\260902_win元素').resolve()
        ensure_form_tab(package)
        selectors={name:package.selector(name,kind='win') for name in (INPUT,SAVE)}
        return '当前Package和两个Win32 Selector已准备',[f'显式session类型: {type(package).__name__}']

    def success(selector,name,kwargs=None,keyword=False):
        kwargs=kwargs or {}
        result=win32.find(selector=selector,**kwargs) if keyword else win32.find(selector,**kwargs)
        assert isinstance(result,Win32Element),type(result)
        assert result.name==name,f'返回名称{result.name!r}，预期{name!r}'
        assert result.raw.get('source_element_id')==selectors[name].id(),result.raw
        bounds=result.get_bounding(to96dpi=False,relative_to='screen')
        assert len(bounds)==4 and bounds[2]>0 and bounds[3]>0,bounds
        return '返回唯一Runtime元素，来源ID及名称正确、实时边界有效',[f'名称: {result.name}；source_id: {result.raw.get("source_element_id")}；边界: {bounds}']

    def rejected(call,error):
        try: call()
        except error: return f'{error.__name__}正确报告'
        raise AssertionError(f'没有抛出{error.__name__}')

    try:
        ready=helper.run_case('测试准备',prepare)
        results.append(ready)
        if ready.passed:
            cases=[('名称默认调用',INPUT,INPUT,{},False),
                   ('Selector零超时',selectors[INPUT],INPUT,dict(timeout=0),False),
                   ('名称关键字',SAVE,SAVE,dict(timeout=2),True),
                   ('显式None上下文',INPUT,INPUT,dict(session=None,timeout=0),False),
                   ('显式Package上下文',selectors[INPUT],INPUT,dict(session=package,timeout=0),False),
                   ('None超时',INPUT,INPUT,dict(timeout=None),False),
                   ('数字字符串超时',INPUT,INPUT,dict(timeout='0.5'),False),
                   ('无限值已有目标',INPUT,INPUT,dict(timeout=-1),False)]
            for name,selector,expected,kwargs,keyword in cases:
                results.append(helper.run_case(name,lambda s=selector,n=expected,k=kwargs,b=keyword:success(s,n,k,b)))
            missing='__missing_'+uuid.uuid4().hex
            results.append(helper.run_case('不存在名称',lambda:rejected(lambda:win32.find(missing,timeout=0),ElementNotFoundError)))
            def invalid_selector():
                for value in (None,123,[],{'name':INPUT}):
                    rejected(lambda v=value:win32.find(v,timeout=0),InvalidParamsError)
                return 'None、整数、列表、字典均被InvalidParamsError拒绝'
            results.append(helper.run_case('非法selector',invalid_selector))
            results.append(helper.run_case('Web Selector',lambda:rejected(lambda:win32.find(Selector(name='web',framework='web',item_id=selectors[INPUT].id()),timeout=0),InvalidParamsError)))
            results.append(helper.run_case('非法session',lambda:rejected(lambda:win32.find(INPUT,session=object(),timeout=0),InvalidParamsError)))
            def invalid_timeout():
                for value in (-2,'bad'):
                    rejected(lambda v=value:win32.find(INPUT,timeout=v),InvalidParamsError)
                return '非法timeout被InvalidParamsError拒绝'
            results.append(helper.run_case('非法超时',invalid_timeout))
            def arguments():
                for call in (lambda:win32.find(),lambda:win32.find(INPUT,0),lambda:win32.find(INPUT,unknown=1)):
                    rejected(call,TypeError)
                return '缺参、多余位置参数及未知关键字被TypeError拒绝'
            results.append(helper.run_case('调用参数边界',arguments))
    finally:
        def cleanup():
            nonlocal focus_status
            errors=[]
            def focus():
                nonlocal focus_status
                focus_status=restore_focus_for_mode(foreground,non_interactive)
            actions=[('前台',focus),('鼠标',lambda:helper.restore_cursor(mouse))]
            if package is not None:actions.append(('Package',package.close))
            for name,action in actions:
                try:action()
                except Exception as exc:errors.append(f'{name}: {exc}')
            if errors:raise RuntimeError('；'.join(errors))
            return '鼠标恢复、Package释放（如已取得）；靶场保留表单页',[f'焦点: {focus_status}']
        results.append(helper.run_case('资源清理',cleanup))
        helper.render_results(results)
    passed=sum(r.passed for r in results)
    ok=passed==len(results)
    print(helper.colored('\n测试通过' if ok else '\n测试失败',helper.ANSI_GREEN if ok else helper.ANSI_RED))
    print(f"  生命周期: {'VERIFIED' if ok else 'READY_FOR_LIVE'}\n  结果: {passed}/{len(results)} 通过\n  总耗时: {(time.perf_counter()-started)*1000:.1f}ms\n  退出码: {0 if ok else 1}")
    return 0 if ok else 1


if __name__=='__main__':
    raise SystemExit(main(non_interactive=parse_run_options().non_interactive))
