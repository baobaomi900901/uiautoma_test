"""WebElement.find_all() 表单输入框独立测试。

本文件包含完整准备、用例、断言、输出及清理逻辑，仅依赖标准库和 uiautoma SDK。
运行函数：run_find_all_cases()；入口：main()。"""
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
from uiautoma import ElementNotFoundError, InvalidParamsError, web
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
MULTI_NAME = 'web靶场_表单测试_ant_radio_label_相似元素'
DOM_ORACLE = """function (element, ids) {
  const frame = document.querySelector('#iframe-shadow-form');
  const doc = frame && frame.contentDocument;
  const host = doc && doc.querySelector('#form-shadow-host');
  const shadow = host && host.shadowRoot;
  const root = shadow && shadow.getElementById('shadow-form-content');
  if (!root) throw new Error('iframe/shadow 表单容器尚未就绪');
  return {
    inputs: ids.map(id => {
      const nodes = root.querySelectorAll('[id="' + id + '"]');
      const node = nodes[0];
      return {id, count: nodes.length, tag: node && node.tagName,
              children: node && node.children.length};
    }),
    radios: Array.from(root.querySelectorAll('.ant-radio-group .ant-radio-wrapper'))
      .map(node => node.textContent.trim())
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
    method = WebElement.find_all
    sig = inspect.signature(method) if callable(method) else None
    if sig is None:
        return result('api_contract', 'FAIL', 'WebElement.find_all 不存在')
    parameters = list(sig.parameters.values())
    names = tuple(sig.parameters)
    selector_name = 'selector'
    ok = names == ('self', selector_name, 'timeout') and parameters[1].kind is inspect.Parameter.POSITIONAL_OR_KEYWORD and (parameters[1].default is inspect.Parameter.empty) and (parameters[2].kind is inspect.Parameter.KEYWORD_ONLY) and (parameters[2].default == 10)
    annotation = str(sig.return_annotation).replace('"', '').replace("'", '').replace(' ', '')
    ok = ok and annotation == 'list[WebElement]'
    return result('api_contract', 'PASS' if ok else 'FAIL', f'{selector_name} 必填，timeout 仅限关键字且默认 10；返回 list[WebElement]' if ok else f'公开签名不符合合同: {sig}')

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

def expect_exception(action: Callable, expected):
    try:
        value = action()
    except expected as exc:
        return f'预期 {expected.__name__}；实际 {type(exc).__name__}: {exc}'
    except Exception as exc:
        raise AssertionError(error_detail(f'预期 {expected.__name__}，实际异常不同', exc)) from exc
    raise AssertionError(f'预期 {expected.__name__}，实际返回 {value!r}')

def check_matches(value, expected: list[str], *, by_text: bool = False):
    if not isinstance(value, list):
        raise AssertionError(f'预期 list[WebElement]，实际 {type(value).__name__}')
    if any(not isinstance(item, WebElement) for item in value):
        raise AssertionError(f'预期所有项均为 WebElement，实际类型 {[type(item).__name__ for item in value]}')
    actual = [item.get_text().strip() if by_text else item.get_attribute('id') for item in value]
    detail = f'预期 {len(expected)} 项 {expected!r}；实际 {len(value)} 项 {actual!r}'
    if Counter(actual) != Counter(expected):
        if expected and not value:
            detail += '；页面基线有目标，作用域返回空列表（参照 #64，仍计失败）'
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
        if not value:
            detail += '；页面基线有目标，作用域返回空列表（参照 #64，仍计失败）'
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
                or item.get('count') != 1 or item.get('tag') != 'INPUT'
                or item.get('children') != 0):
            raise AssertionError(f'预期容器内唯一叶子 INPUT {expected_id!r}，实际 {item!r}')
    texts = snapshot.get('radios')
    if (not isinstance(texts, list) or len(texts) < 2
            or any(not isinstance(text, str) or not text for text in texts)
            or len(set(texts)) != len(texts)):
        raise AssertionError(f'多项参照需要至少两个文本可区分的 Ant 单选项，实际 {texts!r}')
    return texts


def check_empty_scope(scope, selector: str, timeout: float):
    started = time.perf_counter()
    detail = check_matches(scope.find_all(selector, timeout=timeout), [])
    elapsed = time.perf_counter() - started
    # timeout=0 只查一次，不对跨进程通信耗时设脆弱的毫秒上限。
    if timeout > 0 and elapsed < timeout - 0.05:
        raise AssertionError(f'预期等待约 {timeout:g}s，实际提前返回 {elapsed:.3f}s；{detail}')
    return f'目标已在页面中定位，但不在输入框子树内；{detail}；等待 {elapsed:.3f}s'


def run_find_all_cases(root, package, args, seeds, radio_texts):
    results = []
    # 分别核对实际捕获节点；密码库项是 span，不能替换成内部 input 来冒充命中。
    for name, dom_id in INPUT_IDS.items():
        case_id = 'name_' + dom_id.removeprefix('form-controls-ant-')
        record_case(results, case_id, lambda name=name, dom_id=dom_id:
                    name + '；' + check_input_matches(root.find_all(name, timeout=args.timeout), name))

    name = TARGETS[0]
    record_case(results, 'selector_object', lambda:
                check_input_matches(root.find_all(package.selector(name), timeout=args.timeout), name))
    record_case(results, 'zero_timeout_hit', lambda:
                check_input_matches(root.find_all(name, timeout=0), name))
    record_case(results, 'multiple_matches', lambda:
                MULTI_NAME + '；' + check_matches(
                    root.find_all(MULTI_NAME, timeout=args.timeout), radio_texts, by_text=True))

    # 区分“库里没有该名称”和“库条目有效但子树没有匹配”。
    missing_name = f'__uiautoma_missing_{time.time_ns()}__'
    record_case(results, 'unknown_library_name', lambda:
                expect_exception(lambda: root.find_all(missing_name, timeout=0), ElementNotFoundError))
    leaf, outside_name = seeds[TARGETS[0]], TARGETS[1]
    record_case(results, 'empty_scope_zero', lambda:
                check_empty_scope(leaf, outside_name, 0))
    record_case(results, 'empty_scope_wait', lambda:
                check_empty_scope(leaf, outside_name, args.empty_timeout))

    for label, invalid in (('selector_none', None), ('selector_integer', 123),
                           ('selector_empty', ''), ('selector_blank', '   ')):
        record_case(results, label, lambda invalid=invalid:
                    expect_exception(lambda: root.find_all(invalid, timeout=0), InvalidParamsError))
    record_case(results, 'invalid_timeout', lambda:
                expect_exception(lambda: root.find_all(name, timeout=-2), InvalidParamsError))
    record_case(results, 'invalid_timeout_type', lambda:
                expect_exception(lambda: root.find_all(name, timeout='bad'), InvalidParamsError))
    record_case(results, 'missing_selector', lambda:
                expect_exception(lambda: root.find_all(), TypeError))
    record_case(results, 'positional_timeout', lambda:
                expect_exception(lambda: root.find_all(name, 1), TypeError))
    record_case(results, 'unknown_keyword', lambda:
                expect_exception(lambda: root.find_all(name, unsupported=True), TypeError))
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
            if resolved.parent != temp_root.resolve() or not resolved.name.startswith('uiautoma-element-find-all-'):
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
        temp_dir = Path(tempfile.mkdtemp(prefix='uiautoma-element-find-all-', dir=args.temp_root))
        resources['temp_dir'] = temp_dir
        library_copy = temp_dir / 'library'
        shutil.copytree(args.library, library_copy)
        package = uiautoma.open(str(library_copy), timeout=args.runtime_timeout, connect_timeout=args.runtime_timeout)
        resources['package'] = package
        for name in (*TARGETS, SWITCH, MULTI_NAME):
            package.selector(name)
        prepared('已打开元素库副本；四个输入框、动态 ID 开关及相似元素库项均存在')

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
            detail = check_input_matches([item], name)
            seeds[name] = item
            prepared(name + '；' + detail)

        stage, started = 'root_prepare', time.perf_counter()
        root = find_common_root(seeds)
        if root is None:
            raise RuntimeError('四个输入框未能全部到达靶场共同容器 #shadow-form-content')
        prepared('四条父级链均到达 #shadow-form-content；未比较 Runtime .id')

        stage, started = 'dom_oracle', time.perf_counter()
        snapshot = page.execute_javascript(DOM_ORACLE, list(INPUT_IDS.values()))
        radio_texts = validate_dom(snapshot)
        prepared(f'独立 DOM 核对：四个输入框各 1 项且均无子元素；Ant 单选标签 {radio_texts!r}')

        stage, started = 'find_all_cases', time.perf_counter()
        results.extend(run_find_all_cases(root, package, args, seeds, radio_texts))
    except Exception as exc:
        results.append(result(stage, 'FAIL', error_detail('检查失败', exc),
                              (time.perf_counter() - started) * 1000))
    finally:
        # 资源一经创建即登记，准备中途失败也走相同清理路径。
        cleanup(resources, results, args.temp_root)
    return results, 0 if all(item['status'] == 'PASS' for item in results) else 1


def main(argv=None):
    import argparse
    parser = argparse.ArgumentParser(description='WebElement.find_all() 表单输入框专项验收')
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
    print('API     : uiautoma.web.WebElement.find_all', flush=True)
    print(f'页面    : {URL}', flush=True)
    print(f'元素库  : {args.library}', flush=True)
    print(f'SDK     : {uiautoma.__file__}', flush=True)
    if not args.contract_only:
        print('参照    : 页面定位 + 独立 DOM；#64 相关空列表仍按实际预期判失败', flush=True)
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
