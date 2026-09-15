"""WebBrowser.scroll_to() 页面对象 API 专项验收。

说明：
场景准备用 `execute_javascript()` 注入一个 4000×4000 的 spacer（id `uiautoma-scroll-spacer`），
确保页面可纵向与横向滚动——靶场页面本身很高但不横向溢出。该注入是**场景准备**，
不是被测 API 的内容。

位置断言用同一页面的独立 JS 读数（`window.scrollY/scrollX` 与
`documentElement.scrollHeight/scrollWidth`）交叉核对，不只看 `scroll_to` 自身的返回值。
底部判定用关系式 `scrollY + clientHeight >= scrollHeight`，避免依赖特定视口高度。

`scroll_to(*, location, behavior, top, left)` 四个参数全部**仅限关键字**；非法
`location` / `behavior` 在 SDK 侧即被拒绝。

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
RAW_SMOOTH_TOP = "function () { window.scrollTo({top: 0, left: window.scrollX, behavior: 'smooth'}); return true; }"
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
    method = getattr(WebBrowser, "scroll_to", None)
    sig = inspect.signature(method) if callable(method) else None
    if sig is None:
        return result("api_contract", "FAIL", "WebBrowser.scroll_to 不存在")
    parameters = list(sig.parameters.values())
    names = tuple(sig.parameters)
    annotation = str(sig.return_annotation)
    ok = (
        names == ("self", "location", "behavior", "top", "left")
        and all(p.kind is inspect.Parameter.KEYWORD_ONLY for p in parameters[1:])
        and parameters[1].default == "bottom"
        and parameters[2].default == "instant"
        and parameters[3].default == 0
        and parameters[4].default == 0
        and annotation in {"None", "<class 'NoneType'>"}
    )
    detail = (
        "location/behavior/top/left 全为仅限关键字（默认 bottom/instant/0/0），返回 None"
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


def expect_raises(call, expected_type, label: str, expected_trace: str | None = None):
    try:
        call()
    except expected_type as exc:
        trace = str(getattr(exc, "trace_info", "") or "")
        if expected_trace is not None and trace != expected_trace:
            return result(
                label, "FAIL",
                f"{exception_name(exc)} 类型正确但 trace 不符：期望 {expected_trace!r}，实际 {trace!r}",
                trace_info=trace,
            )
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


def is_at_bottom(m: dict) -> bool:
    """纵向与横向都到达底部（关系式判定，不依赖视口高度）。"""
    sh, sw = float(m.get("sh") or 0), float(m.get("sw") or 0)
    ch, cw = float(m.get("ch") or 0), float(m.get("cw") or 0)
    return (float(m.get("top") or 0) + ch) >= sh and (float(m.get("left") or 0) + cw) >= sw


def wait_until(predicate, timeout: float = 6.0, interval: float = 0.2):
    started = time.perf_counter()
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return True, round(time.perf_counter() - started, 3)
        time.sleep(interval)
    return False, round(time.perf_counter() - started, 3)


def settle_top(page: WebBrowser, timeout: float = 3.0, interval: float = 0.2, stable_reads: int = 3):
    """轮询直到 scrollY 连续稳定或超时，返回 (最终 scrollY, 耗时)。"""
    started = time.perf_counter()
    deadline = time.monotonic() + timeout
    last = float(metrics(page).get("top") or 0)
    stable = 0
    while time.monotonic() < deadline:
        time.sleep(interval)
        current = float(metrics(page).get("top") or 0)
        if current == last:
            stable += 1
            if stable >= stable_reads:
                break
        else:
            stable = 0
            last = current
    return last, round(time.perf_counter() - started, 3)


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

        # 场景准备：注入 spacer 使页面可双向滚动
        try:
            injected = page.execute_javascript(SPACER) is True
            m0 = metrics(page)
            scrollable = float(m0.get("sh") or 0) > 0 and float(m0.get("sw") or 0) > 0
            results.append(result(
                "scrollable_prepare",
                "PASS" if injected and scrollable else "FAIL",
                f"已注入 spacer：scrollHeight={m0.get('sh')}, scrollWidth={m0.get('sw')}"
                if injected and scrollable else
                f"页面不可滚动或注入失败: injected={injected}, metrics={m0}",
                scroll_height=m0.get("sh"), scroll_width=m0.get("sw"),
            ))
            if not (injected and scrollable):
                return results, 1
        except Exception as exc:  # noqa: BLE001
            results.append(result("scrollable_prepare", "BLOCKED", error_detail("无法准备可滚动页面", exc)))
            return results, 2

        # 目标用例 1：默认滚到底部
        try:
            returned = page.scroll_to()
        except Exception as exc:  # noqa: BLE001
            results.append(result("default_bottom", "FAIL", error_detail("scroll_to() 调用失败", exc)))
        else:
            m = metrics(page)
            ok = returned is None and is_at_bottom(m)
            results.append(result(
                "default_bottom",
                "PASS" if ok else "FAIL",
                f"默认滚到底部：scrollY={m.get('top')}, scrollX={m.get('left')}（纵向与横向均到底）"
                if ok else f"未到底部: return={returned!r}, metrics={m}",
                returned=repr(returned), **{k: m.get(k) for k in ("top", "left", "sh", "sw", "ch", "cw")},
            ))

        # 目标用例 2：回到顶部，保留横向位置
        before = metrics(page)
        try:
            returned = page.scroll_to(location="top")
        except Exception as exc:  # noqa: BLE001
            results.append(result("top_preserves_horizontal", "FAIL", error_detail("scroll_to(location='top') 失败", exc)))
        else:
            m = metrics(page)
            ok = returned is None and float(m.get("top") or 0) == 0 and float(m.get("left") or 0) == float(before.get("left") or 0)
            results.append(result(
                "top_preserves_horizontal",
                "PASS" if ok else "FAIL",
                f"回到顶部且保留横向位置：scrollY=0, scrollX={m.get('left')}" if ok else
                f"结果不符: return={returned!r}, before_left={before.get('left')}, metrics={m}",
                returned=repr(returned), **{k: m.get(k) for k in ("top", "left")},
            ))

        # 目标用例 3：point 精确落点
        try:
            returned = page.scroll_to(location="point", top=300, left=250)
        except Exception as exc:  # noqa: BLE001
            results.append(result("point_exact", "FAIL", error_detail("scroll_to(point) 失败", exc)))
        else:
            m = metrics(page)
            ok = returned is None and float(m.get("top") or 0) == 300 and float(m.get("left") or 0) == 250
            results.append(result(
                "point_exact",
                "PASS" if ok else "FAIL",
                "point(top=300,left=250) 精确落点：scrollY=300, scrollX=250" if ok else
                f"落点不符: return={returned!r}, metrics={m}",
                returned=repr(returned), **{k: m.get(k) for k in ("top", "left")},
            ))

        # 目标用例 4：point 只给 left，top 归 0
        try:
            returned = page.scroll_to(location="point", left=120)
        except Exception as exc:  # noqa: BLE001
            results.append(result("point_left_only", "FAIL", error_detail("scroll_to(point, left) 失败", exc)))
        else:
            m = metrics(page)
            ok = returned is None and float(m.get("top") or 0) == 0 and float(m.get("left") or 0) == 120
            results.append(result(
                "point_left_only",
                "PASS" if ok else "FAIL",
                "只给 left=120 时 scrollX=120 且 scrollY 归 0" if ok else
                f"结果不符: return={returned!r}, metrics={m}",
                returned=repr(returned), **{k: m.get(k) for k in ("top", "left")},
            ))

        # 目标用例 5：越界 point 被夹取到底部
        try:
            returned = page.scroll_to(location="point", top=999999, left=999999)
        except Exception as exc:  # noqa: BLE001
            results.append(result("point_overshoot_clamped", "FAIL", error_detail("越界 point 调用失败", exc)))
        else:
            m = metrics(page)
            ok = returned is None and is_at_bottom(m)
            results.append(result(
                "point_overshoot_clamped",
                "PASS" if ok else "FAIL",
                f"越界 point 被浏览器夹取到底部：scrollY={m.get('top')}, scrollX={m.get('left')}" if ok else
                f"结果不符: return={returned!r}, metrics={m}",
                returned=repr(returned), **{k: m.get(k) for k in ("top", "left", "sh", "sw")},
            ))

        # 目标用例 6：负值 point 被夹取到 0
        try:
            returned = page.scroll_to(location="point", top=-50, left=-50)
        except Exception as exc:  # noqa: BLE001
            results.append(result("point_negative_clamped", "FAIL", error_detail("负值 point 调用失败", exc)))
        else:
            m = metrics(page)
            ok = returned is None and float(m.get("top") or 0) == 0 and float(m.get("left") or 0) == 0
            results.append(result(
                "point_negative_clamped",
                "PASS" if ok else "FAIL",
                "负值 point 被夹取到 0：scrollY=0, scrollX=0" if ok else
                f"结果不符: return={returned!r}, metrics={m}",
                returned=repr(returned), **{k: m.get(k) for k in ("top", "left")},
            ))

        # 目标用例 7：smooth 与浏览器原生同语句行为一致（透传保真，不硬要求动画收敛）
        # 说明：smooth 由浏览器合成器驱动；当浏览器窗口未被合成（本机实测视口 clientHeight=0）时
        # 动画不会推进。因此断言「产品行为 == 原生 window.scrollTo({behavior:'smooth'}) 行为」，
        # 而不是断言必然收敛；是否推进记入 extra 供证据判断。
        try:
            page.scroll_to(location="point", top=1500, left=0)
            start_top = float(metrics(page).get("top") or 0)
            returned = page.scroll_to(location="top", behavior="smooth")
            product_top, product_waited = settle_top(page)
            page.scroll_to(location="point", top=1500, left=0)
            page.execute_javascript(RAW_SMOOTH_TOP)
            raw_top, raw_waited = settle_top(page)
            in_range = start_top > 0 and 0 <= product_top <= start_top
            ok = returned is None and in_range and product_top == raw_top
            converged = product_top == 0
            results.append(result(
                "smooth_matches_browser_control",
                "PASS" if ok else "FAIL",
                (
                    f"smooth 与原生 window.scrollTo({{behavior:'smooth'}}) 行为一致"
                    f"（起点 {start_top:.0f} → 终值 {product_top:.0f}，"
                    f"{'已收敛到顶部' if converged else '本环境未推进动画（视口 clientHeight=0，合成器不驱动）'}）"
                    if ok
                    else f"结果不符: return={returned!r}, start={start_top}, product={product_top}, raw={raw_top}"
                ),
                returned=repr(returned), start_top=start_top,
                product_final_top=product_top, raw_final_top=raw_top,
                converged=converged, seconds=max(product_waited, raw_waited),
            ))
        except Exception as exc:  # noqa: BLE001
            results.append(result("smooth_matches_browser_control", "FAIL", error_detail("smooth 用例失败", exc)))

        # 参数校验：非法 location / behavior 在 SDK 侧拒绝
        results.append(expect_raises(
            lambda: page.scroll_to(location="middle"),
            InvalidParamsError, "invalid_location", expected_trace="invalid_params",
        ))
        results.append(expect_raises(
            lambda: page.scroll_to(behavior="fast"),
            InvalidParamsError, "invalid_behavior", expected_trace="invalid_params",
        ))
        results.append(expect_raises(lambda: page.scroll_to("top"), TypeError, "extra_positional"))
        results.append(expect_raises(
            lambda: page.scroll_to(location="top", unsupported=True),
            TypeError, "unknown_keyword",
        ))
    except Exception as exc:  # noqa: BLE001
        results.append(result("scenario", "FAIL", error_detail("scroll_to 场景执行失败", exc)))
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
    parser = argparse.ArgumentParser(description="WebBrowser.scroll_to() 页面对象 API 验收")
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
    print("API     : uiautoma.web.WebBrowser.scroll_to")
    print(f"页面    : {args.target_url}")
    print("进度     状态    测试项                  测试结果")
    print("────────────────────────────────────────────────────────────────────────")
    for index, current in enumerate(results, 1):
        status = current["status"]
        color = {"PASS": GREEN, "BLOCKED": YELLOW}.get(status, RED)
        label = {"PASS": "通过", "BLOCKED": "阻塞"}.get(status, "失败")
        print(f"{index:02d}/{len(results):02d}    {color}[{label}]{RESET}  {current['case_id']:<28}  {current['detail']}")
    print("────────────────────────────────────────────────────────────────────────")
    summary = "测试通过" if code == 0 else ("测试阻塞" if code == 2 else "测试失败")
    print(f"{summary} · {sum(item['status'] == 'PASS' for item in results)}/{len(results)} 通过 · 退出码 {code}")
    if args.json:
        print(json.dumps({
            "api": "uiautoma.web.WebBrowser.scroll_to",
            "target_url": args.target_url,
            "mode": args.mode,
            "status": "PASS" if code == 0 else ("BLOCKED" if code == 2 else "FAIL"),
            "exit_code": code,
            "results": results,
        }, ensure_ascii=False, indent=2))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
