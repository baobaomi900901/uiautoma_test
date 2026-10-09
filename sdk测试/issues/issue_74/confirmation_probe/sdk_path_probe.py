"""Exact Cookie parameters, only WebBrowser page binding differs; background only."""
import json
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace

sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'web'))
from _web_browser_cookie_common import CookieContext, URL, PRODUCT, ActionError

report={'headless_native_comparator':'browser_set_cookie_native_confirmation_20261006.json',
        'silent_running':True,'product_worktree':str(PRODUCT),
        'product_commit':subprocess.check_output(['git','-C',str(PRODUCT),'rev-parse','HEAD'],text=True).strip(),
        'pairs':[]}
c=CookieContext('set_cookie',SimpleNamespace(target_url=URL,json=True))
code=0
try:
    report['environment']=c.setup()
    guard=c.guard_page()
    for round in (1,2,3):
        name=c.register('pair_'+str(round),'/xpath/stop-load-test/')
        params={'name':name,'value':'same-write','path':'/xpath/stop-load-test/','sessionCookie':True}
        pair={'round':round,'params':params,'calls':[]}
        report['pairs'].append(pair)
        sequence=[('main',c.page),('guard',guard)] if round!=2 else [('guard',guard),('main',c.page)]
        for label,page in sequence:
            try:
                returned=page.set_cookie(**params)
                actual={'return':returned}
            except ActionError as exc:
                actual={'exception':type(exc).__name__,'message':str(exc),'trace':exc.trace_info}
            native_main=c.observe()
            native_guard=c.observe(guard)
            row={'page':label,'url':page.get_url(),'actual':actual,
                 'native_main':[n for n in native_main['cookies'] if n['name']==name],
                 'native_guard':[n for n in native_guard['cookies'] if n['name']==name]}
            pair['calls'].append(row)
            c.require(len(row['native_guard'])==1 and row['native_guard'][0]['value']=='same-write'
                      and not row['native_main'],row)
            if label=='main':
                c.require(actual=={'exception':'ActionError','message':'浏览器操作失败，请重试','trace':'cookie_set_failed'},row)
            else:
                c.require(actual=={'return':None},row)
            row['confirmation_status']='PASS'
            print('pair',round,label,json.dumps(row,ensure_ascii=False),flush=True)
    report['confirmation']='SAME_PARAMETERS_PAGE_URL_ISOLATED'
except Exception as exc:
    code=1
    report['error']={'exception':type(exc).__name__,'message':str(exc)}
    print('error',json.dumps(report['error'],ensure_ascii=False),flush=True)
finally:
    try:
        report['cleanup']=c.cleanup()
        print('cleanup',json.dumps(report['cleanup'],ensure_ascii=False),flush=True)
    except Exception as exc:
        code=1
        report['cleanup']={'exception':type(exc).__name__,'message':str(exc)}
    report['exit_code']=code
    (ROOT/'web/evidence/artifacts/browser_set_cookie_sdk_path_confirmation_20261006.json').write_text(
        json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
raise SystemExit(code)
