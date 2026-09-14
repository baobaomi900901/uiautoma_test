r"""WebElement.input() 表单双侧总入口。

用途：在 GitHub iframe/shadow 表单靶场分别运行 Ant 与原生普通文本框的 input() 测试。
API参数记录在 test_web_element_input.py 顶部；此脚本参数仅控制批量运行。
公共步骤：打开指定页面、确认动态ID开关关闭、提交按钮复制表单值、比较后点击对应重置。
脚本不会修改产品源码；每一侧子进程独立关闭浏览器并释放Package。

运行：uv run .\web\test_web_element_input_form.py
参数：--mode chrome、--profile-directory Default、--keep-running（调试时保留页面）。
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parent
RUNNER = ROOT / "test_web_element_input.py"
URL = "https://baobaomi900901.github.io/xpath/#/iframe-shadow-form"
LIBRARY = Path(r"D:\code\元素库\260902_web元素")
GREEN, RED, RESET = "\x1b[92m", "\x1b[91m", "\x1b[0m"
COMMON = (
    "--mode", "chrome",
    "--target-url", URL,
    "--element-library", str(LIBRARY),
    "--input-text", "UIAutoma_Input_01",
)


def _extract_report(stdout: str) -> dict:
    decoder = json.JSONDecoder()
    for index, char in enumerate(stdout):
        if char != "{":
            continue
        try:
            value, _ = decoder.raw_decode(stdout[index:])
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict) and "results" in value and "exit_code" in value:
            return value
    raise ValueError("子脚本未输出可解析报告")


def run_side(label: str, input_name: str, submit_name: str, reset_name: str, args) -> tuple[int, int]:
    command = [sys.executable, str(RUNNER), *COMMON,
               "--profile-directory", args.profile_directory,
               "--input-element-name", input_name,
               "--submit-element-name", submit_name,
               "--reset-element-name", reset_name]
    if args.contract_only:
        command.append("--contract-only")
    log_dir = ROOT / ".logs" / "input_form"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / f"{time.strftime('%Y%m%d-%H%M%S')}-{label}.log"
    started = time.perf_counter()
    child_env = dict(__import__("os").environ)
    child_env["PYTHONIOENCODING"] = "utf-8"
    completed = subprocess.run(command, cwd=ROOT.parent, check=False, env=child_env,
                               capture_output=True, text=True,
                               encoding="utf-8", errors="replace")
    elapsed_ms = (time.perf_counter() - started) * 1000
    log_path.write_text(completed.stdout + ("\n[stderr]\n" + completed.stderr if completed.stderr else ""), encoding="utf-8")
    try:
        report = _extract_report(completed.stdout)
        items = report.get("results", [])
        passed = sum(1 for item in items if item.get("status") == "PASS")
        ok = completed.returncode == 0 and report.get("exit_code") == 0
        status = "通过" if ok else "失败"
        print(f"{label:<6} {(GREEN if ok else RED)}[{status}]{RESET} {passed}/{len(items)} 项通过，耗时 {elapsed_ms:.1f}ms")
        for item in items:
            item_ok = item.get("status") == "PASS"
            detail = str(item.get("detail") or item.get("message") or "")
            item_status = "通过" if item_ok else "失败"
            print(f"       {(GREEN if item_ok else RED)}[{item_status}]{RESET} {item.get('case_id', '未知')}: {detail}")
        if not ok and not items:
            print("       失败项: 子脚本未返回测试项")
        print(f"       原始日志: {log_path}")
        return completed.returncode, passed
    except ValueError as exc:
        print(f"{label:<6} [失败] 无法解析子脚本报告，退出码 {completed.returncode}")
        print(f"       原因: {exc}; 原始日志: {log_path}")
        return completed.returncode or 1, 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Ant/原生 Web 表单 input() 双侧测试")
    parser.add_argument("--mode", choices=("chrome",), default="chrome", help="浏览器模式，当前固定chrome")
    parser.add_argument("--profile-directory", default="Default", help="Chrome Profile标识；传给子脚本前需为稳定Profile")
    parser.add_argument("--contract-only", action="store_true", help="两侧仅执行公开签名检查")
    args = parser.parse_args()
    if not LIBRARY.is_dir():
        print(f"元素库不存在: {LIBRARY}", file=sys.stderr)
        return 2
    if not RUNNER.is_file():
        print(f"子测试脚本不存在: {RUNNER}", file=sys.stderr)
        return 2
    sides = (
        ("Ant", "web靶场_表单测试_ant_输入框", "web靶场_表单测试_ant_按钮_提交", "web靶场_表单测试_ant_按钮_重置"),
        ("原生", "web靶场_表单测试_原生_输入框", "web靶场_表单测试_原生_按钮_提交", "web靶场_表单测试_原生_重置"),
    )
    print("UIAutoma Web API 测试")
    print(" API     : WebElement.input")
    print(f" 页面    : {URL}")
    print(f" 元素库  : {LIBRARY}")
    print(" 输出    : 按 Win32 风格显示逐项状态；完整子脚本日志另存")
    print("进度     状态    测试侧    测试结果")
    print("───────  ──────  ───────  ─────────────────────────────────────────")
    results = [run_side(*side, args) for side in sides]
    print("\n" + "─" * 72)
    total_passed = sum(passed for _, passed in results)
    total_cases = sum(1 for _code, _passed in results)
    final_code = 0 if all(code == 0 for code, _ in results) else 1
    print(f"{'测试通过' if final_code == 0 else '测试失败'} · 双侧汇总 · {total_passed} 项通过 · 退出码 {final_code}")
    return 0 if all(code == 0 for code, _ in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
