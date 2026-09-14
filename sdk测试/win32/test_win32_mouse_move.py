"""``uiautoma.win32.mouse_move()`` 合法参数冒烟测试。

API 参数（不是测试脚本参数）::

    win32.mouse_move(
        point_x: int,
        point_y: int,
        relative_to: str = "screen",
        move_speed: str | None = None,
        delay_after: float = 1,
    ) -> None

本脚本只调用 ``win32.mouse_move()``，覆盖以下合法取值：

* ``relative_to``：``screen``、``position``、``window``；
* ``move_speed``：``instant``、``fast``、``middle``、``slow``；
* ``delay_after``：``0``、``1``。

不调用其他 UIAutoma SDK API，不测试非法参数，也不恢复测试后的鼠标位置。
"""

from __future__ import annotations

import os
import sys
import time
from typing import Any

from uiautoma import win32


__test__ = False

CASES: tuple[tuple[str, tuple[int, int, str, str, int]], ...] = (
    ("屏幕慢速", (100, 100, "screen", "slow", 1)),
    ("屏幕瞬移", (150, 100, "screen", "instant", 0)),
    ("屏幕快速", (200, 100, "screen", "fast", 0)),
    ("屏幕中速", (250, 100, "screen", "middle", 0)),
    ("当前位置偏移", (20, 20, "position", "instant", 0)),
    ("活动窗口偏移", (20, 20, "window", "instant", 0)),
)

ANSI_GREEN = "\x1b[32m"
ANSI_RED = "\x1b[31m"
ANSI_CYAN = "\x1b[36m"
ANSI_RESET = "\x1b[0m"


def _color(text: str, ansi: str, *, enabled: bool) -> str:
    return f"{ansi}{text}{ANSI_RESET}" if enabled else text


def _call_text(arguments: tuple[int, int, str, str, int]) -> str:
    x, y, relative_to, move_speed, delay_after = arguments
    return (
        f'win32.mouse_move({x}, {y}, "{relative_to}", '
        f'"{move_speed}", {delay_after})'
    )


def _run_case(
    label: str,
    arguments: tuple[int, int, str, str, int],
) -> dict[str, Any]:
    started = time.perf_counter()
    try:
        result = win32.mouse_move(*arguments)
    except Exception as exc:  # noqa: BLE001
        return {
            "label": label,
            "status": "FAIL",
            "detail": "调用失败",
            "call": _call_text(arguments),
            "elapsed_ms": (time.perf_counter() - started) * 1000,
            "exception": exc.__class__.__name__,
            "message": str(exc),
        }

    return {
        "label": label,
        "status": "PASS" if result is None else "FAIL",
        "detail": "调用完成并返回 None" if result is None else "返回值不是 None",
        "call": _call_text(arguments),
        "elapsed_ms": (time.perf_counter() - started) * 1000,
        "return_value": result,
    }


def main() -> int:
    color = "NO_COLOR" not in os.environ and sys.stdout.isatty()
    print(_color("UIAutoma Win32 API 测试", ANSI_CYAN, enabled=color))
    print()
    print("  API: uiautoma.win32.mouse_move")
    print()

    started = time.perf_counter()
    results: list[dict[str, Any]] = []
    total = len(CASES)
    for index, (label, arguments) in enumerate(CASES, start=1):
        result = _run_case(label, arguments)
        results.append(result)
        passed = result["status"] == "PASS"
        badge = _color(
            "[通过]" if passed else "[失败]",
            ANSI_GREEN if passed else ANSI_RED,
            enabled=color,
        )
        print(f"[{index}/{total}] {badge} {label}")
        print(f"      调用: {result['call']}")
        print(f"      结果: {result['detail']}  {result['elapsed_ms']:.1f}ms")
        if not passed and result.get("exception"):
            print(f"      异常: {result['exception']}: {result['message']}")

    passed_count = sum(result["status"] == "PASS" for result in results)
    exit_code = 0 if passed_count == total else 1
    elapsed_ms = (time.perf_counter() - started) * 1000
    print()
    summary = "测试通过" if exit_code == 0 else "测试失败"
    summary_color = ANSI_GREEN if exit_code == 0 else ANSI_RED
    print(_color(summary, summary_color, enabled=color))
    print(f"  结果  : {passed_count}/{total} 通过")
    print(f"  总耗时: {elapsed_ms:.1f}ms")
    print(f"  退出码: {exit_code}")
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
