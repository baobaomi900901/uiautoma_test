import json
from pathlib import Path
import sys
import time
sys.dont_write_bytecode = True
sys.path.insert(0, r'D:\code\desktop\sdk\src')
sys.path.insert(0, r'D:\code\元素库\sdk测试\web')
from uiautoma import web, open as open_package, ping
from test_web_element_get_select_options import copy_library, disable_dynamic_ids, find_switch

ROOT = "document.querySelector('#iframe-shadow-form').contentDocument.querySelector('#form-shadow-host').shadowRoot"
tmp = Path(__file__).parent / 'library'
page = package = None
previous = None
baseline = set()
report = {'cases': []}
def js(body, arg=None, main=False):
    return page.execute_javascript('function(_e,a){const root='+ROOT+';'+body+'}', arg, execution_world='MAIN' if main else 'ISOLATED')
try:
    ping(timeout=5)
    baseline = {p._page_ref['id'] for p in web.get_all(mode='chrome')}
    copy_library(Path(r'D:\code\元素库\260902_web元素'), tmp)
    package = open_package(str(tmp), timeout=8, connect_timeout=8)
    page = web.create('https://baobaomi900901.github.io/xpath/#/iframe-shadow-form', mode='chrome', silent_running=True, load_timeout=25)
    previous = disable_dynamic_ids(page)
    # Only replace clipboard writes on this owned page, in MAIN; form handlers and state stay intact.
    report['observer'] = js("window.__inputProbe=[];for(const n of [navigator,document.querySelector('#iframe-shadow-form').contentWindow.navigator]){Object.defineProperty(n.clipboard,'writeText',{configurable:true,value:async t=>{window.__inputProbe.push(String(t));}});}return true;", main=True)
    for side, name in [('ant', 'web靶场_表单测试_ant_输入框'), ('native', 'web靶场_表单测试_原生_输入框')]:
        for mode in ['dom', 'silent_default', 'cdp']:
            js("root.getElementById('form-controls-'+a+'-reset').click();return true;", side)
            time.sleep(.15)
            el = page.find(name, timeout=4)
            report['cases'].append(row := {'side': side, 'mode': mode, 'id': el.get_attribute('id')})
            try:
                kwargs={'delay_after':.1}
                if mode=='dom': kwargs['simulative']=False
                if mode=='cdp': kwargs.update(simulative=False, cdp_input=True)
                row['return'] = el.input('SDK中文123😀', **kwargs)
                row['native_value'] = js("return root.getElementById('form-controls-'+a+'-text').value;", side)
                js("root.getElementById('form-controls-'+a+'-submit').click();return true;", side)
                for _ in range(25):
                    value=js("return root.getElementById(a+'-result').textContent;",side)
                    try: row['submitted']=json.loads(value); break
                    except ValueError: time.sleep(.1)
                row['clipboard_observed']=js("return window.__inputProbe.length;",main=True)
            except Exception as exc:
                row['error']={'exception':type(exc).__name__,'message':str(exc),'trace':getattr(exc,'trace_info','')}
            print(json.dumps(row, ensure_ascii=False), flush=True)
except Exception as exc:
    report['environment_error']={'exception':type(exc).__name__,'message':str(exc),'trace':getattr(exc,'trace_info','')}
    print(json.dumps(report['environment_error'],ensure_ascii=False),flush=True)
finally:
    errors=[]
    if page:
        try:
            if previous=='true': find_switch(page).click(simulative=False,delay_after=0)
            page.close(ignore_beforeunload=True)
        except Exception as exc: errors.append(str(exc))
    if package:
        try: package.close()
        except Exception as exc: errors.append(str(exc))
    if tmp.exists():
        import shutil
        assert tmp.resolve().parent==Path(__file__).parent.resolve()
        shutil.rmtree(tmp)
    try:
        after={p._page_ref['id'] for p in web.get_all(mode='chrome')}
        report['cleanup']={'errors':errors,'tabs':f'{len(baseline)}->{len(after)}','external_added':sorted(after-baseline),'external_removed':sorted(baseline-after)}
    except Exception as exc: report['cleanup']={'errors':errors+[str(exc)]}
    Path(__file__).with_suffix('.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('cleanup',json.dumps(report['cleanup'],ensure_ascii=False),flush=True)
