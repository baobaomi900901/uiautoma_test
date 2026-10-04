"""使用用户保存的按钮测试真实 alert/confirm/prompt，读取页面 #status 确证结果。

靶场：#/web-dialog-test；库：260902_web元素；仅操作临时库和本次标签。
源码快照与逐项结果写入报告。退出码：0 全通过，1 失败，2 环境阻塞。
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
    Context, LIBRARY, PRODUCT, copy_library, native_windows, open_package, web,
    WebBrowser, ActionError, InvalidParamsError,
)
from test_web_browser_handle_javascript_dialog import check_contract

__test__ = False
API = 'uiautoma.web.WebBrowser.handle_javascript_dialog'
URL = 'https://baobaomi900901.github.io/xpath/#/web-dialog-test'
TARGETS = {
    'alert': ('web靶场_触发alert对话框_按钮','btn-alert','这是一条 Alert 消息，请点击确定关闭。'),
    'confirm': ('web靶场_触发confirm对话框_按钮','btn-confirm','是否确认执行此操作？'),
    'prompt': ('web靶场_触发Prompt对话框_按钮','btn-prompt','请输入您的名称：'),
}


class DialogContext(Context):
    def __init__(self,args):
        super().__init__('browser.handle_javascript_dialog',progress=not args.json)
        self.args=args
        self.elements={}

    def setup(self):
        self.baseline={p._page_ref['id'] for p in web.get_all(mode='chrome')}
        self.dialogs_before=set(native_windows('#32770'))
        copy_library(self.args.element_library,self.tmp/'library')
        self.package=open_package(str(self.tmp/'library'),timeout=8,connect_timeout=8)
        self.page=web.create(self.args.target_url,mode='chrome',load_timeout=25,silent_running=False)
        self.page_id=self.page._page_ref['id']
        self.page.activate()
        return {'url':self.page.get_url(),'library':str(self.args.element_library),
                'temporary_library':str(self.tmp/'library'),'baseline_tabs':len(self.baseline)}

    def prepare_element(self,kind):
        name,node_id,_=TARGETS[kind]
        element=self.el(name)
        actual_id=element.get_attribute('id')
        self.expect(actual_id==node_id,{'element_name':name,'id':actual_id,'expected_id':node_id})
        self.elements[kind]=element
        return {'element_name':name,'id':actual_id}

    def scenario(self,kind,result,text,prefix):
        self.page.activate()
        if self.progress: print(f'[{kind}/{result}] 点击 {TARGETS[kind][0]}…',flush=True)
        self.elements[kind].click(simulative=True,delay_after=1)
        message=self.page.get_javascript_dialog_text(wait_appear_timeout=self.args.wait_timeout)
        self.expect(message==TARGETS[kind][2],{'dialog_text':message})
        if self.progress: print(f'[{kind}/{result}] 对话框已出现，停留 {self.args.dialog_observe_seconds:g} 秒…',flush=True)
        time.sleep(self.args.dialog_observe_seconds)
        returned=self.page.handle_javascript_dialog(result,text=text,wait_appear_timeout=self.args.wait_timeout)
        status=self.wait(lambda:self.js("document.getElementById('status').textContent",form=False),
                         lambda value:isinstance(value,str) and value.startswith(prefix))
        return self.expect(returned is None,{'return':returned,'dialog_text':message,'page_status':status})

    def cleanup(self):
        sweep_error=None
        swept=False
        if self.page is not None:
            try:
                self.page.handle_javascript_dialog('cancel',wait_appear_timeout=0)
                swept=True
            except ActionError as exc:
                if exc.trace_info!='web_dialog_timeout': sweep_error=str(exc)
            except Exception as exc: sweep_error=str(exc)
        actual=super().cleanup()
        actual.update({'javascript_swept':swept,'sweep_error':sweep_error})
        return self.expect(sweep_error is None,actual)


def run(args):
    c=DialogContext(args)
    def contract():
        checked=check_contract()
        return c.expect(checked['status']=='PASS',{'signature':str(inspect.signature(WebBrowser.handle_javascript_dialog)),
                                                'contract':checked['detail']})
    c.case('api_contract','公开参数、默认值、关键字约束和返回注解与源码合同一致',contract)
    if not args.contract_only:
        try:
            if c.case('environment','Runtime、Chrome、靶场和临时元素库可用',c.setup)=='PASS':
                prepared=[c.case(kind+'_element','用户指定库元素定位到对应触发按钮',lambda k=kind:c.prepare_element(k))
                          for kind in TARGETS]
                if all(status=='PASS' for status in prepared):
                    for case_id,kind,result,text,prefix in [
                        ('alert_accept','alert','ok',None,'Alert 已关闭（用户点击了确定）'),
                        ('confirm_accept_true','confirm','ok',None,'Confirm 结果：确定（true）'),
                        ('confirm_cancel_false','confirm','cancel',None,'Confirm 结果：取消（false）'),
                        ('prompt_accept_text','prompt','ok','uiautoma 音乐','Prompt 结果：确定，输入值为「uiautoma 音乐」'),
                        ('prompt_default_text','prompt','ok',None,'Prompt 结果：确定，输入值为「UiPilot」'),
                        ('prompt_cancel_null','prompt','cancel',None,'Prompt 结果：取消（null）'),
                        ('cancel_ignores_text','prompt','cancel','should-be-ignored','Prompt 结果：取消（null）'),
                    ]:
                        if c.case(case_id,'返回 None，页面自身 #status 显示 '+prefix,
                                  lambda k=kind,r=result,t=text,p=prefix:c.scenario(k,r,t,p))!='PASS':
                            try:c.page.handle_javascript_dialog('cancel',wait_appear_timeout=0)
                            except Exception: pass
                    c.case('no_dialog_timeout','无对话框且等待 0 秒时抛 ActionError，trace=web_dialog_timeout',
                           lambda:c.raises(ActionError,lambda:c.page.handle_javascript_dialog('ok',wait_appear_timeout=0),trace='web_dialog_timeout'))
                    c.case('invalid_result','非法 dialog_result 抛 InvalidParamsError，trace=invalid_params',
                           lambda:c.raises(InvalidParamsError,lambda:c.page.handle_javascript_dialog('maybe'),trace='invalid_params'))
                    c.case('invalid_timeout','wait_appear_timeout=-2 抛 InvalidParamsError',
                           lambda:c.raises(InvalidParamsError,lambda:c.page.handle_javascript_dialog('ok',wait_appear_timeout=-2)))
        finally:
            c.case('cleanup','清扫本次对话框、关闭本次标签和库、删除临时文件，复核标签数',c.cleanup)
    failed=any(r['status']=='FAIL' for r in c.rows)
    blocked=any(r['status']=='KNOWN' for r in c.rows)
    verified=not args.contract_only and len(c.rows)==16 and all(r['status']=='PASS' for r in c.rows)
    code=1 if failed else 2 if blocked else 0
    method=WebBrowser.handle_javascript_dialog
    return {'api':API,'lifecycle':'VERIFIED' if verified else 'READY_FOR_LIVE',
            'url':args.target_url,'element_library':str(args.element_library),
            'product_worktree':str(PRODUCT),
            'product_commit':subprocess.check_output(['git','-C',str(PRODUCT),'rev-parse','HEAD'],text=True).strip(),
            'contract':{'signature':str(inspect.signature(method)),'source_file':inspect.getsourcefile(method),
                        'source_line':inspect.getsourcelines(method)[1],'docstring':inspect.getdoc(method)},
            'results':c.rows,'exit_code':code},code


def main():
    parser=argparse.ArgumentParser(description=API+'：用户库按钮专项验收')
    parser.add_argument('--target-url',default=URL)
    parser.add_argument('--element-library',type=Path,default=LIBRARY)
    parser.add_argument('--wait-timeout',type=float,default=8)
    parser.add_argument('--dialog-observe-seconds',type=float,default=1)
    parser.add_argument('--contract-only',action='store_true')
    parser.add_argument('--json',action='store_true')
    parser.add_argument('--report-file',type=Path)
    args=parser.parse_args()
    if args.wait_timeout<0 or args.dialog_observe_seconds<0: parser.error('CLI 等待时间必须非负')
    if not args.json: print('UIAutoma Web API 测试\nAPI     : '+API+'\n页面    : '+args.target_url,flush=True)
    report,code=run(args)
    if args.report_file:
        args.report_file.parent.mkdir(parents=True,exist_ok=True)
        args.report_file.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    if args.json: print(json.dumps(report,ensure_ascii=False,indent=2))
    else:
        for i,row in enumerate(report['results'],1):
            color,label={'PASS':('\x1b[92m','通过'),'FAIL':('\x1b[91m','失败'),'KNOWN':('\x1b[93m','阻塞')}[row['status']]
            print(f"{i:02}/{len(report['results']):02} {color}[{label}]\x1b[0m {row['case_id']} 期望 {row['expected']}；实测 {row['actual']}；{row['elapsed_ms']}ms")
        passed=sum(r['status']=='PASS' for r in report['results'])
        print(f"{report['lifecycle']} · {passed}/{len(report['results'])} 通过 · 退出码 {code}")
    return code


if __name__=='__main__':
    raise SystemExit(main())
