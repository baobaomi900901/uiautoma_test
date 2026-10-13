"""使用 UIAutoma SDK Web API，按元素库名称填写 iframe + Shadow 表单。

运行前请通过 build-test.py 启动 UIAutoma，并使用已安装 SDK 的 Python 环境。
完成后保留 Chrome 页面和当前元素库，便于查看填写结果。
"""

from pathlib import Path

import uiautoma
from uiautoma import web


URL = "https://baobaomi900901.github.io/xpath/#/iframe-shadow-form"
ELEMENT_LIBRARY = Path(__file__).resolve().parent / "element"
FIELDS = (
    ("文本输入框_ant", "这是_ant_输入框"),
    ("文本输入框_原生", "这是_原生_输入框"),
)


def main() -> int:
    if not (ELEMENT_LIBRARY / "package.json").is_file():
        raise FileNotFoundError(f"元素库不存在或尚未初始化：{ELEMENT_LIBRARY}")

    try:
        # 先绑定元素库，使后续 Web API 共用本次 SDK 连接。
        print(f"[1/4] 连接元素库：{ELEMENT_LIBRARY}", flush=True)
        uiautoma.open(str(ELEMENT_LIBRARY))

        print(f"[2/4] 使用 Chrome 打开靶场：{URL}", flush=True)
        page = web.create(URL, mode="chrome", load_timeout=20)

        # find 按库内名称定位，自动处理已保存的 iframe / Shadow DOM 路径。
        # 两个元素均找到且唯一后再开始填写；找不到或有多个匹配时会报错。
        elements = [(page.find(name, timeout=20), name, text) for name, text in FIELDS]
        for step, (element, name, text) in enumerate(elements, start=3):
            # 通过网页接口覆盖输入，并触发输入事件，避免中文输入法干扰。
            element.input(text, simulative=False, append=False, delay_after=0)
            actual = element.get_value()
            if actual != text:
                raise RuntimeError(f"{name} 填写失败：期望 {text!r}，实际 {actual!r}")
            print(f"[{step}/4] {name}：{actual}", flush=True)

        print("填写完成，两个输入框内容均已核对。", flush=True)
        return 0
    finally:
        # 释放 SDK 连接；浏览器页面及 Runtime 当前元素库继续保留。
        uiautoma.close()


if __name__ == "__main__":
    raise SystemExit(main())
