# `uiautoma.web.auto_handle_popup()`

注册自动点击网页 DOM 弹窗关闭按钮的规则。

## 签名

```python
web.auto_handle_popup(
    handle_method: str,
    close_button=None,
    element_selector=None,
    process: str | None = None,
    package=None,
) -> None
```

## 参数与返回

| 参数 | 说明 |
|---|---|
| `handle_method` | 使用 `"close_dialog"`。`"execute_process"` 当前不支持。 |
| `close_button` | 已保存的关闭按钮元素名称，或指向该库元素的 Web Selector；默认 None，使用 close_dialog 时必须提供。 |
| `element_selector` | 默认 None，当前 close_dialog 路径不使用。 |
| `process` | 默认 None，当前 close_dialog 路径不使用。 |
| `package` | 默认 None，当前 close_dialog 路径不使用；应事先打开包含关闭按钮的元素库。 |

成功注册返回 `None`。关闭动作在后台异步执行；返回并不表示弹窗已经关闭。

## 使用顺序

1. 在 App 中保存弹窗的关闭按钮，确认选择器只定位到一个关闭按钮。
2. 用 `uiautoma.open()` 连接包含该按钮的元素库。
3. 注册规则。
4. 注册后通过 `web.get()` 获取页面，或通过 `web.create()` 创建页面。
5. 触发弹窗。后台发现唯一、可见的关闭按钮时自动点击。

规则只绑定注册后通过 SDK 获取或创建的页面。重复触发同一弹窗也可以再次处理；应让上次关闭状态完成后再打开。

## 示例

以下名称来自 keys-click-test 靶场，库路径按实际位置调整。

```python
import time
import uiautoma
from uiautoma import web

with uiautoma.open(r".\web元素库") as package:
    web.auto_handle_popup(
        "close_dialog",
        close_button="web靶场_模态弹窗_关闭按钮",
    )
    page = web.create(
        "https://baobaomi900901.github.io/xpath/#/keys-click-test",
        mode="chrome",
    )
    try:
        page.find("web靶场_打开遮罩弹窗_按钮").click()
        modal = page.find("web靶场_模态弹窗")
        deadline = time.monotonic() + 8
        while modal.is_displayed():
            if time.monotonic() >= deadline:
                raise TimeoutError("弹窗未在 8 秒内关闭")
            time.sleep(0.1)
    finally:
        web.remove_all_auto_handle_popup()
        page.close()
```

在同一个已打开元素库的作用域内，关闭按钮也可以使用元素库提供的 Selector：

```python
close_selector = package.selector("web靶场_模态弹窗_关闭按钮", kind="web")
web.auto_handle_popup("close_dialog", close_button=close_selector)
```

上面的两种注册方式任选一种；同一关闭按钮重复注册会报错。

## 异常与限制

- `InvalidParamsError`：非法处理方式、缺少关闭按钮、空名称、错误参数类型、非 Web Selector，或同一连接重复注册同一关闭按钮。
- `UnsupportedActionError`：使用 `execute_process`。
- 当前不支持跨 iframe 的关闭按钮。
- `close_button` 指向库中的已保存元素，不接受实时 WebElement 或原始 CSS/XPath 查询来代替库元素。
- 原生 JavaScript `alert`、`confirm`、`prompt` 使用 `WebBrowser.handle_javascript_dialog()`；文件选择窗口使用 `web.handle_upload_dialog()`。

## 验证范围

2026-10-05，在产品源码快照 `cb9332d1a04c09e04df54af958e028b2bc45af9b` 的 dev Runtime / Chrome 下，使用靶场的真实 Ant Design Modal 连续 3 轮验收，每轮 **19/19 PASS**，退出码 0，资源清理 PASS。

已验证关闭按钮名称和 Web Selector、注册后 get/create 页面、重复打开、重复注册与参数错误。自动分支仅点击打开按钮，通过被动 DOM 点击监听和弹窗可见性确认自动关闭。未覆盖 Edge、跨 iframe 异常、多规则并行、选择器歧义等场景。`remove_all_auto_handle_popup()` 仅作辅助清理，未在本轮独立验收其移除后行为。

详细证据见 [auto_handle_popup 验证记录](../../../tests/SDK/web/evidence/auto_handle_popup.md)。
