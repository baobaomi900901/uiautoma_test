"""WebElement.child_at()：表单输入框及其祖先容器的独立验收。

预期结果由原生 DOM children 提供；原有 test_web_element_child_at.py 保留。
本文件只依赖标准库和 uiautoma，不依赖其它测试脚本。
源码快照：D:/code/desktop @ c101caa9dcd115a461fc71ecaed351b0dea880b8。
状态：VERIFIED（2026-09-19 用户实测 40/40；含预期的零预算超时边界）。
"""
from __future__ import annotations

import argparse
import hashlib
import inspect
import math
import shutil
import tempfile
import time
from html.parser import HTMLParser
from pathlib import Path
from typing import Callable

import uiautoma
from uiautoma import ActionError, InvalidParamsError, web
from uiautoma.web import WebBrowser, WebElement

__test__ = False
URL = "https://baobaomi900901.github.io/xpath/#/iframe-shadow-form"
LIBRARY = Path(r"D:\code\元素库\260902_web元素")
TARGET_NAME = "web靶场_表单测试_ant_输入框"
TARGET_DOM_ID = "form-controls-ant-text"
SWITCH = "web靶场_表单测试_控制表单组件id是否为动态的开关"
GREEN, RED, RESET = "\x1b[92m", "\x1b[91m", "\x1b[0m"

DOM_ORACLE = """function (element, inputId) {
  const frame = document.querySelector('#iframe-shadow-form');
  const doc = frame && frame.contentDocument;
  const host = doc && doc.querySelector('#form-shadow-host');
  const shadow = host && host.shadowRoot;
  if (!shadow) throw new Error('iframe/open shadow 尚未就绪');
  const matches = shadow.querySelectorAll('[id="' + inputId + '"]');
  if (matches.length !== 1 || matches[0].tagName !== 'INPUT')
    throw new Error('文本输入框不是唯一 INPUT');
  const input = matches[0];
  function info(node) {
    return {tag: node.tagName, id: node.id || '',
            class: node.getAttribute('class') || '', html: node.outerHTML};
  }
  const ancestors = [];
  let current = input.parentElement;
  let multiIndex = -1;
  for (let depth = 0; current && depth < 32; depth++) {
    const children = Array.from(current.children).map(info);
    const descendantCount = current.querySelectorAll('*').length;
    ancestors.push({
      node: info(current), children,
      descendant_count: descendantCount,
      non_element_count: current.childNodes.length - current.children.length
    });
    if (children.length >= 2 && descendantCount > children.length &&
        new Set(children.map(node => node.html)).size === children.length) {
      multiIndex = ancestors.length - 1;
      break;
    }
    current = current.parentElement;
  }
  if (multiIndex < 0) throw new Error('原生祖先链中没有适合验证多项及非递归语义的容器');
  return {
    input: info(input), leaf_children: Array.from(input.children).map(info),
    ancestors, multi_index: multiIndex,
    target_index: ancestors[0].children.findIndex(child => child.id === inputId)
  };
}"""


def result(case_id: str, status: str, detail: str, elapsed_ms: float = 0):
    return {'case_id': case_id, 'status': status, 'detail': detail, 'elapsed_ms': elapsed_ms}

def error_detail(prefix: str, exc: BaseException) -> str:
    detail = f'{prefix}: {type(exc).__name__}: {exc}'
    trace = str(getattr(exc, 'trace_info', '') or '')
    if trace:
        detail += f' [trace={trace}]'
    trace_id = str(getattr(exc, 'trace_id', '') or '')
    if trace_id:
        detail += f' [trace_id={trace_id}]'
    return detail

def record_case(results, label: str, action: Callable):
    started = time.perf_counter()
    try:
        detail = action()
        status = 'PASS'
    except Exception as exc:
        detail = error_detail('检查失败', exc)
        status = 'FAIL'
    results.append(result(label, status, detail, (time.perf_counter() - started) * 1000))
    return status == 'PASS'

def expect_exception(action: Callable, expected, *, trace: str | None = None, min_elapsed: float = 0):
    started = time.perf_counter()
    try:
        value = action()
    except expected as exc:
        elapsed = time.perf_counter() - started
        actual_trace = str(getattr(exc, 'trace_info', '') or '')
        if trace is not None and actual_trace != trace:
            raise AssertionError(f'预期 {expected.__name__} / trace={trace}，实际 trace={actual_trace}: {exc}') from exc
        if elapsed < min_elapsed - 0.05:
            raise AssertionError(f'预期等待约 {min_elapsed:g}s，实际 {elapsed:.3f}s 提前结束') from exc
        return f'预期 {expected.__name__}；实际 {type(exc).__name__}: {exc}' + (
            f'；trace={actual_trace}' if actual_trace else '')
    except Exception as exc:
        raise AssertionError(error_detail(f'预期 {expected.__name__}，实际异常不同', exc)) from exc
    raise AssertionError(f'预期 {expected.__name__}，实际返回 {type(value).__name__}')

def disable_dynamic_ids(captured: WebElement, *, timeout: float) -> bool:
    """捕获点可能是开关内部 span；仅对 role=switch 读取 aria-checked。"""
    switch = captured
    for depth in range(5):
        if switch is None:
            raise RuntimeError('动态 ID 捕获元素的父级链已结束，未找到 role="switch"')
        if switch.get_attribute('role') == 'switch':
            break
        if depth == 4:
            raise RuntimeError('动态 ID 捕获元素及其近邻父级中未找到 role="switch"')
        switch = switch.parent()

    def checked() -> bool:
        state = switch.get_attribute('aria-checked')
        if state not in ('true', 'false'):
            raise RuntimeError(f'动态 ID 开关 aria-checked 无效: {state!r}')
        return state == 'true'
    was_checked = checked()
    if not was_checked:
        return False
    switch.click(simulative=False, delay_after=0)
    deadline = time.monotonic() + timeout
    while checked():
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise RuntimeError(f"动态 ID 开关点击后 {timeout:g} 秒仍未关闭: aria-checked='true'")
        time.sleep(min(0.1, remaining))
    return True

def contract():
    sig = inspect.signature(WebElement.child_at)
    params = sig.parameters
    annotation = str(sig.return_annotation).replace('"', '').replace("'", '').replace(' ', '')
    ok = (tuple(params) == ('self', 'index', 'timeout')
          and params['index'].kind is inspect.Parameter.POSITIONAL_OR_KEYWORD
          and params['index'].default is inspect.Parameter.empty
          and params['index'].annotation in (int, 'int')
          and params['timeout'].kind is inspect.Parameter.KEYWORD_ONLY
          and params['timeout'].default == 5.0
          and annotation == 'WebElement|None')
    return result('api_contract', 'PASS' if ok else 'FAIL',
                  'index 必填、从 0 开始；timeout 仅限关键字、默认 5.0；返回 WebElement 或 None'
                  if ok else f'签名不符: {sig}')


class RootMarkup(HTMLParser):
    def __init__(self):
        super().__init__()
        self.tag, self.attrs = '', {}

    def handle_starttag(self, tag, attrs):
        if not self.tag:
            self.tag, self.attrs = tag.upper(), dict(attrs)


def summary(info):
    return f"{info['tag']} id={info['id']!r} class={info['class']!r}"


def check_dom_element(value, expected):
    if not isinstance(value, WebElement):
        raise AssertionError(f'预期 WebElement {summary(expected)}；实际 {type(value).__name__}')
    html = value.get_html()
    if not isinstance(html, str):
        raise AssertionError(f'元素 outerHTML 预期 str；实际 {type(html).__name__}')
    parsed = RootMarkup()
    parsed.feed(html)
    parsed.close()
    actual = {'tag': parsed.tag, 'id': parsed.attrs.get('id') or '',
              'class': parsed.attrs.get('class') or ''}
    if any(actual[key] != expected[key] for key in actual) or html != expected['html']:
        expected_hash = hashlib.sha256(expected['html'].encode('utf-8')).hexdigest()[:12]
        actual_hash = hashlib.sha256(html.encode('utf-8')).hexdigest()[:12]
        raise AssertionError(
            f'预期 {summary(expected)}；实际 {summary(actual)}；'
            f'HTML 摘要预期 {expected_hash}，实际 {actual_hash}')
    return summary(actual)


def check_child(value, expected, index):
    if expected is None:
        if value is not None:
            raise AssertionError(f'index={index!r} 预期 None；实际 {type(value).__name__}')
        return f'index={index!r} 预期 None；实际 None'
    detail = check_dom_element(value, expected)
    return f'index={index!r}；预期 {summary(expected)}；实际 {detail}；outerHTML 与原生直接子元素一致'


def validate_dom(snapshot):
    if not isinstance(snapshot, dict):
        raise AssertionError(f'DOM 参照应为 dict，实际 {type(snapshot).__name__}')

    def valid_info(info):
        return (isinstance(info, dict)
                and all(isinstance(info.get(key), str) for key in ('tag', 'id', 'class', 'html'))
                and bool(info['tag']) and bool(info['html']))

    target = snapshot.get('input')
    if not valid_info(target) or target['tag'] != 'INPUT' or target['id'] != TARGET_DOM_ID:
        raise AssertionError('DOM 参照不是指定文本输入框')
    if snapshot.get('leaf_children') != []:
        raise AssertionError(f'文本 input 预期无直接子元素，实际 {snapshot.get("leaf_children")!r}')
    ancestors = snapshot.get('ancestors')
    if not isinstance(ancestors, list) or not 1 <= len(ancestors) <= 32:
        raise AssertionError('缺少有界的原生祖先链')
    for depth, row in enumerate(ancestors, 1):
        if not isinstance(row, dict) or not valid_info(row.get('node')):
            raise AssertionError(f'第 {depth} 层容器信息无效')
        children = row.get('children')
        if not isinstance(children, list) or any(not valid_info(item) for item in children):
            raise AssertionError(f'第 {depth} 层直接子元素参照无效')
        if (type(row.get('descendant_count')) is not int or row['descendant_count'] < len(children)
                or type(row.get('non_element_count')) is not int or row['non_element_count'] < 0):
            raise AssertionError(f'第 {depth} 层原生节点计数不符')
    target_index = snapshot.get('target_index')
    if (type(target_index) is not int or not 0 <= target_index < len(ancestors[0]['children'])
            or ancestors[0]['children'][target_index] != target):
        raise AssertionError('输入框不在原生直接父容器的预期位置')
    multi_index = snapshot.get('multi_index')
    if type(multi_index) is not int or not 0 <= multi_index < len(ancestors):
        raise AssertionError('多项容器层号无效')
    multi = ancestors[multi_index]
    if (len(multi['children']) < 2 or multi['descendant_count'] <= len(multi['children'])
            or len({item['html'] for item in multi['children']}) != len(multi['children'])):
        raise AssertionError('多项容器须有可区分的直接子元素，且包含更深后代')
    return snapshot


def prepare_containers(target, snapshot, *, timeout):
    current, parent = target, None
    for depth, reference in enumerate(snapshot['ancestors'][:snapshot['multi_index'] + 1], 1):
        current = current.parent(timeout=timeout)
        try:
            check_dom_element(current, reference['node'])
        except Exception as exc:
            raise AssertionError(error_detail(f'第 {depth} 层容器准备失败', exc)) from exc
        if parent is None:
            parent = current
    return parent, current


def check_zero_timeout(container, expected):
    """只有零预算项可接受明确超时；正常返回仍须取得索引 0 的正确节点。"""
    try:
        value = container.child_at(0, timeout=0)
    except ActionError as exc:
        if exc.trace_info != 'web_dom_timeout':
            raise
        return (error_detail('零预算边界：预期正确子元素或明确超时；实际超时', exc)
                + '；本次未取得子元素，不按读取成功描述')
    return '零预算内返回子元素；' + check_child(value, expected, 0)


def run_child_at_cases(target, parent, multi, args, snapshot):
    results = []
    snapshot = validate_dom(snapshot)
    children = snapshot['ancestors'][snapshot['multi_index']]['children']
    target_index = snapshot['target_index']
    count = len(children)
    record_case(results, 'child_at_default', lambda:
                check_child(multi.child_at(0), children[0], 0))
    record_case(results, 'index_keyword', lambda:
                check_child(multi.child_at(index=1), children[1], 1))
    record_case(results, 'timeout_keyword', lambda:
                check_child(parent.child_at(target_index, timeout=args.timeout), snapshot['input'], target_index))
    record_case(results, 'none_timeout', lambda:
                check_child(multi.child_at(0, timeout=None), children[0], 0))
    record_case(results, 'zero_timeout', lambda: check_zero_timeout(multi, children[0]))

    def repeat():
        for _ in range(3):
            detail = check_child(multi.child_at(0, timeout=args.timeout), children[0], 0)
        return '连续三次与独立 DOM 比对通过；' + detail
    record_case(results, 'repeat_child_at', repeat)

    def all_indices():
        for index, expected in enumerate(children):
            check_child(multi.child_at(index, timeout=args.timeout), expected, index)
        return (f'逐个索引 0..{count - 1} 均与原生 children 对应；直接子元素 {count} 项，'
                f"全部后代 {snapshot['ancestors'][snapshot['multi_index']]['descendant_count']} 项")
    record_case(results, 'all_direct_indices', all_indices)
    record_case(results, 'last_index', lambda:
                check_child(multi.child_at(count - 1, timeout=args.timeout), children[-1], count - 1))
    record_case(results, 'index_equals_count', lambda:
                check_child(multi.child_at(count, timeout=args.timeout), None, count))
    record_case(results, 'large_index', lambda:
                check_child(multi.child_at(count + 1000, timeout=args.timeout), None, count + 1000))
    record_case(results, 'negative_index', lambda:
                check_child(multi.child_at(-1, timeout=args.timeout), None, -1))
    record_case(results, 'leaf_zero', lambda:
                check_child(target.child_at(0, timeout=args.timeout), None, 0))
    record_case(results, 'leaf_positive', lambda:
                check_child(target.child_at(1, timeout=args.timeout), None, 1))

    def returned_child():
        value = parent.child_at(target_index, timeout=args.timeout)
        check_child(value, snapshot['input'], target_index)
        if value.get_attribute('id') != TARGET_DOM_ID:
            raise AssertionError('返回元素读取 DOM id 不符')
        detail = check_child(value.child_at(0, timeout=args.timeout), None, 0)
        return '返回的 input 可读取 id 并继续调用 child_at()；' + detail
    record_case(results, 'returned_child_usable', returned_child)

    # 当前源码 int(index) 的兼容行为，与公开 int 参数的常规用法分开呈现。
    for label, supplied in (('numeric_string', '1'), ('fraction_truncation', 1.9), ('bool_index', True)):
        record_case(results, label, lambda supplied=supplied:
                    '当前实现 int(index) 转换后为 1；' +
                    check_child(multi.child_at(supplied, timeout=args.timeout), children[1], supplied))
    for label, invalid in (('index_none', None), ('index_text', 'bad'),
                           ('index_empty', ''), ('index_list', []),
                           ('index_dict', {}), ('index_fraction_string', '1.5')):
        record_case(results, label, lambda invalid=invalid:
                    f'输入 index={invalid!r}；' +
                    expect_exception(lambda: multi.child_at(invalid), InvalidParamsError))
    record_case(results, 'negative_timeout', lambda:
                expect_exception(lambda: multi.child_at(0, timeout=-1), InvalidParamsError))
    record_case(results, 'negative_fraction_timeout', lambda:
                expect_exception(lambda: multi.child_at(0, timeout=-0.1), InvalidParamsError))
    record_case(results, 'nonnumeric_timeout', lambda:
                expect_exception(lambda: multi.child_at(0, timeout='bad'), InvalidParamsError))
    record_case(results, 'missing_index', lambda:
                expect_exception(lambda: multi.child_at(), TypeError))
    record_case(results, 'positional_timeout', lambda:
                expect_exception(lambda: multi.child_at(0, 1), TypeError))
    record_case(results, 'unknown_keyword', lambda:
                expect_exception(lambda: multi.child_at(0, unsupported=True), TypeError))
    record_case(results, 'after_invalid', lambda:
                check_child(multi.child_at(0, timeout=args.timeout), children[0], 0))
    return results


def cleanup(resources, results, temp_root: Path):
    page, package, temp_dir = (resources.get(key) for key in ('page', 'package', 'temp_dir'))
    if page is not None:
        def close_page():
            page.close(ignore_beforeunload=True)
            return '本次创建页面的 close() 调用成功'
        record_case(results, 'cleanup_page', close_page)
    package_closed = True
    if package is not None:
        def close_package():
            package.close()
            return '本次 Package 的 close() 调用成功'
        package_closed = record_case(results, 'cleanup_package', close_package)
    if temp_dir is not None:
        def remove_copy():
            if not package_closed:
                raise RuntimeError(f'Package 关闭失败，保留其临时元素库供排查: {temp_dir}')
            resolved = temp_dir.resolve()
            if resolved.parent != temp_root.resolve() or not resolved.name.startswith('uiautoma-element-child-at-'):
                raise RuntimeError(f'临时目录归属不符，未删除: {resolved}')
            shutil.rmtree(resolved)
            if resolved.exists():
                raise RuntimeError(f'临时目录仍存在: {resolved}')
            return '本次临时元素库副本已删除并核对不存在'
        record_case(results, 'cleanup_temp', remove_copy)

def run(args):
    results = [contract()]
    if results[-1]['status'] != 'PASS' or args.contract_only:
        return results, 0 if results[-1]['status'] == 'PASS' else 1
    resources = {}
    stage, started = 'library_prepare', time.perf_counter()

    def prepared(detail):
        results.append(result(stage, 'PASS', detail, (time.perf_counter() - started) * 1000))

    try:
        if not args.library.is_dir():
            raise FileNotFoundError(f'元素库不存在: {args.library}')
        args.temp_root.mkdir(parents=True, exist_ok=True)
        temp_dir = Path(tempfile.mkdtemp(prefix='uiautoma-element-child-at-', dir=args.temp_root))
        resources['temp_dir'] = temp_dir
        library_copy = temp_dir / 'library'
        shutil.copytree(args.library, library_copy)
        package = uiautoma.open(str(library_copy), timeout=args.runtime_timeout, connect_timeout=args.runtime_timeout)
        resources['package'] = package
        for name in (TARGET_NAME, SWITCH):
            package.selector(name)
        prepared('元素库副本已打开，文本输入框和动态 ID 开关库项存在')

        stage, started = 'page_prepare', time.perf_counter()
        page = web.create(URL, mode=args.mode, load_timeout=args.load_timeout)
        resources['page'] = page
        if not isinstance(page, WebBrowser):
            raise AssertionError(f'预期 WebBrowser；实际 {type(page).__name__}')
        prepared('已打开本次独立测试页面')

        stage, started = 'dynamic_id_switch', time.perf_counter()
        switch = page.find(SWITCH, timeout=args.element_timeout)
        was_checked = disable_dynamic_ids(switch, timeout=args.element_timeout)
        prepared(f'aria-checked: {"true → false（点击一次）" if was_checked else "false（未点击）"}')

        stage, started = 'target_prepare', time.perf_counter()
        target = page.find(TARGET_NAME, timeout=args.element_timeout)
        if not isinstance(target, WebElement):
            raise AssertionError(f'预期 WebElement；实际 {type(target).__name__}')
        actual_id = target.get_attribute('id')
        if actual_id != TARGET_DOM_ID:
            raise AssertionError(f'预期 DOM id={TARGET_DOM_ID!r}；实际 {actual_id!r}')
        prepared(f'已取得 {TARGET_NAME}；实际 DOM id={actual_id!r}')

        stage, started = 'dom_oracle', time.perf_counter()
        snapshot = validate_dom(page.execute_javascript(DOM_ORACLE, TARGET_DOM_ID))
        multi_ref = snapshot['ancestors'][snapshot['multi_index']]
        prepared(f"原生 input 子元素=0；直接父容器子元素={len(snapshot['ancestors'][0]['children'])}；"
                 f"多项容器直接子元素={len(multi_ref['children'])}，全部后代={multi_ref['descendant_count']}，"
                 f"非元素直接子节点={multi_ref['non_element_count']}")

        stage, started = 'containers_prepare', time.perf_counter()
        parent, multi = prepare_containers(target, snapshot, timeout=args.timeout)
        prepared('用 parent() 取得容器并与原生祖先逐层核对；未用 child_at() 或 children() 生成期望值')

        stage, started = 'child_at_cases', time.perf_counter()
        results.extend(run_child_at_cases(target, parent, multi, args, snapshot))
    except Exception as exc:
        results.append(result(stage, 'FAIL', error_detail('检查失败', exc),
                              (time.perf_counter() - started) * 1000))
    finally:
        cleanup(resources, results, args.temp_root)
    return results, 0 if all(item['status'] == 'PASS' for item in results) else 1


def main(argv=None):
    parser = argparse.ArgumentParser(description='WebElement.child_at() 表单输入框及容器独立验收')
    parser.add_argument('--mode', choices=('chrome', 'edge'), default='chrome')
    parser.add_argument('--library', type=Path, default=LIBRARY)
    parser.add_argument('--timeout', type=float, default=2.0, help='有限超时用例使用的秒数；默认调用仍检查 API 的 5 秒默认值')
    parser.add_argument('--element-timeout', type=float, default=10)
    parser.add_argument('--runtime-timeout', type=float, default=20)
    parser.add_argument('--load-timeout', type=float, default=20)
    parser.add_argument('--contract-only', action='store_true')
    args = parser.parse_args(argv)
    args.temp_root = Path(__file__).resolve().parents[1] / '.pytest_tmp'
    for name in ('timeout', 'element_timeout', 'runtime_timeout', 'load_timeout'):
        value = getattr(args, name)
        if not math.isfinite(value) or value <= 0:
            parser.error(f'--{name.replace("_", "-")} 必须为正的有限秒数')

    print('UIAutoma Web API 测试', flush=True)
    print('API     : uiautoma.web.WebElement.child_at', flush=True)
    print(f'页面    : {URL}', flush=True)
    print(f'元素库  : {args.library}', flush=True)
    print(f'测试元素: {TARGET_NAME}', flush=True)
    print(f'SDK     : {uiautoma.__file__}', flush=True)
    print('参照    : 原生 children[index] 及 outerHTML；0 起始，越界返回 None', flush=True)
    started = time.perf_counter()
    results, code = run(args)
    print('进度     状态    测试项                      测试结果 / 耗时')
    print('─' * 100)
    for index, item in enumerate(results, 1):
        color = GREEN if item['status'] == 'PASS' else RED
        label = '通过' if item['status'] == 'PASS' else '失败'
        print(f"{index:02d}/{len(results):02d}    {color}[{label}]{RESET}  "
              f"{item['case_id']:<26}  {item['detail']}  {item['elapsed_ms']:.1f}ms")
    print('─' * 100)
    passed = sum(item['status'] == 'PASS' for item in results)
    print(f'{"测试通过" if code == 0 else "测试失败"} · {passed}/{len(results)} 通过 · '
          f'{(time.perf_counter() - started) * 1000:.1f}ms · 退出码 {code}')
    return code


if __name__ == '__main__':
    raise SystemExit(main())
