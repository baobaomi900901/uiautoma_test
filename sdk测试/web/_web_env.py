"""Web 通道的环境前置检查与诊断（WebElement 读写验收脚本共用）。

两个设计约束：

1. **标签数只作诊断。** 早期版本在 `run()` 最外层直接调用标签数统计，一旦浏览器通道不可用，
   整个脚本会抛 traceback 而不是给出结论。标签数本来就是「仅作诊断」的信息，不得让主流程失败。
2. **环境不具备要干净地报阻塞。** 运行时一次连着多个 Chrome 用户环境/插件时，Runtime 会拒绝
   所有 `web.*` 调用（trace `web_environment_ambiguous`），`get_all` 与 `create` 都不可用。
   这时按产品提示固定目标用户环境即可继续；无法固定时记 `BLOCKED`（退出码 2），不记产品缺陷。

固定用户环境是**进程内**状态：SDK 把它存在 `client._web_environments`，随后每次 `web.*` 调用
以 `user_environments` 参数发出，进程结束时自然消失，不会改变其他 SDK 会话的默认环境。
"""
from __future__ import annotations

import json
import os
import re
from pathlib import Path

from uiautoma import web

__all__ = [
    "ENV_TRACES",
    "chrome_user_data_dir",
    "check_web_channel",
    "list_chrome_profiles",
    "pin_environment",
    "safe_tab_count",
]

PROFILE_KEY_RE = re.compile(r"Profile \d+|[a-zA-Z0-9]+")

# 表示「环境不具备」而非产品缺陷的 trace
ENV_TRACES = {
    "web_environment_ambiguous",
    "web_environment_unavailable",
    "web_environment_window_not_open",
    "native_host_unavailable",
    "plugin_not_connected",
    "web_bridge_unavailable",
    "web_session_unavailable",
    "browser_session_disconnected",
    "browser_session_discovery_failed",
    "browser_executable_not_found",
    "browser_launch_timeout",
}


def _trace(exc: BaseException) -> str:
    return str(getattr(exc, "trace_info", "") or "")


def safe_tab_count(mode: str = "chrome") -> int | None:
    """当前标签数；仅作诊断。任何失败都返回 ``None``，绝不抛异常。"""
    try:
        return len(web.get_all(mode=mode))
    except Exception:  # noqa: BLE001 - 诊断信息失败不应影响主流程
        return None


def chrome_user_data_dir(override: str | os.PathLike[str] | None = None) -> Path:
    """Chrome 用户数据目录；默认取 ``%LOCALAPPDATA%\\Google\\Chrome\\User Data``。"""
    if override:
        return Path(override).expanduser().resolve()
    local = os.environ.get("LOCALAPPDATA", "")
    return (Path(local) / "Google" / "Chrome" / "User Data").resolve()


def list_chrome_profiles(
    user_data_dir: str | os.PathLike[str] | None = None,
) -> tuple[list[str], str]:
    """只读 Chrome ``Local State``，列出可选用户环境。

    返回 ``(可读展示列表, 错误文本)``；只读文件，不修改 Profile。
    """
    root = chrome_user_data_dir(user_data_dir)
    try:
        payload = json.loads((root / "Local State").read_text(encoding="utf-8"))
        cache = payload["profile"]["info_cache"]
        if not isinstance(cache, dict):
            raise ValueError("profile.info_cache 不是对象")
    except Exception as exc:  # noqa: BLE001
        return [], f"{type(exc).__name__}: {exc}"
    items: list[tuple[str, str]] = []
    for directory, metadata in cache.items():
        if not PROFILE_KEY_RE.fullmatch(str(directory)):
            continue
        metadata = metadata if isinstance(metadata, dict) else {}
        shown = str(metadata.get("shortcut_name") or metadata.get("name") or directory)
        items.append((str(directory), shown))
    items.sort(key=lambda pair: (pair[0] != "Default", pair[0]))
    return [f"{d}（{n}）" if n != d else d for d, n in items], ""


def pin_environment(
    mode: str,
    profile_name: str | None = None,
    user_data_dir: str | os.PathLike[str] | None = None,
) -> tuple[bool, str]:
    """按产品提示固定目标用户环境。返回 ``(是否成功, 说明)``，不抛异常。"""
    try:
        if user_data_dir:
            web.set_user_environment(
                mode,
                profile_name=profile_name,
                specifield_userdata=True,
                user_data_dir=str(user_data_dir),
            )
        else:
            web.set_user_environment(mode, profile_name=profile_name)
    except Exception as exc:  # noqa: BLE001
        trace = _trace(exc)
        return False, f"{type(exc).__name__}: {exc}" + (f" [trace={trace}]" if trace else "")
    target = profile_name or (str(user_data_dir) if user_data_dir else "默认环境")
    return True, f"已固定用户环境 {target}"


def check_web_channel(mode: str = "chrome") -> dict:
    """探测浏览器通道是否可用。返回结构化结论，不抛异常。

    ``{"ok": bool, "trace": str, "message": str, "exception": str, "tabs": int | None}``
    """
    try:
        pages = web.get_all(mode=mode)
    except Exception as exc:  # noqa: BLE001
        return {
            "ok": False,
            "trace": _trace(exc),
            "message": str(exc),
            "exception": type(exc).__name__,
            "tabs": None,
        }
    return {"ok": True, "trace": "", "message": "", "exception": "", "tabs": len(pages)}
