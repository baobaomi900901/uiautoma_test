"""WebElement.click() 独立验收：keys-click-test + 260902_web元素。

VERIFIED：2026-09-19 用户完整实测 62/62 通过，退出码 0。
真实 Win 点击后恢复焦点并核对原日志；本轮清理时原前台未恢复，记录为警告。
只依赖标准库和 uiautoma；不调用 dblclick()/hover()/focus() 充当 click()。
参照：靶场复制 JSON + 原生 CF_UNICODETEXT + 临时 DOM 事件监听。
源码快照 D:/code/desktop @ c101caa9dcd115a461fc71ecaed351b0dea880b8。
靶场源码：https://github.com/baobaomi900901/xpath/blob/main/WEB/src/pages/KeysClickTestPage.tsx
仅操作本次页面/元素库副本；复制并恢复剪贴板格式数据、鼠标与原前台。
真实鼠标测试期间请勿操作鼠标键盘。退出码：0 通过，1 失败，2 环境阻塞。
真实鼠标 keys='win' 留到全部普通场景及参数检查之后；其后仅执行资源清理。
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
    'single': ('单击触发', 'btn-click-target'),
    'double': ('双击触发', 'btn-dblclick-target'),
    'right': ('右键触发', 'btn-rightclick-target'),
    'grid': ('测试九宫格按钮', 'position-grid-panel'),
    'hover': ('测试hover', 'hover-target'),
    'focus': ('测试focus', 'focus-target'),
    'copy': ('读取最近一条点击记录', 'btn-copy-latest-keys-log'),
}
COLORS = {'PASS': '\x1b[92m', 'FAIL': '\x1b[91m', 'BLOCKED': '\x1b[93m'}

# 仅监听和读 DOM；clear/scroll/blur 是用例准备，不制造被测点击事件。
PROBE = """function (element, arg) {
  const ids = ['btn-click-target','btn-dblclick-target','btn-rightclick-target',
    'position-grid-panel','hover-target','focus-target'];
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
    const state = {events: [], armed: false, types: ['click','dblclick','contextmenu','mouseover','focusin']};
    state.listen = event => {
      if (!state.armed || !(event.target instanceof Element)) return;
      const root = event.target.closest(ids.map(id => '#' + id).join(','));
      if (!root) return;
      if (event.type === 'mouseover' && event.relatedTarget instanceof Node && root.contains(event.relatedTarget)) return;
      const r = root.getBoundingClientRect();
      state.events.push({buttonId: root.id, type: event.type, button: event.button,
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
    signature = inspect.signature(WebElement.click)
    expected = dict(button='left', simulative=True, keys='none', delay_after=1, move_mouse=False, anchor=None)
    require(tuple(signature.parameters) == ('self', *expected), f'签名不符: {signature}')
    for name, default in expected.items():
        param = signature.parameters[name]
        require(param.kind == inspect.Parameter.KEYWORD_ONLY and param.default == default,
                f'{name} 预期关键字参数、默认 {default!r}；实际 {param}')
    require(str(signature.return_annotation) in ('None', "<class 'NoneType'>"), f'返回注解不符: {signature}')
    return '六个参数均仅限关键字；默认值与源码一致；返回 None'


class NativeState:
    """剪贴板独立读取；进入时复制实际数据，不跨用例持有 OLE 代理。"""
    MODIFIERS = (('shift', 0x10), ('ctrl', 0x11), ('alt', 0x12), ('lwin', 0x5B), ('rwin', 0x5C))
    MEMORY_FORMATS = {1, 7, 8, 13, 15, 16, 17}
    NAMED_MEMORY_FORMATS = {'HTML Format', 'Rich Text Format', 'Rich Text Format Without Objects', 'PNG'}

    def __init__(self):
        self.user = ctypes.WinDLL('user32', use_last_error=True)
        self.kernel = ctypes.WinDLL('kernel32', use_last_error=True)
        self.saved = None
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

    def restore_browser_foreground(self, target, *, allow_start_menu=False):
        actual = self.window_info(target['handle'])
        if (actual != target or not target['pid'] or
                target['process'].lower() not in ('chrome.exe', 'msedge.exe')):
            raise Blocked(f'点击前记录的浏览器窗口已失效或身份改变: {actual!r}')
        require(not self.held_keys(), '焦点恢复前辅助键仍按下，拒绝发送其他按键')
        front = self.window_info()
        dismissed = False
        # 只处理本轮真实 Win 点击后新出现且身份再次核对一致的开始菜单。
        if (allow_start_menu and front['handle'] != target['handle'] and
                front['process'].lower() == 'startmenuexperiencehost.exe' and
                self.window_info() == front):
            self.user.keybd_event(0x1B, 0, 0, 0)
            self.user.keybd_event(0x1B, 0, 2, 0)
            dismissed = True
            deadline = time.monotonic() + 0.5
            while self.user.GetForegroundWindow() == front['handle'] and time.monotonic() < deadline:
                time.sleep(0.05)
        activated = bool(self.user.SetForegroundWindow(target['handle']))
        return (f'恢复前前台={front!r}；开始菜单 Esc={dismissed}；'
                f'SetForegroundWindow={activated}（仍需 DOM 焦点核验）')

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
        return f'已复制原剪贴板 {len(self.saved)} 个格式的实际数据，记录鼠标和前台；辅助键均未按下'

    def sentinel(self):
        require(self.captured, '未保存剪贴板，不允许覆盖')
        self.modified = True
        value = 'uiautoma-click-' + uuid.uuid4().hex
        clipboard.set_text(value)
        require(self.read_text() == value, '剪贴板哨兵写入与独立读回不一致')
        return value

    def park(self):
        require(self.user.SetCursorPos(0, 0), '测试准备移动鼠标失败')

    def separate_single_clicks(self):
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
    target_id = TARGETS[case['target']][1]
    wanted = 'contextmenu' if case['kwargs'].get('button', 'left') == 'right' else 'click'
    actions = [event for event in events if event['type'] in ('click', 'dblclick', 'contextmenu')]
    require(len(actions) == 1, f'预期恰好一次 {wanted}（无 dblclick）；实际 {actions!r}')
    actual = actions[0]
    expected = dict(buttonId=target_id, type=wanted, button=2 if wanted == 'contextmenu' else 0,
                    keys=case['kwargs'].get('keys', 'none'), trusted=case['kwargs'].get('simulative', True))
    for field, value in expected.items():
        require(type(actual.get(field)) is type(value) and actual.get(field) == value,
                f'事件 {field} 预期 {value!r}；实际 {actual.get(field)!r}')
    if case['target'] == 'grid':
        require(all(isinstance(actual.get(field), (int, float)) and math.isfinite(actual[field])
                    for field in ('x', 'y', 'width', 'height')), f'坐标无效: {actual!r}')
        require(0 <= actual['x'] < actual['width'] and 0 <= actual['y'] < actual['height'],
                f'点击位置不在九宫格面板内: {actual!r}')
        position = position_label(actual)
        if case.get('position'):
            require(position == case['position'], f"九宫格预期 {case['position']}；实际 {position}")
    return actual


def position_label(event):
    col = min(2, int(event['x'] * 3 / event['width']))
    row = min(2, int(event['y'] * 3 / event['height']))
    return (('topLeft-(左上)', 'top-(上)', 'topRight-(右上)'),
            ('left-(左)', 'center-(中)', 'right-(右)'),
            ('bottomLeft-(左下)', 'bottom-(下)', 'bottomRight-(右下)'))[row][col]


def log_check(log, observed, expected_id, event_type):
    require(isinstance(log, dict), f'剪贴板预期 JSON 对象；实际 {log!r}')
    expected = dict(buttonId=expected_id, eventType=event_type,
                    detectedKeys=observed['keys'] if event_type not in ('hover', 'focus') else '-',
                    isTrusted=observed['trusted'],
                    clickSource='真实鼠标' if observed['trusted'] else 'JS/插件模拟')
    for field, value in expected.items():
        require(type(log.get(field)) is type(value) and log.get(field) == value,
                f'日志 {field} 预期 {value!r}；实际 {log.get(field)!r}')
    require(isinstance(log.get('time'), str) and bool(log['time']), f'日志缺少时间: {log!r}')
    if expected_id == 'position-grid-panel':
        require(log.get('clickPosition') == position_label(observed),
                f'方位日志与独立事件坐标不符: {log!r}')
        # native offsetX/Y 相对真正 event.target，可能是格子或 span，不能当作相对面板坐标。
        for field in ('offsetX', 'offsetY'):
            require(type(log.get(field)) is int and log[field] == observed[field],
                    f'{field} 日志与原生事件不一致: {log!r} / {observed!r}')


def prepare_case(page, key, native, dom_id, timeout):
    try:
        page.activate()
    except Exception as exc:
        if getattr(exc, 'trace_info', '') != 'activate_tab_failed':
            raise
        raise Blocked('用例准备阶段无法激活测试页面，click() 未执行；' + error_detail(exc)) from exc
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
        notes.append(native.restore_browser_foreground(browser_window, allow_start_menu=True))
    deadline = time.monotonic() + timeout
    while True:
        state = original_log_state(page, key, latest_key)
        if state.get('documentFocused') is True:
            return state, '焦点已恢复并核验，原日志未变；' + '；'.join(notes)
        if time.monotonic() >= deadline:
            raise Blocked('复制前焦点恢复失败，未重试被测点击；document.hasFocus()=False；' + '；'.join(notes))
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
            recovery.append('仅重试复制一次，未重试被测点击')
        return log, '；'.join(recovery)
    raise Blocked('复制后剪贴板哨兵未替换，尚未完成日志验证；'
                  f'document.hasFocus()（复制前）={state.get("documentFocused")}；' + '；'.join(recovery))


def run_click_case(page, elements, key, native, case, timeout):
    dom_id = TARGETS[case['target']][1]
    marker = prepare_case(page, key, native, dom_id, timeout)
    if case['kwargs'].get('simulative', True):
        native.separate_single_clicks()
    browser_window = None
    if case['kwargs'].get('simulative', True) and case['kwargs'].get('keys') == 'win':
        before = probe(page, key, 'read')
        if before.get('documentFocused') is not True:
            raise Blocked('真实 Win 点击前页面未聚焦，未执行被测点击')
        browser_window = native.window_info()
        if browser_window['process'].lower() not in ('chrome.exe', 'msedge.exe'):
            raise Blocked(f'真实 Win 点击前未确认浏览器前台窗口: {browser_window!r}')
    started, caught = time.perf_counter(), None
    returned = None
    try:
        returned = elements[case['target']].click(**case['kwargs'])
    except Exception as exc:
        caught = exc
    elapsed = time.perf_counter() - started
    if case['kwargs'].get('simulative', True):
        native.last_physical_click = time.monotonic()
    if case.get('error_after'):
        require(isinstance(caught, InvalidParamsError), f'动作后预期 InvalidParamsError；实际 {error_detail(caught) if caught else returned!r}')
        require('delay_after' in str(caught), f'异常来源不是 delay_after: {caught}')
    elif caught is not None:
        raise caught
    else:
        require(returned is None, f'预期返回 None；实际 {returned!r}')
    require(not native.held_keys(), f'动作后辅助键未释放: {native.held_keys()}')
    # DOM 模式分时派发事件；仅等待事件，不重试被测动作。
    state = wait_for(lambda: probe(page, key, 'read'),
                     lambda value: any(e['type'] in ('click', 'contextmenu', 'dblclick') for e in value['events']),
                     timeout, '点击调用后未观察到动作事件')
    time.sleep(0.2)
    state = probe(page, key, 'read')
    observed = event_check(state['events'], case)
    minimum = case.get('min_delay', 0)
    require(elapsed >= minimum - 0.02, f'预期动作后等待至少约 {minimum}s；调用仅 {elapsed:.3f}s')

    app_type = case.get('app_type')
    app_observed = observed
    if app_type in ('hover', 'focus'):
        event_type = 'mouseover' if app_type == 'hover' else 'focusin'
        candidates = [e for e in state['events'] if e['buttonId'] == dom_id and e['type'] == event_type]
        require(bool(candidates), f'真实鼠标点击未观察到附带的 {event_type} 事件: {state!r}')
        app_observed = candidates[-1]
        if app_type == 'focus':
            require(state['activeId'] == dom_id, f'点击后焦点不在目标: {state["activeId"]!r}')
    if app_type is None:
        require(not state['rows'], f'本场景不应生成靶场操作日志；实际 {state["rows"]!r}')
        require(native.read_text() == marker, '无日志场景不应修改剪贴板')
        log_detail = '靶场未生成操作日志，独立监听确认一次 click（不要求 dblclick/hover/focus）'
    else:
        state = wait_for(lambda: probe(page, key, 'read'), lambda value: bool(value['rows']), timeout, '靶场未生成日志')
        latest_key = state['rows'][0]['key']
        require(latest_key.startswith(dom_id + '-' + app_type + '-'), f'最近记录目标/事件错误: {state["rows"]!r}')
        try:
            log, recovery_detail = copy_original_log(page, elements['copy'], key, native,
                                                      latest_key, marker, browser_window, timeout)
        except Blocked as exc:
            raise Blocked(f'独立事件已核对: {observed["type"]}、keys={observed["keys"]}、trusted={observed["trusted"]}；{exc}') from exc
        log_check(log, app_observed, dom_id, app_type)
        log_detail = f"剪贴板 {log['buttonId']}/{log['eventType']}/{log['detectedKeys']}/{log['clickSource']}"
        if case['target'] == 'grid':
            log_detail += f"；{log['clickPosition']}，offset=({log['offsetX']},{log['offsetY']})"
        if recovery_detail:
            log_detail += '；' + recovery_detail
    outcome = '动作已发生后拒绝非法 delay_after' if case.get('error_after') else '返回 None'
    return f'{outcome}；独立事件一次 {observed["type"]}、button={observed["button"]}、keys={observed["keys"]}、trusted={observed["trusted"]}；{log_detail}；调用 {elapsed * 1000:.1f}ms'


def click_cases():
    cases = [dict(name='default_click', target='single', kwargs={}, app_type='click', min_delay=1)]
    for simulative, prefix in ((True, 'mouse'), (False, 'dom')):
        for key in ('none', 'alt', 'ctrl', 'shift', 'win'):
            cases.append(dict(name=f'{prefix}_keys_{key}', target='single', app_type='click',
                              kwargs=dict(simulative=simulative, keys=key, delay_after=0)))
        cases.append(dict(name=f'{prefix}_right', target='right', app_type='contextmenu',
                          kwargs=dict(simulative=simulative, button='right', delay_after=0)))
        cases.append(dict(name=f'{prefix}_double_target_single', target='double', app_type=None,
                          kwargs=dict(simulative=simulative, delay_after=0)))
        for target in ('hover', 'focus'):
            cases.append(dict(name=f'{prefix}_click_{target}', target=target,
                              app_type=target if simulative else None,
                              kwargs=dict(simulative=simulative, delay_after=0)))
    for name, delay, minimum in (('delay_none', None, 0), ('delay_positive', 0.2, 0.2)):
        cases.append(dict(name=name, target='single', app_type='click', min_delay=minimum,
                          kwargs=dict(simulative=False, delay_after=delay)))
    cases.append(dict(name='move_mouse_true', target='single', app_type='click',
                      kwargs=dict(move_mouse=True, delay_after=0)))
    anchors = [('top_left', 12, 12, 'topLeft-(左上)'), ('top_center', 0, 12, 'top-(上)'),
               ('top_right', -12, 12, 'topRight-(右上)'), ('middle_left', 12, 0, 'left-(左)'),
               ('middle_center', 0, 0, 'center-(中)'), ('middle_right', -12, 0, 'right-(右)'),
               ('bottom_left', 12, -12, 'bottomLeft-(左下)'), ('bottom_center', 0, -12, 'bottom-(下)'),
               ('bottom_right', -12, -12, 'bottomRight-(右下)')]
    # 九宫格有圆角；边角向内偏移，避免故意点击圆角外的不可命中点。
    for anchor, x, y, position in anchors:
        cases.append(dict(name='anchor_' + anchor, target='grid', app_type='click', position=position,
                          kwargs=dict(anchor=(anchor, x, y), delay_after=0)))
    for name, anchor, position in (('anchor_string', 'middle_center', 'center-(中)'),
                                    ('anchor_dict', {'anchor':'top_right','offset_x':-16,'offset_y':16}, 'topRight-(右上)'),
                                    ('anchor_random', 'random', None)):
        cases.append(dict(name=name, target='grid', app_type='click', position=position,
                          kwargs=dict(anchor=anchor, delay_after=0)))
    cases.append(dict(name='dom_anchor_ignored', target='grid', app_type='click', position='center-(中)',
                      kwargs=dict(simulative=False, anchor=('top_left',12,12), move_mouse=True, delay_after=0)))
    for name, delay in (('negative_delay_after_action', -1), ('text_delay_after_action', 'bad')):
        cases.append(dict(name=name, target='single', app_type='click', error_after=True,
                          kwargs=dict(simulative=False, delay_after=delay)))
    return cases


def invalid_case(page, elements, key, native, args, kwargs, positional=(), expected=InvalidParamsError):
    marker = prepare_case(page, key, native, TARGETS['single'][1], args.wait_timeout)
    try:
        elements['single'].click(*positional, **kwargs)
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
    key = '__uiautoma_click_' + uuid.uuid4().hex
    parts = urlsplit(args.url)
    run_url = urlunsplit(parts._replace(query=parts.query + ('&' if parts.query else '') + 'uiautoma_click_run=' + uuid.uuid4().hex))
    stage, started = 'native_state', time.perf_counter()
    def ready(detail):
        rows.append(dict(case_id=stage, status='PASS', detail=detail, elapsed_ms=(time.perf_counter()-started)*1000))
    try:
        native = NativeState()
        resources['native'] = native
        ready(native.capture())
        stage, started = 'library_prepare', time.perf_counter()
        if not args.library.is_dir():
            raise Blocked(f'元素库不存在: {args.library}')
        args.temp_root.mkdir(parents=True, exist_ok=True)
        temp = Path(tempfile.mkdtemp(prefix='uiautoma-element-click-', dir=args.temp_root))
        resources['temp'] = temp
        shutil.copytree(args.library, temp/'library')
        package = uiautoma.open(str(temp/'library'), timeout=args.runtime_timeout, connect_timeout=args.runtime_timeout)
        resources['package'] = package
        for label, _ in TARGETS.values():
            package.selector(PREFIX+label)
        ready('已打开元素库副本；六个测试元素及独立复制按钮均存在')
        stage, started = 'page_prepare', time.perf_counter()
        page = web.create(run_url, mode=args.mode, load_timeout=args.load_timeout)
        resources['page'] = page
        require(isinstance(page, WebBrowser), f'预期 WebBrowser；实际 {type(page).__name__}')
        ready('已新建带本次标记的独立靶场页面')
        stage, started = 'elements_prepare', time.perf_counter()
        elements = {name: bind_target(page, label, dom_id, args.element_timeout) for name, (label, dom_id) in TARGETS.items()}
        ready('七个库元素均已核对 DOM id；复制使用“读取最近一条点击记录”，不是 focus 目标')
        stage, started = 'event_observer', time.perf_counter()
        resources['observer_attempted'] = True
        probe(page, key, 'install')
        ready('已安装临时原生事件监听；逐项清空靶场日志，剪贴板使用唯一哨兵防止旧记录误通过')
        stage = 'click_cases'
        deferred_win = []
        for case in click_cases():
            if case['kwargs'].get('keys') == 'win' and case['kwargs'].get('simulative', True):
                deferred_win.append(case)
                continue
            record_case(rows, case['name'], lambda case=case: run_click_case(page, elements, key, native, case, args.wait_timeout))
        for name, kwargs in (
            ('invalid_button', {'button':'middle'}), ('button_case_sensitive', {'button':'LEFT'}),
            ('invalid_keys', {'keys':'ctrl+shift'}), ('keys_none_object', {'keys':None}),
            ('simulative_integer', {'simulative':1}), ('simulative_none', {'simulative':None}),
            ('move_mouse_integer', {'move_mouse':1}), ('move_mouse_none', {'move_mouse':None}),
            ('anchor_unknown', {'anchor':'invalid'}), ('anchor_integer', {'anchor':123}),
        ):
            record_case(rows, name, lambda kwargs=kwargs: invalid_case(page,elements,key,native,args,kwargs))
        record_case(rows, 'positional_argument', lambda: invalid_case(page,elements,key,native,args,{},('left',),TypeError))
        record_case(rows, 'unknown_keyword', lambda: invalid_case(page,elements,key,native,args,{'timeout':1},expected=TypeError))
        record_case(rows, 'after_invalid', lambda: run_click_case(page,elements,key,native,
                    dict(target='single',kwargs=dict(delay_after=0),app_type='click'),args.wait_timeout))
        # Win 的真实按下/释放可能改变系统前台；后面不再安排业务用例。
        for case in deferred_win:
            record_case(rows, case['name'], lambda case=case: run_click_case(page, elements, key, native, case, args.wait_timeout))
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
                require(resolved.parent == args.temp_root.resolve() and resolved.name.startswith('uiautoma-element-click-'),
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
    parser = argparse.ArgumentParser(description='WebElement.click() 点击靶场独立验收')
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
        print('UIAutoma Web API 测试\nAPI     : uiautoma.web.WebElement.click',flush=True)
        print(f'页面    : {args.url}\n元素库  : {args.library}\nSDK     : {uiautoma.__file__}',flush=True)
        print('复制元素: '+PREFIX+TARGETS['copy'][0],flush=True)
        print('参照    : 剪贴板 JSON + 独立 DOM 事件；请勿操作鼠标键盘',flush=True)
        print('顺序    : 真实鼠标 Win 键最后测试，其后仅清理；DOM win 按普通用例执行',flush=True)
        print('边界    : 双击/hover/focus 区域仅验收 click；九宫格边角内移避开圆角，未验证逐像素偏移或鼠标轨迹形状',flush=True)
    started = time.perf_counter()
    rows = run(args)
    code = 1 if any(r['status']=='FAIL' for r in rows) else 2 if any(r['status']=='BLOCKED' for r in rows) else 0
    if args.json:
        print(json.dumps(dict(api='WebElement.click',lifecycle='READY_FOR_LIVE',results=rows,exit_code=code),ensure_ascii=False,indent=2))
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
