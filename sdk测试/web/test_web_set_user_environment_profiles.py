"""set_user_environment() Chrome Profile 全量验收脚本。

只读取 Chrome Local State 中的 Profile 配置；逐个选择 Profile、打开百度、关闭本次标签页，
最后恢复原浏览器环境。不会关闭用户已有标签页，也不写入 Profile 文件。
"""
from __future__ import annotations

import argparse
import inspect
import json
import os
import re
import sys
import time
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

PRODUCT_ROOT = Path(__file__).resolve().parents[3]
SDK_SRC = PRODUCT_ROOT / "sdk" / "src"
if str(SDK_SRC) not in sys.path:
    sys.path.insert(0, str(SDK_SRC))

import uiautoma  # noqa: E402
from uiautoma import web  # noqa: E402
from uiautoma.web import WebBrowser  # noqa: E402

__test__ = False
BAIDU_URL = "https://www.baidu.com/"
PROFILE_KEY_RE = re.compile(r"Profile \d+|[a-zA-Z0-9]+")
GREEN, RED, YELLOW, RESET = "\x1b[92m", "\x1b[91m", "\x1b[93m", "\x1b[0m"


def item(case_id: str, status: str, detail: str, **extra: Any) -> dict[str, Any]:
    return {"case_id": case_id, "status": status, "detail": detail, **extra}


def check_contract() -> dict[str, Any]:
    set_sig = inspect.signature(web.set_user_environment)
    reset_sig = inspect.signature(web.reset_user_environment)
    expected = ("mode", "profile_name", "specifield_userdata", "user_data_dir")
    if tuple(set_sig.parameters) != expected:
        return item("api_contract", "FAIL", f"set_user_environment 签名不符: {set_sig}")
    if tuple(reset_sig.parameters) != ("mode",):
        return item("api_contract", "FAIL", f"reset_user_environment 签名不符: {reset_sig}")
    if any(p.kind != inspect.Parameter.POSITIONAL_OR_KEYWORD for p in set_sig.parameters.values()):
        return item("api_contract", "FAIL", "set_user_environment 参数位置规则不符")
    if set_sig.parameters["specifield_userdata"].default is not False:
        return item("api_contract", "FAIL", "specifield_userdata 默认值不符")
    return item("api_contract", "PASS", "set/reset 公开签名和默认值符合当前源码")


def chrome_user_data_dir(override: Path | None) -> Path:
    if override is not None:
        return override.expanduser().resolve()
    local = os.environ.get("LOCALAPPDATA", "")
    return (Path(local) / "Google" / "Chrome" / "User Data").resolve()


def read_profiles(root: Path) -> tuple[list[dict[str, Any]], str | None]:
    state_file = root / "Local State"
    try:
        payload = json.loads(state_file.read_text(encoding="utf-8"))
        cache = payload["profile"]["info_cache"]
        if not isinstance(cache, dict):
            raise ValueError("profile.info_cache 不是对象")
        profiles = []
        for directory, metadata in cache.items():
            if not PROFILE_KEY_RE.fullmatch(str(directory)):
                continue
            metadata = metadata if isinstance(metadata, dict) else {}
            profiles.append({
                "directory": str(directory),
                "display_name": str(metadata.get("shortcut_name") or metadata.get("name") or directory),
                "directory_exists": (root / str(directory)).is_dir(),
            })
        profiles.sort(key=lambda p: (p["directory"] != "Default", p["directory"]))
        return profiles, None
    except Exception as exc:  # noqa: BLE001
        return [], f"{type(exc).__name__}: {exc}"


def is_baidu(url: str) -> bool:
    try:
        host = (urlsplit(url).hostname or "").casefold()
    except ValueError:
        return False
    return host == "baidu.com" or host.endswith(".baidu.com")


def run(args: argparse.Namespace) -> tuple[list[dict[str, Any]], int]:
    results = [check_contract()]
    if results[-1]["status"] != "PASS":
        return results, 1
    root = chrome_user_data_dir(args.chrome_user_data_dir)
    profiles, error = read_profiles(root)
    if error:
        results.append(item("profile_query", "BLOCKED", "无法读取 Chrome Profile 配置", root=str(root), error=error))
        return results, 2
    if not profiles:
        results.append(item("profile_query", "FAIL", "Local State 中没有可测试的 Chrome Profile", root=str(root)))
        return results, 1
    profile_summary = "、".join(f"{p['directory']}（{p['display_name']}）" for p in profiles)
    results.append(item("profile_query", "PASS", f"查询到 {len(profiles)} 个 Chrome Profile：{profile_summary}",
                        root=str(root), profile_count=len(profiles), profiles=profiles))
    pages: list[WebBrowser] = []
    try:
        for profile in profiles:
            name = profile["directory"]
            started = time.perf_counter()
            page: WebBrowser | None = None
            try:
                if not profile["directory_exists"]:
                    results.append(item(f"profile_{name}", "BLOCKED", f"Profile={name}；显示名={profile['display_name']}；目录不存在，跳过打开百度",
                                        profile=name, display_name=profile["display_name"]))
                    continue
                returned = web.set_user_environment(args.mode, name)
                if returned is not None:
                    raise RuntimeError("set_user_environment 返回值不是 None")
                page = web.create(BAIDU_URL, mode=args.mode, load_timeout=args.load_timeout)
                pages.append(page)
                if not isinstance(page, WebBrowser):
                    raise RuntimeError(f"web.create 返回类型错误: {type(page).__name__}")
                current_url = page.get_url()
                if not is_baidu(current_url):
                    raise RuntimeError(f"当前 URL 不是百度: {current_url}")
                results.append(item(f"profile_{name}", "PASS", f"Profile={name}；显示名={profile['display_name']}；已打开百度并核对 URL",
                                    profile=name, display_name=profile["display_name"],
                                    url=current_url, elapsed_ms=round((time.perf_counter() - started) * 1000, 1)))
            except Exception as exc:  # noqa: BLE001
                trace = str(getattr(exc, "trace_info", "") or getattr(exc, "error_code", "") or "")
                expected_unavailable = (not args.strict_profile_availability
                                        and type(exc).__name__ == "UIAError"
                                        and trace == "web_environment_unavailable")
                results.append(item(f"profile_{name}", "PASS" if expected_unavailable else "FAIL",
                                    f"Profile={name}；显示名={profile['display_name']}；"
                                    + ("插件未连接，符合预期环境状态，跳过百度打开"
                                       if expected_unavailable else f"打开百度失败: {type(exc).__name__}: {exc}"),
                                    profile=name, display_name=profile["display_name"], trace_info=trace,
                                    expected_environment_block=expected_unavailable,
                                    elapsed_ms=round((time.perf_counter() - started) * 1000, 1)))
            finally:
                if page is not None:
                    try:
                        page.close(ignore_beforeunload=True)
                    except Exception as exc:  # noqa: BLE001
                        results.append(item(f"profile_{name}_cleanup", "FAIL", f"标签页关闭失败: {type(exc).__name__}: {exc}"))
        try:
            web.reset_user_environment(args.mode)
            results.append(item("environment_reset", "PASS", "已恢复原浏览器环境选择"))
        except Exception as exc:  # noqa: BLE001
            results.append(item("environment_reset", "FAIL", f"环境恢复失败: {type(exc).__name__}: {exc}"))
    finally:
        # 仅在异常中断且仍有引用时尝试关闭自己创建的页面；不操作用户已有页面。
        for page in pages:
            try:
                page.close(ignore_beforeunload=True)
            except Exception:
                pass
    blocked = any(r["status"] == "BLOCKED" for r in results)
    return results, 0 if all(r["status"] == "PASS" for r in results) else (2 if blocked else 1)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="逐个 Chrome Profile 打开百度并恢复环境")
    parser.add_argument("--mode", choices=("chrome",), default="chrome")
    parser.add_argument("--chrome-user-data-dir", type=Path, default=None,
                        help="可选：覆盖 Chrome User Data 根目录")
    parser.add_argument("--load-timeout", type=float, default=20)
    parser.add_argument("--contract-only", action="store_true")
    parser.add_argument("--strict-profile-availability", action="store_true",
                        help="严格要求每个 Profile 插件可用；默认将 web_environment_unavailable 视为预期环境状态")
    args = parser.parse_args(argv)
    if args.load_timeout <= 0:
        parser.error("--load-timeout 必须大于 0")
    print("UIAutoma Web API 测试")
    print(" API     : uiautoma.web.set_user_environment")
    print(" 范围    : 读取 Chrome Profile；每个 Profile 打开一次 https://www.baidu.com/；不修改 Profile 文件")
    results, code = run(args) if not args.contract_only else ([check_contract()], 0)
    print("进度     状态    测试项                  测试结果")
    print("───────  ──────  ─────────────────────  ─────────────────────────────")
    for index, current in enumerate(results, 1):
        status = current["status"]
        color = {"PASS": GREEN, "BLOCKED": YELLOW}.get(status, RED)
        label = {"PASS": "通过", "BLOCKED": "阻塞"}.get(status, "失败")
        print(f"{index:02d}/{len(results):02d}    {color}[{label}]{RESET}  {current['case_id']:<22}  {current['detail']}")
    passed = sum(r["status"] == "PASS" for r in results)
    print("─" * 72)
    print(f"{'测试通过' if code == 0 else ('测试阻塞' if code == 2 else '测试失败')} · {passed}/{len(results)} 通过 · 退出码 {code}")
    return code


if __name__ == "__main__":
    raise SystemExit(main())
