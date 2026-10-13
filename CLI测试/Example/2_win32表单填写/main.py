# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
r"""读取城市选项状态，再设置单选深圳、多选仅北京和上海。

运行：uv run .\main.py
前置：UIAutoma 和 Win32 靶场已启动。脚本自动打开旁边 element 目录的元素库。
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

# 使用本会话指定的 SDK 源码，禁止在被测项目中生成 __pycache__。
sys.dont_write_bytecode = True
SDK_SOURCE = Path(r"D:\code\desktop\sdk\src")
if not (SDK_SOURCE / "uiautoma" / "__init__.py").is_file():
    raise RuntimeError(f"SDK 不存在：{SDK_SOURCE}")
sys.path.insert(0, str(SDK_SOURCE))

import uiautoma
from uiautoma import win32
from uiautoma.win32 import Win32Element, Win32Window


LIBRARY_DIR = Path(__file__).resolve().parent / "element"
CITIES = ("北京", "上海", "广州", "深圳", "杭州")
SELECTED_CITY = "深圳"
CHECKED_CITIES = {"北京", "上海"}
WINDOW_TITLE = "Win32 靶场 - UIA"
WINDOW_CLASS = "XPathWin32ShootingRange"
WINDOW_PROCESS = "win32-shooting-range-uia.exe"


def read_form(
    window: Win32Window,
) -> tuple[Win32Element, dict[str, Win32Element], dict]:
    """通过保存的选择器重新查找控件；未知、三态或范围错误直接报错。"""
    single = window.find("城市（单选）", timeout=5)
    options = single.get_all_select_items()
    selected = single.get_selected_item()
    if len(options) != len(CITIES) or set(options) != set(CITIES):
        raise RuntimeError(f"单选选项范围不正确：{options!r}")
    if len(selected) > 1 or any(city not in options for city in selected):
        raise RuntimeError(f"单选当前选中项无效：{selected!r}")

    checks = {}
    checked_states = {}
    for element in window.find_all("城市（多选）选项", timeout=5):
        attributes = element.get_all_attributes()
        name = attributes.get("Name")
        if name not in CITIES or name in checks:
            raise RuntimeError(f"多选集合包含额外或重复元素：{name!r}")
        if attributes.get("IsTogglePatternAvailable") is not True:
            raise RuntimeError(f"{name} 不支持读取 Toggle 状态")
        toggle_state = attributes.get("ToggleToggleState")
        if type(toggle_state) is not int or toggle_state not in (0, 1):
            raise RuntimeError(f"{name} 的勾选状态未知或为三态：{toggle_state!r}")
        checks[name] = element
        checked_states[name] = toggle_state == 1
    if set(checks) != set(CITIES):
        raise RuntimeError(f"多选集合选项不完整：{list(checks)!r}")

    state = {
        "城市（单选）": {
            "当前选中": selected,
            "选项状态": {city: city in selected for city in options},
        },
        "城市（多选）": {city: checked_states[city] for city in CITIES},
    }
    return single, checks, state


def main() -> None:
    if not (LIBRARY_DIR / "package.json").is_file():
        raise RuntimeError(f"元素库不存在或尚未初始化：{LIBRARY_DIR}")
    try:
        # 与网页示例一致：绑定脚本旁边的元素库，供后续 Win32 API 使用。
        uiautoma.open(str(LIBRARY_DIR))
        windows = win32.get_list(
            title=WINDOW_TITLE,
            class_name=WINDOW_CLASS,
            process_name=WINDOW_PROCESS,
            timeout=5,
        )
        targets = []
        for window in windows:
            detail = window.get_detail()
            if (
                detail.get("title") == WINDOW_TITLE
                and detail.get("class_name") == WINDOW_CLASS
                and detail.get("process_name", "").casefold() == WINDOW_PROCESS
            ):
                targets.append(window)
        if len(targets) != 1:
            raise RuntimeError(f"预期唯一的 Win32 靶场窗口，实际为 {len(targets)} 个")
        window = targets[0]

        single, checks, before = read_form(window)
        print("修改前：", flush=True)
        print(json.dumps(before, ensure_ascii=False, indent=2), flush=True)

        single.select(SELECTED_CITY, mode="exact", delay_after=0)
        for city in CITIES:
            mode = "check" if city in CHECKED_CITIES else "uncheck"
            checks[city].check(mode=mode, delay_after=0)

        # 重新查找并读取实时属性，不将动作返回值当作最终状态。
        _, _, after = read_form(window)
        print("修改后：", flush=True)
        print(json.dumps(after, ensure_ascii=False, indent=2), flush=True)
        if after["城市（单选）"]["当前选中"] != [SELECTED_CITY]:
            raise RuntimeError("单选设置后验证失败")
        expected_checks = {city: city in CHECKED_CITIES for city in CITIES}
        if after["城市（多选）"] != expected_checks:
            raise RuntimeError("多选设置后验证失败")
        print("验证通过：单选深圳，多选仅北京和上海。", flush=True)
    finally:
        # 只释放 SDK 连接，保留窗口及 Runtime 当前元素库。
        uiautoma.close()


if __name__ == "__main__":
    try:
        main()
    except (uiautoma.UIAutomaError, RuntimeError) as exc:
        print(f"执行失败：{exc}", file=sys.stderr)
        raise SystemExit(1)
