"""在已发布慢资源靶场验收 WebBrowser.is_load_completed()。

用共享 DOM、原生 Navigation Timing 和图片状态确证加载阶段；
复用 stop_load 靶场的准备与清理，独立断言本 API 的布尔值和异常。
"""
from __future__ import annotations

import argparse
import inspect
import json
import math
from pathlib import Path
import socket
import subprocess
import sys
import time

sys.dont_write_bytecode = True
from test_web_browser_stop_load import (
    ActionError, CLEANUP_BUTTON, LIBRARY, PRODUCT, ROOT, START_BUTTON,
    StopLoadContext, URL, WebBrowser,
)

__test__ = False
API = 'uiautoma.web.WebBrowser.is_load_completed'
TOTAL_CASES = 19
CONTRACT = ROOT / 'web' / 'is_load_completed_contract_20261005.json'
OBSERVE = '''function () {
  const n = performance.getEntriesByType('navigation')[0];
  const log = document.getElementById('event-log');
  const scene = log?.textContent.trim() ? JSON.parse(log.textContent) : null;
  const image = document.getElementById('slow-resource');
  return {url:location.href, timeOrigin:performance.timeOrigin,
    readyState:document.readyState, loadEventEnd:n?.loadEventEnd || 0,
    loadEventStart:n?.loadEventStart || 0, navigationType:n?.type,
    scene, image:image ? {complete:image.complete, naturalWidth:image.naturalWidth, src:image.src} : null};
}'''


class LoadCompletedContext(StopLoadContext):
    def observe(self):
        return self.page.execute_javascript(OBSERVE)

    @staticmethod
    def phase(state):
        scene, image = state['scene'], state['image']
        if scene and scene['resourceStatus'] == 'pending' and not scene['resourceLoaded'] \
                and scene['loadEvents'] == 0 and state['readyState'] == 'interactive' \
                and state['loadEventEnd'] == 0 and image and not image['complete']:
            return 'pending'
        if scene and scene['resourceStatus'] == 'loaded' and scene['resourceLoaded'] \
                and scene['loadEvents'] == 1 and state['readyState'] == 'complete' \
                and state['loadEventEnd'] > 0 and image and image['naturalWidth'] > 0:
            return 'completed'
        return 'transition'

    def sample(self):
        before = self.observe()
        started = time.monotonic()
        value = self.page.is_load_completed()
        call_ms = round((time.monotonic() - started) * 1000, 1)
        after = self.observe()
        self.expect(type(value) is bool, {'value':value, 'type':type(value).__name__})
        left, right = self.phase(before), self.phase(after)
        stable = before['timeOrigin'] == after['timeOrigin'] and left == right
        if stable and left in {'pending', 'completed'}:
            self.expect(value is (left == 'completed'), {'before':before, 'value':value, 'after':after})
        return {'before':before, 'value':value, 'after':after,
                'stable_phase':left if stable else 'transition', 'call_ms':call_ms}

    def prepared_true(self):
        samples = [self.sample() for _ in range(3)]
        for sample in samples:
            self.expect(sample['value'] is True and all(n['readyState'] == 'complete'
                        and n['loadEventEnd'] > 0 for n in (sample['before'], sample['after'])), sample)
        return {'summary':{'values':[s['value'] for s in samples], 'native':'complete / loadEventEnd > 0'},
                'samples':samples}

    def pending_false(self):
        self.pending_first = self.observe()
        deadline, samples = time.monotonic() + self.args.observe_seconds, []
        while True:
            sample = self.sample()
            self.expect(sample['value'] is False and sample['stable_phase'] == 'pending', sample)
            samples.append(sample)
            if time.monotonic() >= deadline:
                break
            time.sleep(.1)
        return {'summary':{'values':sorted(set(s['value'] for s in samples)), 'samples':len(samples),
                           'observe_seconds':self.args.observe_seconds, 'native':'interactive / loadEventEnd = 0'},
                'samples':samples}

    def queries_readonly(self):
        last, first = self.observe(), self.pending_first
        self.expect(first['url'] == last['url'] and first['timeOrigin'] == last['timeOrigin']
                    and first['scene']['runId'] == last['scene']['runId']
                    and first['scene']['events'] == last['scene']['events']
                    and last['scene']['heartbeat'] > first['scene']['heartbeat']
                    and self.phase(last) == 'pending', {'before':first, 'after':last})
        return {'summary':{'same_document':True, 'resource_status':'pending',
                           'heartbeat':f"{first['scene']['heartbeat']}->{last['scene']['heartbeat']}"},
                'before':first, 'after':last}

    def expect_action_error(self, fn, message='网页加载失败', trace='web_page_load_failed'):
        try:
            fn()
        except ActionError as exc:
            detail = {'exception':type(exc).__name__, 'message':str(exc), 'trace':exc.trace_info}
            return self.expect(str(exc) == message and exc.trace_info == trace, detail)
        raise AssertionError('预期 ActionError，实际未抛异常')

    def stopped_error(self):
        stopped = self.stop_pending()  # 仅用于准备本 API 的失败状态。
        samples = []
        for _ in range(3):
            before = self.observe()
            error = self.expect_action_error(self.page.is_load_completed)
            after = self.observe()
            self.expect(all(n['readyState'] == 'complete' and n['loadEventEnd'] == 0
                            and n['scene']['resourceStatus'] == 'error' and n['scene']['loadEvents'] == 0
                            for n in (before, after)), {'before':before, 'after':after})
            samples.append({'before':before, 'error':error, 'after':after})
        return {'summary':{'samples':3, 'error':samples[0]['error'], 'native':'complete / loadEventEnd = 0'},
                'preparation_stop':stopped, 'samples':samples}

    def transition(self, previous=None):
        deadline, samples = time.monotonic() + 15, []
        while time.monotonic() < deadline:
            sample = self.sample()
            samples.append(sample)
            if sample['value'] is True and sample['stable_phase'] == 'completed':
                break
            time.sleep(.1)
        self.expect(any(s['stable_phase'] == 'pending' and s['value'] is False for s in samples)
                    and samples[-1]['stable_phase'] == 'completed' and samples[-1]['value'] is True, samples)
        after, scene = samples[-1]['after'], samples[-1]['after']['scene']
        self.expect(scene['elapsedMs'] >= scene['delayMs']
                    and any(e['type'] == 'worker_response_released' for e in scene['events'])
                    and not any(e['type'] == 'resource_error' for e in scene['events']), after)
        if previous:
            self.expect(after['url'] == previous['url'] and after['timeOrigin'] != previous['timeOrigin']
                        and scene['runId'] == previous['scene']['runId'], {'previous':previous, 'after':after})
        return {'summary':{'values':sorted(set(s['value'] for s in samples)), 'samples':len(samples),
                           'natural_elapsed_ms':scene['elapsedMs'], 'delay_ms':scene['delayMs'],
                           'load_events':scene['loadEvents'], 'image_width':after['image']['naturalWidth'],
                           'new_document':bool(previous)}, 'samples':samples}

    def natural_transition(self):
        before = self.begin(self.args.natural_seconds)
        return {'preparation':before, **self.transition()}

    def completed_true(self):
        samples = [self.sample() for _ in range(3)]
        self.expect(all(s['value'] is True and s['stable_phase'] == 'completed' for s in samples), samples)
        return {'summary':{'values':[s['value'] for s in samples], 'native':'complete / loadEventEnd > 0'},
                'samples':samples}

    def reload_transition(self):
        previous = self.observe()
        returned = self.page.reload(load_timeout=0)
        self.expect(returned is None, returned)
        # 等待新文档建立，随后在慢资源窗口内强制覆盖 False 和 True。
        self.wait(self.observe, lambda n:n['timeOrigin'] != previous['timeOrigin'] and n['scene']
                  and n['scene']['heartbeat'] >= 1 and self.phase(n) == 'pending')
        return {'reload_return':returned, 'previous':previous, **self.transition(previous)}

    def native_error_page(self):
        # 保留一个本次独占、未 listen 的端口，制造连接失败而不启动服务。
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as refused:
            refused.bind(('127.0.0.1', 0))
            target = f'http://127.0.0.1:{refused.getsockname()[1]}/uiautoma-is-load-completed-error.html'
            navigation = self.expect_action_error(lambda:self.page.navigate(target, load_timeout=5))
            native = self.observe()
            self.expect(native['url'] == 'chrome-error://chromewebdata/' and native['readyState'] == 'complete'
                        and native['loadEventEnd'] > 0, native)
            errors = [self.expect_action_error(self.page.is_load_completed) for _ in range(3)]
        return {'summary':{'error':errors[0], 'samples':3, 'native_url':native['url'],
                           'readyState':native['readyState'], 'loadEventEnd':native['loadEventEnd']},
                'target':target, 'navigation_error':navigation, 'native':native, 'errors':errors}

    def recover_error(self):
        returned = self.page.navigate(self.args.target_url, load_timeout=20)
        self.setup_ready()
        return {'navigate_return':returned, **self.prepared_true()}

    def closed_page_error(self):
        page = self.page
        page.close(ignore_beforeunload=True)
        self.page = None
        return self.expect_action_error(page.is_load_completed, '网页对象已失效', 'stale_page_reference')


def run(args):
    c = LoadCompletedContext(args)
    contract = json.loads(CONTRACT.read_text(encoding='utf-8'))
    method = WebBrowser.is_load_completed
    c.case('api_contract', '无参数、返回 bool；签名/docstring/SDK 源码与只读快照一致',
           lambda:c.expect(str(inspect.signature(method)) == contract['signature']
                           and inspect.getdoc(method) == contract['docstring']
                           and inspect.getsource(method) == contract['source'], contract['signature']))

    def rejected(fn):
        try:
            fn()
        except TypeError as exc:
            return {'exception':type(exc).__name__, 'message':str(exc), 'runtime_called':False}
        raise AssertionError('预期 Python TypeError')

    c.case('invalid_positional', '多余位置参数由 Python 抛 TypeError，未连接 Runtime',
           lambda:rejected(lambda:method(object(), 1)))
    c.case('invalid_keyword', '未知 timeout 参数由 Python 抛 TypeError，未连接 Runtime',
           lambda:rejected(lambda:method(object(), timeout=1)))
    if not args.contract_only and all(r['status'] == 'PASS' for r in c.rows):
        if c.case('library_targets', '元素库包含两个唯一 Web 按钮', c.library_targets) == 'PASS':
            try:
                if c.case('environment', '连接 dev Runtime，创建本次页面/临时库并记录标签基线', c.setup) == 'PASS':
                    for name, expected, fn in [
                        ('fixture_setup', '靶场已准备；两个库元素映射正确；默认慢资源 30 秒', c.fixture_setup),
                        ('prepared_true', '原生 complete 且 loadEventEnd > 0，连续三次返回 True', c.prepared_true),
                        ('start_long_loading', '点击库开始按钮；30 秒资源 pending，文档 interactive', c.start_long),
                        ('pending_false', '持续观察慢资源；每次调用前后仍 pending，返回 bool False', c.pending_false),
                        ('queries_readonly', '查询保留文档/run/资源事件，资源等待且 JS 心跳增长', c.queries_readonly),
                        ('stopped_loading_error', '资源中止后虽 complete，三次均抛网页加载失败 / web_page_load_failed', c.stopped_error),
                        ('natural_transition', '重新开始；原生状态确认等待到自然完成，API 从 False 转 True', c.natural_transition),
                        ('completed_true', '图片成功且 load 一次、loadEventEnd > 0；连续三次 True', c.completed_true),
                        ('reload_transition', '零等待刷新建立新文档；慢资源期间 False，自然完成后 True', c.reload_transition),
                        ('native_error_page', '连接拒绝进入 Chrome 原生错误页；三次抛网页加载失败', c.native_error_page),
                        ('recover_error_true', '错误后导航回准备页；原生加载完成且连续三次 True', c.recover_error),
                        ('cleanup_worker_button', '点击库清理按钮；只注销本目录注册，原有注册按基线恢复', c.cleanup_worker),
                        ('closed_page_error', '关闭页面后抛网页对象已失效 / stale_page_reference', c.closed_page_error),
                    ]:
                        if not args.json:
                            print('正在测试：'+name+'…', flush=True)
                        if c.case(name, expected, fn) != 'PASS':
                            break
            finally:
                c.case('cleanup', '关闭本次标签/库、删除临时副本并复核原有标签基线', c.cleanup)
    failed = any(r['status'] == 'FAIL' for r in c.rows)
    blocked = any(r['status'] == 'BLOCKED' for r in c.rows)
    code = 1 if failed else 2 if blocked else 0
    verified = not args.contract_only and len(c.rows) == TOTAL_CASES and all(r['status'] == 'PASS' for r in c.rows)
    report = {'api':API, 'lifecycle':'VERIFIED' if verified else 'READY_FOR_LIVE',
              'url':args.target_url, 'element_library':str(args.element_library),
              'product_worktree':str(PRODUCT),
              'product_commit':subprocess.check_output(['git','-C',str(PRODUCT),'rev-parse','HEAD'], text=True).strip(),
              'contract_file':str(CONTRACT), 'contract':contract, 'results':c.rows,
              'preparation_recovery':c.preparation_recovery, 'exit_code':code}
    return report, code


def main():
    parser = argparse.ArgumentParser(description=API+'：真实加载状态与错误验收')
    parser.add_argument('--target-url', default=URL)
    parser.add_argument('--element-library', type=Path, default=LIBRARY)
    parser.add_argument('--start-button', default=START_BUTTON)
    parser.add_argument('--cleanup-button', default=CLEANUP_BUTTON)
    parser.add_argument('--wait-timeout', type=float, default=12)
    parser.add_argument('--observe-seconds', type=float, default=2)
    parser.add_argument('--natural-seconds', type=int, default=3)
    parser.add_argument('--contract-only', action='store_true')
    parser.add_argument('--json', action='store_true')
    parser.add_argument('--report-file', type=Path)
    args = parser.parse_args()
    if not math.isfinite(args.wait_timeout) or args.wait_timeout <= 0 \
            or not math.isfinite(args.observe_seconds) or not 1 <= args.observe_seconds <= 10 \
            or not 2 <= args.natural_seconds <= 10:
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
        print('进度     状态    测试项                  测试结果')
        labels = {'PASS':('\x1b[92m','通过'), 'FAIL':('\x1b[91m','失败'), 'BLOCKED':('\x1b[93m','阻塞')}
        for index, row in enumerate(report['results'], 1):
            color, label = labels[row['status']]
            actual = row['actual']
            if isinstance(actual, dict):
                actual = actual.get('summary', actual)
            brief = json.dumps(actual, ensure_ascii=False)
            if len(brief) > 700:
                brief = brief[:697]+'…'
            print(f"{index:02}/{len(report['results']):02} {color}[{label}]\x1b[0m {row['case_id']} 期望 {row['expected']}；实测 {brief}；{row['elapsed_ms']}ms")
        passed = sum(r['status'] == 'PASS' for r in report['results'])
        print(f"{report['lifecycle']} · {passed}/{len(report['results'])} 通过 · 退出码 {code}")
    return code


if __name__ == '__main__':
    raise SystemExit(main())
