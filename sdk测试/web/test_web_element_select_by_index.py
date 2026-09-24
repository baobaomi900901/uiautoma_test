"""WebElement.select_by_index() 实测：原生 select 索引与 Ant 自定义下拉框边界。

靶场：https://baobaomi900901.github.io/xpath/#/iframe-shadow-form
元素库：D:\\code\\元素库\\260902_web元素（运行时只连接临时副本）。
期望来自页面 option 文本/value 与表单提交 JSON，状态由 DOM 独立复核。
退出码：0=全部 PASS（允许 KNOWN），1=FAIL，2=环境 BLOCKED。
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
NATIVE = "web靶场_表单测试_原生_select单选"
NATIVE_SUBMIT = "web靶场_表单测试_原生_按钮_提交"
NATIVE_RESET = "web靶场_表单测试_原生_重置"
ANT = "web靶场_表单测试_ant_select单选"
ANT_RESET = "web靶场_表单测试_ant_按钮_重置"
OPTIONS = (("请选择城市", ""), ("北京", "beijing"), ("上海", "shanghai"),
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


def check_contract(WebElement: type) -> dict[str, Any]:
    started = time.perf_counter()
    try:
        signature = inspect.signature(WebElement.select_by_index)
        parameters = list(signature.parameters.values())
        ok = (tuple(signature.parameters) == ("self", "index", "delay_after")
              and parameters[0].kind is inspect.Parameter.POSITIONAL_OR_KEYWORD
              and parameters[1].kind is inspect.Parameter.POSITIONAL_OR_KEYWORD
              and parameters[1].default is inspect.Parameter.empty
              and str(parameters[1].annotation) in {"int", "<class 'int'>"}
              and parameters[2].kind is inspect.Parameter.POSITIONAL_OR_KEYWORD
              and parameters[2].default == 1
              and str(parameters[2].annotation) in {"float", "<class 'float'>"}
              and str(signature.return_annotation) in {"None", "<class 'NoneType'>"})
        return row("api_contract", "PASS" if ok else "FAIL",
                   "select_by_index(self, index: int, delay_after: float=1) -> None",
                   str(signature), started)
    except Exception as exc:
        return row("api_contract", "FAIL", "可读取公开签名", error(exc), started)


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


READ = """function (_element) {
  const root = document.querySelector('#iframe-shadow-form')?.contentDocument
    ?.querySelector('#form-shadow-host')?.shadowRoot;
  const native = root?.getElementById('form-controls-native-city');
  const ant = root?.getElementById('form-controls-ant-city');
  const result = root?.getElementById('native-result');
  return {
    native: native ? {tag: native.tagName, value: native.value,
      selectedIndex: native.selectedIndex,
      options: [...native.options].map(x => ({text: x.text, value: x.value, selected: x.selected}))} : null,
    ant: ant ? {tag: ant.tagName, role: ant.getAttribute('role'),
      display: ant.closest('.ant-select')?.textContent || '', value: ant.value} : null,
    nativeResult: result?.textContent || null
  };
}"""

def state(page: Any) -> dict[str, Any]:
    value = page.execute_javascript(READ)
    if not isinstance(value, dict) or not value.get("native") or not value.get("ant"):
        raise RuntimeError(f"表单控件不可读：{value!r}")
    return value


def reset_native(page: Any) -> str:
    page.find(NATIVE_RESET, timeout=8).click(simulative=False, delay_after=0.1)
    time.sleep(1.5)
    return state(page)["native"]["value"]


def submit_native(page: Any, expected_city: str | None) -> dict[str, Any]:
    before = state(page).get("nativeResult")
    page.find(NATIVE_SUBMIT, timeout=8).click(simulative=False, delay_after=0.15)
    deadline = time.monotonic() + 5
    last = None
    while time.monotonic() < deadline:
        text = state(page).get("nativeResult")
        if text != before:
            try:
                value = json.loads(text)
            except (TypeError, ValueError):
                value = None
            if isinstance(value, dict):
                last = value
                if value.get("city") == expected_city:
                    return value
        time.sleep(0.1)
    if last is not None:
        return last
    raise RuntimeError("提交后未产生新的表单 JSON")


def native_case(page: Any, case_id: str, index: int, expected_value: str,
                *, call_style: str = "keyword_delay", preselect: bool = False) -> dict[str, Any]:
    started = time.perf_counter()
    expected = (f"{'先选择北京；' if preselect else ''}select_by_index({index}) 返回 None；"
                f"DOM value={expected_value!r}；提交 city={expected_value!r}；重置 value=''" )
    try:
        before = reset_native(page)
        target = page.find(NATIVE, timeout=8)
        control_id = target.get_attribute("id")
        if before != "" or control_id != "form-controls-native-city":
            raise RuntimeError(f"前置状态或库元素映射不符：value={before!r}, id={control_id!r}")
        if preselect:
            target.select_by_index(1, delay_after=0.2)
            if state(page)["native"]["value"] != "beijing":
                raise RuntimeError("越界或占位用例的北京前置选择未建立")
        invoked = time.perf_counter()
        if call_style == "default":
            returned = target.select_by_index(index)
        elif call_style == "positional_delay":
            returned = target.select_by_index(index, 0.1)
        elif call_style == "keyword_index":
            returned = target.select_by_index(index=index, delay_after=0.1)
        else:
            returned = target.select_by_index(index, delay_after=0.1)
        call_ms = (time.perf_counter() - invoked) * 1000
        deadline = time.monotonic() + 2
        while True:
            current = state(page)["native"]["value"]
            if current == expected_value or time.monotonic() >= deadline:
                break
            time.sleep(0.1)
        payload = submit_native(page, expected_value)
        after_reset = reset_native(page)
        passed = (returned is None and current == expected_value and payload.get("city") == expected_value
                  and after_reset == "" and (call_style != "default" or call_ms >= 850))
        actual = (f"返回={returned!r}，DOM value={current!r}，提交 city={payload.get('city')!r}，"
                  f"重置 value={after_reset!r}，调用耗时={call_ms:.1f}ms")
        return row(case_id, "PASS" if passed else "FAIL", expected, actual, started)
    except Exception as exc:
        return row(case_id, "FAIL", expected, error(exc), started)


def invalid_case(page: Any, case_id: str, expected_type: type,
                 message_fragment: str) -> dict[str, Any]:
    started = time.perf_counter()
    expected = f"{case_id} 抛出 {expected_type.__name__} 且含 {message_fragment!r}；DOM value 不变"
    try:
        before = reset_native(page)
        target = page.find(NATIVE, timeout=8)
        try:
            if case_id == "bool_index":
                returned = target.select_by_index(True, delay_after=0)
            elif case_id == "float_index":
                returned = target.select_by_index(1.0, delay_after=0)
            elif case_id == "string_index":
                returned = target.select_by_index("1", delay_after=0)
            elif case_id == "none_index":
                returned = target.select_by_index(None, delay_after=0)
            elif case_id == "index_missing":
                returned = target.select_by_index()
            else:
                raise AssertionError(f"未知用例：{case_id}")
            actual = f"未抛错，返回={returned!r}"
            passed = False
        except Exception as exc:
            after = state(page)["native"]["value"]
            passed = isinstance(exc, expected_type) and message_fragment in str(exc) and after == before
            actual = f"{error(exc)}；DOM value={after!r}"
        return row(case_id, "PASS" if passed else "FAIL", expected, actual, started)
    except Exception as exc:
        return row(case_id, "FAIL", expected, error(exc), started)


def ant_boundary(page: Any, ActionError: type) -> dict[str, Any]:
    started = time.perf_counter()
    expected = "Ant 库元素为 input[role=combobox]；select_by_index(1) 拒绝且无状态变化"
    try:
        page.find(ANT_RESET, timeout=8).click(simulative=False, delay_after=0.1)
        time.sleep(1.5)
        target = page.find(ANT, timeout=8)
        before = state(page)["ant"]
        if target.get_attribute("id") != "form-controls-ant-city" or before["tag"] != "INPUT":
            raise RuntimeError(f"Ant 库元素映射异常：{before!r}")
        try:
            returned = target.select_by_index(1, delay_after=0)
            return row("ant_custom_combobox", "FAIL", expected,
                       f"未拒绝，返回={returned!r}，状态={state(page)['ant']!r}", started)
        except Exception as exc:
            after = state(page)["ant"]
            correct = (isinstance(exc, ActionError) and getattr(exc, "trace_info", "") == "element_not_selectable"
                       and after == before)
            return row("ant_custom_combobox", "KNOWN" if correct else "FAIL", expected,
                       f"{error(exc)}；前={before!r}；后={after!r}", started)
    except Exception as exc:
        return row("ant_custom_combobox", "FAIL", expected, error(exc), started)


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

    temp_dir = args.test_root / ".pytest_tmp" / "select_by_index" / uuid.uuid4().hex
    package = page = None
    native_ref = None
    baseline = None
    baseline_ids: set[str] = set()
    test_page_id = None
    previous_switch = None
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
        ant = page.find(ANT, timeout=8)
        native = page.find(NATIVE, timeout=8)
        native_ref = native
        ok = (snapshot["native"]["tag"] == "SELECT" and actual_options == list(OPTIONS)
              and snapshot["ant"]["tag"] == "INPUT" and snapshot["ant"]["role"] == "combobox"
              and ant.get_attribute("id") == "form-controls-ant-city"
              and native.get_attribute("id") == "form-controls-native-city")
        rows.append(row("environment", "PASS" if ok else "BLOCKED",
                        "Runtime/Chrome/元素库可用；Ant 为 combobox、原生为标准 select；五项 option 符合靶场",
                        f"原标签数={baseline}；开关原状态={previous_switch!r}；"
                        f"Ant={snapshot['ant']!r}；原生 options={actual_options!r}", started))
        if not ok:
            raise RuntimeError("靶场 DOM 或元素库映射与预期不符")
        environment_ready = True

        rows.append(ant_boundary(page, ActionError))
        rows.append(native_case(page, "index_one_default", 1, "beijing", call_style="default"))
        rows.append(native_case(page, "index_two_positional_delay", 2, "shanghai", call_style="positional_delay"))
        rows.append(native_case(page, "index_zero_placeholder", 0, "", preselect=True))
        rows.append(native_case(page, "negative_last", -1, "shenzhen"))
        rows.append(native_case(page, "negative_second_last", -2, "guangzhou"))
        rows.append(native_case(page, "positive_out_of_range", 99, "beijing", preselect=True))
        rows.append(native_case(page, "negative_out_of_range", -99, "beijing", preselect=True))
        rows.append(native_case(page, "keyword_index", 3, "guangzhou", call_style="keyword_index"))
        rows.append(invalid_case(page, "bool_index", InvalidParamsError, "index"))
        rows.append(invalid_case(page, "float_index", InvalidParamsError, "index"))
        rows.append(invalid_case(page, "string_index", InvalidParamsError, "index"))
        rows.append(invalid_case(page, "none_index", InvalidParamsError, "index"))
        rows.append(invalid_case(page, "index_missing", TypeError, "index"))
    except Exception as exc:
        rows.append(row("environment_error", "FAIL" if environment_ready else "BLOCKED",
                        "测试环境与靶场可用，测试步骤可完成", error(exc), time.perf_counter()))
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
                returned = native_ref.select_by_index(1, delay_after=0)
                rows.append(row("closed_package", "FAIL", "库连接关闭后抛 StalePackageError",
                                f"未抛错，返回={returned!r}", lifecycle_start))
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
    parser = argparse.ArgumentParser(description="WebElement.select_by_index() iframe/Shadow 双侧表单实测")
    parser.add_argument("--contract-only", action="store_true")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--report-file", type=Path)
    parser.add_argument("--target-url", default=URL)
    parser.add_argument("--element-library", type=Path, default=LIBRARY)
    parser.add_argument("--product-root", type=Path, default=PRODUCT)
    parser.add_argument("--test-root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    rows, code, commit = run(args)
    report = {"api": "uiautoma.web.WebElement.select_by_index", "url": args.target_url,
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
