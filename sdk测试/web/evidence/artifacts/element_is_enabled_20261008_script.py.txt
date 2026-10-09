"""WebElement.is_enabled 后台验收；真实库按钮与独立浏览器状态参考。

只在自有静默标签中临时切换现有按钮属性，每项恢复，最终关闭资源。
不点击、不激活窗口、不发送键鼠输入。HTML disabled 按属性存在与 IDL 判断；
aria-disabled 按 ARIA true/false 判断。退出码 0 全通过、1 失败、2 环境阻塞。
--contract-only 不连接 Runtime。
"""
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
ROOT = Path(__file__).resolve().parents[1]
PRODUCT = Path(r'D:\code\desktop')
sys.path[:0] = [str(PRODUCT/'sdk/src'), str(ROOT/'web')]
from uiautoma import web, open as open_package, ping, ActionError, HostUnavailableError
from uiautoma.web import WebElement
from test_web_element_get_select_options import copy_library

URL = 'https://baobaomi900901.github.io/xpath/#/keys-click-test'
LIBRARY = Path(r'D:\code\元素库\260902_web元素')
CONTRACT = ROOT/'web/element_is_enabled_contract_20261008.json'
TARGETS = (
    ('disabled_button', 'web靶场_disabled_按钮', 'btn-disabled-click-target', False),
    ('click_button', 'web靶场_测试点击_单击触发', 'btn-click-target', True),
)
ATTRIBUTE_VALUES = ('', 'disabled', 'true', 'false', 'False')


class Blocked(Exception):
    pass


class Failure(AssertionError):
    def __init__(self, detail):
        self.detail = detail
        super().__init__(json.dumps(detail, ensure_ascii=False, default=str))


def require(ok, detail):
    if not ok:
        raise Failure(detail)
    return detail


def error(exc):
    return {'exception': type(exc).__name__, 'message': str(exc), 'trace': getattr(exc, 'trace_info', '')}


def raises(kind, fn, message='', trace=''):
    try:
        fn()
    except kind as exc:
        detail = error(exc)
        return require((not message or message in str(exc)) and (not trace or detail['trace'] == trace), detail)
    raise Failure({'expected_exception': kind.__name__, 'actual': 'returned normally'})


def contract():
    frozen = json.loads(CONTRACT.read_text(encoding='utf-8'))
    signature = inspect.signature(WebElement.is_enabled)
    require(tuple(signature.parameters) == ('self',) and str(signature.return_annotation) == 'bool', str(signature))
    require(str(signature) == frozen['signature'] and inspect.getsource(WebElement.is_enabled) == frozen['source'], 'SDK method changed; review frozen contract')
    commit = subprocess.check_output(['git', '-C', str(PRODUCT), 'rev-parse', 'HEAD'], text=True).strip()
    require(commit == frozen['commit'], {'expected_commit': frozen['commit'], 'actual_commit': commit})
    for snapshot in frozen['source_snapshots']:
        path = Path(snapshot['worktree'])/snapshot['path']
        require(hashlib.sha256(path.read_bytes()).hexdigest() == snapshot['sha256'], {'changed_source': str(path)})
    return {'signature': str(signature), 'worktree': str(PRODUCT), 'commit': commit, 'rpc': frozen['rpc'], 'timeout_ms': frozen['timeout_ms'], 'source_sections': len(frozen['source_snapshots'])}


class ValidationRaw:
    calls = 0

    def is_enabled(self):
        self.calls += 1
        raise AssertionError('Argument validation must precede raw delegation')


class Run:
    def __init__(self, args):
        self.args, self.rows, self.elements = args, [], {}
        self.page = self.package = self.baseline = self.page_id = self.library_hash = self.original = None
        self.ready = False
        self.total = 3 if args.contract_only else 32
        self.tmp = ROOT/'.pytest_tmp/is_enabled_live'/uuid.uuid4().hex
        self.targets = ((TARGETS[0][0], args.disabled_element, *TARGETS[0][2:]),
                        (TARGETS[1][0], args.enabled_element, *TARGETS[1][2:]))

    def case(self, name, expected, fn, live=False):
        start = time.perf_counter()
        try:
            if live and not self.ready:
                raise Blocked('环境准备未通过，未执行本用例')
            actual, status = fn(), 'PASS'
        except Failure as exc:
            actual, status = exc.detail, 'FAIL'
        except Exception as exc:
            actual = error(exc)
            status = 'BLOCKED' if isinstance(exc, (Blocked, HostUnavailableError, ConnectionError)) else 'FAIL'
        row = {'case_id': name, 'status': status, 'expected': expected, 'actual': actual, 'elapsed_ms': round((time.perf_counter()-start)*1000, 1)}
        self.rows.append(row)
        display = actual
        if isinstance(actual, dict) and 'dom_before' in actual:
            keys = ('name', 'id', 'disabled_attribute', 'dom_disabled', 'pseudo_disabled', 'aria_disabled', 'expected_is_enabled', 'actual_is_enabled', 'return_type', 'readonly', 'values', 'attributes_focus_scroll_events_unchanged')
            display = {key: actual[key] for key in keys if key in actual}
        color, label = {'PASS': ('\x1b[32m', '通过'), 'FAIL': ('\x1b[31m', '失败'), 'BLOCKED': ('\x1b[33m', '阻塞')}[status]
        print(f"{len(self.rows):02d}/{self.total:02d} {color}[{label}]\x1b[0m {name} 期望 {expected}；实测 {json.dumps(display, ensure_ascii=False, default=str)}；{row['elapsed_ms']}ms", flush=True)
        return status

    def js(self, body, arg=None):
        return self.page.execute_javascript('function(_e,a){'+body+'}', arg)

    def snapshot(self):
        return self.js("""
          const pick=id=>{const e=document.getElementById(id);return e?{id:e.id,tag:e.tagName,
            attributes:[...e.attributes].map(x=>[x.name,x.value]).sort((a,b)=>a[0].localeCompare(b[0])),
            disabled:e.disabled,pseudo_disabled:e.matches(':disabled'),disabled_attribute:e.getAttribute('disabled'),
            aria_disabled:e.getAttribute('aria-disabled'),text:e.textContent}:null;};
          return {buttons:['btn-disabled-click-target','btn-click-target'].map(pick),
            focus:document.activeElement?.id||'',scroll:[scrollX,scrollY],events:{...window.__isEnabledObserve.counts}};
        """)

    def setup(self):
        ping(timeout=5)
        if not self.args.library.is_dir():
            raise Blocked('元素库目录不存在：'+str(self.args.library))
        self.library_hash = hashlib.sha256((self.args.library/'elements.json').read_bytes()).hexdigest()
        self.baseline = {p._page_ref['id'] for p in web.get_all(mode='chrome')}
        copy_library(self.args.library, self.tmp/'library')
        self.package = open_package(str(self.tmp/'library'), timeout=8, connect_timeout=8)
        self.page = web.create(self.args.url, mode='chrome', silent_running=True, load_timeout=25)
        self.page_id = self.page._page_ref['id']
        self.js("""
          const counts={click:0,input:0,change:0,keydown:0};const listener=e=>{counts[e.type]++;};
          for(const k of Object.keys(counts))document.addEventListener(k,listener,true);
          window.__isEnabledObserve={counts,listener};return true;
        """)
        self.original = self.snapshot()
        require(all(x and x['tag'] == 'BUTTON' for x in self.original['buttons']), self.original)
        require(self.page.get_url() == self.args.url, {'actual_url': self.page.get_url()})
        self.ready = True
        return {'url': self.page.get_url(), 'library': str(self.args.library), 'silent_running': True, 'baseline_tabs': len(self.baseline), 'original_states': self.original['buttons']}

    def restore(self):
        if self.original:
            self.js("""
              for(const row of a.buttons){const e=document.getElementById(row.id);
                for(const x of [...e.attributes])e.removeAttribute(x.name);
                for(const [k,v] of row.attributes)e.setAttribute(k,v);}return true;
            """, self.original)

    def mapping(self, key, name, id):
        matches = self.page.find_all(name, timeout=5)
        detail = {'name': name, 'matches': len(matches), 'ids': [e.get_attribute('id') for e in matches]}
        require(detail['ids'] == [id], detail)
        self.elements[key] = matches[0]
        return detail

    def element(self, key):
        if key not in self.elements:
            raise Blocked('库元素未唯一定位：'+key)
        return self.elements[key]

    def dom(self, id):
        return next(x for x in self.snapshot()['buttons'] if x['id'] == id)

    def read(self, key, name, id, expected):
        before = self.snapshot()
        dom = next(x for x in before['buttons'] if x['id'] == id)
        require(type(dom['disabled']) is bool and dom['disabled'] == dom['pseudo_disabled'], {'oracle_disagrees': dom})
        value = self.element(key).is_enabled()
        after = self.snapshot()
        detail = {'name': name, 'id': id, 'disabled_attribute': dom['disabled_attribute'], 'dom_disabled': dom['disabled'], 'pseudo_disabled': dom['pseudo_disabled'], 'aria_disabled': dom['aria_disabled'], 'expected_is_enabled': expected, 'actual_is_enabled': value, 'return_type': type(value).__name__, 'readonly': before == after, 'dom_before': before, 'dom_after': after}
        return require(type(value) is bool and value is expected and before == after, detail)

    def baseline_state(self, key, name, id, expected):
        self.restore()
        return self.read(key, name, id, expected)

    def attribute(self, key, name, id, value):
        self.restore()
        try:
            self.js("const e=document.getElementById(a.id);e.removeAttribute('aria-disabled');e.setAttribute('disabled',a.value);return true;", {'id': id, 'value': value})
            dom = self.dom(id)
            require(dom['disabled_attribute'] == value and dom['disabled'] is True and dom['pseudo_disabled'] is True, {'preparation_failed': dom})
            return self.read(key, name, id, False)
        finally:
            self.restore()

    def dynamic(self, key, name, id):
        self.restore()
        details = []
        try:
            for disabled in (False, True, False):
                self.js("const e=document.getElementById(a.id);e.removeAttribute('aria-disabled');e.disabled=a.disabled;return true;", {'id': id, 'disabled': disabled})
                dom = self.dom(id)
                require(dom['disabled'] is disabled and dom['pseudo_disabled'] is disabled, {'preparation_failed': dom})
                details.append(self.read(key, name, id, not disabled))
            return {'name': name, 'sequence': [x['actual_is_enabled'] for x in details], 'same_element_reference': True, 'measurements': details}
        finally:
            self.restore()

    def aria(self, key, name, id, value):
        self.restore()
        try:
            self.js("const e=document.getElementById(a.id);e.disabled=false;if(a.value===null)e.removeAttribute('aria-disabled');else e.setAttribute('aria-disabled',a.value);return true;", {'id': id, 'value': value})
            dom = self.dom(id)
            require(dom['disabled'] is False and dom['pseudo_disabled'] is False and dom['aria_disabled'] == value, {'preparation_failed': dom})
            return self.read(key, name, id, value != 'true')
        finally:
            self.restore()

    def readonly(self, key, name, id, expected):
        self.restore()
        before = self.snapshot()
        values = [self.element(key).is_enabled() for _ in range(3)]
        after = self.snapshot()
        return require(before == after and all(type(v) is bool and v is expected for v in values), {'name': name, 'values': values, 'expected': expected, 'attributes_focus_scroll_events_unchanged': before == after, 'dom_before': before, 'dom_after': after})

    def restored(self):
        self.restore()
        actual = self.snapshot()
        return require(actual == self.original and not any(actual['events'].values()), {'attributes_focus_scroll_events_restored': actual == self.original, 'events': actual['events']})

    def closed_page(self):
        self.page.close(ignore_beforeunload=True)
        return raises(ActionError, self.element('click_button').is_enabled, '网页对象已失效', 'stale_page_reference')

    def closed_package(self):
        self.package.close()
        return raises(HostUnavailableError, self.element('click_button').is_enabled, '连接已关闭')

    def cleanup(self):
        errors = []
        try:
            current = {p._page_ref['id'] for p in web.get_all(mode='chrome')} if self.baseline is not None else set()
            if self.page and self.page_id in current:
                try:
                    self.restore()
                    self.js("const w=window.__isEnabledObserve;if(w){for(const k of Object.keys(w.counts))document.removeEventListener(k,w.listener,true);delete window.__isEnabledObserve;}return true;")
                except Exception as exc:
                    errors.append(error(exc))
                self.page.close(ignore_beforeunload=True)
        except Exception as exc:
            errors.append(error(exc))
        if self.package:
            try:
                self.package.close()
            except Exception as exc:
                errors.append(error(exc))
        if self.tmp.exists():
            require(self.tmp.resolve().parent == (ROOT/'.pytest_tmp/is_enabled_live').resolve(), 'Unexpected cleanup path')
            shutil.rmtree(self.tmp)
        after = {p._page_ref['id'] for p in web.get_all(mode='chrome')} if self.baseline is not None else set()
        unchanged = self.library_hash is None or hashlib.sha256((self.args.library/'elements.json').read_bytes()).hexdigest() == self.library_hash
        detail = {'errors': errors, 'own_tab_closed': self.page_id not in after, 'temporary_copy_removed': not self.tmp.exists(), 'source_library_unchanged': unchanged, 'tab_count': f'{len(self.baseline or set())}->{len(after)}', 'external_added': sorted(after-(self.baseline or set())), 'external_removed': sorted((self.baseline or set())-after)}
        return require(not errors and detail['own_tab_closed'] and detail['temporary_copy_removed'] and unchanged and not detail['external_added'] and not detail['external_removed'], detail)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--url', default=URL)
    parser.add_argument('--library', type=Path, default=LIBRARY)
    parser.add_argument('--disabled-element', default=TARGETS[0][1])
    parser.add_argument('--enabled-element', default=TARGETS[1][1])
    parser.add_argument('--contract-only', action='store_true')
    parser.add_argument('--json', action='store_true')
    parser.add_argument('--report-file', type=Path)
    args = parser.parse_args(argv)
    run = Run(args)
    print('UIAutoma Web API 测试\nAPI     : uiautoma.web.WebElement.is_enabled\n页面    : '+args.url, flush=True)
    good = run.case('api_contract', '签名仅 self，返回 bool；SDK→RPC→Runtime→引擎快照一致', contract) == 'PASS'
    raw = ValidationRaw()
    validation_element = WebElement(raw)
    run.case('unexpected_positional', '多余位置参数抛 TypeError，raw 调用 0 次', lambda: raises(TypeError, lambda: validation_element.is_enabled(True)))
    run.case('unexpected_keyword', '多余关键字抛 TypeError，raw 调用 0 次', lambda: raises(TypeError, lambda: validation_element.is_enabled(timeout=1)))
    require(raw.calls == 0, {'unexpected_raw_calls': raw.calls})
    if not args.contract_only:
        try:
            if good:
                run.case('environment', 'Runtime、库副本、自有静默靶场可用', run.setup)
            else:
                run.case('environment', '合同一致后再连接 Runtime', lambda: (_ for _ in ()).throw(Blocked('合同已变，先核对源码')))
            for key, name, id, expected in run.targets:
                run.case('mapping_'+key, '库选择器唯一命中 '+id, lambda key=key, name=name, id=id: run.mapping(key, name, id), live=True)
            for key, name, id, expected in run.targets:
                run.case('baseline_'+key, f'原始按钮状态 is_enabled() is {expected}', lambda key=key, name=name, id=id, expected=expected: run.baseline_state(key, name, id, expected), live=True)
            for key, name, id, expected in run.targets:
                for value in ATTRIBUTE_VALUES:
                    run.case('disabled_'+(value or 'empty')+'_'+key, 'HTML disabled 存在即禁用；IDL / :disabled=True；API=False', lambda key=key, name=name, id=id, value=value: run.attribute(key, name, id, value), live=True)
            for key, name, id, expected in run.targets:
                run.case('dynamic_'+key, '同一对象动态切换，返回 True→False→True', lambda key=key, name=name, id=id: run.dynamic(key, name, id), live=True)
            for key, name, id, expected in run.targets:
                for value in ('true', 'false', None):
                    run.case('aria_'+str(value)+'_'+key, '原生 disabled 不存在；ARIA true=False、false/缺失=True', lambda key=key, name=name, id=id, value=value: run.aria(key, name, id, value), live=True)
            for key, name, id, expected in run.targets:
                run.case('readonly_'+key, '连读三次 bool 正确，不改变属性、焦点、滚动或事件计数', lambda key=key, name=name, id=id, expected=expected: run.readonly(key, name, id, expected), live=True)
            run.case('restore_original', '自有两个按钮恢复原状态，无 click/input/change/keydown 事件', run.restored, live=True)
            run.case('closed_page', '页面关闭后 ActionError / stale_page_reference', run.closed_page, live=True)
            run.case('closed_package', '连接关闭后 HostUnavailableError / 连接已关闭', run.closed_package, live=True)
        finally:
            run.case('cleanup', '关闭自有页面/连接、删副本；库不变、标签基线一致', run.cleanup)
    counts = {state: sum(row['status'] == state for row in run.rows) for state in ('PASS', 'FAIL', 'BLOCKED')}
    code = 2 if counts['BLOCKED'] else 1 if counts['FAIL'] else 0
    state = 'SKIPPED' if args.contract_only and code == 0 else 'VERIFIED' if code == 0 else 'READY_FOR_LIVE'
    result = {'api': 'uiautoma.web.WebElement.is_enabled', 'date': '2026-10-08', 'state': state, 'url': args.url, 'library': str(args.library), 'counts': counts, 'total': len(run.rows), 'exit_code': code, 'contract_only': args.contract_only, 'rows': run.rows}
    if args.report_file:
        args.report_file.parent.mkdir(parents=True, exist_ok=True)
        args.report_file.write_text(json.dumps(result, ensure_ascii=False, indent=2, default=str)+'\n', encoding='utf-8')
    print(f"{state} · {counts['PASS']}/{len(run.rows)} 通过 · {counts['FAIL']} 失败 · {counts['BLOCKED']} 阻塞 · 退出码 {code}", flush=True)
    if args.json:
        print(json.dumps(result, ensure_ascii=False, default=str))
    return code


if __name__ == '__main__':
    raise SystemExit(main())
