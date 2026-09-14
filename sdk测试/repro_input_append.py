"""最小复现：Win32Element.input(simulative=False, append=True) 失败。"""

import uiautoma
from uiautoma import win32
from win32._form_tab import ensure_form_tab


package = uiautoma.current()
ensure_form_tab(package)
selector = package.selector("win32靶场_表单控件_输入框_姓名", kind="win")
window = win32.get(
    "Win32 靶场 - UIA",
    class_name="XPathWin32ShootingRange",
    process_name="win32-shooting-range-uia.exe",
)
element = window.find(selector, timeout=5)
original_value = element.get_value()

try:
    # 自动化覆盖输入：正常。
    element.input(
        "BASE",
        simulative=False,
        append=False,
        focus_timeout=0,
        delay_after=0,
        click_before_input=False,
    )
    print("覆盖输入成功:", element.get_value())

    # 自动化追加输入：当前版本在这里触发 DWORD_PTR 错误。
    element.input(
        "_APPEND",
        simulative=False,
        append=True,
        focus_timeout=0,
        delay_after=0,
        click_before_input=False,
    )
    print("追加输入成功:", element.get_value())

finally:
    try:
        element.input(
            original_value,
            simulative=False,
            append=False,
            focus_timeout=0,
            delay_after=0,
            click_before_input=False,
        )
        print("输入框原值已恢复")
    finally:
        package.close()
