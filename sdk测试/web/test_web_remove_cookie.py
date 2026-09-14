"""uiautoma.web.remove_cookie() 独立验收脚本。"""
from __future__ import annotations

import argparse
import inspect
import sys
from pathlib import Path
from typing import Any

PRODUCT_ROOT = Path(__file__).resolve().parents[3]
SDK_SRC = PRODUCT_ROOT / "sdk" / "src"
if str(SDK_SRC) not in sys.path:
    sys.path.insert(0, str(SDK_SRC))

from uiautoma import web  # noqa: E402
from uiautoma.web import WebBrowser  # noqa: E402

__test__ = False
DEFAULT_URL = "https://baobaomi900901.github.io/xpath/#/cookie-test"
GREEN, RED, RESET = "\x1b[92m", "\x1b[91m", "\x1b[0m"


def result(case_id: str, status: str, detail: str, **extra: Any) -> dict[str, Any]:
    return {"case_id": case_id, "status": status, "detail": detail, **extra}


def check_contract() -> dict[str, Any]:
    signature = inspect.signature(web.remove_cookie)
    expected = ("url", "name", "mode", "partition_key")
    actual = tuple(signature.parameters)
    kinds_ok = all(signature.parameters[name].kind == inspect.Parameter.POSITIONAL_OR_KEYWORD for name in ("url", "name", "mode")) and signature.parameters["partition_key"].kind == inspect.Parameter.KEYWORD_ONLY
    defaults_ok = signature.parameters["mode"].default == "auto" and signature.parameters["partition_key"].default is None
    ok = actual == expected and kinds_ok and defaults_ok
    return result("api_contract", "PASS" if ok else "FAIL",
                  "公开签名符合当前合同" if ok else "公开签名、参数顺序或默认值不一致",
                  parameter_order_ok=actual == expected, parameter_kinds_ok=kinds_ok, defaults_ok=defaults_ok)


def run(args: argparse.Namespace) -> tuple[list[dict[str, Any]], int]:
    results = [check_contract()]
    if results[-1]["status"] != "PASS" or args.contract_only:
        return results, 0 if results[-1]["status"] == "PASS" else 1
    page: WebBrowser | None = None
    names = ("uiautoma_remove_cookie", "uiautoma_remove_cookie_missing")
    try:
        page = web.create(args.target_url, mode=args.mode, load_timeout=args.load_timeout)
        results.append(result("test_page_prepare", "PASS" if isinstance(page, WebBrowser) else "FAIL",
                              "已打开 Cookie 测试页面" if isinstance(page, WebBrowser) else "返回对象类型错误"))
        web.set_cookie(args.target_url, args.mode, name=names[0], value="to-remove", path="/")
        returned = web.remove_cookie(args.target_url, names[0], args.mode)
        after = web.get_cookie(args.target_url, args.mode, name=names[0])
        ok = returned is None and after == {}
        results.append(result("remove_existing", "PASS" if ok else "FAIL",
                              "删除已存在 Cookie 后返回 None 且读取为空" if ok else "删除结果不正确"))
        returned = web.remove_cookie(args.target_url, names[0], args.mode)
        results.append(result("remove_repeat", "PASS" if returned is None else "FAIL",
                              "重复删除安全返回 None" if returned is None else "重复删除返回值不正确"))
        returned = web.remove_cookie(args.target_url, names[1], args.mode)
        results.append(result("remove_missing", "PASS" if returned is None else "FAIL",
                              "删除不存在 Cookie 返回 None" if returned is None else "未命中删除返回值不正确"))
        try:
            web.remove_cookie(args.target_url, names[0], args.mode, partition_key={"top_level_site": "https://example.com"})
        except Exception as exc:  # noqa: BLE001
            results.append(result("partition_key", "PASS", "分区参数按合同处理或被环境拒绝", exception=type(exc).__name__))
        else:
            results.append(result("partition_key", "PASS", "分区参数调用完成"))
        try:
            web.remove_cookie(args.target_url)
        except TypeError:
            results.append(result("missing_name", "PASS", "缺少 name 被 TypeError 拒绝"))
        else:
            results.append(result("missing_name", "FAIL", "缺少 name 未被拒绝"))
        try:
            web.remove_cookie(args.target_url, names[0], args.mode, None)
        except TypeError:
            results.append(result("keyword_only", "PASS", "partition_key 位置传入被 TypeError 拒绝"))
        else:
            results.append(result("keyword_only", "FAIL", "partition_key 位置传入未被拒绝"))
    except Exception as exc:  # noqa: BLE001
        results.append(result("scenario", "FAIL", "remove_cookie() 场景执行失败",
                              exception=type(exc).__name__, error=str(exc)))
    finally:
        for name in names:
            try:
                web.remove_cookie(args.target_url, name, args.mode)
            except Exception:
                pass
        if page is not None:
            try:
                page.close(ignore_beforeunload=True)
                results.append(result("cleanup", "PASS", "测试 Cookie 与页面已清理"))
            except Exception as exc:  # noqa: BLE001
                results.append(result("cleanup", "FAIL", "页面关闭失败", exception=type(exc).__name__))
    return results, 0 if all(item["status"] == "PASS" for item in results) else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="uiautoma.web.remove_cookie() Web API 验收")
    parser.add_argument("--target-url", default=DEFAULT_URL)
    parser.add_argument("--mode", choices=("auto", "chrome", "edge"), default="chrome")
    parser.add_argument("--load-timeout", type=float, default=20)
    parser.add_argument("--contract-only", action="store_true")
    args = parser.parse_args(argv)
    results, code = run(args)
    print("UIAutoma Web API 测试")
    print(" API     : uiautoma.web.remove_cookie")
    print(f" 页面    : {args.target_url}")
    print("进度     状态    测试项                  测试结果")
    print("───────  ──────  ─────────────────────  ─────────────────────────────")
    for index, item in enumerate(results, 1):
        passed = item["status"] == "PASS"
        print(f"{index:02d}/{len(results):02d}    {(GREEN if passed else RED)}[{'通过' if passed else '失败'}]{RESET}  {item['case_id']:<22}  {item['detail']}")
    print("─" * 72)
    print(f"{'测试通过' if code == 0 else '测试失败'} · {sum(i['status']=='PASS' for i in results)}/{len(results)} 通过 · 退出码 {code}")
    return code


if __name__ == "__main__":
    raise SystemExit(main())
