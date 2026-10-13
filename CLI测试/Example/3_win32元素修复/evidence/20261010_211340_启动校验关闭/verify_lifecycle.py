"""真实启动和关闭进程，验证成功、元素缺失和库缺失三个分支。"""
import ctypes
import hashlib
import json
import re
import shutil
import subprocess
import sys
from ctypes import wintypes
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, r"D:\code\desktop\sdk\src")
import uiautoma
from uiautoma import win32

ROOT = Path(r"D:\code\元素库\CLI测试\Example\3_win32元素修复")
EVIDENCE = Path(__file__).resolve().parent
LIBRARY = ROOT / "element"

kernel = ctypes.WinDLL("kernel32", use_last_error=True)
kernel.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
kernel.OpenProcess.restype = wintypes.HANDLE
kernel.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
kernel.WaitForSingleObject.restype = wintypes.DWORD
kernel.CloseHandle.argtypes = [wintypes.HANDLE]
kernel.CloseHandle.restype = wintypes.BOOL


def running(pid):
    handle = kernel.OpenProcess(0x00100000, False, pid)
    if not handle:
        if ctypes.get_last_error() == 87:
            return False
        raise ctypes.WinError(ctypes.get_last_error())
    try:
        result = kernel.WaitForSingleObject(handle, 0)
        if result not in (0, 258):
            raise RuntimeError(f"WaitForSingleObject returned {result}")
        return result == 258
    finally:
        kernel.CloseHandle(handle)


def library_hashes():
    return {str(p.relative_to(LIBRARY)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in LIBRARY.rglob("*") if p.is_file()}


def run_case(label, library=None):
    if library is None:
        command = [sys.executable, "-B", str(ROOT / "main.py")]
    else:
        code = (
            "import runpy; from pathlib import Path; "
            f"n=runpy.run_path({str(ROOT / 'main.py')!r}); "
            f"n['main'].__globals__['LIBRARY_DIR']=Path({str(library)!r}); "
            "raise SystemExit(n['main']())"
        )
        command = [sys.executable, "-B", "-c", code]
    result = subprocess.run(command, cwd=r"D:\code\元素库\sdk测试",
                            capture_output=True, encoding="utf-8", timeout=45)
    (EVIDENCE / f"{label}.stdout.txt").write_text(result.stdout, encoding="utf-8")
    (EVIDENCE / f"{label}.stderr.txt").write_text(result.stderr, encoding="utf-8")
    (EVIDENCE / f"{label}.command.json").write_text(
        json.dumps({"command": command, "exit_code": result.returncode},
                   ensure_ascii=False, indent=2), encoding="utf-8")
    match = re.search(r"本次启动 PID：(\d+)", result.stdout)
    assert match, result.stdout + result.stderr
    pid = int(match.group(1))
    assert not running(pid), f"Launched process {pid} was not closed"
    assert f"程序已关闭，PID：{pid}" in result.stdout
    return result, pid


before = library_hashes()
existing = [w.get_detail()["process_id"] for w in win32.get_list(
    class_name="XPathWin32ShootingRangeRandomForm", timeout=0)]
uiautoma.close()
results = {}
try:
    # 使用真实库直接运行，随机类名已变化时应停止填写并关闭新进程。
    actual, pid = run_case("actual-library")
    assert actual.returncode == 1, actual.stdout + actual.stderr
    assert "元素没有找到：姓名、城市（单选）、城市（多选），停止填写。" in actual.stdout
    assert "[4/5]" not in actual.stdout
    results["actual_library_missing_elements"] = {"passed": True, "pid": pid, "exit_code": 1}

    # 仅在测试副本中放宽随机 Pane 类名，验证元素可匹配时的完整成功分支。
    compatible = EVIDENCE / "compatible-library"
    shutil.copytree(LIBRARY, compatible)
    for path in (compatible / "snapshot").glob("*.json"):
        snapshot = json.loads(path.read_text(encoding="utf-8"))
        for layer in snapshot.get("path", []):
            kept = []
            for condition in layer.get("required", []):
                if condition.get("name") == "class_name" and str(condition.get("value", "")).startswith("XPathWin32Panel_"):
                    layer.setdefault("optional", []).append(condition)
                else:
                    kept.append(condition)
            layer["required"] = kept
        path.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2), encoding="utf-8")
    success, pid = run_case("compatible-library", compatible)
    assert success.returncode == 0, success.stdout + success.stderr
    state_text = success.stdout.split("修改后：\n", 1)[1].split("\n验证通过：", 1)[0]
    state = json.loads(state_text)
    assert state == {"姓名": "moby", "城市（单选）": ["深圳"], "城市（多选）":
                     {"北京": True, "上海": False, "广州": True, "深圳": False, "杭州": False}}
    results["compatible_fixture_success"] = {"passed": True, "pid": pid, "exit_code": 0, "values": state}

    absent, pid = run_case("missing-library", EVIDENCE / "absent-library")
    assert absent.returncode == 1, absent.stdout + absent.stderr
    assert "元素库不存在或尚未初始化" in absent.stderr
    assert "[3/5]" not in absent.stdout and "[4/5]" not in absent.stdout
    results["missing_library_cleanup"] = {"passed": True, "pid": pid, "exit_code": 1}

    assert library_hashes() == before, "Original library changed during verification"
    assert all(running(pid) for pid in existing), "An existing process was closed"
    results["original_library_unchanged"] = True
    results["existing_processes_preserved"] = existing
finally:
    # 结束临时库验证后，将 Runtime 当前库恢复为用户指定的真实库。
    try:
        uiautoma.open(str(LIBRARY))
    finally:
        uiautoma.close()

(EVIDENCE / "verification.json").write_text(
    json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps(results, ensure_ascii=False, indent=2))
