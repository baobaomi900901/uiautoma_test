r"""#50 验收辅助工具：版本预检、已有自动回归、原生窗口观察、人工结果记录。

从 SDK 测试根目录运行：uv run .\issues\issue_50\test_issue_50.py --help
不修改产品源码、不拉取代码、不关闭进程、不代替人工判断界面行为。
输出保存到 --output（默认本目录 artifacts）。请每个测试版本使用独立输出目录。
"""
from __future__ import annotations

import argparse
import ctypes
from ctypes import wintypes
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parent


def now():
    return datetime.now(timezone.utc).isoformat()


def cases():
    text = (ROOT / "manual_cases.md").read_text(encoding="utf-8")
    parts = re.split(r"(?m)^### ([A-E][0-9]+) (.+)\n", text)
    return {parts[i]: (parts[i + 1], parts[i + 2].strip()) for i in range(1, len(parts), 3)}


def command(args, cwd=None, timeout=120):
    result = subprocess.run(args, cwd=cwd, capture_output=True, encoding="utf-8",
                            errors="replace", timeout=timeout)
    return {"command": args, "cwd": str(cwd) if cwd else None,
            "exit_code": result.returncode, "stdout": result.stdout, "stderr": result.stderr}


def save(directory, name, data):
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / name
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"记录：{path.resolve()}")


def repositories(config):
    data = json.loads(config.read_text(encoding="utf-8-sig"))
    result = {}
    for name in ("desktop", "rust_uia"):
        repo = data["repositories"][name]
        selection = repo.get("selection", {})
        result[name] = Path(selection.get("worktree_path") or repo["root"])
    return result


def preflight(args):
    repos = repositories(args.config)
    report = {"time": now(), "issue": 50, "repositories": {}, "checks": [],
              "scope": "源码提交包含性和运行路径；不证明运行二进制由当前 HEAD 构建"}
    for name, commits in {"desktop": ("92cd5fb", "aba9f01"),
                          "rust_uia": ("3bc16ea", "1b4744f")}.items():
        path = repos[name]
        head = command(["git", "rev-parse", "HEAD"], path)
        status = command(["git", "status", "--short"], path)
        report["repositories"][name] = {"path": str(path), "head": head, "local_changes": status}
        for commit in commits:
            check = command(["git", "merge-base", "--is-ancestor", commit, "HEAD"], path)
            passed = check["exit_code"] == 0
            report["checks"].append({"name": f"{name} 包含 {commit}", "passed": passed, "detail": check})
            print(f"[{'通过' if passed else '阻塞'}] {name} 包含 {commit}")
    ps = shutil.which("pwsh") or shutil.which("powershell")
    script = r"""
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$os = Get-CimInstance Win32_OperatingSystem
$processes = @(Get-CimInstance Win32_Process | Where-Object {
    $_.Name -match '^(UIAutoma.*|chrome|msedge|win32-shooting-range-uia)\.exe$'
} | Select-Object Name,ProcessId,ExecutablePath)
@{windows=$os.Caption; build=$os.BuildNumber; processes=$processes} | ConvertTo-Json -Depth 4
"""
    environment = command([ps, "-NoProfile", "-Command", script])
    if environment["exit_code"]:
        raise RuntimeError(environment["stderr"])
    report["environment"] = json.loads(environment["stdout"])
    processes = report["environment"]["processes"]
    for executable in ("UIAutoma.exe", "UIAutoma.UIAutomation.Provider.exe"):
        matching = [p for p in processes if p["Name"].lower() == executable.lower()]
        passed = bool(matching) and all(p.get("ExecutablePath") for p in matching)
        report["checks"].append({"name": f"运行中的 {executable}", "passed": passed})
        print(f"[{'通过' if passed else '阻塞'}] 运行中的 {executable}")
        for process in matching:
            path = Path(process["ExecutablePath"]) if process.get("ExecutablePath") else None
            if path and path.is_file():
                with path.open("rb") as binary:
                    process["sha256"] = hashlib.file_digest(binary, "sha256").hexdigest()
                print(f"  PID {process['ProcessId']}：{path}")
    save(args.output, "preflight.json", report)
    print("仍需人工填写显示器缩放、测试包构建来源；源码包含提交不等于运行版本已核实。")
    return 0 if all(c["passed"] for c in report["checks"]) else 2


def regression(args):
    repo = repositories(args.config)["desktop"]
    node = shutil.which("node")
    if not node:
        raise RuntimeError("未找到 Node.js")
    print("运行现有捕获窗口恢复/取消回归（受控测试，不是实际窗口验收）…")
    result = command([node, "--test", "tests/app/test-capture-window-restore.test.mjs"], repo, 90)
    save(args.output, "automated_regression.json", {"time": now(), **result})
    print(result["stdout"][-2500:])
    if result["stderr"]:
        print(result["stderr"][-1500:])
    return 0 if result["exit_code"] == 0 else 1


def observe(args):
    """只采集前台 HWND、菜单状态和 App 窗口样式，不激活任何窗口。"""
    user = ctypes.WinDLL("user32", use_last_error=True)
    class GUIINFO(ctypes.Structure):
        _fields_ = [("cbSize", wintypes.DWORD), ("flags", wintypes.DWORD)] + [
            (n, wintypes.HWND) for n in ("active", "focus", "capture", "menu", "move", "caret")
        ] + [("rect", wintypes.RECT)]
    user.GetForegroundWindow.restype = wintypes.HWND
    user.GetWindowTextW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
    user.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
    user.GetGUIThreadInfo.argtypes = [wintypes.DWORD, ctypes.POINTER(GUIINFO)]
    user.GetWindowLongPtrW.argtypes = [wintypes.HWND, ctypes.c_int]
    user.GetWindowLongPtrW.restype = ctypes.c_ssize_t
    user.IsIconic.argtypes = user.IsWindowVisible.argtypes = [wintypes.HWND]
    callback_type = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    user.EnumWindows.argtypes = [callback_type, wintypes.LPARAM]
    events, previous = [], None
    started = time.monotonic()
    print(f"开始观察 {args.seconds} 秒。现在切回 App 执行 {args.case}；观察器不会抢焦点。")
    try:
        while time.monotonic() - started < args.seconds:
            hwnd = user.GetForegroundWindow()
            title, pid = ctypes.create_unicode_buffer(512), wintypes.DWORD()
            user.GetWindowTextW(hwnd, title, len(title))
            user.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
            info = GUIINFO()
            info.cbSize = ctypes.sizeof(info)
            ok = bool(user.GetGUIThreadInfo(0, ctypes.byref(info)))
            windows = []
            @callback_type
            def visitor(window, unused):
                owner = wintypes.DWORD()
                user.GetWindowThreadProcessId(window, ctypes.byref(owner))
                if owner.value == args.app_pid:
                    windows.append({"hwnd": int(window), "visible": bool(user.IsWindowVisible(window)),
                                    "minimized": bool(user.IsIconic(window)),
                                    "topmost": bool(user.GetWindowLongPtrW(window, -20) & 8)})
                return True
            user.EnumWindows(visitor, 0)
            state = {"foreground_hwnd": int(hwnd or 0), "foreground_pid": pid.value,
                     "foreground_title": title.value,
                     "native_menu_flags": info.flags & 28 if ok else None,
                     "menu_owner": int(info.menu or 0) if ok else None, "app_windows": windows}
            if state != previous:
                events.append({"elapsed_ms": round((time.monotonic()-started)*1000), **state})
                previous = state
            time.sleep(0.05)
    except KeyboardInterrupt:
        pass
    tag = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    save(args.output, f"observe-{args.case}-{tag}.json", {
        "time": now(), "case": args.case, "variant": args.variant, "app_pid": args.app_pid,
        "sample_interval_ms": 50, "events": events,
        "limit": "采样可能漏过短暂事件，不自动判定用例通过；不采集截图或按键"})
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--preflight", action="store_true")
    mode.add_argument("--regression", action="store_true")
    mode.add_argument("--list", action="store_true")
    mode.add_argument("--guide", action="store_true")
    mode.add_argument("--observe", action="store_true")
    mode.add_argument("--record", action="store_true")
    mode.add_argument("--summary", action="store_true")
    parser.add_argument("--config", type=Path, default=Path(r"D:\code\.tools\build-test.config.json"))
    parser.add_argument("--output", type=Path, default=ROOT / "artifacts")
    parser.add_argument("--case", choices=tuple(cases()))
    parser.add_argument("--variant", default="", help="入口或目标变体，例如 new/recapture/Chrome")
    parser.add_argument("--seconds", type=int, default=45)
    parser.add_argument("--app-pid", type=int)
    parser.add_argument("--status", choices=("PASS", "FAIL", "BLOCKED", "NOT_RUN"))
    parser.add_argument("--note", default="")
    args = parser.parse_args()
    if (args.guide or args.observe or args.record) and not args.case:
        parser.error("本操作需要 --case")
    if args.observe and (not args.app_pid or args.app_pid <= 0 or not 1 <= args.seconds <= 600):
        parser.error("观察需要正数 --app-pid，--seconds 范围 1～600")
    if args.record and (not args.status or not args.note.strip()):
        parser.error("记录需要 --status 和描述实际表现的 --note")
    if args.preflight:
        return preflight(args)
    if args.regression:
        return regression(args)
    if args.observe:
        return observe(args)
    if args.list:
        for key, (title, _) in cases().items():
            print(f"{key}  {title}")
    elif args.guide:
        title, body = cases()[args.case]
        print(f"{args.case} {title}\n\n{body}")
    elif args.record:
        args.output.mkdir(parents=True, exist_ok=True)
        with (args.output / "manual_results.jsonl").open("a", encoding="utf-8") as f:
            f.write(json.dumps({"time": now(), "case": args.case, "variant": args.variant,
                                "status": args.status, "note": args.note}, ensure_ascii=False) + "\n")
        print("人工结果已记录（保留历次记录，不自动关闭 Issue）。")
    elif args.summary:
        path = args.output / "manual_results.jsonl"
        latest = {}
        if path.exists():
            for line in path.read_text(encoding="utf-8").splitlines():
                row = json.loads(line)
                latest[(row["case"], row["variant"])] = row
        for key, (title, _) in cases().items():
            rows = [v for (case, _), v in latest.items() if case == key]
            print(f"{key} {title}: " + ("; ".join(f"{r['variant'] or '未分变体'}={r['status']}" for r in rows) or "NOT_RUN"))
        print("此摘要不自动判定 #50 验收通过；须核对所有入口变体及开发协助项。")
    return 0


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    try:
        raise SystemExit(main())
    except (OSError, ValueError, KeyError, RuntimeError, subprocess.TimeoutExpired) as exc:
        print(f"[阻塞] {exc}")
        raise SystemExit(2)
