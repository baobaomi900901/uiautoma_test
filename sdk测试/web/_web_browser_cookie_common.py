"""五个页面 Cookie API 的验收准备、独立原生观察和报告。

靶场为线上 cookie-test；补充同源 slow.svg 文档核对不同 Path。
Cookie Store API / document.cookie 为 oracle，不以 SDK Cookie 读回替代。
原始 Cookie 值只留在内存；报告仅记录本次随机名称的数据。
"""
from __future__ import annotations

import argparse
import hashlib
import inspect
import json
from pathlib import Path
import subprocess
import sys
import time
from urllib.parse import urlsplit
import uuid

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
PRODUCT = Path(r'D:\code\desktop')
sys.path.insert(0, str(PRODUCT/'sdk/src'))
from uiautoma import web, ActionError, InvalidParamsError, HostUnavailableError
from uiautoma.web import WebBrowser

URL = 'https://baobaomi900901.github.io/xpath/#/cookie-test'
GUARD_URL = 'https://baobaomi900901.github.io/xpath/stop-load-test/slow.svg'
CONTRACT = ROOT/'web/browser_cookie_contracts_20261006.json'
APIS = ('get_cookies', 'get_cookie', 'set_cookie', 'remove_cookie', 'clear_cookies')
NATIVE = '''async function(_e,p){
  if(typeof cookieStore==='undefined')throw new Error('native_cookie_store_unavailable');
  const cookies=await cookieStore.getAll();
  const pairs=document.cookie.split(';').map(x=>x.trim()).filter(Boolean).map(x=>{
    const i=x.indexOf('=');return {name:x.slice(0,i),value:x.slice(i+1)};});
  return {url:location.href,hostname:location.hostname,path:location.pathname,now:Date.now(),
    cookies:cookies.filter(c=>c.name.startsWith(p)),
    pairs:pairs.filter(c=>c.name.startsWith(p)), foreign:cookies.filter(c=>!c.name.startsWith(p)),
    readyState:document.readyState,userAgent:navigator.userAgent};
}'''


class MissingScene(Exception):
    pass


class CookieContext:
    def __init__(self, api, args):
        self.api, self.args = api, args
        self.rows, self.pages, self.ledger = [], [], []
        self.page = self.guard = None
        self.baseline = None
        self.foreign = {}
        self.prefix = 'sdk_browser_cookie_'+uuid.uuid4().hex+'_'
        self.origin = f'{urlsplit(args.target_url).scheme}://{urlsplit(args.target_url).netloc}'
        self.host = urlsplit(args.target_url).hostname
        self.partition = {'top_level_site':self.origin, 'has_cross_site_ancestor':False}
        self.cleaned_cookies = False

    def name(self, suffix):
        return self.prefix+suffix

    def require(self, condition, detail):
        if not condition:
            raise AssertionError(repr(detail))
        return detail

    def case(self, name, expected, fn):
        started = time.perf_counter()
        try:
            actual, status = fn(), 'PASS'
        except (MissingScene, HostUnavailableError) as exc:
            status, actual = 'BLOCKED', {'exception':type(exc).__name__, 'message':str(exc)}
        except Exception as exc:
            trace = getattr(exc, 'trace_info', '')
            status = 'BLOCKED' if trace in {'plugin_not_connected','native_host_unavailable',
                'web_bridge_unavailable','uiautomation_provider_unavailable','web_environment_ambiguous'} else 'FAIL'
            actual = {'exception':type(exc).__name__, 'message':str(exc), 'trace':trace}
            actual.update(getattr(exc,'_test_details',{}))
        row = {'case_id':name, 'status':status, 'expected':expected, 'actual':actual,
               'elapsed_ms':round((time.perf_counter()-started)*1000, 1)}
        self.rows.append(row)
        if not self.args.json:
            print(f"已执行 {name}: {status}", flush=True)
        return status

    def raises(self, kind, fn, message='', trace=''):
        try:
            fn()
        except kind as exc:
            detail = {'exception':type(exc).__name__, 'message':str(exc), 'trace':getattr(exc,'trace_info','')}
            return self.require((not message or str(exc)==message) and (not trace or detail['trace']==trace), detail)
        raise AssertionError('预期 '+kind.__name__)

    def observe(self, page=None):
        value = (page or self.page).execute_javascript(NATIVE, self.prefix)
        # 不把外部 Cookie 的值/名称输出到证据。
        foreign = value.pop('foreign')
        value['foreign_fingerprint'] = hashlib.sha256(json.dumps(foreign,sort_keys=True).encode()).hexdigest()
        value['foreign_count'] = len(foreign)
        return value

    @staticmethod
    def cookie_key(cookie):
        return cookie['name'], cookie['path'], cookie.get('domain') or '', bool(cookie.get('partitioned'))

    def values(self, state):
        return sorted((x['name'],x['value'],x['path'],bool(x['partitioned'])) for x in state['cookies'])

    def setup(self):
        self.baseline = {p._page_ref['id'] for p in web.get_all(mode='chrome')}
        self.page = web.create(self.args.target_url, mode='chrome', load_timeout=25, silent_running=True)
        self.pages.append(self.page)
        ready = self.page.execute_javascript('function(){return {url:location.href,form:!!document.getElementById("cookie-add-submit"),state:document.readyState}}')
        self.require(ready['form'] and ready['state']=='complete', ready)
        first = self.observe()
        self.foreign['main'] = first['foreign_fingerprint']
        return {'url':ready['url'], 'user_agent':first['userAgent'], 'baseline_tabs':len(self.baseline),
                'foreign_cookie_count':first['foreign_count'], 'silent_running':True, 'native_cookie_store':True}

    def guard_page(self):
        if self.guard is None:
            self.guard = web.create(GUARD_URL, mode='chrome', load_timeout=20, silent_running=True)
            self.pages.append(self.guard)
            baseline = self.observe(self.guard)
            self.foreign['guard'] = baseline['foreign_fingerprint']
        return self.guard

    def register(self, suffix, path='/xpath/', partitioned=False, domain=None, http_only=False):
        item = {'name':self.name(suffix), 'path':path, 'partitioned':partitioned,
                'domain':domain, 'http_only':http_only}
        if item not in self.ledger:
            self.ledger.append(item)
        return item['name']

    def seed(self, suffix, value, path='/xpath/', secure=False, persistent=False, partitioned=False, domain=None):
        name = self.register(suffix, path, partitioned, domain)
        options = {'name':name, 'value':value, 'path':path, 'secure':secure,
                   'persistent':persistent, 'partitioned':partitioned, 'domain':domain}
        self.page.execute_javascript('''function(_e,c){let parts=[c.name+'='+c.value,'Path='+c.path,'SameSite=Lax'];
          if(c.secure)parts.push('Secure');if(c.persistent)parts.push('Max-Age=600');
          if(c.partitioned)parts.push('Partitioned');if(c.domain)parts.push('Domain='+c.domain);
          document.cookie=parts.join('; ');}''', options)
        return name

    def fixtures(self):
        self.seed('session','session-value')
        self.seed('persistent','persistent-value',path='/',secure=True,persistent=True)
        self.seed('domain','domain-value',domain=self.host)
        self.seed('partition','partition-value',secure=True,partitioned=True)
        # 用原生 Cookie Store 准备另一路径项，另开真实同源文档读取它。
        name = self.register('guard', '/xpath/stop-load-test/')
        self.page.execute_javascript('async function(_e,c){await cookieStore.set(c)}',
            {'name':name,'value':'guard-value','path':'/xpath/stop-load-test/'})
        state = self.observe()
        self.require(len(state['cookies'])==4 and sum(x['partitioned'] for x in state['cookies'])==1, state)
        guard = self.observe(self.guard_page())
        self.require(any(x['name']==name and x['value']=='guard-value' for x in guard['cookies']), guard)
        return {'main':state, 'guard':guard, 'oracle':'native cookieStore + document.cookie; seeds are native JS'}

    def compare(self, actual, expected, state):
        actual_owned = [x for x in actual if x.get('name','').startswith(self.prefix)]
        self.require(len(actual_owned)==len(expected), {'expected_count':len(expected),'actual':actual_owned})
        used = set()
        for n in expected:
            matches = [(i,s) for i,s in enumerate(actual_owned) if s['name']==n['name'] and s['path']==n['path']
                       and s.get('domain','').lstrip('.')==(n['domain'] or state['hostname']).lstrip('.')]
            self.require(len(matches)==1, {'native':n, 'matches':matches})
            i,s = matches[0]
            used.add(i)
            self.require(s['value']==n['value'] and s['secure'] is n['secure'] and s['httpOnly'] is False
                         and s['session'] is (n['expires'] is None) and s['hostOnly'] is (n['domain'] is None),
                         {'native':n,'sdk':s})
            if n['expires'] is None:
                self.require('expirationDate' not in s, s)
            else:
                self.require(abs(s.get('expirationDate',0)*1000-n['expires']) <= 2, {'native':n,'sdk':s})
            if n['partitioned']:
                self.require(s.get('partitionKey')=={'topLevelSite':self.origin,'hasCrossSiteAncestor':False}, s)
            else:
                self.require('partitionKey' not in s, s)
            native_site = 'no_restriction' if n['sameSite']=='none' else n['sameSite']
            self.require(s['sameSite']==native_site, {'native':n,'sdk':s})
        return {'cookies':actual_owned, 'native_expected':expected, 'count':len(expected)}

    def read_all(self, page=None, **filters):
        page = page or self.page
        state = self.observe(page)
        part = bool(filters.get('partition_key'))
        expected = [n for n in state['cookies'] if n['partitioned']==part]
        for key in ('name','path','secure','session'):
            if key in filters:
                expected = [n for n in expected if (n['expires'] is None if key=='session' else n[key])==filters[key]]
        if filters.get('domain'):
            domain = filters['domain'].lstrip('.')
            expected = [n for n in expected if (n['domain'] or self.host).lstrip('.')==domain
                        or (n['domain'] or self.host).lstrip('.').endswith('.'+domain)]
        if part:
            requested=filters['partition_key']
            if requested.get('top_level_site',requested.get('topLevelSite'))!=self.origin \
                    or requested.get('has_cross_site_ancestor',requested.get('hasCrossSiteAncestor',False)):
                expected=[]
        actual = page.get_cookies(**filters)
        self.require(type(actual) is list, type(actual).__name__)
        return self.compare(actual, expected, state)

    def read_one(self, suffix, page=None):
        page = page or self.page
        state = self.observe(page)
        expected = [n for n in state['cookies'] if n['name']==self.name(suffix) and not n['partitioned']]
        actual = page.get_cookie(name=self.name(suffix))
        self.require(type(actual) is dict, type(actual).__name__)
        if not expected:
            return self.require(actual=={}, {'return':actual, 'native_matches':0})
        wanted = sorted(expected,key=lambda x:-len(x['path']))[0]
        return self.compare([actual], [wanted], state)

    def repeat_read(self, single=False):
        before = self.observe()
        samples = [self.read_one('session') if single else self.read_all(name=self.name('session')) for _ in range(3)]
        after = self.observe()
        self.require(self.values(before)==self.values(after), {'before':before,'after':after})
        return {'samples':samples, 'native_unchanged':True}

    def partition_parameters(self):
        method = getattr(self.page, self.api)
        kwargs = {'name':self.name('partition')} if self.api=='remove_cookie' else {}
        result=[]
        for value,kind,message in [( [],TypeError,'partition_key must be a mapping'),
            ({},ValueError,'partition_key.top_level_site is required'),
            ({'top_level_site':self.origin,'has_cross_site_ancestor':'false'},TypeError,'partition_key.has_cross_site_ancestor must be a bool')]:
            result.append(self.raises(kind, lambda v=value:method(**kwargs,partition_key=v),message))
        return result

    def duplicate_fixture(self):
        self.seed('duplicate','root',path='/')
        self.seed('duplicate','deep',path='/xpath/')
        before = self.observe()
        self.require(sorted(n['value'] for n in before['cookies'] if n['name']==self.name('duplicate'))==['deep','root'],before)
        return before

    def remove(self, suffix, partition_key=None):
        before = self.observe()
        returned = self.page.remove_cookie(self.name(suffix), partition_key=partition_key)
        after = self.observe()
        self.require(returned is None, returned)
        part = partition_key is not None
        expected = [n for n in before['cookies'] if not (n['name']==self.name(suffix) and n['partitioned']==part)]
        self.require(self.values({'cookies':expected})==self.values(after), {'before':before,'after':after})
        return {'return':returned,'before':before,'after':after,'deleted_name':self.name(suffix)}

    def scope_absent(self, remove=False):
        before = self.observe(self.guard_page())
        returned = self.page.remove_cookie(self.name('guard')) if remove else self.page.get_cookie(name=self.name('guard'))
        after = self.observe(self.guard)
        self.require(returned is None if remove else returned=={}, returned)
        self.require(self.values(before)==self.values(after), {'before':before,'after':after})
        return {'return':returned,'other_path_retained':True,'guard':after}

    def clear(self, partition_key=None):
        before = self.observe()
        part = partition_key is not None
        # 独立原生观察与 SDK 预检查共同保护：外部数据存在时不调用清理。
        sdk_scope = self.page.get_cookies(partition_key=partition_key)
        if before['foreign_count'] or any(not x['name'].startswith(self.prefix) for x in sdk_scope):
            raise MissingScene('当前 Cookie 范围有本次测试以外的数据；拒绝批量清理')
        guard_before = self.observe(self.guard_page())
        returned = self.page.clear_cookies(partition_key=partition_key)
        after, guard_after = self.observe(), self.observe(self.guard)
        match = not part or partition_key.get('top_level_site',partition_key.get('topLevelSite'))==self.origin
        expected = [n for n in before['cookies'] if not (match and n['partitioned']==part)]
        self.require(returned is None and self.values({'cookies':expected})==self.values(after), {'return':returned,'before':before,'after':after})
        guard_name=self.name('guard')
        self.require([n for n in guard_before['cookies'] if n['name']==guard_name]
                     ==[n for n in guard_after['cookies'] if n['name']==guard_name], guard_after)
        return {'return':returned,'before':before,'after':after,'guard_retained':True,'guard_after':guard_after}

    def write(self, suffix, value='written', **options):
        path = options.get('path') or '/xpath'
        name = self.register(suffix,path,domain=options.get('domain'),http_only=options.get('httpOnly',False))
        before = self.observe()
        returned = self.page.set_cookie(name=name,value=value,**options)
        after = self.observe()
        self.require(returned is None, returned)
        native = [n for n in after['cookies'] if n['name']==name and n['path']==path]
        self.require(len(native)==1,after)
        n=native[0]
        self.require(n['value']==('' if value is None else value) and n['secure'] is options.get('secure',False)
                     and n['domain']==(options.get('domain') or None) and not n['partitioned'],n)
        if options.get('sessionCookie',False):
            self.require(n['expires'] is None,n)
        else:
            duration=options.get('expires',100)*1000
            self.require(before['now']+duration-100 <= n['expires'] <= after['now']+duration+100,n)
        return {'return':returned,'native':n,'time_before':before['now'],'time_after':after['now']}

    def http_only_protection(self):
        name=self.register('http_only','/xpath/',http_only=True)
        returned=self.page.set_cookie(name=name,value='hidden-value',path='/xpath/',httpOnly=True)
        before=self.observe()
        self.page.execute_javascript('function(_e,n){document.cookie=n+"=tamper;Path=/xpath/"}',name)
        blocked=self.observe()
        self.require(returned is None and not any(n['name']==name for s in (before,blocked) for n in s['cookies']),blocked)
        # 删除后同名同 Path 的 JS Cookie 可以创建，排除“该名称/路径不能写”的替代原因。
        self.page.remove_cookie(name)
        self.page.execute_javascript('function(_e,n){document.cookie=n+"=after-remove;Path=/xpath/"}',name)
        unblocked=self.observe()
        self.require(any(n['name']==name and n['value']=='after-remove' for n in unblocked['cookies']),unblocked)
        return {'return':returned,'hidden_before_and_after_js_overwrite':True,'native_after_removal':unblocked,
                'boundary':'独立验证 HttpOnly 防脚本覆盖；没有服务端或 CDP 验证隐藏值'}

    def stale_page(self):
        closed=web.create(self.args.target_url,mode='chrome',load_timeout=20,silent_running=True)
        self.pages.append(closed)
        closed.close(ignore_beforeunload=True)
        kwargs={'name':self.name('stale')} if self.api in {'get_cookie','set_cookie','remove_cookie'} else {}
        return self.raises(ActionError,lambda:getattr(closed,self.api)(**kwargs),'网页对象已失效','stale_page_reference')

    def cleanup(self):
        errors=[]
        if self.page is not None:
            for item in self.ledger:
                try:
                    if item['http_only']:
                        self.page.remove_cookie(item['name'])
                        # Native JS creation confirms that no hidden HttpOnly key remains.
                        self.page.execute_javascript('function(_e,c){document.cookie=c.name+"=cleanup-probe;Path="+c.path}',item)
                        self.require(any(n['name']==item['name'] for n in self.observe()['cookies']),item['name'])
                    # CookieStore.delete 会把 /xpath 规范化成 /xpath/，不能删除 SDK 默认 Path。
                    # document.cookie 保留精确 Path，并可显式删除第一方 Partitioned 项。
                    self.page.execute_javascript('''function(_e,c){let parts=[c.name+'=','Max-Age=0','Path='+c.path];
                      if(c.domain)parts.push('Domain='+c.domain);
                      if(c.partitioned)parts.push('Secure','Partitioned');
                      document.cookie=parts.join('; ');}''',item)
                except Exception as exc:
                    errors.append(type(exc).__name__+': '+str(exc))
            for label,page in [('main',self.page),('guard',self.guard)]:
                if page is None:
                    continue
                try:
                    observed=self.observe(page)
                    self.require(not observed['cookies'],observed)
                    self.require(observed['foreign_fingerprint']==self.foreign[label], '外部 Cookie 原生基线变化：'+label)
                except Exception as exc:
                    errors.append(type(exc).__name__+': '+str(exc))
            self.cleaned_cookies=not errors
        for page in reversed(self.pages):
            try:
                if any(p._page_ref['id']==page._page_ref['id'] for p in web.get_all(mode='chrome')):
                    page.close(ignore_beforeunload=True)
            except Exception as exc:
                errors.append('page: '+str(exc))
        after={p._page_ref['id'] for p in web.get_all(mode='chrome')}
        detail={'errors':errors,'owned_cookies_removed':self.cleaned_cookies,
                'foreign_cookie_baseline_preserved':not errors,'tab_count':f'{len(self.baseline or [])}->{len(after)}',
                'own_tabs_closed':not any(p._page_ref['id'] in after for p in self.pages),
                'external_added':sorted(after-(self.baseline or set())), 'external_removed':sorted((self.baseline or set())-after)}
        self.require(not errors and detail['own_tabs_closed'],detail)
        if self.baseline is not None and after!=self.baseline:
            raise MissingScene('外部标签在测试期间发生变化：'+repr(detail))
        return detail


def matrix(c):
    name=c.api
    p=c.page
    steps=[]
    def add(case,expected,fn):steps.append((case,expected,fn))
    add('native_fixtures','原生 JS 准备会话/持久、域 Cookie、分区和其他 Path；Cookie Store 确认',c.fixtures)
    if name=='get_cookies':
        add('get_all','返回 list；本次所有匹配未分区项的值和属性与原生数据逐项一致',c.read_all)
        add('filter_name','唯一名称筛选命中一个本次 Cookie，完整属性正确',lambda:c.read_all(name=c.name('session')))
        add('name_not_found','随机不存在名称返回 []',lambda:c.read_all(name=c.name('not_found')))
        for suffix,filters in [('domain',{'domain':c.host}),('domain_parent',{'domain':'github.io'}),
                ('domain_dot',{'domain':'.'+c.host}),('domain_miss',{'domain':'sdk-not-matching.invalid'}),
                ('path_root',{'path':'/'}),('path_exact',{'path':'/xpath/'}),('path_miss',{'path':'/xpath'}),
                ('secure_true',{'secure':True}),('secure_false',{'secure':False}),
                ('session_true',{'session':True}),('session_false',{'session':False}),
                ('combined',{'name':c.name('persistent'),'path':'/','secure':True,'session':False})]:
            add('filter_'+suffix,'筛选结果及属性与原生 Cookie Store 的独立筛选结果一致',lambda f=filters:c.read_all(**f))
        add('current_page_scope','同源其他真实文档的额外 Path 项只在该网页 get_cookies 中出现',lambda:c.read_all(page=c.guard_page()))
        add('partition_dict','字典分区命中真正 Partitioned Cookie，完整属性和 topLevelSite/祖先标记正确',lambda:c.read_all(partition_key=c.partition))
        add('partition_alias','camelCase 字典别名得到相同正确分区结果',lambda:c.read_all(partition_key={'topLevelSite':c.origin,'hasCrossSiteAncestor':False}))
        add('partition_wrong_site','错误顶层站点分区返回 []',lambda:c.read_all(partition_key={'top_level_site':'https://example.invalid'}))
        add('partition_wrong_ancestor','first-party 页没有跨站祖先；请求 True 分区返回 []',lambda:c.read_all(partition_key={'top_level_site':c.origin,'has_cross_site_ancestor':True}))
        add('partition_parameters','非法分区类型、空站点与非法祖先类型按源码合同拒绝',c.partition_parameters)
        add('repeat_readonly','三次读取一致；原生 Cookie 数据未改变',c.repeat_read)
    elif name=='get_cookie':
        add('single_session','会话 Cookie 返回 dict，所有属性与原生 Cookie Store 一致',lambda:c.read_one('session'))
        add('single_persistent','持久 Cookie 的值、Secure、有效期与原生结果一致',lambda:c.read_one('persistent'))
        add('single_domain','域 Cookie 的 domain/hostOnly 等属性正确',lambda:c.read_one('domain'))
        add('not_found','未匹配返回 {}',lambda:c.read_one('not_found'))
        add('partition_only_absent','本方法无分区参数；仅分区项返回 {}',lambda:c.read_one('partition'))
        add('other_path_absent','当前网页不匹配另一 Path 的 Cookie，返回 {}；另一文档中的项保留',c.scope_absent)
        add('other_page_binding','另一个 WebBrowser 引用按自己的 URL 读取匹配项',lambda:c.read_one('guard',c.guard_page()))
        def duplicate():
            before=c.duplicate_fixture()
            return {'before':before,'result':c.read_one('duplicate')}
        add('duplicate_longest_path','同名两项都存在时返回最长匹配 Path（/xpath/）的 Cookie',duplicate)
        add('missing_name','未提供名称抛 InvalidParamsError / missing name',lambda:c.raises(InvalidParamsError,lambda:p.get_cookie(),'missing name','invalid_params'))
        add('blank_name','空名称抛 InvalidParamsError / missing name',lambda:c.raises(InvalidParamsError,lambda:p.get_cookie(name=''),'missing name','invalid_params'))
        add('repeat_readonly','连续三次读取正常，原生 Cookie 数据未改变',lambda:c.repeat_read(single=True))
    elif name=='set_cookie':
        add('default_persistent','默认持久 Cookie、100 秒、默认 URL Path /xpath、hostOnly、Secure False、返回 None',lambda:c.write('defaults',value=None))
        add('session_cookie','sessionCookie=True 的过期时间为空，值正确，返回 None',lambda:c.write('session_write',sessionCookie=True,path='/xpath/'))
        add('fractional_expiry','expires 接受有限小数，原生有效期落在调用前后时钟 + 2.5 秒范围',lambda:c.write('fractional',expires=2.5,path='/xpath/'))
        add('secure_cookie','Secure True 写入原生属性正确，返回 None',lambda:c.write('secure_write',secure=True,path='/xpath/'))
        add('domain_cookie','显式当前域名写为域 Cookie，原生 domain 正确',lambda:c.write('domain_write',domain=c.host,path='/xpath/'))
        add('empty_value','value=None 规范化为空字符串，原生值为空',lambda:c.write('empty_write',value=None,path='/xpath/'))
        def overwrite():
            first=c.write('overwrite',value='first',path='/xpath/')
            second=c.write('overwrite',value='second',path='/xpath/')
            return {'first':first,'second':second}
        add('overwrite','同名/同域/同 Path 覆盖后仅一个项且原生值是 second',overwrite)
        def other_path():
            n=c.register('outside_write','/xpath/stop-load-test/')
            try:
                returned=p.set_cookie(name=n,value='other-path',path='/xpath/stop-load-test/',sessionCookie=True)
            except ActionError as exc:
                exc._test_details={'native_main':c.observe(),'native_guard':c.observe(c.guard_page()),
                    'requested':{'name':n,'value':'other-path','path':'/xpath/stop-load-test/','sessionCookie':True}}
                raise
            main=c.observe();guard=c.observe(c.guard_page())
            c.require(returned is None and not any(x['name']==n for x in main['cookies'])
                      and any(x['name']==n and x['value']=='other-path' and x['expires'] is None for x in guard['cookies']),{'main':main,'guard':guard})
            return {'return':returned,'main_hidden':True,'native_guard':guard}
        add('other_path_write','另一路径写入只在真实匹配文档的原生观察中可见',other_path)
        add('http_only_protection','写入后脚本不能读取或覆盖；删除后同名同 Path 可由 JS 创建，排除未写入',c.http_only_protection)
        def expiry():
            written=c.write('expiry',expires=1.2,path='/xpath/')
            started=time.monotonic();last=None
            while time.monotonic()-started<5:
                last=c.observe()
                if not any(n['name']==c.name('expiry') for n in last['cookies']):break
                time.sleep(.1)
            elapsed=time.monotonic()-started
            c.require(not any(n['name']==c.name('expiry') for n in last['cookies']) and .8<=elapsed<5,{'elapsed':elapsed,'after':last})
            return {'written':written,'native_expired':True,'elapsed_seconds':round(elapsed,3)}
        add('natural_expiry','1.2 秒有效期自然到期；原生 Cookie 消失，无 SDK 删除操作',expiry)
        add('missing_name','未提供名称抛 InvalidParamsError / missing name',lambda:c.raises(InvalidParamsError,lambda:p.set_cookie(),'missing name','invalid_params'))
        add('blank_name','空名称抛 InvalidParamsError / missing name',lambda:c.raises(InvalidParamsError,lambda:p.set_cookie(name=''),'missing name','invalid_params'))
        def invalid_expiry():
            return [c.raises(InvalidParamsError,lambda v=v:p.set_cookie(name=c.name('invalid'),expires=v),
                'Cookie 有效期必须为有限秒数','invalid_params') for v in (float('nan'),float('inf'),True,None)]
        add('invalid_expiry','NaN/Infinity/bool/None 有效期均拒绝，未生成 Cookie',invalid_expiry)
        def invalid_flags():
            return [c.raises(InvalidParamsError,lambda k=k:p.set_cookie(name=c.name('invalid'),**{k:'true'}),
                'Cookie 开关必须为布尔值','invalid_params') for k in ('sessionCookie','httpOnly','secure')]
        add('invalid_flags','三个布尔开关均拒绝字符串 true',invalid_flags)
    elif name=='remove_cookie':
        add('remove_one','指定未分区 Cookie 被删除，返回 None，其他项不变',lambda:c.remove('session'))
        add('remove_again','重复删除返回 None，保留其他项',lambda:c.remove('session'))
        add('remove_absent','不存在名称返回 None，原生数据不变',lambda:c.remove('not_found'))
        add('other_path_retained','当前 URL 不匹配的同名目标不能删除，真实匹配文档中的项保留',lambda:c.scope_absent(remove=True))
        add('default_partition_scope','不传分区时不能删除仅 Partitioned 项',lambda:c.remove('partition'))
        add('remove_partition','字典指定分区后删除对应 Partitioned 项，其他项不变',lambda:c.remove('partition',c.partition))
        def duplicate():
            before=c.duplicate_fixture()
            return {'before':before,'result':c.remove('duplicate')}
        add('same_name_paths','当前 Chrome 删除当前 URL 匹配的同名多 Path 项；不同名称保留',duplicate)
        add('blank_name','空名称抛 InvalidParamsError / missing name',lambda:c.raises(InvalidParamsError,lambda:p.remove_cookie(''),'missing name','invalid_params'))
        add('partition_parameters','非法分区类型、空站点和非法祖先类型按源码合同拒绝',c.partition_parameters)
    else:
        add('wrong_partition_noop','错误分区返回 None，全部原生数据和其他 Path 项保留',lambda:c.clear({'top_level_site':'https://example.invalid'}))
        add('clear_unpartitioned','清理匹配当前 URL 的未分区项，返回 None；分区与另一 Path 项保留',c.clear)
        add('clear_again','重复清理未分区空结果返回 None；分区与另一 Path 项保留',c.clear)
        add('clear_partition','显式字典分区清理对应项；另一路径项仍保留',lambda:c.clear(c.partition))
        add('clear_partition_again','重复清理分区空结果返回 None，其他 Path 项保留',lambda:c.clear(c.partition))
        add('partition_parameters','非法分区类型、空站点和非法祖先类型均拒绝',c.partition_parameters)
    return steps


def run(api,args):
    c=CookieContext(api,args)
    frozen=json.loads(CONTRACT.read_text(encoding='utf-8'))
    contract=frozen['apis'][api]
    method=getattr(WebBrowser,api)
    c.case('api_contract','签名、默认值、docstring 和 SDK 源码均匹配只读快照',
        lambda:c.require(str(inspect.signature(method))==contract['signature'] and inspect.getdoc(method)==contract['docstring']
                         and inspect.getsource(method)==contract['source'],contract['signature']))
    extra=(lambda:method(object(),'name','extra')) if api=='remove_cookie' else (lambda:method(object(),'extra'))
    c.case('extra_positional','多余位置参数由 Python TypeError 拒绝，方法体未执行',lambda:c.raises(TypeError,extra))
    c.case('unknown_keyword','未知 keyword 由 Python TypeError 拒绝，方法体未执行',lambda:c.raises(TypeError,lambda:method(object(),unexpected=True)))
    total=None
    if not args.contract_only and all(r['status']=='PASS' for r in c.rows):
        try:
            if c.case('environment','创建后台测试页、读取原生 Cookie Store、记录 Chrome 标签基线',c.setup)=='PASS':
                steps=matrix(c)
                total=3+1+len(steps)+2
                for case,expected,fn in steps:
                    status=c.case(case,expected,fn)
                    if status=='BLOCKED' or (case=='native_fixtures' and status!='PASS'):
                        break
                else:
                    c.case('closed_page','有效参数操作已关闭页面抛 ActionError / 网页对象已失效 / stale_page_reference',c.stale_page)
        finally:
            c.case('cleanup','删除本次 Cookie、原生确认；保留外部 Cookie、关闭自有标签并复核基线',c.cleanup)
    failed=any(r['status']=='FAIL' for r in c.rows)
    blocked=any(r['status']=='BLOCKED' for r in c.rows)
    code=1 if failed else 2 if blocked else 0
    verified=not args.contract_only and total==len(c.rows) and all(r['status']=='PASS' for r in c.rows)
    discrepancies=[]
    if api in {'get_cookies','remove_cookie','clear_cookies'}:
        discrepancies.append('docstring 声称 partition_key 支持网址字符串；当前 SDK 仅接受 Mapping，字符串抛 TypeError。本轮正向分区用例只验证字典。')
    report={'api':'uiautoma.web.WebBrowser.'+api,'lifecycle':'VERIFIED' if verified else 'READY_FOR_LIVE',
        'url':args.target_url,'guard_url':GUARD_URL,'silent_running':True,'oracle':'native CookieStore and document.cookie',
        'product_worktree':str(PRODUCT),'product_commit':subprocess.check_output(['git','-C',str(PRODUCT),'rev-parse','HEAD'],text=True).strip(),
        'contract':contract,'contract_file':str(CONTRACT),'expected_total':total,'results':c.rows,
        'contract_discrepancies':discrepancies,
        'boundaries':['Chrome；第一方 Cookie 分区；不验证跨站祖先为 True 的正向环境。',
            '原生 Cookie Store 不展示 HttpOnly；读取方法的隐藏 Cookie 属性/值未独立验收。',
            'set_cookie 的 HttpOnly 用脚本覆盖保护核验；没有服务端或 CDP 核验隐藏值。'],
        'exit_code':code}
    return report,code


def main(api):
    parser=argparse.ArgumentParser(description='WebBrowser.'+api+' 独立验收')
    parser.add_argument('--target-url',default=URL)
    parser.add_argument('--contract-only',action='store_true')
    parser.add_argument('--json',action='store_true')
    parser.add_argument('--report-file',type=Path)
    args=parser.parse_args()
    if args.target_url!=URL:
        parser.error('本轮合同使用固定 Cookie 靶场；其他域名/Path 需重新准备独立 oracle')
    if not args.json:
        print('UIAutoma Web API 测试\nAPI     : uiautoma.web.WebBrowser.'+api+'\n页面    : '+args.target_url+'\n方式    : 后台 API / JavaScript',flush=True)
    report,code=run(api,args)
    if args.report_file:
        args.report_file.parent.mkdir(parents=True,exist_ok=True)
        args.report_file.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    if args.json:
        print(json.dumps(report,ensure_ascii=False,indent=2))
    else:
        print('进度     状态    测试项                  测试结果')
        colors={'PASS':('\x1b[92m','通过'),'FAIL':('\x1b[91m','失败'),'BLOCKED':('\x1b[93m','阻塞')}
        for i,row in enumerate(report['results'],1):
            color,label=colors[row['status']]
            brief=json.dumps(row['actual'],ensure_ascii=False)
            if len(brief)>850:brief=brief[:847]+'…'
            print(f"{i:02}/{len(report['results']):02} {color}[{label}]\x1b[0m {row['case_id']} 期望 {row['expected']}；实测 {brief}；{row['elapsed_ms']}ms")
        passed=sum(r['status']=='PASS' for r in report['results'])
        print(f"{report['lifecycle']} · {passed}/{len(report['results'])} 通过 · 退出码 {code}")
        for text in report['contract_discrepancies']:print('文档差异：'+text)
    return code
