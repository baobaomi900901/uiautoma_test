"""`WebBrowser.get_html()` 验收脚本。

靶场/页面
    `https://baobaomi900901.github.io/xpath/#/element-html-test`（元素 HTML 测试页，固定 id
    由 `WEB/src/pages/ElementHtmlTestPage.tsx` 与 `WEB/src/App.tsx` 独立推导）；
    `#/iframe-shadow-form` 用于验证「只读主框架」；`chrome://newtab/` 用于验证非脚本化页面。

期望值来源
    1. 独立推导：靶场源码里写死的固定 id、`outerHTML` 不含 DOCTYPE 的 DOM 规范语义、
       手写注入片段的字符长度。
    2. 活推导：用 `execute_javascript`（CDP 通道）制造已知 DOM 状态，再用 `get_html`
       （`chrome.scripting` 通道）读回。
    3. 独立确证：Python 标准库 `html.parser` 解析返回串，与浏览器实时
       `document.getElementsByTagName('*').length` 和 id 集合对照。

被测源码要点（worktree `D:\\code\\desktop`，基线 `c101caa9`）
    `sdk/src/uiautoma/web/browser.py:95` `get_html(self) -> str` 无参数，
    取 RPC 结果的 `html`，回退 `value`，再回退空串；
    RPC `web.browser.get_html`（`sdk/src/uiautoma/_core/client.py:1248`）；
    Runtime `runtime/services/action_service.py:2891` → `_run_web_browser_command(command="get_html")`
    （`page_ref` 失效返回 `stale_page_reference`）；引擎
    `chrome/engine/plugin_packages/browser_command_package.js:537,1619` 用
    `chrome.scripting.executeScript` 在 `frameIds:[0]` 读 `document.documentElement.outerHTML`。

实测抖动口径
    空闲态连续读取精确稳定（12/12 长度相同）。靶场页的 antd cssinjs `<style>` 会在页面自身
    节奏下增删，实测总长可漂移 2 字符；因此长度类断言使用 `LENGTH_JITTER_BUDGET`，且只作为
    辅助判据，主判据是内容级（探针标记、固定 id、元素计数）。

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
from html.parser import HTMLParser
from pathlib import Path

import uiautoma
from uiautoma import web
from uiautoma.web import WebBrowser

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _web_page_identity import tab_count  # noqa: E402

__test__ = False

BASE_URL = "https://baobaomi900901.github.io/xpath/"
FIXTURE_URL = BASE_URL + "#/element-html-test"
FRAME_URL = BASE_URL + "#/iframe-shadow-form"
UNSUPPORTED_URL = "chrome://newtab/"

# 由 ElementHtmlTestPage.tsx 与 index.html 独立推导的固定 id
AUTHORED_IDS = (
    "root",
    "element-html-input",
    "element-html-apply",
    "element-html-reset",
    "element-html-target",
    "element-html-result",
)
LIVE_MARKER = "uiautoma-get-html-live-probe"
PROBE_NODE_ID = "uiautoma-probe-node"
IFRAME_INNER_ID = "form-shadow-host"

# 实测抖动预算（字符）：详见模块 docstring「实测抖动口径」。
# 相对 11.7 万字符的文档为 0.007%，小到不足以掩盖缺 DOCTYPE（约 15 字符）、
# 少包裹元素或读错帧这类系统性偏差。
LENGTH_JITTER_BUDGET = 8

GREEN, RED, YELLOW, RESET = "\x1b[92m", "\x1b[91m", "\x1b[93m", "\x1b[0m"


class ElementCounter(HTMLParser):
    """用标准库独立统计返回串中的元素与 id。"""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=False)
        self.count = 0
        self.ids: list[str] = []

    def _bump(self, attrs) -> None:
        self.count += 1
        for key, value in attrs:
            if key == "id" and value:
                self.ids.append(value)

    def handle_starttag(self, tag, attrs) -> None:
        self._bump(attrs)

    def handle_startendtag(self, tag, attrs) -> None:
        self._bump(attrs)


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
    method = getattr(WebBrowser, "get_html", None)
    if not callable(method):
        rec.add("api_contract", "FAIL", "WebBrowser.get_html 不存在")
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


def live_probe(page: WebBrowser) -> dict:
    """一次 CDP 往返取实时 DOM 事实，作为 get_html 的独立对照。"""
    return page.execute_javascript(
        "function () { return {"
        " count: document.getElementsByTagName('*').length,"
        " ids: Array.from(document.querySelectorAll('[id]')).map(function (e) { return e.id; }),"
        " outer: document.documentElement.outerHTML,"
        " doctype: document.doctype ? document.doctype.name : null"
        "}; }",
        execution_world="MAIN",
    )


def wait_frame_host(page: WebBrowser, *, timeout: float = 20) -> dict:
    """等待 iframe 文档就绪并回报 iframe 内部结构（只读）。"""
    deadline = time.monotonic() + timeout
    last: object = "未执行"
    while True:
        last = page.execute_javascript(
            "function () { var f = document.getElementById('iframe-shadow-form');"
            " if (!f) return { stage: 'no_iframe' };"
            " var d = f.contentDocument;"
            " if (!d) return { stage: 'no_document' };"
            " if (d.readyState !== 'complete') return { stage: 'loading' };"
            " var host = d.getElementById('" + IFRAME_INNER_ID + "');"
            " if (!host) return { stage: 'no_host' };"
            " return { stage: 'ok', innerLen: d.documentElement.outerHTML.length,"
            "  innerHasHost: d.documentElement.outerHTML.indexOf('" + IFRAME_INNER_ID + "') >= 0,"
            "  shadowChildren: host.shadowRoot ? host.shadowRoot.childElementCount : -1 }; }",
            execution_world="MAIN",
        )
        if isinstance(last, dict) and last.get("stage") == "ok":
            return last
        if time.monotonic() >= deadline:
            return last if isinstance(last, dict) else {"stage": str(last)}


def run(args):
    rec = Recorder()
    if not check_contract(rec):
        return rec.results, 1
    if args.contract_only:
        return rec.results, 0

    baseline_tabs = tab_count(args.mode)
    created: list[tuple[str, WebBrowser]] = []
    closed: set[str] = set()
    work_dir = Path(tempfile.mkdtemp(prefix="uiautoma-get-html-", dir=str(args.temp_root)))

    def track(name: str, page: WebBrowser) -> WebBrowser:
        created.append((name, page))
        return page

    def close_tracked(name: str) -> str:
        """关闭一次并返回错误文本（空串表示成功）。"""
        if name in closed:
            return ""
        closed.add(name)
        page = dict(created)[name]
        try:
            page.close(ignore_beforeunload=True)
            return ""
        except Exception as exc:  # noqa: BLE001
            return f"{name}: {type(exc).__name__}: {exc}"

    fixture: WebBrowser | None = None
    frame: WebBrowser | None = None

    try:
        info = uiautoma.ping()
        rec.add(
            "env_baseline", "PASS",
            f"Runtime {info.runtime_version} 协议 {info.protocol}，进入时 {baseline_tabs} 个标签",
            runtime_version=str(info.runtime_version), tabs_before=baseline_tabs,
        )

        # ---- 准备：靶场 fixture ----
        fixture = track("fixture", web.create(FIXTURE_URL, mode=args.mode, load_timeout=args.load_timeout))
        if not isinstance(fixture, WebBrowser):
            rec.add("page_prepare", "FAIL", f"web.create 未返回 WebBrowser: {type(fixture).__name__}")
            return rec.results, 1
        url = fixture.get_url()
        title = fixture.get_title()
        prepared = url.rstrip("/").endswith("#/element-html-test") and title == "元素 HTML 测试"
        rec.add(
            "page_prepare", "PASS" if prepared else "FAIL",
            f"靶场页已打开：url={url!r}，title={title!r}（源码推导标题应为 '元素 HTML 测试'）"
            if prepared else f"靶场页不符：url={url!r}，title={title!r}",
            url=url, title=title,
        )
        if not prepared:
            return rec.results, 1

        html = fixture.get_html()

        # ---- 返回形态 ----
        type_ok = type(html) is str and bool(html)
        rec.add(
            "return_type_nonempty", "PASS" if type_ok else "FAIL",
            f"返回原生 str 且非空，长度 {len(html)}" if type_ok
            else f"期望非空 str，实测 type={type(html).__name__} 长度={len(html)}",
            html_length=len(html),
        )

        # ---- 独立确证：与实时 DOM 对照，并核对 DOCTYPE 语义 ----
        dom = live_probe(fixture)
        same_outer = html == str(dom.get("outer") or "")
        no_doctype = not html.lstrip().lower().startswith("<!doctype")
        dom_has_doctype = dom.get("doctype") == "html"
        outer_ok = same_outer and no_doctype and dom_has_doctype
        rec.add(
            "outerhtml_semantics", "PASS" if outer_ok else "FAIL",
            f"与实时 documentElement.outerHTML 逐字节相等，且不含 DOCTYPE"
            f"（实时 doctype={dom.get('doctype')!r}，长度 delta={len(html) - len(str(dom.get('outer') or ''))}）"
            if outer_ok else
            f"outerHTML 语义不符：相等={same_outer}，无 DOCTYPE={no_doctype}，实时 doctype={dom.get('doctype')!r}",
            equals_outer=same_outer, no_doctype=no_doctype, dom_doctype=dom.get("doctype"),
        )

        # ---- 独立推导：靶场源码固定 id ----
        missing = [item for item in AUTHORED_IDS if f'id="{item}"' not in html]
        rec.add(
            "authored_ids_present", "PASS" if not missing else "FAIL",
            f"靶场源码写死的 {len(AUTHORED_IDS)} 个固定 id 全部出现在返回串中"
            if not missing else f"缺失固定 id: {missing}",
            missing=missing,
        )

        # ---- 独立确证：标准库解析 vs 浏览器实时 DOM ----
        parser = ElementCounter()
        parser.feed(html)
        live_count = int(dom.get("count") or 0)
        live_ids = [str(item) for item in (dom.get("ids") or [])]
        only_live = sorted(set(live_ids) - set(parser.ids))
        only_parsed = sorted(set(parser.ids) - set(live_ids))
        parse_ok = parser.count == live_count and not only_live and not only_parsed
        rec.add(
            "independent_parse", "PASS" if parse_ok else "FAIL",
            f"标准库解析得 {parser.count} 个元素，浏览器实时 DOM 为 {live_count} 个，id 集合完全一致"
            if parse_ok else
            f"解析与 DOM 不一致：解析={parser.count} 实时={live_count}，仅实时有={only_live}，仅解析有={only_parsed}",
            parsed_count=parser.count, live_count=live_count,
        )

        # ---- 重复读取稳定性（任何 DOM 变更之前：空闲态）----
        reads = [fixture.get_html() for _ in range(4)]
        stable = len(set(reads)) == 1
        rec.add(
            "repeat_read_stable", "PASS" if stable else "FAIL",
            f"空闲态连续 4 次逐字节一致，长度均为 {len(reads[0])}"
            if stable else f"空闲态连续读取不一致，长度={[len(item) for item in reads]}",
            lengths=[len(item) for item in reads],
        )

        # ---- 活推导：CDP 制造 DOM 变更，get_html 必须读回 ----
        reference = fixture.get_html()
        attribute = f' data-uiautoma-probe="{LIVE_MARKER}"'
        node_html = f'<div id="{PROBE_NODE_ID}">{LIVE_MARKER}-node</div>'
        expected_delta = len(attribute) + len(node_html)
        fixture.execute_javascript(
            "function () { document.documentElement.setAttribute('data-uiautoma-probe', '"
            + LIVE_MARKER + "'); var d = document.createElement('div');"
            " d.id = '" + PROBE_NODE_ID + "'; d.textContent = '"
            + LIVE_MARKER + "-node'; document.body.appendChild(d); return 1; }",
            execution_world="MAIN",
        )
        mutated = fixture.get_html()
        measured_delta = len(mutated) - len(reference)
        attr_seen = LIVE_MARKER in mutated
        node_seen = f"{LIVE_MARKER}-node" in mutated
        delta_ok = abs(measured_delta - expected_delta) <= LENGTH_JITTER_BUDGET
        mut_ok = attr_seen and node_seen and delta_ok
        rec.add(
            "live_mutation_visible", "PASS" if mut_ok else "FAIL",
            f"新增属性与节点均被读回，长度增量 {measured_delta} 与手写增量 {expected_delta} 之差"
            f"在抖动预算 ±{LENGTH_JITTER_BUDGET} 内"
            if mut_ok else
            f"DOM 变更未被正确读回：属性={attr_seen} 节点={node_seen}，"
            f"实测增量={measured_delta} 期望={expected_delta}（预算 ±{LENGTH_JITTER_BUDGET}）",
            expected_delta=expected_delta, measured_delta=measured_delta,
        )

        # ---- 活推导：撤销变更后必须还原（内容级为主，长度为辅）----
        fixture.execute_javascript(
            "function () { document.documentElement.removeAttribute('data-uiautoma-probe');"
            " var n = document.getElementById('" + PROBE_NODE_ID + "');"
            " if (n) { n.remove(); } return 1; }",
            execution_world="MAIN",
        )
        restored = fixture.get_html()
        restored_dom = live_probe(fixture)
        restored_parser = ElementCounter()
        restored_parser.feed(restored)
        marker_gone = LIVE_MARKER not in restored and PROBE_NODE_ID not in restored
        ids_missing = [item for item in AUTHORED_IDS if f'id="{item}"' not in restored]
        count_intact = restored_parser.count == int(restored_dom.get("count") or 0)
        length_delta = len(restored) - len(reference)
        restore_ok = (
            marker_gone
            and not ids_missing
            and count_intact
            and abs(length_delta) <= LENGTH_JITTER_BUDGET
        )
        rec.add(
            "live_cleanup_restores", "PASS" if restore_ok else "FAIL",
            f"撤销后探针属性与节点均消失，固定 id 与元素计数（{restored_parser.count}）不变，"
            f"长度偏差 {length_delta} 在抖动预算 ±{LENGTH_JITTER_BUDGET} 内"
            if restore_ok else
            f"撤销后未还原：标记残留={not marker_gone}，缺失 id={ids_missing}，"
            f"计数一致={count_intact}，长度偏差={length_delta}（预算 ±{LENGTH_JITTER_BUDGET}）",
            length_delta=length_delta, marker_gone=marker_gone, ids_missing=ids_missing,
        )

        # ---- 参数校验：零参数合同 ----
        try:
            fixture.get_html("extra")  # type: ignore[call-arg]
            rec.add("param_positional", "FAIL", "额外位置参数未被拒绝")
        except TypeError as exc:
            rec.add("param_positional", "PASS", f"多余位置参数被 TypeError 拒绝：{exc}")
        except Exception as exc:  # noqa: BLE001
            rec.add("param_positional", "FAIL", error_detail("期望 TypeError", exc))

        try:
            fixture.get_html(timeout=1)  # type: ignore[call-arg]
            rec.add("param_keyword", "FAIL", "未声明的 timeout 关键字未被拒绝")
        except TypeError as exc:
            rec.add("param_keyword", "PASS", f"未声明关键字被 TypeError 拒绝：{exc}")
        except Exception as exc:  # noqa: BLE001
            rec.add("param_keyword", "FAIL", error_detail("期望 TypeError", exc))

        # ---- 静默（后台）标签页同样可读 ----
        silent = track(
            "silent",
            web.create(FIXTURE_URL, mode=args.mode, load_timeout=args.load_timeout, silent_running=True),
        )
        silent_html = silent.get_html()
        silent_ok = type(silent_html) is str and "element-html-target" in silent_html
        rec.add(
            "silent_background_read", "PASS" if silent_ok else "FAIL",
            f"silent_running=True 的后台标签页可读，长度 {len(silent_html)}"
            if silent_ok else f"后台标签页读取异常：type={type(silent_html).__name__} 长度={len(silent_html)}",
        )

        # ---- 帧作用域：只读主框架 ----
        frame = track("frame", web.create(FRAME_URL, mode=args.mode, load_timeout=args.load_timeout))
        frame_html = frame.get_html()
        frame_info = wait_frame_host(frame, timeout=args.load_timeout + 10)
        main_has_iframe = 'id="iframe-shadow-form"' in frame_html
        main_has_inner = IFRAME_INNER_ID in frame_html
        inner_ok = (
            isinstance(frame_info, dict)
            and frame_info.get("stage") == "ok"
            and bool(frame_info.get("innerHasHost"))
        )
        frame_ok = main_has_iframe and not main_has_inner and inner_ok
        rec.add(
            "iframe_frame_scope", "PASS" if frame_ok else "FAIL",
            f"主文档返回串含 iframe 元素但不含 iframe 内部 id {IFRAME_INNER_ID}；"
            f"iframe 文档自身确有该 id（stage={frame_info.get('stage')}，shadow 子节点 "
            f"{frame_info.get('shadowChildren')} 个）"
            if frame_ok else
            f"帧作用域不符：主文档有 iframe={main_has_iframe} 含内部 id={main_has_inner}，"
            f"iframe 内部 stage={frame_info.get('stage') if isinstance(frame_info, dict) else frame_info}",
            stage=frame_info.get("stage") if isinstance(frame_info, dict) else None,
            inner_has_host=frame_info.get("innerHasHost") if isinstance(frame_info, dict) else None,
        )

        # ---- 边界：非脚本化真实浏览器页返回明确能力错误 ----
        scratch: WebBrowser | None = None
        for candidate in web.get_all(mode=args.mode):
            if (candidate.get_url() or "").startswith(UNSUPPORTED_URL):
                scratch = candidate
                break
        owned_scratch = False
        if scratch is None:
            try:
                scratch = track(
                    "scratch",
                    web.create(UNSUPPORTED_URL, mode=args.mode, load_timeout=args.load_timeout),
                )
                owned_scratch = True
            except Exception as exc:  # noqa: BLE001
                rec.add(
                    "unsupported_url", "BLOCKED",
                    f"既无 chrome://newtab/ 标签也未能创建：{error_detail('create 失败', exc)}",
                )
                scratch = None
        if scratch is not None:
            try:
                value = scratch.get_html()
                rec.add(
                    "unsupported_url", "FAIL",
                    f"非脚本化页面未被拒绝，返回长度 {len(value)} 的 {type(value).__name__}",
                )
            except Exception as exc:  # noqa: BLE001
                trace = str(getattr(exc, "trace_info", "") or "")
                ok = trace == "unsupported_url"
                rec.add(
                    "unsupported_url", "PASS" if ok else "FAIL",
                    f"非脚本化页面被明确拒绝：{type(exc).__name__} trace={trace} 消息={exc}"
                    if ok else error_detail("未返回 unsupported_url", exc),
                )
            if owned_scratch:
                close_tracked("scratch")

        # ---- 生命周期：关闭后必须报网页失效 ----
        close_tracked("fixture")
        try:
            fixture.get_html()
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
        close_errors = [text for text in (close_tracked(name) for name, _ in list(created)) if text]

        # 复核：本次创建的每个页面对象都必须已失效，证明标签确实关闭（不只「调用了 close」）
        proofs: list[str] = []
        for name, page in created:
            try:
                page.get_url()
                proofs.append(f"{name}=仍可读")
            except Exception as exc:  # noqa: BLE001
                proofs.append(f"{name}={str(getattr(exc, 'trace_info', '') or '') or type(exc).__name__}")
        proofs_ok = all(proof.endswith("stale_page_reference") for proof in proofs)

        shutil.rmtree(work_dir, ignore_errors=True)
        time.sleep(0.8)
        after_tabs = tab_count(args.mode)
        cleanup_ok = not close_errors and proofs_ok and not work_dir.exists()
        rec.add(
            "cleanup", "PASS" if cleanup_ok else "FAIL",
            f"本次创建的 {len(created)} 个页面对象关闭后均报 stale_page_reference，临时目录已删除；"
            f"标签数 {baseline_tabs} → {after_tabs}（用户可能同时浏览，仅作诊断）"
            if cleanup_ok else
            f"清理不完整：关闭错误={close_errors or '无'}，失效复核={proofs}，"
            f"临时目录残留={work_dir.exists()}，标签 {baseline_tabs} → {after_tabs}",
            tabs_before=baseline_tabs, tabs_after=after_tabs, proofs=proofs,
        )

    statuses = {item["status"] for item in rec.results}
    code = 1 if "FAIL" in statuses else (2 if "BLOCKED" in statuses else 0)
    return rec.results, code


def main(argv=None):
    global FIXTURE_URL
    parser = argparse.ArgumentParser(description="WebBrowser.get_html() 页面对象 API 验收")
    parser.add_argument("--target-url", default=FIXTURE_URL, help="靶场 fixture 页面")
    parser.add_argument("--mode", choices=("chrome", "edge"), default="chrome")
    parser.add_argument("--load-timeout", type=float, default=20)
    parser.add_argument("--contract-only", action="store_true")
    parser.add_argument("--json", action="store_true", help="在表格后额外输出 JSON 报告（用于归档验收产物）")
    args = parser.parse_args(argv)
    if args.load_timeout <= 0:
        parser.error("--load-timeout 必须大于 0")
    args.temp_root = Path(__file__).resolve().parents[1] / ".pytest_tmp"
    args.temp_root.mkdir(parents=True, exist_ok=True)

    FIXTURE_URL = args.target_url

    results, code = run(args)
    print("UIAutoma Web API 测试")
    print("API     : uiautoma.web.WebBrowser.get_html")
    print(f"页面    : {args.target_url}")
    print("元素库  : 不需要 Package / 元素库")
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
            "api": "uiautoma.web.WebBrowser.get_html",
            "target_url": args.target_url,
            "mode": args.mode,
            "sdk_path": str(Path(uiautoma.__file__).resolve()),
            "status": "PASS" if code == 0 else ("BLOCKED" if code == 2 else "FAIL"),
            "exit_code": code,
            "results": results,
        }, ensure_ascii=False, indent=2))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
