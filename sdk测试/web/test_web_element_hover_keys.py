"""WebElement.hover() keys-click-test 独立验收。"""
from __future__ import annotations

import argparse
import inspect
import json
from pathlib import Path
import shutil
import tempfile
import time
import uuid
from urllib.request import Request, urlopen

import uiautoma
from uiautoma import InvalidParamsError, ping, web
from uiautoma.web import WebBrowser, WebElement
from uiautoma.win32 import clipboard


URL = "https://baobaomi900901.github.io/xpath/#/keys-click-test"
LIBRARY = Path(r"D:\code\元素库\260902_web元素")
TARGET_NAME = "web靶场_测试点击_测试hover"
COPY_NAME = "web靶场_测试点击_读取最近一条点击记录"
TARGET_ID = "hover-target"
COPY_ID = "btn-copy-latest-keys-log"
GREEN, RED, YELLOW, RESET = "\x1b[92m", "\x1b[91m", "\x1b[93m", "\x1b[0m"


class Blocked(RuntimeError):
    pass


def error_detail(exc: BaseException) -> str:
    text = f"{type(exc).__name__}: {exc}"
    if getattr(exc, "trace_info", ""):
        text += f" [trace={exc.trace_info}]"
    if getattr(exc, "trace_id", ""):
        text += f" [trace_id={exc.trace_id}]"
    return text


def is_blocked(exc: BaseException) -> bool:
    return isinstance(exc, Blocked) or str(getattr(exc, "trace_info", "")) in {
        "browser_launch_timeout",
        "plugin_not_connected",
        "native_host_unavailable",
        "web_bridge_unavailable",
        "activate_tab_failed",
        "web_browser_command_timeout",
    }


def require(value: object, message: str) -> None:
    if not value:
        raise AssertionError(message)


def add_case(rows: list[dict], case_id: str, action) -> None:
    started = time.perf_counter()
    try:
        detail = action()
        rows.append({
            "case_id": case_id,
            "status": "PASS",
            "detail": str(detail),
            "elapsed_ms": round((time.perf_counter() - started) * 1000, 1),
        })
    except Exception as exc:  # noqa: BLE001
        rows.append({
            "case_id": case_id,
            "status": "BLOCKED" if is_blocked(exc) else "FAIL",
            "detail": error_detail(exc),
            "elapsed_ms": round((time.perf_counter() - started) * 1000, 1),
        })


def contract() -> str:
    signature = inspect.signature(WebElement.hover)
    params = signature.parameters
    expected = {"simulative": True, "delay_after": 1, "anchor": None}
    require(tuple(params) == ("self", *expected), f"公开签名不符: {signature}")
    for name, default in expected.items():
        require(params[name].kind == inspect.Parameter.POSITIONAL_OR_KEYWORD,
                f"{name} 应允许位置或关键字参数")
        require(params[name].default == default,
                f"{name} 默认值应为 {default!r}，实际为 {params[name].default!r}")
    require(str(signature.return_annotation).replace("'", "").replace('"', "").replace(" ", "")
            in {"None", "<classNoneType>"}, f"返回注解不符: {signature.return_annotation!r}")
    return "公开签名、位置/关键字参数、默认值与 None 返回值符合合同"


def preflight_target(timeout: float) -> str:
    last: BaseException | None = None
    for attempt in range(1, 4):
        try:
            request = Request(URL, headers={"User-Agent": "UIAutoma-SDK-persistent-test"})
            with urlopen(request, timeout=timeout) as response:
                status = int(getattr(response, "status", 200))
            require(200 <= status < 400, f"HTTP 状态异常: {status}")
            return f"悬停靶场可访问；HTTP 预检第 {attempt} 次成功（{status}）"
        except Exception as exc:  # noqa: BLE001
            last = exc
            time.sleep(0.2 * attempt)
    raise Blocked(f"悬停靶场 HTTPS 预检连续 3 次失败；最后错误: {last}")


def preflight_runtime(timeout: float) -> str:
    ping(timeout=timeout)
    return "Runtime 与 Automation Pipe 可响应"


def _named_elements(value: object) -> list[dict]:
    found: list[dict] = []
    if isinstance(value, dict):
        if str(value.get("name") or value.get("Name") or "") in {TARGET_NAME, COPY_NAME}:
            found.append(value)
        for child in value.values():
            found.extend(_named_elements(child))
    elif isinstance(value, list):
        for child in value:
            found.extend(_named_elements(child))
    return found


def preflight_library() -> str:
    elements_file = LIBRARY / "elements.json"
    require(LIBRARY.is_dir() and elements_file.is_file(), f"元素库不存在: {LIBRARY}")
    payload = json.loads(elements_file.read_text(encoding="utf-8"))
    matches = _named_elements(payload)
    counts = {name: sum(str(item.get("name") or item.get("Name") or "") == name for item in matches)
              for name in (TARGET_NAME, COPY_NAME)}
    require(counts[TARGET_NAME] == 1 and counts[COPY_NAME] == 1,
            f"元素库名称数量不符: {counts}")
    return f"元素库包含悬停元素和复制元素各 1 项；目录={LIBRARY}"


def scrub_copy(source: Path, root: Path) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    owned = Path(tempfile.mkdtemp(prefix="uiautoma-hover-", dir=root))
    shutil.copytree(source, owned, dirs_exist_ok=True)
    elements_file = owned / "elements.json"
    payload = json.loads(elements_file.read_text(encoding="utf-8"))

    def scrub(value: object) -> None:
        if isinstance(value, dict):
            for key, child in list(value.items()):
                if "session" in str(key).casefold() and child:
                    value[key] = ""
                elif str(key).casefold() == "browserpid":
                    value[key] = 0
                else:
                    scrub(child)
        elif isinstance(value, list):
            for child in value:
                scrub(child)

    scrub(payload)
    elements_file.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return owned


def setup(args: argparse.Namespace):
    temp_root = Path(__file__).resolve().parents[1] / ".pytest_tmp"
    owned = scrub_copy(args.library, temp_root)
    package: object | None = None
    page: WebBrowser | None = None
    try:
        package = uiautoma.open(str(owned), timeout=args.runtime_timeout,
                                connect_timeout=args.runtime_timeout)
        page = web.create(URL, mode="chrome", load_timeout=args.load_timeout, silent_running=False)
        page.activate()
        active = web.get_active("chrome", load_timeout=2)
        require(active.get_url() == page.get_url(), "测试页面未成为当前活动页面")
        target = page.find(TARGET_NAME, timeout=args.element_timeout)
        copy = page.find(COPY_NAME, timeout=args.element_timeout)
        require(target.get_attribute("id") == TARGET_ID,
                f"悬停元素 DOM id 不符: {target.get_attribute('id')!r}")
        require(copy.get_attribute("id") == COPY_ID,
                f"复制元素 DOM id 不符: {copy.get_attribute('id')!r}")
        return owned, package, page, target, copy
    except Exception:
        if page:
            try:
                page.close(ignore_beforeunload=True)
            except Exception:
                pass
        if package:
            try:
                package.close()
            except Exception:
                pass
        shutil.rmtree(owned, ignore_errors=True)
        raise


def copy_latest_record(copy: WebElement, timeout: float = 5.0) -> dict:
    marker = f"uiautoma-hover-sentinel-{uuid.uuid4().hex}"
    clipboard.set_text(marker)
    copy.click(simulative=False, delay_after=0)
    deadline = time.monotonic() + timeout
    last: BaseException | None = None
    while time.monotonic() < deadline:
        try:
            text = clipboard.get_text()
            if text and text != marker:
                payload = json.loads(text)
                require(isinstance(payload, dict), "剪贴板记录不是 JSON 对象")
                return payload
        except Exception as exc:  # noqa: BLE001
            last = exc
        time.sleep(0.05)
    raise Blocked(f"复制按钮未写入有效悬停 JSON；最后错误: {last}")


def hover_case(page: WebBrowser, target: WebElement, copy: WebElement, kwargs: dict, wait: float) -> str:
    page.activate()
    # 靶场只在鼠标进入目标时写入 hover 记录；锚点测试可能仍在同一元素内部移动。
    # 先用真实鼠标移到复制按钮，确保下一次物理 hover 从元素外重新进入目标。
    if bool(kwargs.get("simulative", True)):
        copy.hover(simulative=True, delay_after=0)
        time.sleep(0.05)
    started = time.perf_counter()
    returned = target.hover(**kwargs)
    elapsed = (time.perf_counter() - started) * 1000
    require(returned is None, "hover 返回值应为 None")
    payload = copy_latest_record(copy, timeout=wait)
    require(payload.get("buttonId") == TARGET_ID,
            f"日志 buttonId 预期 {TARGET_ID!r}，实际 {payload.get('buttonId')!r}")
    require(payload.get("eventType") == "hover",
            f"日志 eventType 预期 'hover'，实际 {payload.get('eventType')!r}")
    require(payload.get("detectedKeys") in {"-", "none"},
            f"日志 detectedKeys 异常: {payload.get('detectedKeys')!r}")
    trusted = payload.get("isTrusted")
    source = str(payload.get("clickSource") or "")
    require(isinstance(trusted, bool), "日志 isTrusted 应为 bool")
    simulative = bool(kwargs.get("simulative", True))
    if simulative:
        require(trusted is True and "真实鼠标" in source,
                f"simulative=True 应为真实鼠标/trusted=True，实际 source={source!r}, trusted={trusted!r}")
    else:
        require(trusted is False and any(token in source for token in ("JS", "插件", "模拟")),
                f"simulative=False 应为脚本模拟/trusted=False，实际 source={source!r}, trusted={trusted!r}")
    delay = kwargs.get("delay_after")
    if delay is None:
        delay_ok = True
    else:
        delay_ok = elapsed >= max(0.0, float(delay) * 1000 - 80)
    require(delay_ok, f"delay_after={delay!r} 等待不足，调用耗时 {elapsed:.1f}ms")
    mode = "模拟人工" if simulative else "后台"
    return f"{mode} hover 返回 None；eventType=hover；source={source}；trusted={trusted}；调用 {elapsed:.1f}ms"


def invalid_case(target: WebElement, kind: str) -> str:
    action = {
        "simulative": lambda: target.hover(simulative=1),
        "delay_negative": lambda: target.hover(delay_after=-1),
        "delay_text": lambda: target.hover(delay_after="bad"),
        "anchor": lambda: target.hover(anchor="invalid"),
        "unknown": lambda: target.hover(unsupported=True),
    }[kind]
    expected = TypeError if kind == "unknown" else InvalidParamsError
    try:
        action()
    except expected as exc:
        return f"预期 {expected.__name__}；实际 {type(exc).__name__}: {exc}"
    raise AssertionError(f"预期 {expected.__name__}，实际未抛异常")


def cleanup(page: WebBrowser | None, package: object | None, owned: Path | None) -> list[tuple[str, str, str]]:
    rows: list[tuple[str, str, str]] = []
    if page:
        try:
            page.close(ignore_beforeunload=True)
            rows.append(("cleanup_page", "PASS", "本次页面已关闭"))
        except Exception as exc:
            rows.append(("cleanup_page", "FAIL", error_detail(exc)))
    if package:
        try:
            package.close()
            rows.append(("cleanup_package", "PASS", "本次 Package 已关闭"))
        except Exception as exc:
            rows.append(("cleanup_package", "FAIL", error_detail(exc)))
    if owned:
        try:
            shutil.rmtree(owned)
            rows.append(("cleanup_temp", "PASS", "临时元素库副本已删除"))
        except Exception as exc:
            rows.append(("cleanup_temp", "FAIL", error_detail(exc)))
    return rows


def print_report(rows: list[dict], args: argparse.Namespace) -> int:
    total = len(rows)
    passed = sum(item["status"] == "PASS" for item in rows)
    blocked_count = sum(item["status"] == "BLOCKED" for item in rows)
    failed = total - passed - blocked_count
    code = 1 if failed else (2 if blocked_count else 0)
    print("UIAutoma Web API 测试")
    print("API     : uiautoma.web.WebElement.hover")
    print(f"页面    : {URL}")
    print(f"元素库  : {args.library}")
    print(f"测试元素: {TARGET_NAME}")
    print(f"复制元素: {COPY_NAME}")
    print("参照    : 靶场 hover JSON；核对目标、事件类型、来源、isTrusted 和 delay_after")
    print("进度     状态    测试项                         测试结果")
    print("────────────────────────────────────────────────────────────────────────────────────────")
    for index, item in enumerate(rows, 1):
        status = item["status"]
        color = GREEN if status == "PASS" else (YELLOW if status == "BLOCKED" else RED)
        label = {"PASS": "通过", "FAIL": "失败", "BLOCKED": "阻塞"}[status]
        print(f"{index:02d}/{total:02d}    {color}[{label}]{RESET}  {item['case_id']:<30} {item['detail']}  {item['elapsed_ms']:.1f}ms")
    print("────────────────────────────────────────────────────────────────────────────────────────")
    summary = "测试通过" if code == 0 else ("测试阻塞" if code == 2 else "测试失败")
    print(f"{summary} · {passed}/{total} 通过" + (f" · {blocked_count} 阻塞" if blocked_count else "") + f" · 退出码 {code}")
    return code


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="WebElement.hover() keys-click-test 独立验收")
    parser.add_argument("--library", type=Path, default=LIBRARY)
    parser.add_argument("--element-timeout", type=float, default=10)
    parser.add_argument("--runtime-timeout", type=float, default=20)
    parser.add_argument("--load-timeout", type=float, default=20)
    parser.add_argument("--wait-timeout", type=float, default=5)
    parser.add_argument("--contract-only", action="store_true")
    args = parser.parse_args(argv)
    args.library = args.library.resolve()
    rows: list[dict] = []
    add_case(rows, "api_contract", contract)
    if args.contract_only:
        return print_report(rows, args)

    add_case(rows, "target_preflight", lambda: preflight_target(5))
    if rows[-1]["status"] != "PASS":
        return print_report(rows, args)
    add_case(rows, "runtime_preflight", lambda: preflight_runtime(args.runtime_timeout))
    if rows[-1]["status"] != "PASS":
        return print_report(rows, args)
    add_case(rows, "element_library_preflight", preflight_library)
    if rows[-1]["status"] != "PASS":
        return print_report(rows, args)

    owned = package = page = target = copy = None
    try:
        owned, package, page, target, copy = setup(args)
        add_case(rows, "page_and_elements", lambda: "靶场已打开并激活；悬停元素与复制元素 DOM id 已核对")
        cases = [
            ("hover_default", {"simulative": True, "delay_after": 1}),
            ("hover_background", {"simulative": False, "delay_after": 0}),
            ("hover_none_delay", {"simulative": False, "delay_after": None}),
            ("hover_positive_delay", {"simulative": False, "delay_after": 0.2}),
            ("hover_anchor_string", {"simulative": True, "delay_after": 0, "anchor": "top_left"}),
            ("hover_anchor_tuple", {"simulative": True, "delay_after": 0, "anchor": ("bottom_right", -4, -4)}),
            ("hover_anchor_dict", {"simulative": True, "delay_after": 0, "anchor": {"anchor": "middle_center"}}),
            ("hover_anchor_random", {"simulative": True, "delay_after": 0, "anchor": "random"}),
            ("hover_repeat", {"simulative": False, "delay_after": 0}),
        ]
        for case_id, kwargs in cases:
            add_case(rows, case_id, lambda kwargs=kwargs: hover_case(page, target, copy, kwargs, args.wait_timeout))
        for case_id, kind in (
            ("invalid_simulative", "simulative"),
            ("invalid_delay_negative", "delay_negative"),
            ("invalid_delay_type", "delay_text"),
            ("invalid_anchor", "anchor"),
            ("unknown_keyword", "unknown"),
        ):
            add_case(rows, case_id, lambda kind=kind: invalid_case(target, kind))
        add_case(rows, "positional_arguments", lambda: hover_case(
            page, target, copy, {"simulative": False, "delay_after": 0}, args.wait_timeout
        ) if target.hover(False, 0) is None else (_ for _ in ()).throw(AssertionError("返回值不为 None")))
    except Exception as exc:  # noqa: BLE001
        add_case(rows, "scenario_orchestration", lambda: (_ for _ in ()).throw(exc))
    finally:
        for case_id, status, detail in cleanup(page, package, owned):
            rows.append({"case_id": case_id, "status": status, "detail": detail, "elapsed_ms": 0.0})
    return print_report(rows, args)


if __name__ == "__main__":
    raise SystemExit(main())
