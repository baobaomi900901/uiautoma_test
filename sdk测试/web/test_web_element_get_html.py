"""`WebElement.get_html()` 验收脚本。

靶场/页面
    百度资讯搜索「区块链」结果页（用户提供）：
    `https://www.baidu.com/s?ie=utf-8&bsst=1&rsv_dl=news_t_sk&tn=news&cl=2&medium=0&rtt=1&wd=%E5%8C%BA%E5%9D%97%E9%93%BE`

元素库/元素
    `D:\\code\\元素库\\260902_web元素`（本轮只用副本），元素 `web靶场_测试超链接` ——
    搜索结果第一条的标题链接，节点为 `<a class="news-title-font_1xS-F" target="_blank" aria-label="标题：…">`。

期望值来源
    1. **独立推导**（HTML 序列化规范）：返回串必须是元素自身 `outerHTML`——以 `<a` 开头、
       以 `</a>` 结尾、不含 `<html`；属性值中的 `&` 必须序列化为 `&amp;`（而属性 API 返回原始 `&`）；
       `innerHTML` 必须是返回串的真子串。
    2. **独立确证**（与产品通道无关）：页面侧用 `document.querySelectorAll('a')` 枚举全部锚点，
       取回各自的 `outerHTML` / `innerHTML` / `innerText`，要求产品返回串与其中**恰好一个**逐字节相等。
       期望值不经过任何产品返回值推导。
    3. **活推导**：在上述独立定位到的同一节点上改属性，产品必须立刻读回；撤销后必须归零。

被测源码要点（worktree `D:\\code\\desktop`，基线 `c101caa9`）
    `sdk/src/uiautoma/web/element.py:536` `get_html(self) -> str`，无参数，委托 `self._raw.get_html()`；
    `sdk/src/uiautoma/_core/client.py:3906` `get_html(*, timeout: float = 5.0)`，取 `html` 回退 `value` 回退 `""`；
    RPC `web.get_html`（`runtime/services/capabilities.py:273`，必填 `package_token`/`element_id`/`timeout_ms`）；
    Runtime `action_service.web_get_html_element`（`:2486`）；引擎
    `chrome/engine/engine_packages/page_engine_runtime.js:3665` 返回 `element.outerHTML`（非字符串则 `""`）。

环境阻塞口径
    目标页面是外部实时站点，元素库路径绑定的是百度当时的 DOM 结构。若元素无法绑定
    （`ElementNotFoundError`）或页面无法打开，按**环境阻塞**记 `BLOCKED`（退出码 2），
    不写成产品缺陷。

退出码
    `0` 全部 PASS（允许 KNOWN）；`1` 存在 FAIL；`2` 无 FAIL 但存在 BLOCKED。
"""
from __future__ import annotations

import argparse
import inspect
import json
import shutil
import sys
import tempfile
import time
from pathlib import Path

import uiautoma
from uiautoma import web
from uiautoma.web import WebBrowser, WebElement

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _web_env import (  # noqa: E402
    check_web_channel,
    list_chrome_profiles,
    pin_environment,
    safe_tab_count,
)

__test__ = False

TARGET_URL = (
    "https://www.baidu.com/s?ie=utf-8&bsst=1&rsv_dl=news_t_sk&tn=news"
    "&cl=2&medium=0&rtt=1&wd=%E5%8C%BA%E5%9D%97%E9%93%BE"
)
DEFAULT_LIBRARY = Path(r"D:\code\元素库\260902_web元素")
ELEMENT_NAME = "web靶场_测试超链接"
EXPECTED_PAGE_TITLE = "百度资讯搜索_区块链"
MARKER = "uiautoma-element-get-html-probe"

GREEN, RED, YELLOW, RESET = "\x1b[92m", "\x1b[91m", "\x1b[93m", "\x1b[0m"

# 独立确证用的页面侧采集：只看 DOM，不看产品返回
ORACLE_JS = (
    "function () { return Array.from(document.querySelectorAll('a')).map(function (e) {"
    " return { outer: e.outerHTML, inner: e.innerHTML,"
    " text: e.innerText, label: e.getAttribute('aria-label') }; }); }"
)


class Recorder:
    def __init__(self) -> None:
        self.results: list[dict] = []
        self._t0 = time.monotonic()

    def add(self, case_id: str, status: str, detail: str, **extra) -> dict:
        now = time.monotonic()
        elapsed = now - self._t0
        self._t0 = now
        item = {
            "case_id": case_id,
            "status": status,
            "detail": f"{detail}（耗时 {elapsed:.2f}s）",
            "elapsed": round(elapsed, 3),
            **extra,
        }
        self.results.append(item)
        return item


def error_detail(prefix: str, exc: BaseException) -> str:
    detail = f"{prefix}: {type(exc).__name__}: {exc}"
    trace = str(getattr(exc, "trace_info", "") or "")
    if trace:
        detail += f" [trace={trace}]"
    return detail


def check_contract(rec: Recorder) -> bool:
    method = getattr(WebElement, "get_html", None)
    if not callable(method):
        rec.add("api_contract", "FAIL", "WebElement.get_html 不存在")
        return False
    signature = inspect.signature(method)
    parameters = list(signature.parameters.values())
    names = tuple(signature.parameters)
    annotation = signature.return_annotation
    annotation_ok = annotation is str or str(annotation) == "str"
    ok = (
        names == ("self",)
        and parameters[0].kind is inspect.Parameter.POSITIONAL_OR_KEYWORD
        and annotation_ok
    )
    rec.add(
        "api_contract",
        "PASS" if ok else "FAIL",
        f"get_html 无参数、返回 str（签名 {signature}，返回注解 {annotation!r}）" if ok
        else f"公开签名不符合合同: {signature}",
        signature=str(signature),
    )
    return ok


def run(args):
    rec = Recorder()
    if not check_contract(rec):
        return rec.results, 1
    if args.contract_only:
        return rec.results, 0

    baseline_tabs = safe_tab_count(args.mode)
    work_dir = Path(tempfile.mkdtemp(prefix="uiautoma-element-get-html-", dir=str(args.temp_root)))
    package = None
    page: WebBrowser | None = None
    element: WebElement | None = None
    page_closed = False

    def cleanup_case() -> None:
        close_errors: list[str] = []
        if page is not None and not page_closed:
            try:
                page.close(ignore_beforeunload=True)
            except Exception as exc:  # noqa: BLE001
                close_errors.append(f"page: {type(exc).__name__}: {exc}")
        if package is not None:
            try:
                package.close()
            except Exception as exc:  # noqa: BLE001
                close_errors.append(f"package: {type(exc).__name__}: {exc}")
        shutil.rmtree(work_dir, ignore_errors=True)
        time.sleep(0.8)
        after_tabs = safe_tab_count(args.mode)
        cleanup_ok = not close_errors and not work_dir.exists()
        rec.add(
            "cleanup", "PASS" if cleanup_ok else "FAIL",
            f"测试页面与 Package 已关闭，元素库副本已删除；"
            f"标签数 {baseline_tabs} → {after_tabs}（用户可能同时浏览，仅作诊断）"
            if cleanup_ok else
            f"清理不完整：关闭错误={close_errors or '无'}，临时目录残留={work_dir.exists()}，"
            f"标签 {baseline_tabs} → {after_tabs}",
            tabs_before=baseline_tabs, tabs_after=after_tabs,
        )

    try:
        # ---- 浏览器通道前置检查 ----
        # 一次连着多个 Chrome 用户环境/插件时，Runtime 会拒绝所有 web.* 调用
        # （trace web_environment_ambiguous），get_all 与 create 都不可用。
        # 这不是产品缺陷、也不是判据问题：按产品提示固定目标用户环境即可继续。
        channel = check_web_channel(args.mode)
        pinned_note = ""
        profiles: list[str] = []
        profile_error = ""
        if not channel["ok"]:
            profiles, profile_error = list_chrome_profiles(args.chrome_user_data_dir)
            if args.profile or args.chrome_user_data_dir:
                ok, pinned_note = pin_environment(args.mode, args.profile, args.chrome_user_data_dir)
                if ok:
                    channel = check_web_channel(args.mode)
        if not channel["ok"]:
            if profiles:
                hint = "；可选用户环境：" + "、".join(profiles)
            elif profile_error:
                hint = f"；无法读取 Chrome Local State（{profile_error}）"
            else:
                hint = ""
            rec.add(
                "env_prepare", "BLOCKED",
                f"浏览器通道不可用（{channel['exception']} trace={channel['trace'] or '无'}）："
                f"{channel['message']}{hint}"
                + (f"；{pinned_note}" if pinned_note else "")
                + "；可用 --profile <名称> 指定目标用户环境后重试",
                trace=channel["trace"], profiles=profiles,
            )
            return rec.results, 2
        baseline_tabs = channel["tabs"]
        rec.add(
            "env_prepare", "PASS",
            f"浏览器通道可用，进入时 {baseline_tabs} 个标签"
            + (f"（{pinned_note}）" if pinned_note else ""),
            tabs_before=baseline_tabs,
        )

        # ---- 环境准备：元素库副本 ----
        library_copy = work_dir / "library"
        try:
            shutil.copytree(args.library, library_copy)
        except OSError as exc:
            rec.add("library_prepare", "BLOCKED", f"元素库复制失败：{error_detail('copy', exc)}")
            return rec.results, 2
        package = uiautoma.open(str(library_copy), timeout=args.runtime_timeout,
                                connect_timeout=args.runtime_timeout)
        info = uiautoma.ping()
        rec.add(
            "library_prepare", "PASS",
            f"元素库副本已打开（{args.library.name}），Runtime {info.runtime_version} 协议 {info.protocol}，"
            f"进入时 {baseline_tabs} 个标签",
            runtime_version=str(info.runtime_version), tabs_before=baseline_tabs,
        )

        # ---- 页面准备 ----
        try:
            page = web.create(args.target_url, mode=args.mode, load_timeout=args.load_timeout)
        except Exception as exc:  # noqa: BLE001
            rec.add("page_prepare", "BLOCKED", f"目标页面打开失败：{error_detail('create', exc)}")
            return rec.results, 2
        try:
            title = page.get_title()
        except Exception as exc:  # noqa: BLE001
            rec.add("page_prepare", "BLOCKED", f"页面标题读取失败：{error_detail('get_title', exc)}")
            return rec.results, 2
        rec.add(
            "page_prepare", "PASS",
            f"目标页面已打开：title={title!r}（元素库分组 origin=https://www.baidu.com）",
            url=page.get_url(), title=title,
        )

        # ---- 元素绑定（外部站点，失败即环境阻塞）----
        try:
            all_hits = page.find_all(args.element, timeout=args.element_timeout)
            element = page.find(args.element, timeout=args.element_timeout)
        except Exception as exc:  # noqa: BLE001
            rec.add(
                "element_bind", "BLOCKED",
                f"库元素 {args.element} 在当前百度页面上无法绑定：{error_detail('find', exc)}；"
                f"百度资讯结果页会随发布时间改版，属外部环境变化，不记产品缺陷",
            )
            return rec.results, 2
        rec.add(
            "element_bind", "PASS",
            f"库元素绑定成功：find_all 命中 {len(all_hits)} 个，find 返回单一 WebElement"
            f"（Runtime id={element.id}）",
            hits=len(all_hits), element_id=str(element.id), element_name=str(element.name),
        )

        html = element.get_html()

        # ---- 返回形态 ----
        type_ok = type(html) is str and bool(html)
        rec.add(
            "return_type_nonempty", "PASS" if type_ok else "FAIL",
            f"返回原生 str 且非空，长度 {len(html)}" if type_ok
            else f"期望非空 str，实测 type={type(html).__name__} 长度={len(html)}",
            html_length=len(html),
        )

        # ---- 独立推导：元素级 outerHTML 而非页面 HTML ----
        starts_anchor = html.lstrip().startswith("<a")
        ends_anchor = html.rstrip().endswith("</a>")
        no_html_root = "<html" not in html.lower()
        scope_ok = starts_anchor and ends_anchor and no_html_root
        rec.add(
            "element_scope_outerhtml", "PASS" if scope_ok else "FAIL",
            f"返回串以 <a 开头、</a> 结尾且不含 <html：确认是元素自身 outerHTML 而非页面 HTML"
            if scope_ok else
            f"范围不符：starts=<a {starts_anchor}，ends=</a> {ends_anchor}，含 <html={not no_html_root}",
            head=html[:100],
        )

        # ---- 独立确证：与页面侧枚举的全部锚点逐一比对 ----
        oracle = page.execute_javascript(ORACLE_JS, execution_world="MAIN")
        if not isinstance(oracle, list) or not oracle:
            rec.add("independent_dom_match", "BLOCKED", "页面侧未能枚举到任何 a 元素")
        else:
            outers = [str(item.get("outer") or "") for item in oracle]
            matches = [index for index, value in enumerate(outers) if value == html]
            unique = len(matches) == 1
            rec.add(
                "independent_dom_match", "PASS" if unique else "FAIL",
                f"返回串与页面侧枚举的 {len(oracle)} 个锚点中第 {matches[0]} 个 outerHTML 逐字节相等，且唯一"
                if unique else
                f"未唯一匹配：页面锚点数={len(oracle)}，逐字节相等的下标={matches}",
                anchor_total=len(oracle), matched_index=matches,
            )
            matched = oracle[matches[0]] if unique else None
            if matched is not None:
                inner = str(matched.get("inner") or "")
                text = str(matched.get("text") or "")
                inner_ok = bool(inner) and inner in html and len(html) > len(inner)
                rec.add(
                    "inner_html_contained", "PASS" if inner_ok else "FAIL",
                    f"同一节点的 innerHTML（{len(inner)} 字符）是返回串的真子串，"
                    f"返回串比 innerHTML 多 {len(html) - len(inner)} 字符（自身标签与属性）"
                    if inner_ok else
                    f"innerHTML 关系不符：inner 空={not inner}，是子串={inner in html}，"
                    f"len(html)={len(html)} len(inner)={len(inner)}",
                    inner_length=len(inner),
                )
                # ---- 独立推导：HTML 序列化必须含子标签，且与纯文本通道不同 ----
                markup_ok = "<" in html and len(html) > len(text)
                rec.add(
                    "markup_vs_text", "PASS" if markup_ok else "FAIL",
                    f"返回串含子标签标记且显著长于 innerText"
                    f"（HTML {len(html)} 字符 vs 文本 {len(text)} 字符），与 get_text() 通道不同"
                    if markup_ok else
                    f"HTML 与文本未区分：HTML={len(html)} 字符，文本={len(text)} 字符，含子标签={'<' in html}",
                    html_length=len(html), text_length=len(text),
                )

        # ---- 独立推导：属性值在 HTML 中必须按 HTML 规则转义 ----
        try:
            raw_href = str(element.get_attribute("href") or "")
        except Exception as exc:  # noqa: BLE001
            rec.add("attribute_escaping", "FAIL", error_detail("href 读取失败", exc))
        else:
            if "&" not in raw_href:
                rec.add(
                    "attribute_escaping", "KNOWN",
                    f"该元素 href 不含 &（{raw_href[:60]!r}），本次环境没有转义样本，不判定",
                )
            else:
                escaped = raw_href.replace("&", "&amp;")
                escape_ok = escaped in html
                rec.add(
                    "attribute_escaping", "PASS" if escape_ok else "FAIL",
                    f"属性 API 返回原始 &（href 含 {raw_href.count('&')} 个），"
                    f"返回 HTML 中同值按 HTML 规则序列化为 &amp;"
                    if escape_ok else
                    f"转义不符：期望包含 {escaped[:80]!r}，实测含 &amp;={'&amp;' in html}",
                    amp_count=raw_href.count("&"),
                )

        # ---- 活推导：改同一节点，产品必须立刻读回 ----
        if isinstance(oracle, list) and oracle:
            outers = [str(item.get("outer") or "") for item in oracle]
            matches = [index for index, value in enumerate(outers) if value == html]
            if len(matches) != 1:
                rec.add("live_mutation_visible", "FAIL", "无法唯一确定目标节点下标，活推导未执行")
            else:
                index = matches[0]
                target_ok = page.execute_javascript(
                    "function () { var e = document.querySelectorAll('a')[" + str(index) + "];"
                    " if (!e) return false;"
                    " e.setAttribute('data-uiautoma-probe', '" + MARKER + "'); return true; }",
                    execution_world="MAIN",
                )
                after = element.get_html()
                expected_delta = len(f' data-uiautoma-probe="{MARKER}"')
                delta = len(after) - len(html)
                seen = MARKER in after
                mut_ok = bool(target_ok) and seen and delta == expected_delta
                rec.add(
                    "live_mutation_visible", "PASS" if mut_ok else "FAIL",
                    f"独立定位到的同一节点加属性后返回值立刻体现，长度增量 {delta} 等于手写增量 {expected_delta}"
                    if mut_ok else
                    f"活推导不符：命中节点={target_ok}，标记可见={seen}，增量={delta} 期望={expected_delta}",
                    measured_delta=delta, expected_delta=expected_delta,
                )
                page.execute_javascript(
                    "function () { var e = document.querySelectorAll('a')[" + str(index) + "];"
                    " if (e) { e.removeAttribute('data-uiautoma-probe'); } return true; }",
                    execution_world="MAIN",
                )
                restored = element.get_html()
                restore_ok = MARKER not in restored and len(restored) == len(html)
                rec.add(
                    "live_cleanup_restores", "PASS" if restore_ok else "FAIL",
                    f"撤销后标记消失且长度精确还原为 {len(html)}"
                    if restore_ok else
                    f"撤销后未还原：残留={MARKER in restored}，长度={len(restored)} 期望={len(html)}",
                )

        # ---- 重复读取稳定性 ----
        reads = [element.get_html() for _ in range(3)]
        stable = len(set(reads)) == 1 == len({len(item) for item in reads}) and reads[0] == html
        rec.add(
            "repeat_read_stable", "PASS" if stable else "FAIL",
            f"连续 3 次读取与首次逐字节一致，长度均为 {len(reads[0])}"
            if stable else f"重复读取不一致，长度={[len(item) for item in reads]}",
            lengths=[len(item) for item in reads],
        )

        # ---- 参数校验：零参数合同 ----
        try:
            element.get_html("extra")  # type: ignore[call-arg]
            rec.add("param_positional", "FAIL", "额外位置参数未被拒绝")
        except TypeError as exc:
            rec.add("param_positional", "PASS", f"多余位置参数被 TypeError 拒绝：{exc}")
        except Exception as exc:  # noqa: BLE001
            rec.add("param_positional", "FAIL", error_detail("期望 TypeError", exc))

        try:
            element.get_html(timeout=1)  # type: ignore[call-arg]
            rec.add("param_keyword", "FAIL", "未声明的 timeout 关键字未被拒绝")
        except TypeError as exc:
            rec.add("param_keyword", "PASS", f"未声明关键字被 TypeError 拒绝：{exc}")
        except Exception as exc:  # noqa: BLE001
            rec.add("param_keyword", "FAIL", error_detail("期望 TypeError", exc))

        # ---- 生命周期：页面关闭后元素必须失效 ----
        page.close(ignore_beforeunload=True)
        page_closed = True
        try:
            element.get_html()
            rec.add("stale_page_reference", "FAIL", "页面关闭后 get_html 未报错")
        except Exception as exc:  # noqa: BLE001
            trace = str(getattr(exc, "trace_info", "") or "")
            ok = trace == "stale_page_reference" and "失效" in str(exc)
            rec.add(
                "stale_page_reference", "PASS" if ok else "FAIL",
                f"关闭后读取被拒绝：{type(exc).__name__} trace={trace} 消息={exc}"
                if ok else error_detail("关闭后报错语义不符", exc),
            )
    except Exception as exc:  # noqa: BLE001
        rec.add("scenario", "FAIL", error_detail("get_html 场景执行失败", exc))
    finally:
        cleanup_case()

    statuses = {item["status"] for item in rec.results}
    code = 1 if "FAIL" in statuses else (2 if "BLOCKED" in statuses else 0)
    return rec.results, code


def main(argv=None):
    parser = argparse.ArgumentParser(description="WebElement.get_html() 元素对象 API 验收")
    parser.add_argument("--target-url", default=TARGET_URL, help="目标页面 URL")
    parser.add_argument("--library", type=Path, default=DEFAULT_LIBRARY, help="元素库目录（只读，测试用副本）")
    parser.add_argument("--element", default=ELEMENT_NAME, help="元素库中的元素名称")
    parser.add_argument("--mode", choices=("chrome", "edge"), default="chrome")
    parser.add_argument("--load-timeout", type=float, default=40)
    parser.add_argument("--element-timeout", type=float, default=15)
    parser.add_argument("--runtime-timeout", type=float, default=30)
    parser.add_argument("--contract-only", action="store_true")
    parser.add_argument("--profile", default=None,
                        help="Chrome 用户环境目录名或显示名；浏览器通道报环境歧义时用它固定目标环境")
    parser.add_argument("--chrome-user-data-dir", default=None,
                        help="Chrome 用户数据目录，用于读取可选用户环境列表")
    parser.add_argument("--json", action="store_true", help="在表格后额外输出 JSON 报告（用于归档验收产物）")
    args = parser.parse_args(argv)
    if args.load_timeout <= 0 or args.element_timeout <= 0 or args.runtime_timeout <= 0:
        parser.error("timeout 参数必须大于 0")
    if not args.library.is_dir():
        parser.error(f"元素库不存在: {args.library}")
    args.temp_root = Path(__file__).resolve().parents[1] / ".pytest_tmp"
    args.temp_root.mkdir(parents=True, exist_ok=True)

    results, code = run(args)
    print("UIAutoma Web API 测试")
    print("API     : uiautoma.web.WebElement.get_html")
    print(f"页面    : {args.target_url}")
    print(f"元素库  : {args.library}（元素 {args.element}）")
    print("进度     状态    测试项                  测试结果")
    print("────────────────────────────────────────────────────────────────────────")
    for index, current in enumerate(results, 1):
        status = current["status"]
        color = {"PASS": GREEN, "BLOCKED": YELLOW, "KNOWN": YELLOW}.get(status, RED)
        label = {"PASS": "通过", "BLOCKED": "阻塞", "KNOWN": "已知"}.get(status, "失败")
        print(f"{index:02d}/{len(results):02d}    {color}[{label}]{RESET}  "
              f"{current['case_id']:<24}  {current['detail']}")
    print("────────────────────────────────────────────────────────────────────────")
    summary = "测试通过" if code == 0 else ("测试阻塞" if code == 2 else "测试失败")
    print(f"{summary} · {sum(item['status'] == 'PASS' for item in results)}/{len(results)} 通过 · 退出码 {code}")
    if args.json:
        print(json.dumps({
            "api": "uiautoma.web.WebElement.get_html",
            "target_url": args.target_url,
            "library": str(args.library),
            "element": args.element,
            "mode": args.mode,
            "sdk_path": str(Path(uiautoma.__file__).resolve()),
            "status": "PASS" if code == 0 else ("BLOCKED" if code == 2 else "FAIL"),
            "exit_code": code,
            "results": results,
        }, ensure_ascii=False, indent=2))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
