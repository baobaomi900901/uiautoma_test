r"""顶层win32.find_all(selector, *, timeout=20, session=None) -> list[Win32Element]。

用途：查找当前或指定Package中所有匹配的Win32元素，未找到返回[]。
selector必填，可位置/关键字，接受名称字符串或Win32 Selector；timeout/session仅限关键字。
timeout=0单次、正数有限等待、-1无限等待；None默认20秒，数字字符串可转换。
session=None使用当前上下文；显式current()返回的Package按正常用例测试，不用私有会话绕过。
脚本参数：--non-interactive 自动模式，焦点恢复失败仅警告；默认人工模式。
运行：uv run .\win32\test_win32_module_find_all.py --non-interactive
前置：dev、靶场运行，启用 D:\code\元素库\260902_win元素。
先使用表单页姓名输入框和保存按钮验证参数，再切换表格页，以相似单元格选择器验证多项。
表格请保持第1页（含文本1和用户1）；不翻页、不改元素库、不固定多项总数。
查询不修改内容，结束恢复鼠标/前台并释放Package，保留表格页。
"""

import inspect
import time
import uuid
from pathlib import Path
from uiautoma import current,win32,InvalidParamsError
from uiautoma.selector import Selector
from uiautoma.win32 import Win32Element
from _form_tab import ensure_form_tab
import test_win32_get_value as helper
from test_win32_highlight import restore_focus_for_mode,parse_run_options

INPUT='win32靶场_表单控件_输入框_姓名'
SAVE='win32靶场_表单控件_按钮_保存'
FIRST_CELL='win32靶场_表格数据_list首个单元格'
NORMAL_CELL='win32靶场_表格数据_list普通单元格'
SIMILAR_CELLS='win32靶场_表格数据_list普通单元格_相似元素'


def contract():
    sig=inspect.signature(win32.find_all)
    assert list(sig.parameters)==['selector','timeout','session'],sig
    p=sig.parameters['selector']
    assert p.default is p.empty and p.kind==p.POSITIONAL_OR_KEYWORD,sig
    for name,value in [('timeout',20),('session',None)]:
        p=sig.parameters[name]
        assert p.kind==p.KEYWORD_ONLY and p.default==value,sig
    assert str(sig.return_annotation)=='list[Win32Element]',sig
    return 'selector必填，timeout/session仅限关键字，返回list[Win32Element]'


def validate_items(items,name,source_id):
    assert type(items) is list and len(items)==1,f'预期唯一目标组成的列表，实际{items!r}'
    item=items[0]
    assert isinstance(item,Win32Element),type(item)
    assert item.name==name and item.raw.get('source_element_id')==source_id,item.raw
    return item


def main(non_interactive=False):
    print('UIAutoma Win32 API 测试\n  API: 顶层win32.find_all')
    print('  目标: 表单元素及表格单元格\n  覆盖: 单项、空列表、多项命中及参数规则；表格需停留第1页')
    results=[helper.run_case('API 合同',contract)]
    package=None
    selectors={}
    cell_references=set()
    mouse,foreground=helper.current_cursor(),helper.current_foreground()
    focus_status='未检查'
    started=time.perf_counter()

    def prepare():
        nonlocal package,selectors
        package=current(required=True,refresh=True,timeout=5)
        assert Path(package.package_dir).resolve()==Path(r'D:\code\元素库\260902_win元素').resolve()
        ensure_form_tab(package)
        selectors={name:package.selector(name,kind='win') for name in (INPUT,SAVE)}
        return '当前Package与Selector已准备',[f'session类型: {type(package).__name__}']

    def success(selector,name,kwargs=None,keyword=False):
        kwargs=kwargs or {}
        items=win32.find_all(selector=selector,**kwargs) if keyword else win32.find_all(selector,**kwargs)
        item=validate_items(items,name,selectors[name].id())
        bounds=item.get_bounding(to96dpi=False,relative_to='screen')
        assert len(bounds)==4 and bounds[2]>0 and bounds[3]>0,bounds
        return '返回单项Win32Element列表，名称/来源ID及实时边界正确',[f'数量: {len(items)}；名称: {item.name}；边界: {bounds}']

    def missing(timeout):
        returned=win32.find_all('__missing_'+uuid.uuid4().hex,timeout=timeout)
        assert type(returned) is list and returned==[],returned
        return f'不存在的元素名返回[]，timeout={timeout}'

    def reject(call,error):
        try:call()
        except error:return f'{error.__name__}正确拒绝'
        raise AssertionError(f'没有抛出{error.__name__}')

    def identity(item):
        assert isinstance(item,Win32Element),type(item)
        value=item.get_attribute('RuntimeId')
        assert isinstance(value,str) and value,f'单元格RuntimeId无效: {value!r}'
        return value

    def prepare_table():
        nonlocal cell_references
        window=win32.get(title='Win32 靶场 - UIA',process_name='win32-shooting-range-uia.exe',timeout=5)
        tab=window.find(package.selector('win32靶场_tab_item表格数据',kind='win'),timeout=5)
        tab.click(delay_after=0.2)
        ids=[]
        for name,text in ((FIRST_CELL,'1'),(NORMAL_CELL,'用户1')):
            selector=package.selector(name,kind='win')
            matches=win32.find_all(selector,timeout=2)
            assert type(matches) is list and len(matches)==1,f'{name}预期唯一参照，实际{len(matches)}项；请确认表格第1页'
            assert matches[0].get_text()==text,f'{name}文本不符'
            ids.append(identity(matches[0]))
        assert len(set(ids))==2,'两个参照元素指向同一控件'
        cell_references=set(ids)
        return '表格页已打开，文本1与用户1分别定位到不同单元格'

    def multiple(use_selector):
        selector=package.selector(SIMILAR_CELLS,kind='win')
        value=selector if use_selector else SIMILAR_CELLS
        matches=win32.find_all(value,timeout=0)
        assert type(matches) is list and len(matches)>1,f'相似选择器应命中多项，实际{matches!r}'
        ids=[]
        texts=[]
        for item in matches:
            assert isinstance(item,Win32Element),type(item)
            assert item.raw.get('source_element_id')==selector.id(),'返回项未关联相似选择器'
            ids.append(identity(item))
            texts.append(item.get_text())
        assert len(set(ids))==len(ids),'多项结果重复包含同一个Runtime控件'
        assert cell_references.issubset(set(ids)),'相似结果未包含首个及普通参照单元格'
        return '返回多个不同Runtime单元格，包含两个指定参照元素',[f'数量: {len(matches)}；前10项文本: {texts[:10]!r}']

    try:
        ready=helper.run_case('测试准备',prepare)
        results.append(ready)
        if ready.passed:
            for name,selector,expected,kwargs,keyword in [
                ('名称默认调用',INPUT,INPUT,{},False),
                ('Selector零超时',selectors[INPUT],INPUT,dict(timeout=0),False),
                ('名称关键字',SAVE,SAVE,dict(timeout=2),True),
                ('显式None上下文',INPUT,INPUT,dict(session=None,timeout=0),False),
                ('显式Package上下文',selectors[INPUT],INPUT,dict(session=package,timeout=0),False),
                ('None超时',INPUT,INPUT,dict(timeout=None),False),
                ('数字字符串超时',INPUT,INPUT,dict(timeout='0.5'),False),
                ('无限值已有目标',INPUT,INPUT,dict(timeout=-1),False)]:
                results.append(helper.run_case(name,lambda s=selector,n=expected,k=kwargs,b=keyword:success(s,n,k,b)))
            results.append(helper.run_case('未找到零超时',lambda:missing(0)))
            results.append(helper.run_case('未找到有限超时',lambda:missing(0.3)))
            def invalid_selector():
                for value in (None,123,[],{'name':INPUT}):
                    reject(lambda v=value:win32.find_all(v,timeout=0),InvalidParamsError)
                return 'None、整数、列表、字典均被InvalidParamsError拒绝'
            results.append(helper.run_case('非法selector',invalid_selector))
            results.append(helper.run_case('Web Selector',lambda:reject(lambda:win32.find_all(Selector(name='web',framework='web',item_id=selectors[INPUT].id()),timeout=0),InvalidParamsError)))
            results.append(helper.run_case('非法session',lambda:reject(lambda:win32.find_all(INPUT,session=object(),timeout=0),InvalidParamsError)))
            def invalid_timeout():
                for value in (-2,'bad'):reject(lambda v=value:win32.find_all(INPUT,timeout=v),InvalidParamsError)
                return '非法超时被InvalidParamsError拒绝'
            results.append(helper.run_case('非法超时',invalid_timeout))
            def arguments():
                for call in (lambda:win32.find_all(),lambda:win32.find_all(INPUT,0),lambda:win32.find_all(INPUT,unknown=1)):
                    reject(call,TypeError)
                return '缺参、多余位置参数及未知关键字被TypeError拒绝'
            results.append(helper.run_case('调用参数边界',arguments))
            table_ready=helper.run_case('表格页与参照',prepare_table)
            results.append(table_ready)
            if table_ready.passed:
                results.append(helper.run_case('名称多项命中',lambda:multiple(False)))
                results.append(helper.run_case('Selector多项命中',lambda:multiple(True)))
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
            return '鼠标恢复、Package释放（如已取得）；靶场保持运行，保留最后测试页',[f'焦点: {focus_status}']
        results.append(helper.run_case('资源清理',cleanup))
        helper.render_results(results)
    passed=sum(r.passed for r in results)
    ok=passed==len(results)
    print(helper.colored('\n测试通过' if ok else '\n测试失败',helper.ANSI_GREEN if ok else helper.ANSI_RED))
    print(f"  生命周期: {'VERIFIED' if ok else 'READY_FOR_LIVE'}\n  结果: {passed}/{len(results)} 通过\n  总耗时: {(time.perf_counter()-started)*1000:.1f}ms\n  退出码: {0 if ok else 1}")
    return 0 if ok else 1


if __name__=='__main__':
    raise SystemExit(main(non_interactive=parse_run_options().non_interactive))
