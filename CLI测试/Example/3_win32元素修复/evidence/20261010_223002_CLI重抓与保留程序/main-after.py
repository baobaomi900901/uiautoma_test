# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
r"""启动随机 Win32 表单，校验保存的元素，填写并验证，最后保留程序。

运行：uv run .\main.py
前置：UIAutoma 已启动，旁边 element 目录中已有三个“_修复”元素。
这些元素保留字段名称，取消每次启动都会变化的 Pane 类名必选条件。
"""

from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path

# 使用本会话确认的 SDK 源码；禁止在被测源码目录生成字节码。
sys.dont_write_bytecode = True
SDK_SOURCE = Path(r"D:\code\desktop\sdk\src")
if not (SDK_SOURCE / "uiautoma" / "__init__.py").is_file():
    raise RuntimeError(f"SDK 不存在：{SDK_SOURCE}")
sys.path.insert(0, str(SDK_SOURCE))

import uiautoma
from uiautoma import win32
from uiautoma.win32 import Win32Element, Win32Window


LIBRARY_DIR = Path(__file__).resolve().parent / "element"
APP_EXE = Path(r"D:\code\xpath\WIN32\dist\UIA 版（标准 Win32 控件_随机表单）.exe")
WINDOW_CLASS = "XPathWin32ShootingRangeRandomForm"
ELEMENT_ASSETS = {
    "姓名": "姓名_修复",
    "城市（单选）": "城市（单选）_修复",
    "城市（多选）": "城市（多选）_修复",
}
CITIES = ("北京", "上海", "广州", "深圳", "杭州")
NAME = "moby"
SINGLE_CITY = "深圳"
MULTI_CITIES = {"北京", "广州"}


def wait_for_window(process: subprocess.Popen, timeout: float = 10) -> Win32Window:
    """按启动 PID 获取窗口，避免把同名的旧窗口当作新窗口。"""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError(f"程序在窗口就绪前退出，退出码：{process.returncode}")
        for window in win32.get_list(
            class_name=WINDOW_CLASS, process_name=APP_EXE.name, timeout=0,
        ):
            if window.get_detail().get("process_id") == process.pid:
                return window
        time.sleep(0.1)
    raise RuntimeError(f"等待程序窗口超时，PID：{process.pid}")


def missing_elements(window: Win32Window) -> list[str]:
    """三个保存元素都检查完后再决定是否填写。"""
    missing = []
    for name, asset in ELEMENT_ASSETS.items():
        try:
            if name == "城市（多选）":
                found = bool(window.find_all(asset, timeout=3))
            else:
                window.find(asset, timeout=3)
                found = True
        except uiautoma.ElementNotFoundError:
            found = False
        print(f"  {name}：{'已找到' if found else '元素没有找到'}", flush=True)
        if not found:
            missing.append(name)
    return missing


def read_form(
    window: Win32Window,
) -> tuple[Win32Element, Win32Element, dict[str, Win32Element], dict]:
    """先定位全部控件并核对复选框范围，避免操作无关元素。"""
    name_field = window.find(ELEMENT_ASSETS["姓名"], timeout=5)
    single = window.find(ELEMENT_ASSETS["城市（单选）"], timeout=5)
    options = single.get_all_select_items()
    if len(options) != len(CITIES) or set(options) != set(CITIES):
        raise RuntimeError(f"单选城市选项范围不正确：{options!r}")

    checks: dict[str, Win32Element] = {}
    checked: dict[str, bool] = {}
    for element in window.find_all(ELEMENT_ASSETS["城市（多选）"], timeout=5):
        attributes = element.get_all_attributes()
        city = attributes.get("Name")
        if city not in CITIES or city in checks:
            raise RuntimeError(f"多选集合包含额外或重复元素：{city!r}")
        state = attributes.get("ToggleToggleState")
        if attributes.get("IsTogglePatternAvailable") is not True:
            raise RuntimeError(f"{city} 不支持读取勾选状态")
        if type(state) is not int or state not in (0, 1):
            raise RuntimeError(f"{city} 的勾选状态未知或为三态：{state!r}")
        checks[city] = element
        checked[city] = state == 1
    if set(checks) != set(CITIES):
        raise RuntimeError(f"多选城市选项不完整：{list(checks)!r}")

    values = {
        "姓名": name_field.get_value(),
        "城市（单选）": single.get_selected_item(),
        "城市（多选）": {city: checked[city] for city in CITIES},
    }
    return name_field, single, checks, values


def main() -> int:
    process = None
    window = None
    try:
        print(f"[1/5] 打开程序：{APP_EXE}", flush=True)
        if not APP_EXE.is_file():
            raise RuntimeError(f"程序不存在：{APP_EXE}")
        process = subprocess.Popen([str(APP_EXE)], cwd=str(Path(__file__).resolve().parent))
        print(f"  本次启动 PID：{process.pid}", flush=True)

        print(f"[2/5] 连接元素库：{LIBRARY_DIR}", flush=True)
        if not (LIBRARY_DIR / "package.json").is_file():
            raise RuntimeError(f"元素库不存在或尚未初始化：{LIBRARY_DIR}")
        uiautoma.open(str(LIBRARY_DIR))
        window = wait_for_window(process)

        print("[3/5] 校验元素是否存在", flush=True)
        missing = missing_elements(window)
        if missing:
            print(f"元素没有找到：{'、'.join(missing)}，停止填写。", flush=True)
            return 1

        print("[4/5] 填写表单", flush=True)
        name_field, single, checks, before = read_form(window)
        print("修改前：", flush=True)
        print(json.dumps(before, ensure_ascii=False, indent=2), flush=True)

        name_field.input(
            NAME, simulative=False, append=False,
            click_before_input=False, focus_timeout=0, delay_after=0,
        )
        single.select(SINGLE_CITY, mode="exact", delay_after=0)
        for city in CITIES:
            mode = "check" if city in MULTI_CITIES else "uncheck"
            checks[city].check(mode=mode, delay_after=0)

        # 重新通过保存的选择器定位，读取实时值验证最终结果。
        _, _, _, after = read_form(window)
        print("修改后：", flush=True)
        print(json.dumps(after, ensure_ascii=False, indent=2), flush=True)
        expected = {
            "姓名": NAME,
            "城市（单选）": [SINGLE_CITY],
            "城市（多选）": {city: city in MULTI_CITIES for city in CITIES},
        }
        if after != expected:
            raise RuntimeError(f"填写后验证失败：期望 {expected!r}，实际 {after!r}")
        print("验证通过：姓名 moby，单选深圳，多选仅北京和广州。", flush=True)
        return 0
    finally:
        # 断开 SDK 客户端，不关闭或结束目标进程；失败时也保留窗口供检查。
        uiautoma.close()
        if process is not None and process.poll() is None:
            print("[5/5] 保留本次启动的程序", flush=True)
            print(f"  程序保持打开，PID：{process.pid}", flush=True)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (uiautoma.UIAutomaError, RuntimeError, OSError, subprocess.SubprocessError) as exc:
        print(f"执行失败：{exc}", file=sys.stderr)
        raise SystemExit(1)
