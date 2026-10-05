"""Run one remaining Web API against existing live targets; no target page creation."""
from __future__ import annotations

import argparse
import concurrent.futures
import ctypes
from ctypes import wintypes
import inspect
import json
import math
from pathlib import Path
import shutil
import subprocess
import sys
import time
from urllib.request import urlopen
import uuid

ROOT = Path(r'D:\code\元素库\sdk测试')
PRODUCT = Path(r'D:\code\desktop')
LIBRARY = Path(r'D:\code\元素库\260902_web元素')
sys.dont_write_bytecode = True
sys.path.insert(0, str(PRODUCT / 'sdk' / 'src'))
sys.path.insert(0, str(ROOT / 'web'))
from uiautoma import web, open as open_package, ActionError, InvalidParamsError, HostUnavailableError
from uiautoma.web import WebElement, WebBrowser
from test_web_element_get_select_options import copy_library, disable_dynamic_ids, find_switch

BASE = 'https://baobaomi900901.github.io/xpath/#/'
TARGET_OVERRIDE = None
__test__ = False
FORM = 'iframe-shadow-form'
INPUT = 'web靶场_表单测试_原生_输入框'
ANT_INPUT = 'web靶场_表单测试_ant_输入框'
SINGLE = 'web靶场_表单测试_原生_select单选'
MULTI = 'web靶场_表单测试_原生_select多选_options_面板'
ANT_SINGLE = 'web靶场_表单测试_ant_select单选'
ANT_MULTI = 'web靶场_表单测试_ant_select多选'
RESET = 'web靶场_表单测试_原生_重置'
ROOT_JS = "document.querySelector('#iframe-shadow-form').contentDocument.querySelector('#form-shadow-host').shadowRoot"
SKIPS = {
    'web.remove_all_auto_handle_popup': 'keys-click-test 的 DOM 弹窗与关闭按钮已具备；尚未独立验收规则移除后弹窗保持打开的真实行为',
    'web.set_user_environment_fingerprint': '当前源码直接抛 UnsupportedActionError，未实现指纹浏览器环境',
    'browser.stop_load': '缺少加载持续不完成的现有靶场；完整加载页不能验证中止待处理导航',
    'browser.extract_table': '当前源码直接抛 UnsupportedActionError，未实现表格提取',
    'element.extract_table': '当前源码直接抛 UnsupportedActionError，未实现表格提取',
    'element.get_basetable_value': '当前源码直接抛 UnsupportedActionError，未实现基础表格提取',
}
IMPLEMENTED = ['element.name','element.get_selected_item','element.set_attribute','element.get_attribute',
    'element.get_all_attributes','element.get_bounding','element.get_anchor_position',
    'element.get_anchor_viewport_position','element.screenshot','element.is_checked','element.is_enabled',
    'element.is_displayed','element.execute_javascript','element.scroll_to','element.get_scroll',
    'element.drag_to','element.drag_to_by_cdp','element.upload','element.download','element.highlight',
    'browser.go_back','web.handle_upload_dialog','web.auto_handle_popup']
APIS = IMPLEMENTED + list(SKIPS)
CONTRACT_FILE = ROOT / 'web' / 'remaining_web_contracts_20261004.json'


def api_object(api):
    kind, name = api.split('.')
    cls = {'web': web, 'browser': WebBrowser, 'element': WebElement}[kind]
    value = getattr(cls, name)
    return value.fget if isinstance(value, property) else value


def freeze_contracts():
    out = {}
    commit = subprocess.check_output(['git','-C',str(PRODUCT),'rev-parse','HEAD'],text=True).strip()
    for api in APIS:
        obj = api_object(api)
        out[api] = {'signature':str(inspect.signature(obj)), 'docstring':inspect.getdoc(obj),
                    'source_file':str(Path(inspect.getsourcefile(obj)).relative_to(PRODUCT)),
                    'source_line':inspect.getsourcelines(obj)[1], 'source':inspect.getsource(obj)}
    CONTRACT_FILE.write_text(json.dumps({'product_worktree':str(PRODUCT),'product_commit':commit,'apis':out},
                                       ensure_ascii=False,indent=2)+'\n',encoding='utf-8')


class Skip(Exception):
    pass


class Context:
    def __init__(self, api, progress=False):
        self.api = api
        self.progress = progress
        self.rows = []
        self.page = self.package = self.reference = None
        self.previous_switch = None
        self.baseline = set()
        self.page_id = None
        self.tmp = ROOT / '.pytest_tmp' / 'web_remaining' / uuid.uuid4().hex
        self.dialogs_before = set()
        self.dialog_owner = None

    def case(self, case_id, expected, fn, known=False):
        start = time.perf_counter()
        try:
            actual = fn()
            status = 'KNOWN' if known else 'PASS'
        except Skip as exc:
            status, actual = 'KNOWN', {'skip':str(exc)}
        except Exception as exc:
            trace=getattr(exc,'trace_info','')
            actual = {'exception':type(exc).__name__, 'message':str(exc), 'trace':trace}
            if self.api == 'web.handle_upload_dialog':
                actual.update(getattr(exc, '_upload_test_details', {}))
                response = getattr(exc, 'response', None)
                if response is None:
                    response = getattr(getattr(exc, 'result', None), 'raw', None)
                for _ in range(8):
                    if not isinstance(response, dict): break
                    if response.get('missing_capabilities'):
                        actual['missing_capabilities'] = response['missing_capabilities']
                        actual['provider_reason'] = response.get('log_lines', [])
                    response = response.get('raw')
            if trace in {'uiautomation_provider_unavailable','browser_host_window_mismatch'}:
                status='KNOWN'
                actual['skip']='当前原生 Provider/浏览器窗口环境不可用，跳过此分支'
            else:status='FAIL'
        self.rows.append({'case_id':case_id,'status':status,'expected':expected,'actual':actual,
                          'elapsed_ms':round((time.perf_counter()-start)*1000,1)})
        return status

    def expect(self, condition, actual):
        if not condition:
            raise AssertionError(repr(actual))
        return actual

    def raises(self, exception, fn, message='', trace=''):
        try:
            fn()
        except exception as exc:
            return self.expect((not message or message in str(exc)) and
                (not trace or trace == getattr(exc,'trace_info','')),
                {'exception':type(exc).__name__,'message':str(exc),'trace':getattr(exc,'trace_info','')})
        raise AssertionError(f'Expected {exception.__name__}')

    def js(self, expression, argument=None, form=True):
        root = ROOT_JS if form else 'document'
        return self.page.execute_javascript('function (_element, args) { const root='+root+'; return ('+expression+'); }',argument)

    def el(self, name=INPUT):
        self.reference = self.page.find(name,timeout=4)
        return self.reference

    def css(self, selector):
        self.reference = self.page.find_by_css(selector,timeout=4)
        return self.reference

    def form_css(self, selector):
        ancestor=self.el()
        while ancestor is not None:
            try:
                target=ancestor.find_by_css(selector,timeout=0)
                self.reference=target
                return target
            except Exception as exc:
                if type(exc).__name__!='ElementNotFoundError':raise
            ancestor=ancestor.parent()
        raise Skip('当前 iframe/Shadow 上下文中缺少 '+selector)

    def node(self, id):
        return self.js("(()=>{const e=root.getElementById(args);return e?{id:e.id,tag:e.tagName,type:e.type,value:e.value,checked:e.checked,disabled:e.disabled,attrs:Object.fromEntries([...e.attributes].map(a=>[a.name,a.value])),display:getComputedStyle(e).display,visibility:getComputedStyle(e).visibility}:null})()",id)

    def wait(self, fn, predicate, timeout=3):
        deadline=time.monotonic()+timeout
        while True:
            value=fn()
            if predicate(value): return value
            if time.monotonic()>deadline: raise AssertionError(f'Timeout: {value!r}')
            time.sleep(.1)

    def setup(self):
        route = 'geometry-test' if self.api in {'element.scroll_to','element.get_scroll','element.drag_to','element.drag_to_by_cdp'} else FORM
        if self.api=='element.download': route='download-dialog-test'
        if self.api in {'element.upload','web.handle_upload_dialog'}: route='upload-dialog-test'
        self.baseline={p._page_ref['id'] for p in web.get_all(mode='chrome')}
        self.dialogs_before=set(native_windows('#32770'))
        copy_library(LIBRARY,self.tmp/'library')
        self.package=open_package(str(self.tmp/'library'),timeout=8,connect_timeout=8)
        self.target_url=TARGET_OVERRIDE or BASE+route
        self.page=web.create(self.target_url,mode='chrome',load_timeout=25,
                             silent_running=self.api not in {'element.drag_to','element.drag_to_by_cdp','web.handle_upload_dialog'})
        self.page_id=self.page._page_ref['id']
        if route==FORM:
            self.previous_switch=disable_dynamic_ids(self.page)
            e=self.el()
            self.expect(e.get_attribute('id')=='form-controls-native-text',{'id':e.get_attribute('id')})
        if route=='geometry-test' and self.api in {'element.scroll_to','element.get_scroll'}:
            self.js("(()=>{const tab=[...document.querySelectorAll('[role=tab]')].find(e=>e.textContent==='元素滚动测试'); if(!tab)return false; tab.click();return true})()",form=False)
            self.wait(lambda:self.js("!!document.getElementById('element-scroll-container')",form=False),bool)
        if self.api in {'element.upload','element.download','web.handle_upload_dialog'}:
            self.page.activate()
            ctypes.windll.user32.GetForegroundWindow.restype=wintypes.HWND
            self.dialog_owner=int(ctypes.windll.user32.GetForegroundWindow() or 0)
        return {'url':self.page.get_url(),'baseline_tabs':len(self.baseline),'library':str(LIBRARY),'temporary_library':str(self.tmp/'library')}

    def cleanup(self):
        errors=[]
        own_dialogs={hwnd for hwnd,info in native_windows('#32770').items()
                     if hwnd not in self.dialogs_before and info['owner']==self.dialog_owner}
        for hwnd in own_dialogs:
            ctypes.windll.user32.PostMessageW(wintypes.HWND(hwnd),0x10,0,0)
        if own_dialogs:time.sleep(.2)
        if self.page is not None:
            try:
                if self.previous_switch=='true': find_switch(self.page).click(simulative=False,delay_after=.1)
                self.page.close(ignore_beforeunload=True)
            except Exception as exc: errors.append(str(exc))
        if self.package is not None:
            try:self.package.close()
            except Exception as exc:errors.append(str(exc))
        if self.tmp.exists():
            resolved=self.tmp.resolve()
            if resolved.parent != (ROOT/'.pytest_tmp'/'web_remaining').resolve():
                errors.append('Unexpected cleanup path')
            else: shutil.rmtree(resolved)
        after={p._page_ref['id'] for p in web.get_all(mode='chrome')}
        dialogs={hwnd for hwnd,info in native_windows('#32770').items()
                 if hwnd not in self.dialogs_before and info['owner']==self.dialog_owner}
        return self.expect(not errors and self.page_id not in after and not self.tmp.exists() and not dialogs,
            {'errors':errors,'own_tab_closed':self.page_id not in after,'temporary_copy_removed':not self.tmp.exists(),
             'tab_count':f'{len(self.baseline)}->{len(after)}','external_added':list(after-self.baseline),
             'external_removed':list(self.baseline-after),'new_dialogs':list(dialogs)})


def native_windows(class_name):
    u=ctypes.windll.user32
    u.GetWindow.argtypes=[wintypes.HWND,wintypes.UINT]
    u.GetWindow.restype=wintypes.HWND
    found={}
    cb=ctypes.WINFUNCTYPE(wintypes.BOOL,wintypes.HWND,wintypes.LPARAM)
    def visit(hwnd,_):
        name=ctypes.create_unicode_buffer(256)
        u.GetClassNameW(hwnd,name,256)
        if name.value==class_name and u.IsWindowVisible(hwnd):
            r=wintypes.RECT();u.GetWindowRect(hwnd,ctypes.byref(r))
            found[int(hwnd)]={'x':r.left,'y':r.top,'width':r.right-r.left,'height':r.bottom-r.top,
                              'owner':int(u.GetWindow(hwnd,4) or 0)}
        return True
    u.EnumWindows(cb(visit),0)
    return found


def selected(c):
    def read(name,id,values):
        before=c.js("[...root.getElementById(args).options].map(e=>({text:e.text,value:e.value,selected:e.selected}))",id)
        actual=c.el(name).get_selected_item()
        after=c.js("[...root.getElementById(args).options].map(e=>({text:e.text,value:e.value,selected:e.selected}))",id)
        expected=[o['text'].replace('\xa0',' ') for o in before if o['selected']]
        return c.expect(actual==expected==values and before==after,{'result':actual,'dom':before,'unchanged':before==after})
    for name,id,values in [(SINGLE,'form-controls-native-city',['请选择城市']),(MULTI,'form-controls-native-cities',[])]:
        c.case('initial_'+id,'读取当前选中项目，DOM 前后不变',lambda n=name,i=id,v=values:read(n,i,v))
    c.el(SINGLE).select_by_index(2,delay_after=.2)
    c.case('single_changed','单选上海返回 [上海]',lambda:read(SINGLE,'form-controls-native-city',['上海']))
    c.el(MULTI).select_multiple_by_index([0,2],delay_after=.2)
    c.case('multi_changed','多选返回北京、广州，按 DOM 顺序',lambda:read(MULTI,'form-controls-native-cities',['北京','广州']))
    c.el(RESET).click(simulative=False,delay_after=.2)
    c.wait(lambda:c.js("root.getElementById('form-controls-native-city').value"),lambda x:x=='')
    c.case('reset','重置后多选返回空列表',lambda:read(MULTI,'form-controls-native-cities',[]))
    for name in [ANT_SINGLE,ANT_MULTI]:
        c.case('ant_'+name,'非 SELECT 抛 ActionError/element_options_not_readable',
            lambda n=name:c.raises(ActionError,lambda:c.el(n).get_selected_item(),trace='element_options_not_readable'),known=True)
    c.case('no_extra_parameter','多余位置参数抛 TypeError',lambda:c.raises(TypeError,lambda:c.el().get_selected_item(1)))


def attributes(c):
    api=c.api.split('.')[1]
    for name,id in [(INPUT,'form-controls-native-text'),(ANT_INPUT,'form-controls-ant-text')]:
        def read(n=name,i=id):
            e=c.el(n); before=c.node(i)
            if api=='get_attribute':
                actual={k:e.get_attribute(k) for k in ['id','type','placeholder','data-uiautoma-absent']}
                expected={k:before['attrs'].get(k) for k in actual}
            elif api=='get_all_attributes':
                actual=e.get_all_attributes();expected=before['attrs']
            else:
                original=before['attrs'].get('data-uiautoma-batch')
                try:
                    returned=e.set_attribute('data-uiautoma-batch','音乐 " <&>')
                    actual=c.node(i)['attrs'].get('data-uiautoma-batch')
                    return c.expect(returned is None and actual=='音乐 " <&>',{'return':returned,'dom_attribute':actual})
                finally:
                    c.js("(()=>{const e=root.getElementById(args.id);if(args.value===null)e.removeAttribute('data-uiautoma-batch');else e.setAttribute('data-uiautoma-batch',args.value);return e.getAttribute('data-uiautoma-batch')})()",{'id':i,'value':original})
            return c.expect(actual==expected and before==c.node(i),{'actual':actual,'independent_dom':expected})
        c.case('native' if name==INPUT else 'ant','真实元素属性与 DOM 对照，修改后恢复',read)
    if api in {'set_attribute','get_attribute'}:
        fn=lambda:c.el().set_attribute('', 'x') if api=='set_attribute' else c.el().get_attribute('')
        c.case('empty_name','空属性名抛 InvalidParamsError',lambda:c.raises(InvalidParamsError,fn))
    if api=='set_attribute':
        c.case('nonstring_value','非字符串属性值抛 InvalidParamsError',lambda:c.raises(InvalidParamsError,lambda:c.el().set_attribute('data-x',1)))
    else:
        c.case('extra_argument','多余位置参数抛 TypeError',lambda:c.raises(TypeError,lambda:getattr(c.el(),api)(1,2)))


def checked(c):
    for kind in ['原生','ant']:
        name=f'web靶场_表单测试_{kind}_checkbox_input_音乐'
        id='form-controls-'+('native' if kind=='原生' else 'ant')+'-hobbyMusic'
        for mode,expected in [('initial',False),('check',True),('uncheck',False)]:
            def run(n=name,i=id,m=mode,v=expected):
                e=c.el(n)
                if m!='initial':e.check(m,delay_after=.2)
                before=c.node(i)
                result=e.is_checked();after=c.node(i)
                return c.expect(result is v and result is before['checked'] and before==after,
                                {'result':result,'dom_checked':before['checked'],'checked_attribute':before['attrs'].get('checked')})
            c.case(kind+'_'+mode,'IDL checked 与读取值一致；调用不改 DOM',run)
    c.case('text_input','普通文本 input 的 IDL checked 为 False，API 同样返回 False',
           lambda:c.expect(c.el().is_checked() is c.node('form-controls-native-text')['checked'] is False,
                           {'dom':c.node('form-controls-native-text'),'result':c.el().is_checked()}))


def enabled(c):
    for id in ['form-controls-native-text','form-controls-native-disabled','form-controls-ant-disabled']:
        c.case(id,'真实启用/禁用状态与 DOM disabled 一致',
               lambda i=id:c.expect(c.form_css('#'+i).is_enabled() is (not c.node(i)['disabled']),c.node(i)))
    id='form-controls-native-text'
    def toggle():
        try:
            c.js("(root.getElementById(args).disabled=true)",id)
            e=c.form_css('#'+id); off=e.is_enabled()
            c.js("(root.getElementById(args).disabled=false)",id)
            on=e.is_enabled()
            return c.expect(off is False and on is True,{'disabled_result':off,'enabled_result':on})
        finally:c.js("(root.getElementById(args).disabled=false)",id)
    c.case('toggle_disabled','动态禁用 False，恢复 True',toggle)
    def boolean_attr():
        try:
            c.js("root.getElementById(args).setAttribute('disabled','false')",id)
            dom=c.node(id);actual=c.el().is_enabled()
            return c.expect(actual is (not dom['disabled']),{'actual':actual,'dom_disabled':dom['disabled'],'attribute':dom['attrs']['disabled']})
        finally:c.js("root.getElementById(args).removeAttribute('disabled')",id)
    c.case('boolean_disabled_attribute','HTML 布尔 disabled 属性存在时即禁用，包括值 false',boolean_attr)


def displayed(c):
    e=c.el(); id='form-controls-native-text'
    original=c.node(id)['attrs'].get('style')
    try:
        for key,value,expected in [('visible','','True'),('display_none','display:none','False'),('visibility_hidden','visibility:hidden','False')]:
            def run(v=value,w=expected):
                c.js("root.getElementById(args.id).setAttribute('style',args.style)",{'id':id,'style':v})
                actual=e.is_displayed()
                oracle=c.js("(()=>{const e=root.getElementById(args);const s=getComputedStyle(e);return !!e.getClientRects().length && s.display!=='none' && s.visibility!=='hidden'})()",id)
                return c.expect(actual is oracle and actual is (w=='True'),{'actual':actual,'dom_visible':oracle})
            c.case(key,'显示状态与 clientRects/computedStyle 对照',run)
    finally:
        c.js("(()=>{const e=root.getElementById(args.id);if(args.style===null)e.removeAttribute('style');else e.setAttribute('style',args.style)})()",{'id':id,'style':original})


def javascript(c):
    e=c.el(); payload={'音乐':['甲',1,True,None],'nested':{'x':2}}
    for world in ['ISOLATED','MAIN']:
        def run(w=world):
            actual=e.execute_javascript('function(element,args){return {id:element.id,tag:element.tagName,args:args};}',payload,w)
            expected={'id':'form-controls-native-text','tag':'INPUT','args':payload}
            return c.expect(actual==expected,{'actual':actual,'expected':expected})
        c.case('roundtrip_'+world,'跨 iframe/Shadow 绑定真实 element，JSON 参数和结果保真',run)
    c.case('null','JS null 返回 None',lambda:c.expect(e.execute_javascript('function(){return null;}') is None,'None'))
    c.case('undefined','JS undefined 返回 None',lambda:c.expect(e.execute_javascript('function(){}') is None,'None'))
    c.case('invalid_world','错误执行环境抛 InvalidParamsError',lambda:c.raises(InvalidParamsError,lambda:e.execute_javascript('function(){}',execution_world='bad')))
    c.case('script_error','脚本异常抛 ActionError',lambda:c.raises(ActionError,lambda:e.execute_javascript('function(){throw new Error("uiautoma-probe");}')))


def scroll(c):
    def dom():return c.js("(()=>{const e=document.getElementById('element-scroll-container');return {top:e.scrollTop,left:e.scrollLeft,height:e.scrollHeight,width:e.scrollWidth,client:e.clientHeight}})()",form=False)
    before=dom()
    if before['height']<=before['client']:raise Skip('现有元素没有垂直滚动范围')
    e=c.css('#element-scroll-container')
    if c.api.endswith('.get_scroll'):
        for offset in [0,137,400]:
            def read(v=offset):
                c.js("(document.getElementById('element-scroll-container').scrollTop=args)",v,form=False)
                oracle=dom(); actual=e.get_scroll()
                return c.expect(actual==oracle['top'],{'result':actual,'dom':oracle})
            c.case('current_'+str(offset),'读取实际 scrollTop',read)
        for direction,key in [('vertical','height'),('horizontal','width')]:
            c.case('bottom_'+direction,'bottom 返回内容总高度/宽度',lambda d=direction,k=key:c.expect(e.get_scroll(direction=d,location='bottom')==dom()[k],dom()))
        c.case('invalid_direction','错误方向抛 InvalidParamsError',lambda:c.raises(InvalidParamsError,lambda:e.get_scroll(direction='bad')))
    else:
        for loc,offset in [('point',137),('top',0),('one_screen',before['client']),('bottom',before['height']-before['client'])]:
            def move(l=loc,v=offset):
                if l=='one_screen':c.js("(document.getElementById('element-scroll-container').scrollTop=0)",form=False)
                returned=e.scroll_to(location=l,top=v)
                after=c.wait(dom,lambda x:abs(x['top']-v)<=1)
                return c.expect(returned is None,{'return':returned,'dom':after,'expected_top':v})
            c.case(loc,'滚动后 DOM scrollTop 到达目标',move)
        c.case('invalid_location','错误位置抛 InvalidParamsError',lambda:c.raises(InvalidParamsError,lambda:e.scroll_to(location='bad')))
        c.case('invalid_behavior','错误滚动效果抛 InvalidParamsError',lambda:c.raises(InvalidParamsError,lambda:e.scroll_to(behavior='bad')))
    c.js("(document.getElementById('element-scroll-container').scrollTop=0)",form=False)


def form_rect(c):
    return c.js("(()=>{const f=document.querySelector('#iframe-shadow-form'),e=root.getElementById('form-controls-native-text');const r=e.getBoundingClientRect(),q=f.getBoundingClientRect();return {x:r.x+q.x+f.clientLeft,y:r.y+q.y+f.clientTop,width:r.width,height:r.height,dpr:window.devicePixelRatio}})()")


def geometry(c):
    e=c.el();e.scroll_to(location='top',search_up=True)
    c.page.activate()
    if c.api.endswith('get_bounding'):
        def read(relative,normalize):
            dom=form_rect(c);actual=e.get_bounding(to96dpi=normalize,relative_to=relative)
            physical=e.get_bounding(to96dpi=False,relative_to=relative)
            return c.expect(set(actual)=={'x','y','width','height'} and all(type(x)==int for x in actual.values())
                and abs(physical['width']-dom['width']*dom['dpr'])<=2 and abs(physical['height']-dom['height']*dom['dpr'])<=2,
                {'result':actual,'physical':physical,'independent_dom':dom})
        for relative in ['screen','window']:
            for normalized in [False,True]:c.case(relative+str(normalized),'尺寸与 DOM × devicePixelRatio 一致，返回整数矩形',lambda r=relative,n=normalized:read(r,n))
        c.case('invalid_reference','非法坐标参照抛 InvalidParamsError',lambda:c.raises(InvalidParamsError,lambda:e.get_bounding(relative_to='bad')))
    else:
        viewport=c.api.endswith('get_anchor_viewport_position')
        specs=[(None,.5,.5),('top_left',0,0),('bottom_right',1,1),('top_center',.5,0),
               (('middle_right',3,-2),1,.5),({'anchor':'bottom_left','offset_x':2,'offset_y':-3},0,1)]
        for i,(anchor,fx,fy) in enumerate(specs):
            def read(a=anchor,x=fx,y=fy):
                if viewport:
                    dom=form_rect(c);box={'x':round(dom['x']),'y':round(dom['y']),'width':round(dom['width']),'height':round(dom['height'])}
                    actual=e.get_anchor_viewport_position(anchor=a)
                else:
                    dom=form_rect(c);box=e.get_bounding(to96dpi=False)
                    c.expect(abs(box['width']-dom['width']*dom['dpr'])<=2,{'bounding':box,'dom':dom})
                    actual=e.get_anchor_position(anchor=a,to96dpi=False)
                ox,oy=(a[1],a[2]) if isinstance(a,tuple) else ((a.get('offset_x',0),a.get('offset_y',0)) if isinstance(a,dict) else (0,0))
                expected=(math.floor(box['x']+box['width']*x+ox+.5),math.floor(box['y']+box['height']*y+oy+.5))
                return c.expect(isinstance(actual,tuple) and len(actual)==2 and all(type(v)==int for v in actual)
                    and all(abs(u-v)<=1 for u,v in zip(actual,expected)),{'actual':actual,'expected':expected,'dom':dom,'reference_rect':box})
            c.case('anchor_'+str(i),'锚点和偏移与真实矩形计算一致',read)
        c.case('invalid_anchor','无效锚点抛 InvalidParamsError',lambda:c.raises(InvalidParamsError,lambda:getattr(e,c.api.split('.')[1])(anchor='bad')))


def screenshot(c):
    from test_web_element_screenshot_to_clipboard import png_rows,crop,byte_diff
    e=c.el(); c.page.activate()
    def capture():
        returned=e.screenshot(str(c.tmp),file_name='element.png')
        dom=form_rect(c)
        c.page.screenshot(str(c.tmp),file_name='viewport.png',full_size=False)
        image=png_rows(Path(returned)); page=png_rows(c.tmp/'viewport.png')
        dpr=dom['dpr'];x=math.floor(dom['x']*dpr);y=math.floor(dom['y']*dpr)
        candidates=[]
        for dx in [-1,0,1]:
            for dy in [-1,0,1]:
                ref=crop(page,x+dx,y+dy,image[0],image[1])
                diff,total,note=byte_diff(image,ref)
                if total:candidates.append((diff,total,dx,dy))
        best=min(candidates) if candidates else None
        expected=(round(dom['width']*dpr),round(dom['height']*dpr))
        return c.expect(Path(returned).exists() and abs(image[0]-expected[0])<=2 and abs(image[1]-expected[1])<=2
            and best is not None and best[0]/best[1]<.025,
            {'saved_path':returned,'png_size':image[:2],'dom_size':expected,'best_pixel_compare':best})
    c.case('file_and_framing','PNG 尺寸与 DOM 一致，取景与页面 PNG 对照（±1px 扫描、差异<2.5%）',capture)
    c.case('invalid_filename','非法文件名抛 InvalidParamsError',lambda:c.raises(InvalidParamsError,lambda:e.screenshot(str(c.tmp),file_name='../escape.png')))


def drag(c):
    id='coordinate-drag-target'
    def rect():return c.js("(()=>{const e=document.getElementById('coordinate-drag-target');if(!e)return null;const r=e.getBoundingClientRect();return {x:r.x,y:r.y,width:r.width,height:r.height,logs:document.querySelectorAll('#coordinate-drag-log tbody tr:not(.ant-table-placeholder)').length}})()",form=False)
    if rect() is None:raise Skip('已部署 geometry-test 页面缺少 coordinate-drag-target')
    modes=[False,True] if c.api.endswith('.drag_to') else ['cdp']
    for mode in modes:
        def move(m=mode):
            c.css('#coordinate-drag-reset').click(simulative=False,delay_after=.1)
            e=c.css('#'+id); e.execute_javascript('function(e){e.scrollIntoView({block:"center"});}')
            time.sleep(.1);before=rect()
            if m=='cdp': returned=e.drag_to_by_cdp(target_x=round(before['x']+before['width']/2+40),target_y=round(before['y']+before['height']/2+25),delay_after=.2,move_speed='fast')
            else:returned=e.drag_to(simulative=m,left=40,top=25,behavior='smooth',delay_after=.2,move_speed='fast')
            time.sleep(.2);after=rect();delta=(after['x']-before['x'],after['y']-before['y'])
            return c.expect(returned is None and abs(delta[0]-40)<=2 and abs(delta[1]-25)<=2 and after['logs']>=1,
                {'return':returned,'mode':m,'delta':delta,'before':before,'after':after})
        c.case('move_'+str(mode),'拖动位移 (+40,+25)，DOM 和页面停止日志同时确证',move)
    e=c.css('#'+id)
    if c.api.endswith('.drag_to'):
        c.case('invalid_behavior','错误行为抛 InvalidParamsError',lambda:c.raises(InvalidParamsError,lambda:e.drag_to(behavior='bad')))
        c.case('invalid_mode','非 bool simulative 抛 InvalidParamsError',lambda:c.raises(InvalidParamsError,lambda:e.drag_to(simulative=1)))
    else:c.case('invalid_target_type','错误目标参照抛 InvalidParamsError',lambda:c.raises(InvalidParamsError,lambda:e.drag_to_by_cdp(target_type='bad')))
    c.css('#coordinate-drag-reset').click(simulative=False,delay_after=.1)


def upload(c):
    path=c.tmp/'upload.txt';path.write_text('uiautoma real upload\n音乐',encoding='utf-8')
    e=c.el('web靶场_上传对话框测试 _原生_上传组件')
    def selected_files():return c.js("[...document.getElementById('input-upload-single').files].map(f=>({name:f.name,size:f.size}))",form=False)
    def run():
        returned=e.upload(str(path),simulative=False,clipboard_input=False,dialog_timeout=8)
        actual=selected_files()
        return c.expect(returned is None and actual==[{'name':path.name,'size':path.stat().st_size}],actual)
    c.case('real_file','上传返回 None，DOM FileList 文件名与大小一致',run)
    c.case('missing_file','不存在文件抛 InvalidParamsError',lambda:c.raises(InvalidParamsError,lambda:e.upload(str(c.tmp/'missing.txt'))))
    c.case('invalid_timeout','非法超时抛 InvalidParamsError',lambda:c.raises(InvalidParamsError,lambda:e.upload(str(path),dialog_timeout=-2)))


def upload_dialog(c):
    paths = [c.tmp/'upload_甲.txt', c.tmp/'upload_乙.txt']
    for i, path in enumerate(paths):
        path.write_text('uiautoma upload test '+str(i)+'\n音乐', encoding='utf-8')
    targets = [
        ('single_element','web靶场_单文件上传测试_按钮','input-upload-single',False,'choose_file','cancel'),
        ('multiple_element','web靶场_多文件上传测试_按钮','input-upload-multiple',True,'choose_multiple_files','cancel_multiple'),
    ]

    def selected_files(node_id):
        return c.js('[...document.getElementById(args).files].map(f=>({name:f.name,size:f.size}))',node_id,form=False)

    def handle(element,name,file_names,result):
        stage, api_called, observed = 'activate_page', False, {}
        try:
            c.page.activate()
            before_dialogs = set(native_windows('#32770'))
            stage = 'click_upload_input'
            if c.progress:
                print(f'[{result}] 点击 {name}，唤起文件选择窗口…',flush=True)
            element.click(simulative=True,delay_after=.1)
            stage = 'observe_upload_dialog'
            observed = c.wait(lambda:{hwnd:info for hwnd,info in native_windows('#32770').items()
                if hwnd not in before_dialogs and info['owner']==c.dialog_owner},bool,timeout=3)
            c.expect(len(observed)==1,{'dialogs':observed})
            if c.progress:
                print(f'[{result}] 已观察到文件选择窗口 {list(observed)}，停留 1 秒…',flush=True)
            time.sleep(1)
            stage, api_called = 'handle_upload_dialog', True
            returned = web.handle_upload_dialog(file_names,result,'chrome',clipboard_input=False,wait_appear_timeout=8)
            stage = 'observe_dialog_closed'
            c.wait(lambda:not(set(observed)&set(native_windows('#32770'))),bool,timeout=3)
            return {'return':returned,'element_name':name,'dialog_hwnds':list(observed),
                    'dialog_observed':True,'dialog_closed':True}
        except Exception as exc:
            exc._upload_test_details = {'stage':stage,'api_called':api_called,
                                       'element_name':name,'dialog_observed':bool(observed)}
            raise

    for prepare_id,name,node_id,multiple,choose_id,cancel_id in targets:
        element = None
        def prepare():
            nonlocal element
            element = c.el(name)
            actual = c.js('(()=>{const e=document.getElementById(args);return e?{id:e.id,tag:e.tagName,type:e.type,multiple:e.multiple}:null})()',node_id,form=False)
            actual_id = element.get_attribute('id')
            return c.expect(actual_id==node_id and actual=={'id':node_id,'tag':'INPUT','type':'file','multiple':multiple},
                {'element_name':name,'element_id':actual_id,'dom':actual})
        prepared = c.case(prepare_id,'用户指定库元素映射到对应 file input，multiple 属性正确',prepare)=='PASS'
        chosen = paths if multiple else paths[:1]
        expected = [{'name':p.name,'size':p.stat().st_size} for p in chosen]
        def choose():
            if not prepared: raise Skip('指定上传元素的准备检查未通过')
            file_names = [str(p) for p in chosen] if multiple else str(chosen[0])
            detail = handle(element,name,file_names,'ok')
            actual = selected_files(node_id)
            detail.update({'files':actual,'expected_files':expected})
            return c.expect(detail['return'] is None and sorted(actual,key=lambda f:f['name'])==sorted(expected,key=lambda f:f['name']),detail)
        accepted = c.case(choose_id,'真实窗口确认返回 None，DOM FileList 文件名和大小与磁盘一致',choose)=='PASS'
        def cancel():
            if not accepted: raise Skip('确认文件未通过，无法验证取消保留原文件')
            before = selected_files(node_id)
            detail = handle(element,name,[],'cancel')
            after = selected_files(node_id)
            detail.update({'before_files':before,'after_files':after})
            return c.expect(detail['return'] is None and before==after,detail)
        c.case(cancel_id,'真实窗口取消返回 None，DOM FileList 保留原文件',cancel)
    c.case('invalid_result','非法 dialog_result 抛 InvalidParamsError',lambda:c.raises(InvalidParamsError,lambda:web.handle_upload_dialog([],'bad','chrome')))


def download(c):
    e=c.el('web靶场_下载对话框测试 _下载txt')
    oracle=urlopen('https://baobaomi900901.github.io/xpath/samples/demo.txt',timeout=12).read()
    def run():
        path=e.download(str(c.tmp),file_name='received.txt',clipboard_input=False,dialog_timeout=8,wait_complete_timeout=12)
        actual=Path(path).read_bytes()
        return c.expect(Path(path).resolve()==(c.tmp/'received.txt').resolve() and actual==oracle,
            {'path':path,'bytes':len(actual),'matches_independent_http':actual==oracle})
    c.case('real_download','返回文件路径，字节与独立 HTTP 读取的 demo.txt 相同',run)
    c.case('invalid_timeout','非法等待时间抛 InvalidParamsError',lambda:c.raises(InvalidParamsError,lambda:e.download(str(c.tmp),dialog_timeout=-2)))


def highlight(c):
    e=c.el()
    before=native_windows('UIAutoma_HighlightWin32')
    def run():
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            start=time.perf_counter();future=pool.submit(e.highlight,.5,.15)
            observed={}
            while not future.done():
                observed.update(native_windows('UIAutoma_HighlightWin32'))
                time.sleep(.025)
            returned=future.result();elapsed=time.perf_counter()-start
        after=native_windows('UIAutoma_HighlightWin32')
        return c.expect(returned is None and bool(set(observed)-set(before)) and not(set(after)-set(before)) and elapsed>=.6,
            {'return':returned,'overlay_windows':observed,'overlays_remaining':after,'elapsed_s':elapsed})
    c.case('visible_overlay','独立 Win32 观察高亮窗出现并移除，持续时间与后置等待生效',run)
    c.case('zero','duration=0 返回 None',lambda:c.expect(e.highlight(0) is None,'None'))
    for v in [-1,True,float('nan')]:c.case('invalid_'+repr(v),'非法 duration 抛 InvalidParamsError',lambda x=v:c.raises(InvalidParamsError,lambda:e.highlight(x)))


def back(c):
    original=c.page.get_url()
    c.page.navigate(BASE+'element-html-test',load_timeout=15)
    def run():
        returned=c.page.go_back(load_timeout=15)
        url=c.wait(c.page.get_url,lambda u:u==original)
        return c.expect(returned is None,{'return':returned,'url':url})
    c.case('first_back','首次后退回到原 URL，页面实际地址确证',run)
    c.case('extra_positional','仅关键字 load_timeout 不接受位置值',lambda:c.raises(TypeError,lambda:c.page.go_back(1)))


def name(c):
    for n,id in [(INPUT,'form-controls-native-text'),(ANT_INPUT,'form-controls-ant-text'),(SINGLE,'form-controls-native-city')]:
        def read(value=n,i=id):
            e=c.el(value)
            dom=c.js("(()=>{const e=root.getElementById(args);return String(e.innerText||e.value||e.tagName||'')})()",i)
            return c.expect(e.name==dom,{'library_name':value,'runtime_name':e.name,'independent_dom_name':dom})
        c.case(n,'对象 name 为获取时的 DOM 文本/值/标签名，与现场 DOM 对照',read)


CASES={'name':name,'get_selected_item':selected,'set_attribute':attributes,'get_attribute':attributes,
       'get_all_attributes':attributes,'is_checked':checked,'is_enabled':enabled,'is_displayed':displayed,
       'execute_javascript':javascript,'scroll_to':scroll,'get_scroll':scroll,'get_bounding':geometry,
       'get_anchor_position':geometry,'get_anchor_viewport_position':geometry,'screenshot':screenshot,
       'drag_to':drag,'drag_to_by_cdp':drag,'upload':upload,'download':download,'highlight':highlight,
    'go_back':back,'handle_upload_dialog':upload_dialog}


def run_api(api,contract_only=False,progress=False):
    if api == 'web.auto_handle_popup':
        from test_web_auto_handle_popup import run, URL, OPEN_BUTTON, CLOSE_BUTTON, MODAL
        return run(argparse.Namespace(contract_only=contract_only, json=not progress,
            element_library=LIBRARY, target_url=TARGET_OVERRIDE or URL,
            open_button=OPEN_BUTTON, close_button=CLOSE_BUTTON, modal=MODAL,
            control_observe_seconds=3, wait_timeout=8))
    c=Context(api,progress=progress)
    contracts=json.loads(CONTRACT_FILE.read_text(encoding='utf-8'))
    contract=contracts['apis'][api]
    c.case('api_contract','公开签名与只读源码快照一致',lambda:c.expect(str(inspect.signature(api_object(api)))==contract['signature'],str(inspect.signature(api_object(api)))))
    if api in SKIPS:
        c.rows.append({'case_id':'skip','status':'KNOWN','expected':'需要真实正向场景','actual':{'skip':SKIPS[api]},'elapsed_ms':0})
        lifecycle='SKIPPED'
    elif contract_only:lifecycle='READY_FOR_LIVE'
    else:
        try:
            if c.case('environment','Runtime/Chrome/现有靶场与临时库可用',c.setup)=='PASS':
                try:CASES[api.split('.')[1]](c)
                except Skip as exc:c.rows.append({'case_id':'skip','status':'KNOWN','expected':'需要真实场景','actual':{'skip':str(exc)},'elapsed_ms':0})
                except Exception as exc:c.rows.append({'case_id':'scenario_error','status':'FAIL','expected':'场景可运行','actual':{'exception':type(exc).__name__,'message':str(exc)},'elapsed_ms':0})
        finally:
            reference=c.reference
            c.case('cleanup','关闭本次页面和库、删除临时目录、复核标签和文件弹窗',c.cleanup)
            if reference is not None and api.startswith('element.') and api!='element.name':
                method=getattr(reference,api.split('.')[1])
                if api.split('.')[1] in {'get_selected_item','get_attribute','get_all_attributes','get_bounding','get_anchor_position','get_anchor_viewport_position','is_checked','is_enabled','is_displayed','get_scroll','execute_javascript'}:
                    args=('id',) if api.endswith('.get_attribute') else ('function(){return 1;}',) if api.endswith('.execute_javascript') else ()
                    c.case('closed_package','关闭连接后抛当前版本的 HostUnavailableError',lambda:c.raises(HostUnavailableError,lambda:method(*args),message='连接已关闭'))
        canonical={
            'element.get_bounding':['screenFalse','windowFalse'],
            'element.get_anchor_position':['anchor_0'],
            'element.highlight':['visible_overlay'],
            'web.handle_upload_dialog':['choose_file','cancel','choose_multiple_files','cancel_multiple'],
            'element.drag_to':['move_False'],
        }.get(api,[])
        required_skipped=bool(canonical) and not any(r['case_id'] in canonical and r['status']=='PASS' for r in c.rows)
        if api=='web.handle_upload_dialog':
            required_skipped=not set(canonical).issubset({r['case_id'] for r in c.rows if r['status']=='PASS'})
        lifecycle='READY_FOR_LIVE' if any(r['status']=='FAIL' for r in c.rows) else 'SKIPPED' if required_skipped or any(r['case_id']=='skip' for r in c.rows) else 'VERIFIED'
    code=1 if any(r['status']=='FAIL' for r in c.rows) else 0
    commit=subprocess.check_output(['git','-C',str(PRODUCT),'rev-parse','HEAD'],text=True).strip()
    return {'api':api,'lifecycle':lifecycle,'url':getattr(c,'target_url',None),'element_library':str(LIBRARY),
            'product_worktree':str(PRODUCT),'product_commit':commit,
            'contract':contract,'results':c.rows,'exit_code':code},code


def main(default_api=None):
    global LIBRARY, TARGET_OVERRIDE
    p=argparse.ArgumentParser()
    p.add_argument('--api',choices=APIS,default=default_api)
    p.add_argument('--contract-only',action='store_true')
    p.add_argument('--json',action='store_true')
    p.add_argument('--report-file',type=Path)
    p.add_argument('--freeze-contracts',action='store_true')
    p.add_argument('--element-library',type=Path,default=LIBRARY)
    p.add_argument('--target-url',default=None)
    a=p.parse_args()
    LIBRARY=a.element_library
    TARGET_OVERRIDE=a.target_url
    if a.freeze_contracts:freeze_contracts();return 0
    if not a.api:p.error('--api is required')
    report,code=run_api(a.api,a.contract_only,progress=not a.json)
    if a.report_file:
        a.report_file.parent.mkdir(parents=True,exist_ok=True)
        a.report_file.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    if a.json:print(json.dumps(report,ensure_ascii=True,indent=2))
    else:
        owner={'element':'uiautoma.web.WebElement','browser':'uiautoma.web.WebBrowser','web':'uiautoma.web'}
        kind,method=a.api.split('.')
        print('UIAutoma Web API 测试\nAPI     : '+owner[kind]+'.'+method+'\n页面    : '+str(report['url'] or '场景条件不满足，已跳过'))
        for i,r in enumerate(report['results'],1):
            color='\x1b[92m' if r['status']=='PASS' else '\x1b[91m' if r['status']=='FAIL' else '\x1b[93m'
            label={'PASS':'通过','FAIL':'失败','KNOWN':'已知/跳过'}[r['status']]
            print(f"{i:02}/{len(report['results']):02} {color}[{label}]\x1b[0m {r['case_id']} 期望 {r['expected']}；实测 {r['actual']}；{r['elapsed_ms']}ms")
        passed=sum(r['status']=='PASS' for r in report['results']);known=sum(r['status']=='KNOWN' for r in report['results'])
        print(f"{report['lifecycle']} · {passed}/{len(report['results'])} 通过 · {known} 已知/跳过 · 退出码 {code}")
    return code


if __name__=='__main__':raise SystemExit(main())
