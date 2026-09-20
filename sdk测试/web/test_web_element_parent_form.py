"""WebElement.parent()：iframe/open shadow 表单输入框的独立验收脚本。

独立 DOM parentElement 提供父级链参照；脚本不修改表单值。
原 test_web_element_parent.py 保留，本文件仅依赖标准库和 uiautoma SDK。
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
  const ancestors = [];
  let current = input;
  for (let depth = 0; depth < 32; depth++) {
    const parent = current.parentElement;
    if (parent === null) break;
    ancestors.push({tag: parent.tagName, id: parent.id || '',
                    class: parent.getAttribute('class') || '', html: parent.outerHTML});
    current = parent;
  }
  if (current.parentElement !== null) throw new Error('原生父级链超过 32 层');
  return {
    input_id: input.id, input_tag: input.tagName, ancestors,
    boundary: {
      id: current.id || '', parent_element_null: current.parentElement === null,
      parent_node_type: current.parentNode ? current.parentNode.nodeType : null,
      shadow_host_id: current.getRootNode().host ? current.getRootNode().host.id : null
    }
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
    sig = inspect.signature(WebElement.parent)
    params = sig.parameters
    annotation = str(sig.return_annotation).replace('"', '').replace("'", '').replace(' ', '')
    ok = (
        tuple(params) == ('self', 'timeout')
        and params['timeout'].kind is inspect.Parameter.KEYWORD_ONLY
        and params['timeout'].default == 5.0
        and annotation == 'WebElement|None'
    )
    return result('api_contract', 'PASS' if ok else 'FAIL',
                  'timeout 仅限关键字、默认 5.0；返回 WebElement 或 None'
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


def check_parent(value, expected):
    if expected is None:
        if value is not None:
            raise AssertionError(f'预期无父元素时返回 None；实际 {type(value).__name__}')
        return '原生 parentElement=null；实际 parent() 返回 None'
    if not isinstance(value, WebElement):
        raise AssertionError(f'预期父元素 {summary(expected)}；实际 {type(value).__name__}')
    html = value.get_html()
    if not isinstance(html, str):
        raise AssertionError(f'父元素 outerHTML 预期 str；实际 {type(html).__name__}')
    parsed = RootMarkup()
    parsed.feed(html)
    parsed.close()
    actual = {'tag': parsed.tag, 'id': parsed.attrs.get('id') or '',
              'class': parsed.attrs.get('class') or ''}
    detail = f'预期 {summary(expected)}；实际 {summary(actual)}'
    if (any(actual[key] != expected[key] for key in actual) or html != expected['html']):
        expected_hash = hashlib.sha256(expected['html'].encode('utf-8')).hexdigest()[:12]
        actual_hash = hashlib.sha256(html.encode('utf-8')).hexdigest()[:12]
        raise AssertionError(f'{detail}；DOM 结构不一致，HTML 摘要预期 {expected_hash}，实际 {actual_hash}')
    return detail + '；outerHTML 与独立 DOM 参照一致'


def validate_dom(snapshot):
    if not isinstance(snapshot, dict):
        raise AssertionError(f'DOM 参照应为 dict，实际 {snapshot!r}')
    if snapshot.get('input_id') != TARGET_DOM_ID or snapshot.get('input_tag') != 'INPUT':
        raise AssertionError('DOM 参照不是指定文本输入框')
    ancestors = snapshot.get('ancestors')
    if not isinstance(ancestors, list) or not 1 <= len(ancestors) <= 32:
        raise AssertionError(f'原生祖先链应为 1–32 项，实际 {ancestors!r}')
    for index, item in enumerate(ancestors, 1):
        if (not isinstance(item, dict)
                or any(not isinstance(item.get(key), str) for key in ('tag', 'id', 'class', 'html'))
                or not item['tag'] or not item['html']):
            raise AssertionError(f'第 {index} 层原生父节点信息不完整')
    if ancestors[-1]['id'] != 'shadow-form-content':
        raise AssertionError(f'原生祖先链终点不是 Shadow 内容器: {ancestors[-1]["id"]!r}')
    boundary = snapshot.get('boundary')
    expected_boundary = {'id': 'shadow-form-content', 'parent_element_null': True,
                         'parent_node_type': 11, 'shadow_host_id': 'form-shadow-host'}
    if not isinstance(boundary, dict) or any(boundary.get(key) != value for key, value in expected_boundary.items()):
        raise AssertionError(f'原生 ShadowRoot 边界不符: {boundary!r}')
    return ancestors


def walk_ancestors(target, ancestors, *, timeout):
    current = target
    for depth, expected in enumerate(ancestors, 1):
        try:
            current = current.parent(timeout=timeout)
            check_parent(current, expected)
        except Exception as exc:
            raise AssertionError(error_detail(f'第 {depth} 层父级核对失败', exc)) from exc
    return current


def check_zero_timeout(target, expected):
    """零预算边界：允许精确的超时错误，成功返回时仍核验真实父节点。

    parent 的 timeout 是本次操作预算，没有 find(timeout=0) 的单次查询特例。
    当前 Runtime 将零预算归一到最小等待；不能保证异步浏览器请求及时完成。
    """
    try:
        value = target.parent(timeout=0)
    except ActionError as exc:
        if exc.trace_info != 'web_dom_timeout':
            raise
        return (error_detail('零预算边界：预期可取得正确父元素或明确超时；实际超时', exc)
                + '；本次未取得父元素，不按读取成功描述')
    return '零预算内取得父元素；' + check_parent(value, expected)


def run_parent_cases(target, args, snapshot):
    results = []
    ancestors = validate_dom(snapshot)
    expected = ancestors[0]
    record_case(results, 'parent_default', lambda: check_parent(target.parent(), expected))
    record_case(results, 'parent_keyword', lambda:
                check_parent(target.parent(timeout=args.timeout), expected))
    # 只在零预算用例接受明确的 web_dom_timeout，正数和默认预算仍要求成功。
    record_case(results, 'parent_zero_timeout', lambda:
                check_zero_timeout(target, expected))
    record_case(results, 'parent_none_timeout', lambda:
                check_parent(target.parent(timeout=None), expected))

    def repeat():
        details = [check_parent(target.parent(timeout=args.timeout), expected) for _ in range(3)]
        return '三次结果分别与原生父节点核对；' + details[-1]
    record_case(results, 'repeat_parent', repeat)

    terminal = {}
    def walk():
        terminal['element'] = walk_ancestors(target, ancestors, timeout=args.timeout)
        return f'原生 {len(ancestors)} 层祖先逐层核对通过；终点 #shadow-form-content'
    chain_ok = record_case(results, 'ancestor_chain', walk)
    if chain_ok:
        record_case(results, 'boundary_none', lambda:
                    check_parent(terminal['element'].parent(), None))
        def repeat_none():
            for _ in range(2):
                check_parent(terminal['element'].parent(timeout=args.timeout), None)
            return 'ShadowRoot 边界连续两次返回 None；没有当作 Element 返回 Shadow host'
        record_case(results, 'boundary_repeat', repeat_none)
    else:
        results.append(result('boundary_none', 'FAIL', '祖先链核对失败，未取得可靠终点；不能判定无父元素用例通过'))

    # parent 的超时转换拒绝所有负数，不能照搬 find 系列 timeout=-1 的规则。
    record_case(results, 'negative_timeout', lambda:
                expect_exception(lambda: target.parent(timeout=-1), InvalidParamsError))
    record_case(results, 'negative_fraction', lambda:
                expect_exception(lambda: target.parent(timeout=-0.1), InvalidParamsError))
    record_case(results, 'nonnumeric_timeout', lambda:
                expect_exception(lambda: target.parent(timeout='bad'), InvalidParamsError))
    record_case(results, 'positional_timeout', lambda:
                expect_exception(lambda: target.parent(1), TypeError))
    record_case(results, 'unknown_keyword', lambda:
                expect_exception(lambda: target.parent(unsupported=True), TypeError))
    record_case(results, 'after_invalid', lambda:
                check_parent(target.parent(timeout=args.timeout), expected))
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
            if resolved.parent != temp_root.resolve() or not resolved.name.startswith('uiautoma-element-parent-'):
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
        temp_dir = Path(tempfile.mkdtemp(prefix='uiautoma-element-parent-', dir=args.temp_root))
        resources['temp_dir'] = temp_dir
        library_copy = temp_dir / 'library'
        shutil.copytree(args.library, library_copy)
        package = uiautoma.open(str(library_copy), timeout=args.runtime_timeout, connect_timeout=args.runtime_timeout)
        resources['package'] = package
        for name in (TARGET_NAME, SWITCH):
            package.selector(name)
        prepared('元素库副本已打开，文本输入框与动态 ID 开关库项存在')

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
            raise AssertionError(f'预期 INPUT id={TARGET_DOM_ID!r}；实际 id={actual_id!r}')
        prepared(f'已取得 {TARGET_NAME}；实际 DOM id={actual_id!r}')

        stage, started = 'dom_oracle', time.perf_counter()
        snapshot = page.execute_javascript(DOM_ORACLE, TARGET_DOM_ID)
        ancestors = validate_dom(snapshot)
        prepared(f'原生直接父级 {summary(ancestors[0])}；祖先共 {len(ancestors)} 层；'
                 '终点 parentElement=null，parentNode 为 ShadowRoot')

        stage, started = 'parent_cases', time.perf_counter()
        results.extend(run_parent_cases(target, args, snapshot))
    except Exception as exc:
        results.append(result(stage, 'FAIL', error_detail('检查失败', exc),
                              (time.perf_counter() - started) * 1000))
    finally:
        cleanup(resources, results, args.temp_root)
    return results, 0 if all(item['status'] == 'PASS' for item in results) else 1


def main(argv=None):
    parser = argparse.ArgumentParser(description='WebElement.parent() 表单文本输入框独立验收')
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
    print('API     : uiautoma.web.WebElement.parent', flush=True)
    print(f'页面    : {URL}', flush=True)
    print(f'元素库  : {args.library}', flush=True)
    print(f'测试元素: {TARGET_NAME}', flush=True)
    print(f'SDK     : {uiautoma.__file__}', flush=True)
    print('参照    : 原生 parentElement 及 outerHTML；ShadowRoot 不属于父元素', flush=True)
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
