"""WebElement.find() 表单输入框独立测试。

本文件包含完整准备、用例、断言、输出及清理逻辑，仅依赖标准库和 uiautoma SDK。
运行函数：run_find_cases()；入口：main()。"""
from __future__ import annotations
import inspect
import shutil
import tempfile
import time
from pathlib import Path
from typing import Callable
import uiautoma
from uiautoma import AmbiguousElementError, ElementNotFoundError, InvalidParamsError, web
from uiautoma.web import WebBrowser, WebElement
__test__ = False
URL = 'https://baobaomi900901.github.io/xpath/#/iframe-shadow-form'
LIBRARY = Path('D:\\code\\元素库\\260902_web元素')
SWITCH = 'web靶场_表单测试_控制表单组件id是否为动态的开关'
TARGETS = ('web靶场_表单测试_ant_输入框', 'web靶场_表单测试_ant_密码输入框', 'web靶场_表单测试_ant_邮箱输入框')
GREEN, RED, YELLOW, RESET = ('\x1b[92m', '\x1b[91m', '\x1b[93m', '\x1b[0m')

def result(case_id: str, status: str, detail: str):
    return {'case_id': case_id, 'status': status, 'detail': detail}

def error_detail(prefix: str, exc: BaseException) -> str:
    detail = f'{prefix}: {type(exc).__name__}: {exc}'
    trace = str(getattr(exc, 'trace_info', '') or '')
    if trace:
        detail += f' [trace={trace}]'
    return detail

def contract():
    method = WebElement.find
    sig = inspect.signature(method) if callable(method) else None
    if sig is None:
        return result('api_contract', 'FAIL', 'WebElement.find 不存在')
    parameters = list(sig.parameters.values())
    names = tuple(sig.parameters)
    selector_name = 'selector'
    ok = names == ('self', selector_name, 'timeout') and parameters[1].kind is inspect.Parameter.POSITIONAL_OR_KEYWORD and (parameters[1].default is inspect.Parameter.empty) and (parameters[2].kind is inspect.Parameter.KEYWORD_ONLY) and (parameters[2].default == 10)
    return result('api_contract', 'PASS' if ok else 'FAIL', f'{selector_name} 必填，timeout 仅限关键字且默认 10' if ok else f'公开签名不符合合同: {sig}')

def call(action: Callable):
    try:
        return (True, action(), None)
    except Exception as exc:
        return (False, None, exc)

def expect_exception(label: str, action: Callable, expected):
    ok, value, exc = call(action)
    if not ok and isinstance(exc, expected):
        return result(label, 'PASS', f'{type(exc).__name__} 正确拒绝')
    if not ok:
        return result(label, 'FAIL', f'应为 {expected.__name__}，实际为 {type(exc).__name__}: {exc}')
    return result(label, 'FAIL', f'调用未被拒绝，返回 {value!r}')

def find_common_root(seeds: dict[str, WebElement]):
    """核对同一靶场 iframe/open shadow 内三个输入框的固定公共容器。

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

def prepare(args):
    temp_dir = Path(tempfile.mkdtemp(prefix='uiautoma-element-find-', dir=str(args.temp_root)))
    library_copy = temp_dir / 'library'
    shutil.copytree(args.library, library_copy)
    package = None
    page = None
    try:
        package = uiautoma.open(str(library_copy), timeout=args.runtime_timeout, connect_timeout=args.runtime_timeout)
        page = web.create(URL, mode=args.mode, load_timeout=args.load_timeout)
        if not isinstance(page, WebBrowser):
            raise RuntimeError('web.create 未返回 WebBrowser')
        switch = page.find(SWITCH, timeout=args.element_timeout)
        was_checked = disable_dynamic_ids(switch, timeout=args.element_timeout)
        seeds = {name: page.find(name, timeout=args.element_timeout) for name in TARGETS}
        root = find_common_root(seeds)
        if root is None:
            raise RuntimeError('三个输入框未能全部到达靶场共同容器 #shadow-form-content')
        return (package, page, root, seeds, temp_dir, was_checked)
    except Exception:
        if page is not None:
            try:
                page.close(ignore_beforeunload=True)
            except Exception:
                pass
        if package is not None:
            try:
                package.close()
            except Exception:
                pass
        shutil.rmtree(temp_dir, ignore_errors=True)
        raise

def selector_values():
    return {'unique': list(TARGETS), 'empty': '__uiautoma_missing_form_element__', 'invalid': (None, 123, '')}


def run_find_cases(root, package, args):
    results = []
    values = selector_values()
    all_ok = True
    details = []
    for name in values['unique']:
        ok, value, exc = call(lambda: root.find(name, timeout=args.timeout))
        expected_type = WebElement
        one_ok = ok and isinstance(value, expected_type)
        one_ok = one_ok and value.name == name
        details.append(f"{name.rsplit('_', 1)[-1]}={value.name!r}") if one_ok else details.append(f"{name.rsplit('_', 1)[-1]} 失败")
        all_ok = all_ok and one_ok
    results.append(result('unique_matches', 'PASS' if all_ok else 'FAIL', '；'.join(details) if all_ok else '至少一个输入框唯一匹配失败'))
    selector = package.selector(TARGETS[0])
    ok, value, exc = call(lambda: root.find(selector, timeout=0))
    selector_ok = ok and (isinstance(value, WebElement) and value.name == TARGETS[0] or (isinstance(value, list) and len(value) == 1 and (value[0].name == TARGETS[0])))
    results.append(result('selector_object', 'PASS' if selector_ok else 'FAIL', 'Selector 对象调用结果与名称字符串一致' if selector_ok else error_detail('Selector 对象调用失败', exc) if exc else 'Selector 对象返回结果不符'))
    results.append(expect_exception('missing_element', lambda: root.find(values['empty'], timeout=0), ElementNotFoundError))
    valid_selector = TARGETS[0]
    results.append(expect_exception('invalid_timeout', lambda: root.find(valid_selector, timeout=-2), InvalidParamsError))
    results.append(expect_exception('invalid_timeout_type', lambda: root.find(valid_selector, timeout='bad'), InvalidParamsError))
    results.append(expect_exception('missing_selector', lambda: root.find(), TypeError))
    results.append(expect_exception('positional_timeout', lambda: root.find(valid_selector, 1), TypeError))
    results.append(expect_exception('unknown_keyword', lambda: root.find(valid_selector, unsupported=True), TypeError))
    return results

def run(args):
    results = [contract()]
    if results[-1]['status'] != 'PASS' or args.contract_only:
        return (results, 0 if results[-1]['status'] == 'PASS' else 1)
    package = page = root = temp_dir = None
    try:
        package, page, root, seeds, temp_dir, was_checked = prepare(args)
        results.append(result('page_and_elements', 'PASS', '动态 ID 已关闭；三个输入框均已核对祖先容器 #shadow-form-content'))
        results.extend(run_find_cases(root, package, args))
    except Exception as exc:
        results.append(result('scenario', 'FAIL', error_detail('find 场景执行失败', exc)))
    finally:
        if page is not None:
            try:
                page.close(ignore_beforeunload=True)
                results.append(result('cleanup_page', 'PASS', '测试页面已关闭'))
            except Exception as exc:
                results.append(result('cleanup_page', 'FAIL', error_detail('测试页面关闭失败', exc)))
        if package is not None:
            try:
                package.close()
                results.append(result('cleanup_package', 'PASS', '元素库 Package 已关闭'))
            except Exception as exc:
                results.append(result('cleanup_package', 'FAIL', error_detail('Package 关闭失败', exc)))
        if temp_dir is not None:
            try:
                shutil.rmtree(temp_dir)
                results.append(result('cleanup_temp', 'PASS', '临时元素库副本已删除'))
            except Exception as exc:
                results.append(result('cleanup_temp', 'FAIL', error_detail('临时目录清理失败', exc)))
    return (results, 0 if all((item['status'] == 'PASS' for item in results)) else 1)

def main(argv=None):
    import argparse
    parser = argparse.ArgumentParser(description='WebElement.find() 表单输入框专项验收')
    parser.add_argument('--mode', choices=('chrome', 'edge'), default='chrome')
    parser.add_argument('--library', type=Path, default=LIBRARY)
    parser.add_argument('--timeout', type=float, default=5)
    parser.add_argument('--element-timeout', type=float, default=10)
    parser.add_argument('--runtime-timeout', type=float, default=20)
    parser.add_argument('--load-timeout', type=float, default=20)
    parser.add_argument('--contract-only', action='store_true')
    args = parser.parse_args(argv)
    args.temp_root = Path(__file__).resolve().parents[1] / '.pytest_tmp'
    args.temp_root.mkdir(parents=True, exist_ok=True)
    if not args.library.is_dir():
        parser.error(f'元素库不存在: {args.library}')
    if args.timeout < 0 or args.element_timeout <= 0 or args.runtime_timeout <= 0 or (args.load_timeout <= 0):
        parser.error('timeout 参数范围不合法')
    results, code = run(args)
    print('UIAutoma Web API 测试')
    print('API     : uiautoma.web.WebElement.find')
    print(f'页面    : {URL}')
    print(f'元素库  : {args.library}')
    print('进度     状态    测试项                  测试结果')
    print('────────────────────────────────────────────────────────────────────────')
    for index, item in enumerate(results, 1):
        color = GREEN if item['status'] == 'PASS' else RED
        label = '通过' if item['status'] == 'PASS' else '失败'
        print(f"{index:02d}/{len(results):02d}    {color}[{label}]{RESET}  {item['case_id']:<22}  {item['detail']}")
    print('────────────────────────────────────────────────────────────────────────')
    print(f"{('测试通过' if code == 0 else '测试失败')} · {sum((item['status'] == 'PASS' for item in results))}/{len(results)} 通过 · 退出码 {code}")
    return code
if __name__ == '__main__':
    raise SystemExit(main())
