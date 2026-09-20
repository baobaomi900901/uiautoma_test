"""WebElement.dblclick() 独立验收：keys-click-test + 260902_web元素。

VERIFIED：2026-09-20 用户完整实测 41/41 通过，退出码 0；清理时原前台恢复有警告。
目标：web靶场_测试点击_双击触发；复制：web靶场_测试点击_读取最近一条点击记录。
独立参照：DOM 事件顺序 click/click/dblclick + 原生 CF_UNICODETEXT 读取靶场 JSON。
源码快照 D:/code/desktop @ c101caa9dcd115a461fc71ecaed351b0dea880b8（2026-09-20）。
只依赖标准库和 uiautoma，不导入其他测试脚本；原有 test_web_element_dblclick.py 保留。
仅操作本次页面和元素库副本；保存并恢复支持的剪贴板格式、鼠标和原前台。
运行期间请勿操作键鼠；双击动作不自动重试，复制最多重试一次。
退出码：0 通过，1 检查失败，2 环境阻塞。
"""
from __future__ import annotations

import argparse
import ctypes
from ctypes import wintypes
import inspect
import json
import math
from pathlib import Path
import shutil
import tempfile
import time
from urllib.parse import urlsplit, urlunsplit
import uuid

import uiautoma
from uiautoma import InvalidParamsError, web
from uiautoma.web import WebBrowser, WebElement
from uiautoma.win32 import clipboard

__test__ = False
URL = 'https://baobaomi900901.github.io/xpath/#/keys-click-test'
LIBRARY = Path(r'D:\code\元素库\260902_web元素')
PREFIX = 'web靶场_测试点击_'
TARGETS = {
    'double': ('双击触发', 'btn-dblclick-target'),
    'copy': ('读取最近一条点击记录', 'btn-copy-latest-keys-log'),
}
COLORS = {'PASS': '\x1b[92m', 'FAIL': '\x1b[91m', 'BLOCKED': '\x1b[93m'}

# 仅监听和读 DOM；clear/scroll/blur 是用例准备，不制造被测点击事件。
PROBE = """function (element, arg) {
  const ids = ['btn-dblclick-target'];
  const need = id => {
    const all = document.querySelectorAll('[id="' + id + '"]');
    if (all.length !== 1) throw new Error(id + ': expected one DOM element, got ' + all.length);
    return all[0];
  };
  const rows = () => Array.from(document.querySelectorAll('#keys-click-log tbody tr[data-row-key]'))
    .map(row => ({key: row.getAttribute('data-row-key'), text: row.innerText}));
  const snapshot = () => ({events: window[arg.key].events.slice(), rows: rows(),
    activeId: document.activeElement && document.activeElement.id,
    documentFocused: document.hasFocus(), visibility: document.visibilityState});
  if (arg.op === 'install') {
    if (window[arg.key]) throw new Error('observer key already exists');
    ids.concat(['btn-copy-latest-keys-log','btn-clear-keys-log']).forEach(need);
    const state = {events: [], armed: false, types: ['click','dblclick','contextmenu']};
    state.listen = event => {
      if (!state.armed || !(event.target instanceof Element)) return;
      const root = event.target.closest(ids.map(id => '#' + id).join(','));
      if (!root) return;
      const r = root.getBoundingClientRect();
      state.events.push({buttonId: root.id, type: event.type, button: event.button, detail: event.detail,
        keys: [['alt',event.altKey],['ctrl',event.ctrlKey],['shift',event.shiftKey],['win',event.metaKey]]
          .filter(pair => pair[1]).map(pair => pair[0]).join('+') || 'none',
        trusted: event.isTrusted, x: event.clientX - r.left, y: event.clientY - r.top,
        width: r.width, height: r.height, offsetX: Math.round(event.offsetX), offsetY: Math.round(event.offsetY)});
      if (state.events.length > 100) state.events.shift();
    };
    window[arg.key] = state;
    state.types.forEach(type => document.addEventListener(type, state.listen, true));
    return ids.map(id => ({id, tag: need(id).tagName}));
  }
  const state = window[arg.key];
  if (!state) {
    if (arg.op === 'remove') return true;
    throw new Error('event observer missing');
  }
  if (arg.op === 'prepare') {
    state.armed = false;
    if (document.activeElement && document.activeElement.blur) document.activeElement.blur();
    const clear = need('btn-clear-keys-log');
    if (!clear.disabled) clear.click();
    need(arg.id).scrollIntoView({block:'center', inline:'center', behavior:'instant'});
    return true;
  }
  if (arg.op === 'ready') {
    const r = need(arg.id).getBoundingClientRect();
    return {rows: rows(), visible: r.width > 0 && r.height > 0 && r.top >= 0 && r.left >= 0 &&
      r.bottom <= innerHeight && r.right <= innerWidth, width: r.width, height: r.height};
  }
  if (arg.op === 'arm') { state.events = []; state.armed = true; return snapshot(); }
  if (arg.op === 'read') return snapshot();
  if (arg.op === 'remove') {
    state.types.forEach(type => document.removeEventListener(type, state.listen, true));
    delete window[arg.key];
    return !Object.prototype.hasOwnProperty.call(window, arg.key);
  }
  throw new Error('unknown observer operation');
}"""


class Blocked(RuntimeError):
    pass


def error_detail(exc):
    text = f'{type(exc).__name__}: {exc}'
    for attr in ('trace_info', 'trace_id'):
        value = getattr(exc, attr, None)
        if value:
            text += f' [{attr}={value}]'
    return text


def record_case(rows, name, action):
    started = time.perf_counter()
    try:
        detail, status = action(), 'PASS'
    except Exception as exc:
        detail = error_detail(exc)
        status = 'BLOCKED' if isinstance(exc, Blocked) else 'FAIL'
    rows.append(dict(case_id=name, status=status, detail=detail,
                     elapsed_ms=(time.perf_counter() - started) * 1000))
    return status == 'PASS'


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def contract():
    signature = inspect.signature(WebElement.dblclick)
    expected = dict(simulative=True, delay_after=1, move_mouse=False, anchor=None)
    require(tuple(signature.parameters) == ('self', *expected), f'签名不符: {signature}')
    for name, default in expected.items():
        param = signature.parameters[name]
        require(param.kind == inspect.Parameter.KEYWORD_ONLY and param.default == default
                and type(param.default) is type(default),
                f'{name} 预期关键字参数、默认 {default!r}；实际 {param}')
    require(str(signature.return_annotation) in ('None', "<class 'NoneType'>"), f'返回注解不符: {signature}')
    return '四个参数仅限关键字，默认值与源码一致；返回 None；不接受 button/keys/timeout'


class NativeState:
    """剪贴板独立读取；进入时复制实际数据，不跨用例持有 OLE 代理。"""
    MODIFIERS = (('shift', 0x10), ('ctrl', 0x11), ('alt', 0x12), ('lwin', 0x5B), ('rwin', 0x5C))
    MEMORY_FORMATS = {1, 7, 8, 13, 15, 16, 17}
    NAMED_MEMORY_FORMATS = {'HTML Format', 'Rich Text Format', 'Rich Text Format Without Objects', 'PNG'}
    EPHEMERAL_FORMAT_PREFIX = 'Chromium internal source '

    def __init__(self):
        self.user = ctypes.WinDLL('user32', use_last_error=True)
        self.kernel = ctypes.WinDLL('kernel32', use_last_error=True)
        self.saved = None
        self.ignored_formats = []
        self.captured = self.modified = False
        self.last_physical_click = 0.0
        for name, args, rest in (
            ('OpenClipboard', [wintypes.HWND], wintypes.BOOL),
            ('CloseClipboard', [], wintypes.BOOL),
            ('IsClipboardFormatAvailable', [wintypes.UINT], wintypes.BOOL),
            ('GetClipboardData', [wintypes.UINT], wintypes.HANDLE),
            ('EnumClipboardFormats', [wintypes.UINT], wintypes.UINT),
            ('GetClipboardFormatNameW', [wintypes.UINT, wintypes.LPWSTR, ctypes.c_int], ctypes.c_int),
            ('EmptyClipboard', [], wintypes.BOOL),
            ('SetClipboardData', [wintypes.UINT, wintypes.HANDLE], wintypes.HANDLE),
            ('CreateWindowExW', [wintypes.DWORD, wintypes.LPCWSTR, wintypes.LPCWSTR, wintypes.DWORD,
                                 ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int,
                                 wintypes.HWND, wintypes.HMENU, wintypes.HINSTANCE, ctypes.c_void_p], wintypes.HWND),
            ('DestroyWindow', [wintypes.HWND], wintypes.BOOL),
            ('GetCursorPos', [ctypes.POINTER(wintypes.POINT)], wintypes.BOOL),
            ('SetCursorPos', [ctypes.c_int, ctypes.c_int], wintypes.BOOL),
            ('GetForegroundWindow', [], wintypes.HWND),
            ('SetForegroundWindow', [wintypes.HWND], wintypes.BOOL),
            ('IsWindow', [wintypes.HWND], wintypes.BOOL),
            ('GetWindowThreadProcessId', [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)], wintypes.DWORD),
            ('GetClassNameW', [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int], ctypes.c_int),
            ('GetAsyncKeyState', [ctypes.c_int], ctypes.c_short),
            ('GetDoubleClickTime', [], wintypes.UINT),
            ('keybd_event', [wintypes.BYTE, wintypes.BYTE, wintypes.DWORD, ctypes.c_size_t], None),
        ):
            fn = getattr(self.user, name)
            fn.argtypes, fn.restype = args, rest
        for name, args, rest in (
            ('GlobalLock', [wintypes.HGLOBAL], ctypes.c_void_p),
            ('GlobalUnlock', [wintypes.HGLOBAL], wintypes.BOOL),
            ('GlobalSize', [wintypes.HGLOBAL], ctypes.c_size_t),
            ('GlobalAlloc', [wintypes.UINT, ctypes.c_size_t], wintypes.HGLOBAL),
            ('GlobalFree', [wintypes.HGLOBAL], wintypes.HGLOBAL),
            ('GetModuleHandleW', [wintypes.LPCWSTR], wintypes.HMODULE),
            ('OpenProcess', [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD], wintypes.HANDLE),
            ('QueryFullProcessImageNameW', [wintypes.HANDLE, wintypes.DWORD, wintypes.LPWSTR,
                                          ctypes.POINTER(wintypes.DWORD)], wintypes.BOOL),
            ('CloseHandle', [wintypes.HANDLE], wintypes.BOOL),
        ):
            fn = getattr(self.kernel, name)
            fn.argtypes, fn.restype = args, rest
        self.cursor = wintypes.POINT()
        require(self.user.GetCursorPos(ctypes.byref(self.cursor)), 'GetCursorPos 失败')
        self.foreground = self.user.GetForegroundWindow()

    def held_keys(self):
        return [name for name, vk in self.MODIFIERS if self.user.GetAsyncKeyState(vk) & 0x8000]

    def window_info(self, handle=None):
        handle = int((self.user.GetForegroundWindow() if handle is None else handle) or 0)
        result = dict(handle=handle, pid=0, process='', class_name='')
        if not handle or not self.user.IsWindow(handle):
            return result
        pid = wintypes.DWORD()
        self.user.GetWindowThreadProcessId(handle, ctypes.byref(pid))
        name = ctypes.create_unicode_buffer(256)
        self.user.GetClassNameW(handle, name, len(name))
        result.update(pid=pid.value, class_name=name.value)
        process = self.kernel.OpenProcess(0x1000, False, pid.value)
        if process:
            try:
                image = ctypes.create_unicode_buffer(32768)
                size = wintypes.DWORD(len(image))
                if self.kernel.QueryFullProcessImageNameW(process, 0, image, ctypes.byref(size)):
                    result['process'] = Path(image.value).name
            finally:
                self.kernel.CloseHandle(process)
        return result

    def restore_browser_foreground(self, target):
        actual = self.window_info(target['handle'])
        if (actual != target or not target['pid'] or
                target['process'].lower() not in ('chrome.exe', 'msedge.exe')):
            raise Blocked(f'原测试浏览器窗口已失效或身份改变: {actual!r}')
        require(not self.held_keys(), '焦点恢复前辅助键仍按下')
        activated = bool(self.user.SetForegroundWindow(target['handle']))
        return f'SetForegroundWindow={activated}（仍需 DOM 焦点核验）'

    def get_cursor(self):
        point = wintypes.POINT()
        require(self.user.GetCursorPos(ctypes.byref(point)), 'GetCursorPos 失败')
        return point.x, point.y

    def open_clipboard(self, owner=None):
        for _ in range(30):
            if self.user.OpenClipboard(owner):
                return
            time.sleep(0.05)
        raise Blocked('剪贴板持续被占用，无法打开')

    def read_text(self):
        self.open_clipboard()
        try:
            if not self.user.IsClipboardFormatAvailable(13):
                return None
            handle = self.user.GetClipboardData(13)
            size = self.kernel.GlobalSize(handle)
            if not handle or not 0 < size <= 8 * 1024 * 1024:
                raise Blocked(f'Unicode 剪贴板数据无效或过大: {size}')
            pointer = self.kernel.GlobalLock(handle)
            if not pointer:
                raise Blocked('GlobalLock 剪贴板失败')
            try:
                return ctypes.string_at(pointer, size).decode('utf-16-le').split('\0', 1)[0]
            finally:
                self.kernel.GlobalUnlock(handle)
        finally:
            self.user.CloseClipboard()

    def snapshot_clipboard(self):
        self.open_clipboard()
        try:
            result, fmt, total = {}, 0, 0
            while True:
                ctypes.set_last_error(0)
                fmt = self.user.EnumClipboardFormats(fmt)
                if not fmt:
                    require(ctypes.get_last_error() == 0, '剪贴板格式枚举失败')
                    return result
                name = ctypes.create_unicode_buffer(256)
                self.user.GetClipboardFormatNameW(fmt, name, len(name))
                if name.value.startswith(self.EPHEMERAL_FORMAT_PREFIX):
                    self.ignored_formats.append(f'{fmt} ({name.value})')
                    continue
                if fmt not in self.MEMORY_FORMATS and name.value not in self.NAMED_MEMORY_FORMATS:
                    raise Blocked(f'剪贴板格式 {fmt} ({name.value}) 暂不支持无损快照；原内容未改动')
                handle = self.user.GetClipboardData(fmt)
                size = self.kernel.GlobalSize(handle)
                total += size
                if not handle or not 0 < size <= 32 * 1024 * 1024 or total > 64 * 1024 * 1024:
                    raise Blocked(f'剪贴板格式 {fmt} 数据无法完整复制；原内容未改动')
                pointer = self.kernel.GlobalLock(handle)
                require(bool(pointer), f'格式 {fmt} GlobalLock 失败')
                try:
                    result[fmt] = ctypes.string_at(pointer, size)
                finally:
                    self.kernel.GlobalUnlock(handle)
        finally:
            self.user.CloseClipboard()

    def write_snapshot(self, snapshot):
        pending, owner, opened = {}, None, False
        try:
            # 在清空剪贴板前准备全部数据块；转交给系统的句柄不再自行释放。
            for fmt, data in snapshot.items():
                handle = self.kernel.GlobalAlloc(0x42, len(data))  # MOVEABLE | ZEROINIT
                require(bool(handle), f'格式 {fmt} 分配恢复数据失败')
                pending[fmt] = handle
                pointer = self.kernel.GlobalLock(handle)
                require(bool(pointer), f'格式 {fmt} 锁定恢复数据失败')
                try:
                    ctypes.memmove(pointer, data, len(data))
                finally:
                    self.kernel.GlobalUnlock(handle)
            # message-only 隐藏窗口为 EmptyClipboard/SetClipboardData 提供有效 owner。
            owner = self.user.CreateWindowExW(0, 'STATIC', 'uiautoma-clipboard-restore', 0,
                0, 0, 0, 0, wintypes.HWND(-3), None, self.kernel.GetModuleHandleW(None), None)
            require(bool(owner), '创建剪贴板恢复 owner 失败')
            self.open_clipboard(owner)
            opened = True
            require(self.user.EmptyClipboard(), '恢复时清空剪贴板失败')
            for fmt in list(pending):
                require(bool(self.user.SetClipboardData(fmt, pending[fmt])), f'恢复格式 {fmt} 失败')
                del pending[fmt]
        finally:
            if opened:
                self.user.CloseClipboard()
            for handle in pending.values():
                self.kernel.GlobalFree(handle)
            if owner:
                self.user.DestroyWindow(owner)

    def capture(self):
        if self.held_keys():
            raise Blocked(f'请释放辅助键后重跑: {self.held_keys()}')
        self.saved = self.snapshot_clipboard()
        self.captured = True
        ignored = f'；忽略已知 Chromium 临时格式 {self.ignored_formats}' if self.ignored_formats else ''
        return (f'已复制原剪贴板 {len(self.saved)} 个格式的实际数据{ignored}，'
                '记录鼠标和前台；辅助键均未按下')

    def sentinel(self):
        require(self.captured, '未保存剪贴板，不允许覆盖')
        self.modified = True
        value = 'uiautoma-dblclick-' + uuid.uuid4().hex
        clipboard.set_text(value)
        require(self.read_text() == value, '剪贴板哨兵写入与独立读回不一致')
        return value

    def park(self):
        require(self.user.SetCursorPos(0, 0), '测试准备移动鼠标失败')

    def separate_double_clicks(self):
        remaining = self.user.GetDoubleClickTime() / 1000 + 0.05 - (time.monotonic() - self.last_physical_click)
        if remaining > 0:
            time.sleep(remaining)

    def restore(self):
        if not self.modified:
            return '本次尚未改动剪贴板，无需恢复'
        require(self.captured and self.saved is not None, '缺少剪贴板实际数据快照')
        self.write_snapshot(self.saved)
        actual = self.snapshot_clipboard()
        for fmt, data in self.saved.items():
            require(fmt in actual and actual[fmt][:len(data)] == data,
                    f'恢复后的剪贴板格式 {fmt} 数据不一致')
        if not self.saved:
            require(not actual, '原剪贴板为空，恢复后仍含数据')
        return f'原剪贴板 {len(self.saved)} 个格式已恢复并逐项读回核验（包括原文本/HTML，如有）'

    def restore_input(self):
        # 测试开始要求辅助键全松开；只释放本轮仍按下的辅助键。
        for _, vk in self.MODIFIERS:
            if self.user.GetAsyncKeyState(vk) & 0x8000:
                self.user.keybd_event(vk, 0, 2, 0)
        require(not self.held_keys(), f'辅助键未释放: {self.held_keys()}')
        require(self.user.SetCursorPos(self.cursor.x, self.cursor.y), '鼠标恢复失败')
        now = wintypes.POINT()
        require(self.user.GetCursorPos(ctypes.byref(now)) and (now.x, now.y) == (self.cursor.x, self.cursor.y),
                '鼠标恢复后坐标不符')
        restored = bool(self.user.SetForegroundWindow(self.foreground)) if self.foreground else False
        return '辅助键已释放、鼠标位置已恢复；' + ('前台已恢复' if restored and self.user.GetForegroundWindow() == self.foreground else '前台未恢复（警告）')


def probe(page, key, op, **extra):
    return page.execute_javascript(PROBE, dict(key=key, op=op, **extra))


def wait_for(read, accept, seconds, description):
    deadline, last = time.monotonic() + seconds, None
    while True:
        last = read()
        if accept(last):
            return last
        if time.monotonic() >= deadline:
            raise AssertionError(f'{description}；最后实际值={last!r}')
        time.sleep(0.05)


def bind_target(page, name, dom_id, timeout):
    captured = page.find(PREFIX + name, timeout=timeout)
    for _ in range(6):
        require(isinstance(captured, WebElement), f'{name} 未取得 WebElement')
        if captured.get_attribute('id') == dom_id:
            return captured
        captured = captured.parent(timeout=timeout)
    raise AssertionError(f'{name} 捕获点及近邻父级均不是 #{dom_id}')


def event_check(events, case):
    actions = [event for event in events if event['type'] in ('click', 'dblclick', 'contextmenu')]
    require([e['type'] for e in actions] == ['click', 'click', 'dblclick'],
            f"预期事件顺序 click/click/dblclick；实际 {[e['type'] for e in actions]!r}，事件={actions!r}")
    expected = dict(buttonId=TARGETS['double'][1], button=0, keys='none',
                    trusted=case['kwargs'].get('simulative', True))
    for index, actual in enumerate(actions, 1):
        for field, value in expected.items():
            require(type(actual.get(field)) is type(value) and actual.get(field) == value,
                    f'第 {index} 个事件 {field} 预期 {value!r}；实际 {actual.get(field)!r}')
        require(all(type(actual.get(field)) in (int, float) and math.isfinite(actual[field])
                    for field in ('x','y','width','height')), f'事件坐标无效: {actual!r}')
        require(actual['width'] > 0 and actual['height'] > 0 and
                0 <= actual['x'] < actual['width'] and 0 <= actual['y'] < actual['height'],
                f'事件坐标不在目标按钮内: {actual!r}')
    observed = actions[-1]
    for actual in actions[:-1]:
        require(abs(actual['x']-observed['x']) <= 1 and abs(actual['y']-observed['y']) <= 1,
                f'双击各事件位置不一致: {actions!r}')
    x, y, width, height = (observed[field] for field in ('x','y','width','height'))
    position = case.get('position')
    if position == 'center':
        require(abs(x-width/2) <= 3 and abs(y-height/2) <= 3,
                f'预期按钮中心（允许 3 CSS px 舍入误差）；实际 x/y/w/h={(x,y,width,height)}')
    elif position == 'top_left':
        require(x < width/2 and y < height/2, f'预期按钮左上区域；实际 {(x,y,width,height)}')
    elif position == 'bottom_right':
        require(x > width/2 and y > height/2, f'预期按钮右下区域；实际 {(x,y,width,height)}')
    return observed


def log_check(log, observed):
    require(isinstance(log, dict), f'剪贴板预期 JSON 对象；实际 {log!r}')
    expected = dict(buttonId=TARGETS['double'][1], buttonLabel='双击触发按钮', eventType='dblclick',
                    detectedKeys='none', isTrusted=observed['trusted'],
                    clickSource='真实鼠标' if observed['trusted'] else 'JS/插件模拟')
    for field, value in expected.items():
        require(type(log.get(field)) is type(value) and log.get(field) == value,
                f'日志 {field} 预期 {value!r}；实际 {log.get(field)!r}')
    require(isinstance(log.get('time'), str) and bool(log['time']), f'日志缺少时间: {log!r}')


def prepare_case(page, key, native, dom_id, timeout):
    try:
        page.activate()
    except Exception as exc:
        if getattr(exc, 'trace_info', '') != 'activate_tab_failed':
            raise
        raise Blocked('用例准备阶段无法激活测试页面，dblclick() 未执行；' + error_detail(exc)) from exc
    native.park()
    probe(page, key, 'prepare', id=dom_id)
    wait_for(lambda: probe(page, key, 'ready', id=dom_id),
             lambda value: not value['rows'] and value['visible'], timeout, '页面清空记录/滚动就绪失败')
    require(not native.held_keys(), f'开始前存在按住的辅助键: {native.held_keys()}')
    marker = native.sentinel()
    probe(page, key, 'arm')
    return marker


def original_log_state(page, key, latest_key):
    state = probe(page, key, 'read')
    require(state['rows'] and state['rows'][0]['key'] == latest_key,
            f'原日志已被覆盖或清除，拒绝继续复制: {state["rows"]!r}')
    return state


def ensure_copy_focus(page, key, native, latest_key, browser_window, timeout):
    state = original_log_state(page, key, latest_key)
    if state.get('documentFocused') is True:
        return state, ''
    notes = []
    try:
        page.activate()
        notes.append('已尝试 page.activate()')
    except Exception as exc:
        notes.append(error_detail(exc))
    state = original_log_state(page, key, latest_key)
    if state.get('documentFocused') is not True and browser_window is not None:
        notes.append(native.restore_browser_foreground(browser_window))
    deadline = time.monotonic() + timeout
    while True:
        state = original_log_state(page, key, latest_key)
        if state.get('documentFocused') is True:
            return state, '焦点已恢复并核验，原日志未变；' + '；'.join(notes)
        if time.monotonic() >= deadline:
            raise Blocked('复制前焦点恢复失败，未重试被测双击；document.hasFocus()=False；' + '；'.join(notes))
        time.sleep(0.05)


def copy_original_log(page, copy_button, key, native, latest_key, marker, browser_window, timeout):
    recovery = []
    state = None
    for attempt in range(2):
        state, detail = ensure_copy_focus(page, key, native, latest_key, browser_window, timeout)
        if detail:
            recovery.append(detail)
        copy_button.click(simulative=False, delay_after=0)
        def read_log():
            value = native.read_text()
            if value is None or value == marker:
                return None
            try:
                return json.loads(value)
            except (ValueError, TypeError) as exc:
                raise AssertionError(f'复制后不是有效 JSON: {value[:180]!r}') from exc
        try:
            log = wait_for(read_log, lambda value: value is not None,
                           min(1.0, timeout) if attempt == 0 else timeout, '复制按钮未写入新的 JSON')
        except AssertionError:
            value = native.read_text()
            if value is not None and value != marker:
                raise
            original_log_state(page, key, latest_key)
            continue
        original_log_state(page, key, latest_key)
        if attempt:
            recovery.append('仅重试复制一次，未重试被测双击')
        return log, '；'.join(recovery)
    raise Blocked('复制后剪贴板哨兵未替换，尚未完成日志验证；'
                  f'document.hasFocus()（复制前）={state.get("documentFocused")}；' + '；'.join(recovery))


def run_dblclick_case(page, elements, key, native, case, timeout):
    dom_id = TARGETS['double'][1]
    marker = prepare_case(page, key, native, dom_id, timeout)
    simulative = case['kwargs'].get('simulative', True)
    if simulative:
        native.separate_double_clicks()
    browser_window = native.window_info()
    if browser_window.get('process', '').lower() not in ('chrome.exe','msedge.exe'):
        browser_window = None
    cursor_before = native.get_cursor()
    started, caught, returned = time.perf_counter(), None, None
    try:
        returned = elements['double'].dblclick(**case['kwargs'])
    except Exception as exc:
        caught = exc
    elapsed = time.perf_counter() - started
    if simulative:
        native.last_physical_click = time.monotonic()
    if case.get('error_after'):
        require(isinstance(caught, InvalidParamsError) and 'delay_after' in str(caught),
                f'动作后预期 delay_after 的 InvalidParamsError；实际 {error_detail(caught) if caught else returned!r}')
    elif caught is not None:
        raise caught
    else:
        require(returned is None, f'预期返回 None；实际 {returned!r}')
    require(not native.held_keys(), f'动作后辅助键未释放: {native.held_keys()}')
    # DOM 路径按定时器派发事件；等到 dblclick，不在第一次 click 后提前判定。
    wait_for(lambda: probe(page,key,'read'),
             lambda value: any(e['type']=='dblclick' for e in value['events']),
             timeout, '未观察到完整 dblclick 事件')
    time.sleep(0.2)
    state = probe(page,key,'read')
    observed = event_check(state['events'],case)
    if not simulative:
        require(native.get_cursor() == cursor_before, 'DOM 双击改变了系统鼠标坐标')
    minimum = case.get('min_delay',0)
    require(elapsed >= minimum-0.02, f'预期动作后延时至少约 {minimum}s；实际调用 {elapsed:.3f}s')
    state = wait_for(lambda: probe(page,key,'read'), lambda value: bool(value['rows']),
                     timeout, '双击后靶场未生成日志')
    require(len(state['rows']) == 1, f'每次双击应生成恰好一条靶场记录；实际 {state["rows"]!r}')
    latest_key = state['rows'][0]['key']
    require(latest_key.startswith(dom_id+'-dblclick-'), f'记录目标或类型错误: {state["rows"]!r}')
    try:
        log, recovery_detail = copy_original_log(page,elements['copy'],key,native,
                                                  latest_key,marker,browser_window,timeout)
    except Blocked as exc:
        raise Blocked(f'独立双击事件已核对：click/click/dblclick、trusted={observed["trusted"]}；{exc}') from exc
    log_check(log,observed)
    outcome = '双击已发生后拒绝非法 delay_after' if case.get('error_after') else '返回 None'
    detail = (f'{outcome}；2 次 click + 1 次 dblclick；button=0、keys=none、trusted={observed["trusted"]}；'
              f'剪贴板 {log["buttonId"]}/{log["eventType"]}/{log["clickSource"]}；'
              f'位置=({observed["x"]:.1f},{observed["y"]:.1f})，按钮=({observed["width"]:.1f},{observed["height"]:.1f})；'
              f'调用 {elapsed*1000:.1f}ms')
    return detail + ('；'+recovery_detail if recovery_detail else '')


def dblclick_cases():
    cases = [
        dict(name='default_dblclick',kwargs={},position='center',min_delay=1),
        dict(name='mouse_explicit',kwargs=dict(simulative=True,move_mouse=False,anchor=None,delay_after=0),position='center'),
        dict(name='dom_dblclick',kwargs=dict(simulative=False,delay_after=0),position='center'),
        dict(name='delay_none',kwargs=dict(simulative=False,delay_after=None),position='center'),
        dict(name='delay_positive',kwargs=dict(simulative=False,delay_after=0.2),position='center',min_delay=0.2),
        dict(name='mouse_move_true',kwargs=dict(move_mouse=True,delay_after=0),position='center'),
        dict(name='dom_move_ignored',kwargs=dict(simulative=False,move_mouse=True,delay_after=0),position='center'),
        dict(name='anchor_string',kwargs=dict(anchor='middle_center',delay_after=0),position='center'),
        dict(name='anchor_tuple',kwargs=dict(anchor=('top_left',8,8),delay_after=0),position='top_left'),
        dict(name='anchor_dict',kwargs=dict(anchor={'anchor':'bottom_right','offset_x':-8,'offset_y':-8},delay_after=0),position='bottom_right'),
        dict(name='anchor_random',kwargs=dict(anchor='random',delay_after=0)),
        dict(name='dom_anchor_ignored',kwargs=dict(simulative=False,anchor=('top_left',8,8),delay_after=0),position='center'),
    ]
    for simulative, prefix in ((True,'mouse'),(False,'dom')):
        for index in range(1,3):
            cases.append(dict(name=f'{prefix}_repeat_{index}',kwargs=dict(simulative=simulative,delay_after=0),position='center'))
    for name, delay in (('negative_delay_after_action',-1),('text_delay_after_action','bad')):
        cases.append(dict(name=name,kwargs=dict(simulative=False,delay_after=delay),position='center',error_after=True))
    return cases


def invalid_case(page, elements, key, native, args, kwargs, positional=(), expected=InvalidParamsError):
    marker = prepare_case(page, key, native, TARGETS['double'][1], args.wait_timeout)
    try:
        elements['double'].dblclick(*positional, **kwargs)
    except expected as exc:
        detail = f'预期 {expected.__name__}；实际 {type(exc).__name__}: {exc}'
    else:
        raise AssertionError(f'预期 {expected.__name__}，实际未抛异常')
    time.sleep(0.2)
    state = probe(page, key, 'read')
    require(not state['events'] and not state['rows'], f'非法参数仍产生事件/日志: {state!r}')
    require(native.read_text() == marker, '非法参数调用改变了剪贴板')
    return detail + '；未产生目标事件或靶场记录'


def run(args):
    rows, resources = [], {}
    if not record_case(rows, 'api_contract', contract) or args.contract_only:
        return rows
    key = '__uiautoma_dblclick_' + uuid.uuid4().hex
    parts = urlsplit(args.url)
    run_url = urlunsplit(parts._replace(query=parts.query + ('&' if parts.query else '') + 'uiautoma_dblclick_run=' + uuid.uuid4().hex))
    stage, started = 'library_prepare', time.perf_counter()
    def ready(detail):
        rows.append(dict(case_id=stage, status='PASS', detail=detail, elapsed_ms=(time.perf_counter()-started)*1000))
    try:
        native = NativeState()
        resources['native'] = native
        if not args.library.is_dir():
            raise Blocked(f'元素库不存在: {args.library}')
        args.temp_root.mkdir(parents=True, exist_ok=True)
        temp = Path(tempfile.mkdtemp(prefix='uiautoma-element-dblclick-', dir=args.temp_root))
        resources['temp'] = temp
        shutil.copytree(args.library, temp/'library')
        package = uiautoma.open(str(temp/'library'), timeout=args.runtime_timeout, connect_timeout=args.runtime_timeout)
        resources['package'] = package
        for label, _ in TARGETS.values():
            package.selector(PREFIX+label)
        ready('已打开元素库副本；双击目标和复制按钮两个库项均存在')
        stage, started = 'page_prepare', time.perf_counter()
        page = web.create(run_url, mode=args.mode, load_timeout=args.load_timeout)
        resources['page'] = page
        require(isinstance(page, WebBrowser), f'预期 WebBrowser；实际 {type(page).__name__}')
        ready('已新建带本次标记的独立靶场页面')
        stage, started = 'elements_prepare', time.perf_counter()
        elements = {name: bind_target(page, label, dom_id, args.element_timeout) for name, (label, dom_id) in TARGETS.items()}
        ready('两个库元素均已核对 DOM id：btn-dblclick-target 与 btn-copy-latest-keys-log')
        # Chrome 页面已经可见且元素已确认后，才读取剪贴板；不可恢复格式也会走完整页面清理。
        stage, started = 'native_state', time.perf_counter()
        ready(native.capture())
        stage, started = 'event_observer', time.perf_counter()
        resources['observer_attempted'] = True
        probe(page, key, 'install')
        ready('已安装临时原生事件监听；逐项清空靶场日志，剪贴板使用唯一哨兵防止旧记录误通过')
        stage = 'dblclick_cases'
        for case in dblclick_cases():
            record_case(rows,case['name'],lambda case=case:run_dblclick_case(page,elements,key,native,case,args.wait_timeout))
        for name, kwargs in (
            ('simulative_integer',{'simulative':1}), ('simulative_none',{'simulative':None}),
            ('move_mouse_integer',{'move_mouse':1}), ('move_mouse_none',{'move_mouse':None}),
            ('anchor_unknown',{'anchor':'invalid'}), ('anchor_integer',{'anchor':123}),
        ):
            record_case(rows,name,lambda kwargs=kwargs:invalid_case(page,elements,key,native,args,kwargs))
        record_case(rows,'positional_argument',lambda:invalid_case(page,elements,key,native,args,{},(True,),TypeError))
        for name, kwargs in (
            ('reject_button',{'button':'right'}), ('reject_keys',{'keys':'win'}), ('reject_timeout',{'timeout':1}),
        ):
            record_case(rows,name,lambda kwargs=kwargs:invalid_case(page,elements,key,native,args,kwargs,expected=TypeError))
        record_case(rows,'after_invalid',lambda:run_dblclick_case(page,elements,key,native,
                    dict(kwargs=dict(delay_after=0),position='center'),args.wait_timeout))
    except Exception as exc:
        rows.append(dict(case_id=stage, status='BLOCKED' if isinstance(exc, Blocked) else 'FAIL',
                         detail=error_detail(exc), elapsed_ms=(time.perf_counter()-started)*1000))
    finally:
        page = resources.get('page')
        if page is not None and resources.get('observer_attempted'):
            def remove_probe():
                require(probe(page,key,'remove') is True, '观察器未移除')
                return '本次临时事件监听已移除并核对'
            record_case(rows,'cleanup_observer',remove_probe)
        if page is not None:
            def close_page():
                page.close(ignore_beforeunload=True)
                wait_for(lambda: web.get_all(mode=args.mode,url=run_url),lambda pages:not pages,
                         args.wait_timeout,'本次测试标签仍在枚举结果中')
                return '本次页面已关闭，按唯一 URL 枚举确认无残留'
            record_case(rows,'cleanup_page',close_page)
        package = resources.get('package')
        package_closed = True
        if package is not None:
            def close_package():
                package.close()
                return '本次 Package 已关闭'
            package_closed = record_case(rows,'cleanup_package',close_package)
        if resources.get('temp') is not None:
            def remove_temp():
                resolved = resources['temp'].resolve()
                require(package_closed, 'Package 关闭失败，保留副本供排查')
                require(resolved.parent == args.temp_root.resolve() and resolved.name.startswith('uiautoma-element-dblclick-'),
                        f'目录归属不符，不删除: {resolved}')
                shutil.rmtree(resolved)
                require(not resolved.exists(), f'副本目录仍存在: {resolved}')
                return '本次元素库副本已删除并核对不存在'
            record_case(rows,'cleanup_temp',remove_temp)
        native = resources.get('native')
        if native is not None:
            record_case(rows,'cleanup_clipboard',native.restore)
            if native.captured:
                record_case(rows,'cleanup_input',native.restore_input)
    return rows


def main(argv=None):
    parser = argparse.ArgumentParser(description='WebElement.dblclick() 双击靶场独立验收')
    parser.add_argument('--mode',choices=('chrome','edge'),default='chrome')
    parser.add_argument('--url',default=URL)
    parser.add_argument('--library',type=Path,default=LIBRARY)
    parser.add_argument('--element-timeout',type=float,default=10)
    parser.add_argument('--runtime-timeout',type=float,default=20)
    parser.add_argument('--load-timeout',type=float,default=20)
    parser.add_argument('--wait-timeout',type=float,default=4)
    parser.add_argument('--contract-only',action='store_true')
    parser.add_argument('--json',action='store_true',help='仅向终端输出 JSON，不自动生成日志文件')
    args = parser.parse_args(argv)
    args.temp_root = Path(__file__).resolve().parents[1]/'.pytest_tmp'
    for name in ('element_timeout','runtime_timeout','load_timeout','wait_timeout'):
        require(math.isfinite(getattr(args,name)) and getattr(args,name)>0, f'{name} 必须为正的有限秒数')
    if not args.json:
        print('UIAutoma Web API 测试\nAPI     : uiautoma.web.WebElement.dblclick',flush=True)
        print(f'页面    : {args.url}\n元素库  : {args.library}\nSDK     : {uiautoma.__file__}',flush=True)
        print('测试元素: '+PREFIX+TARGETS['double'][0],flush=True)
        print('复制元素: '+PREFIX+TARGETS['copy'][0],flush=True)
        print('参照    : 原生事件 click/click/dblclick + 剪贴板 JSON；请勿操作鼠标键盘',flush=True)
        print('边界    : 本轮仅双击按钮；锚点核对中心/所在区域，不验证全部九宫格位置、逐像素偏移或轨迹形状',flush=True)
    started = time.perf_counter()
    rows = run(args)
    code = 1 if any(r['status']=='FAIL' for r in rows) else 2 if any(r['status']=='BLOCKED' for r in rows) else 0
    if args.json:
        print(json.dumps(dict(api='WebElement.dblclick',lifecycle='READY_FOR_LIVE',results=rows,exit_code=code),ensure_ascii=False,indent=2))
    else:
        print('进度     状态    测试项                      测试结果 / 耗时\n'+'─'*100)
        for index,row in enumerate(rows,1):
            status = {'PASS':'通过','FAIL':'失败','BLOCKED':'阻塞'}[row['status']]
            print(f"{index:02d}/{len(rows):02d}    {COLORS[row['status']]}[{status}]\x1b[0m  {row['case_id']:<28} {row['detail']}  {row['elapsed_ms']:.1f}ms")
        passed = sum(r['status']=='PASS' for r in rows)
        print('─'*100)
        print(f'{"本轮检查通过" if code==0 else "测试失败" if code==1 else "测试阻塞"} · READY_FOR_LIVE · {passed}/{len(rows)} 通过 · {(time.perf_counter()-started)*1000:.1f}ms · 退出码 {code}')
    return code


if __name__ == '__main__':
    raise SystemExit(main())
