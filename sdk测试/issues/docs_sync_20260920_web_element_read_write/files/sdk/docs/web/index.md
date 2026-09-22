# `uiautoma.web`

当前接口说明按 6C/6D 实现维护，历史实机证据单独保存在 `tests/SDK/web/evidence/`。本页不将早期 VERIFIED 或失败结论当作当前版本验收结果。

| API | 作用 |
| --- | --- |
| [`WebElement.check()`](check.md) | 设置复选框或单选框状态。 |
| [`WebElement.child_at()`](child_at.md) | 按索引获取子元素。 |
| [`WebElement.children()`](children.md) | 获取子元素列表。 |
| [`WebElement.click()`](click.md) | 单击当前网页元素。 |
| [`WebElement.clipboard_input()`](clipboard_input.md) | 通过剪贴板填写网页输入框，可避免输入法影响。 |
| [`web.close_all()`](close_all.md) | 关闭指定浏览器的全部网页。 |
| [`WebElement.dblclick()`](dblclick.md) | 双击当前网页元素。 |
| [`WebElement.download()`](download.md) | 下载文件。 |
| [`WebElement.drag_to()`](drag_to.md) | 拖拽网页元素到指定位置。 |
| [`WebElement.focus()`](focus.md) | 激活当前网页元素。 |
| [`WebElement.get_all_attributes()`](get_all_attributes.md) | 获取网页元素的全部属性值。 |
| [`WebElement.get_all_select_items()`](get_all_select_items.md) | 获取网页下拉框全部选项的文本。 |
| [`WebElement.get_attribute()`](get_attribute.md) | 获取网页元素的属性值。 |
| [`WebElement.get_bounding()`](get_bounding.md) | 获取网页元素的位置和尺寸。 |
| [`web.get_cookie()`](get_cookie.md) | 获取指定网址中指定名称的 Cookie。 |
| [`WebElement.get_html()`](get_html.md) | 读取 Web 元素 HTML。 |
| [`WebElement.get_select_options()`](get_select_options.md) | 获取网页下拉框全部选项的信息。 |
| [`WebElement.get_selected_item()`](get_selected_item.md) | 获取网页下拉框当前选中项的文本。 |
| [`WebElement.get_text()`](get_text.md) | 读取 Web 元素文本。 |
| [`WebElement.get_value()`](get_value.md) | 获取网页元素的值。 |
| [`web.handle_save_dialog()`](handle_save_dialog.md) | 处理浏览器的文件保存对话框。 |
| [`web.handle_upload_dialog()`](handle_upload_dialog.md) | 处理浏览器的文件上传对话框。 |
| [`WebElement.hover()`](hover.md) | 鼠标悬停当前网页元素。 |
| [`WebElement.input()`](input.md) | 填写网页输入框。 |
| [`WebElement.is_checked()`](is_checked.md) | 判断网页复选框或单选框是否被选中。 |
| [`WebElement.is_enabled()`](is_enabled.md) | 判断网页元素是否可用。 |
| [`WebElement.next_sibling()`](next_sibling.md) | 获取下一个兄弟元素。 |
| [`WebElement.parent()`](parent.md) | 获取父元素。 |
| [`WebElement.previous_sibling()`](previous_sibling.md) | 获取上一个兄弟元素。 |
| [`web.remove_cookie()`](remove_cookie.md) | 移除指定网址中指定名称的 Cookie。 |
| [`WebElement.select()`](select.md) | 按选项内容设置网页下拉框。 |
| [`WebElement.select_by_index()`](select_by_index.md) | 按下标设置网页下拉框。 |
| [`WebElement.select_multiple()`](select_multiple.md) | 按选项内容设置多选网页下拉框。 |
| [`WebElement.select_multiple_by_index()`](select_multiple_by_index.md) | 按下标设置多选网页下拉框。 |
| [`WebElement.set_attribute()`](set_attribute.md) | 设置当前元素的属性。 |
| [`web.set_cookie()`](set_cookie.md) | 设置指定网址的 Cookie，已存在时覆盖。 |
| [`WebElement.set_value()`](set_value.md) | 设置当前网页元素的文本值（value 属性），不改变输入焦点或触发输入事件。 |
| [`WebElement.upload()`](upload.md) | 上传文件。 |
| [`WebElement.highlight()`](highlight.md) | 显示当前元素的原生高亮框。 |

页面和元素截图见[截图说明](screenshot.md)。

页面脚本、Cookie、网络、环境选择等完整调用见[最小示例](../../../docs/SDK设计方案/UIAutoma%20SDK%20API%20最小示例参考.md)。

普通元素不再提供 `locate()`、`exists()` 或 `double_click()`；双击使用 `dblclick()`。表格提取、指纹浏览器和执行子流程继续后置。

`WebElement.get_html()`、`get_value()`、`set_value()` 已于 2026-09-20 在当前基线（`c101caa9`）
用真实 Chrome 与真实库元素复验通过；各自的行为要点与已知边界见对应页面，原始记录见
`tests/SDK/web/evidence/`。更早日期的实机结论保留原样，不代表当前版本。

本轮修改范围与复核清单见[6D-3 开发记录](../../../docs/SDK设计方案/阶段6D-3%20合同与文档收口开发记录.md)。
