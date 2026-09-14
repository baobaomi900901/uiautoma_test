r"""表单相关的已通过 Win32 SDK 回归入口。

从测试根目录运行：
    uv run .\win32\test_win32_form_regression.py --non-interactive

脚本按顺序启动独立测试并保存输出；列表不包含当前已知缺陷或会真实关闭靶场的测试。
每个子测试使用相同的 UIAutoma dev/元素库环境；失败时继续执行后续项目。
"""

from __future__ import annotations

import argparse
import subprocess
import sys
import time
from pathlib import Path


TESTS = [
    "test_win32_parent.py",
    "test_win32_children.py",
    "test_win32_find_related_element.py",
    "test_win32_get_value.py",
    "test_win32_get_text.py",
    "test_win32_get_attribute.py",
    "test_win32_get_all_attributes.py",
    "test_win32_element_properties.py",
    "test_win32_get_bounding.py",
    "test_win32_clipboard_input.py",
    "test_win32_select.py",
    "test_win32_select_by_index.py",
    "test_win32_get_all_select_items.py",
    "test_win32_get_selected_item.py",
    "test_win32_click.py",
    "test_win32_dblclick.py",
]


def main() -> int:
    parser = argparse.ArgumentParser(description="表单相关 Win32 SDK 回归入口")
    parser.add_argument("--non-interactive", action="store_true", help="兼容批量测试命令；子测试按自身规则运行")
    parser.add_argument("--timeout", type=float, default=180, help="每个子测试最长秒数，默认180")
    args = parser.parse_args()

    root = Path(__file__).resolve().parent
    log_dir = root.parent / ".logs" / "form-regression"
    log_dir.mkdir(parents=True, exist_ok=True)
    results: list[tuple[str, int, float, Path]] = []
    print(f"表单 Win32 SDK 回归：{len(TESTS)} 个测试")
    print(f"日志目录：{log_dir}")

    for index, name in enumerate(TESTS, start=1):
        script = root / name
        log_path = log_dir / f"{index:02d}-{script.stem}.log"
        started = time.perf_counter()
        print(f"[{index:02d}/{len(TESTS):02d}] {name}", flush=True)
        if not script.is_file():
            log_path.write_text(f"脚本不存在：{script}\n", encoding="utf-8")
            results.append((name, 2, 0.0, log_path))
            print("  阻塞：脚本不存在", flush=True)
            continue
        try:
            completed = subprocess.run(
                [sys.executable, str(script)],
                cwd=root.parent,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=args.timeout,
            )
            log_path.write_text(completed.stdout or "", encoding="utf-8")
            code = completed.returncode
        except subprocess.TimeoutExpired as exc:
            output = exc.stdout or ""
            log_path.write_text(str(output) + f"\n超时：{args.timeout}s\n", encoding="utf-8")
            code = 124
        elapsed = time.perf_counter() - started
        results.append((name, code, elapsed, log_path))
        print(f"  {'通过' if code == 0 else '失败'}：退出码 {code}，{elapsed:.1f}s", flush=True)

    passed = sum(code == 0 for _, code, _, _ in results)
    print("\n回归汇总")
    for name, code, elapsed, log_path in results:
        print(f"  [{'通过' if code == 0 else '失败'}] {name}: {code} ({elapsed:.1f}s) -> {log_path}")
    print(f"结果：{passed}/{len(results)} 通过")
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
