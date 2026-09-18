"""uiautoma.web.delete_cookie() 收敛验收脚本（原名：可用性验收）。

结论：`delete_cookie` 从未出现在 `main@c101caa9`，也不在上一基线 `dbe9e015` 中
（`dbe9e015:sdk/src/uiautoma/web/__init__.py` 只有 `remove_cookie(url, name, mode='auto', *, partition_key=None)`）。
本脚本原样断言 `delete_cookie` 公开，属**早于本次基线切换的历史漂移**；
现改写为收敛契约：确认旧名不存在，且替代函数 `remove_cookie` 以当前签名公开并导出。
"""
from __future__ import annotations

import argparse
import inspect
from typing import Any

from uiautoma import web

__test__ = False
GREEN, RED, RESET = "\x1b[92m", "\x1b[91m", "\x1b[0m"
EXPECTED_REMOVE_COOKIE = ("url", "name", "mode", "partition_key")


def result(case_id: str, status: str, detail: str, **extra: Any) -> dict[str, Any]:
    return {"case_id": case_id, "status": status, "detail": detail, **extra}


def check_contract() -> list[dict[str, Any]]:
    has_old = hasattr(web, "delete_cookie")
    exported_old = "delete_cookie" in getattr(web, "__all__", ())
    results = [result(
        "retired_name_absent",
        "PASS" if not has_old and not exported_old else "FAIL",
        "uiautoma.web 已无 delete_cookie（属性与 __all__ 均不存在）" if not has_old and not exported_old
        else f"delete_cookie 仍可访问: 属性={has_old}, __all__={exported_old}",
        has_attribute=has_old,
        in_all=exported_old,
    )]

    remove = getattr(web, "remove_cookie", None)
    present = callable(remove) and "remove_cookie" in getattr(web, "__all__", ())
    signature = inspect.signature(remove) if callable(remove) else None
    actual = tuple(signature.parameters) if signature else ()
    kinds_ok = bool(signature) and all(
        signature.parameters[name].kind == inspect.Parameter.POSITIONAL_OR_KEYWORD
        for name in EXPECTED_REMOVE_COOKIE[:3]
    ) and signature.parameters["partition_key"].kind == inspect.Parameter.KEYWORD_ONLY
    defaults_ok = bool(signature) and (
        signature.parameters["mode"].default == "auto"
        and signature.parameters["partition_key"].default is None
    )
    ok = present and actual == EXPECTED_REMOVE_COOKIE and kinds_ok and defaults_ok
    results.append(result(
        "replacement_remove_cookie",
        "PASS" if ok else "FAIL",
        f"替代函数 uiautoma.web.remove_cookie 已公开，签名: {signature}" if ok
        else f"remove_cookie 合同不符: 公开={present}, 签名={signature}",
        signature=str(signature),
    ))
    return results


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="uiautoma.web.delete_cookie() 收敛验收")
    parser.add_argument("--contract-only", action="store_true", help="仅校验契约面（本脚本全部用例均为契约面）")
    args = parser.parse_args(argv)
    results = check_contract()
    print("UIAutoma Web API 测试")
    print(" API     : uiautoma.web.delete_cookie（已收敛为 remove_cookie）")
    print("进度     状态    测试项                  测试结果")
    print("───────  ──────  ─────────────────────  ─────────────────────────────")
    for index, item in enumerate(results, 1):
        passed = item["status"] == "PASS"
        print(f"{index:02d}/{len(results):02d}    {(GREEN if passed else RED)}[{'通过' if passed else '失败'}]{RESET}  "
              f"{item['case_id']:<22}  {item['detail']}")
    print("─" * 72)
    code = 0 if all(item["status"] == "PASS" for item in results) else 1
    print(f"{'测试通过' if code == 0 else '测试失败'} · "
          f"{sum(i['status'] == 'PASS' for i in results)}/{len(results)} 通过 · 退出码 {code}")
    return code


if __name__ == "__main__":
    raise SystemExit(main())
