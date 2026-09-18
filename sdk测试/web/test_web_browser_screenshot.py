"""WebBrowser.screenshot() 页面对象 API 专项验收。

靶场：维护者的官方靶场 `https://baobaomi900901.github.io/xpath/#/form-controls`
（测试侧不自建页面）。

期望值来源：**活推导** —— 先用 `execute_javascript()` 读出
`documentElement.scrollWidth/scrollHeight` 与 `window.innerWidth/innerHeight`，
再与实际产出的图片尺寸比对。

「截图确实成功」不能靠返回值判定（本 API 返回 `None`），因此脚本**直接解析产出的图片字节**：
- PNG：校验 8 字节魔数 + 读 IHDR 的宽高；
- JPEG：校验 `FFD8FF` 魔数 + 读 SOF 段的宽高。

产物写入本工作区临时目录（`sdk测试/.pytest_tmp/<run_id>/`），结束时整目录删除。

退出码：0 = 全部 PASS；1 = 存在 FAIL；2 = 无非 FAIL 但存在 BLOCKED。
"""
from __future__ import annotations

import argparse
import inspect
import json
import shutil
import struct
import time
import uuid
from pathlib import Path
from urllib.parse import urlsplit

from uiautoma import InvalidParamsError, web
from uiautoma.web import WebBrowser
from _web_page_identity import count_key, leaked, page_key

__test__ = False

DEFAULT_URL = "https://baobaomi900901.github.io/xpath/#/form-controls"
RUN_TMP_ROOT = Path(__file__).resolve().parents[1] / ".pytest_tmp"
PNG_MAGIC = b"\x89PNG\r\n\x1a\n"
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
    method = getattr(WebBrowser, "screenshot", None)
    sig = inspect.signature(method) if callable(method) else None
    if sig is None:
        return result("api_contract", "FAIL", "WebBrowser.screenshot 不存在")
    parameters = list(sig.parameters.values())
    names = tuple(sig.parameters)
    ok = (
        names == ("self", "folder_path", "file_name", "full_size", "piece_height", "height")
        and parameters[1].kind is inspect.Parameter.POSITIONAL_OR_KEYWORD
        and parameters[1].default is inspect.Parameter.empty
        and parameters[2].kind is inspect.Parameter.KEYWORD_ONLY
        and parameters[2].default is None
        and parameters[3].kind is inspect.Parameter.KEYWORD_ONLY
        and parameters[3].default is True
        and parameters[4].kind is inspect.Parameter.KEYWORD_ONLY
        and parameters[4].default == 0
        and parameters[5].kind is inspect.Parameter.KEYWORD_ONLY
        and parameters[5].default == 0
        and str(sig.return_annotation) == "None"
    )
    detail = (
        "folder_path 必填；file_name / full_size / piece_height / height 仅限关键字"
        "（默认 None / True / 0 / 0）；返回注解 None" if ok else f"公开签名不符合合同: {sig}"
    )
    return result("api_contract", "PASS" if ok else "FAIL", detail)


def exception_name(exc: BaseException) -> str:
    return type(exc).__name__


def error_detail(prefix: str, exc: BaseException) -> str:
    trace_info = str(getattr(exc, "trace_info", "") or "")
    return f"{prefix}: {exception_name(exc)}: {exc}" + (f" [trace={trace_info}]" if trace_info else "")


def expect_raises(call, expected_type, label: str, message_contains: str = "",
                  max_elapsed: float | None = None):
    started = time.perf_counter()
    try:
        call()
    except expected_type as exc:
        elapsed = round(time.perf_counter() - started, 3)
        text = str(exc)
        if message_contains and message_contains not in text:
            return result(label, "FAIL", f"{exception_name(exc)} 消息不含 {message_contains!r}：{text}", elapsed_s=elapsed)
        if max_elapsed is not None and elapsed > max_elapsed:
            return result(label, "FAIL", f"耗时过长：{elapsed}s > {max_elapsed}s（应在 SDK 侧立即拒绝）", elapsed_s=elapsed)
        return result(label, "PASS", f"{exception_name(exc)} 正确拒绝（{elapsed}s）：{text}", elapsed_s=elapsed)
    except Exception as exc:  # noqa: BLE001
        return result(label, "FAIL", f"拒绝类型错误，应为 {expected_type.__name__}: {exception_name(exc)}: {exc}")
    return result(label, "FAIL", "调用未被拒绝")


def image_info(path: Path):
    """独立解析图片字节，返回 (格式, 宽, 高) 或错误字符串。"""
    try:
        data = path.read_bytes()
    except Exception as exc:  # noqa: BLE001
        return None, None, f"读取失败 {type(exc).__name__}"
    if data[:8] == PNG_MAGIC:
        if len(data) < 24:
            return "png", None, "PNG 过短"
        width, height = struct.unpack(">II", data[16:24])
        return "png", (width, height), None
    if data[:3] == b"\xff\xd8\xff":
        index = 2
        while index + 9 < len(data):
            if data[index] != 0xFF:
                index += 1
                continue
            marker = data[index + 1]
            if marker in (0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7, 0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF):
                height, width = struct.unpack(">HH", data[index + 5:index + 9])
                return "jpeg", (width, height), None
            if marker in (0xD8, 0xD9) or 0xD0 <= marker <= 0xD7:
                index += 2
                continue
            seg_len = struct.unpack(">H", data[index + 2:index + 4])[0]
            index += 2 + seg_len
        return "jpeg", None, "未找到 SOF 段"
    return None, None, f"未知格式，前 4 字节={data[:4]!r}"


def shot_case(case_id: str, label: str, folder: Path, call, expected, *,
              expected_ext: str = "png", elapsed_note: bool = False):
    """执行截图 → 核对返回值、文件数量、格式与尺寸。"""
    started = time.perf_counter()
    try:
        returned = call()
    except Exception as exc:  # noqa: BLE001
        return result(case_id, "FAIL", error_detail(f"{label} 调用失败", exc))
    elapsed = round(time.perf_counter() - started, 3)
    files = sorted(p for p in folder.rglob("*") if p.is_file())
    if returned is not None:
        return result(case_id, "FAIL", f"{label} 应返回 None，实际 {returned!r}", elapsed_s=elapsed)
    if len(files) != 1:
        return result(case_id, "FAIL", f"{label} 应恰好产出 1 个文件，实际 {len(files)}：{[f.name for f in files]}",
                      elapsed_s=elapsed)
    file = files[0]
    fmt, size, error = image_info(file)
    if error:
        return result(case_id, "FAIL", f"{label} 产出文件不可解析：{error}（{file.name}）", elapsed_s=elapsed)
    if fmt != expected_ext:
        return result(case_id, "FAIL", f"{label} 期望 {expected_ext} 格式，实际 {fmt}", elapsed_s=elapsed)
    if size != tuple(expected):
        return result(case_id, "FAIL", f"{label} 尺寸不符：期望 {tuple(expected)}，实际 {size}", elapsed_s=elapsed)
    return result(
        case_id, "PASS",
        f"{label} 产出 {file.name}（{fmt} {size[0]}×{size[1]}，{elapsed}s）",
        file_name=file.name, format=fmt, width=size[0], height=size[1], elapsed_s=elapsed)


def single_file(folder: Path) -> Path | None:
    files = sorted(p for p in folder.rglob("*") if p.is_file())
    return files[0] if len(files) == 1 else None


def run(args):
    results = [check_contract()]
    if results[-1]["status"] != "PASS" or args.contract_only:
        return results, 0 if results[-1]["status"] == "PASS" else 1

    run_id = uuid.uuid4().hex
    run_dir = RUN_TMP_ROOT / run_id
    page = None
    page_id = ""
    try:
        try:
            page = web.create(args.target_url, mode=args.mode, load_timeout=args.load_timeout)
            page_id = page_key(page)
            baseline_matches = count_key(page_id, args.mode)
            current = page.get_url()
            ok = isinstance(page, WebBrowser) and same_url(current, args.target_url)
            results.append(result(
                "page_prepare", "PASS" if ok else "FAIL",
                "已打开官方靶场页" if ok else f"URL 不符: {current!r}", url=current))
            if not ok:
                return results, 1
        except Exception as exc:  # noqa: BLE001
            results.append(result("page_prepare", "BLOCKED", error_detail("无法打开靶场页", exc)))
            return results, 2

        # 活推导：页面尺寸与视口尺寸
        try:
            metrics = page.execute_javascript(
                "function () { const el = document.documentElement;"
                " return {sh: el.scrollHeight, sw: el.scrollWidth,"
                " ih: window.innerHeight, iw: window.innerWidth}; }")
            ok = (
                isinstance(metrics, dict)
                and int(metrics.get("sh") or 0) > 0
                and int(metrics.get("sw") or 0) > 0
                and int(metrics.get("ih") or 0) > 0
            )
            results.append(result(
                "dom_expectations", "PASS" if ok else "FAIL",
                f"活推导页面尺寸 {metrics.get('sw')}×{metrics.get('sh')}，视口 {metrics.get('iw')}×{metrics.get('ih')}"
                if ok else f"无法取得页面尺寸: {metrics}", metrics=metrics))
            if not ok:
                return results, 1
            full_w, full_h = int(metrics["sw"]), int(metrics["sh"])
            view_h, view_w = int(metrics["ih"]), int(metrics["iw"])
        except Exception as exc:  # noqa: BLE001
            results.append(result("dom_expectations", "BLOCKED", error_detail("无法读取页面尺寸", exc)))
            return results, 2

        # 目标用例 1：默认整页截图（自动命名）
        folder = run_dir / "default"
        results.append(shot_case(
            "default_full_page", "默认整页（自动命名）", folder,
            lambda: page.screenshot(str(folder)), (full_w, full_h)))

        # 目标用例 2：显式文件名 + 扩展名决定格式（用 .jpg 验证非 PNG 分支）
        folder = run_dir / "named"
        results.append(shot_case(
            "custom_name_jpg", "file_name='acceptance-shot.jpg'", folder,
            lambda: page.screenshot(str(folder), file_name="acceptance-shot.jpg"),
            (full_w, full_h), expected_ext="jpeg"))
        jpg = single_file(folder)
        if jpg is not None:
            results[-1]["actual_file_name"] = jpg.name

        # 目标用例 3：仅视口（应小于整页高度，且不超过视口）
        folder = run_dir / "viewport"
        started = time.perf_counter()
        try:
            returned = page.screenshot(str(folder), full_size=False)
            elapsed = round(time.perf_counter() - started, 3)
            file = single_file(folder)
            info = image_info(file)[1] if file else None
            ok = (
                returned is None and info is not None
                and 0 < info[1] < full_h and info[0] <= full_w
                and info[1] <= view_h
            )
            results.append(result(
                "viewport_only", "PASS" if ok else "FAIL",
                f"full_size=False 产出视口尺寸 {info[0]}×{info[1]}（整页高 {full_h}，视口高 {view_h}）" if ok else
                f"结果不符: return={returned!r}, size={info}, full=({full_w},{full_h}), viewport=({view_w},{view_h})",
                size=list(info) if info else None, full_size=[full_w, full_h], viewport=[view_w, view_h],
                elapsed_s=elapsed))
        except Exception as exc:  # noqa: BLE001
            results.append(result("viewport_only", "FAIL", error_detail("视口截图失败", exc)))

        # 目标用例 4：height 限高
        folder = run_dir / "height"
        results.append(shot_case(
            "height_clip", "height=600 限高", folder,
            lambda: page.screenshot(str(folder), height=600), (full_w, 600)))

        # 目标用例 5：piece_height 分段并拼接回整页
        folder = run_dir / "pieces"
        results.append(shot_case(
            "piece_height_stitch", "piece_height=500 分段拼接", folder,
            lambda: page.screenshot(str(folder), piece_height=500), (full_w, full_h)))

        # 目标用例 6：多级目录自动创建
        folder = run_dir / "deep" / "nested" / "folder"
        results.append(shot_case(
            "auto_create_folder", "多级目录自动创建", folder,
            lambda: page.screenshot(str(folder)), (full_w, full_h)))

        # 参数校验（均应在 SDK 侧立即拒绝）
        results.append(expect_raises(
            lambda: page.screenshot(""), InvalidParamsError, "empty_folder",
            message_contains="保存目录", max_elapsed=1.0))
        results.append(expect_raises(
            lambda: page.screenshot("   "), InvalidParamsError, "blank_folder",
            message_contains="保存目录", max_elapsed=1.0))
        results.append(expect_raises(
            lambda: page.screenshot(None), InvalidParamsError, "non_str_folder",
            message_contains="保存目录", max_elapsed=1.0))
        results.append(expect_raises(
            lambda: page.screenshot(str(run_dir / "bad1"), file_name="a/b"), InvalidParamsError,
            "file_name_with_slash", message_contains="非法字符", max_elapsed=1.0))
        results.append(expect_raises(
            lambda: page.screenshot(str(run_dir / "bad2"), file_name=".."), InvalidParamsError,
            "file_name_dotdot", message_contains="非法字符", max_elapsed=1.0))
        results.append(expect_raises(
            lambda: page.screenshot(str(run_dir / "bad3"), file_name="a\x01b"), InvalidParamsError,
            "file_name_control_char", message_contains="非法字符", max_elapsed=1.0))
        results.append(expect_raises(
            lambda: page.screenshot(str(run_dir / "bad4"), full_size=1), InvalidParamsError,
            "full_size_non_bool", message_contains="full_size", max_elapsed=1.0))
        results.append(expect_raises(
            lambda: page.screenshot(str(run_dir / "bad5"), piece_height=-1), InvalidParamsError,
            "piece_height_negative", message_contains="piece_height", max_elapsed=1.0))
        results.append(expect_raises(
            lambda: page.screenshot(str(run_dir / "bad6"), piece_height=True), InvalidParamsError,
            "piece_height_bool", message_contains="piece_height", max_elapsed=1.0))
        results.append(expect_raises(
            lambda: page.screenshot(str(run_dir / "bad7"), height="x"), InvalidParamsError,
            "height_non_int", message_contains="height", max_elapsed=1.0))

        # 关闭页面并复核
        try:
            returned = page.close(ignore_beforeunload=True)
        except Exception as exc:  # noqa: BLE001
            results.append(result("page_close_verified", "FAIL", error_detail("page.close 调用失败", exc)))
        else:
            time.sleep(0.5)
            leftover = leaked(page_id, baseline_matches, args.mode)
            ok = returned is None and not leftover
            results.append(result(
                "page_close_verified", "PASS" if ok else "FAIL",
                "页面已关闭，且 web.get_all() 复核无残留" if ok else
                f"关闭后仍有残留: return={returned!r}, leftover={len(leftover)}",
                leftover_pages=len(leftover)))
        page = None
    except Exception as exc:  # noqa: BLE001
        results.append(result("scenario", "FAIL", error_detail("screenshot 场景执行失败", exc)))
    finally:
        page_close_error = ""
        if page is not None:
            try:
                page.close(ignore_beforeunload=True)
            except Exception as exc:  # noqa: BLE001
                page_close_error = f"{type(exc).__name__}: {exc}"
        produced = len([p for p in run_dir.rglob("*") if p.is_file()]) if run_dir.exists() else 0
        shutil.rmtree(run_dir, ignore_errors=True)
        leftover = []
        try:
            leftover = leaked(page_id, baseline_matches, args.mode)
        except Exception as exc:  # noqa: BLE001
            page_close_error = page_close_error or f"get_all 复核失败: {type(exc).__name__}: {exc}"
        cleaned = not leftover and not page_close_error and not run_dir.exists()
        results.append(result(
            "cleanup", "PASS" if cleaned else "FAIL",
            f"已关闭页面（get_all 复核无残留）、删除本次截图目录（含 {produced} 个产物文件）" if cleaned else
            f"清理不完整: 残留页面={len(leftover)}, close 错误={page_close_error or '无'}, 目录残留={run_dir.exists()}",
            leftover_pages=len(leftover), produced_files=produced, page_close_error=page_close_error))

    statuses = {item["status"] for item in results}
    code = 1 if "FAIL" in statuses else (2 if "BLOCKED" in statuses else 0)
    return results, code


def main(argv=None):
    parser = argparse.ArgumentParser(description="WebBrowser.screenshot() 页面对象 API 验收")
    parser.add_argument("--target-url", default=DEFAULT_URL, help="靶场页")
    parser.add_argument("--mode", choices=("chrome", "edge"), default="chrome")
    parser.add_argument("--load-timeout", type=float, default=20)
    parser.add_argument("--contract-only", action="store_true")
    parser.add_argument("--json", action="store_true", help="在表格后额外输出 JSON 报告（用于归档验收产物）")
    args = parser.parse_args(argv)
    if args.load_timeout <= 0:
        parser.error("--load-timeout 必须大于 0")

    results, code = run(args)
    print("UIAutoma Web API 测试")
    print("API     : uiautoma.web.WebBrowser.screenshot")
    print(f"页面    : {args.target_url}")
    print("进度     状态    测试项                  测试结果")
    print("────────────────────────────────────────────────────────────────────────")
    for index, current in enumerate(results, 1):
        status = current["status"]
        color = {"PASS": GREEN, "BLOCKED": YELLOW}.get(status, RED)
        label = {"PASS": "通过", "BLOCKED": "阻塞"}.get(status, "失败")
        print(f"{index:02d}/{len(results):02d}    {color}[{label}]{RESET}  {current['case_id']:<26}  {current['detail']}")
    print("────────────────────────────────────────────────────────────────────────")
    summary = "测试通过" if code == 0 else ("测试阻塞" if code == 2 else "测试失败")
    print(f"{summary} · {sum(item['status'] == 'PASS' for item in results)}/{len(results)} 通过 · 退出码 {code}")
    if args.json:
        print(json.dumps({
            "api": "uiautoma.web.WebBrowser.screenshot",
            "target_url": args.target_url, "mode": args.mode,
            "status": "PASS" if code == 0 else ("BLOCKED" if code == 2 else "FAIL"),
            "exit_code": code, "results": results,
        }, ensure_ascii=False, indent=2))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
