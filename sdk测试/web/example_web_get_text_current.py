"""最小示例：读取当前网页中指定元素的文本。

前提：Chrome 已打开目标网页，且包含该元素的 Web 元素库 Package 已处于当前会话。
示例不创建、关闭或修改网页。
"""
from uiautoma import web


page = web.get_active(mode="chrome")
target = page.find("web靶场_测试get_text_靶元素")
print(target.get_text())
