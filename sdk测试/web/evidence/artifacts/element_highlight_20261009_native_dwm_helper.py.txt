"""WebElement.get_anchor_position 后台验收。

同源 iframe/open Shadow 表单的库中 Ant 输入框；期望由原生 DOM 与
独立 Win32 viewport 屏幕原点推导，不调用 get_bounding 或 SDK 锚点计算 helper。
复用既有几何测试的环境/清理 helper，当前原生参考只支持 96 DPI。
退出码：0 全通过、1 失败、2 阻塞。默认静默自有标签，无系统输入或窗口激活。
"""
from __future__ import annotations

import argparse
import ctypes
from ctypes import wintypes
import hashlib
import inspect
import json
import math
import sys
import time
from pathlib import Path

__test__ = False
sys.dont_write_bytecode = True
ROOT = Path(r'D:\code\元素库\sdk测试')
sys.path.insert(0, str(ROOT/'web'))
import test_web_element_get_bounding as geometry
from uiautoma import ActionError, HostUnavailableError, InvalidParamsError
from uiautoma.web import WebElement

CONTRACT = ROOT/'web/element_get_anchor_position_contract_20261008.json'
POSITIONS = {
    'top_left': (0, 0), 'top_center': (.5, 0), 'top_right': (1, 0),
    'middle_left': (0, .5), 'middle_center': (.5, .5), 'middle_right': (1, .5),
    'bottom_left': (0, 1), 'bottom_center': (.5, 1), 'bottom_right': (1, 1),
}
FORMS = [
    ('none', None, 'middle_center', (0, 0)),
    ('tuple', ('middle_center', 7, -9), 'middle_center', (7, -9)),
    ('list', ['bottom_right', -4, 5], 'bottom_right', (-4, 5)),
    ('dict', {'anchor': 'top_left', 'offset_x': 8, 'offset_y': -6}, 'top_left', (8, -6)),
    ('fractional_offset', ('middle_center', .5, -.5), 'middle_center', (.5, -.5)),
    ('dict_default_position', {'offset_x': 3, 'offset_y': -4}, 'middle_center', (3, -4)),
    ('empty_list', [], 'middle_center', (0, 0)),
    ('casefold', 'TOP_RIGHT', 'top_right', (0, 0)),
    ('outside_bounds', ('middle_center', 700, -80), 'middle_center', (700, -80)),
]
INVALID = [
    ('invalid_name', 'bad', '不支持的锚点'),
    ('blank_name', '', '不支持的锚点'),
    ('whitespace_name', ' top_left ', '不支持的锚点'),
    ('invalid_tuple_name', ('bad', 0, 0), '不支持的锚点'),
    ('invalid_dict_name', {'anchor': 'bad'}, '不支持的锚点'),
    ('invalid_type', 123, 'anchor 必须是 None、字符串、元组或映射对象'),
    ('uppercase_random', 'RANDOM', '不支持的锚点'),
]


def contract():
    frozen = json.loads(CONTRACT.read_text(encoding='utf-8'))
    actual = str(inspect.signature(WebElement.get_anchor_position))
    geometry.require(actual == frozen['signature'], actual)
    geometry.require(inspect.getsource(WebElement.get_anchor_position) == frozen['source'], 'SDK method changed; review contract')
    commits = {'desktop': geometry.source_commit(geometry.PRODUCT), 'rust_uia': geometry.source_commit(geometry.PROVIDER)}
    geometry.require(commits == frozen['commits'], {'expected': frozen['commits'], 'actual': commits})
    for snapshot in frozen['source_snapshots']:
        file = Path(snapshot['worktree'])/snapshot['path']
        geometry.require(hashlib.sha256(file.read_bytes()).hexdigest() == snapshot['sha256'], {'changed_source': str(file)})
    return {'signature': actual, 'commits': commits, 'return': 'tuple[int,int]', 'keyword_only': ['anchor', 'to96dpi']}


class ValidationRaw:
    """Parameter tests only: fail if a rejected value reaches the RPC boundary."""

    def __init__(self):
        self.calls = 0

    def geometry(self, **kwargs):
        self.calls += 1
        raise AssertionError('Invalid argument reached RPC: '+repr(kwargs))


class NativeOracle(geometry.NativeOracle):
    """Use DWM visible frame bounds for maximized Chrome's invisible resize border."""

    def __init__(self):
        super().__init__()
        self.u.IsZoomed.argtypes = [wintypes.HWND]
        self.u.IsZoomed.restype = wintypes.BOOL
        self.dwm = ctypes.WinDLL('dwmapi', use_last_error=True)
        self.dwm.DwmGetWindowAttribute.argtypes = [wintypes.HWND, wintypes.DWORD, wintypes.LPVOID, wintypes.DWORD]
        self.dwm.DwmGetWindowAttribute.restype = ctypes.c_long

    def info(self, hwnd):
        row = super().info(hwnd)
        if row['class'] == 'Chrome_WidgetWin_1':
            row['maximized'] = bool(self.u.IsZoomed(hwnd))
            row['raw_window_rect'] = dict(row['rect'])
            row['rect_source'] = 'GetWindowRect'
            if row['maximized']:
                rect = wintypes.RECT()
                result = self.dwm.DwmGetWindowAttribute(hwnd, 9, ctypes.byref(rect), ctypes.sizeof(rect))
                if result != 0:
                    raise geometry.Blocked('Cannot read DWM maximized frame bounds: '+str(result))
                row['rect'] = {'x': rect.left, 'y': rect.top, 'width': rect.right-rect.left, 'height': rect.bottom-rect.top}
                row['rect_source'] = 'DWM_EXTENDED_FRAME_BOUNDS'
        return row


class Run(geometry.Run):
    def __init__(self, args):
        super().__init__(args)
        self.total = 1+len(INVALID)+2
        if not args.contract_only:
            self.total += 3+1+2*len(POSITIONS)+2*len(FORMS)+4+4*4+1+2+2+1

    def setup(self):
        result = super().setup()
        self.oracle.close()
        self.oracle = NativeOracle()
        return result

    def case(self, name, expected, fn):
        start = time.perf_counter()
        try:
            actual = fn(); status = 'PASS'
        except Exception as exc:
            actual = geometry.error(exc)
            status = 'BLOCKED' if isinstance(exc, geometry.Blocked) or type(exc).__name__ in {'HostUnavailableError', 'ConnectionError'} or getattr(exc, 'trace_info', '') == 'uiautomation_provider_unavailable' else 'FAIL'
        row = {'case_id': name, 'status': status, 'expected': expected, 'actual': actual, 'elapsed_ms': round((time.perf_counter()-start)*1000, 1)}
        self.rows.append(row)
        display = {key: actual[key] for key in ('point', 'expected_point', 'difference', 'dpi', 'dpr', 'scroll', 'foreground_unchanged')} if isinstance(actual, dict) and 'expected_point' in actual else actual
        color, label = {'PASS': ('\x1b[32m', '通过'), 'FAIL': ('\x1b[31m', '失败'), 'BLOCKED': ('\x1b[33m', '阻塞')}[status]
        print(f"{len(self.rows):02d}/{self.total:02d} {color}[{label}]\x1b[0m {name} 期望 {expected}；实测 {json.dumps(display, ensure_ascii=False, default=str)}；{row['elapsed_ms']}ms", flush=True)
        return status

    def reference(self, dom, native):
        rect = {key: math.floor(dom['rect'][key]*dom['dpr']+.5) for key in geometry.KEYS}
        for key in ('x', 'y'):
            rect[key] += native['viewport']['client_origin'][key]
        return rect

    def point(self, anchor=None, position='middle_center', offset=(0, 0), normal=True, scene='baseline', default=False):
        before = self.prepare(scene); native = self.oracle.measure(before)
        foreground = self.oracle.foreground()
        actual = self.element.get_anchor_position() if default else self.element.get_anchor_position(anchor=anchor, to96dpi=normal)
        after = self.observe(); native_after = self.oracle.measure(after); foreground_after = self.oracle.foreground()
        if before != after or native != native_after:
            raise geometry.Blocked(json.dumps({'reason': 'DOM/native reference moved during read', 'before': before, 'after': after, 'native_before': native, 'native_after': native_after}, ensure_ascii=False))
        rect = self.reference(before, native)
        fx, fy = POSITIONS[position]; factor = 96/native['dpi'] if normal else 1
        physical = (math.floor(rect['x']+rect['width']*fx+offset[0]+.5), math.floor(rect['y']+rect['height']*fy+offset[1]+.5))
        expected = tuple(math.floor(value*factor+.5) for value in physical)
        valid = type(actual) is tuple and len(actual) == 2 and all(type(value) is int for value in actual)
        difference = [actual[i]-expected[i] for i in range(2)] if valid else None
        detail = {'point': actual, 'expected_point': expected, 'difference': difference, 'anchor': anchor, 'position': position, 'offset': offset, 'scene': scene, 'to96dpi': normal, 'dpi': native['dpi'], 'dpr': before['dpr'], 'scroll': before['scroll'], 'foreground_unchanged': foreground == foreground_after, 'foreground_before': foreground, 'foreground_after': foreground_after, 'native': native, 'dom_before': before, 'dom_after': after, 'physical_reference_rect': rect}
        geometry.require(valid and difference == [0, 0], detail)
        if foreground != native['hwnd'] and foreground_after == native['hwnd']:
            raise geometry.Blocked(json.dumps({'reason': 'Test Chrome became foreground during call', **detail}, ensure_ascii=False))
        return detail

    def random_points(self, normal, offset):
        before = self.prepare('baseline'); native = self.oracle.measure(before); rect = self.reference(before, native)
        foreground = self.oracle.foreground(); factor = 96/native['dpi'] if normal else 1
        anchor = 'random' if offset == (0, 0) else ('random', *offset)
        points = [self.element.get_anchor_position(anchor=anchor, to96dpi=normal) for _ in range(12)]
        after = self.observe(); native_after = self.oracle.measure(after); foreground_after = self.oracle.foreground()
        if before != after or native != native_after:
            raise geometry.Blocked('Random sample DOM/native reference moved during read')
        lower = tuple(math.floor((rect[key]+offset[i])+.5) for i, key in enumerate(('x', 'y')))
        upper = (math.floor(rect['x']+rect['width']+offset[0]+.5), math.floor(rect['y']+rect['height']+offset[1]+.5))
        lower = tuple(math.floor(value*factor+.5) for value in lower)
        upper = tuple(math.floor(value*factor+.5) for value in upper)
        valid = all(type(p) is tuple and len(p) == 2 and all(type(v) is int for v in p) and all(lower[i] <= p[i] <= upper[i] for i in range(2)) for p in points)
        detail = {'anchor': anchor, 'to96dpi': normal, 'points': points, 'lower': lower, 'upper': upper, 'unique_points': len(set(points)), 'all_in_range': valid, 'dpi': native['dpi'], 'dpr': before['dpr'], 'foreground_before': foreground, 'foreground_after': foreground_after, 'foreground_unchanged': foreground == foreground_after, 'native': native, 'dom_before': before, 'dom_after': after}
        geometry.require(valid and len(set(points)) >= 2, detail)
        if foreground != native['hwnd'] and foreground_after == native['hwnd']:
            raise geometry.Blocked('Test Chrome became foreground during random sampling')
        return detail

    def readonly(self):
        self.restore(); before = self.stable()
        points = [self.element.get_anchor_position(anchor='middle_center', to96dpi=False) for _ in range(3)]
        after = self.observe()
        return geometry.require(before == after and all(p == points[0] for p in points), {'points': points, 'dom_scroll_value_focus_style_unchanged': before == after})

    def closed_page(self):
        self.page.close(ignore_beforeunload=True)
        return geometry.raises(ActionError, lambda: self.element.get_anchor_position(), trace='stale_page_reference')

    def closed_package(self):
        self.package.close()
        return geometry.raises(HostUnavailableError, lambda: self.element.get_anchor_position(), '连接已关闭')


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--url', default=geometry.URL)
    parser.add_argument('--library', type=Path, default=geometry.LIBRARY)
    parser.add_argument('--element', default=geometry.NAME)
    parser.add_argument('--contract-only', action='store_true')
    parser.add_argument('--json', action='store_true')
    parser.add_argument('--report-file', type=Path)
    args = parser.parse_args(argv); run = Run(args)
    print('UIAutoma Web API 测试\nAPI     : uiautoma.web.WebElement.get_anchor_position\n页面    : '+args.url, flush=True)
    good = run.case('api_contract', '签名、源码、默认值、关键字参数及只读快照一致', contract) == 'PASS'
    raw = ValidationRaw(); validation_element = WebElement(raw)
    for name, anchor, message in INVALID:
        def invalid(anchor=anchor, message=message):
            result = geometry.raises(InvalidParamsError, lambda: validation_element.get_anchor_position(anchor=anchor), message)
            geometry.require(raw.calls == 0, {'rpc_calls': raw.calls})
            return {**result, 'rpc_calls': raw.calls}
        run.case(name, 'SDK 在 RPC 前拒绝；InvalidParamsError / '+message, invalid)
    run.case('keyword_only', '位置传参抛 TypeError', lambda: geometry.raises(TypeError, lambda: validation_element.get_anchor_position('top_left')))
    run.case('unknown_keyword', '未知关键字抛 TypeError', lambda: geometry.raises(TypeError, lambda: validation_element.get_anchor_position(relative_to='window')))
    if good and not args.contract_only:
        try:
            if run.case('environment', '静默自有靶场/库副本可用；保留用户标签', run.setup) == 'PASS':
                if run.case('library_mapping', '库选择器唯一命中 Ant input', run.mapping) == 'PASS':
                    run.case('native_oracle', '独立 Win32 唯一识别 96 DPI Chrome 主窗口与 viewport', lambda: run.oracle.measure(run.observe()))
                    run.case('default_center', '默认参数返回元素中心屏幕坐标、两个 int', lambda: run.point(default=True))
                    for position in POSITIONS:
                        for normal in (False, True):
                            run.case(f'{position}_{normal}', '锚点与 DOM + Win32 独立参考完全相同，无点击 inset', lambda position=position, normal=normal: run.point(anchor=position, position=position, normal=normal))
                    for name, anchor, position, offset in FORMS:
                        for normal in (False, True):
                            run.case(f'form_{name}_{normal}', '形式/偏移符合快照；独立屏幕坐标完全相同', lambda anchor=anchor, position=position, offset=offset, normal=normal: run.point(anchor, position, offset, normal))
                    for offset in ((0, 0), (11, -7)):
                        for normal in (False, True):
                            run.case(f'random_{offset}_{normal}', '12 个整数元组位于完整矩形加偏移范围内，至少两点不同', lambda offset=offset, normal=normal: run.random_points(normal, offset))
                    for scene in geometry.SCENES[1:]:
                        for position in ('middle_center', 'bottom_right'):
                            for normal in (False, True):
                                run.case(f'{scene}_{position}_{normal}', '场景变化后锚点仍与独立坐标相同，读取不滚动', lambda scene=scene, position=position, normal=normal: run.point(anchor=position, position=position, normal=normal, scene=scene))
                    run.case('readonly_repeat', '连读三次相同；滚动/value/focus/style 不变', run.readonly)
                    run.case('restore_scene', '自有页面样式/滚动精确恢复', run.restore_case)
                    run.case('restore_preference', '动态 ID 开关/localStorage 精确恢复', run.restore_preference)
                    run.case('closed_page', '关闭页面后抛 ActionError / stale_page_reference', run.closed_page)
                    run.case('closed_package', '关闭库连接后抛 HostUnavailableError / 连接已关闭', run.closed_package)
        finally:
            run.case('cleanup', '自有资源已清理，源库/用户标签不变', run.cleanup)
    code = 1 if any(r['status'] == 'FAIL' for r in run.rows) else 2 if any(r['status'] == 'BLOCKED' for r in run.rows) else 0
    report = {'api': 'uiautoma.web.WebElement.get_anchor_position', 'date': '2026-10-08', 'lifecycle': 'VERIFIED' if code == 0 and not args.contract_only and len(run.rows) == run.total else 'READY_FOR_LIVE', 'scope': 'background Chrome, iframe/open Shadow Ant input, native DPI=96; higher DPI conversion not verified', 'worktrees': {'desktop': str(geometry.PRODUCT), 'rust_uia': str(geometry.PROVIDER)}, 'commits': {'desktop': geometry.source_commit(geometry.PRODUCT), 'rust_uia': geometry.source_commit(geometry.PROVIDER)}, 'url': args.url, 'library': str(args.library), 'element': args.element, 'results': run.rows, 'exit_code': code}
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
