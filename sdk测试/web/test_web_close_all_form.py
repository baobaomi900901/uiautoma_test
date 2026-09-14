"""close_all() 的 Win32 风格输出入口；实际场景由既有持久化脚本执行。"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
RUNNER = ROOT / "test_web_close_all.py"
GREEN, RED, YELLOW, RESET = "\x1b[92m", "\x1b[91m", "\x1b[93m", "\x1b[0m"


def extract(text: str) -> dict:
    start = text.find("{")
    while start >= 0:
        try:
            value, _ = json.JSONDecoder().raw_decode(text[start:])
            if isinstance(value, dict) and "results" in value:
                return value
        except json.JSONDecodeError:
            pass
        start = text.find("{", start + 1)
    raise ValueError("未找到 close_all 报告")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="uiautoma.web.close_all() Web API 验收")
    parser.add_argument("--allow-close-all-pages", action="store_true", help="授权关闭当前全部 Chrome 页面")
    parser.add_argument("--contract-only", action="store_true")
    parser.add_argument("--profile-directory", default="Default")
    args = parser.parse_args(argv)
    command = [sys.executable, str(RUNNER), "--mode", "chrome", "--profile-directory", args.profile_directory]
    if args.allow_close_all_pages:
        command.append("--allow-close-all-pages")
    if args.contract_only:
        command.append("--contract-only")
    started = time.perf_counter()
    child_env = dict(os.environ)
    child_env["PYTHONIOENCODING"] = "utf-8"
    completed = subprocess.run(command, cwd=ROOT.parent, env=child_env,
                               capture_output=True, text=True,
                               encoding="utf-8", errors="replace", check=False)
    elapsed = (time.perf_counter() - started) * 1000
    try:
        report = extract(completed.stdout)
        items = report.get("results", [])
        passed = sum(item.get("status") == "PASS" for item in items)
        ok = completed.returncode == 0
        print("UIAutoma Web API 测试")
        print(" API     : uiautoma.web.close_all")
        for index, url in enumerate(report.get("target_urls", []), 1):
            print(f" 页面{index}   : {url}")
        print("进度     状态    测试项                  测试结果")
        print("───────  ──────  ─────────────────────  ─────────────────────────────")
        for index, item in enumerate(items, 1):
            status = item.get("status")
            label, color = {"PASS": ("通过", GREEN), "BLOCKED": ("阻塞", YELLOW)}.get(status, ("失败", RED))
            print(f"{index:02d}/{len(items):02d}    {color}[{label}]{RESET}  "
                  f"{item.get('case_id', '未知'):<22}  {item.get('detail', '')}")
            if status != "PASS":
                for key, field_label in (("failed_url", "失败地址"), ("exception", "异常"),
                                         ("error", "原因"), ("trace_info", "追踪")):
                    if item.get(key):
                        print(f"         {field_label}: {item[key]}")
        print("─" * 72)
        summary = "测试通过" if ok else ("测试阻塞" if completed.returncode == 2 else "测试失败")
        print(f"{summary} · {passed}/{len(items)} 通过 · {elapsed:.1f}ms · 退出码 {completed.returncode}")
        if not args.allow_close_all_pages and not args.contract_only:
            print("提示：真实关闭场景需显式添加 --allow-close-all-pages")
        return completed.returncode
    except ValueError as exc:
        print(f"{RED}[失败]{RESET} 无法解析 close_all 报告：{exc}")
        if completed.stderr:
            print(completed.stderr[-1000:])
        return completed.returncode or 1


if __name__ == "__main__":
    raise SystemExit(main())
