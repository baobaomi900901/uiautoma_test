"""Compare capture preview flags, occlusion and foreground restoration via uia.exe.

Run with Python -B. All captures use a test-owned probe library; product sources
are read only. Native Win32 calls below only read foreground and z-order.
"""
from __future__ import annotations

import ctypes
from ctypes import wintypes
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
import threading
import time
import uuid

CLI = Path(r"D:\code\desktop\cli\target\x86_64-pc-windows-msvc\release\uia.exe")
SOURCE = Path(r"D:\code\desktop")
URL = "https://baobaomi900901.github.io/xpath/#/iframe-shadow-form"
EXAMPLE = Path(r"D:\code\元素库\CLI测试\Example\1_网页表单填写\element")
OUT = Path(__file__).resolve().parent / "artifacts"
PROBE = OUT / "probe_library"
OUT.mkdir(parents=True, exist_ok=True)

user32 = ctypes.WinDLL("user32", use_last_error=True)
user32.GetForegroundWindow.restype = wintypes.HWND
user32.GetTopWindow.argtypes = [wintypes.HWND]
user32.GetTopWindow.restype = wintypes.HWND
user32.GetWindow.argtypes = [wintypes.HWND, wintypes.UINT]
user32.GetWindow.restype = wintypes.HWND
tracked: dict[str, int] = {}


def save(name, value):
    (OUT / (name + ".json")).write_text(
        json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def call(name, args, *, allow_failure=False, timeout=45):
    result = subprocess.run(
        [str(CLI), "--format", "json", *map(str, args)],
        capture_output=True, text=True, encoding="utf-8", timeout=timeout,
    )
    (OUT / (name + ".stdout.json")).write_text(result.stdout, encoding="utf-8")
    (OUT / (name + ".stderr.txt")).write_text(result.stderr, encoding="utf-8")
    payload = json.loads(result.stdout)
    with (OUT / "commands.jsonl").open("a", encoding="utf-8") as stream:
        stream.write(json.dumps({"name": name, "args": args, "exit_code": result.returncode}, ensure_ascii=False) + "\n")
    if not allow_failure and (result.returncode or not payload.get("ok")):
        raise RuntimeError(f"{name}: {payload}")
    return payload


def state():
    order, ranks, seen = [], {}, set()
    hwnd = user32.GetTopWindow(None)
    rank = 0
    while hwnd and int(hwnd) not in seen and rank < 2000:
        handle = int(hwnd)
        seen.add(handle)
        for name, target in tracked.items():
            if target == handle:
                order.append(name)
                ranks[name] = rank
        hwnd = user32.GetWindow(hwnd, 2)  # GW_HWNDNEXT; read only.
        rank += 1
    return {"foreground": int(user32.GetForegroundWindow() or 0), "tracked_order": order, "ranks": ranks}


def run_code(name, code):
    path = OUT / (name + ".js")
    path.write_text(code, encoding="utf-8")
    return call(name, ["web", "run-code", "--page", page_ref, "--file", str(path)])["data"]["result"]


METRICS = r'''async page => {
  const viewport = await page.evaluate(() => ({width:innerWidth,height:innerHeight}));
  const matches = [], scrolls = [];
  for (const [index, frame] of page.frames().entries()) {
    scrolls.push({index,url:frame.url(),...await frame.evaluate(() => ({x:scrollX,y:scrollY}))});
    const locator = frame.locator('input[id="form-controls-native-text"]');
    for (let i = 0; i < await locator.count(); i++) {
      const box = await locator.nth(i).boundingBox();
      matches.push({box, in_viewport:!!box && box.x >= 0 && box.y >= 0 && box.x+box.width <= viewport.width && box.y+box.height <= viewport.height});
    }
  }
  return {viewport,matches,scrolls};
}'''
VISIBLE = r'''async page => {
  for (const frame of page.frames()) {
    const locator = frame.locator('input[id="form-controls-native-text"]');
    if (await locator.count() === 1) await locator.evaluate(el => el.scrollIntoView({block:'center',inline:'center',behavior:'instant'}));
  }
  return true;
}'''
OFFSCREEN = r'''async page => {
  for (const frame of page.frames()) await frame.evaluate(() => window.scrollTo({top:document.documentElement.scrollHeight,behavior:'instant'}));
  return true;
}'''


def observe(name):
    obs = call(name + "-open", ["observe", "web", "open", "--page", page_ref])["data"]
    candidates = re.findall(r'textbox "请输入文本" \[ref=([^\]]+)\]', obs["snapshot"])
    try:
        for ref in candidates:
            details = call(name + "-" + ref, ["observe", "web", "details", "--session", obs["session_id"], "--snapshot", obs["snapshot_id"], "--ref", ref, "--no-highlight"])["data"]["properties"]
            if details["attributes"].get("id") == "form-controls-native-text":
                return obs, ref
        raise RuntimeError("Native text input not found in the current observation")
    except Exception:
        call(name + "-close-error", ["observe", "web", "close", "--session", obs["session_id"]])
        raise


original_hashes = {str(path): hashlib.sha256(path.read_bytes()).hexdigest() for path in EXAMPLE.rglob("*") if path.is_file()}
version = subprocess.run([str(CLI), "--version"], capture_output=True, text=True, encoding="utf-8")
assert version.returncode == 0
metadata = {"cli": str(CLI), "cli_sha256": hashlib.sha256(CLI.read_bytes()).hexdigest(), "version": version.stdout.strip(), "version_exit_code": version.returncode, "sources": {}, "cli_test_dir": r"D:\code\元素库\CLI测试", "sdk_test_dir": r"D:\code\元素库\sdk测试"}
for source in (r"D:\code\desktop", r"D:\code\rust_uia"):
    metadata["sources"][source] = {key: subprocess.check_output(["git", "-C", source, *args], text=True).strip() for key, args in [("root", ["rev-parse", "--show-toplevel"]), ("branch", ["branch", "--show-current"]), ("commit", ["rev-parse", "HEAD"])]}
save("environment", metadata)

sys.path.insert(0, str(SOURCE))
from runtime.services.package_variables import normalize_package_document
from runtime.services.state import atomic_write_json
from runtime.library.element_store import ensure_library_layout

assert not PROBE.exists(), "Use a fresh artifacts directory; never blindly replay committed captures"
PROBE.mkdir()
atomic_write_json(PROBE / "package.json", normalize_package_document({"id": str(uuid.uuid4()), "name": "截图诊断探针", "variables": []}))
ensure_library_layout(str(PROBE))
current = call("current-before", ["package", "current"])["data"]
assert current["has_current_package"] and Path(current["package_dir"]).resolve() == EXAMPLE.resolve()
pages = call("pages", ["browser", "list", "--url", URL])["data"]["items"]
pages = [page for page in pages if page["url"] == URL]
assert len(pages) == 1
page_ref = pages[0]["page_ref"]
browser_windows = call("browser-windows", ["windows", "list", "--process-name", "chrome.exe"])["data"]["items"]
browser_windows = [window for window in browser_windows if "iframe + Shadow 表单测试" in window["title"]]
occluders = call("occluder-windows", ["windows", "list", "--process-name", "UIAutoma.exe"])["data"]["items"]
assert len(browser_windows) == len(occluders) == 1
tracked = {"browser": browser_windows[0]["handle"], "occluder": occluders[0]["handle"]}
save("tracked-windows", {"browser": browser_windows[0], "occluder": occluders[0], "initial_state": state()})
original_metrics = run_code("original-metrics", METRICS)
results = []

try:
    call("probe-open", ["package", "open", "--path", str(PROBE)])
    for round_number in (1, 2):
        for kind in ("visible-no-highlight", "visible-default", "offscreen-default"):
            name = f"round-{round_number}-{kind}"
            run_code(name + "-visible-fixture", VISIBLE)
            if kind == "offscreen-default":
                run_code(name + "-offscreen-fixture", OFFSCREEN)
            metrics_before = run_code(name + "-metrics-before", METRICS)
            assert len(metrics_before["matches"]) == 1
            if kind == "offscreen-default" and metrics_before["matches"][0]["in_viewport"]:
                results.append({"name": name, "blocked": "Scroll fixture did not move input out of viewport"})
                continue
            obs, ref = observe(name)
            try:
                call(name + "-occlude", ["windows", "activate", "--hwnd", tracked["occluder"]])
                before = state()
                assert before["foreground"] == tracked["occluder"]
                assert before["tracked_order"] == ["occluder", "browser"]
                events = []
                stop = threading.Event()
                started = time.monotonic()

                def sample():
                    previous = None
                    while not stop.is_set():
                        snapshot = state()
                        if snapshot != previous:
                            events.append({"elapsed_ms": round((time.monotonic() - started) * 1000, 2), **snapshot})
                            previous = snapshot
                        stop.wait(0.01)

                sampler = threading.Thread(target=sample, daemon=True)
                sampler.start()
                try:
                    args = ["capture", "web", "--session", obs["session_id"], "--snapshot", obs["snapshot_id"], "--ref", ref, "--package", str(PROBE), "--name", name]
                    if kind == "visible-no-highlight":
                        args.append("--no-highlight")
                    capture = call(name + "-capture", args, allow_failure=True, timeout=135)
                finally:
                    stop.set()
                    sampler.join()
                after = state()
                metrics_after = run_code(name + "-metrics-after", METRICS)
                row = {"name": name, "metrics_before": metrics_before, "metrics_after": metrics_after, "before": before, "after": after, "events": events, "browser_was_foreground": any(event["foreground"] == tracked["browser"] for event in events) or after["foreground"] == tracked["browser"], "foreground_restored": after["foreground"] == before["foreground"], "pair_z_order_restored": after["tracked_order"] == before["tracked_order"], "capture": capture}
                results.append(row)
                save(name + "-telemetry", row)
                print(json.dumps({key: row[key] for key in ("name", "browser_was_foreground", "foreground_restored", "pair_z_order_restored")}, ensure_ascii=False), flush=True)
                print("capture:", json.dumps(capture, ensure_ascii=False), flush=True)
            finally:
                call(name + "-observe-close", ["observe", "web", "close", "--session", obs["session_id"]])
                call(name + "-restore-occluder", ["windows", "activate", "--hwnd", tracked["occluder"]])
            save("results", results)
finally:
    originals = json.dumps(original_metrics["scrolls"], ensure_ascii=False)
    run_code("restore-scrolls", "async page => { const originals = " + originals + "; const frames = page.frames(); for (const item of originals) { const frame = frames[item.index]; if (frame && frame.url() === item.url) await frame.evaluate(({x,y}) => window.scrollTo({left:x,top:y,behavior:'instant'}), item); } return true; }")
    call("restore-package", ["package", "open", "--path", current["package_dir"]])
    restored = call("current-after", ["package", "current"])["data"]
    assert restored == current
    final_hashes = {str(path): hashlib.sha256(path.read_bytes()).hexdigest() for path in EXAMPLE.rglob("*") if path.is_file()}
    assert final_hashes == original_hashes
    save("cleanup", {"current_package_restored": True, "original_example_unchanged": True, "tracked_state": state()})
    save("results", results)
    print("Cleanup: original package restored; original assets unchanged.", flush=True)
