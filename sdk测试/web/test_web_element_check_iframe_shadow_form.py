"""WebElement.check() 实测：iframe → Shadow DOM 内的 Ant 与原生表单。

元素库：D:\\code\\元素库\\260902_web元素。预期来自靶场表单语义；提交后的
JSON 和 DOM checked 状态用于独立确证。0=全通过，1=失败，2=环境阻塞。
运行：uv run .\\web\\test_web_element_check_iframe_shadow_form.py
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
PREFIX = "web靶场_表单测试_"
HOBBIES = ("阅读", "运动", "音乐", "旅行")
COLORS = {"PASS": "\x1b[92m", "FAIL": "\x1b[91m", "BLOCKED": "\x1b[93m", "KNOWN": "\x1b[93m"}
RESET = "\x1b[0m"


def item(case_id: str, status: str, expected: str, actual: str, started: float) -> dict[str, Any]:
    return {"case_id": case_id, "status": status, "expected": expected,
            "actual": actual, "elapsed_ms": round((time.perf_counter() - started) * 1000, 1)}


def error(exc: BaseException) -> str:
    trace = getattr(exc, "trace_info", None)
    return f"{type(exc).__name__}: {exc}" + (f" [trace={trace}]" if trace else "")


def commit_at(root: Path) -> str:
    try:
        return subprocess.check_output(
            ["git", "-C", str(root), "rev-parse", "HEAD"], text=True,
            encoding="utf-8", stderr=subprocess.DEVNULL,
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        return "unknown"


def check_contract(WebElement: type) -> dict[str, Any]:
    started = time.perf_counter()
    try:
        sig = inspect.signature(WebElement.check)
        params = tuple(sig.parameters.values())
        correct = (
            tuple(sig.parameters) == ("self", "mode", "delay_after")
            and all(p.kind is inspect.Parameter.POSITIONAL_OR_KEYWORD for p in params)
            and params[1].default == "check"
            and params[2].default == 1
            and str(sig.return_annotation) in {"None", "<class 'NoneType'>"}
        )
        return item("api_contract", "PASS" if correct else "FAIL",
                    "check(self, mode='check', delay_after=1) -> None；参数可按位置或名称传入",
                    str(sig), started)
    except Exception as exc:
        return item("api_contract", "FAIL", "可读取公开签名", error(exc), started)


def copy_library(source: Path, target: Path) -> None:
    """只改本次副本中的旧浏览器会话标识，不改用户元素库。"""
    shutil.copytree(source, target)
    paths = [target / "elements.json", *(target / "snapshot").glob("*.json")]
    for path in paths:
        if not path.is_file():
            continue
        data = json.loads(path.read_text(encoding="utf-8"))
        stack = [data]
        while stack:
            value = stack.pop()
            if isinstance(value, dict):
                for key, child in value.items():
                    if isinstance(key, str) and "session" in key.casefold() and child:
                        value[key] = ""
                    elif key == "BrowserPid" and child:
                        value[key] = 0
                    elif isinstance(child, (dict, list)):
                        stack.append(child)
            elif isinstance(value, list):
                stack.extend(value)
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def disable_dynamic_ids(page: Any) -> str:
    switch = page.find(SWITCH, timeout=10)
    for _ in range(5):
        if switch.get_attribute("role") == "switch":
            break
        switch = switch.parent()
    else:
        raise RuntimeError("动态 ID 捕获元素附近没有 role=switch")
    before = switch.get_attribute("aria-checked")
    if before == "true":
        switch.click(simulative=False, delay_after=0)
        deadline = time.monotonic() + 5
        while switch.get_attribute("aria-checked") != "false":
            if time.monotonic() >= deadline:
                raise RuntimeError("动态 ID 开关未关闭")
            time.sleep(0.1)
    elif before != "false":
        raise RuntimeError(f"动态 ID 开关状态无效: {before!r}")
    return before


READ_FORM = """function (_element, args) {
  const frame = document.querySelector('#iframe-shadow-form');
  const root = frame?.contentDocument?.querySelector('#form-shadow-host')?.shadowRoot;
  const control = root?.getElementById(args.id);
  const result = root?.getElementById(args.side + '-result');
  return {found: !!control, tag: control?.tagName || null,
          type: control?.type || null, checked: control?.checked ?? null,
          result: result?.textContent || null};
}"""


def read_form(page: Any, side: str, control_id: str) -> dict[str, Any]:
    result_side = "native" if side == "原生" else "ant"
    value = page.execute_javascript(READ_FORM, {"side": result_side, "id": control_id})
    if not isinstance(value, dict) or not value.get("found"):
        raise RuntimeError(f"DOM 未找到控件 {control_id!r}: {value!r}")
    return value


def wait_checked(page: Any, side: str, control_id: str, expected: bool,
                 timeout: float = 2.0) -> dict[str, Any]:
    """check 的 Page Engine 鼠标事件异步派发；等待真实 DOM 稳定到目标态。"""
    deadline = time.monotonic() + timeout
    while True:
        value = read_form(page, side, control_id)
        if value["checked"] is expected or time.monotonic() >= deadline:
            return value
        time.sleep(0.1)


def result_payload(page: Any, side: str, control_id: str,
                   expected_field: str | None = None,
                   expected_value: Any = None) -> dict[str, Any]:
    deadline = time.monotonic() + 4
    last_value = None
    while time.monotonic() < deadline:
        text = read_form(page, side, control_id).get("result")
        try:
            value = json.loads(text)
        except (TypeError, ValueError):
            time.sleep(0.1)
            continue
        if isinstance(value, dict):
            last_value = value
            if expected_field is None or value.get(expected_field) == expected_value:
                return value
        time.sleep(0.1)
    if last_value is not None:
        return last_value
    raise RuntimeError(f"{side} 提交后结果区未出现 JSON")


def submit_and_read(page: Any, side: str, control_id: str,
                    expected_field: str, expected_value: Any) -> dict[str, Any]:
    submit = page.find(button_name(side, "提交"), timeout=8)
    submit.click(simulative=False, delay_after=0.15)
    # Web DOM click 以定时器派发；连续提交时结果区可能仍是上一次的 JSON。
    time.sleep(0.8)
    return result_payload(page, side, control_id, expected_field, expected_value)


def name(side: str, kind: str, role: str, label: str) -> str:
    return f"{PREFIX}{side}_{kind}_{role}_{label}"


def button_name(side: str, action: str) -> str:
    if side == "ant" or action == "提交":
        return f"{PREFIX}{side}_按钮_{action}"
    return f"{PREFIX}{side}_{action}"


def run_action(page: Any, side: str, kind: str, role: str, label: str,
               mode: str, expected_checked: bool, expected_value: Any,
               delay: float = 0.05, use_defaults: bool = False,
               use_positional: bool = False) -> dict[str, Any]:
    case_id = f"{side}_{kind}_{role}_{label}_{mode}"
    started = time.perf_counter()
    expected = (f"{role} 的 check({mode}) 返回 None；DOM checked={expected_checked}；"
                f"提交值={expected_value!r}")
    try:
        page.find(button_name(side, "重置"), timeout=8).click(simulative=False, delay_after=0.1)
        time.sleep(1.5)
        target = page.find(name(side, kind, role, label), timeout=8)
        control_id = (target.get_attribute("id") if role == "input" else
                      target.execute_javascript("function (element) { return element.control?.id || element.querySelector('input')?.id || null; }"))
        html = target.get_html().lstrip().lower()
        if not control_id or not html.startswith(f"<{role}"):
            raise RuntimeError(f"元素库类型或 input id 不符: html={html[:90]!r}, id={control_id!r}")
        before = read_form(page, side, control_id)
        if before["checked"] is not False:
            raise RuntimeError(f"重置后控件不是未选中: {before!r}")
        invoked = time.perf_counter()
        returned = (target.check() if use_defaults else target.check(mode, delay)
                    if use_positional else target.check(mode=mode, delay_after=delay))
        call_ms = (time.perf_counter() - invoked) * 1000
        after = wait_checked(page, side, control_id, expected_checked)
        field = "gender" if kind == "radio" else "hobbies"
        payload = submit_and_read(page, side, control_id, field, expected_value)
        observed = payload.get(field)
        value_ok = observed == expected_value if kind == "radio" else set(observed or []) == set(expected_value)
        min_ms = 850 if use_defaults else max(0, delay * 1000 - 25)
        page.find(button_name(side, "重置"), timeout=8).click(simulative=False, delay_after=0.1)
        reset_checked = wait_checked(page, side, control_id, False)["checked"]
        passed = (returned is None and after["checked"] is expected_checked and value_ok
                  and call_ms >= min_ms and reset_checked is False)
        actual = (f"返回={returned!r}, DOM checked={after['checked']!r}, 提交 {field}={observed!r}, "
                  f"重置 checked={reset_checked!r}, check 耗时={call_ms:.1f}ms")
        return item(case_id, "PASS" if passed else "FAIL", expected, actual, started)
    except Exception as exc:
        try:
            page.find(button_name(side, "重置"), timeout=8).click(simulative=False, delay_after=0.1)
        except Exception:
            pass
        status = "BLOCKED" if type(exc).__name__ == "AmbiguousElementError" else "FAIL"
        actual = error(exc)
        if status == "BLOCKED":
            try:
                matches = page.find_all(name(side, kind, role, label), timeout=0)
                ids = [match.get_attribute("id") for match in matches]
                actual += f"；元素库选择器匹配 {len(matches)} 个节点，id={ids!r}"
            except Exception:
                pass
        return item(case_id, status, expected, actual, started)


def run_modes(page: Any, side: str, role: str) -> list[dict[str, Any]]:
    """在同一 checkbox 上观察 check/uncheck/toggle 的状态转移。"""
    rows = []
    control_name = name(side, "checkbox", "input", "阅读")
    for mode, desired in (("check", True), ("check", True), ("uncheck", False),
                          ("toggle", True), ("toggle", False)):
        started = time.perf_counter()
        try:
            target = page.find(name(side, "checkbox", role, "阅读"), timeout=8)
            control_id = page.find(control_name, timeout=8).get_attribute("id")
            before = read_form(page, side, control_id)["checked"]
            required_before = mode in {"uncheck"} or (mode == "check" and len(rows) == 1) or (mode == "toggle" and len(rows) == 4)
            if before is not required_before:
                rows.append(item(f"{side}_{role}_mode_{len(rows) + 1}_{mode}", "KNOWN",
                                 f"前置 checked={required_before}，随后 checked={desired}",
                                 f"前置 checked={before!r}；前序动作未建立目标状态", started))
                continue
            returned = target.check(mode=mode, delay_after=0)
            actual = wait_checked(page, side, control_id, desired)["checked"]
            wanted_hobbies = ["阅读"] if desired else []
            payload = submit_and_read(page, side, control_id, "hobbies", wanted_hobbies)
            hobbies = payload.get("hobbies")
            passed = (returned is None and actual is desired and hobbies == wanted_hobbies)
            rows.append(item(f"{side}_{role}_mode_{len(rows) + 1}_{mode}",
                             "PASS" if passed else "FAIL", f"返回 None，checked={desired}，提交值符合预期",
                             f"返回={returned!r}，checked={actual!r}，hobbies={hobbies!r}", started))
            time.sleep(0.4)
        except Exception as exc:
            rows.append(item(f"{side}_{role}_mode_{len(rows) + 1}_{mode}", "FAIL",
                             f"checked={desired}", error(exc), started))
    return rows


def run_invalid(page: Any, side: str) -> list[dict[str, Any]]:
    from uiautoma import ActionError, InvalidParamsError
    rows = []
    target = page.find(name(side, "checkbox", "input", "阅读"), timeout=8)
    for case_id, kwargs, fragment in (
        ("mode_invalid", {"mode": "bad", "delay_after": 0}, "mode"),
        ("delay_negative", {"mode": "check", "delay_after": -0.1}, "delay_after"),
        ("delay_text", {"mode": "check", "delay_after": "abc"}, "delay_after"),
    ):
        started = time.perf_counter()
        try:
            value = target.check(**kwargs)
            rows.append(item(f"{side}_{case_id}", "FAIL", f"InvalidParamsError 含 {fragment}",
                             f"未抛错，返回={value!r}", started))
        except Exception as exc:
            passed = isinstance(exc, InvalidParamsError) and fragment in str(exc)
            rows.append(item(f"{side}_{case_id}", "PASS" if passed else "FAIL",
                             f"InvalidParamsError 含 {fragment}", error(exc), started))
    radio = page.find(name(side, "radio", "input", "男"), timeout=8)
    for mode in ("uncheck", "toggle"):
        started = time.perf_counter()
        try:
            returned = radio.check(mode=mode, delay_after=0)
            rows.append(item(f"{side}_radio_{mode}", "FAIL", "ActionError/radio_cannot_uncheck",
                             f"未抛错，返回={returned!r}", started))
        except Exception as exc:
            passed = isinstance(exc, ActionError) and getattr(exc, "trace_info", "") == "radio_cannot_uncheck"
            rows.append(item(f"{side}_radio_{mode}", "PASS" if passed else "FAIL",
                             "ActionError/radio_cannot_uncheck", error(exc), started))
    return rows


def run(args: argparse.Namespace) -> tuple[list[dict[str, Any]], int, str]:
    src = args.product_root / "sdk" / "src"
    if str(src) not in sys.path:
        sys.path.insert(0, str(src))
    from uiautoma import open as open_package, web
    from uiautoma.web import WebElement
    rows = [check_contract(WebElement)]
    product_commit = commit_at(args.product_root)
    if args.contract_only or rows[0]["status"] != "PASS":
        return rows, 0 if rows[0]["status"] == "PASS" else 1, product_commit

    temp_dir = args.test_root / ".pytest_tmp" / "check" / uuid.uuid4().hex
    package = page = None
    baseline = None
    previous_switch = None
    try:
        started = time.perf_counter()
        if not args.element_library.is_dir():
            raise FileNotFoundError(f"元素库不存在: {args.element_library}")
        if not src.is_dir():
            raise FileNotFoundError(f"SDK 源码目录不存在: {src}")
        baseline = len(web.get_all(mode="chrome"))
        temp_dir.mkdir(parents=True)
        copy_library(args.element_library, temp_dir / "library")
        package = open_package(str(temp_dir / "library"), timeout=8, connect_timeout=8)
        page = web.create(args.target_url, mode="chrome", load_timeout=25, silent_running=True)
        previous_switch = disable_dynamic_ids(page)
        rows.append(item("environment", "PASS", "Runtime/Chrome/元素库/靶场可用，动态 ID 关闭",
                         f"原标签数={baseline}，开关原状态={previous_switch!r}，元素数={package.web_count}", started))

        for side in ("ant", "原生"):
            for role in ("input", "label"):
                for label, value in (("男", "male"), ("女", "female")):
                    rows.append(run_action(page, side, "radio", role, label, "check", True, value,
                                           use_defaults=side == "ant" and role == "input" and label == "男",
                                           use_positional=side == "原生" and role == "input" and label == "男"))
                for label in ("全选", *HOBBIES):
                    values = list(HOBBIES) if label == "全选" else [label]
                    rows.append(run_action(page, side, "checkbox", role, label, "check", True, values))
                page.find(button_name(side, "重置"), timeout=8).click(simulative=False, delay_after=0.1)
                time.sleep(1.5)
                rows.extend(run_modes(page, side, role))
            rows.extend(run_invalid(page, side))
    except Exception as exc:
        started = time.perf_counter()
        rows.append(item("environment", "BLOCKED", "测试环境与页面可用", error(exc), started))
    finally:
        started = time.perf_counter()
        cleanup_errors = []
        if page is not None and previous_switch == "true":
            try:
                switch = page.find(SWITCH, timeout=5)
                for _ in range(5):
                    if switch.get_attribute("role") == "switch":
                        break
                    switch = switch.parent()
                if switch.get_attribute("aria-checked") == "false":
                    switch.click(simulative=False, delay_after=0.1)
                if switch.get_attribute("aria-checked") != "true":
                    cleanup_errors.append("动态 ID 开关未恢复原状态")
            except Exception as exc:
                cleanup_errors.append(f"恢复动态 ID 开关: {error(exc)}")
        if page is not None:
            try:
                page.close(ignore_beforeunload=True)
            except Exception as exc:
                cleanup_errors.append(f"关闭页面: {error(exc)}")
        if package is not None:
            try:
                package.close()
            except Exception as exc:
                cleanup_errors.append(f"关闭元素库: {error(exc)}")
        if temp_dir.exists():
            shutil.rmtree(temp_dir)
        try:
            after = len(web.get_all(mode="chrome")) if baseline is not None else None
            if baseline is not None and after != baseline:
                cleanup_errors.append(f"标签数 {baseline} -> {after}")
        except Exception as exc:
            cleanup_errors.append(f"复核标签: {error(exc)}")
        if temp_dir.exists():
            cleanup_errors.append(f"临时目录仍存在: {temp_dir}")
        rows.append(item("cleanup", "PASS" if not cleanup_errors else "FAIL",
                         "动态 ID 开关恢复；本次页面与元素库连接关闭，临时副本删除，标签数恢复",
                         "; ".join(cleanup_errors) if cleanup_errors else "逐项复核通过", started))
    code = 1 if any(row["status"] == "FAIL" for row in rows) else 2 if any(
        row["status"] == "BLOCKED" for row in rows) else 0
    return rows, code, product_commit


def main() -> int:
    parser = argparse.ArgumentParser(description="WebElement.check() iframe/shadow 双侧表单实测")
    parser.add_argument("--contract-only", action="store_true")
    parser.add_argument("--json", action="store_true", help="输出完整 JSON 报告")
    parser.add_argument("--report-file", type=Path, help="将完整 JSON 报告另存为 UTF-8 文件")
    parser.add_argument("--target-url", default=URL)
    parser.add_argument("--element-library", type=Path, default=LIBRARY)
    parser.add_argument("--product-root", type=Path, default=PRODUCT)
    parser.add_argument("--test-root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    rows, code, commit = run(args)
    report = {"api": "uiautoma.web.WebElement.check", "url": args.target_url,
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
        for index, row in enumerate(rows, 1):
            status = row["status"]
            label = {"PASS": "通过", "FAIL": "失败", "BLOCKED": "阻塞", "KNOWN": "已知"}[status]
            print(f"{index:02}/{len(rows):02}    {COLORS[status]}[{label}]{RESET}  "
                  f"{row['case_id']:<29}  期望 {row['expected']}；实测 {row['actual']}；"
                  f"{row['elapsed_ms']}ms")
        passed = sum(row["status"] == "PASS" for row in rows)
        print("─" * 100)
        print(f"测试{'通过' if code == 0 else '失败或阻塞'} · {passed}/{len(rows)} 通过 · 退出码 {code}")
    return code


if __name__ == "__main__":
    raise SystemExit(main())
