"""WebElement.input 双输入框验收；默认后台，--foreground 才使用系统键盘。"""
from __future__ import annotations
import argparse
import hashlib
import inspect
import json
import shutil
import subprocess
import sys
import time
import uuid
from pathlib import Path

__test__ = False
sys.dont_write_bytecode = True
ROOT = Path(r'D:\code\元素库\sdk测试')
PRODUCT = Path(r'D:\code\desktop')
sys.path.insert(0, str(PRODUCT/'sdk/src'))
sys.path.insert(0, str(ROOT/'web'))
from uiautoma import web, open as open_package, ping, ActionError, InvalidParamsError, UnsupportedActionError
from uiautoma.web import WebElement
from test_web_element_get_select_options import copy_library, disable_dynamic_ids, find_switch

URL = 'https://baobaomi900901.github.io/xpath/#/iframe-shadow-form'
LIBRARY = Path(r'D:\code\元素库\260902_web元素')
NAMES = {'ant':'web靶场_表单测试_ant_输入框','native':'web靶场_表单测试_原生_输入框'}
ROOT_JS = "document.querySelector('#iframe-shadow-form').contentDocument.querySelector('#form-shadow-host').shadowRoot"
CONTRACT = ROOT/'web/element_input_contract_20261008.json'
TEXT = 'SDK 输入 中文 123 😀✓'
SPECIAL = '!@#$%^&*()_+-=[]{};:\'",.?/\\|~'

class Blocked(Exception): pass

def require(ok, detail):
    if not ok: raise AssertionError(json.dumps(detail, ensure_ascii=False, default=str))
    return detail

def error(exc):
    return {'exception':type(exc).__name__,'message':str(exc),'trace':getattr(exc,'trace_info','')}

def raises(kind, fn, message='', trace=''):
    try: fn()
    except kind as exc:
        d=error(exc)
        require((not message or message in d['message']) and (not trace or trace==d['trace']),d)
        return d
    raise AssertionError('Expected '+kind.__name__)

def contract():
    frozen=json.loads(CONTRACT.read_text(encoding='utf-8'))
    require(str(inspect.signature(WebElement.input))==frozen['signature'],str(inspect.signature(WebElement.input)))
    require(inspect.getsource(WebElement.input)==frozen['source'],'SDK input source changed; review new contract')
    actual=subprocess.check_output(['git','-C',str(PRODUCT),'rev-parse','HEAD'],text=True).strip()
    require(actual==frozen['product_commit'],{'expected':frozen['product_commit'],'actual':actual})
    return {'signature':frozen['signature'],'product_commit':actual,'source':str(Path(inspect.getfile(WebElement.input)))}

class Run:
    def __init__(self, args):
        self.args=args; self.rows=[]; self.page=None; self.package=None; self.baseline=None
        self.previous=None; self.library_hash=None
        self.tmp=ROOT/'.pytest_tmp/input_live'/uuid.uuid4().hex
        self.id=None
    def case(self, name, expected, fn):
        start=time.perf_counter()
        try: actual=fn(); status='PASS'
        except Exception as exc:
            actual=error(exc)
            status='BLOCKED' if isinstance(exc,Blocked) or type(exc).__name__ in {'HostUnavailableError','ConnectionError'} else 'FAIL'
        row={'case_id':name,'status':status,'expected':expected,'actual':actual,'elapsed_ms':round((time.perf_counter()-start)*1000,1)}
        self.rows.append(row)
        label={'PASS':'通过','FAIL':'失败','BLOCKED':'阻塞'}[status]
        color={'PASS':'\x1b[32m','FAIL':'\x1b[31m','BLOCKED':'\x1b[33m'}[status]
        print(f"{len(self.rows):02d} [{color}{label}\x1b[0m] {name}: 期望 {expected}；实测 {json.dumps(actual,ensure_ascii=False,default=str)}；{row['elapsed_ms']}ms",flush=True)
        return status
    def js(self, body, arg=None, main=False):
        return self.page.execute_javascript('function(_e,a){const root='+ROOT_JS+';'+body+'}',arg,execution_world='MAIN' if main else 'ISOLATED')
    def wait(self, fn, predicate, timeout=5):
        end=time.monotonic()+timeout
        while True:
            value=fn()
            if predicate(value): return value
            if time.monotonic()>end: raise AssertionError('Timed out: '+repr(value))
            time.sleep(.05)
    def setup(self):
        ping(timeout=5)
        if not self.args.library.is_dir(): raise Blocked('元素库目录不存在')
        self.library_hash=hashlib.sha256((self.args.library/'elements.json').read_bytes()).hexdigest()
        self.baseline={p._page_ref['id'] for p in web.get_all(mode='chrome')}
        copy_library(self.args.library,self.tmp/'library')
        self.package=open_package(str(self.tmp/'library'),timeout=8,connect_timeout=8)
        self.page=web.create(URL,mode='chrome',silent_running=not self.args.foreground,load_timeout=25)
        self.id=self.page._page_ref['id']
        self.previous=disable_dynamic_ids(self.page)
        observer=self.js('''
          window.__uiaInput={events:[],copies:[],mutate:0};
          for(const n of [navigator,document.querySelector('#iframe-shadow-form').contentWindow.navigator]){
            Object.defineProperty(n.clipboard,'writeText',{configurable:true,value:async text=>{window.__uiaInput.copies.push(String(text));}});
          }
          for(const type of ['beforeinput','input','change']) root.addEventListener(type,e=>{
            if(!/^form-controls-(ant|native)-text$/.test(e.target.id))return;
            window.__uiaInput.events.push({type,id:e.target.id,value:e.target.value});
            if(type==='input' && window.__uiaInput.mutate>0){window.__uiaInput.mutate--;e.target.value='first-attempt-mismatch';}
          },true);
          return {clipboard_observer:true,root_is_shadow:root instanceof document.querySelector('#iframe-shadow-form').contentWindow.ShadowRoot};
        ''',main=True)
        if self.args.foreground: self.page.activate()
        return {'url':self.page.get_url(),'silent_running':not self.args.foreground,'baseline_tabs':len(self.baseline),'temporary_library':str(self.tmp/'library'),'observer':observer}
    def mapping(self, side):
        all_matches=self.page.find_all(NAMES[side],timeout=4)
        require(len(all_matches)==1,{'name':NAMES[side],'matches':len(all_matches)})
        el=all_matches[0]; expected='form-controls-'+side+'-text'
        require(el.get_attribute('id')==expected,{'id':el.get_attribute('id'),'expected':expected})
        return {'name':NAMES[side],'matches':1,'id':expected}
    def reset(self, side):
        self.js("root.getElementById('form-controls-'+a+'-reset').click();return true;",side)
        self.wait(lambda:self.js("return {value:root.getElementById('form-controls-'+a+'-text').value,result:root.getElementById(a+'-result').textContent};",side),lambda s:s['value']=='' and not s['result'].lstrip().startswith('{'))
        self.js('window.__uiaInput.events=[];window.__uiaInput.copies=[];window.__uiaInput.mutate=0;return true;',main=True)
    def observe(self, side):
        return self.js("const e=root.getElementById('form-controls-'+a+'-text');return {value:e.value,focused:root.activeElement===e};",side)
    def submit(self, side):
        self.js("root.getElementById('form-controls-'+a+'-submit').click();return true;",side)
        def read():
            raw=self.js("return root.getElementById(a+'-result').textContent;",side)
            try: return json.loads(raw)
            except ValueError: return None
        payload=self.wait(read,lambda x:isinstance(x,dict) and 'text' in x)
        copied=self.js('return window.__uiaInput.copies;',main=True)
        require(len(copied)==1 and json.loads(copied[0])==payload,{'copy_count':len(copied),'payload':payload})
        return payload['text']
    def scenario(self, side, spec):
        self.reset(side)
        el=self.page.find(NAMES[side],timeout=4)
        if spec.get('focus'): self.js("root.getElementById('form-controls-'+a+'-text').focus();return true;",side)
        if spec.get('blur'): self.js("root.getElementById('form-controls-'+a+'-text').blur();return true;",side)
        calls=[]
        for index,(text,params) in enumerate(spec['steps']):
            options={'delay_after':0,**params}
            if spec.get('mutate') and index==len(spec['steps'])-1: self.js('window.__uiaInput.mutate=1;return true;',main=True)
            before=self.observe(side)
            events_before=self.js('return window.__uiaInput.events.length;',main=True)
            start=time.perf_counter(); caught=None; returned=None
            try: returned=el.input(text,**options)
            except Exception as exc: caught=exc
            elapsed=time.perf_counter()-start
            after=self.observe(side)
            events=self.js('return window.__uiaInput.events.slice(a);',events_before,main=True)
            detail={'text':text,'options':options,'return':returned,'error':error(caught) if caught else None,'native':after,'elapsed_ms':round(elapsed*1000,1),'input_events':sum(e['type']=='input' for e in events)}
            calls.append(detail)
            if index==len(spec['steps'])-1 and spec.get('error'):
                require(isinstance(caught,ActionError) and getattr(caught,'trace_info','')==spec['error'],detail)
            elif caught: raise caught
            else: require(returned is None,detail)
            if spec.get('no_focus'): require(after['focused']==before['focused']==False,detail)
            if index==len(spec['steps'])-1:
                if 'min_seconds' in spec: require(elapsed>=spec['min_seconds'],detail)
                if 'input_events' in spec: require(detail['input_events']==spec['input_events'],detail)
        actual=self.observe(side)
        submitted=self.submit(side)
        require(actual['value']==submitted==spec['expected'],{'expected':spec['expected'],'native':actual,'submitted':submitted,'calls':calls})
        return {'native_value':actual['value'],'submitted_text':submitted,'calls':calls}
    def cleanup(self):
        errors=[]
        if self.page:
            try:
                if self.previous=='true': find_switch(self.page).click(simulative=False,delay_after=0)
                self.page.close(ignore_beforeunload=True)
            except Exception as exc: errors.append(error(exc))
        if self.package:
            try: self.package.close()
            except Exception as exc: errors.append(error(exc))
        if self.tmp.exists():
            require(self.tmp.resolve().parent==(ROOT/'.pytest_tmp/input_live').resolve(),'Unexpected cleanup path')
            shutil.rmtree(self.tmp)
        after={p._page_ref['id'] for p in web.get_all(mode='chrome')} if self.baseline is not None else set()
        source_ok=self.library_hash is None or hashlib.sha256((self.args.library/'elements.json').read_bytes()).hexdigest()==self.library_hash
        d={'errors':errors,'own_tab_closed':self.id not in after,'temporary_copy_removed':not self.tmp.exists(),'source_library_unchanged':source_ok,'tab_count':f'{len(self.baseline or set())}->{len(after)}','external_added':sorted(after-(self.baseline or set())),'external_removed':sorted((self.baseline or set())-after)}
        require(not errors and d['own_tab_closed'] and source_ok and not d['external_added'] and not d['external_removed'],d)
        return d

def scenarios():
    dom={'simulative':False}
    cdp={'simulative':False,'cdp_input':True}
    def item(name,text,kw,**extra): return {'id':name,'steps':[(text,kw)],'expected':text,**extra}
    return [
        item('dom_unicode',TEXT,dom),
        item('dom_literal_symbols',SPECIAL,dom),
        {'id':'dom_overwrite','steps':[('original',dom),(TEXT,dom)],'expected':TEXT},
        {'id':'dom_append','steps':[('前缀-',dom),('尾部😀',{**dom,'append':True})],'expected':'前缀-尾部😀'},
        {'id':'dom_empty_clear','steps':[(TEXT,dom),('',dom)],'expected':''},
        item('silent_default',TEXT,{}),
        item('silent_ignored_keyboard_options','silent',{'force_ime_eng':True,'send_key_delay':500,'focus_timeout':1000,'anchor':('top_left',5,5)}),
        item('dom_no_click',TEXT,{**dom,'click_before_input':False},no_focus=True,blur=True),
        item('delay_none',TEXT,{**dom,'delay_after':None}),
        item('delay_one_second',TEXT,{**dom,'delay_after':1},min_seconds=.95),
        item('check_default',TEXT,{**dom,'input_check':True}),
        item('check_explicit',TEXT,{**dom,'input_check':True,'retry_times':0,'check_value':TEXT}),
        item('check_fail_zero','actual',{**dom,'input_check':True,'retry_times':0,'check_value':'different'},error='input_check_failed',input_events=1),
        item('check_fail_two','actual',{**dom,'input_check':True,'retry_times':2,'check_value':'different'},error='input_check_failed',input_events=3),
        item('check_recovery','recovered',{**dom,'input_check':True,'retry_times':1},mutate=True,input_events=2),
        {'id':'check_append_no_retry','steps':[('prefix-',dom),('tail',{**dom,'append':True,'input_check':True,'retry_times':3,'check_value':'different'})],'expected':'prefix-tail','error':'input_check_failed','input_events':1},
        item('cdp_unicode',TEXT,cdp),
        {'id':'cdp_append','steps':[('CDP-',cdp),('尾部😀',{**cdp,'append':True})],'expected':'CDP-尾部😀'},
        item('cdp_priority',TEXT,{'simulative':True,'cdp_input':True}),
        item('cdp_no_click_focused',TEXT,{**cdp,'click_before_input':False},focus=True),
        item('cdp_no_click_unfocused','',{**cdp,'click_before_input':False},blur=True,error='element_not_focused'),
        {'id':'cdp_hotkey_replace','steps':[('old',dom),('^a新值',{**cdp,'append':True,'contains_hotkey':True,'input_check':True,'check_value':'新值','send_key_delay':0})],'expected':'新值'},
    ]

def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--library',type=Path,default=LIBRARY)
    parser.add_argument('--foreground',action='store_true',help='允许激活 Chrome 并使用系统键盘；运行期间勿操作电脑')
    parser.add_argument('--contract-only',action='store_true')
    parser.add_argument('--report-file',type=Path)
    args=parser.parse_args(argv); run=Run(args)
    print('UIAutoma Web API 测试\nAPI     : uiautoma.web.WebElement.input\n页面    : '+URL,flush=True)
    run.case('api_contract','签名、源码和只读 commit 与冻结合同一致',contract)
    invalid=[
        ('required_text',TypeError,lambda:WebElement.input(object())),
        ('extra_positional',TypeError,lambda:WebElement.input(object(),'x',False)),
        ('unknown_keyword',TypeError,lambda:WebElement.input(object(),'x',unknown=True)),
        ('invalid_simulative',InvalidParamsError,lambda:WebElement.input(object(),'x',simulative='false')),
        ('dom_hotkey_unsupported',UnsupportedActionError,lambda:WebElement.input(object(),'^a',simulative=False,contains_hotkey=True)),
        ('append_check_missing',InvalidParamsError,lambda:WebElement.input(object(),'x',simulative=False,append=True,input_check=True)),
        ('hotkey_check_missing',InvalidParamsError,lambda:WebElement.input(object(),'^a',cdp_input=True,contains_hotkey=True,input_check=True)),
        ('invalid_retry_negative',InvalidParamsError,lambda:WebElement.input(object(),'x',input_check=True,retry_times=-1)),
        ('invalid_retry_bool',InvalidParamsError,lambda:WebElement.input(object(),'x',input_check=True,retry_times=True)),
        ('invalid_retry_float',InvalidParamsError,lambda:WebElement.input(object(),'x',input_check=True,retry_times=1.5)),
        ('invalid_anchor',InvalidParamsError,lambda:WebElement.input(object(),'x',anchor='invalid-anchor')),
    ]
    for name,kind,fn in invalid: run.case(name,'在访问 Runtime 前抛 '+kind.__name__,lambda kind=kind,fn=fn:raises(kind,fn))
    if not args.contract_only:
        try:
            if run.case('environment','后台靶场、临时库、剪贴板截获器可用，保留用户标签',run.setup)=='PASS':
                for side in NAMES:
                    if run.case(side+'_library_mapping','库选择器唯一命中指定 '+side+' input',lambda side=side:run.mapping(side))!='PASS': continue
                    for spec in scenarios():
                        run.case(side+'_'+spec['id'],'返回/异常符合合同，原生 DOM 与真实提交 text 均为 '+repr(spec['expected']),lambda side=side,spec=spec:run.scenario(side,spec))
                if args.foreground:
                    for side in NAMES:
                        for spec in [
                            {'id':'keyboard_default','steps':[('SDK 中文 123',{})],'expected':'SDK 中文 123'},
                            {'id':'keyboard_ime_delay_anchor','steps':[('IME123',{'force_ime_eng':True,'send_key_delay':0,'focus_timeout':0,'anchor':{'anchor':'middle_center','offset_x':0,'offset_y':0}})],'expected':'IME123'},
                            {'id':'keyboard_append','steps':[('key-',{}),('tail',{'append':True})],'expected':'key-tail'},
                        ]: run.case(side+'_'+spec['id'],'系统键盘输入与真实表单提交一致',lambda side=side,spec=spec:run.scenario(side,spec))
        finally: run.case('cleanup','关闭自有页面/库，删除副本，源库和外部标签基线不变',run.cleanup)
    code=1 if any(r['status']=='FAIL' for r in run.rows) else 2 if any(r['status']=='BLOCKED' for r in run.rows) else 0
    report={'api':'uiautoma.web.WebElement.input','date':'2026-10-08','lifecycle':'VERIFIED' if code==0 and not args.contract_only else 'READY_FOR_LIVE','scope':'background plus system keyboard' if args.foreground else 'background DOM/silent-default/CDP; system keyboard excluded','product_worktree':str(PRODUCT),'product_commit':subprocess.check_output(['git','-C',str(PRODUCT),'rev-parse','HEAD'],text=True).strip(),'url':URL,'library':str(args.library),'results':run.rows,'exit_code':code}
    if args.report_file:
        args.report_file.parent.mkdir(parents=True,exist_ok=True)
        args.report_file.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    passed=sum(r['status']=='PASS' for r in run.rows)
    print(f"{'测试通过' if code==0 else '测试失败' if code==1 else '测试阻塞'} · {passed}/{len(run.rows)} 通过 · 退出码 {code}",flush=True)
    return code

if __name__=='__main__': raise SystemExit(main())
