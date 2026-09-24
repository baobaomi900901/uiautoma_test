"""WebElement.select_multiple() 在 iframe / Shadow 表单中的真实浏览器验收。

目标元素：Ant 自定义多选和原生 <select multiple>；以 DOM selected 状态与
页面自身提交的 JSON 为独立确证。退出码 0=无 FAIL/BLOCKED（允许 KNOWN），
1=FAIL，2=BLOCKED。运行时只连接元素库的临时副本。
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
NATIVE = "web靶场_表单测试_原生_select多选_options_面板"
NATIVE_SUBMIT = "web靶场_表单测试_原生_按钮_提交"
NATIVE_RESET = "web靶场_表单测试_原生_重置"
ANT = "web靶场_表单测试_ant_select多选"
ANT_RESET = "web靶场_表单测试_ant_按钮_重置"
OPTIONS = (("北京", "beijing"), ("上海", "shanghai"),
           ("广州", "guangzhou"), ("深圳", "shenzhen"))
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
    expected = "select_multiple(self, items: list[str], *, mode='fuzzy', append=False, delay_after=1) -> None"
    try:
        signature = inspect.signature(element_class.select_multiple)
        parameters = list(signature.parameters.values())
        ok = (tuple(signature.parameters) == ("self", "items", "mode", "append", "delay_after")
              and parameters[0].kind is inspect.Parameter.POSITIONAL_OR_KEYWORD
              and parameters[1].kind is inspect.Parameter.POSITIONAL_OR_KEYWORD
              and parameters[1].default is inspect.Parameter.empty
              and str(parameters[1].annotation) == "list[str]"
              and parameters[2].kind is inspect.Parameter.KEYWORD_ONLY
              and parameters[2].default == "fuzzy"
              and str(parameters[2].annotation) in {"str", "<class 'str'>"}
              and parameters[3].kind is inspect.Parameter.KEYWORD_ONLY
              and parameters[3].default is False
              and str(parameters[3].annotation) in {"bool", "<class 'bool'>"}
              and parameters[4].kind is inspect.Parameter.KEYWORD_ONLY
              and parameters[4].default == 1
              and str(parameters[4].annotation) in {"float", "<class 'float'>"}
              and str(signature.return_annotation) in {"None", "<class 'NoneType'>"})
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
  const native = root?.getElementById('form-controls-native-cities');
  const ant = root?.getElementById('form-controls-ant-cities');
  return {
    native: native ? {tag:native.tagName, multiple:native.multiple,
      options:[...native.options].map(x=>({text:x.text,value:x.value,selected:x.selected}))} : null,
    ant: ant ? {tag:ant.closest('.ant-select-selection-overflow')?.tagName,
      text:ant.closest('.ant-select')?.textContent || '', value:ant.value} : null,
    nativeResult:root?.getElementById('native-result')?.textContent || null
  };
}"""


def state(page: Any) -> dict[str, Any]:
    value = page.execute_javascript(READ)
    if not isinstance(value, dict) or not value.get("native") or not value.get("ant"):
        raise RuntimeError(f"表单多选控件不可读：{value!r}")
    return value


def selected(page: Any) -> list[str]:
    return [option["value"] for option in state(page)["native"]["options"] if option["selected"]]


def reset_native(page: Any) -> list[str]:
    page.find(NATIVE_RESET, timeout=8).click(simulative=False, delay_after=0.1)
    # React reset 可能先改 DOM、再提交受控状态；等它稳定后才开始下一例。
    time.sleep(1.5)
    deadline = time.monotonic() + 3
    while True:
        values = selected(page)
        if not values or time.monotonic() >= deadline:
            return values
        time.sleep(0.1)


def submit_native(page: Any) -> dict[str, Any]:
    before = state(page).get("nativeResult")
    page.find(NATIVE_SUBMIT, timeout=8).click(simulative=False, delay_after=0.15)
    deadline = time.monotonic() + 5
    while time.monotonic() < deadline:
        text = state(page).get("nativeResult")
        if text != before:
            try:
                result = json.loads(text)
            except (TypeError, ValueError):
                result = None
            if isinstance(result, dict) and isinstance(result.get("cities"), list):
                return result
        time.sleep(0.1)
    raise RuntimeError("提交后未产生新的 cities JSON")


def native_case(page: Any, case_id: str, items: list[str], expected_values: list[str],
                *, mode: str = "fuzzy", append: bool = False, defaults: bool = False,
                preselect: bool = False) -> dict[str, Any]:
    started = time.perf_counter()
    expected = (f"{'预选北京；' if preselect else ''}select_multiple({items!r}, mode={mode!r}, "
                f"append={append}) 返回 None；DOM 与提交 cities={expected_values!r}；重置=[]")
    try:
        before = reset_native(page)
        target = page.find(NATIVE, timeout=8)
        if before or target.get_attribute("id") != "form-controls-native-cities":
            raise RuntimeError(f"基线或元素映射异常：{before!r}, id={target.get_attribute('id')!r}")
        if preselect:
            target.select_multiple(["北京"], mode="exact", delay_after=0.15)
            if selected(page) != ["beijing"]:
                raise RuntimeError("北京前置选择未建立")
        invoked = time.perf_counter()
        result = (target.select_multiple(items) if defaults else
                  target.select_multiple(items, mode=mode, append=append, delay_after=0.1))
        call_ms = (time.perf_counter() - invoked) * 1000
        deadline = time.monotonic() + 2
        while True:
            current = selected(page)
            if current == expected_values or time.monotonic() >= deadline:
                break
            time.sleep(0.1)
        payload = submit_native(page)
        after_reset = reset_native(page)
        actual_cities = payload.get("cities")
        ok = (result is None and current == expected_values and actual_cities == expected_values
              and after_reset == [] and (not defaults or call_ms >= 850))
        actual = (f"返回={result!r}，DOM={current!r}，提交 cities={actual_cities!r}，"
                  f"重置={after_reset!r}，调用耗时={call_ms:.1f}ms")
        return row(case_id, "PASS" if ok else "FAIL", expected, actual, started)
    except Exception as exc:
        return row(case_id, "FAIL", expected, error(exc), started)


def ant_boundary(page: Any, action_error: type) -> dict[str, Any]:
    started = time.perf_counter()
    expected = "Ant 库元素是 div；select_multiple(['北京','上海']) 抛 ActionError/element_not_selectable，状态不变"
    try:
        page.find(ANT_RESET, timeout=8).click(simulative=False, delay_after=0.1)
        target = page.find(ANT, timeout=8)
        before = state(page)
        if before["ant"]["tag"] != "DIV" or "ant-select-selection-overflow" not in (target.get_attribute("class") or ""):
            raise RuntimeError(f"Ant 库元素映射异常：{before['ant']!r}")
        try:
            result = target.select_multiple(["北京", "上海"], mode="exact", delay_after=0)
            return row("ant_custom_multiselect", "FAIL", expected,
                       f"未抛错，返回={result!r}，状态={state(page)!r}", started)
        except Exception as exc:
            after = state(page)
            ok = (isinstance(exc, action_error) and getattr(exc, "trace_info", "") == "element_not_selectable"
                  and after["ant"] == before["ant"] and after["native"] == before["native"])
            return row("ant_custom_multiselect", "KNOWN" if ok else "FAIL", expected,
                       f"{error(exc)}；Ant 前={before['ant']!r}；后={after['ant']!r}", started)
    except Exception as exc:
        return row("ant_custom_multiselect", "FAIL", expected, error(exc), started)


def invalid_case(page: Any, case_id: str, expected_type: type, fragment: str) -> dict[str, Any]:
    started = time.perf_counter()
    expected = f"{case_id} 抛 {expected_type.__name__}，错误含 {fragment!r}；DOM 不变"
    try:
        if reset_native(page):
            raise RuntimeError("参数校验前未清空选中项")
        target = page.find(NATIVE, timeout=8)
        before = selected(page)
        try:
            if case_id == "items_string":
                result = target.select_multiple("北京", delay_after=0)  # type: ignore[arg-type]
            elif case_id == "items_mixed":
                result = target.select_multiple(["北京", 1], delay_after=0)  # type: ignore[list-item]
            elif case_id == "mode_value_removed":
                result = target.select_multiple(["北京"], mode="value", delay_after=0)
            elif case_id == "regex_invalid":
                result = target.select_multiple(["["], mode="regex", delay_after=0)
            elif case_id == "items_missing":
                result = target.select_multiple()  # type: ignore[call-arg]
            elif case_id == "mode_positional":
                result = target.select_multiple(["北京"], "exact")  # type: ignore[call-arg]
            else:
                raise AssertionError(f"未定义用例：{case_id}")
            return row(case_id, "FAIL", expected, f"未抛错，返回={result!r}，DOM={selected(page)!r}", started)
        except Exception as exc:
            after = selected(page)
            correct = isinstance(exc, expected_type) and fragment in str(exc) and after == before
            return row(case_id, "PASS" if correct else "FAIL", expected,
                       f"{error(exc)}；前={before!r}；后={after!r}", started)
    except Exception as exc:
        return row(case_id, "FAIL", expected, error(exc), started)


def run(args: argparse.Namespace) -> tuple[list[dict[str, Any]], int, str]:
    sdk_src = args.product_root / "sdk" / "src"
    if str(sdk_src) not in sys.path:
        sys.path.insert(0, str(sdk_src))
    from uiautoma import ActionError, InvalidParamsError, StalePackageError, open as open_package, web
    from uiautoma.web import WebElement

    rows = [check_contract(WebElement)]
    commit = source_commit(args.product_root)
    if args.contract_only or rows[0]["status"] != "PASS":
        return rows, 0 if rows[0]["status"] == "PASS" else 1, commit

    temp_dir = args.test_root / ".pytest_tmp" / "select_multiple" / uuid.uuid4().hex
    package = page = native_ref = None
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
        actual_options = [(x["text"], x["value"]) for x in snapshot["native"]["options"]]
        native_ref = page.find(NATIVE, timeout=8)
        ant_ref = page.find(ANT, timeout=8)
        ok = (snapshot["native"]["tag"] == "SELECT" and snapshot["native"]["multiple"] is True
              and actual_options == list(OPTIONS) and snapshot["ant"]["tag"] == "DIV"
              and native_ref.get_attribute("id") == "form-controls-native-cities"
              and "ant-select-selection-overflow" in (ant_ref.get_attribute("class") or ""))
        rows.append(row("environment", "PASS" if ok else "BLOCKED",
                        "Runtime/Chrome/库可用；原生 select multiple 四项 option；Ant 为 div",
                        f"原标签数={baseline}；开关原状态={previous_switch!r}；"
                        f"原生 options={actual_options!r}；Ant={snapshot['ant']!r}", started))
        if not ok:
            raise RuntimeError("靶场 DOM 或元素库映射与预期不符")
        environment_ready = True

        rows.append(ant_boundary(page, ActionError))
        rows.append(native_case(page, "fuzzy_default", ["京", "海"], ["beijing", "shanghai"], defaults=True))
        rows.append(native_case(page, "exact_two", ["北京", "上海"], ["beijing", "shanghai"], mode="exact"))
        rows.append(native_case(page, "regex_two", ["^广", "^深"], ["guangzhou", "shenzhen"], mode="regex"))
        rows.append(native_case(page, "append_true", ["上海"], ["beijing", "shanghai"],
                                mode="exact", append=True, preselect=True))
        rows.append(native_case(page, "append_false", ["深圳"], ["shenzhen"],
                                mode="exact", preselect=True))
        rows.append(native_case(page, "empty_replace", [], [], mode="exact", preselect=True))
        rows.append(native_case(page, "empty_append", [], ["beijing"],
                                mode="exact", append=True, preselect=True))
        rows.append(native_case(page, "no_match_replace", ["不存在城市"], [],
                                mode="exact", preselect=True))
        rows.append(native_case(page, "no_match_append", ["不存在城市"], ["beijing"],
                                mode="exact", append=True, preselect=True))
        rows.append(native_case(page, "exact_case_sensitive", ["beijing"], [], mode="exact"))
        rows.append(invalid_case(page, "items_string", InvalidParamsError, "items"))
        rows.append(invalid_case(page, "items_mixed", InvalidParamsError, "items"))
        rows.append(invalid_case(page, "mode_value_removed", InvalidParamsError, "match"))
        rows.append(invalid_case(page, "regex_invalid", InvalidParamsError, "正则"))
        rows.append(invalid_case(page, "items_missing", TypeError, "items"))
        rows.append(invalid_case(page, "mode_positional", TypeError, "positional"))
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
        if native_ref is not None and package is not None:
            lifecycle_start = time.perf_counter()
            try:
                result = native_ref.select_multiple(["北京"], mode="exact", delay_after=0)
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
                        "恢复开关、关闭本次标签和库连接、删除临时副本；独立追踪本次标签 ID",
                        "; ".join(cleanup_errors) if cleanup_errors else f"逐项复核通过；{tab_note}", started))
    code = 1 if any(x["status"] == "FAIL" for x in rows) else 2 if any(
        x["status"] == "BLOCKED" for x in rows) else 0
    return rows, code, commit


def main() -> int:
    parser = argparse.ArgumentParser(description="WebElement.select_multiple() iframe/Shadow 表单实测")
    parser.add_argument("--contract-only", action="store_true")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--report-file", type=Path)
    parser.add_argument("--target-url", default=URL)
    parser.add_argument("--element-library", type=Path, default=LIBRARY)
    parser.add_argument("--product-root", type=Path, default=PRODUCT)
    parser.add_argument("--test-root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    rows, code, commit = run(args)
    report = {"api": "uiautoma.web.WebElement.select_multiple", "url": args.target_url,
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
