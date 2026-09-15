"""WebElement.get_text() 元素 HTML 靶场专项验收。"""
from __future__ import annotations

import argparse
import inspect
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
from uiautoma.web import WebBrowser, WebElement  # noqa: E402

__test__ = False
DEFAULT_URL = "https://baobaomi900901.github.io/xpath/#/element-html-test"
LIBRARY = Path(r"D:\code\元素库\260902_web元素")
INPUT_NAME = "web靶场_测试get_text_输入框"
APPLY_NAME = "web靶场_测试get_text_按钮_确定"
RESET_NAME = "web靶场_测试get_text_按钮_重置"
TARGET_NAME = "web靶场_测试get_text_靶元素"
RESET_TEXT = "等待渲染 HTML…"
GREEN, RED, RESET = "\x1b[92m", "\x1b[91m", "\x1b[0m"


def result(case_id: str, status: str, detail: str, **extra: Any) -> dict[str, Any]:
    return {"case_id": case_id, "status": status, "detail": detail, **extra}


def check_contract() -> dict[str, Any]:
    signature = inspect.signature(WebElement.get_text)
    ok = tuple(signature.parameters) == ("self",) and signature.return_annotation in (str, "str", "'str'")
    return result("api_contract", "PASS" if ok else "FAIL",
                  "get_text 无公开参数，返回 str" if ok else f"get_text 合同不符: {signature}")


def run(args: argparse.Namespace) -> tuple[list[dict[str, Any]], int]:
    results = [check_contract()]
    if results[-1]["status"] != "PASS" or args.contract_only:
        return results, 0 if results[-1]["status"] == "PASS" else 1
    page: WebBrowser | None = None
    package: Any | None = None
    elements: dict[str, WebElement] = {}
    try:
        try:
            page = web.create(args.target_url, mode=args.mode, load_timeout=args.load_timeout)
            package = uiautoma.open(str(LIBRARY), timeout=args.runtime_timeout, connect_timeout=args.runtime_timeout)
            for key, name in (("input", INPUT_NAME), ("apply", APPLY_NAME), ("reset", RESET_NAME), ("target", TARGET_NAME)):
                elements[key] = page.find(name, timeout=args.element_timeout)
                if not isinstance(elements[key], WebElement) or not str(elements[key].id or ""):
                    raise RuntimeError(f"{name} 未返回有效 WebElement")
            results.append(result("page_and_elements", "PASS", "靶场、元素库和四个目标元素均已就绪",
                                  element_names={key: value.name for key, value in elements.items()},
                                  web_count=getattr(package, "web_count", None)))
        except Exception as exc:  # noqa: BLE001
            results.append(result("page_and_elements", "FAIL", f"测试准备失败: {type(exc).__name__}: {exc}"))
            return results, 1

        def reset_and_verify() -> str:
            elements["reset"].click(simulative=False, delay_after=0)
            deadline = time.monotonic() + 2.0
            input_value, target_text = None, None
            while time.monotonic() < deadline:
                input_value = elements["input"].get_value()
                target_text = elements["target"].get_text()
                if str(input_value or "") == "" and target_text == RESET_TEXT:
                    return "输入框已清空；靶元素已恢复默认提示"
                time.sleep(0.05)
            raise AssertionError(f"重置状态不符: input={input_value!r}, target={target_text!r}")

        try:
            initial_detail = reset_and_verify()
            results.append(result("initial_reset", "PASS", initial_detail))
        except Exception as exc:  # noqa: BLE001
            results.append(result("initial_reset", "FAIL", f"初始重置失败: {type(exc).__name__}: {exc}"))
            return results, 1
        cases = (
            ("plain_text", "普通文本 UIAutoma 123 中文 😀✓", "普通文本与 Unicode"),
            ("special_chars", "!@#$%^&*()_+-=[]{};:'\\\",.?/\\|~", "特殊字符原样渲染"),
            ("nested_html", "<div><span><label>三层嵌套文本</label></span></div>", "div→span→label 三层嵌套"),
        )
        for case_id, text, description in cases:
            started = False
            try:
                # 使用剪贴板输入更新受控 React 输入框，避免模拟键盘对 Unicode 产生编码替换。
                elements["input"].clipboard_input(text, delay_after=0.2)
                started = True
                entered = str(elements["input"].get_value() or "")
                if entered != text:
                    raise AssertionError(f"输入框未写入预期文本: entered={entered!r}, expected={text!r}")
                # Ant Button 的受控 onClick 需要真实点击事件才能提交输入状态。
                elements["apply"].click(simulative=True, delay_after=0.2)
                oracle = page.execute_javascript("function () { return document.getElementById('element-html-target').innerText; }", execution_world="MAIN")
                if str(oracle or "") == RESET_TEXT:
                    raise AssertionError("点击确定后靶元素仍为默认提示，输入/确定步骤未生效")
                actual = elements["target"].get_text()
                if not isinstance(actual, str):
                    raise AssertionError(f"get_text 返回类型错误: {type(actual).__name__}")
                if actual != str(oracle or ""):
                    raise AssertionError(f"get_text 与独立 DOM innerText 不一致: actual={actual!r}, oracle={oracle!r}")
                if case_id == "nested_html" and actual != "三层嵌套文本":
                    raise AssertionError(f"三层嵌套文本不符合预期: {actual!r}")
                detail = f"{description}；get_text 与 DOM innerText 一致: {actual!r}"
                status = "PASS"
            except Exception as exc:  # noqa: BLE001
                detail, status = f"{description}失败: {type(exc).__name__}: {exc}", "FAIL"
            finally:
                try:
                    reset_and_verify()
                except Exception as exc:  # noqa: BLE001
                    detail += f"；重置失败: {type(exc).__name__}: {exc}"
                    status = "FAIL"
            results.append(result(case_id, status, detail, input_text=text, started=started))

        try:
            elements["target"].get_text("extra")
        except TypeError:
            results.append(result("argument_rules", "PASS", "额外位置参数被 TypeError 拒绝"))
        else:
            results.append(result("argument_rules", "FAIL", "额外位置参数未被拒绝"))
    except Exception as exc:  # noqa: BLE001
        results.append(result("scenario", "FAIL", f"场景执行失败: {type(exc).__name__}: {exc}"))
    finally:
        try:
            reset_and_verify()
        except Exception:
            pass
        cleanup_ok = True
        if package is not None:
            try:
                package.close()
            except Exception:
                cleanup_ok = False
        if page is not None:
            try:
                page.close(ignore_beforeunload=True)
            except Exception:
                cleanup_ok = False
        results.append(result("cleanup", "PASS" if cleanup_ok else "FAIL",
                              "Package 和测试页面已清理" if cleanup_ok else "资源清理失败"))
    return results, 0 if all(item["status"] == "PASS" for item in results) else 1


def main(argv=None):
    parser = argparse.ArgumentParser(description="WebElement.get_text() HTML 靶场验收")
    parser.add_argument("--target-url", default=DEFAULT_URL)
    parser.add_argument("--mode", choices=("chrome", "edge"), default="chrome")
    parser.add_argument("--load-timeout", type=float, default=20)
    parser.add_argument("--runtime-timeout", type=float, default=5)
    parser.add_argument("--element-timeout", type=float, default=10)
    parser.add_argument("--contract-only", action="store_true")
    args = parser.parse_args(argv)
    results, code = run(args)
    print("UIAutoma Web API 测试\n API     : uiautoma.web.WebElement.get_text")
    print(f" 页面    : {args.target_url}\n 元素库  : {LIBRARY}")
    print("进度     状态    测试项                  测试结果")
    print("───────  ──────  ─────────────────────  ─────────────────────────────")
    for i, current in enumerate(results, 1):
        passed = current["status"] == "PASS"
        print(f"{i:02d}/{len(results):02d}    {(GREEN if passed else RED)}[{'通过' if passed else '失败'}]{RESET}  {current['case_id']:<22}  {current['detail']}")
    print("─" * 72)
    print(f"{'测试通过' if code == 0 else '测试失败'} · {sum(i['status']=='PASS' for i in results)}/{len(results)} 通过 · 退出码 {code}")
    return code


if __name__ == "__main__":
    raise SystemExit(main())
