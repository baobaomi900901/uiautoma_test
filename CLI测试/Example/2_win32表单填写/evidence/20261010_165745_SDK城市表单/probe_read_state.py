import json
import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, r"D:\code\desktop\sdk\src")
import uiautoma
from uiautoma import package, win32

with uiautoma.current(required=True) as pkg:
    print(json.dumps({"sdk_version": uiautoma.__version__, "sdk_file": uiautoma.__file__, "package_dir": pkg.package_dir}, ensure_ascii=False))
    if Path(pkg.package_dir).resolve() != Path(__file__).resolve().parents[2]:
        raise RuntimeError("当前元素库不是本示例库")
    window = win32.get(title="Win32 靶场 - UIA", class_name="XPathWin32ShootingRange", process_name="win32-shooting-range-uia.exe", timeout=5)
    print(json.dumps({"window": window.get_detail()}, ensure_ascii=False))
    single = window.find(package.selector("城市（单选）", kind="win"), timeout=5)
    print(json.dumps({"single_options": single.get_all_select_items(), "single_selected": single.get_selected_item()}, ensure_ascii=False))
    checks = window.find_all(package.selector("城市（多选）选项", kind="win"), timeout=5)
    for element in checks:
        attrs = element.get_all_attributes()
        state_attrs = {key: value for key, value in attrs.items() if any(fragment in key.casefold() for fragment in ("toggle", "legacyiaccessible", "selected"))}
        print(json.dumps({"text": element.get_text(), "attribute_name": element.get_attribute("Name"), "toggle_state": element.get_attribute("ToggleToggleState"), "attributes": state_attrs}, ensure_ascii=False))
