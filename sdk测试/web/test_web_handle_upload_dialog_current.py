"""uiautoma.web.handle_upload_dialog() 上传对话框靶场专项验收。"""
from __future__ import annotations

import argparse
import ctypes
import inspect
import os
import sys
import time
from pathlib import Path
from typing import Any

PRODUCT_ROOT = Path(__file__).resolve().parents[3]
SDK_SRC = PRODUCT_ROOT / "sdk" / "src"
if str(SDK_SRC) not in sys.path:
    sys.path.insert(0, str(SDK_SRC))

import uiautoma  # noqa: E402
from uiautoma import web  # noqa: E402
from uiautoma.web import WebBrowser  # noqa: E402

__test__ = False
DEFAULT_URL = "https://baobaomi900901.github.io/xpath/#/upload-dialog-test"
DEFAULT_LIBRARY = Path(r"D:\code\元素库\260902_web元素")
DEFAULT_ELEMENT = "web靶场_上传对话框测试 _原生_上传组件"
GREEN, RED, RESET = "\x1b[92m", "\x1b[91m", "\x1b[0m"
UPLOAD_DIALOG_TITLES = ("打开", "选择文件", "选择要上传的文件", "open", "choose file", "file upload")


def _is_upload_dialog(hwnd: int) -> bool:
    if os.name != "nt" or not hwnd:
        return False
    user32 = ctypes.windll.user32
    if not user32.IsWindow(int(hwnd)) or not user32.IsWindowVisible(int(hwnd)):
        return False
    cls = ctypes.create_unicode_buffer(256)
    title = ctypes.create_unicode_buffer(512)
    user32.GetClassNameW(int(hwnd), cls, len(cls))
    user32.GetWindowTextW(int(hwnd), title, len(title))
    return str(cls.value) == "#32770" and any(part in str(title.value).casefold() for part in UPLOAD_DIALOG_TITLES)


def _find_upload_dialog() -> int:
    if os.name != "nt":
        return 0
    user32 = ctypes.windll.user32
    foreground = int(user32.GetForegroundWindow() or 0)
    if _is_upload_dialog(foreground):
        return foreground
    found = ctypes.c_void_p(0)
    callback_type = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)
    def visit(hwnd, _lparam):
        if _is_upload_dialog(int(hwnd)):
            found.value = int(hwnd)
            return False
        return True
    user32.EnumWindows(callback_type(visit), None)
    return int(found.value or 0)


def _close_upload_dialog(hwnd: int) -> dict[str, Any]:
    if not hwnd:
        return {"status": "PASS", "confirmed": True, "found": False}
    user32 = ctypes.windll.user32
    posted = bool(user32.PostMessageW(int(hwnd), 0x0010, 0, 0))
    deadline = time.monotonic() + 2
    while time.monotonic() < deadline and _is_upload_dialog(hwnd):
        time.sleep(0.05)
    confirmed = not _is_upload_dialog(hwnd)
    return {"status": "PASS" if posted and confirmed else "FAIL", "confirmed": confirmed,
            "found": True, "close_message_posted": posted, "hwnd": int(hwnd)}


def result(case_id: str, status: str, detail: str, **extra: Any) -> dict[str, Any]:
    return {"case_id": case_id, "status": status, "detail": detail, **extra}


def check_contract() -> dict[str, Any]:
    signature = inspect.signature(web.handle_upload_dialog)
    # 44c8e91f：公开参数 file_paths 改名为 file_names（RPC 层仍是 file_paths）
    expected = ("file_names", "dialog_result", "mode", "simulative", "clipboard_input",
                "wait_appear_timeout", "force_ime_eng", "send_key_delay", "focus_timeout")
    actual = tuple(signature.parameters)
    kinds_ok = all(signature.parameters[name].kind == inspect.Parameter.POSITIONAL_OR_KEYWORD for name in expected[:3]) and all(signature.parameters[name].kind == inspect.Parameter.KEYWORD_ONLY for name in expected[3:])
    defaults = {"dialog_result": "ok", "mode": "auto", "simulative": False, "clipboard_input": True,
                "wait_appear_timeout": 20, "force_ime_eng": False, "send_key_delay": 50, "focus_timeout": 1000}
    defaults_ok = all(signature.parameters[name].default == value for name, value in defaults.items())
    ok = actual == expected and kinds_ok and defaults_ok
    return result("api_contract", "PASS" if ok else "FAIL",
                  "公开签名符合当前合同" if ok else "公开签名、参数顺序或默认值不一致",
                  parameter_order_ok=actual == expected, parameter_kinds_ok=kinds_ok, defaults_ok=defaults_ok)


def run_case(results: list[dict[str, Any]], case_id: str, call) -> bool:
    started = time.perf_counter()
    try:
        detail, status, extra = call()
    except Exception as exc:  # noqa: BLE001
        trace = str(getattr(exc, "trace_info", "") or getattr(exc, "error_code", "") or "")
        detail = f"{type(exc).__name__}: {exc}" + (f" [trace={trace}]" if trace else "")
        status, extra = "FAIL", {"exception": type(exc).__name__, "trace_info": trace,
                                  "strategy": str(getattr(exc, "strategy", "") or ""),
                                  "log_lines": list(getattr(exc, "log_lines", []) or [])}
    results.append(result(case_id, status, detail,
                          elapsed_ms=round((time.perf_counter() - started) * 1000, 1), **extra))
    return status == "PASS"


def selected_file_name(page: WebBrowser, element: Any, file_path: Path) -> bool:
    values = []
    try:
        values.append(str(element.get_value() or ""))
    except Exception:
        pass
    try:
        raw = page.execute_javascript(
            "Array.from(document.querySelectorAll('input[type=file]')).map(item => item.value || '')",
            execution_world="MAIN",
        )
        if isinstance(raw, list):
            values.extend(str(item) for item in raw)
    except Exception:
        pass
    return any(Path(value.replace("\\", "/")).name.casefold() == file_path.name.casefold() for value in values if value)


def run(args: argparse.Namespace) -> tuple[list[dict[str, Any]], int]:
    results = [check_contract()]
    if results[-1]["status"] != "PASS" or args.contract_only:
        return results, 0 if results[-1]["status"] == "PASS" else 1
    page: WebBrowser | None = None
    package: Any | None = None
    dialog_hwnd = 0
    upload_file = args.upload_file.resolve()
    if not upload_file.is_file():
        results.append(result("upload_file_prepare", "FAIL", f"上传文件不存在: {upload_file}"))
        return results, 1
    results.append(result("upload_file_prepare", "PASS", "已确认用户指定上传文件存在；测试不会删除该文件",
                          file_path=str(upload_file), file_size=upload_file.stat().st_size))
    try:
        def prepare():
            nonlocal page, package
            page = web.create(args.target_url, mode=args.mode, load_timeout=args.load_timeout)
            if not isinstance(page, WebBrowser):
                raise RuntimeError(f"页面返回类型错误: {type(page).__name__}")
            package = uiautoma.open(str(args.element_library), timeout=args.runtime_timeout, connect_timeout=args.runtime_timeout)
            count = getattr(package, "web_count", None)
            element = page.find(args.element_name, timeout=args.element_timeout)
            element_id = str(getattr(element, "id", "") or "")
            if not isinstance(count, int) or count <= 0:
                raise RuntimeError(f"元素库没有可用 Web 元素: web_count={count!r}")
            if not element_id:
                raise RuntimeError("上传元素缺少运行时 id")
            return "已打开上传靶场并获取可操作上传按钮", "PASS", {
                "library_element_name": args.element_name,
                "runtime_element_name": str(getattr(element, "name", "") or ""),
                "web_count": count,
            }

        if not run_case(results, "page_and_element_prepare", prepare):
            return results, 1

        def upload_ok():
            nonlocal dialog_hwnd
            page.activate()
            element = page.find(args.element_name, timeout=args.element_timeout)
            try:
                element.click(simulative=True, delay_after=0.2)
            except Exception as exc:
                raise RuntimeError(f"触发上传按钮点击失败: {type(exc).__name__}: {exc}") from exc
            time.sleep(0.1)
            dialog_hwnd = _find_upload_dialog()
            try:
                returned = web.handle_upload_dialog(str(upload_file), "ok", args.mode,
                                                     simulative=False, clipboard_input=True,
                                                     wait_appear_timeout=args.dialog_timeout)
            except Exception as exc:
                trace = str(getattr(exc, "trace_info", "") or getattr(exc, "error_code", "") or "")
                raise RuntimeError(f"handle_upload_dialog 调用失败: {type(exc).__name__}: {exc}" + (f" [trace={trace}]" if trace else "")) from exc
            selected = selected_file_name(page, element, upload_file)
            ok = returned is None and selected
            return ("选择文件成功并在页面读回文件名" if ok else "返回值或页面文件选择状态不符合预期",
                    "PASS" if ok else "FAIL", {"return_is_none": returned is None, "selected_file_name_matches": selected})

        if not run_case(results, "upload_ok", upload_ok):
            return results, 1

        def cancel():
            nonlocal dialog_hwnd
            page.activate()
            page.find(args.element_name, timeout=args.element_timeout).click(simulative=True, delay_after=0.2)
            time.sleep(0.1)
            dialog_hwnd = _find_upload_dialog()
            returned = web.handle_upload_dialog([], "cancel", args.mode, wait_appear_timeout=args.dialog_timeout)
            return ("取消上传返回 None" if returned is None else "取消上传返回值不正确",
                    "PASS" if returned is None else "FAIL", {"return_is_none": returned is None})

        if not run_case(results, "cancel", cancel):
            return results, 1

        def invalid_result():
            try:
                web.handle_upload_dialog([], "invalid", args.mode)
            except Exception as exc:
                return "非法 dialog_result 被拒绝", "PASS", {"exception": type(exc).__name__}
            return "非法 dialog_result 未被拒绝", "FAIL", {}

        run_case(results, "invalid_dialog_result", invalid_result)
        def keyword_only():
            try:
                web.handle_upload_dialog([], "ok", args.mode, True)
            except TypeError:
                return "simulative 位置传入被 TypeError 拒绝", "PASS", {}
            return "simulative 位置传入未被拒绝", "FAIL", {}

        run_case(results, "keyword_only", keyword_only)
    finally:
        cleanup_ok = True
        preserve = args.preserve_on_failure and any(item["status"] == "FAIL" for item in results)
        if preserve:
            dialog_cleanup = {"status": "BLOCKED", "confirmed": False, "preserved": True,
                              "reason": "preserve_on_failure"}
        else:
            try:
                dialog_cleanup = _close_upload_dialog(dialog_hwnd)
            except Exception as exc:  # noqa: BLE001
                dialog_cleanup = {"status": "FAIL", "confirmed": False,
                                  "exception": type(exc).__name__, "error": str(exc)}
            if dialog_cleanup.get("status") != "PASS":
                cleanup_ok = False
        try:
            if package is not None:
                package.close()
        except Exception:
            cleanup_ok = False
        if not preserve:
            try:
                if page is not None:
                    page.close(ignore_beforeunload=True)
            except Exception:
                cleanup_ok = False
        else:
            cleanup_ok = False
        results.append(result("cleanup", "PASS" if cleanup_ok else "FAIL",
                              "上传系统弹窗、Package、页面已清理；用户文件保留"
                              if cleanup_ok else "按 preserve_on_failure 保留系统弹窗/页面，需人工处理",
                              dialog_cleanup=dialog_cleanup))
    return results, 0 if all(item["status"] == "PASS" for item in results) else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="uiautoma.web.handle_upload_dialog() Web API 验收")
    parser.add_argument("--target-url", default=DEFAULT_URL)
    parser.add_argument("--element-library", type=Path, default=DEFAULT_LIBRARY)
    parser.add_argument("--element-name", default=DEFAULT_ELEMENT)
    parser.add_argument("--upload-file", type=Path,
                        default=Path(r"C:\Users\moby\Desktop\jianfa260819.lnc"),
                        help="上传文件路径；默认使用用户指定的 jianfa260819.lnc，测试不会删除")
    parser.add_argument("--mode", choices=("chrome", "edge"), default="chrome")
    parser.add_argument("--load-timeout", type=float, default=20)
    parser.add_argument("--runtime-timeout", type=float, default=5)
    parser.add_argument("--element-timeout", type=float, default=10)
    parser.add_argument("--dialog-timeout", type=float, default=20)
    parser.add_argument("--contract-only", action="store_true")
    parser.add_argument("--preserve-on-failure", action="store_true",
                        help="API 失败时保留系统上传弹窗和网页，便于人工确认；默认自动清理")
    args = parser.parse_args(argv)
    print("UIAutoma Web API 测试\n API     : uiautoma.web.handle_upload_dialog")
    print(f" 页面    : {args.target_url}\n 元素库  : {args.element_library}\n 测试元素: {args.element_name}\n 上传文件: {args.upload_file}")
    results, code = run(args)
    print("进度     状态    测试项                  测试结果 / 耗时\n" + "─" * 110)
    for i, item in enumerate(results, 1):
        passed = item["status"] == "PASS"
        print(f"{i:02d}/{len(results):02d}    {(GREEN if passed else RED)}[{'通过' if passed else '失败'}]{RESET}  {item['case_id']:<22}  {item['detail']}  {item.get('elapsed_ms', 0):.1f}ms")
    print("─" * 110)
    print(f"{'测试通过' if code == 0 else '测试失败'} · {sum(i['status']=='PASS' for i in results)}/{len(results)} 通过 · 退出码 {code}")
    return code


if __name__ == "__main__":
    raise SystemExit(main())
