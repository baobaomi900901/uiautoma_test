"""WebBrowser.http_request() 页面对象 API 专项验收。

在被测网页的上下文里发送 HTTP 请求（引擎侧用页面内的 `fetch` 执行）。

## 目标站点的选择

- **官方靶场静态文件**（同源、相对路径、非 2xx、HEAD、保存文件、gzip 语义）——
  维护者的靶场 `https://baobaomi900901.github.io/xpath/`，测试侧不自建页面。
- **外部回显服务 `https://httpbin.org`**（请求方法/请求头/请求体是否真的送达、超时语义、
  大文件与二进制）——靶场是 GitHub Pages 静态托管，做不了服务端回显，故回显相关用例走它；
  该服务不可达时相关用例如实记 `BLOCKED`（不误判为 FAIL）。

## 源码要点（本次实测逐条核对）

- 请求在页面 ISOLATED 世界里用 `fetch(url, {method, headers, body, signal})` 发起，
  因此**相对路径按当前页面 URL 解析**、**默认 `credentials: 'same-origin'`**。
- 引擎先起 `connect_timeout` 的 AbortController 计时，收到响应头后再换成 `download_timeout`
  的计时 → **`connect_timeout` 约束到响应头为止，`download_timeout` 只约束读响应体**。
- `!response.ok` 时立即返回，`content` 为空字符串；带 `save_filename` 时改用
  `arrayBuffer()` → base64（32768 字节分块）→ SDK 解码为 `bytes` 并原子落盘（仅 2xx 才落盘）。
- 参数校验在 Runtime `runtime/web/http_response.py:validate_request()`；
  `url` 缺失由更早的传输层拒绝（消息为英文 `missing url`）。

退出码：0 = 全部 PASS（允许 BLOCKED 时另计）；1 = 存在 FAIL；2 = 无非 FAIL 但存在 BLOCKED。
"""
from __future__ import annotations

import argparse
import inspect
import json
import shutil
import time
import urllib.request
import uuid
from pathlib import Path

from uiautoma import ActionError, InvalidParamsError, web
from uiautoma.web import WebBrowser
from _web_page_identity import count_key, leaked, page_key

__test__ = False

PAGE_URL = "https://baobaomi900901.github.io/xpath/#/element-html-test"
SITE_BASE = "https://baobaomi900901.github.io/xpath/"
STATIC_FILE = "delayed-element.html"
STATIC_BYTES = 5289
MISSING_PATH = f"/xpath/{uuid.uuid4().hex}"  # 随机不存在路径（标准靶场宿主上的 404，不自造文件名）
ECHO_BASE = "https://httpbin.org"
# 地址形态探测已按边界约定删除（2026-09-18）：connect_timeout 语义改由回显服务的 /delay 覆盖。
RUN_TMP_ROOT = Path(__file__).resolve().parents[1] / ".pytest_tmp"
GREEN, RED, YELLOW, RESET = "\x1b[92m", "\x1b[91m", "\x1b[93m", "\x1b[0m"


def result(case_id: str, status: str, detail: str, **extra):
    return {"case_id": case_id, "status": status, "detail": detail, **extra}


def exception_name(exc: BaseException) -> str:
    return type(exc).__name__


def error_detail(prefix: str, exc: BaseException) -> str:
    trace_info = str(getattr(exc, "trace_info", "") or "")
    return f"{prefix}: {exception_name(exc)}: {str(exc)[:200]}" + (f" [trace={trace_info}]" if trace_info else "")


def check_contract():
    method = getattr(WebBrowser, "http_request", None)
    sig = inspect.signature(method) if callable(method) else None
    if sig is None:
        return result("api_contract", "FAIL", "WebBrowser.http_request 不存在")
    parameters = list(sig.parameters.values())
    names = tuple(sig.parameters)
    keyword_only = {name for name, p in sig.parameters.items()
                    if p.kind is inspect.Parameter.KEYWORD_ONLY}
    ok = (
        names == ("self", "url", "method", "headers", "body", "save_filename",
                  "connect_timeout", "download_timeout")
        and parameters[1].kind is inspect.Parameter.POSITIONAL_OR_KEYWORD
        and keyword_only == {"method", "headers", "body", "save_filename",
                             "connect_timeout", "download_timeout"}
        and sig.parameters["method"].default == "GET"
        and sig.parameters["headers"].default is None
        and sig.parameters["body"].default is None
        and sig.parameters["save_filename"].default is None
        and sig.parameters["connect_timeout"].default == 30
        and sig.parameters["download_timeout"].default == 300
        and str(sig.return_annotation) == "dict"
    )
    return result(
        "api_contract", "PASS" if ok else "FAIL",
        "url 为位置参数，其余 6 个仅限关键字（默认 GET/None/None/None/30/300），返回注解 dict" if ok
        else f"公开签名不符合合同: {sig}")


def expect_raises(call, expected_type, label: str, message_contains: str = "",
                  max_elapsed: float | None = None, min_elapsed: float | None = None, **extra):
    started = time.perf_counter()
    try:
        call()
    except expected_type as exc:
        elapsed = round(time.perf_counter() - started, 3)
        text = str(exc)
        if message_contains and message_contains not in text:
            return result(label, "FAIL", f"{exception_name(exc)} 消息不含 {message_contains!r}：{text[:200]}",
                          elapsed_s=elapsed, **extra)
        if max_elapsed is not None and elapsed > max_elapsed:
            return result(label, "FAIL", f"耗时过长：{elapsed}s > {max_elapsed}s", elapsed_s=elapsed, **extra)
        if min_elapsed is not None and elapsed < min_elapsed:
            return result(label, "FAIL", f"耗时过短：{elapsed}s < {min_elapsed}s（可能未真正等待）",
                          elapsed_s=elapsed, **extra)
        return result(label, "PASS", f"{exception_name(exc)} 正确拒绝（{elapsed}s）：{text[:160]}",
                      elapsed_s=elapsed, **extra)
    except Exception as exc:  # noqa: BLE001
        return result(label, "FAIL",
                      f"拒绝类型错误，应为 {expected_type.__name__}: {exception_name(exc)}: {exc}", **extra)
    return result(label, "FAIL", "调用未被拒绝", **extra)


def describe(response) -> str:
    if not isinstance(response, dict):
        return repr(response)
    content = response.get("content")
    shape = f"{type(content).__name__} len={len(content)}" if isinstance(content, (str, bytes)) else repr(content)
    return (f"status={response.get('status_code')}, content_type={response.get('content_type')!r}, "
            f"content_encoding={response.get('content_encoding')!r}, content=<{shape}>")


def fetch_reference(url: str) -> bytes | None:
    """独立下载参考字节（urllib 不发 Accept-Encoding，服务端返回未压缩字节）。"""
    try:
        with urllib.request.urlopen(urllib.request.Request(url), timeout=20) as response:
            return response.read()
    except Exception:  # noqa: BLE001
        return None


def expect_timeout_abort(call, label: str, elapsed_range: tuple[float, float], note: str, **extra):
    """超时被约束的用例：应为 ActionError，且耗时应落在给定区间。

    实测两种失败形态都会出现——`AbortError: signal is aborted without reason` /
    `AbortError: The user aborted a request.`（abort 先触发）与
    `TypeError: Failed to fetch`（网络层错误先抛出），语义关键在**耗时被超时参数约束**，
    因此两种消息都接受并如实记下实际形态。
    """
    started = time.perf_counter()
    try:
        response = call()
    except ActionError as exc:
        elapsed = round(time.perf_counter() - started, 3)
        text = str(exc)
        first_line = text.splitlines()[0][:120]
        low, high = elapsed_range
        kind = "abort" if "abort" in text.lower() else ("Failed to fetch" if "Failed to fetch" in text else "其他")
        ok = kind != "其他" and low <= elapsed <= high
        return result(
            label, "PASS" if ok else "FAIL",
            f"{note}：{exception_name(exc)}（{elapsed}s，形态={kind}）—— {first_line}" if ok else
            f"{note}：未按预期中止或耗时异常（elapsed={elapsed}s，形态={kind}）：{first_line}",
            elapsed_s=elapsed, failure_shape=kind, **extra)
    except Exception as exc:  # noqa: BLE001
        return result(label, "FAIL",
                      f"异常类型不符，应为 ActionError: {exception_name(exc)}: {exc}", **extra)
    return result(label, "FAIL", f"预期被中止但返回了结果：{describe(response)}", **extra)


def run(args):
    results = [check_contract()]
    if results[-1]["status"] != "PASS" or args.contract_only:
        return results, 0 if results[-1]["status"] == "PASS" else 1

    run_id = uuid.uuid4().hex
    work_dir = RUN_TMP_ROOT / run_id
    save_dir = work_dir / "saved"
    page = None
    page_id = ""
    echo_ready = False
    try:
        try:
            baseline = web.get_all(mode=args.mode)
            results.append(result(
                "environment_baseline", "PASS",
                f"进入时浏览器共 {len(baseline)} 个标签；本脚本**不打开任何元素库**"
                f"（http_request 只用 page_ref，无需 Package）", tabs=len(baseline)))
        except Exception as exc:  # noqa: BLE001
            results.append(result("environment_baseline", "BLOCKED", error_detail("无法读取标签列表", exc)))
            return results, 2

        work_dir.mkdir(parents=True, exist_ok=True)
        save_dir.mkdir(parents=True, exist_ok=True)

        try:
            page = web.create(args.page_url, mode=args.mode, load_timeout=args.load_timeout)
            page_id = page_key(page)
            baseline_matches = count_key(page_id, args.mode)
            ok = isinstance(page, WebBrowser)
            results.append(result(
                "page_prepare", "PASS" if ok else "FAIL",
                "已打开靶场页" if ok else f"返回对象异常: {page!r}", url=page.get_url()))
            if not ok:
                return results, 1
        except Exception as exc:  # noqa: BLE001
            results.append(result("page_prepare", "BLOCKED", error_detail("无法打开靶场页", exc)))
            return results, 2

        # 回显服务可达性（用它自己的通道判断，避免误判）
        try:
            probe = page.http_request(f"{ECHO_BASE}/get", connect_timeout=10, download_timeout=20)
            echo_ready = probe.get("status_code") == 200
            results.append(result(
                "echo_service_probe", "PASS" if echo_ready else "BLOCKED",
                f"回显服务 {ECHO_BASE} 可达（status={probe.get('status_code')}）" if echo_ready else
                f"回显服务不可达：{describe(probe)}；依赖它的用例本次记 BLOCKED"))
        except Exception as exc:  # noqa: BLE001
            results.append(result("echo_service_probe", "BLOCKED",
                                  f"回显服务不可达，依赖它的用例本次记 BLOCKED：{error_detail('', exc)}"))

        # ---------- 官方靶场静态文件（同源 / 相对路径） ----------
        reference_text = None
        reference_bytes = fetch_reference(SITE_BASE + STATIC_FILE)
        if reference_bytes is not None:
            reference_text = reference_bytes.decode("utf-8")
            results.append(result(
                "reference_download", "PASS",
                f"已独立下载参考文件 {STATIC_FILE}（{len(reference_bytes)} 字节）"))
        else:
            results.append(result("reference_download", "BLOCKED", "独立下载参考文件失败"))

        try:
            response = page.http_request("/xpath/" + STATIC_FILE)
            content = response.get("content")
            ok = (response.get("status_code") == 200
                  and response.get("content_type") == "text/html; charset=utf-8"
                  and isinstance(content, str)
                  and reference_text is not None and content == reference_text)
            results.append(result(
                "relative_path_leading_slash", "PASS" if ok else "FAIL",
                f"相对路径 /xpath/{STATIC_FILE}：{describe(response)}，"
                f"内容与独立下载的文本逐字符一致" if ok else
                f"结果不符：{describe(response)}；与参考文本一致="
                f"{isinstance(content, str) and reference_text is not None and content == reference_text}"))
            results.append(result(
                "gzip_transfer_reported_but_decoded", "PASS" if response.get("content_encoding") else "FAIL",
                f"服务端以 {response.get('content_encoding')!r} 传输，而 content 已是解码后的文本"
                f"（长度 {len(content) if isinstance(content, str) else '?'} 字符 ≠ "
                f"磁盘 {STATIC_BYTES} 字节；含中文多字节）" if response.get("content_encoding") else
                f"未观测到传输编码：{describe(response)}"))
        except Exception as exc:  # noqa: BLE001
            results.append(result("relative_path_leading_slash", "FAIL", error_detail("调用失败", exc)))

        try:
            response = page.http_request(STATIC_FILE)
            content = response.get("content")
            ok = (response.get("status_code") == 200 and isinstance(content, str)
                  and reference_text is not None and content == reference_text)
            results.append(result(
                "relative_path_without_slash", "PASS" if ok else "FAIL",
                f"无前导斜杠的相对路径 {STATIC_FILE} 同样命中（证明按页面 URL 解析 base）：{describe(response)}"
                if ok else f"结果不符：{describe(response)}"))
        except Exception as exc:  # noqa: BLE001
            results.append(result("relative_path_without_slash", "FAIL", error_detail("调用失败", exc)))

        try:
            response = page.http_request(SITE_BASE + "slow-load-30s.html")
            ok = response.get("status_code") == 200 and isinstance(response.get("content"), str) \
                and len(response["content"]) > 100
            results.append(result(
                "absolute_url", "PASS" if ok else "FAIL",
                f"绝对 URL 请求成功：{describe(response)}" if ok else f"结果不符：{describe(response)}"))
        except Exception as exc:  # noqa: BLE001
            results.append(result("absolute_url", "FAIL", error_detail("调用失败", exc)))

        try:
            response = page.http_request(MISSING_PATH)
            content = response.get("content")
            ok = response.get("status_code") == 404 and content == "" and isinstance(content, str)
            results.append(result(
                "not_found_empty_content", "PASS" if ok else "FAIL",
                f"404 时 status_code=404 且 content 为空**字符串**：{describe(response)}" if ok else
                f"结果不符：{describe(response)}"))
        except Exception as exc:  # noqa: BLE001
            results.append(result("not_found_empty_content", "FAIL", error_detail("调用失败", exc)))

        try:
            response = page.http_request("/xpath/" + STATIC_FILE, method="HEAD")
            content = response.get("content")
            ok = response.get("status_code") == 200 and content == ""
            results.append(result(
                "head_no_body", "PASS" if ok else "FAIL",
                f"HEAD 返回 200 且无响应体：{describe(response)}" if ok else f"结果不符：{describe(response)}"))
        except Exception as exc:  # noqa: BLE001
            results.append(result("head_no_body", "FAIL", error_detail("调用失败", exc)))

        try:
            response = page.http_request("/xpath/" + STATIC_FILE, method="POST", body="x=1")
            ok = response.get("status_code") == 405 and response.get("content") == ""
            results.append(result(
                "post_to_static_file_rejected", "PASS" if ok else "FAIL",
                f"对静态文件 POST 得到 405 且无内容（非 2xx 语义）：{describe(response)}" if ok else
                f"结果不符：{describe(response)}"))
        except Exception as exc:  # noqa: BLE001
            results.append(result("post_to_static_file_rejected", "FAIL", error_detail("调用失败", exc)))

        # ---------- 外部回显服务 ----------
        def echo_case(case_id: str, label: str, call, check):
            if not echo_ready:
                return result(case_id, "BLOCKED", f"回显服务不可达，跳过：{label}")
            started = time.perf_counter()
            try:
                response = call()
            except Exception as exc:  # noqa: BLE001
                return result(case_id, "FAIL", error_detail(f"{label} 调用失败", exc))
            elapsed = round(time.perf_counter() - started, 3)
            ok, detail = check(response)
            return result(case_id, "PASS" if ok else "FAIL", detail, elapsed_s=elapsed)

        def parse_json(response):
            content = response.get("content")
            if not isinstance(content, str):
                raise ValueError(f"content 不是字符串：{type(content).__name__}")
            return json.loads(content)

        def check_post_echo(response):
            if response.get("status_code") != 200:
                return False, f"状态码非 200：{describe(response)}"
            payload = parse_json(response)
            headers = payload.get("headers") or {}
            got = {
                "data": payload.get("data"),
                "x_probe": headers.get("X-Probe"),
                "content_type": headers.get("Content-Type"),
                "url": payload.get("url"),
            }
            ok = (got["data"] == '{"hello":"世界"}' and got["x_probe"] == "uiautomata-42"
                  and got["content_type"] == "application/json"
                  and str(got["url"]).startswith(ECHO_BASE + "/post"))
            return ok, (f"回显核对：data={got['data']!r}、X-Probe={got['x_probe']!r}、"
                        f"Content-Type={got['content_type']!r}、url={got['url']!r}"
                        if ok else f"回显不符：{got}")

        results.append(echo_case(
            "echo_post_body_and_headers", "POST 回显（请求体与自定义请求头）",
            lambda: page.http_request(f"{ECHO_BASE}/post", method="POST", body='{"hello":"世界"}',
                                      headers={"Content-Type": "application/json",
                                               "X-Probe": "uiautomata-42"}),
            check_post_echo))

        for case_id, method, endpoint, body in (
            ("echo_put", "PUT", "/put", "put-body"),
            ("echo_patch", "PATCH", "/patch", "patch-body"),
            ("echo_delete", "DELETE", "/delete", None),
        ):
            def check_method(response, method=method, body=body):
                if response.get("status_code") != 200:
                    return False, f"状态码非 200：{describe(response)}"
                payload = parse_json(response)
                data = payload.get("data")
                ok = (data == body) if body else (data == "")
                return ok, (f"{method} 送达且回显 data={data!r}" if ok else f"{method} 回显不符：data={data!r}")

            results.append(echo_case(
                case_id, f"{method} {endpoint}",
                lambda endpoint=endpoint, method=method, body=body: page.http_request(
                    ECHO_BASE + endpoint, method=method, body=body),
                check_method))

        results.append(echo_case(
            "lowercase_method_uppercased", "小写方法名 get",
            lambda: page.http_request(f"{ECHO_BASE}/get", method="get"),
            lambda response: (response.get("status_code") == 200,
                              f"小写 'get' 被规范化为大写并成功：{describe(response)}")
            if response.get("status_code") == 200 else
            (False, f"结果不符：{describe(response)}")))

        results.append(expect_raises(
            lambda: page.http_request(f"{ECHO_BASE}/get", method="GET", body="nope"),
            ActionError, "get_with_body_rejected",
            message_contains="GET/HEAD method cannot have body", max_elapsed=5.0))

        # 跨源 Cookie 不外泄
        try:
            page.set_cookie(name="uiautomata_probe", value="probe-value")
            cookie = page.get_cookie(name="uiautomata_probe")
            if not echo_ready:
                results.append(result("cross_origin_no_cookie_leak", "BLOCKED", "回显服务不可达，跳过"))
            else:
                response = page.http_request(f"{ECHO_BASE}/cookies")
                payload = parse_json(response) if response.get("status_code") == 200 else {}
                echoed = payload.get("cookies") or {}
                ok = echoed == {}
                results.append(result(
                    "cross_origin_no_cookie_leak", "PASS" if ok else "FAIL",
                    f"已设置靶场 Cookie（{cookie.get('name')}@{cookie.get('domain')}），"
                    f"跨源请求回显 cookies={echoed} —— 默认 credentials=same-origin，不外泄" if ok else
                    f"跨源请求带出了 Cookie：{echoed}"))
        except Exception as exc:  # noqa: BLE001
            results.append(result("cross_origin_no_cookie_leak", "FAIL", error_detail("Cookie 用例失败", exc)))
        finally:
            try:
                page.remove_cookie("uiautomata_probe")
            except Exception:  # noqa: BLE001
                pass

        # ---------- 超时语义 ----------
        # 按 2026-09-18 边界约定，不再用不可路由地址制造「连接永不完成」；
        # connect_timeout 的约束语义改由回显服务的 /delay 路径覆盖（见下）。

        if echo_ready:
            results.append(expect_timeout_abort(
                lambda: page.http_request(f"{ECHO_BASE}/delay/4", connect_timeout=1),
                "connect_timeout_bounds_headers", (0.8, 3.0),
                "/delay/4 + connect_timeout=1：响应头未到即中止"))
            started = time.perf_counter()
            try:
                response = page.http_request(f"{ECHO_BASE}/delay/2")
                elapsed = round(time.perf_counter() - started, 3)
                ok = response.get("status_code") == 200 and elapsed >= 1.8
                results.append(result(
                    "headers_delay_within_connect_timeout", "PASS" if ok else "FAIL",
                    f"/delay/2 在默认超时下成功（{elapsed}s）——说明 TTFB 由 connect_timeout 约束、"
                    f"download_timeout 不约束它" if ok else
                    f"结果不符：{describe(response)}，耗时 {elapsed}s", elapsed_s=elapsed))
            except Exception as exc:  # noqa: BLE001
                results.append(result("headers_delay_within_connect_timeout", "FAIL",
                                      error_detail("调用失败", exc)))
            results.append(expect_timeout_abort(
                lambda: page.http_request(f"{ECHO_BASE}/drip?numbytes=50&duration=5&delay=0",
                                          download_timeout=1),
                "download_timeout_bounds_body", (0.8, 4.0),
                "头部即时返回、响应体分块 5s：download_timeout=1 在读体阶段中止"))
            started = time.perf_counter()
            try:
                response = page.http_request(f"{ECHO_BASE}/drip?numbytes=50&duration=2&delay=0",
                                             download_timeout=6)
                elapsed = round(time.perf_counter() - started, 3)
                content = response.get("content")
                ok = response.get("status_code") == 200 and isinstance(content, str) and len(content) == 50
                results.append(result(
                    "drip_within_download_timeout", "PASS" if ok else "FAIL",
                    f"分块响应在 download_timeout=6 内完整读完（{elapsed}s，{len(content)} 字符）" if ok else
                    f"结果不符：{describe(response)}，耗时 {elapsed}s", elapsed_s=elapsed))
            except Exception as exc:  # noqa: BLE001
                results.append(result("drip_within_download_timeout", "FAIL", error_detail("调用失败", exc)))
        else:
            for case_id in ("connect_timeout_bounds_headers", "headers_delay_within_connect_timeout",
                            "download_timeout_bounds_body", "drip_within_download_timeout"):
                results.append(result(case_id, "BLOCKED", "回显服务不可达，跳过"))

        # ---------- 保存文件 ----------
        try:
            target = save_dir / "nested" / "deep" / "saved-page.html"
            response = page.http_request("/xpath/" + STATIC_FILE, save_filename=str(target))
            content = response.get("content")
            reference = fetch_reference(SITE_BASE + STATIC_FILE)
            ok = (response.get("status_code") == 200 and isinstance(content, bytes)
                  and target.is_file() and reference is not None
                  and target.read_bytes() == reference and content == reference)
            results.append(result(
                "save_text_creates_nested_dirs", "PASS" if ok else "FAIL",
                f"保存到嵌套新目录成功：content 为 bytes（{len(content) if isinstance(content, bytes) else '?'} 字节），"
                f"落盘文件与独立下载的字节完全一致" if ok else
                f"结果不符：{describe(response)}，文件存在={target.is_file()}，"
                f"字节一致={target.read_bytes() == reference if target.is_file() and reference else False}"))
        except Exception as exc:  # noqa: BLE001
            results.append(result("save_text_creates_nested_dirs", "FAIL", error_detail("保存用例失败", exc)))

        if echo_ready:
            try:
                target = save_dir / "big.bin"
                response = page.http_request(f"{ECHO_BASE}/bytes/100000", save_filename=str(target),
                                             download_timeout=60)
                content = response.get("content")
                ok = (response.get("status_code") == 200 and isinstance(content, bytes)
                      and len(content) == 100000 and target.is_file()
                      and target.stat().st_size == 100000 and target.read_bytes() == content)
                results.append(result(
                    "save_binary_chunked_100k", "PASS" if ok else "FAIL",
                    f"100000 字节二进制：content 为 bytes 且长度 100000，落盘文件同长度且与 content 逐字节一致"
                    f"（跨 32768 分块路径）" if ok else
                    f"结果不符：{describe(response)}，文件大小="
                    f"{target.stat().st_size if target.is_file() else 'n/a'}"))
            except Exception as exc:  # noqa: BLE001
                results.append(result("save_binary_chunked_100k", "FAIL", error_detail("二进制保存失败", exc)))

            try:
                response = page.http_request(f"{ECHO_BASE}/bytes/2000")
                content = response.get("content")
                ok = response.get("status_code") == 200 and isinstance(content, str)
                results.append(result(
                    "binary_without_save_is_text", "PASS" if ok else "FAIL",
                    f"不保存时二进制响应被按文本解码：content 为 str（{len(content)} 字符，"
                    f"与 2000 字节不等 → 有损）——想拿原始字节必须传 save_filename" if ok else
                    f"结果不符：{describe(response)}"))
            except Exception as exc:  # noqa: BLE001
                results.append(result("binary_without_save_is_text", "FAIL", error_detail("调用失败", exc)))
        else:
            for case_id in ("save_binary_chunked_100k", "binary_without_save_is_text"):
                results.append(result(case_id, "BLOCKED", "回显服务不可达，跳过"))

        try:
            target = save_dir / "not-saved.html"
            response = page.http_request(MISSING_PATH, save_filename=str(target))
            content = response.get("content")
            ok = response.get("status_code") == 404 and content == "" and not target.exists()
            results.append(result(
                "non_2xx_not_saved", "PASS" if ok else "FAIL",
                f"非 2xx 时不落盘且 content 为空字符串：{describe(response)}，文件存在={target.exists()}" if ok else
                f"结果不符：{describe(response)}，文件存在={target.exists()}"))
        except Exception as exc:  # noqa: BLE001
            results.append(result("non_2xx_not_saved", "FAIL", error_detail("调用失败", exc)))

        try:
            target = save_dir / "head.bin"
            response = page.http_request("/xpath/" + STATIC_FILE, method="HEAD",
                                         save_filename=str(target))
            ok = (response.get("status_code") == 200 and isinstance(response.get("content"), bytes)
                  and target.is_file() and target.stat().st_size == 0)
            results.append(result(
                "head_save_creates_empty_file", "PASS" if ok else "FAIL",
                f"HEAD + save_filename：content 为空 bytes，落盘 0 字节文件（如实记录该行为）" if ok else
                f"结果不符：{describe(response)}，文件大小="
                f"{target.stat().st_size if target.is_file() else 'n/a'}"))
        except Exception as exc:  # noqa: BLE001
            results.append(result("head_save_creates_empty_file", "FAIL", error_detail("调用失败", exc)))

        results.append(expect_raises(
            lambda: page.http_request("/xpath/" + STATIC_FILE, save_filename=str(save_dir)),
            InvalidParamsError, "save_path_is_directory", message_contains="文件名", max_elapsed=1.0))

        # ---------- 参数校验 ----------
        results.append(expect_raises(
            lambda: page.http_request(""), InvalidParamsError, "url_empty",
            message_contains="missing url", max_elapsed=1.0))
        results.append(expect_raises(
            lambda: page.http_request(None), InvalidParamsError, "url_none",
            message_contains="missing url", max_elapsed=1.0))
        results.append(expect_raises(
            lambda: page.http_request(SITE_BASE, method=""), InvalidParamsError, "method_empty",
            message_contains="HTTP 方法不能为空", max_elapsed=1.0))
        results.append(expect_raises(
            lambda: page.http_request(SITE_BASE, headers={"X": 1}), InvalidParamsError,
            "headers_non_str_value", message_contains="字符串字典", max_elapsed=1.0))
        results.append(expect_raises(
            lambda: page.http_request(SITE_BASE, method="POST", body={"a": 1}), InvalidParamsError,
            "body_not_str", message_contains="字符串", max_elapsed=1.0))
        results.append(expect_raises(
            lambda: page.http_request(SITE_BASE, connect_timeout=0), InvalidParamsError,
            "connect_timeout_zero", message_contains="至少 1 秒", max_elapsed=1.0))
        results.append(expect_raises(
            lambda: page.http_request(SITE_BASE, connect_timeout=0.5), InvalidParamsError,
            "connect_timeout_fraction", message_contains="至少 1 秒", max_elapsed=1.0))
        results.append(expect_raises(
            lambda: page.http_request(SITE_BASE, download_timeout=True), InvalidParamsError,
            "download_timeout_bool", message_contains="至少 1 秒", max_elapsed=1.0))
        results.append(expect_raises(
            lambda: page.http_request(SITE_BASE, save_filename=""), InvalidParamsError,
            "save_filename_empty", message_contains="保存路径", max_elapsed=1.0))

        # ---------- 生命周期 ----------
        try:
            page.close(ignore_beforeunload=True)
        except Exception as exc:  # noqa: BLE001
            results.append(result("page_close_verified", "FAIL", error_detail("page.close 调用失败", exc)))
        else:
            time.sleep(0.5)
            leftover = leaked(page_id, baseline_matches, args.mode)
            results.append(result(
                "page_close_verified", "PASS" if not leftover else "FAIL",
                "页面已关闭，且 web.get_all() 复核无残留" if not leftover else
                f"关闭后仍有残留: {len(leftover)}", leftover_pages=len(leftover)))
        results.append(expect_raises(
            lambda: page.http_request(SITE_BASE), ActionError, "after_page_close", max_elapsed=3.0))
        page = None
    except Exception as exc:  # noqa: BLE001
        results.append(result("scenario", "FAIL", error_detail("http_request 场景执行失败", exc)))
    finally:
        close_error = ""
        if page is not None:
            try:
                page.close(ignore_beforeunload=True)
            except Exception as exc:  # noqa: BLE001
                close_error = f"{exception_name(exc)}: {exc}"
        produced = len([p for p in work_dir.rglob("*") if p.is_file()]) if work_dir.exists() else 0
        shutil.rmtree(work_dir, ignore_errors=True)
        time.sleep(0.5)
        cleaned = not close_error and not work_dir.exists()
        results.append(result(
            "cleanup", "PASS" if cleaned else "FAIL",
            f"已关闭页面、删除本次临时目录（含 {produced} 个落盘产物）" if cleaned else
            f"清理不完整: 错误={close_error or '无'}, 临时目录残留={work_dir.exists()}",
            produced_files=produced, error=close_error))

    statuses = {item["status"] for item in results}
    code = 1 if "FAIL" in statuses else (2 if "BLOCKED" in statuses else 0)
    return results, code


def main(argv=None):
    parser = argparse.ArgumentParser(description="WebBrowser.http_request() 页面对象 API 验收")
    parser.add_argument("--page-url", default=PAGE_URL, help="请求发起所在的靶场页")
    parser.add_argument("--mode", choices=("chrome", "edge"), default="chrome")
    parser.add_argument("--load-timeout", type=float, default=20)
    parser.add_argument("--contract-only", action="store_true")
    parser.add_argument("--json", action="store_true", help="在表格后额外输出 JSON 报告（用于归档验收产物）")
    args = parser.parse_args(argv)
    if args.load_timeout <= 0:
        parser.error("--load-timeout 必须大于 0")

    results, code = run(args)
    print("UIAutoma Web API 测试")
    print("API     : uiautoma.web.WebBrowser.http_request")
    print(f"页面    : {args.page_url}")
    print(f"回显服务: {ECHO_BASE}（不可达时相关用例记 BLOCKED）")
    print("进度     状态    测试项                  测试结果")
    print("────────────────────────────────────────────────────────────────────────")
    for index, current in enumerate(results, 1):
        status = current["status"]
        color = {"PASS": GREEN, "BLOCKED": YELLOW}.get(status, RED)
        label = {"PASS": "通过", "BLOCKED": "阻塞"}.get(status, "失败")
        print(f"{index:02d}/{len(results):02d}    {color}[{label}]{RESET}  "
              f"{current['case_id']:<38}  {current['detail']}")
    print("────────────────────────────────────────────────────────────────────────")
    summary = "测试通过" if code == 0 else ("测试阻塞" if code == 2 else "测试失败")
    print(f"{summary} · {sum(item['status'] == 'PASS' for item in results)}/{len(results)} 通过 · 退出码 {code}")
    if args.json:
        print(json.dumps({
            "api": "uiautoma.web.WebBrowser.http_request",
            "page_url": args.page_url, "echo_base": ECHO_BASE, "mode": args.mode,
            "status": "PASS" if code == 0 else ("BLOCKED" if code == 2 else "FAIL"),
            "exit_code": code, "results": results,
        }, ensure_ascii=False, indent=2))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
