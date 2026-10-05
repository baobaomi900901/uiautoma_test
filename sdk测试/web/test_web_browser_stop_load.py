"""使用已发布靶场与用户库元素验收 WebBrowser.stop_load()。

自然完成作为对照，随后中止 30 秒慢资源；读取共享 DOM、浏览器原生
图片状态及 Resource Timing 作为确证。只操作本次标签与临时元素库。
"""
from __future__ import annotations

import argparse
import inspect
import json
import math
from pathlib import Path
import shutil
import subprocess
import sys
import time
from urllib.parse import parse_qsl, urljoin, urlsplit
import uuid

sys.dont_write_bytecode = True
from _web_remaining_common import (
    ActionError, CONTRACT_FILE, HostUnavailableError, LIBRARY, PRODUCT, ROOT,
    WebBrowser, copy_library, open_package, web,
)

__test__ = False
API = 'uiautoma.web.WebBrowser.stop_load'
URL = 'https://baobaomi900901.github.io/xpath/stop-load-test/index.html'
START_BUTTON = 'web靶场_停止加载测试_开始测试_按钮'
CLEANUP_BUTTON = 'web靶场_停止加载测试_清理测试环境_按钮'
TOTAL_CASES = 18

# SDK 脚本执行于隔离世界；页面发布在 DOM 的快照可跨世界读取。
SNAPSHOT = '''function () {
  const log = document.getElementById('event-log');
  if (!log?.textContent.trim()) return null;
  const state = JSON.parse(log.textContent);
  const image = document.getElementById('slow-resource');
  return {...state, actualReadyState: document.readyState, url: location.href,
    image: image ? {complete:image.complete, naturalWidth:image.naturalWidth, src:image.src} : null,
    resourceTiming: performance.getEntriesByType('resource')
      .filter(e => e.name === image?.src).map(e => ({url:e.name, startTime:e.startTime,
        responseEnd:e.responseEnd, decodedBodySize:e.decodedBodySize, transferSize:e.transferSize}))};
}'''
SETUP = '''function () { return {url:location.href, readyState:document.readyState,
  state:document.getElementById('setup-state')?.dataset.state,
  error:document.getElementById('setup-error')?.textContent,
  controller:navigator.serviceWorker.controller?.scriptURL,
  delay:document.getElementById('delay-seconds')?.value}; }'''
REGISTRATIONS = '''function () { return navigator.serviceWorker.getRegistrations()
  .then(items=>items.map(r=>({scope:r.scope, activeState:r.active?.state,
    scriptURL:r.active?.scriptURL || r.waiting?.scriptURL || r.installing?.scriptURL}))); }'''


class MissingScene(Exception):
    pass


class StopLoadContext:
    def __init__(self, args):
        self.args = args
        self.rows = []
        self.page = self.package = None
        self.baseline = None
        self.owned_ids = set()
        self.tmp = ROOT / '.pytest_tmp' / 'stop_load' / uuid.uuid4().hex
        self.scope = urljoin(args.target_url, './')
        self.worker = urljoin(args.target_url, './sw.js')
        self.baseline_registration = None
        self.worker_cleaned = False
        self.preparation_recovery = []

    def expect(self, condition, actual):
        if not condition:
            raise AssertionError(repr(actual))
        return actual

    def case(self, name, expected, fn):
        started = time.perf_counter()
        try:
            actual, status = fn(), 'PASS'
        except (MissingScene, HostUnavailableError) as exc:
            status, actual = 'BLOCKED', {'reason':str(exc), 'exception':type(exc).__name__}
        except Exception as exc:
            status = 'BLOCKED' if getattr(exc, 'trace_info', '') in {
                'plugin_not_connected', 'native_host_unavailable', 'uiautomation_provider_unavailable',
                'web_bridge_unavailable', 'web_environment_ambiguous',
            } else 'FAIL'
            actual = {'exception':type(exc).__name__, 'message':str(exc), 'trace':getattr(exc, 'trace_info', '')}
        self.rows.append({'case_id':name, 'status':status, 'expected':expected,
                          'actual':actual, 'elapsed_ms':round((time.perf_counter()-started)*1000, 1)})
        return status

    def wait(self, read, predicate, timeout=None):
        deadline = time.monotonic() + (timeout or self.args.wait_timeout)
        last = None
        while time.monotonic() < deadline:
            last = read()
            if predicate(last):
                return last
            time.sleep(.1)
        raise AssertionError(f'等待状态未收敛：{last!r}')

    def setup_ready(self, recover=True):
        deadline = time.monotonic() + self.args.wait_timeout
        last = None
        while time.monotonic() < deadline:
            last = self.page.execute_javascript(SETUP)
            if last.get('state') == 'error':
                registrations = self.registrations()
                active = any(r['scope'] == self.scope and r.get('activeState') == 'activated'
                             and r.get('scriptURL') == self.worker for r in registrations)
                # 注册已激活但本次文档尚未被控制：再导航一次，让新文档被 active worker 接管。
                # 这是靶场准备；不重试被测 stop_load，也不允许其他初始化错误被吞掉。
                if recover and active and not last.get('controller') and last.get('error') == '测试环境准备超时，请重新打开准备页。':
                    returned = self.page.navigate(self.args.target_url, load_timeout=20)
                    after = self.setup_ready(recover=False)
                    self.preparation_recovery.append({'before':last, 'registrations':registrations,
                                                      'navigate_return':returned, 'after':after})
                    return after
                raise MissingScene('靶场准备失败：' + repr(last))
            if last.get('state') == 'ready' and last.get('controller') == self.worker:
                return last
            time.sleep(.1)
        raise MissingScene('靶场未准备完成：' + repr(last))

    def snapshot(self):
        return self.page.execute_javascript(SNAPSHOT)

    def registrations(self):
        return self.page.execute_javascript(REGISTRATIONS)

    def library_targets(self):
        catalog = self.args.element_library / 'elements.json'
        if not catalog.is_file():
            raise MissingScene(f'元素库不存在：{catalog}')
        pending, matches = [json.loads(catalog.read_text(encoding='utf-8-sig'))], {}
        while pending:
            value = pending.pop()
            if isinstance(value, dict):
                if value.get('type') == 'web' and value.get('name') in (self.args.start_button, self.args.cleanup_button):
                    matches.setdefault(value['name'], []).append(value.get('id'))
                pending.extend(value.values())
            elif isinstance(value, list):
                pending.extend(value)
        for name in (self.args.start_button, self.args.cleanup_button):
            if len(matches.get(name, [])) != 1:
                raise MissingScene(f'库中 Web 元素必须唯一：{name}，实测 {matches.get(name, [])}')
        return matches

    def setup(self):
        pages = web.get_all(mode='chrome')
        self.baseline = {p._page_ref['id'] for p in pages}
        for existing in pages:
            if (existing.url or '').startswith(self.scope):
                registrations = existing.execute_javascript(REGISTRATIONS)
                self.baseline_registration = next((r for r in registrations if r['scope'] == self.scope), None)
                break
        copy_library(self.args.element_library, self.tmp / 'library')
        self.package = open_package(str(self.tmp / 'library'), timeout=8, connect_timeout=8)
        self.page = web.create(self.args.target_url, mode='chrome', load_timeout=25, silent_running=False)
        self.owned_ids.add(self.page._page_ref['id'])
        return {'url':self.page.get_url(), 'baseline_tabs':len(self.baseline),
                'library':str(self.args.element_library), 'temporary_library':str(self.tmp/'library'),
                'baseline_registration':self.baseline_registration}

    def fixture_setup(self):
        ready = self.setup_ready()
        registrations = self.registrations()
        mappings = {}
        for name, expected_id in ((self.args.start_button, 'start-test'), (self.args.cleanup_button, 'cleanup-worker')):
            element = self.page.find(name, timeout=4)
            mapping = element.execute_javascript('function(e){return {id:e.id,tag:e.tagName,disabled:e.disabled}}')
            self.expect(mapping == {'id':expected_id, 'tag':'BUTTON', 'disabled':False}, mapping)
            mappings[name] = mapping
        self.expect(ready['delay'] == '30' and ready['readyState'] == 'complete', ready)
        return {'setup':ready, 'mappings':mappings, 'registrations':registrations,
                'preparation_recovery':list(self.preparation_recovery)}

    def stop_prepared(self):
        before = self.page.execute_javascript(SETUP)
        returned = self.page.stop_load()
        after = self.page.execute_javascript(SETUP)
        return self.expect(returned is None and before == after,
                           {'return':returned, 'before':before, 'after':after})

    def begin(self, seconds):
        if not self.page.get_url().startswith(urljoin(self.args.target_url, './index.html')):
            self.page.navigate(self.args.target_url, load_timeout=20)
        self.setup_ready()
        self.page.execute_javascript('function(_e,seconds){document.getElementById("delay-seconds").value=String(seconds)}', seconds)
        self.page.find(self.args.start_button, timeout=4).click(simulative=False, delay_after=.1)
        state = self.wait(self.snapshot, lambda x:x and x['heartbeat'] >= 2)
        self.expect(state['controlled'] and state['delayMs'] == seconds*1000 and state['version'] == 1, state)
        self.expect(state['actualReadyState'] == 'interactive' and state['resourceStatus'] == 'pending'
                    and not state['resourceLoaded'] and state['loadEvents'] == 0
                    and any(e['type'] == 'worker_request_started' for e in state['events']), state)
        self.expect(state['runId'] == dict(parse_qsl(urlsplit(state['url']).query)).get('run'), state)
        return state

    def natural_control(self):
        before = self.begin(self.args.natural_seconds)
        after = self.wait(self.snapshot, lambda x:x and x['resourceLoaded'] and x['loadEvents'] == 1
                          and x['actualReadyState'] == 'complete', timeout=15)
        self.expect(after['runId'] == before['runId'] and after['resourceStatus'] == 'loaded'
                    and after['elapsedMs'] >= after['delayMs'] and after['image']['naturalWidth'] > 0
                    and any(e['type'] == 'worker_response_released' for e in after['events'])
                    and not any(e['type'] == 'resource_error' for e in after['events']), after)
        return {'before':before, 'after':after}

    def stop_completed(self):
        before = self.snapshot()
        returned = self.page.stop_load()
        after = self.snapshot()
        return self.expect(returned is None and after['resourceLoaded'] and after['loadEvents'] == 1
                           and after['runId'] == before['runId'] and after['events'] == before['events'],
                           {'return':returned, 'after':after})

    def start_long(self):
        return self.begin(30)

    def control_without_stop(self):
        first = self.snapshot()
        deadline, samples = time.monotonic() + self.args.observe_seconds, 0
        while True:
            state = self.snapshot()
            self.expect(state['runId'] == first['runId'] and state['actualReadyState'] == 'interactive'
                        and state['resourceStatus'] == 'pending' and not state['resourceTiming']
                        and not state['resourceLoaded'] and state['loadEvents'] == 0, state)
            samples += 1
            if time.monotonic() >= deadline:
                break
            time.sleep(.1)
        self.expect(state['heartbeat'] > first['heartbeat'], {'first':first, 'last':state})
        return {'before':first, 'after':state, 'samples':samples}

    def stop_pending(self):
        before = self.snapshot()
        if before['resourceStatus'] != 'pending' or before['delayMs'] - before['elapsedMs'] < 4000:
            raise MissingScene('停载前未保留足够等待窗口：' + repr(before))
        started = time.monotonic()
        returned = self.page.stop_load()
        call_ms = round((time.monotonic()-started)*1000, 1)
        after = self.wait(self.snapshot, lambda x:x and x['actualReadyState'] == 'complete'
                          and x['resourceStatus'] == 'error' and x['resourceTiming'], timeout=5)
        elapsed_ms = round((time.monotonic()-started)*1000, 1)
        errors = [e for e in after['events'] if e['type'] == 'resource_error']
        self.expect(returned is None and after['runId'] == before['runId']
                    and not after['resourceLoaded'] and after['image']['complete']
                    and after['image']['naturalWidth'] == 0 and len(errors) == 1
                    and errors[0]['atMs'] < after['delayMs'] and after['elapsedMs'] < after['delayMs']
                    and not any(e['type'] == 'worker_response_released' for e in after['events'])
                    and all(e['decodedBodySize'] == 0 and e['responseEnd'] > 0 for e in after['resourceTiming']), after)
        return {'return':returned, 'call_ms':call_ms, 'completion_ms':elapsed_ms, 'before':before, 'after':after}

    def js_after_stop(self):
        first = self.snapshot()
        last = self.wait(self.snapshot, lambda x:x['heartbeat'] > first['heartbeat'])
        return self.expect(last['actualReadyState'] == 'complete' and last['runId'] == first['runId']
                           and not last['resourceLoaded'], {'before':first, 'after':last})

    def repeated_stop(self):
        before = self.snapshot()
        returned = [self.page.stop_load(), self.page.stop_load()]
        after = self.snapshot()
        return self.expect(returned == [None, None] and before['events'] == after['events']
                           and before['runId'] == after['runId'] and after['actualReadyState'] == 'complete',
                           {'returns':returned, 'after':after})

    def restart_stop(self):
        previous_run = self.snapshot()['runId']
        restarted = self.begin(6)
        self.expect(restarted['runId'] != previous_run, restarted)
        return {'previous_run':previous_run, 'new_loading':restarted, 'stop':self.stop_pending()}

    def cleanup_worker(self):
        self.page.navigate(self.args.target_url, load_timeout=20)
        self.setup_ready()
        before = self.registrations()
        returned = self.page.find(self.args.cleanup_button, timeout=4).click(simulative=False, delay_after=.1)
        state = self.wait(lambda:self.page.execute_javascript(SETUP), lambda x:x['state'] == 'removed')
        after = self.registrations()
        self.expect(returned is None and not any(r['scope'] == self.scope for r in after)
                    and {r['scope'] for r in after} == {r['scope'] for r in before if r['scope'] != self.scope}, after)
        restored = False
        if self.baseline_registration:
            self.page.execute_javascript('''function(_e,r){return navigator.serviceWorker.register(r.scriptURL,
              {scope:r.scope,updateViaCache:'none'}).then(()=>true)}''', self.baseline_registration)
            restored = any(r['scope'] == self.scope for r in self.registrations())
            self.expect(restored, self.registrations())
        self.worker_cleaned = True
        return {'click_return':returned, 'state':state, 'before':before, 'after':after,
                'baseline_registration_restored':restored}

    def closed_page_error(self):
        page = self.page
        page.close(ignore_beforeunload=True)
        self.page = None
        try:
            page.stop_load()
        except ActionError as exc:
            actual = {'exception':type(exc).__name__, 'message':str(exc), 'trace':exc.trace_info}
            return self.expect(str(exc) == '网页对象已失效' and exc.trace_info == 'stale_page_reference', actual)
        raise AssertionError('关闭页面后 stop_load 未抛 ActionError')

    def cleanup(self):
        errors = []
        if self.page is not None:
            if not self.worker_cleaned:
                try:
                    self.cleanup_worker()
                except Exception as exc:
                    errors.append('worker: ' + str(exc))
            try:
                self.page.close(ignore_beforeunload=True)
            except Exception as exc:
                errors.append('page: ' + str(exc))
            self.page = None
        if self.package is not None:
            try:
                self.package.close()
            except Exception as exc:
                errors.append('library: ' + str(exc))
        if self.tmp.exists():
            if self.tmp.resolve().parent != (ROOT/'.pytest_tmp'/'stop_load').resolve():
                errors.append('临时目录超出预期边界')
            else:
                shutil.rmtree(self.tmp)
        if self.baseline is None:
            return self.expect(not errors, {'errors':errors, 'resources_created':False})
        after = {p._page_ref['id'] for p in web.get_all(mode='chrome')}
        detail = {'errors':errors, 'own_tabs_closed':not (self.owned_ids & after),
                  'temporary_copy_removed':not self.tmp.exists(), 'worker_cleaned':self.worker_cleaned,
                  'tab_count':f'{len(self.baseline)}->{len(after)}',
                  'external_added':sorted(after-self.baseline), 'external_removed':sorted(self.baseline-after)}
        self.expect(not errors and detail['own_tabs_closed'] and detail['temporary_copy_removed'], detail)
        if after != self.baseline:
            raise MissingScene('测试期间外部标签发生变化：' + repr(detail))
        return detail


def run(args):
    options = argparse.Namespace(**{key:getattr(args,key,default) for key,default in {
        'target_url':URL, 'element_library':LIBRARY, 'start_button':START_BUTTON,
        'cleanup_button':CLEANUP_BUTTON, 'contract_only':False, 'wait_timeout':12,
        'observe_seconds':1, 'natural_seconds':2, 'json':True,
    }.items()})
    options.element_library = Path(options.element_library)
    c = StopLoadContext(options)
    contract = json.loads(CONTRACT_FILE.read_text(encoding='utf-8'))['apis']['browser.stop_load']
    c.case('api_contract', '签名、docstring 与入口源码均匹配只读快照；返回 None',
           lambda:c.expect(str(inspect.signature(WebBrowser.stop_load)) == contract['signature']
                           and inspect.getdoc(WebBrowser.stop_load) == contract['docstring']
                           and inspect.getsource(WebBrowser.stop_load) == contract['source'], contract['signature']))
    def rejected(fn):
        try:
            fn()
        except TypeError as exc:
            return {'exception':type(exc).__name__, 'message':str(exc), 'runtime_called':False}
        raise AssertionError('预期 Python TypeError')
    c.case('invalid_positional', '多余位置参数由 Python 抛 TypeError，未连接 Runtime',
           lambda:rejected(lambda:WebBrowser.stop_load(object(), 1)))
    c.case('invalid_keyword', '不存在的 timeout 参数由 Python 抛 TypeError，未连接 Runtime',
           lambda:rejected(lambda:WebBrowser.stop_load(object(), timeout=1)))
    if not options.contract_only and c.case('library_targets', '元素库包含两个唯一 Web 按钮', c.library_targets) == 'PASS':
        try:
            if c.case('environment', '连接 dev Runtime，创建本次页面与临时库，记录标签基线', c.setup) == 'PASS':
                for name, expected, fn in [
                    ('fixture_setup', '靶场准备成功；两个库元素映射到正确按钮；默认 30 秒', c.fixture_setup),
                    ('stop_prepared_page', '准备页已完成时停载返回 None，不改变页面', c.stop_prepared),
                    ('natural_control', '不调用停载，2 秒资源自然完成、图片有宽度且一次 load', c.natural_control),
                    ('stop_completed_resource', '资源自然完成后停载返回 None，已加载图片与事件保留', c.stop_completed),
                    ('start_long_loading', '点击库开始按钮，30 秒资源 pending，文档 interactive，JS 正常', c.start_long),
                    ('control_without_stop', '未调用停载的观察期内资源保持 pending，心跳增长', c.control_without_stop),
                    ('stop_pending_resource', '停载返回 None；延迟到期前文档结束、图片未完成，资源错误与空响应计时相符', c.stop_pending),
                    ('javascript_after_stop', '停载后 JS 心跳仍增长，文档保持 complete', c.js_after_stop),
                    ('repeated_stop', '中止后再次调用两次均返回 None，不产生新资源事件', c.repeated_stop),
                    ('restart_and_stop', '原页面可再次开始；新 run 的 6 秒资源也被成功中止', c.restart_stop),
                    ('cleanup_worker_button', '点击库清理按钮，仅注销本目录注册；原有注册按基线恢复', c.cleanup_worker),
                    ('closed_page_error', '页面关闭后抛 ActionError：网页对象已失效 / stale_page_reference', c.closed_page_error),
                ]:
                    if not options.json and name in {'natural_control','start_long_loading','stop_pending_resource','restart_and_stop'}:
                        print('正在测试：' + name + '…', flush=True)
                    if c.case(name, expected, fn) != 'PASS':
                        break
        finally:
            c.case('cleanup', '关闭本次页面/库、清除临时目录，复核标签基线', c.cleanup)
    failed = any(row['status'] == 'FAIL' for row in c.rows)
    blocked = any(row['status'] == 'BLOCKED' for row in c.rows)
    code = 1 if failed else 2 if blocked else 0
    verified = not options.contract_only and len(c.rows) == TOTAL_CASES and all(row['status'] == 'PASS' for row in c.rows)
    report = {'api':API, 'lifecycle':'VERIFIED' if verified else 'READY_FOR_LIVE',
              'url':options.target_url, 'element_library':str(options.element_library),
              'start_button':options.start_button, 'cleanup_button':options.cleanup_button,
              'product_worktree':str(PRODUCT),
              'product_commit':subprocess.check_output(['git','-C',str(PRODUCT),'rev-parse','HEAD'], text=True).strip(),
              'contract':contract, 'preparation_recovery':c.preparation_recovery, 'results':c.rows, 'exit_code':code}
    return report, code


def main():
    parser = argparse.ArgumentParser(description=API+'：真实资源停载验收')
    parser.add_argument('--target-url', default=URL)
    parser.add_argument('--element-library', type=Path, default=LIBRARY)
    parser.add_argument('--start-button', default=START_BUTTON)
    parser.add_argument('--cleanup-button', default=CLEANUP_BUTTON)
    parser.add_argument('--wait-timeout', type=float, default=12)
    parser.add_argument('--observe-seconds', type=float, default=1)
    parser.add_argument('--natural-seconds', type=int, default=2)
    parser.add_argument('--contract-only', action='store_true')
    parser.add_argument('--json', action='store_true')
    parser.add_argument('--report-file', type=Path)
    args = parser.parse_args()
    if not math.isfinite(args.wait_timeout) or args.wait_timeout <= 0 or not math.isfinite(args.observe_seconds) or not 1 <= args.observe_seconds <= 10 or not 2 <= args.natural_seconds <= 10:
        parser.error('等待时间须为有限正数；观察时间为 1–10 秒，自然对照为 2–10 秒整数')
    if not args.json:
        print('UIAutoma Web API 测试\nAPI     : '+API+'\n页面    : '+args.target_url, flush=True)
    report, code = run(args)
    if args.report_file:
        args.report_file.parent.mkdir(parents=True, exist_ok=True)
        args.report_file.write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        labels = {'PASS':('\x1b[92m','通过'), 'FAIL':('\x1b[91m','失败'), 'BLOCKED':('\x1b[93m','阻塞')}
        for index, row in enumerate(report['results'], 1):
            color, label = labels[row['status']]
            print(f"{index:02}/{len(report['results']):02} {color}[{label}]\x1b[0m {row['case_id']} 期望 {row['expected']}；实测 {row['actual']}；{row['elapsed_ms']}ms")
        passed = sum(row['status'] == 'PASS' for row in report['results'])
        print(f"{report['lifecycle']} · {passed}/{len(report['results'])} 通过 · 退出码 {code}")
    return code


if __name__ == '__main__':
    raise SystemExit(main())
