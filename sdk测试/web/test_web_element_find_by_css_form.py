"""WebElement.find_by_css() 表单输入框独立测试。

本文件包含完整准备、用例、断言、输出及清理逻辑，仅依赖标准库和 uiautoma SDK。
运行函数：run_find_by_css_cases()；入口：main()。"""
from __future__ import annotations
import inspect
import math
import shutil
import tempfile
import time
from collections import Counter
from html.parser import HTMLParser
from pathlib import Path
from typing import Callable
import uiautoma
from uiautoma import AmbiguousElementError, ElementNotFoundError, InvalidParamsError, web
from uiautoma._core import RpcProtocolError
from uiautoma.web import WebBrowser, WebElement
__test__ = False
URL = 'https://baobaomi900901.github.io/xpath/#/iframe-shadow-form'
LIBRARY = Path('D:\\code\\元素库\\260902_web元素')
SWITCH = 'web靶场_表单测试_控制表单组件id是否为动态的开关'
PASSWORD_NAME = 'web靶场_表单测试_ant_密码输入框'
# 这些是对应控件内部 INPUT 的 id。密码库项捕获的是外层 span，并无此 id。
INPUT_IDS = {
    'web靶场_表单测试_ant_输入框': 'form-controls-ant-text',
    'web靶场_表单测试_ant_密码输入框': 'form-controls-ant-password',
    'web靶场_表单测试_ant_邮箱输入框': 'form-controls-ant-email',
    'web靶场_表单测试_ant_数字输入框': 'form-controls-ant-number',
}
TARGETS = tuple(INPUT_IDS)
# 密码库项是包装 span；CSS 用例分别检查包装 span 和其内部 input。
CSS_CASES = (
    ('css_text_default', 'input#form-controls-ant-text', TARGETS[0], False),
    ('css_password_wrapper', 'span.ant-input-affix-wrapper.ant-input-password', PASSWORD_NAME, True),
    ('css_password_input', '.ant-input-password > input#form-controls-ant-password', PASSWORD_NAME, False),
    ('css_email', 'input[id="form-controls-ant-email"][placeholder="user@example.com"]', TARGETS[2], False),
    ('css_number', 'input#form-controls-ant-number[role="spinbutton"]', TARGETS[3], False),
)
TEXT_CSS = CSS_CASES[0][1]
EMAIL_CSS = CSS_CASES[3][1]
MISSING_CSS = 'input[data-uiautoma-css-absent="true"]'
DOM_ORACLE = """function (element, args) {
  const frame = document.querySelector('#iframe-shadow-form');
  const doc = frame && frame.contentDocument;
  const host = doc && doc.querySelector('#form-shadow-host');
  const shadow = host && host.shadowRoot;
  const root = shadow && shadow.getElementById('shadow-form-content');
  if (!root) throw new Error('iframe/shadow 表单容器尚未就绪');
  const password = root.querySelector('#form-controls-ant-password');
  const wrapper = password && password.parentElement;
  return {
    inputs: args.ids.map(id => {
      const nodes = root.querySelectorAll('[id="' + id + '"]');
      const node = nodes[0];
      return {id, count: nodes.length, tag: node && node.tagName,
              children: node && node.children.length};
    }),
    queries: args.queries.map(css => {
      const nodes = Array.from(root.querySelectorAll(css));
      return {css, count: nodes.length, nodes: nodes.map(node => ({tag: node.tagName, id: node.id || null}))};
    }),
    multiple_count: root.querySelectorAll('input').length,
    missing_count: root.querySelectorAll(args.missing).length,
    self_count: root.querySelectorAll('#shadow-form-content').length,
    password_input_count: wrapper ? wrapper.querySelectorAll('input').length : 0
  };
}"""

GREEN, RED, YELLOW, RESET = ('\x1b[92m', '\x1b[91m', '\x1b[93m', '\x1b[0m')

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

def contract():
    sig = inspect.signature(WebElement.find_by_css)
    params = sig.parameters
    ok = (
        tuple(params) == ('self', 'css_selector', 'timeout')
        and params['css_selector'].kind is inspect.Parameter.POSITIONAL_OR_KEYWORD
        and params['css_selector'].default is inspect.Parameter.empty
        and params['timeout'].kind is inspect.Parameter.KEYWORD_ONLY
        and params['timeout'].default == 10
        and str(sig.return_annotation).replace('"', '').replace("'", '') == 'WebElement'
    )
    return result('api_contract', 'PASS' if ok else 'FAIL',
                  'css_selector 必填；timeout 仅限关键字且默认 10；返回唯一 WebElement'
                  if ok else f'公开签名不符合合同: {sig}')

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

def check_matches(value, expected: list[str], *, by_text: bool = False):
    if not isinstance(value, list):
        raise AssertionError(f'预期 list[WebElement]，实际 {type(value).__name__}')
    if any(not isinstance(item, WebElement) for item in value):
        raise AssertionError(f'预期所有项均为 WebElement，实际类型 {[type(item).__name__ for item in value]}')
    actual = [item.get_text().strip() if by_text else item.get_attribute('id') for item in value]
    detail = f'预期 {len(expected)} 项 {expected!r}；实际 {len(value)} 项 {actual!r}'
    if Counter(actual) != Counter(expected):
        raise AssertionError(detail)
    return detail

class CapturedMarkup(HTMLParser):
    """解析 get_html() 的单个元素 outerHTML，仅保留身份字段，不输出表单值。"""
    def __init__(self):
        super().__init__()
        self.root_tag = None
        self.root_attrs = {}
        self.inputs = []

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        if self.root_tag is None:
            self.root_tag = tag
            self.root_attrs = attributes
        elif tag == 'input':
            self.inputs.append((attributes.get('id'), attributes.get('type')))


def check_input_matches(value, name: str):
    expected_id = INPUT_IDS[name]
    if name != PASSWORD_NAME:
        return check_matches(value, [expected_id])
    if not isinstance(value, list):
        raise AssertionError(f'密码库项预期 list[WebElement]，实际 {type(value).__name__}')
    if len(value) != 1:
        detail = f'密码库项预期 1 项 span.ant-input-affix-wrapper；实际 {len(value)} 项'
        raise AssertionError(detail)
    if not isinstance(value[0], WebElement):
        raise AssertionError(f'密码库项预期 WebElement，实际 {type(value[0]).__name__}')
    html = value[0].get_html()
    if not isinstance(html, str):
        raise AssertionError(f'密码库项 HTML 预期 str，实际 {type(html).__name__}')
    markup = CapturedMarkup()
    markup.feed(html)
    markup.close()
    actual = {'tag': markup.root_tag, 'id': markup.root_attrs.get('id'),
              'class': markup.root_attrs.get('class'), 'inputs': markup.inputs}
    detail = (f'预期 1 项 span.ant-input-affix-wrapper，内含 input#{expected_id}[type=password]；'
              f'实际 1 项 {actual!r}')
    if (markup.root_tag != 'span'
            or 'ant-input-affix-wrapper' not in (markup.root_attrs.get('class') or '').split()
            or markup.inputs != [(expected_id, 'password')]):
        raise AssertionError(detail)
    return detail


def check_element(value, expected_id: str):
    if not isinstance(value, WebElement):
        raise AssertionError(f'预期唯一 WebElement，实际 {type(value).__name__}')
    actual_id = value.get_attribute('id')
    detail = f'预期 DOM id={expected_id!r}；实际 {actual_id!r}'
    if actual_id != expected_id:
        raise AssertionError(detail)
    return detail


def check_saved_element(value, name: str):
    if not isinstance(value, WebElement):
        raise AssertionError(f'{name} 预期唯一 WebElement，实际 {type(value).__name__}')
    return check_input_matches([value], name)


def check_css_target(value, name: str, wrapper: bool):
    return check_saved_element(value, name) if wrapper else check_element(value, INPUT_IDS[name])


def find_common_root(seeds: dict[str, WebElement]):
    """核对同一靶场 iframe/open shadow 内所有输入框的固定公共容器。

    SDK 的 .id 是每次查询分配的 Runtime 对象标识，不能用于祖先链求交集。
    本靶场的 #shadow-form-content 是现有容器，包含 Ant 与原生两侧表单。
    使用公开 get_attribute('id') 读取 DOM id，并要求每条祖先链都到达该容器。
    """
    root = None
    for name in TARGETS:
        current = seeds[name]
        for _ in range(32):
            if current is None:
                return None
            try:
                if current.get_attribute('id') == 'shadow-form-content':
                    if root is None:
                        root = current
                    break
                current = current.parent()
            except Exception as exc:
                raise RuntimeError(error_detail(f'{name} 的共同容器准备失败', exc)) from exc
        else:
            return None
    return root

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

def validate_dom(snapshot):
    if not isinstance(snapshot, dict):
        raise AssertionError(f'DOM 参照预期 dict，实际 {snapshot!r}')
    inputs = snapshot.get('inputs')
    if not isinstance(inputs, list) or len(inputs) != len(TARGETS):
        raise AssertionError(f'DOM 输入框参照不完整: {inputs!r}')
    for item, expected_id in zip(inputs, INPUT_IDS.values()):
        if (not isinstance(item, dict) or item.get('id') != expected_id
                or item.get('count') != 1 or item.get('tag') != 'INPUT' or item.get('children') != 0):
            raise AssertionError(f'预期唯一叶子 INPUT {expected_id!r}，实际 {item!r}')
    queries = snapshot.get('queries')
    if not isinstance(queries, list) or len(queries) != len(CSS_CASES):
        raise AssertionError(f'CSS 独立参照不完整: {queries!r}')
    for actual, (label, css, name, wrapper) in zip(queries, CSS_CASES):
        nodes = actual.get('nodes') if isinstance(actual, dict) else None
        if (not isinstance(nodes, list) or len(nodes) != 1
                or actual.get('css') != css or actual.get('count') != 1):
            raise AssertionError(f'{label} 预期 CSS 唯一命中，实际 {actual!r}')
        node = nodes[0]
        if (not isinstance(node, dict) or node.get('tag') != ('SPAN' if wrapper else 'INPUT')
                or (not wrapper and node.get('id') != INPUT_IDS[name])):
            raise AssertionError(f'{label} CSS 命中错误节点: {node!r}')
    multiple = snapshot.get('multiple_count')
    if type(multiple) is not int or multiple < 2:
        raise AssertionError(f'歧义参照预期 input 至少 2 项，实际 {multiple!r}')
    for key, expected in (('missing_count', 0), ('self_count', 0), ('password_input_count', 1)):
        if snapshot.get(key) != expected:
            raise AssertionError(f'{key} 预期 {expected}，实际 {snapshot.get(key)!r}')
    return f'5 个 CSS 各唯一命中；input 多项={multiple}；不存在选择器及根自身均为 0 项；密码包装内 input=1'


def run_find_by_css_cases(root, args, seeds):
    results = []
    for index, (label, css, name, wrapper) in enumerate(CSS_CASES):
        if index == 0:
            record_case(results, label, lambda css=css, name=name, wrapper=wrapper:
                        check_css_target(root.find_by_css(css), name, wrapper))
        else:
            record_case(results, label, lambda css=css, name=name, wrapper=wrapper:
                        check_css_target(root.find_by_css(css, timeout=args.timeout), name, wrapper))
    record_case(results, 'keyword_css', lambda:
                check_element(root.find_by_css(css_selector=TEXT_CSS, timeout=args.timeout), INPUT_IDS[TARGETS[0]]))
    record_case(results, 'zero_timeout_hit', lambda:
                check_element(root.find_by_css(TEXT_CSS, timeout=0), INPUT_IDS[TARGETS[0]]))

    def repeat():
        checks = [check_element(root.find_by_css(TEXT_CSS, timeout=0), INPUT_IDS[TARGETS[0]]) for _ in range(3)]
        return '连续三次分别核对 DOM id；' + checks[-1]
    record_case(results, 'repeat_read', repeat)
    record_case(results, 'ambiguous', lambda:
                expect_exception(lambda: root.find_by_css('input', timeout=0), AmbiguousElementError))
    record_case(results, 'missing_zero', lambda:
                expect_exception(lambda: root.find_by_css(MISSING_CSS, timeout=0), ElementNotFoundError))
    record_case(results, 'missing_wait', lambda:
                expect_exception(lambda: root.find_by_css(MISSING_CSS, timeout=args.empty_timeout),
                                 ElementNotFoundError, min_elapsed=args.empty_timeout))
    record_case(results, 'scope_outside', lambda:
                expect_exception(lambda: seeds[TARGETS[0]].find_by_css(EMAIL_CSS, timeout=0), ElementNotFoundError))
    record_case(results, 'scope_excludes_self', lambda:
                expect_exception(lambda: root.find_by_css('#shadow-form-content', timeout=0), ElementNotFoundError))
    record_case(results, 'password_inner_scope', lambda:
                check_element(seeds[PASSWORD_NAME].find_by_css('input', timeout=0), INPUT_IDS[PASSWORD_NAME]))

    # 当前 SDK 快照把 invalid_css_selector 映射为 RpcProtocolError；
    # 必须同时核对 trace，不能把其它 Runtime 异常当作语法拒绝通过。
    record_case(results, 'invalid_css_syntax', lambda:
                expect_exception(lambda: root.find_by_css('input[', timeout=0),
                                 RpcProtocolError, trace='invalid_css_selector'))
    record_case(results, 'after_invalid_css', lambda:
                check_element(root.find_by_css(TEXT_CSS, timeout=0), INPUT_IDS[TARGETS[0]]))
    for label, invalid in (('selector_none', None), ('selector_integer', 123),
                           ('selector_empty', ''), ('selector_blank', '   ')):
        record_case(results, label, lambda invalid=invalid:
                    expect_exception(lambda: root.find_by_css(invalid, timeout=0), InvalidParamsError))
    record_case(results, 'invalid_timeout', lambda:
                expect_exception(lambda: root.find_by_css(TEXT_CSS, timeout=-2), InvalidParamsError))
    record_case(results, 'invalid_timeout_type', lambda:
                expect_exception(lambda: root.find_by_css(TEXT_CSS, timeout='bad'), InvalidParamsError))
    record_case(results, 'missing_selector', lambda:
                expect_exception(lambda: root.find_by_css(), TypeError))
    record_case(results, 'positional_timeout', lambda:
                expect_exception(lambda: root.find_by_css(TEXT_CSS, 1), TypeError))
    record_case(results, 'unknown_keyword', lambda:
                expect_exception(lambda: root.find_by_css(TEXT_CSS, unsupported=True), TypeError))
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
            if resolved.parent != temp_root.resolve() or not resolved.name.startswith('uiautoma-element-css-'):
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
        temp_dir = Path(tempfile.mkdtemp(prefix='uiautoma-element-css-', dir=args.temp_root))
        resources['temp_dir'] = temp_dir
        library_copy = temp_dir / 'library'
        shutil.copytree(args.library, library_copy)
        package = uiautoma.open(str(library_copy), timeout=args.runtime_timeout, connect_timeout=args.runtime_timeout)
        resources['package'] = package
        for name in (*TARGETS, SWITCH):
            package.selector(name)
        prepared('已打开元素库副本；四个输入框与动态 ID 开关库项均存在')

        stage, started = 'page_prepare', time.perf_counter()
        page = web.create(URL, mode=args.mode, load_timeout=args.load_timeout)
        resources['page'] = page
        if not isinstance(page, WebBrowser):
            raise AssertionError(f'预期 WebBrowser，实际 {type(page).__name__}')
        prepared('已新建本次测试页面')

        stage, started = 'dynamic_id_switch', time.perf_counter()
        switch = page.find(SWITCH, timeout=args.element_timeout)
        was_checked = disable_dynamic_ids(switch, timeout=args.element_timeout)
        prepared(f'aria-checked: {"true → false（点击一次）" if was_checked else "false（未点击）"}')

        seeds = {}
        for name, expected_id in INPUT_IDS.items():
            stage = 'page_' + expected_id.removeprefix('form-controls-ant-')
            started = time.perf_counter()
            item = page.find(name, timeout=args.element_timeout)
            detail = check_saved_element(item, name)
            seeds[name] = item
            prepared(name + '；' + detail)

        stage, started = 'root_prepare', time.perf_counter()
        root = find_common_root(seeds)
        if root is None:
            raise RuntimeError('四个输入框未能全部到达靶场共同容器 #shadow-form-content')
        prepared('四条父级链均到达 #shadow-form-content；未比较 Runtime .id')

        stage, started = 'dom_oracle', time.perf_counter()
        snapshot = page.execute_javascript(DOM_ORACLE, {
            'ids': list(INPUT_IDS.values()),
            'queries': [case[1] for case in CSS_CASES],
            'missing': MISSING_CSS,
        })
        prepared(validate_dom(snapshot))

        stage, started = 'find_by_css_cases', time.perf_counter()
        results.extend(run_find_by_css_cases(root, args, seeds))
    except Exception as exc:
        results.append(result(stage, 'FAIL', error_detail('检查失败', exc),
                              (time.perf_counter() - started) * 1000))
    finally:
        # 资源一经创建即登记，准备中途失败也走相同清理路径。
        cleanup(resources, results, args.temp_root)
    return results, 0 if all(item['status'] == 'PASS' for item in results) else 1


def main(argv=None):
    import argparse
    parser = argparse.ArgumentParser(description='WebElement.find_by_css() 表单输入框专项验收')
    parser.add_argument('--mode', choices=('chrome', 'edge'), default='chrome')
    parser.add_argument('--library', type=Path, default=LIBRARY)
    parser.add_argument('--timeout', type=float, default=5)
    parser.add_argument('--empty-timeout', type=float, default=0.3)
    parser.add_argument('--element-timeout', type=float, default=10)
    parser.add_argument('--runtime-timeout', type=float, default=20)
    parser.add_argument('--load-timeout', type=float, default=20)
    parser.add_argument('--contract-only', action='store_true')
    args = parser.parse_args(argv)
    args.temp_root = Path(__file__).resolve().parents[1] / '.pytest_tmp'
    for name in ('timeout', 'empty_timeout', 'element_timeout', 'runtime_timeout', 'load_timeout'):
        value = getattr(args, name)
        if not math.isfinite(value) or value < 0 or (name != 'timeout' and value == 0):
            parser.error(f'--{name.replace("_", "-")} 必须为有限秒数（仅 --timeout 允许 0）')

    print('UIAutoma Web API 测试', flush=True)
    print('API     : uiautoma.web.WebElement.find_by_css', flush=True)
    print(f'页面    : {URL}', flush=True)
    print(f'元素库  : {args.library}', flush=True)
    print(f'SDK     : {uiautoma.__file__}', flush=True)
    if not args.contract_only:
        print('参照    : 元素库定位根容器；CSS 查询当前子树；原生 DOM 独立核对', flush=True)
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
