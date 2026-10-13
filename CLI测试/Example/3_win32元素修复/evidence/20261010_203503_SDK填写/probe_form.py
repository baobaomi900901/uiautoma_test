import json
import sys

sys.dont_write_bytecode = True
sys.path.insert(0, r"D:\code\desktop\sdk\src")

import uiautoma
from uiautoma import win32

try:
    uiautoma.open(r"D:\code\元素库\CLI测试\Example\3_win32元素修复\element")
    window = win32.get_by_selector("姓名", timeout=5)
    name = window.find("姓名", timeout=5)
    single = window.find("城市（单选）", timeout=5)
    checks = window.find_all("城市（多选）", timeout=5)
    result = {
        "sdk_source": uiautoma.__file__,
        "sdk_version": uiautoma.__version__,
        "window": window.get_detail(),
        "姓名": name.get_value(),
        "城市（单选）": {"options": single.get_all_select_items(), "selected": single.get_selected_item()},
        "城市（多选）": [element.get_all_attributes() for element in checks],
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
finally:
    uiautoma.close()
