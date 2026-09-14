"""uiautoma.web.handle_save_dialog() 下载对话框靶场专项验收。"""
from __future__ import annotations

import argparse
import inspect
import shutil
import sys
import tempfile
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
DEFAULT_URL = "https://baobaomi900901.github.io/xpath/#/download-dialog-test"
DEFAULT_LIBRARY = Path(r"D:\code\元素库\260902_web元素")
DEFAULT_ELEMENT = "web靶场_下载对话框测试 _下载txt"
GREEN, RED, RESET = "\x1b[92m", "\x1b[91m", "\x1b[0m"


def result(case_id: str, status: str, detail: str, **extra: Any) -> dict[str, Any]:
    return {"case_id": case_id, "status": status, "detail": detail, **extra}


def check_contract() -> dict[str, Any]:
    signature = inspect.signature(web.handle_save_dialog)
    expected = ("file_folder", "dialog_result", "mode", "file_name", "overwrite", "wait_complete",
                "wait_complete_timeout", "simulative", "clipboard_input", "wait_appear_timeout",
                "force_ime_eng", "send_key_delay", "focus_timeout")
    actual = tuple(signature.parameters)
    kinds_ok = all(signature.parameters[name].kind == inspect.Parameter.POSITIONAL_OR_KEYWORD for name in expected[:3]) and all(signature.parameters[name].kind == inspect.Parameter.KEYWORD_ONLY for name in expected[3:])
    defaults = {"dialog_result": "ok", "mode": "auto", "file_name": None, "overwrite": True,
                "wait_complete": False, "wait_complete_timeout": 300, "simulative": False,
                "clipboard_input": True, "wait_appear_timeout": 20, "force_ime_eng": False,
                "send_key_delay": 50, "focus_timeout": 1000}
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
        status, extra = "FAIL", {
            "exception": type(exc).__name__,
            "trace_info": trace,
            "strategy": str(getattr(exc, "strategy", "") or ""),
            "fallback_reason": str(getattr(exc, "fallback_reason", "") or ""),
            "log_lines": list(getattr(exc, "log_lines", []) or []),
        }
    results.append(result(case_id, status, detail, elapsed_ms=round((time.perf_counter() - started) * 1000, 1), **extra))
    return status == "PASS"


def wait_file(path: Path, timeout: float = 5.0) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if path.is_file() and path.stat().st_size >= 0:
            return True
        time.sleep(0.1)
    return path.is_file()


def run(args: argparse.Namespace) -> tuple[list[dict[str, Any]], int]:
    results = [check_contract()]
    if results[-1]["status"] != "PASS" or args.contract_only:
        return results, 0 if results[-1]["status"] == "PASS" else 1
    page: WebBrowser | None = None
    package: Any | None = None
    run_dir = Path(tempfile.mkdtemp(prefix="uiautoma-save-dialog-"))
    file_name = "uiautoma-save-dialog.txt"
    try:
        def prepare():
            nonlocal page, package
            try:
                page = web.create(args.target_url, mode=args.mode, load_timeout=args.load_timeout)
            except Exception as exc:
                raise RuntimeError(f"打开靶场失败: {type(exc).__name__}: {exc}") from exc
            if not isinstance(page, WebBrowser):
                raise RuntimeError(f"页面返回类型错误: {type(page).__name__}")
            try:
                package = uiautoma.open(str(args.element_library), timeout=args.runtime_timeout, connect_timeout=args.runtime_timeout)
            except Exception as exc:
                raise RuntimeError(f"元素库连接失败: {type(exc).__name__}: {exc}") from exc
            web_count = getattr(package, "web_count", None)
            if not isinstance(web_count, int) or web_count <= 0:
                raise RuntimeError(f"元素库没有可用 Web 元素: web_count={web_count!r}")
            try:
                element = page.find(args.element_name, timeout=args.element_timeout)
            except Exception as exc:
                raise RuntimeError(f"下载元素查找失败（名称={args.element_name!r}）: {type(exc).__name__}: {exc}") from exc
            runtime_name = str(getattr(element, "name", "") or "")
            element_id = str(getattr(element, "id", "") or "")
            if not element_id:
                raise RuntimeError(f"下载元素已返回但缺少运行时 id: runtime_name={runtime_name!r}")
            return "已打开靶场并获取可操作下载按钮", "PASS", {
                "library_element_name": args.element_name,
                "runtime_element_name": runtime_name,
                "element_id_present": True,
                "web_count": web_count,
            }

        if not run_case(results, "page_and_element_prepare", prepare):
            return results, 1

        def save_once():
            page.activate()
            element = page.find(args.element_name, timeout=args.element_timeout)
            # 受控页面使用 DOM 点击，避免已有 Chrome 会话触发 HWND 绑定错误。
            try:
                click_return = element.click(simulative=False, delay_after=0.2)
            except Exception as exc:
                raise RuntimeError(f"触发下载按钮点击失败: {type(exc).__name__}: {exc}") from exc
            path = run_dir / file_name
            try:
                returned = web.handle_save_dialog(str(run_dir), "ok", args.mode, file_name=file_name,
                                                  overwrite=True, wait_complete=False,
                                                  wait_appear_timeout=args.dialog_timeout)
            except Exception as exc:
                trace = str(getattr(exc, "trace_info", "") or getattr(exc, "error_code", "") or "")
                extra = {"exception": type(exc).__name__, "trace_info": trace,
                         "strategy": str(getattr(exc, "strategy", "") or ""),
                         "log_lines": list(getattr(exc, "log_lines", []) or [])}
                return f"handle_save_dialog 调用失败: {type(exc).__name__}: {exc}" + (f" [trace={trace}]" if trace else ""), "FAIL", extra
            exists = wait_file(path)
            ok = click_return is None and returned == str(path) and exists
            return ("点击下载元素后保存对话框成功，返回路径与文件存在" if ok else "保存结果、返回路径或文件存在性不符合预期",
                    "PASS" if ok else "FAIL", {"returned_path": returned, "file_exists": exists})

        if not run_case(results, "save_ok", save_once):
            return results, 1

        def cancel_once():
            # 确认保存场景可能改变下载按钮/浏览器下载状态；刷新后再验证取消，
            # 避免把前一场景的页面状态误判为取消 API 失败。
            page.reload(load_timeout=args.load_timeout)
            page.activate()
            element = page.find(args.element_name, timeout=args.element_timeout)
            try:
                element.click(simulative=False, delay_after=0.2)
            except Exception as exc:
                raise RuntimeError(f"触发取消场景下载按钮失败: {type(exc).__name__}: {exc}") from exc
            try:
                returned = web.handle_save_dialog(str(run_dir), "cancel", args.mode, wait_appear_timeout=args.dialog_timeout)
            except Exception as exc:
                trace = str(getattr(exc, "trace_info", "") or getattr(exc, "error_code", "") or "")
                extra = {"exception": type(exc).__name__, "trace_info": trace,
                         "strategy": str(getattr(exc, "strategy", "") or ""),
                         "log_lines": list(getattr(exc, "log_lines", []) or [])}
                return f"handle_save_dialog 取消调用失败: {type(exc).__name__}: {exc}" + (f" [trace={trace}]" if trace else ""), "FAIL", extra
            return ("取消保存返回空字符串" if returned == "" else "取消保存返回值不正确",
                    "PASS" if returned == "" else "FAIL", {"returned_path": returned})

        if not run_case(results, "cancel", cancel_once):
            return results, 1

        def invalid_dialog_result():
            try:
                web.handle_save_dialog(str(run_dir), "invalid", args.mode)
            except Exception as exc:  # noqa: BLE001
                return "非法 dialog_result 被拒绝", "PASS", {"exception": type(exc).__name__}
            return "非法 dialog_result 未被拒绝", "FAIL", {}

        run_case(results, "invalid_dialog_result", invalid_dialog_result)
        def keyword_only():
            try:
                web.handle_save_dialog(str(run_dir), "ok", args.mode, "positional.txt")
            except TypeError:
                return "file_name 位置传入被 TypeError 拒绝", "PASS", {}
            return "file_name 位置传入未被拒绝", "FAIL", {}

        run_case(results, "keyword_only", keyword_only)
    finally:
        cleanup_ok = True
        try:
            if package is not None:
                package.close()
        except Exception:
            cleanup_ok = False
        try:
            if page is not None:
                page.close(ignore_beforeunload=True)
        except Exception:
            cleanup_ok = False
        try:
            shutil.rmtree(run_dir)
        except Exception:
            cleanup_ok = False
        results.append(result("cleanup", "PASS" if cleanup_ok else "FAIL",
                              "Package、页面和临时下载目录已清理" if cleanup_ok else "资源清理失败"))
    return results, 0 if all(item["status"] == "PASS" for item in results) else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="uiautoma.web.handle_save_dialog() Web API 验收")
    parser.add_argument("--target-url", default=DEFAULT_URL)
    parser.add_argument("--element-library", type=Path, default=DEFAULT_LIBRARY)
    parser.add_argument("--element-name", default=DEFAULT_ELEMENT)
    parser.add_argument("--mode", choices=("chrome", "edge"), default="chrome")
    parser.add_argument("--profile-directory", default="Default")
    parser.add_argument("--load-timeout", type=float, default=20)
    parser.add_argument("--runtime-timeout", type=float, default=5)
    parser.add_argument("--element-timeout", type=float, default=10)
    parser.add_argument("--dialog-timeout", type=float, default=20)
    parser.add_argument("--contract-only", action="store_true")
    args = parser.parse_args(argv)
    print("UIAutoma Web API 测试\n API     : uiautoma.web.handle_save_dialog")
    print(f" 页面    : {args.target_url}\n 元素库  : {args.element_library}\n 测试元素: {args.element_name}")
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
