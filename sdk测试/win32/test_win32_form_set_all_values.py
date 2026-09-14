r"""表单页控件批量赋值/状态测试。

运行：uv run .\win32\test_win32_form_set_all_values.py --non-interactive

分类：
* 文本框、密码、邮箱、年龄、文本域 -> set_value()
* 下拉框 -> select()
* 复选/单选 -> check("check")
* 面板、标题、Tab、保存/重置按钮没有可设置值，记录为SKIP，不点击保存。

测试结束点击表单重置按钮恢复靶场状态。脚本逐项继续执行并汇总失败；不提交表单。
"""

from __future__ import annotations

import argparse
import time
from pathlib import Path

import uiautoma
from uiautoma import win32
from uiautoma.win32 import Win32Element
from _form_tab import ensure_form_tab


LIBRARY = Path(r"D:\code\元素库\260902_win元素")
TARGET_TITLE = "Win32 靶场 - UIA"
TARGET_PROCESS = "win32-shooting-range-uia.exe"

TEXT_VALUES = {
    "win32靶场_表单控件_输入框_姓名": "UIAutoma_姓名_测试",
    "win32靶场_表单控件_密码_输入框": "P@ssw0rd_测试",
    "win32靶场_表单控件_邮箱_输入框": "uiautoma@example.com",
    "win32靶场_表单控件_输入框_年龄": "28",
    "win32靶场_表单控件_文本域_备注": "表单批量赋值测试\r\n第二行",
}
SELECT_VALUE = ("win32靶场_表单控件_下拉框_城市", "深圳")
CHECK_VALUES = [
    "win32靶场_表单控件_多选_北京",
    "win32靶场_表单控件_多选_上海",
    "win32靶场_表单控件_多选_广州",
    "win32靶场_表单控件_多选_深圳",
    "win32靶场_表单控件_多选_杭州",
    "win32靶场_表单控件_多选_阅读",
    "win32靶场_表单控件_多选_运动",
    "win32靶场_表单控件_多选_音乐",
    "win32靶场_表单控件_多选_旅行",
    "win32靶场_表单控件_多选_同意用户协议",
    "win32靶场_表单控件_单选_男",
]
SKIPPED = [
    "win32靶场_表单控件_按钮_保存",
    "win32靶场_表单控件_按钮_重置",
    "win32靶场_表单控件_表单面板",
    "win32靶场_表单控件_标题",
    "win32靶场_tab_item表单控件",
]


def main() -> int:
    parser = argparse.ArgumentParser(description="表单控件批量赋值测试")
    parser.add_argument("--non-interactive", action="store_true")
    parser.parse_args()

    print("UIAutoma Win32 表单控件批量赋值")
    print(f"元素库: {LIBRARY}")
    print("规则: 文本 set_value；下拉 select；复选/单选 check；按钮和容器跳过")
    package = None
    window = None
    failures: list[str] = []
    passed = 0
    attempted = 0
    started = time.perf_counter()

    try:
        package = uiautoma.current(required=True, refresh=True, timeout=5)
        if Path(package.package_dir).resolve() != LIBRARY.resolve():
            raise RuntimeError(f"当前元素库不符：{package.package_dir}")
        ensure_form_tab(package)
        window = win32.get(title=TARGET_TITLE, process_name=TARGET_PROCESS, timeout=5)

        def find(name: str) -> Win32Element:
            element = window.find(package.selector(name, kind="win"), timeout=5)
            if not isinstance(element, Win32Element):
                raise TypeError(f"{name} 未返回 Win32Element")
            return element

        for name, value in TEXT_VALUES.items():
            attempted += 1
            try:
                find(name).set_value(value)
                passed += 1
                print(f"[通过] set_value  {name} <- {value!r}")
            except Exception as exc:
                failures.append(f"{name}: {type(exc).__name__}: {exc}")
                print(f"[失败] set_value  {name}: {exc}")

        name, value = SELECT_VALUE
        attempted += 1
        try:
            find(name).select(value, mode="exact", delay_after=0)
            passed += 1
            print(f"[通过] select     {name} <- {value!r}")
        except Exception as exc:
            failures.append(f"{name}: {type(exc).__name__}: {exc}")
            print(f"[失败] select     {name}: {exc}")

        for name in CHECK_VALUES:
            attempted += 1
            try:
                find(name).check("check", delay_after=0)
                passed += 1
                print(f"[通过] check      {name}")
            except Exception as exc:
                failures.append(f"{name}: {type(exc).__name__}: {exc}")
                print(f"[失败] check      {name}: {exc}")

        for name in SKIPPED:
            print(f"[跳过] 无可设置值  {name}")
    except Exception as exc:
        failures.append(f"准备失败: {type(exc).__name__}: {exc}")
        print(f"[失败] 准备: {exc}")
    finally:
        if window is not None and package is not None:
            try:
                window.find(package.selector("win32靶场_表单控件_按钮_重置", kind="win"), timeout=5).click(
                    simulative=False, delay_after=0.2, move_mouse=False
                )
                print("[清理] 已点击表单重置按钮")
            except Exception as exc:
                failures.append(f"重置失败: {type(exc).__name__}: {exc}")
                print(f"[失败] 重置: {exc}")
        if package is not None:
            try:
                package.close()
            except Exception as exc:
                failures.append(f"Package关闭失败: {type(exc).__name__}: {exc}")
        elapsed = (time.perf_counter() - started) * 1000
        print("\n汇总")
        print(f"  已执行: {attempted}")
        print(f"  通过  : {passed}/{attempted}")
        print(f"  跳过  : {len(SKIPPED)}（无可设置值或不执行按钮动作）")
        print(f"  总耗时: {elapsed:.1f}ms")
        if failures:
            print("  失败项:")
            for failure in failures:
                print(f"    - {failure}")
        print(f"  退出码: {1 if failures else 0}")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
