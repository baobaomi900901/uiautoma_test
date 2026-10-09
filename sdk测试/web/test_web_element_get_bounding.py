"""WebElement.get_bounding 后台验收。

靶场：iframe-shadow-form；元素库：260902_web元素；目标：Ant 输入框。
期望值由真实 DOM 矩形和独立 Win32 原生窗口/网页客户区测量推导，
不读取被测 Runtime 的 geometry 元数据。当前原生窗口参考支持 96 DPI。
只对自有标签做滚动/样式干预；不激活窗口，不发送系统输入。
退出码 0 全通过、1 失败、2 环境阻塞；--contract-only 不启动浏览器。
"""
from __future__ import annotations

import argparse
import ctypes
from ctypes import wintypes
import hashlib
import inspect
import json
import math
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
PROVIDER = Path(r'D:\code\rust_uia')
sys.path.insert(0, str(PRODUCT/'sdk/src'))
sys.path.insert(0, str(ROOT/'web'))
from uiautoma import web, open as open_package, ping, InvalidParamsError, ActionError, HostUnavailableError
from uiautoma.web import WebElement
from test_web_element_get_select_options import copy_library, disable_dynamic_ids, find_switch

URL = 'https://baobaomi900901.github.io/xpath/#/iframe-shadow-form'
LIBRARY = Path(r'D:\code\元素库\260902_web元素')
NAME = 'web靶场_表单测试_ant_输入框'
CONTRACT = ROOT/'web/element_get_bounding_contract_20261008.json'
KEYS = ('x', 'y', 'width', 'height')
SCENES = ('baseline', 'top_scroll', 'iframe_scroll', 'translate_resize', 'negative_position')


class Blocked(Exception):
    pass


def require(ok, detail):
    if not ok:
        raise AssertionError(json.dumps(detail, ensure_ascii=False, default=str))
    return detail


def error(exc):
    return {'exception': type(exc).__name__, 'message': str(exc), 'trace': getattr(exc, 'trace_info', '')}


def raises(kind, fn, message='', trace=''):
    try:
        fn()
    except kind as exc:
        detail = error(exc)
        require((not message or message in detail['message']) and (not trace or trace == detail['trace']), detail)
        return detail
    raise AssertionError('Expected '+kind.__name__)


def source_commit(path):
    return subprocess.check_output(['git', '-C', str(path), 'rev-parse', 'HEAD'], text=True).strip()


def check_contract():
    frozen = json.loads(CONTRACT.read_text(encoding='utf-8'))
    require(str(inspect.signature(WebElement.get_bounding)) == frozen['signature'], str(inspect.signature(WebElement.get_bounding)))
    require(inspect.getsource(WebElement.get_bounding) == frozen['source'], 'SDK source changed; review contract')
    commits = {'desktop': source_commit(PRODUCT), 'rust_uia': source_commit(PROVIDER)}
    require(commits == frozen['commits'], {'expected': frozen['commits'], 'actual': commits})
    for snapshot in frozen['source_snapshots']:
        path = Path(snapshot['worktree'])/snapshot['path']
        require(hashlib.sha256(path.read_bytes()).hexdigest() == snapshot['sha256'], {'changed_source': str(path)})
    return {'signature': frozen['signature'], 'commits': commits, 'keys': list(KEYS)}


class NativeOracle:
    """Read-only ctypes channel; never calls SetForegroundWindow/ShowWindow/MoveWindow."""

    def __init__(self):
        self.u = ctypes.WinDLL('user32', use_last_error=True)
        self.k = ctypes.WinDLL('kernel32', use_last_error=True)
        self.cb = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
        prototypes = {
            'SetThreadDpiAwarenessContext': ([wintypes.HANDLE], wintypes.HANDLE),
            'GetForegroundWindow': ([], wintypes.HWND),
            'GetDpiForWindow': ([wintypes.HWND], wintypes.UINT),
            'GetWindowRect': ([wintypes.HWND, ctypes.POINTER(wintypes.RECT)], wintypes.BOOL),
            'GetClientRect': ([wintypes.HWND, ctypes.POINTER(wintypes.RECT)], wintypes.BOOL),
            'ClientToScreen': ([wintypes.HWND, ctypes.POINTER(wintypes.POINT)], wintypes.BOOL),
            'GetClassNameW': ([wintypes.HWND, wintypes.LPWSTR, ctypes.c_int], ctypes.c_int),
            'IsWindowVisible': ([wintypes.HWND], wintypes.BOOL),
            'GetWindowThreadProcessId': ([wintypes.HWND, ctypes.POINTER(wintypes.DWORD)], wintypes.DWORD),
            'EnumWindows': ([self.cb, wintypes.LPARAM], wintypes.BOOL),
            'EnumChildWindows': ([wintypes.HWND, self.cb, wintypes.LPARAM], wintypes.BOOL),
        }
        for name, (args, result) in prototypes.items():
            fn = getattr(self.u, name); fn.argtypes = args; fn.restype = result
        self.k.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
        self.k.OpenProcess.restype = wintypes.HANDLE
        self.k.QueryFullProcessImageNameW.argtypes = [wintypes.HANDLE, wintypes.DWORD, wintypes.LPWSTR, ctypes.POINTER(wintypes.DWORD)]
        self.k.QueryFullProcessImageNameW.restype = wintypes.BOOL
        self.k.CloseHandle.argtypes = [wintypes.HANDLE]; self.k.CloseHandle.restype = wintypes.BOOL
        self.old_dpi = self.u.SetThreadDpiAwarenessContext(wintypes.HANDLE(-4))
        if not self.old_dpi:
            raise Blocked('Cannot enable physical-coordinate measurements on test thread')

    def foreground(self):
        return int(self.u.GetForegroundWindow() or 0)

    def close(self):
        if self.old_dpi:
            self.u.SetThreadDpiAwarenessContext(self.old_dpi)
            self.old_dpi = None

    def info(self, hwnd):
        name = ctypes.create_unicode_buffer(256)
        self.u.GetClassNameW(hwnd, name, len(name))
        rect, client, point = wintypes.RECT(), wintypes.RECT(), wintypes.POINT()
        if not (self.u.GetWindowRect(hwnd, ctypes.byref(rect)) and self.u.GetClientRect(hwnd, ctypes.byref(client)) and self.u.ClientToScreen(hwnd, ctypes.byref(point))):
            raise Blocked('Native window changed during measurement')
        return {'hwnd': int(hwnd), 'class': name.value, 'rect': {'x': rect.left, 'y': rect.top, 'width': rect.right-rect.left, 'height': rect.bottom-rect.top}, 'client_origin': {'x': point.x, 'y': point.y}, 'client_size': {'width': client.right-client.left, 'height': client.bottom-client.top}, 'dpi': int(self.u.GetDpiForWindow(hwnd))}

    def is_chrome(self, hwnd):
        pid = wintypes.DWORD(); self.u.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        handle = self.k.OpenProcess(0x1000, False, pid.value)
        if not handle:
            return False
        try:
            path = ctypes.create_unicode_buffer(32768); size = wintypes.DWORD(len(path))
            return bool(self.k.QueryFullProcessImageNameW(handle, 0, path, ctypes.byref(size))) and Path(path.value).name.casefold() == 'chrome.exe'
        finally:
            self.k.CloseHandle(handle)

    def measure(self, dom):
        matches, callback_errors = [], []

        def each(hwnd, _):
            try:
                if not self.u.IsWindowVisible(hwnd) or not self.is_chrome(hwnd):
                    return True
                row = self.info(hwnd)
                if row['class'] != 'Chrome_WidgetWin_1':
                    return True
                # Current reference is explicitly limited to a 96-DPI Chrome window.
                if row['dpi'] != 96 or any(abs(row['rect'][key]-dom['window'][key]) > 1 for key in KEYS):
                    return True
                children = []

                def child(ch, _):
                    try:
                        item = self.info(ch)
                        if item['class'] == 'Chrome_RenderWidgetHostHWND' and self.u.IsWindowVisible(ch) and all(abs(item['client_size'][key]-dom['inner'][key]*dom['dpr']) <= 1 for key in ('width', 'height')):
                            children.append(item)
                    except Exception as exc:
                        callback_errors.append(error(exc))
                    return True

                self.u.EnumChildWindows(hwnd, self.cb(child), 0)
                if len(children) == 1:
                    row['viewport'] = children[0]; matches.append(row)
            except Exception as exc:
                callback_errors.append(error(exc))
            return True

        self.u.EnumWindows(self.cb(each), 0)
        if len(matches) != 1:
            raise Blocked(json.dumps({'reason': 'Cannot uniquely identify 96-DPI native Chrome window and viewport', 'matches': matches, 'callback_errors': callback_errors, 'dom_window': dom['window']}, ensure_ascii=False))
        return matches[0]


class Run:
    def __init__(self, args):
        self.args = args; self.rows = []; self.page = None; self.package = None; self.element = None; self.oracle = None
        self.baseline = None; self.id = None; self.library_hash = None; self.previous = None; self.storage_before = None; self.original = None
        self.tmp = ROOT/'.pytest_tmp/bounding_live'/uuid.uuid4().hex
        self.total = 7 if args.contract_only else 38

    def case(self, name, expected, fn):
        start = time.perf_counter()
        try:
            actual = fn(); status = 'PASS'
        except Exception as exc:
            actual = error(exc)
            status = 'BLOCKED' if isinstance(exc, Blocked) or type(exc).__name__ in {'HostUnavailableError', 'ConnectionError'} or getattr(exc, 'trace_info', '') == 'uiautomation_provider_unavailable' else 'FAIL'
        row = {'case_id': name, 'status': status, 'expected': expected, 'actual': actual, 'elapsed_ms': round((time.perf_counter()-start)*1000, 1)}
        self.rows.append(row)
        display = actual
        if isinstance(actual, dict) and 'native' in actual and 'bounding' in actual:
            display = {key: actual[key] for key in ('bounding', 'expected_rect', 'difference', 'dpi', 'dpr', 'scroll', 'foreground_unchanged')}
        color, label = {'PASS': ('\x1b[32m', '通过'), 'FAIL': ('\x1b[31m', '失败'), 'BLOCKED': ('\x1b[33m', '阻塞')}[status]
        print(f"{len(self.rows):02d}/{self.total:02d} {color}[{label}]\x1b[0m {name} 期望 {expected}；实测 {json.dumps(display, ensure_ascii=False, default=str)}；{row['elapsed_ms']}ms", flush=True)
        return status

    def js(self, body, arg=None):
        return self.page.execute_javascript("function(_e,a){const f=document.querySelector('#iframe-shadow-form');const root=f.contentDocument.querySelector('#form-shadow-host').shadowRoot;const e=root.getElementById('form-controls-ant-text');"+body+'}', arg)

    def observe(self):
        return self.js("""
          const q=f.getBoundingClientRect(),r=e.getBoundingClientRect();
          return {id:e.id,tag:e.tagName,rect:{x:q.x+f.clientLeft+r.x,y:q.y+f.clientTop+r.y,width:r.width,height:r.height},
            inner:{width:innerWidth,height:innerHeight},window:{x:screenX,y:screenY,width:outerWidth,height:outerHeight},dpr:devicePixelRatio,
            scroll:{top_x:scrollX,top_y:scrollY,frame_x:f.contentWindow.scrollX,frame_y:f.contentWindow.scrollY},
            value:e.value,focus:{top:document.activeElement?.id||'',shadow:root.activeElement?.id||''},style:e.getAttribute('style'),frame_style:f.getAttribute('style')};
        """)

    def setup(self):
        ping(timeout=5)
        if not self.args.library.is_dir():
            raise Blocked('元素库目录不存在')
        self.oracle = NativeOracle()
        self.library_hash = hashlib.sha256((self.args.library/'elements.json').read_bytes()).hexdigest()
        self.baseline = {p._page_ref['id'] for p in web.get_all(mode='chrome')}
        copy_library(self.args.library, self.tmp/'library')
        self.package = open_package(str(self.tmp/'library'), timeout=8, connect_timeout=8)
        self.page = web.create(self.args.url, mode='chrome', silent_running=True, load_timeout=25)
        self.id = self.page._page_ref['id']
        self.storage_before = self.js("return localStorage.getItem('form-controls-dynamic-ids');")
        self.previous = disable_dynamic_ids(self.page)
        self.original = self.stable()
        return {'url': self.page.get_url(), 'library': str(self.args.library), 'silent_running': True, 'baseline_tabs': len(self.baseline)}

    def mapping(self):
        matches = self.page.find_all(self.args.element, timeout=5)
        require(len(matches) == 1, {'name': self.args.element, 'matches': len(matches)})
        self.element = matches[0]
        actual = {'name': self.args.element, 'matches': len(matches), 'id': self.element.get_attribute('id'), 'tag': self.observe()['tag']}
        return require(actual['id'] == 'form-controls-ant-text' and actual['tag'] == 'INPUT', actual)

    def restore(self):
        if not self.original:
            return None
        return self.js("if(a.style===null)e.removeAttribute('style');else e.setAttribute('style',a.style);if(a.frame_style===null)f.removeAttribute('style');else f.setAttribute('style',a.frame_style);window.scrollTo({left:a.scroll.top_x,top:a.scroll.top_y,behavior:'instant'});f.contentWindow.scrollTo({left:a.scroll.frame_x,top:a.scroll.frame_y,behavior:'instant'});return true;", self.original)

    def stable(self):
        end = time.monotonic()+3
        previous = self.observe(); count = 0
        while time.monotonic() < end:
            time.sleep(.05)
            current = self.observe()
            count = count+1 if current == previous else 0
            if count >= 2:
                return current
            previous = current
        raise Blocked('DOM layout did not settle: '+json.dumps(previous, ensure_ascii=False))

    def prepare(self, scene):
        self.restore()
        if scene == 'top_scroll':
            self.js("f.style.setProperty('height',Math.max(1300,innerHeight+400)+'px','important');window.scrollTo({top:60,left:0,behavior:'instant'});return true;")
        elif scene == 'iframe_scroll':
            self.js("f.contentWindow.scrollTo({top:73,left:0,behavior:'instant'});return true;")
        elif scene == 'translate_resize':
            self.js("e.style.setProperty('transition','none','important');e.style.setProperty('animation','none','important');e.getAnimations().forEach(a=>a.cancel());e.style.transform='translate(13.25px,17.75px)';e.style.boxSizing='border-box';e.style.width='237.5px';e.style.height='37.5px';return true;")
        elif scene == 'negative_position':
            self.js("e.style.setProperty('transition','none','important');e.style.setProperty('animation','none','important');e.getAnimations().forEach(a=>a.cancel());e.style.transform='translate(-200.25px,-550.75px)';return true;")
        before = self.stable()
        if scene == 'top_scroll':
            require(before['scroll']['top_y'] > self.original['scroll']['top_y'], before)
        if scene == 'iframe_scroll':
            require(before['scroll']['frame_y'] > self.original['scroll']['frame_y'], before)
        if scene == 'translate_resize':
            require(before['rect']['width'] == 237.5 and before['rect']['height'] == 37.5, before)
        if scene == 'negative_position':
            require(before['rect']['x'] < 0 and before['rect']['y'] < 0, before)
        return before

    def measurement(self, scene='baseline', normal=True, relative='screen', call='explicit'):
        before = self.prepare(scene)
        native = self.oracle.measure(before)
        foreground = self.oracle.foreground()
        if call == 'default':
            actual = self.element.get_bounding()
        elif call == 'positional':
            actual = self.element.get_bounding(normal, relative)
        else:
            actual = self.element.get_bounding(to96dpi=normal, relative_to=relative)
        after = self.observe(); native_after = self.oracle.measure(after); foreground_after = self.oracle.foreground()
        if before != after or native != native_after:
            raise Blocked(json.dumps({'reason': 'DOM/native geometry moved during read', 'before': before, 'after': after, 'native_before': native, 'native_after': native_after}, ensure_ascii=False))
        factor = 96/native['dpi'] if normal else 1
        physical = {key: math.floor(before['rect'][key]*before['dpr']+.5) for key in KEYS}
        for key in ('x', 'y'):
            physical[key] += native['viewport']['client_origin'][key]
            if relative == 'window':
                physical[key] -= native['client_origin'][key]
        expected = {key: math.floor(physical[key]*factor+.5) for key in KEYS}
        difference = {key: actual.get(key, None)-expected[key] if isinstance(actual, dict) and type(actual.get(key)) is int else None for key in KEYS}
        detail = {'bounding': actual, 'expected_rect': expected, 'difference': difference, 'dpi': native['dpi'], 'dpr': before['dpr'], 'scroll': before['scroll'], 'foreground_unchanged': foreground == foreground_after, 'foreground_before': foreground, 'foreground_after': foreground_after, 'native': native, 'dom_before': before, 'dom_after': after, 'scene': scene, 'relative_to': relative, 'to96dpi': normal}
        require(isinstance(actual, dict) and set(actual) == set(KEYS) and all(type(actual[key]) is int for key in KEYS), detail)
        require(all(value == 0 for value in difference.values()), detail)
        # Foreground changes by the user are recorded, not blamed on the API.
        if foreground != native['hwnd'] and foreground_after == native['hwnd']:
            raise Blocked(json.dumps({'reason': 'Test Chrome became foreground during geometry call', **detail}, ensure_ascii=False))
        return detail

    def readonly(self):
        self.restore(); before = self.stable()
        values = [self.element.get_bounding(False, 'window') for _ in range(3)]
        after = self.observe()
        return require(before == after and all(v == values[0] for v in values), {'values': values, 'dom_scroll_value_focus_style_unchanged': before == after})

    def restore_case(self):
        self.restore(); after = self.stable()
        return require(after == self.original, {'restored': after == self.original, 'actual': after})

    def restore_preference(self):
        if self.previous == 'true':
            find_switch(self.page).click(simulative=False, delay_after=0)
        self.js("if(a===null)localStorage.removeItem('form-controls-dynamic-ids');else localStorage.setItem('form-controls-dynamic-ids',a);return true;", self.storage_before)
        actual = self.js("return localStorage.getItem('form-controls-dynamic-ids');")
        switched = find_switch(self.page).get_attribute('aria-checked')
        return require(actual == self.storage_before and switched == self.previous, {'expected_storage': self.storage_before, 'actual_storage': actual, 'expected_switch': self.previous, 'actual_switch': switched})

    def closed_page(self):
        self.page.close(ignore_beforeunload=True)
        return raises(ActionError, lambda: self.element.get_bounding(), trace='stale_page_reference')

    def closed_package(self):
        self.package.close()
        return raises(HostUnavailableError, lambda: self.element.get_bounding(), '连接已关闭')

    def cleanup(self):
        errors = []
        if self.page:
            try:
                ids = {p._page_ref['id'] for p in web.get_all(mode='chrome')}
                if self.id in ids:
                    self.restore()
                    if self.previous == 'true':
                        find_switch(self.page).click(simulative=False, delay_after=0)
                    self.js("if(a===null)localStorage.removeItem('form-controls-dynamic-ids');else localStorage.setItem('form-controls-dynamic-ids',a);return true;", self.storage_before)
                    self.page.close(ignore_beforeunload=True)
            except Exception as exc:
                errors.append(error(exc))
        if self.package:
            try:
                self.package.close()
            except Exception as exc:
                errors.append(error(exc))
        if self.tmp.exists():
            require(self.tmp.resolve().parent == (ROOT/'.pytest_tmp/bounding_live').resolve(), 'Unexpected cleanup path')
            shutil.rmtree(self.tmp)
        after = {p._page_ref['id'] for p in web.get_all(mode='chrome')} if self.baseline is not None else set()
        unchanged = self.library_hash is None or hashlib.sha256((self.args.library/'elements.json').read_bytes()).hexdigest() == self.library_hash
        if self.oracle:
            self.oracle.close()
        detail = {'errors': errors, 'own_tab_closed': self.id not in after, 'temporary_copy_removed': not self.tmp.exists(), 'source_library_unchanged': unchanged, 'tab_count': f'{len(self.baseline or set())}->{len(after)}', 'external_added': sorted(after-(self.baseline or set())), 'external_removed': sorted((self.baseline or set())-after)}
        return require(not errors and detail['own_tab_closed'] and detail['temporary_copy_removed'] and unchanged and not detail['external_added'] and not detail['external_removed'], detail)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--url', default=URL)
    parser.add_argument('--library', type=Path, default=LIBRARY)
    parser.add_argument('--element', default=NAME)
    parser.add_argument('--contract-only', action='store_true')
    parser.add_argument('--json', action='store_true', help='报告结束后输出完整 JSON')
    parser.add_argument('--report-file', type=Path)
    args = parser.parse_args(argv); run = Run(args)
    print('UIAutoma Web API 测试\nAPI     : uiautoma.web.WebElement.get_bounding\n页面    : '+args.url, flush=True)
    good = run.case('api_contract', '签名、默认值、源码及两仓库只读 commit 与冻结合同一致', check_contract) == 'PASS'
    for name, value in [('invalid_reference', 'bad'), ('blank_reference', ''), ('case_sensitive_reference', 'SCREEN'), ('none_reference', None)]:
        run.case(name, 'SDK 立即抛 InvalidParamsError / relative_to 必须是 screen 或 window', lambda value=value: raises(InvalidParamsError, lambda: WebElement.get_bounding(object(), relative_to=value), 'relative_to 必须是 screen 或 window'))
    run.case('extra_positional', '多余位置参数抛 TypeError', lambda: raises(TypeError, lambda: WebElement.get_bounding(object(), True, 'screen', 1)))
    run.case('unknown_keyword', '未知关键字抛 TypeError', lambda: raises(TypeError, lambda: WebElement.get_bounding(object(), unknown=True)))
    if not args.contract_only and good:
        try:
            if run.case('environment', 'Runtime、静默自有页面与临时库可用', run.setup) == 'PASS':
                if run.case('library_mapping', '指定库元素唯一命中 Ant input', run.mapping) == 'PASS':
                    run.case('native_oracle', 'Win32 独立唯一识别 Chrome 主窗口及网页 viewport；记录 DPI', lambda: run.oracle.measure(run.observe()))
                    run.case('default', '默认 screen/96 DPI，四个整数与独立坐标完全相同', lambda: run.measurement(call='default'))
                    for scene in SCENES:
                        for relative in ('screen', 'window'):
                            for normal in (False, True):
                                run.case(f'{scene}_{relative}_{normal}', '四个整数与 DOM + Win32 独立推导完全相同，读取不滚动', lambda scene=scene, relative=relative, normal=normal: run.measurement(scene, normal, relative))
                    run.case('positional_arguments', '两个可选参数可按位置传入，window 物理矩形正确', lambda: run.measurement(normal=False, relative='window', call='positional'))
                    run.case('readonly_repeat', '连读三次相同；滚动、value、focus、style 不变', run.readonly)
                    run.case('restore_scene', '自有页面样式/滚动恢复到进入时值', run.restore_case)
                    run.case('restore_preference', '动态 ID 开关和站点 localStorage 精确恢复', run.restore_preference)
                    run.case('closed_page', '关闭自有页面后抛 ActionError / stale_page_reference', run.closed_page)
                    run.case('closed_package', '关闭库连接后抛 HostUnavailableError / 连接已关闭', run.closed_package)
        finally:
            run.case('cleanup', '自有页面/库、副本已清理；源库、外部标签不变', run.cleanup)
    code = 1 if any(r['status'] == 'FAIL' for r in run.rows) else 2 if any(r['status'] == 'BLOCKED' for r in run.rows) else 0
    report = {'api': 'uiautoma.web.WebElement.get_bounding', 'date': '2026-10-08', 'lifecycle': 'VERIFIED' if code == 0 and not args.contract_only and len(run.rows) == run.total else 'READY_FOR_LIVE', 'scope': 'background Chrome, iframe/open Shadow Ant input, native window DPI=96; higher native DPI not verified', 'worktrees': {'desktop': str(PRODUCT), 'rust_uia': str(PROVIDER)}, 'commits': {'desktop': source_commit(PRODUCT), 'rust_uia': source_commit(PROVIDER)}, 'url': args.url, 'library': str(args.library), 'element': args.element, 'results': run.rows, 'exit_code': code}
    if args.report_file:
        args.report_file.parent.mkdir(parents=True, exist_ok=True)
        args.report_file.write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    passed = sum(r['status'] == 'PASS' for r in run.rows)
    print(f"{'测试通过' if code == 0 else '测试失败' if code == 1 else '测试阻塞'} · {passed}/{len(run.rows)} 通过 · 退出码 {code}", flush=True)
    return code


if __name__ == '__main__':
    raise SystemExit(main())
