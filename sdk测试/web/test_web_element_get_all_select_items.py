"""WebElement.get_all_select_items() 在 iframe / Shadow 表单中的真实浏览器验收。

比较 SDK 文本列表与页面 DOM option；测试原生单选、多选、选中后不变、
重复、空列表和不换行空格，以及 Ant 自定义下拉框边界。只连接元素库的临时副本。
"""

from __future__ import annotations

import argparse
import inspect
import json
import shutil
import subprocess
import sys
import time
import uuid
from pathlib import Path
from typing import Any


URL = "https://baobaomi900901.github.io/xpath/#/iframe-shadow-form"
LIBRARY = Path(r"D:\code\元素库\260902_web元素")
PRODUCT = Path(r"D:\code\desktop")
SWITCH = "web靶场_表单测试_控制表单组件id是否为动态的开关"
SINGLE = "web靶场_表单测试_原生_select单选"
MULTI = "web靶场_表单测试_原生_select多选_options_面板"
ANT_SINGLE = "web靶场_表单测试_ant_select单选"
ANT_MULTI = "web靶场_表单测试_ant_select多选"
NATIVE_INPUT = "web靶场_表单测试_原生_输入框"
NATIVE_RESET = "web靶场_表单测试_原生_重置"
SINGLE_OPTIONS = [
    {"name": "请选择城市", "value": "", "selected": True},
    {"name": "北京", "value": "beijing", "selected": False},
    {"name": "上海", "value": "shanghai", "selected": False},
    {"name": "广州", "value": "guangzhou", "selected": False},
    {"name": "深圳", "value": "shenzhen", "selected": False},
]
MULTI_OPTIONS = [
    {"name": "北京", "value": "beijing", "selected": False},
    {"name": "上海", "value": "shanghai", "selected": False},
    {"name": "广州", "value": "guangzhou", "selected": False},
    {"name": "深圳", "value": "shenzhen", "selected": False},
]
SINGLE_ITEMS = [item["name"] for item in SINGLE_OPTIONS]
MULTI_ITEMS = [item["name"] for item in MULTI_OPTIONS]
COLORS = {"PASS": "\x1b[92m", "FAIL": "\x1b[91m", "BLOCKED": "\x1b[93m", "KNOWN": "\x1b[93m"}
RESET = "\x1b[0m"
__test__ = False


def row(case_id: str, status: str, expected: str, actual: str, started: float) -> dict[str, Any]:
    return {"case_id": case_id, "status": status, "expected": expected,
            "actual": actual, "elapsed_ms": round((time.perf_counter() - started) * 1000, 1)}


def error(exc: BaseException) -> str:
    trace = getattr(exc, "trace_info", None)
    return f"{type(exc).__name__}: {exc}" + (f" [trace={trace}]" if trace else "")


def source_commit(root: Path) -> str:
    try:
        return subprocess.check_output(["git", "-C", str(root), "rev-parse", "HEAD"],
                                       text=True, encoding="utf-8", stderr=subprocess.DEVNULL).strip()
    except (OSError, subprocess.CalledProcessError):
        return "unknown"


def check_contract(element_class: type) -> dict[str, Any]:
    started = time.perf_counter()
    expected = "get_all_select_items(self) -> list[str]"
    try:
        signature = inspect.signature(element_class.get_all_select_items)
        parameters = list(signature.parameters.values())
        ok = (tuple(signature.parameters) == ("self",)
              and parameters[0].kind is inspect.Parameter.POSITIONAL_OR_KEYWORD
              and parameters[0].default is inspect.Parameter.empty
              and str(signature.return_annotation) == "list[str]")
        return row("api_contract", "PASS" if ok else "FAIL", expected, str(signature), started)
    except Exception as exc:
        return row("api_contract", "FAIL", expected, error(exc), started)


def copy_library(source: Path, target: Path) -> None:
    shutil.copytree(source, target)
    for path in (target / "elements.json", *(target / "snapshot").glob("*.json")):
        if not path.is_file():
            continue
        data = json.loads(path.read_text(encoding="utf-8"))
        pending = [data]
        while pending:
            value = pending.pop()
            if isinstance(value, dict):
                for key, child in value.items():
                    if isinstance(key, str) and "session" in key.casefold() and child:
                        value[key] = ""
                    elif key == "BrowserPid" and child:
                        value[key] = 0
                    elif isinstance(child, (dict, list)):
                        pending.append(child)
            elif isinstance(value, list):
                pending.extend(value)
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def find_switch(page: Any) -> Any:
    switch = page.find(SWITCH, timeout=8)
    for _ in range(5):
        if switch.get_attribute("role") == "switch":
            return switch
        switch = switch.parent()
    raise RuntimeError("动态 ID 开关附近未找到 role=switch")


def disable_dynamic_ids(page: Any) -> str:
    switch = find_switch(page)
    previous = switch.get_attribute("aria-checked")
    if previous == "true":
        switch.click(simulative=False, delay_after=0.1)
        deadline = time.monotonic() + 5
        while switch.get_attribute("aria-checked") != "false":
            if time.monotonic() >= deadline:
                raise RuntimeError("动态 ID 开关未关闭")
            time.sleep(0.1)
    elif previous != "false":
        raise RuntimeError(f"动态 ID 开关状态异常：{previous!r}")
    return previous


READ = """function () {
  const root = document.querySelector('#iframe-shadow-form')?.contentDocument
    ?.querySelector('#form-shadow-host')?.shadowRoot;
  const pick = id => {
    const el = root?.getElementById(id);
    return el ? {tag:el.tagName, multiple:el.multiple,
      options:[...el.options].map(x=>({name:x.text,value:x.value,selected:x.selected}))} : null;
  };
  const antSingle = root?.getElementById('form-controls-ant-city');
  const antMulti = root?.getElementById('form-controls-ant-cities');
  return {single:pick('form-controls-native-city'), multi:pick('form-controls-native-cities'),
    antSingle:antSingle ? {tag:antSingle.tagName, value:antSingle.value,
      display:antSingle.closest('.ant-select')?.textContent || ''} : null,
    antMulti:antMulti ? {tag:antMulti.closest('.ant-select-selection-overflow')?.tagName,
      value:antMulti.value, display:antMulti.closest('.ant-select')?.textContent || ''} : null};
}"""

GET_HTML = """function () {
  const root = document.querySelector('#iframe-shadow-form').contentDocument
    .querySelector('#form-shadow-host').shadowRoot;
  return root.getElementById('form-controls-native-city').innerHTML;
}"""
INJECT_DUPLICATE = """function () {
  const root = document.querySelector('#iframe-shadow-form').contentDocument
    .querySelector('#form-shadow-host').shadowRoot;
  const el = root.getElementById('form-controls-native-city');
  const duplicate = el.options[1].cloneNode(true);
  duplicate.dataset.uiautomaProbe = 'duplicate';
  el.appendChild(duplicate);
}"""
INJECT_NBSP = """function () {
  const root = document.querySelector('#iframe-shadow-form').contentDocument
    .querySelector('#form-shadow-host').shadowRoot;
  const option = document.createElement('option');
  option.textContent = '甲' + String.fromCharCode(160) + '乙';
  option.value = 'nbsp';
  root.getElementById('form-controls-native-city').appendChild(option);
}"""
CLEAR_OPTIONS = """function () {
  const root = document.querySelector('#iframe-shadow-form').contentDocument
    .querySelector('#form-shadow-host').shadowRoot;
  root.getElementById('form-controls-native-city').replaceChildren();
}"""
RESTORE_OPTIONS = """function (_element, html) {
  const root = document.querySelector('#iframe-shadow-form').contentDocument
    .querySelector('#form-shadow-host').shadowRoot;
  root.getElementById('form-controls-native-city').innerHTML = html;
}"""


def state(page: Any) -> dict[str, Any]:
    value = page.execute_javascript(READ)
    if (not isinstance(value, dict) or not value.get("single") or not value.get("multi")
            or not value.get("antSingle") or not value.get("antMulti")):
        raise RuntimeError(f"四个下拉控件的 DOM 不可读：{value!r}")
    return value


def texts(options: list[dict[str, Any]]) -> list[str]:
    return [option["name"].replace("\u00a0", " ") for option in options]


def valid_items(value: Any) -> bool:
    return isinstance(value, list) and all(isinstance(item, str) for item in value)


def read_case(page: Any, case_id: str, name: str, side: str,
              expected_items: list[str]) -> dict[str, Any]:
    started = time.perf_counter()
    expected = f"{name} 返回 {len(expected_items)} 个文本，顺序与页面 DOM 一致；读取不改 DOM"
    try:
        before = state(page)[side]["options"]
        result = page.find(name, timeout=8).get_all_select_items()
        after = state(page)[side]["options"]
        ok = valid_items(result) and result == expected_items == texts(before) and before == after
        return row(case_id, "PASS" if ok else "FAIL", expected,
                   f"返回={result!r}；DOM 前={before!r}；后={after!r}", started)
    except Exception as exc:
        return row(case_id, "FAIL", expected, error(exc), started)


def ant_case(page: Any, case_id: str, name: str, side: str,
             expected_tag: str, action_error: type) -> dict[str, Any]:
    started = time.perf_counter()
    expected = f"Ant {expected_tag} 调用 get_all_select_items() 抛 ActionError/element_options_not_readable；DOM 不变"
    try:
        before = state(page)
        if before[side]["tag"] != expected_tag:
            raise RuntimeError(f"Ant 元素映射异常：{before[side]!r}")
        target = page.find(name, timeout=8)
        try:
            result = target.get_all_select_items()
            return row(case_id, "FAIL", expected, f"未拒绝，返回={result!r}", started)
        except Exception as exc:
            after = state(page)
            ok = (isinstance(exc, action_error) and getattr(exc, "trace_info", "") == "element_options_not_readable"
                  and after == before)
            return row(case_id, "KNOWN" if ok else "FAIL", expected,
                       f"{error(exc)}；前={before[side]!r}；后={after[side]!r}", started)
    except Exception as exc:
        return row(case_id, "FAIL", expected, error(exc), started)


def selected_case(page: Any, case_id: str, name: str, side: str,
                  expected_items: list[str], selected_values: list[str]) -> dict[str, Any]:
    started = time.perf_counter()
    expected = f"选中 {selected_values!r} 后仍返回全部 {len(expected_items)} 项，顺序与 DOM 一致"
    try:
        target = page.find(name, timeout=8)
        if side == "single":
            target.select_by_index(2, delay_after=0.2)
        else:
            target.select_multiple_by_index([0, 2], delay_after=0.2)
        before = state(page)[side]["options"]
        result = page.find(name, timeout=8).get_all_select_items()
        after = state(page)[side]["options"]
        selected = [item["value"] for item in after if item["selected"]]
        ok = (valid_items(result) and result == expected_items == texts(before)
              and before == after and selected == selected_values)
        return row(case_id, "PASS" if ok else "FAIL", expected,
                   f"选中值={selected!r}；返回={result!r}；DOM={after!r}", started)
    except Exception as exc:
        return row(case_id, "FAIL", expected, error(exc), started)


def repeated_read_case(page: Any) -> dict[str, Any]:
    started = time.perf_counter()
    expected = "连续读取两次，两侧列表相同且页面 DOM 不变"
    try:
        before = state(page)
        reads = {}
        for side, name in (("single", SINGLE), ("multi", MULTI)):
            target = page.find(name, timeout=8)
            reads[side] = [target.get_all_select_items(), target.get_all_select_items()]
        after = state(page)
        ok = (before == after and all(valid_items(values[0]) and
              values[0] == values[1] == texts(before[side]["options"])
              for side, values in reads.items()))
        return row("repeated_read_no_mutation", "PASS" if ok else "FAIL", expected,
                   f"单选两次={reads['single']!r}；多选两次={reads['multi']!r}；DOM 不变={before == after}", started)
    except Exception as exc:
        return row("repeated_read_no_mutation", "FAIL", expected, error(exc), started)


def reset_case(page: Any) -> dict[str, Any]:
    started = time.perf_counter()
    expected = "页面重置后单选占位项 selected=True、多选四项均未选；两侧仍返回全部文本"
    try:
        page.find(NATIVE_RESET, timeout=8).click(simulative=False, delay_after=0.1)
        time.sleep(1.5)
        before = state(page)
        single = page.find(SINGLE, timeout=8).get_all_select_items()
        multi = page.find(MULTI, timeout=8).get_all_select_items()
        after = state(page)
        ok = (single == SINGLE_ITEMS and multi == MULTI_ITEMS
              and before["single"]["options"] == after["single"]["options"] == SINGLE_OPTIONS
              and before["multi"]["options"] == after["multi"]["options"] == MULTI_OPTIONS)
        return row("reset_selected_flags", "PASS" if ok else "FAIL", expected,
                   f"单选={single!r}；多选={multi!r}", started)
    except Exception as exc:
        return row("reset_selected_flags", "FAIL", expected, error(exc), started)


def fixture_case(page: Any, case_id: str) -> dict[str, Any]:
    started = time.perf_counter()
    expected = ("重复北京 option 保留两个文本且顺序与 DOM 一致；恢复原选项"
                if case_id == "duplicate_options" else "DOM option 清空后返回 []；恢复原选项")
    original_html = None
    actual = ""
    ok = False
    try:
        original_html = page.execute_javascript(GET_HTML)
        if not isinstance(original_html, str):
            raise RuntimeError("无法保存原 option HTML")
        before = state(page)["single"]["options"]
        page.execute_javascript(INJECT_DUPLICATE if case_id == "duplicate_options" else CLEAR_OPTIONS)
        dom = state(page)["single"]["options"]
        result = page.find(SINGLE, timeout=8).get_all_select_items()
        if case_id == "duplicate_options":
            ok = (valid_items(result) and len(dom) == len(before) + 1
                  and result == texts(dom) == SINGLE_ITEMS + ["北京"]
                  and dom[-1] == {"name": "北京", "value": "beijing", "selected": False})
        else:
            ok = result == dom == []
        actual = f"返回={result!r}；DOM={dom!r}"
    except Exception as exc:
        actual = error(exc)
    finally:
        if original_html is not None:
            try:
                page.execute_javascript(RESTORE_OPTIONS, original_html)
                restored = state(page)["single"]["options"]
                ok = ok and restored == SINGLE_OPTIONS
                actual += f"；恢复={restored!r}"
            except Exception as exc:
                ok = False
                actual += f"；恢复失败={error(exc)}"
    return row(case_id, "PASS" if ok else "FAIL", expected, actual, started)


def nbsp_case(page: Any) -> dict[str, Any]:
    started = time.perf_counter()
    expected = "DOM option 文本含 U+00A0，返回文本将其改为普通空格；恢复原选项"
    original_html = None
    actual = ""
    ok = False
    try:
        original_html = page.execute_javascript(GET_HTML)
        if not isinstance(original_html, str):
            raise RuntimeError("无法保存原 option HTML")
        page.execute_javascript(INJECT_NBSP)
        before = state(page)["single"]["options"]
        result = page.find(SINGLE, timeout=8).get_all_select_items()
        after = state(page)["single"]["options"]
        ok = (valid_items(result) and before == after and len(before) == len(SINGLE_OPTIONS) + 1
              and before[-1]["name"] == "甲\u00a0乙" and before[-1]["value"] == "nbsp"
              and result == SINGLE_ITEMS + ["甲 乙"])
        actual = f"返回={result!r}；DOM末项={before[-1]!r}；读取不改DOM={before == after}"
    except Exception as exc:
        actual = error(exc)
    finally:
        if original_html is not None:
            try:
                page.execute_javascript(RESTORE_OPTIONS, original_html)
                restored = state(page)["single"]["options"]
                ok = ok and restored == SINGLE_OPTIONS
                actual += f"；恢复={restored!r}"
            except Exception as exc:
                ok = False
                actual += f"；恢复失败={error(exc)}"
    return row("nbsp_normalization", "PASS" if ok else "FAIL", expected, actual, started)


def invalid_target_case(page: Any, action_error: type) -> dict[str, Any]:
    started = time.perf_counter()
    expected = "普通 input 调用 get_all_select_items() 抛 ActionError/element_options_not_readable；DOM 不变"
    try:
        before = state(page)
        target = page.find(NATIVE_INPUT, timeout=8)
        try:
            result = target.get_all_select_items()
            return row("non_select_input", "FAIL", expected, f"未拒绝，返回={result!r}", started)
        except Exception as exc:
            after = state(page)
            ok = (isinstance(exc, action_error) and getattr(exc, "trace_info", "") == "element_options_not_readable"
                  and after == before)
            return row("non_select_input", "PASS" if ok else "FAIL", expected,
                       f"{error(exc)}；DOM 不变={after == before}", started)
    except Exception as exc:
        return row("non_select_input", "FAIL", expected, error(exc), started)


def unexpected_argument_case(page: Any) -> dict[str, Any]:
    started = time.perf_counter()
    expected = "额外位置参数抛 TypeError；DOM 不变"
    try:
        before = state(page)
        target = page.find(SINGLE, timeout=8)
        try:
            result = target.get_all_select_items(1)
            return row("unexpected_argument", "FAIL", expected, f"未拒绝，返回={result!r}", started)
        except Exception as exc:
            after = state(page)
            ok = isinstance(exc, TypeError) and after == before
            return row("unexpected_argument", "PASS" if ok else "FAIL", expected,
                       f"{error(exc)}；DOM 不变={after == before}", started)
    except Exception as exc:
        return row("unexpected_argument", "FAIL", expected, error(exc), started)


def run(args: argparse.Namespace) -> tuple[list[dict[str, Any]], int, str]:
    sdk_src = args.product_root / "sdk" / "src"
    if str(sdk_src) not in sys.path:
        sys.path.insert(0, str(sdk_src))
    from uiautoma import ActionError, StalePackageError, open as open_package, web
    from uiautoma.web import WebElement

    rows = [check_contract(WebElement)]
    commit = source_commit(args.product_root)
    if args.contract_only or rows[0]["status"] != "PASS":
        return rows, 0 if rows[0]["status"] == "PASS" else 1, commit

    temp_dir = args.test_root / ".pytest_tmp" / "get_all_select_items" / uuid.uuid4().hex
    package = page = single_ref = None
    baseline = previous_switch = test_page_id = None
    baseline_ids: set[str] = set()
    environment_ready = False
    try:
        started = time.perf_counter()
        if not sdk_src.is_dir() or not args.element_library.is_dir():
            raise FileNotFoundError(f"SDK 或元素库不存在：{sdk_src}；{args.element_library}")
        baseline_pages = web.get_all(mode="chrome")
        baseline = len(baseline_pages)
        baseline_ids = {item._page_ref["id"] for item in baseline_pages}
        temp_dir.mkdir(parents=True)
        copy_library(args.element_library, temp_dir / "library")
        package = open_package(str(temp_dir / "library"), timeout=8, connect_timeout=8)
        page = web.create(args.target_url, mode="chrome", load_timeout=25, silent_running=True)
        test_page_id = page._page_ref["id"]
        previous_switch = disable_dynamic_ids(page)
        snapshot = state(page)
        single_ref = page.find(SINGLE, timeout=8)
        multi_ref = page.find(MULTI, timeout=8)
        ant_single_ref = page.find(ANT_SINGLE, timeout=8)
        ant_multi_ref = page.find(ANT_MULTI, timeout=8)
        ok = (snapshot["single"]["tag"] == "SELECT" and snapshot["single"]["multiple"] is False
              and snapshot["single"]["options"] == SINGLE_OPTIONS
              and snapshot["multi"]["tag"] == "SELECT" and snapshot["multi"]["multiple"] is True
              and snapshot["multi"]["options"] == MULTI_OPTIONS
              and snapshot["antSingle"]["tag"] == "INPUT" and snapshot["antMulti"]["tag"] == "DIV"
              and single_ref.get_attribute("id") == "form-controls-native-city"
              and multi_ref.get_attribute("id") == "form-controls-native-cities"
              and ant_single_ref.get_attribute("id") == "form-controls-ant-city"
              and "ant-select-selection-overflow" in (ant_multi_ref.get_attribute("class") or ""))
        rows.append(row("environment", "PASS" if ok else "BLOCKED",
                        "Runtime/Chrome/库可用，四元素唯一映射，原生 option 与页面静态清单一致",
                        f"原标签数={baseline}；开关原状态={previous_switch!r}；"
                        f"单选={snapshot['single']!r}；多选={snapshot['multi']!r}", started))
        if not ok:
            raise RuntimeError("页面 DOM 或元素库映射与预期不符")
        environment_ready = True

        rows.append(read_case(page, "native_single_initial", SINGLE, "single", SINGLE_ITEMS))
        rows.append(read_case(page, "native_multi_initial", MULTI, "multi", MULTI_ITEMS))
        rows.append(ant_case(page, "ant_single_combobox", ANT_SINGLE, "antSingle", "INPUT", ActionError))
        rows.append(ant_case(page, "ant_multi_combobox", ANT_MULTI, "antMulti", "DIV", ActionError))
        rows.append(selected_case(page, "native_single_selected", SINGLE, "single", SINGLE_ITEMS, ["shanghai"]))
        rows.append(selected_case(page, "native_multi_selected", MULTI, "multi", MULTI_ITEMS, ["beijing", "guangzhou"]))
        rows.append(repeated_read_case(page))
        rows.append(reset_case(page))
        rows.append(fixture_case(page, "duplicate_options"))
        rows.append(nbsp_case(page))
        rows.append(fixture_case(page, "empty_options"))
        rows.append(invalid_target_case(page, ActionError))
        rows.append(unexpected_argument_case(page))
    except Exception as exc:
        rows.append(row("environment_error", "FAIL" if environment_ready else "BLOCKED",
                        "环境可用且测试步骤可完成", error(exc), time.perf_counter()))
    finally:
        started = time.perf_counter()
        cleanup_errors = []
        if page is not None and previous_switch == "true":
            try:
                switch = find_switch(page)
                if switch.get_attribute("aria-checked") == "false":
                    switch.click(simulative=False, delay_after=0.1)
                if switch.get_attribute("aria-checked") != "true":
                    cleanup_errors.append("动态 ID 开关未恢复")
            except Exception as exc:
                cleanup_errors.append(f"恢复开关：{error(exc)}")
        if page is not None:
            try:
                page.close(ignore_beforeunload=True)
            except Exception as exc:
                cleanup_errors.append(f"关闭页面：{error(exc)}")
        if package is not None:
            try:
                package.close()
            except Exception as exc:
                cleanup_errors.append(f"关闭元素库：{error(exc)}")
        if single_ref is not None and package is not None:
            lifecycle_start = time.perf_counter()
            try:
                result = single_ref.get_all_select_items()
                rows.append(row("closed_package", "FAIL", "库连接关闭后抛 StalePackageError",
                                f"未抛错，返回={result!r}", lifecycle_start))
            except Exception as exc:
                rows.append(row("closed_package", "PASS" if isinstance(exc, StalePackageError) else "FAIL",
                                "库连接关闭后抛 StalePackageError", error(exc), lifecycle_start))
        if temp_dir.exists():
            shutil.rmtree(temp_dir)
        tab_note = ""
        try:
            if baseline is not None:
                deadline = time.monotonic() + 3
                while True:
                    after_pages = web.get_all(mode="chrome")
                    after_ids = {item._page_ref["id"] for item in after_pages}
                    if test_page_id not in after_ids or time.monotonic() >= deadline:
                        break
                    time.sleep(0.1)
                if test_page_id in after_ids:
                    cleanup_errors.append("本次创建的 Chrome 标签仍存在")
                external_added = len(after_ids - baseline_ids - {test_page_id})
                external_removed = len(baseline_ids - after_ids)
                tab_note = (f"本次标签已关闭；外部标签变动 +{external_added}/-{external_removed}；"
                            f"总数 {baseline}->{len(after_pages)}")
        except Exception as exc:
            cleanup_errors.append(f"复核标签：{error(exc)}")
        if temp_dir.exists():
            cleanup_errors.append(f"临时副本仍存在：{temp_dir}")
        rows.append(row("cleanup", "PASS" if not cleanup_errors else "FAIL",
                        "恢复开关、关闭本次标签和库连接、删除临时副本；追踪本次标签 ID",
                        "; ".join(cleanup_errors) if cleanup_errors else f"逐项复核通过；{tab_note}", started))
    code = 1 if any(x["status"] == "FAIL" for x in rows) else 2 if any(
        x["status"] == "BLOCKED" for x in rows) else 0
    return rows, code, commit


def main() -> int:
    parser = argparse.ArgumentParser(description="WebElement.get_all_select_items() iframe/Shadow 表单实测")
    parser.add_argument("--contract-only", action="store_true")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--report-file", type=Path)
    parser.add_argument("--target-url", default=URL)
    parser.add_argument("--element-library", type=Path, default=LIBRARY)
    parser.add_argument("--product-root", type=Path, default=PRODUCT)
    parser.add_argument("--test-root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    rows, code, commit = run(args)
    report = {"api": "uiautoma.web.WebElement.get_all_select_items", "url": args.target_url,
              "element_library": str(args.element_library), "product_worktree": str(args.product_root),
              "product_commit": commit, "results": rows, "exit_code": code}
    if args.report_file:
        args.report_file.parent.mkdir(parents=True, exist_ok=True)
        args.report_file.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if args.json:
        print(json.dumps(report, ensure_ascii=True, indent=2))
    else:
        print("UIAutoma Web API 测试")
        print(f"API     : {report['api']}")
        print(f"页面    : {args.target_url}")
        print(f"源码快照: {args.product_root} @ {commit}")
        print("进度     状态    测试项                         测试结果")
        print("─" * 100)
        for index, result in enumerate(rows, 1):
            status = result["status"]
            label = {"PASS": "通过", "FAIL": "失败", "BLOCKED": "阻塞", "KNOWN": "已知"}[status]
            print(f"{index:02}/{len(rows):02}    {COLORS[status]}[{label}]{RESET}  "
                  f"{result['case_id']:<29}  期望 {result['expected']}；"
                  f"实测 {result['actual']}；{result['elapsed_ms']}ms")
        passed = sum(result["status"] == "PASS" for result in rows)
        known = sum(result["status"] == "KNOWN" for result in rows)
        print("─" * 100)
        print(f"测试{'通过' if code == 0 else '失败或阻塞'} · {passed}/{len(rows)} 通过"
              f" · {known} 已知边界 · 退出码 {code}")
    return code


if __name__ == "__main__":
    raise SystemExit(main())
