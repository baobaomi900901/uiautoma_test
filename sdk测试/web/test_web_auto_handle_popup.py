"""在 keys-click-test 的真实 Ant Design 模态弹窗上验收 auto_handle_popup。

使用用户保存的打开/关闭按钮及临时库副本。DOM 监听只记录点击和可见状态，
不触发关闭。退出码：0 全通过，1 失败，2 环境/库元素缺失。
"""
from __future__ import annotations

import argparse
import inspect
import json
from pathlib import Path
import subprocess
import sys
import time

sys.dont_write_bytecode = True
from _web_remaining_common import (
    Context, CONTRACT_FILE, LIBRARY, PRODUCT, copy_library, native_windows,
    open_package, web, InvalidParamsError,
)
from uiautoma import UnsupportedActionError
from uiautoma.selector import Selector

__test__ = False
API = 'uiautoma.web.auto_handle_popup'
URL = 'https://baobaomi900901.github.io/xpath/#/keys-click-test'
OPEN_BUTTON = 'web靶场_打开遮罩弹窗_按钮'
CLOSE_BUTTON = 'web靶场_模态弹窗_关闭按钮'
MODAL = 'web靶场_模态弹窗'

# 监听已有页面；这里只观察 DOM 和点击事件，不修改弹窗行为。
OBSERVE = r'''function (_element, action) {
  const key = '__uiautoma_popup_test_observer';
  function modal() {
    return [...document.querySelectorAll('.ant-modal')].find(e =>
      e.querySelector('.ant-modal-title')?.textContent.trim() === '遮挡测试弹窗');
  }
  function snapshot() {
    const e = modal(), wrap = e?.closest('.ant-modal-wrap');
    const visible = !!e && !!wrap && wrap.getClientRects().length > 0 &&
      getComputedStyle(wrap).display !== 'none' && getComputedStyle(wrap).visibility !== 'hidden';
    return {visible, close_count: e?.querySelectorAll('button.ant-modal-close').length || 0};
  }
  if (action === 'install') {
    if (window[key]) document.removeEventListener('click', window[key].listener, true);
    const state = {events: []};
    state.listener = event => {
      const button = event.target.closest?.('button.ant-modal-close');
      if (button && modal()?.contains(button)) state.events.push({...snapshot(), at_ms: performance.now()});
    };
    document.addEventListener('click', state.listener, true);
    window[key] = state;
  } else if (action === 'reset') {
    if (window[key]) window[key].events = [];
  } else if (action === 'remove') {
    if (window[key]) document.removeEventListener('click', window[key].listener, true);
    delete window[key];
  }
  return {...snapshot(), close_clicks: window[key]?.events || []};
}'''


class MissingScene(Exception):
    pass


class PopupContext(Context):
    def __init__(self, args):
        super().__init__('web.auto_handle_popup', progress=not args.json)
        self.args = args
        self.baseline = None
        self.opener = self.closer = None

    def case(self, case_id, expected, fn, known=False):
        started = time.perf_counter()
        try:
            actual, status = fn(), 'PASS'
        except MissingScene as exc:
            actual, status = {'reason': str(exc)}, 'BLOCKED'
        except Exception as exc:
            trace = getattr(exc, 'trace_info', '')
            actual = {'exception': type(exc).__name__, 'message': str(exc), 'trace': trace}
            status = 'BLOCKED' if trace in {'uiautomation_provider_unavailable', 'browser_host_window_mismatch'} or type(exc).__name__ == 'HostUnavailableError' else 'FAIL'
        self.rows.append({'case_id': case_id, 'expected': expected, 'status': status,
                          'actual': actual, 'elapsed_ms': round((time.perf_counter()-started)*1000, 1)})
        return status

    def library_targets(self):
        catalog = self.args.element_library / 'elements.json'
        if not catalog.is_file():
            raise MissingScene(f'元素库不存在：{catalog}')
        pending = [json.loads(catalog.read_text(encoding='utf-8'))]
        names = set()
        while pending:
            value = pending.pop()
            if isinstance(value, dict):
                if value.get('type') == 'web' and value.get('id'): names.add(value.get('name'))
                pending.extend(value.values())
            elif isinstance(value, list): pending.extend(value)
        missing = [name for name in (self.args.open_button, self.args.close_button, self.args.modal) if name not in names]
        if missing:
            raise MissingScene('缺少已保存的 Web 元素：' + '、'.join(missing) + '；请在 App 中抓取后复测')
        return {'open_button': self.args.open_button, 'close_button': self.args.close_button, 'modal': self.args.modal}

    def setup(self):
        self.baseline = {p._page_ref['id'] for p in web.get_all(mode='chrome')}
        self.dialogs_before = set(native_windows('#32770'))
        copy_library(self.args.element_library, self.tmp/'library')
        self.package = open_package(str(self.tmp/'library'), timeout=8, connect_timeout=8)
        self.page = web.create(self.args.target_url, mode='chrome', load_timeout=25, silent_running=False)
        self.page_id = self.page._page_ref['id']
        self.observe('install')
        return {'url': self.page.get_url(), 'library': str(self.args.element_library),
                'temporary_library': str(self.tmp/'library'), 'baseline_tabs': len(self.baseline)}

    def observe(self, action='read'):
        return self.page.execute_javascript(OBSERVE, action)

    def prepare_and_control(self):
        self.opener = self.el(self.args.open_button)
        self.expect(self.opener.get_attribute('id') == 'btn-open-occlusion-modal',
                    {'open_button': self.args.open_button, 'id': self.opener.get_attribute('id')})
        self.opener.click(simulative=False, delay_after=.1)
        opened = self.wait(self.observe, lambda value: value['visible'])
        modal_mapping = self.el(self.args.modal).execute_javascript('''function (element) {
          const modal = element.matches('.ant-modal') ? element :
            element.closest('.ant-modal') || element.querySelector('.ant-modal');
          return {tag: element.tagName, title: modal?.querySelector('.ant-modal-title')?.textContent.trim()};
        }''')
        self.expect(modal_mapping['title'] == '遮挡测试弹窗', modal_mapping)
        self.closer = self.el(self.args.close_button)
        mapping = self.closer.execute_javascript('''function (element) {
          const button = element.closest('button.ant-modal-close');
          return {tag: element.tagName, is_modal_close: !!button,
            title: button?.closest('.ant-modal')?.querySelector('.ant-modal-title')?.textContent.trim()};
        }''')
        self.expect(mapping['is_modal_close'] and mapping['title'] == '遮挡测试弹窗' and opened['close_count'] == 1, mapping)
        if self.progress: print(f'未注册规则：弹窗保持打开 {self.args.control_observe_seconds:g} 秒，请观察…', flush=True)
        time.sleep(self.args.control_observe_seconds)
        stable = self.observe()
        self.expect(stable['visible'] and not stable['close_clicks'], stable)
        self.closer.click(simulative=False, delay_after=.1)
        closed = self.wait(self.observe, lambda value: not value['visible'])
        self.expect(len(closed['close_clicks']) == 1, closed)
        self.observe('reset')
        return {'open_id': 'btn-open-occlusion-modal', 'modal_mapping': modal_mapping, 'close_mapping': mapping,
                'without_rule': stable, 'manual_close': closed}

    def register(self, selector=False):
        close = self.package.selector(self.args.close_button, kind='web') if selector else self.args.close_button
        returned = web.auto_handle_popup('close_dialog', close_button=close)
        return self.expect(returned is None, {'return': returned, 'close_button': self.args.close_button,
                                             'argument_type': type(close).__name__})

    def acquire_after_rule(self):
        acquired = web.get(url=self.page.get_url(), mode='chrome', load_timeout=8)
        self.expect(acquired._page_ref['id'] == self.page_id, {'page_id': acquired._page_ref['id'], 'expected_id': self.page_id})
        self.page = acquired
        return {'same_owned_page': True, 'page_id': self.page_id}

    def create_after_rule(self):
        previous = self.page_id
        self.observe('remove')
        self.page.close(ignore_beforeunload=True)
        self.page = None
        self.page = web.create(self.args.target_url, mode='chrome', load_timeout=25, silent_running=False)
        self.page_id = self.page._page_ref['id']
        self.observe('install')
        return self.expect(self.page_id != previous, {'closed_page_id': previous, 'new_page_id': self.page_id})

    def automatic_close(self):
        # 留出后台轮询复核上轮隐藏状态的时间，以便重复触发同一个 DOM 节点。
        time.sleep(.8)
        self.observe('reset')
        if self.progress: print('规则已注册：点击打开按钮，等待 API 自动点击关闭按钮…', flush=True)
        self.opener = self.el(self.args.open_button)
        self.opener.click(simulative=False, delay_after=.05)
        result = self.wait(self.observe, lambda value: not value['visible'] and bool(value['close_clicks']),
                           timeout=self.args.wait_timeout)
        return self.expect(len(result['close_clicks']) == 1 and result['close_clicks'][0]['visible'], result)

    def cleanup(self):
        errors = []
        if self.package is not None:
            try: web.remove_all_auto_handle_popup()
            except Exception as exc: errors.append('remove_rules: ' + str(exc))
        if self.page is not None:
            try: self.observe('remove')
            except Exception as exc: errors.append('remove_observer: ' + str(exc))
        if self.baseline is None:
            return self.expect(not errors and not self.tmp.exists(), {'errors': errors, 'resources_created': False})
        actual = super().cleanup()
        actual['rule_observer_cleanup_errors'] = errors
        return self.expect(not errors and not actual['external_added'] and not actual['external_removed'], actual)


def run(args):
    c = PopupContext(args)
    frozen = json.loads(CONTRACT_FILE.read_text(encoding='utf-8'))['apis']['web.auto_handle_popup']
    c.case('api_contract', '公开签名与只读源码快照一致',
           lambda: c.expect(str(inspect.signature(web.auto_handle_popup)) == frozen['signature'], str(inspect.signature(web.auto_handle_popup))))
    for case_id, expected, error, invoke, message in [
        ('invalid_method', '非法处理方式抛 InvalidParamsError', InvalidParamsError, lambda: web.auto_handle_popup('unknown'), '必须为 close_dialog'),
        ('unsupported_process', 'execute_process 抛 UnsupportedActionError', UnsupportedActionError, lambda: web.auto_handle_popup('execute_process'), '暂不支持'),
        ('missing_close_button', '未提供关闭按钮抛 InvalidParamsError', InvalidParamsError, lambda: web.auto_handle_popup('close_dialog'), 'selector 必须'),
        ('blank_close_button', '空名称抛 InvalidParamsError', InvalidParamsError, lambda: web.auto_handle_popup('close_dialog', close_button=' '), '不能为空'),
        ('invalid_close_type', '非字符串/Selector 抛 InvalidParamsError', InvalidParamsError, lambda: web.auto_handle_popup('close_dialog', close_button=42), 'selector 必须'),
        ('non_web_selector', 'Win Selector 抛 InvalidParamsError', InvalidParamsError, lambda: web.auto_handle_popup('close_dialog', close_button=Selector(name='invalid', framework='win', item_id='invalid')), '需要 Web 选择器'),
    ]:
        c.case(case_id, expected, lambda e=error, f=invoke, m=message: c.raises(e, f, message=m))
    if not args.contract_only:
        if c.case('library_targets', '元素库已保存打开按钮和关闭按钮', c.library_targets) == 'PASS':
            try:
                if c.case('environment', 'Runtime、Chrome、靶场与临时库可用', c.setup) == 'PASS':
                    if c.case('control_without_rule', '打开按钮映射正确；无规则时弹窗保持打开，库关闭按钮可关闭', c.prepare_and_control) == 'PASS':
                        if c.case('register_name', '用关闭按钮名称注册返回 None', c.register) == 'PASS':
                            c.case('duplicate_rule', '同一个关闭按钮重复注册抛 InvalidParamsError',
                                   lambda: c.raises(InvalidParamsError, c.register, message='请勿重复注册'))
                            if c.case('acquire_after_name_rule', '注册后重新获取本次页面', c.acquire_after_rule) == 'PASS':
                                for number in (1, 2):
                                    c.case(f'auto_close_name_{number}', '仅点击打开按钮；自动关闭事件恰好一次且弹窗消失', c.automatic_close)
                        web.remove_all_auto_handle_popup()  # 辅助清理，为 Selector 参数分支重新准备。
                        if c.case('register_selector', '用库中 Web Selector 注册返回 None', lambda: c.register(True)) == 'PASS':
                            if c.case('create_after_selector_rule', '关闭本次旧标签，注册后创建新页面', c.create_after_rule) == 'PASS':
                                c.case('auto_close_selector', 'Web Selector 规则自动点击关闭按钮，弹窗消失', c.automatic_close)
            except Exception as exc:
                c.case('scenario_error', '真实场景完整执行', lambda: (_ for _ in ()).throw(exc))
            finally:
                c.case('cleanup', '移除本连接规则和观察器；关闭本次页面/库并复核标签与临时目录', c.cleanup)
    required = {'control_without_rule', 'register_name', 'auto_close_name_1', 'auto_close_name_2',
                'register_selector', 'auto_close_selector', 'cleanup'}
    passed = {row['case_id'] for row in c.rows if row['status'] == 'PASS'}
    failed = any(row['status'] == 'FAIL' for row in c.rows)
    blocked = any(row['status'] == 'BLOCKED' for row in c.rows)
    code = 1 if failed else 2 if blocked else 0
    verified = not args.contract_only and not failed and not blocked and required <= passed
    return {'api': API, 'lifecycle': 'VERIFIED' if verified else 'READY_FOR_LIVE',
            'url': args.target_url, 'element_library': str(args.element_library),
            'open_button': args.open_button, 'close_button': args.close_button,
            'modal': args.modal,
            'product_worktree': str(PRODUCT),
            'product_commit': subprocess.check_output(['git', '-C', str(PRODUCT), 'rev-parse', 'HEAD'], text=True).strip(),
            'contract': frozen, 'results': c.rows, 'exit_code': code}, code


def main():
    parser = argparse.ArgumentParser(description=API+'：真实 DOM 弹窗验收')
    parser.add_argument('--target-url', default=URL)
    parser.add_argument('--element-library', type=Path, default=LIBRARY)
    parser.add_argument('--open-button', default=OPEN_BUTTON)
    parser.add_argument('--close-button', default=CLOSE_BUTTON)
    parser.add_argument('--modal', default=MODAL)
    parser.add_argument('--control-observe-seconds', type=float, default=3)
    parser.add_argument('--wait-timeout', type=float, default=8)
    parser.add_argument('--contract-only', action='store_true')
    parser.add_argument('--json', action='store_true')
    parser.add_argument('--report-file', type=Path)
    args = parser.parse_args()
    if args.control_observe_seconds < 1 or args.wait_timeout <= 0:
        parser.error('观察时间至少 1 秒，自动关闭等待时间必须大于 0')
    if not args.json: print('UIAutoma Web API 测试\nAPI     : '+API+'\n页面    : '+args.target_url, flush=True)
    report, code = run(args)
    if args.report_file:
        args.report_file.parent.mkdir(parents=True, exist_ok=True)
        args.report_file.write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    if args.json: print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        for index, row in enumerate(report['results'], 1):
            color, label = {'PASS': ('\x1b[92m', '通过'), 'FAIL': ('\x1b[91m', '失败'), 'BLOCKED': ('\x1b[93m', '阻塞')}[row['status']]
            print(f"{index:02}/{len(report['results']):02} {color}[{label}]\x1b[0m {row['case_id']} 期望 {row['expected']}；实测 {row['actual']}；{row['elapsed_ms']}ms")
        passed = sum(row['status'] == 'PASS' for row in report['results'])
        print(f"{report['lifecycle']} · {passed}/{len(report['results'])} 通过 · 退出码 {code}")
    return code


if __name__ == '__main__':
    raise SystemExit(main())
