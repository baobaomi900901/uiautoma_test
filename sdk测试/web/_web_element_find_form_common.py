"""表单靶场 WebElement 查找 API 测试共用运行器。"""
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

URL = "https://baobaomi900901.github.io/xpath/#/iframe-shadow-form"
LIBRARY = Path(r"D:\code\元素库\260902_web元素")
SWITCH = "web靶场_表单测试_控制表单组件id是否为动态的开关"
TARGETS = (
    "web靶场_表单测试_ant_输入框",
    "web靶场_表单测试_ant_密码输入框",
    "web靶场_表单测试_ant_邮箱输入框",
)
GREEN, RED, YELLOW, RESET = "\x1b[92m", "\x1b[91m", "\x1b[93m", "\x1b[0m"


def result(case_id: str, status: str, detail: str):
    return {"case_id": case_id, "status": status, "detail": detail}


def error_detail(prefix: str, exc: BaseException) -> str:
    detail = f"{prefix}: {type(exc).__name__}: {exc}"
    trace = str(getattr(exc, "trace_info", "") or "")
    if trace:
        detail += f" [trace={trace}]"
    return detail


def contract(api: str):
    method = getattr(WebElement, api, None)
    sig = inspect.signature(method) if callable(method) else None
    if sig is None:
        return result("api_contract", "FAIL", f"WebElement.{api} 不存在")
    parameters = list(sig.parameters.values())
    names = tuple(sig.parameters)
    selector_name = {
        "find": "selector", "find_all": "selector",
        "find_by_css": "css_selector", "find_all_by_css": "css_selector",
        "find_by_xpath": "xpath_selector", "find_all_by_xpath": "xpath_selector",
    }[api]
    ok = (
        names == ("self", selector_name, "timeout")
        and parameters[1].kind is inspect.Parameter.POSITIONAL_OR_KEYWORD
        and parameters[1].default is inspect.Parameter.empty
        and parameters[2].kind is inspect.Parameter.KEYWORD_ONLY
        and parameters[2].default == 10
    )
    return result(
        "api_contract", "PASS" if ok else "FAIL",
        f"{selector_name} 必填，timeout 仅限关键字且默认 10" if ok else f"公开签名不符合合同: {sig}",
    )


def call(method: Callable, *args, **kwargs):
    try:
        return True, method(*args, **kwargs), None
    except Exception as exc:  # noqa: BLE001
        return False, None, exc


def expect_exception(label: str, method: Callable, expected, *args, **kwargs):
    ok, value, exc = call(method, *args, **kwargs)
    if not ok and isinstance(exc, expected):
        return result(label, "PASS", f"{type(exc).__name__} 正确拒绝")
    if not ok:
        return result(label, "FAIL", f"应为 {expected.__name__}，实际为 {type(exc).__name__}: {exc}")
    return result(label, "FAIL", f"调用未被拒绝，返回 {value!r}")


def find_common_root(seeds: dict[str, WebElement]):
    chains: dict[str, list[WebElement]] = {}
    for name, seed in seeds.items():
        chain = [seed]
        seen = {seed.id}
        current = seed
        for _ in range(12):
            try:
                current = current.parent()
            except Exception:
                break
            if current.id in seen:
                break
            chain.append(current)
            seen.add(current.id)
        chains[name] = chain
    first = chains[TARGETS[0]]
    common_ids = set(item.id for item in chains[TARGETS[1]]) & set(item.id for item in chains[TARGETS[2]])
    for item in first:
        if item.id in common_ids:
            return item
    return None


def disable_dynamic_ids(captured: WebElement, *, timeout: float) -> bool:
    """捕获点可能是开关内部 span；仅对 role=switch 读取 aria-checked。"""
    switch = captured
    for depth in range(5):
        if switch.get_attribute("role") == "switch":
            break
        if depth == 4:
            raise RuntimeError('动态 ID 捕获元素及其近邻父级中未找到 role="switch"')
        switch = switch.parent()

    def checked() -> bool:
        state = switch.get_attribute("aria-checked")
        if state not in ("true", "false"):
            raise RuntimeError(f"动态 ID 开关 aria-checked 无效: {state!r}")
        return state == "true"

    was_checked = checked()
    if not was_checked:
        return False
    # 点击外层按钮，可在视窗外操作；不重复点击，避免状态反转。
    switch.click(simulative=False, delay_after=0)
    deadline = time.monotonic() + timeout
    while checked():
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise RuntimeError(f"动态 ID 开关点击后 {timeout:g} 秒仍未关闭: aria-checked='true'")
        time.sleep(min(0.1, remaining))
    return True


def prepare(args):
    temp_dir = Path(tempfile.mkdtemp(prefix="uiautoma-element-find-", dir=str(args.temp_root)))
    library_copy = temp_dir / "library"
    shutil.copytree(args.library, library_copy)
    package = None
    page = None
    try:
        package = uiautoma.open(str(library_copy), timeout=args.runtime_timeout, connect_timeout=args.runtime_timeout)
        page = web.create(URL, mode=args.mode, load_timeout=args.load_timeout)
        if not isinstance(page, WebBrowser):
            raise RuntimeError("web.create 未返回 WebBrowser")
        switch = page.find(SWITCH, timeout=args.element_timeout)
        was_checked = disable_dynamic_ids(switch, timeout=args.element_timeout)
        seeds = {name: page.find(name, timeout=args.element_timeout) for name in TARGETS}
        root = find_common_root(seeds)
        if root is None:
            raise RuntimeError("三个输入框没有找到共同的 WebElement 父级")
        return package, page, root, seeds, temp_dir, was_checked
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


def selector_values(api: str):
    if api in {"find", "find_all"}:
        return {
            "unique": list(TARGETS),
            "empty": "__uiautoma_missing_form_element__",
            "invalid": (None, 123, ""),
        }
    if api in {"find_by_css", "find_all_by_css"}:
        return {
            "unique": ["input[type='text']", "input[type='password']", "input[type='email']"],
            "multi": "input",
            "empty": "input[data-uiautoma-missing='yes']",
            "invalid": (None, 123, "input["),
        }
    return {
        "unique": [".//input[@type='text']", ".//input[@type='password']", ".//input[@type='email']"],
        "multi": ".//input",
        "empty": ".//input[@data-uiautoma-missing='yes']",
        "invalid": (None, 123, "//*["),
    }


def run_api(api: str, args):
    results = [contract(api)]
    if results[-1]["status"] != "PASS" or args.contract_only:
        return results, 0 if results[-1]["status"] == "PASS" else 1
    package = page = root = temp_dir = None
    try:
        package, page, root, seeds, temp_dir, was_checked = prepare(args)
        results.append(result("page_and_elements", "PASS", "靶场、元素库、动态 ID 开关及三个输入框均已准备"))
        values = selector_values(api)
        if api in {"find", "find_all"}:
            method = getattr(root, api)
            all_ok = True
            details = []
            for name in values["unique"]:
                ok, value, exc = call(method, name, timeout=args.timeout)
                expected_type = WebElement if api == "find" else list
                one_ok = ok and isinstance(value, expected_type)
                if api == "find":
                    one_ok = one_ok and value.name == name
                    details.append(f"{name.rsplit('_', 1)[-1]}={value.name!r}") if one_ok else details.append(f"{name.rsplit('_', 1)[-1]} 失败")
                else:
                    one_ok = one_ok and len(value) == 1 and value[0].name == name
                    details.append(f"{name.rsplit('_', 1)[-1]}={len(value) if ok else 0}")
                all_ok = all_ok and one_ok
            results.append(result("unique_matches", "PASS" if all_ok else "FAIL", "；".join(details) if all_ok else "至少一个输入框唯一匹配失败"))
            selector = package.selector(TARGETS[0])
            ok, value, exc = call(method, selector, timeout=0)
            selector_ok = ok and ((isinstance(value, WebElement) and value.name == TARGETS[0]) or (isinstance(value, list) and len(value) == 1 and value[0].name == TARGETS[0]))
            results.append(result("selector_object", "PASS" if selector_ok else "FAIL", "Selector 对象调用结果与名称字符串一致" if selector_ok else error_detail("Selector 对象调用失败", exc) if exc else "Selector 对象返回结果不符"))
            if api == "find":
                results.append(expect_exception("missing_element", method, ElementNotFoundError, values["empty"], timeout=0))
            else:
                ok, value, exc = call(method, values["empty"], timeout=0)
                results.append(result("missing_element", "PASS" if ok and value == [] else "FAIL", "未命中返回空列表" if ok and value == [] else error_detail("未命中结果错误", exc) if exc else f"返回 {value!r}"))
        else:
            method = getattr(root, api)
            unique_ok = True
            for selector in values["unique"]:
                ok, value, exc = call(method, selector, timeout=args.timeout)
                if api.startswith("find_all"):
                    unique_ok = unique_ok and ok and isinstance(value, list) and len(value) == 1
                else:
                    unique_ok = unique_ok and ok and isinstance(value, WebElement)
            results.append(result("unique_matches", "PASS" if unique_ok else "FAIL", "文本、密码、邮箱三类输入框均唯一匹配" if unique_ok else "至少一个唯一选择器匹配失败"))
            ok, value, exc = call(method, values["multi"], timeout=0)
            if api.startswith("find_all"):
                multi_ok = ok and isinstance(value, list) and len(value) >= 3
                results.append(result("multiple_matches", "PASS" if multi_ok else "FAIL", f"input 多项匹配返回 {len(value) if ok else 0} 个 WebElement" if multi_ok else error_detail("多项匹配失败", exc) if exc else f"返回 {value!r}"))
            else:
                results.append(result("multiple_matches", "PASS" if (not ok and isinstance(exc, AmbiguousElementError)) else "FAIL", "多项匹配正确抛出 AmbiguousElementError" if not ok and isinstance(exc, AmbiguousElementError) else error_detail("多项匹配结果错误", exc) if exc else "多项匹配未拒绝"))
            ok, value, exc = call(method, values["empty"], timeout=0)
            if api.startswith("find_all"):
                empty_ok = ok and value == []
                results.append(result("not_found", "PASS" if empty_ok else "FAIL", "未命中返回空列表" if empty_ok else error_detail("未命中失败", exc) if exc else f"返回 {value!r}"))
            else:
                results.append(result("not_found", "PASS" if (not ok and isinstance(exc, ElementNotFoundError)) else "FAIL", "未命中正确抛出 ElementNotFoundError" if not ok and isinstance(exc, ElementNotFoundError) else error_detail("未命中结果错误", exc) if exc else "未命中未抛出异常"))
            for invalid in values["invalid"]:
                results.append(expect_exception("invalid_selector", method, InvalidParamsError, invalid, timeout=0))

        method = getattr(root, api)
        if api in {"find", "find_all"}:
            valid_selector = TARGETS[0]
        else:
            valid_selector = values["unique"][0]
        results.append(expect_exception("invalid_timeout", method, InvalidParamsError, valid_selector, timeout=-2))
        results.append(expect_exception("invalid_timeout_type", method, InvalidParamsError, valid_selector, timeout="bad"))  # type: ignore[arg-type]
        results.append(expect_exception("missing_selector", method, TypeError))
        results.append(expect_exception("positional_timeout", method, TypeError, valid_selector, 1))
        results.append(expect_exception("unknown_keyword", method, TypeError, valid_selector, unsupported=True))
    except Exception as exc:  # noqa: BLE001
        results.append(result("scenario", "FAIL", error_detail(f"{api} 场景执行失败", exc)))
    finally:
        if page is not None:
            try:
                page.close(ignore_beforeunload=True)
                results.append(result("cleanup_page", "PASS", "测试页面已关闭"))
            except Exception as exc:  # noqa: BLE001
                results.append(result("cleanup_page", "FAIL", error_detail("测试页面关闭失败", exc)))
        if package is not None:
            try:
                package.close()
                results.append(result("cleanup_package", "PASS", "元素库 Package 已关闭"))
            except Exception as exc:  # noqa: BLE001
                results.append(result("cleanup_package", "FAIL", error_detail("Package 关闭失败", exc)))
        if temp_dir is not None:
            try:
                shutil.rmtree(temp_dir)
                results.append(result("cleanup_temp", "PASS", "临时元素库副本已删除"))
            except Exception as exc:  # noqa: BLE001
                results.append(result("cleanup_temp", "FAIL", error_detail("临时目录清理失败", exc)))
    return results, 0 if all(item["status"] == "PASS" for item in results) else 1


def main_for(api: str, description: str, argv=None):
    import argparse

    parser = argparse.ArgumentParser(description=description)
    parser.add_argument("--mode", choices=("chrome", "edge"), default="chrome")
    parser.add_argument("--library", type=Path, default=LIBRARY)
    parser.add_argument("--timeout", type=float, default=5)
    parser.add_argument("--element-timeout", type=float, default=10)
    parser.add_argument("--runtime-timeout", type=float, default=20)
    parser.add_argument("--load-timeout", type=float, default=20)
    parser.add_argument("--contract-only", action="store_true")
    args = parser.parse_args(argv)
    args.temp_root = Path(__file__).resolve().parents[1] / ".pytest_tmp"
    args.temp_root.mkdir(parents=True, exist_ok=True)
    if not args.library.is_dir():
        parser.error(f"元素库不存在: {args.library}")
    if args.timeout < 0 or args.element_timeout <= 0 or args.runtime_timeout <= 0 or args.load_timeout <= 0:
        parser.error("timeout 参数范围不合法")
    results, code = run_api(api, args)
    print("UIAutoma Web API 测试")
    print(f"API     : uiautoma.web.WebElement.{api}")
    print(f"页面    : {URL}")
    print(f"元素库  : {args.library}")
    print("进度     状态    测试项                  测试结果")
    print("────────────────────────────────────────────────────────────────────────")
    for index, item in enumerate(results, 1):
        color = GREEN if item["status"] == "PASS" else RED
        label = "通过" if item["status"] == "PASS" else "失败"
        print(f"{index:02d}/{len(results):02d}    {color}[{label}]{RESET}  {item['case_id']:<22}  {item['detail']}")
    print("────────────────────────────────────────────────────────────────────────")
    print(f"{'测试通过' if code == 0 else '测试失败'} · {sum(item['status'] == 'PASS' for item in results)}/{len(results)} 通过 · 退出码 {code}")
    return code
