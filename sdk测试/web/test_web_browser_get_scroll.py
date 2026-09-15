"""WebBrowser.get_scroll() 页面对象 API 专项验收。

说明：
场景准备用 `execute_javascript()` 注入 4000×4000 的 spacer，确保页面可纵向与横向滚动。

语义要点（源码与实测一致）：`location="current"` 返回当前偏移（`scrollTop` / `scrollLeft`），
`location="bottom"` 返回**滚动内容的总高/总宽**（`scrollHeight` / `scrollWidth`），
不是最大可滚动偏移。因此「bottom」的断言是与内容尺寸相等，而不是与视口相关的最大偏移。

本 API 的读数与同页面独立 JS 读数（`window.scrollY/scrollX`、
`documentElement.scrollHeight/scrollWidth`）交叉核对；非法 `direction` / `location`
在 SDK 侧即被拒绝。

退出码：0 = 全部 PASS；1 = 存在 FAIL；2 = 无非 FAIL 但存在 BLOCKED。
"""
from __future__ import annotations

import argparse
import inspect
import json
import time
from urllib.parse import urlsplit

from uiautoma import InvalidParamsError, web
from uiautoma.web import WebBrowser

__test__ = False

DEFAULT_URL = "https://baobaomi900901.github.io/xpath/#/form-controls"
SPACER = """
function () {
  const d = document.createElement('div');
  d.id = 'uiautoma-scroll-spacer';
  d.style.height = '4000px';
  d.style.width = '4000px';
  d.style.pointerEvents = 'none';
  document.body.appendChild(d);
  return true;
}
"""
METRICS = """
function () {
  const el = document.documentElement;
  return {top: window.scrollY, left: window.scrollX,
          sh: el.scrollHeight, sw: el.scrollWidth,
          ch: el.clientHeight, cw: el.clientWidth};
}
"""
GREEN, RED, YELLOW, RESET = "\x1b[92m", "\x1b[91m", "\x1b[93m", "\x1b[0m"


def result(case_id: str, status: str, detail: str, **extra):
    return {"case_id": case_id, "status": status, "detail": detail, **extra}


def same_url(actual: str, expected: str) -> bool:
    a, e = urlsplit(str(actual)), urlsplit(str(expected))
    return (
        a.scheme.casefold(), a.netloc.casefold(), a.path or "/", a.query, a.fragment
    ) == (
        e.scheme.casefold(), e.netloc.casefold(), e.path or "/", e.query, e.fragment
    )


def check_contract():
    method = getattr(WebBrowser, "get_scroll", None)
    sig = inspect.signature(method) if callable(method) else None
    if sig is None:
        return result("api_contract", "FAIL", "WebBrowser.get_scroll 不存在")
    parameters = list(sig.parameters.values())
    names = tuple(sig.parameters)
    annotation = str(sig.return_annotation)
    ok = (
        names == ("self", "direction", "location")
        and all(p.kind is inspect.Parameter.KEYWORD_ONLY for p in parameters[1:])
        and parameters[1].default == "vertical"
        and parameters[2].default == "current"
        and annotation == "float"
    )
    detail = (
        "direction/location 仅限关键字（默认 vertical/current），返回注解 float"
        if ok
        else f"公开签名不符合合同: {sig}"
    )
    return result("api_contract", "PASS" if ok else "FAIL", detail, return_annotation=annotation)


def exception_name(exc: BaseException) -> str:
    return type(exc).__name__


def error_detail(prefix: str, exc: BaseException) -> str:
    trace_info = str(getattr(exc, "trace_info", "") or "")
    suffix = f" [trace={trace_info}]" if trace_info else ""
    return f"{prefix}: {exception_name(exc)}: {exc}{suffix}"


def expect_raises(call, expected_type, label: str):
    try:
        call()
    except expected_type as exc:
        trace = str(getattr(exc, "trace_info", "") or "")
        return result(
            label, "PASS",
            f"{exception_name(exc)} 正确拒绝" + (f"（trace={trace}）" if trace else ""),
            trace_info=trace,
        )
    except Exception as exc:  # noqa: BLE001
        return result(label, "FAIL", f"拒绝类型错误，应为 {expected_type.__name__}: {exception_name(exc)}: {exc}")
    return result(label, "FAIL", "调用未被拒绝")


def metrics(page: WebBrowser) -> dict:
    value = page.execute_javascript(METRICS)
    return value if isinstance(value, dict) else {}


def check_scroll(page: WebBrowser, case_id: str, kwargs: dict, expected: float, label: str, **extra):
    """调用 get_scroll 并断言数值、类型均为 float 且等于期望。"""
    try:
        value = page.get_scroll(**kwargs)
    except Exception as exc:  # noqa: BLE001
        return result(case_id, "FAIL", error_detail(f"{label} 调用失败", exc))
    type_ok = isinstance(value, float)
    value_ok = value == expected
    ok = type_ok and value_ok
    return result(
        case_id,
        "PASS" if ok else "FAIL",
        f"{label} 返回 float {expected}" if ok else
        f"{label} 结果不符: 期望 float {expected}，实际 {value!r}({type(value).__name__})",
        actual=repr(value), expected=repr(expected), **extra,
    )


def run(args):
    results = [check_contract()]
    if results[-1]["status"] != "PASS" or args.contract_only:
        return results, 0 if results[-1]["status"] == "PASS" else 1

    page = None
    try:
        started = time.perf_counter()
        page = web.create(args.target_url, mode=args.mode, load_timeout=args.load_timeout)
        elapsed = (time.perf_counter() - started) * 1000
        ok = isinstance(page, WebBrowser)
        results.append(result(
            "page_prepare",
            "PASS" if ok else "FAIL",
            f"已创建 WebBrowser 测试页面（{elapsed:.1f}ms）" if ok else "create 返回类型错误",
        ))
        if not ok:
            return results, 1

        initial_url = page.get_url()
        results.append(result(
            "initial_state",
            "PASS" if same_url(initial_url, args.target_url) else "FAIL",
            "初始 URL 可读" if same_url(initial_url, args.target_url) else f"URL 不符: {initial_url!r}",
            url=initial_url,
        ))

        # 场景准备：注入 spacer
        try:
            page.execute_javascript(SPACER)
            m0 = metrics(page)
            scrollable = float(m0.get("sh") or 0) > 0 and float(m0.get("sw") or 0) > 0
            results.append(result(
                "scrollable_prepare",
                "PASS" if scrollable else "FAIL",
                f"已注入 spacer：scrollHeight={m0.get('sh')}, scrollWidth={m0.get('sw')}" if scrollable else
                f"页面不可滚动: metrics={m0}",
                scroll_height=m0.get("sh"), scroll_width=m0.get("sw"),
            ))
            if not scrollable:
                return results, 1
        except Exception as exc:  # noqa: BLE001
            results.append(result("scrollable_prepare", "BLOCKED", error_detail("无法准备可滚动页面", exc)))
            return results, 2

        # 目标用例 1：位于顶部时默认读数为 0（float）
        page.scroll_to(location="top")
        results.append(check_scroll(page, "initial_current_zero", {}, 0.0, "位于顶部时默认读数"))

        # 目标用例 2：current 与同页面 JS 读数一致
        page.scroll_to(location="point", top=300, left=0)
        m = metrics(page)
        js_top = float(m.get("top") or 0)
        item = check_scroll(
            page, "current_matches_js", {}, js_top,
            "point(top=300) 后的 current 读数（与 JS window.scrollY 一致）",
            js_scroll_y=js_top,
        )
        if item["status"] == "PASS" and js_top != 300:
            item = result(
                "current_matches_js", "FAIL",
                f"点定位未落在 300：JS scrollY={js_top}",
                js_scroll_y=js_top,
            )
        results.append(item)

        # 目标用例 3：location=bottom 返回内容总高（不是最大偏移）
        m = metrics(page)
        content_height = float(m.get("sh") or 0)
        current_now = page.get_scroll()
        item = check_scroll(
            page, "vertical_bottom_content_height", {"location": "bottom"}, content_height,
            "vertical/bottom 返回滚动内容总高",
            scroll_height=content_height, current=current_now,
        )
        if item["status"] == "PASS" and not (content_height > current_now):
            item = result(
                "vertical_bottom_content_height", "FAIL",
                f"内容总高 {content_height} 未大于当前偏移 {current_now}，页面可能不可纵向滚动",
            )
        results.append(item)

        # 目标用例 4：横向 current 读数
        page.scroll_to(location="point", top=0, left=250)
        m = metrics(page)
        js_left = float(m.get("left") or 0)
        results.append(check_scroll(
            page, "horizontal_current", {"direction": "horizontal"}, js_left,
            "point(left=250) 后的 horizontal 读数（与 JS window.scrollX 一致）",
            js_scroll_x=js_left,
        ))

        # 目标用例 5：横向 bottom 返回内容总宽
        m = metrics(page)
        content_width = float(m.get("sw") or 0)
        results.append(check_scroll(
            page, "horizontal_bottom_content_width", {"direction": "horizontal", "location": "bottom"},
            content_width, "horizontal/bottom 返回滚动内容总宽",
            scroll_width=content_width,
        ))

        # 目标用例 6：全部组合的返回类型都是 float
        type_issues = []
        for direction in ("vertical", "horizontal"):
            for location in ("current", "bottom"):
                try:
                    value = page.get_scroll(direction=direction, location=location)
                except Exception as exc:  # noqa: BLE001
                    type_issues.append(f"{direction}/{location}: {exception_name(exc)}")
                    continue
                if not isinstance(value, float):
                    type_issues.append(f"{direction}/{location}: {type(value).__name__}")
        results.append(result(
            "all_combinations_float",
            "PASS" if not type_issues else "FAIL",
            "vertical/horizontal × current/bottom 四种组合均返回 float" if not type_issues else
            "；".join(type_issues),
            combinations=4,
        ))

        # 参数校验：非法 direction / location 在 SDK 侧拒绝
        results.append(expect_raises(lambda: page.get_scroll(direction="diagonal"), InvalidParamsError, "invalid_direction"))
        results.append(expect_raises(lambda: page.get_scroll(location="top"), InvalidParamsError, "invalid_location"))
        results.append(expect_raises(lambda: page.get_scroll("vertical"), TypeError, "extra_positional"))
        results.append(expect_raises(
            lambda: page.get_scroll(direction="vertical", unsupported=True),
            TypeError, "unknown_keyword",
        ))
    except Exception as exc:  # noqa: BLE001
        results.append(result("scenario", "FAIL", error_detail("get_scroll 场景执行失败", exc)))
    finally:
        if page is not None:
            try:
                page.close(ignore_beforeunload=True)
                results.append(result("cleanup", "PASS", "仅关闭本次创建的测试页面"))
            except Exception as exc:  # noqa: BLE001
                results.append(result("cleanup", "FAIL", error_detail("测试页面关闭失败", exc)))

    statuses = {item["status"] for item in results}
    code = 1 if "FAIL" in statuses else (2 if "BLOCKED" in statuses else 0)
    return results, code


def main(argv=None):
    parser = argparse.ArgumentParser(description="WebBrowser.get_scroll() 页面对象 API 验收")
    parser.add_argument("--target-url", default=DEFAULT_URL)
    parser.add_argument("--mode", choices=("chrome", "edge"), default="chrome")
    parser.add_argument("--load-timeout", type=float, default=20)
    parser.add_argument("--contract-only", action="store_true")
    parser.add_argument("--json", action="store_true", help="在表格后额外输出 JSON 报告（用于归档验收产物）")
    args = parser.parse_args(argv)
    if args.load_timeout <= 0:
        parser.error("--load-timeout 必须大于 0")

    results, code = run(args)
    print("UIAutoma Web API 测试")
    print("API     : uiautoma.web.WebBrowser.get_scroll")
    print(f"页面    : {args.target_url}")
    print("进度     状态    测试项                  测试结果")
    print("────────────────────────────────────────────────────────────────────────")
    for index, current in enumerate(results, 1):
        status = current["status"]
        color = {"PASS": GREEN, "BLOCKED": YELLOW}.get(status, RED)
        label = {"PASS": "通过", "BLOCKED": "阻塞"}.get(status, "失败")
        print(f"{index:02d}/{len(results):02d}    {color}[{label}]{RESET}  {current['case_id']:<30}  {current['detail']}")
    print("────────────────────────────────────────────────────────────────────────")
    summary = "测试通过" if code == 0 else ("测试阻塞" if code == 2 else "测试失败")
    print(f"{summary} · {sum(item['status'] == 'PASS' for item in results)}/{len(results)} 通过 · 退出码 {code}")
    if args.json:
        print(json.dumps({
            "api": "uiautoma.web.WebBrowser.get_scroll",
            "target_url": args.target_url,
            "mode": args.mode,
            "status": "PASS" if code == 0 else ("BLOCKED" if code == 2 else "FAIL"),
            "exit_code": code,
            "results": results,
        }, ensure_ascii=False, indent=2))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
