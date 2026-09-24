"""在已打开的 iframe/Shadow 表单页观察 Ant「音乐」复选框的点击与重置。"""

import json
import shutil
import sys
import time
from pathlib import Path
from tempfile import TemporaryDirectory


PRODUCT_SDK = Path(r"D:\code\desktop\sdk\src")
LIBRARY = Path(r"D:\code\元素库\260902_web元素")
URL = "https://baobaomi900901.github.io/xpath/#/iframe-shadow-form"
TARGET_NAME = "web靶场_表单测试_ant_checkbox_input_音乐"
RESET_NAME = "web靶场_表单测试_ant_按钮_重置"
ANT_INPUT_ID = "form-controls-ant-hobbyMusic"

sys.path.insert(0, str(PRODUCT_SDK))
from uiautoma import open as open_package, web  # noqa: E402


def copy_library(source: Path, destination: Path) -> None:
    """连接临时副本，清除旧浏览器会话绑定，不修改采集的原库。"""
    shutil.copytree(source, destination)
    for path in (destination / "elements.json", *(destination / "snapshot").glob("*.json")):
        if not path.is_file():
            continue
        data = json.loads(path.read_text(encoding="utf-8"))
        pending = [data]
        while pending:
            value = pending.pop()
            if isinstance(value, dict):
                for key, child in value.items():
                    if isinstance(key, str) and "session" in key.casefold() and child:
                        value[key] = ""
                    elif key == "BrowserPid" and child:
                        value[key] = 0
                    elif isinstance(child, (dict, list)):
                        pending.append(child)
            elif isinstance(value, list):
                pending.extend(value)
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def ant_music_input(page):
    matches = page.find_all(TARGET_NAME, timeout=8)
    ids = [element.get_attribute("id") for element in matches]
    print(f"元素库匹配到 {len(matches)} 个 input：{ids}", flush=True)
    ant_matches = [element for element, element_id in zip(matches, ids) if element_id == ANT_INPUT_ID]
    if len(ant_matches) != 1:
        raise RuntimeError(f"无法唯一选出 Ant 音乐 input：{ids}")
    return ant_matches[0]


def main() -> None:
    if not PRODUCT_SDK.is_dir() or not LIBRARY.is_dir():
        raise FileNotFoundError(f"SDK 或元素库不存在：{PRODUCT_SDK}；{LIBRARY}")

    temp_root = Path(__file__).resolve().parents[1] / ".pytest_tmp"
    temp_root.mkdir(exist_ok=True)
    with TemporaryDirectory(prefix="music_click_", dir=temp_root) as temp:
        library_copy = Path(temp) / "library"
        copy_library(LIBRARY, library_copy)
        with open_package(str(library_copy), timeout=8, connect_timeout=8):
            page = web.get_active(mode="chrome", silent_running=False)
            current_url = page.get_url()
            if current_url != URL:
                raise RuntimeError(f"请先激活靶场标签页；当前页面：{current_url}")
            print(f"当前页面：{current_url}", flush=True)

            target = ant_music_input(page)
            print(f"点击前 is_checked()：{target.is_checked()}", flush=True)
            target.click(simulative=False, delay_after=0.2)
            print(f"点击后 is_checked()：{ant_music_input(page).is_checked()}", flush=True)

            print("等待 10 秒，请观察页面…", flush=True)
            time.sleep(10)
            page.find(RESET_NAME, timeout=8).click(simulative=False, delay_after=0.2)
            time.sleep(0.5)
            print(f"重置后 is_checked()：{ant_music_input(page).is_checked()}", flush=True)


if __name__ == "__main__":
    main()
