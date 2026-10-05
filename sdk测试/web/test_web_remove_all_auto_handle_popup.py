"""在 keys-click-test 真实模态弹窗上验收 remove_all_auto_handle_popup。

先证明自动关闭有效，再移除规则并连续观察弹窗保持打开且关闭点击为零。
使用用户的三个库元素、临时库与本次标签；退出码 0/1/2 = 通过/失败/阻塞。
"""
from __future__ import annotations

import argparse
import inspect
import json
import math
from pathlib import Path
import subprocess
import sys
import time

sys.dont_write_bytecode = True
from test_web_auto_handle_popup import PopupContext, URL, OPEN_BUTTON, CLOSE_BUTTON, MODAL
from _web_remaining_common import CONTRACT_FILE, LIBRARY, PRODUCT, web

__test__ = False
API = 'uiautoma.web.remove_all_auto_handle_popup'


class RemovePopupContext(PopupContext):
    def __init__(self, args):
        super().__init__(args)
        self.api = 'web.remove_all_auto_handle_popup'

    def prepare_and_control(self):
        self.page.activate()
        return super().prepare_and_control()

    def remove(self):
        returned = web.remove_all_auto_handle_popup()
        return self.expect(returned is None, {'return': returned})

    def prove_rule(self, selector=False):
        self.page.activate()
        registered = self.register(selector)
        acquired = self.acquire_after_rule()
        closed = self.automatic_close()
        return {'registration': registered, 'page': acquired, 'automatic_close': closed}

    def retain(self, open_again=True):
        self.page.activate()
        if open_again:
            self.expect(not self.observe()['visible'], self.observe())
            self.observe('reset')
            self.el(self.args.open_button).click(simulative=False, delay_after=.3)
        # 不在已打开的分支清空事件，避免漏掉移除后迟到的自动点击。
        self.wait(self.observe, lambda state: state['visible'])
        if self.progress:
            print(f'规则已移除：弹窗应保持打开 {self.args.observe_seconds:g} 秒，请观察…', flush=True)
        started = time.monotonic()
        samples = 0
        while True:
            state = self.observe()
            self.expect(state['visible'] and not state['close_clicks'], state)
            samples += 1
            elapsed = time.monotonic() - started
            if elapsed >= self.args.observe_seconds:
                return {**state, 'observed_seconds': round(elapsed, 3), 'samples': samples}
            time.sleep(.1)

    def manual_close(self):
        self.page.activate()
        before = self.observe()
        self.expect(before['visible'] and not before['close_clicks'], before)
        returned = self.el(self.args.close_button).click(simulative=False, delay_after=.3)
        state = self.wait(self.observe, lambda value: not value['visible'])
        return self.expect(returned is None and len(state['close_clicks']) == 1,
                           {'click_return': returned, **state})

    def repeated_remove(self):
        returned = [self.remove(), self.remove()]
        return {'removals': returned, 'still_open': self.retain(False)}

    def reopened(self):
        retained = self.retain()
        closed = self.manual_close()
        return {'after_remove': retained, 'manual_close': closed}

    def remove_before_attach(self):
        # 页面已打开，但新规则尚未通过 get/create 绑定到这个页面。
        registered = self.register()
        removed = self.remove()
        return {'registration': registered, 'remove': removed, 'still_open': self.retain(False)}


def run(args):
    c = RemovePopupContext(args)
    contract = json.loads(CONTRACT_FILE.read_text(encoding='utf-8'))['apis']['web.remove_all_auto_handle_popup']
    c.case('api_contract', '无参数签名与只读源码快照一致，返回注解为 None',
           lambda: c.expect(str(inspect.signature(web.remove_all_auto_handle_popup)) == contract['signature'],
                            str(inspect.signature(web.remove_all_auto_handle_popup))))
    if not args.contract_only:
        if c.case('library_targets', '库中存在打开按钮、模态弹窗与关闭按钮', c.library_targets) == 'PASS':
            try:
                if c.case('environment', 'Runtime、Chrome、靶场、临时库与标签基线可用', c.setup) == 'PASS':
                    cases = [
                        ('empty_rules_remove', '没有规则时返回 None', c.remove),
                        ('control_without_rule', '核对三元素映射，无规则时弹窗保持打开，库关闭按钮可关闭', c.prepare_and_control),
                        ('before_remove_auto', '先注册并绑定规则，确认自动关闭事件一次且弹窗隐藏', c.prove_rule),
                        ('remove_registered', '移除已生效的规则，返回 None', c.remove),
                        ('same_page_after_remove', '原页面弹窗持续可见，自动关闭点击为零', c.retain),
                        ('idempotent_remove_open', '重复移除两次均返回 None，已打开弹窗仍保持打开', c.repeated_remove),
                        ('manual_close_same_page', '显式点击库关闭按钮后弹窗才隐藏', c.manual_close),
                        ('reopen_after_remove', '同页再次打开仍不自动关闭，随后显式关闭', c.reopened),
                        ('create_after_remove', '关闭本次旧标签，在无规则状态创建本次新标签', c.create_after_rule),
                        ('new_page_after_remove', '新页面弹窗持续可见，自动关闭点击为零', c.retain),
                        ('remove_registered_before_attach', '注册未绑定的新规则后移除，已有弹窗不被该 API 关闭', c.remove_before_attach),
                        ('manual_close_new_page', '显式点击新页库关闭按钮后弹窗隐藏', c.manual_close),
                        ('reregister_restore_auto', '规则可重新注册为 Web Selector，绑定后自动关闭恢复', lambda: c.prove_rule(True)),
                        ('second_remove', '再次移除重建的规则，返回 None', c.remove),
                        ('after_second_remove', '第二次移除后弹窗仍保持打开，随后显式关闭', c.reopened),
                    ]
                    for case_id, expected, invoke in cases:
                        if c.case(case_id, expected, invoke) != 'PASS':
                            break
            finally:
                c.case('cleanup', '移除本连接规则/观察器，关闭本次页面和库，复核临时目录与标签', c.cleanup)
    failed = any(row['status'] == 'FAIL' for row in c.rows)
    blocked = any(row['status'] == 'BLOCKED' for row in c.rows)
    verified = not args.contract_only and len(c.rows) == 19 and all(row['status'] == 'PASS' for row in c.rows)
    code = 1 if failed else 2 if blocked else 0
    return {'api': API, 'lifecycle': 'VERIFIED' if verified else 'READY_FOR_LIVE',
            'url': args.target_url, 'element_library': str(args.element_library),
            'open_button': args.open_button, 'close_button': args.close_button, 'modal': args.modal,
            'observation_seconds': args.observe_seconds,
            'product_worktree': str(PRODUCT),
            'product_commit': subprocess.check_output(['git','-C',str(PRODUCT),'rev-parse','HEAD'], text=True).strip(),
            'contract': contract, 'results': c.rows, 'exit_code': code}, code


def main():
    parser = argparse.ArgumentParser(description=API+'：规则移除后的真实弹窗验收')
    parser.add_argument('--target-url', default=URL)
    parser.add_argument('--element-library', type=Path, default=LIBRARY)
    parser.add_argument('--open-button', default=OPEN_BUTTON)
    parser.add_argument('--close-button', default=CLOSE_BUTTON)
    parser.add_argument('--modal', default=MODAL)
    parser.add_argument('--observe-seconds', type=float, default=3)
    parser.add_argument('--wait-timeout', type=float, default=8)
    parser.add_argument('--contract-only', action='store_true')
    parser.add_argument('--json', action='store_true')
    parser.add_argument('--report-file', type=Path)
    args = parser.parse_args()
    args.control_observe_seconds = 1
    if not math.isfinite(args.observe_seconds) or args.observe_seconds < 1 or not math.isfinite(args.wait_timeout) or args.wait_timeout <= 0:
        parser.error('观察时间须为有限数且至少 1 秒，等待时间须为有限正数')
    if not args.json:
        print('UIAutoma Web API 测试\nAPI     : '+API+'\n页面    : '+args.target_url, flush=True)
    report, code = run(args)
    if args.report_file:
        args.report_file.parent.mkdir(parents=True, exist_ok=True)
        args.report_file.write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        for index, row in enumerate(report['results'], 1):
            color, label = {'PASS': ('\x1b[92m','通过'), 'FAIL': ('\x1b[91m','失败'), 'BLOCKED': ('\x1b[93m','阻塞')}[row['status']]
            print(f"{index:02}/{len(report['results']):02} {color}[{label}]\x1b[0m {row['case_id']} 期望 {row['expected']}；实测 {row['actual']}；{row['elapsed_ms']}ms")
        passed = sum(row['status'] == 'PASS' for row in report['results'])
        print(f"{report['lifecycle']} · {passed}/{len(report['results'])} 通过 · 退出码 {code}")
    return code


if __name__ == '__main__':
    raise SystemExit(main())
