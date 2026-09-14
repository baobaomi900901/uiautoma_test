"""uiautoma.web.delete_cookie() 可用性验收脚本。

先确认公开 API 是否存在；若源码未导出，则明确报告 API 缺失，不启动浏览器。
"""
from __future__ import annotations

import argparse
import inspect
import sys
from pathlib import Path

PRODUCT_ROOT = Path(__file__).resolve().parents[3]
SDK_SRC = PRODUCT_ROOT / "sdk" / "src"
if str(SDK_SRC) not in sys.path:
    sys.path.insert(0, str(SDK_SRC))

from uiautoma import web  # noqa: E402

__test__ = False
GREEN, RED, RESET = "\x1b[92m", "\x1b[91m", "\x1b[0m"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="uiautoma.web.delete_cookie() 可用性验收")
    parser.add_argument("--contract-only", action="store_true")
    parser.parse_args(argv)
    exists = hasattr(web, "delete_cookie") and callable(getattr(web, "delete_cookie", None))
    exported = "delete_cookie" in getattr(web, "__all__", ())
    print("UIAutoma Web API 测试")
    print(" API     : uiautoma.web.delete_cookie")
    print("进度     状态    测试项                  测试结果")
    print("───────  ──────  ─────────────────────  ─────────────────────────────")
    if exists and exported:
        signature = inspect.signature(web.delete_cookie)
        print(f"01/01    {GREEN}[通过]{RESET}  api_contract            API 已公开，签名: {signature}")
        print("─" * 72)
        print("测试通过 · 1/1 通过 · 退出码 0")
        return 0
    print(f"01/01    {RED}[失败]{RESET}  api_contract            delete_cookie 未在 uiautoma.web 公开")
    print(f"         exists={exists}；__all__导出={exported}")
    print("─" * 72)
    print("测试失败 · 0/1 通过 · 退出码 1")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
