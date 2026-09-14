# SDK 持久化测试状态

生命周期状态：`DRAFT`、`READY_FOR_LIVE`、`VERIFIED`。

## Win32

| API | 状态 | 持久化脚本 | 验证证据 | 公开文档 |
| --- | --- | --- | --- | --- |
| `uiautoma.win32.get()` | `VERIFIED` | [`win32/test_win32_get.py`](win32/test_win32_get.py) | [`win32/evidence/get.md`](win32/evidence/get.md) | [`sdk/docs/win32/get.md`](../../sdk/docs/win32/get.md) |
| `uiautoma.win32.get_by_handle()` | `VERIFIED` | [`win32/test_win32_get_by_handle.py`](win32/test_win32_get_by_handle.py) | [`win32/evidence/get_by_handle.md`](win32/evidence/get_by_handle.md) | [`sdk/docs/win32/get_by_handle.md`](../../sdk/docs/win32/get_by_handle.md) |
| `uiautoma.win32.get_by_selector()` | `VERIFIED` | [`win32/test_win32_get_by_selector.py`](win32/test_win32_get_by_selector.py) | [`win32/evidence/get_by_selector.md`](win32/evidence/get_by_selector.md) | [`sdk/docs/win32/get_by_selector.md`](../../sdk/docs/win32/get_by_selector.md) |
| `uiautoma.win32.get_desktop()` | `VERIFIED` | [`win32/test_win32_get_desktop.py`](win32/test_win32_get_desktop.py) | [`win32/evidence/get_desktop.md`](win32/evidence/get_desktop.md) | [`sdk/docs/win32/get_desktop.md`](../../sdk/docs/win32/get_desktop.md) |
| `uiautoma.win32.exists()` | `VERIFIED` | [`win32/test_win32_exists.py`](win32/test_win32_exists.py) | [`win32/evidence/exists.md`](win32/evidence/exists.md) | [`sdk/docs/win32/exists.md`](../../sdk/docs/win32/exists.md) |
| `uiautoma.win32.minimize_all()` | `VERIFIED` | [`win32/test_win32_minimize_all.py`](win32/test_win32_minimize_all.py) | [`win32/evidence/minimize_all.md`](win32/evidence/minimize_all.md) | [`sdk/docs/win32/minimize_all.md`](../../sdk/docs/win32/minimize_all.md) |
| `uiautoma.win32.mouse_move()` | `READY_FOR_LIVE` | [`win32/test_win32_mouse_move.py`](win32/test_win32_mouse_move.py) | [`win32/evidence/mouse_move.md`](win32/evidence/mouse_move.md) | [`sdk/docs/win32/mouse_move.md`](../../sdk/docs/win32/mouse_move.md) |
| `uiautoma.win32.mouse_click()` | `VERIFIED` | [`win32/test_win32_mouse_click.py`](win32/test_win32_mouse_click.py) | [`win32/evidence/mouse_click.md`](win32/evidence/mouse_click.md) | [`sdk/docs/win32/mouse_click.md`](../../sdk/docs/win32/mouse_click.md) |
| `uiautoma.win32.mouse_wheel()` | `VERIFIED` | [`win32/test_win32_mouse_wheel.py`](win32/test_win32_mouse_wheel.py) | [`win32/evidence/mouse_wheel.md`](win32/evidence/mouse_wheel.md) | [`sdk/docs/win32/mouse_wheel.md`](../../sdk/docs/win32/mouse_wheel.md) |
| `uiautoma.win32.get_mouse_position()` | `READY_FOR_LIVE` | [`win32/test_win32_get_mouse_position.py`](win32/test_win32_get_mouse_position.py) | [`win32/evidence/get_mouse_position.md`](win32/evidence/get_mouse_position.md) | [`sdk/docs/win32/get_mouse_position.md`](../../sdk/docs/win32/get_mouse_position.md) |
| `uiautoma.win32.send_keys()` | `VERIFIED` | [`win32/test_win32_send_keys.py`](win32/test_win32_send_keys.py) | [`win32/evidence/send_keys.md`](win32/evidence/send_keys.md) | [`sdk/docs/win32/send_keys.md`](../../sdk/docs/win32/send_keys.md) |
| `uiautoma.win32.manual_motion_on()` | `VERIFIED` | [`win32/test_win32_manual_motion.py`](win32/test_win32_manual_motion.py) | [`win32/evidence/manual_motion_on.md`](win32/evidence/manual_motion_on.md) | [`sdk/docs/win32/manual_motion_on.md`](../../sdk/docs/win32/manual_motion_on.md) |
| `uiautoma.win32.manual_motion_off()` | `VERIFIED` | [`win32/test_win32_manual_motion.py`](win32/test_win32_manual_motion.py) | [`win32/evidence/manual_motion_off.md`](win32/evidence/manual_motion_off.md) | [`sdk/docs/win32/manual_motion_off.md`](../../sdk/docs/win32/manual_motion_off.md) |
| `uiautoma.win32.screenshot.save_screen_to_clipboard()` | `VERIFIED` | [`win32/test_win32_save_screen_to_clipboard.py`](win32/test_win32_save_screen_to_clipboard.py) | [`win32/evidence/save_screen_to_clipboard.md`](win32/evidence/save_screen_to_clipboard.md) | [`sdk/docs/win32/save_screen_to_clipboard.md`](../../sdk/docs/win32/save_screen_to_clipboard.md) |
| `uiautoma.win32.screenshot.save_window_to_clipboard()` | `VERIFIED` | [`win32/test_win32_save_window_to_clipboard.py`](win32/test_win32_save_window_to_clipboard.py) | [`win32/evidence/save_window_to_clipboard.md`](win32/evidence/save_window_to_clipboard.md) | [`sdk/docs/win32/save_window_to_clipboard.md`](../../sdk/docs/win32/save_window_to_clipboard.md) |
| `uiautoma.win32.screenshot.save_screen_to_file()` | `VERIFIED` | [`win32/test_win32_save_screen_to_file.py`](win32/test_win32_save_screen_to_file.py) | [`win32/evidence/save_screen_to_file.md`](win32/evidence/save_screen_to_file.md) | [`sdk/docs/win32/save_screen_to_file.md`](../../sdk/docs/win32/save_screen_to_file.md) |

## Web

| API | 状态 | 持久化脚本 | 验证证据 | 公开文档 |
| --- | --- | --- | --- | --- |
| `uiautoma.web.WebElement.click()` | `VERIFIED` | [`web/test_web_element_click.py`](web/test_web_element_click.py) | [`web/evidence/click.md`](web/evidence/click.md) | [`sdk/docs/web/click.md`](../../sdk/docs/web/click.md) |
| `uiautoma.web.WebElement.dblclick()` | `VERIFIED` | [`web/test_web_element_dblclick.py`](web/test_web_element_dblclick.py) | [`web/evidence/dblclick.md`](web/evidence/dblclick.md) | [`sdk/docs/web/dblclick.md`](../../sdk/docs/web/dblclick.md) |
| `uiautoma.web.WebElement.hover()` | `VERIFIED` | [`web/test_web_element_hover.py`](web/test_web_element_hover.py) | [`web/evidence/hover.md`](web/evidence/hover.md) | [`sdk/docs/web/hover.md`](../../sdk/docs/web/hover.md) |
| `uiautoma.web.WebElement.focus()` | `VERIFIED` | [`web/test_web_element_focus.py`](web/test_web_element_focus.py) | [`web/evidence/focus.md`](web/evidence/focus.md) | [`sdk/docs/web/focus.md`](../../sdk/docs/web/focus.md) |
| `uiautoma.web.WebElement.parent()` | `VERIFIED` | [`web/test_web_element_parent.py`](web/test_web_element_parent.py) | [`web/evidence/parent.md`](web/evidence/parent.md) | [`sdk/docs/web/parent.md`](../../sdk/docs/web/parent.md) |
| `uiautoma.web.WebElement.children()` | `VERIFIED` | [`web/test_web_element_children.py`](web/test_web_element_children.py) | [`web/evidence/children.md`](web/evidence/children.md) | [`sdk/docs/web/children.md`](../../sdk/docs/web/children.md) |
| `uiautoma.web.WebElement.child_at()` | `VERIFIED` | [`web/test_web_element_child_at.py`](web/test_web_element_child_at.py) | [`web/evidence/child_at.md`](web/evidence/child_at.md) | [`sdk/docs/web/child_at.md`](../../sdk/docs/web/child_at.md) |
| `uiautoma.web.WebElement.previous_sibling()` | `VERIFIED` | [`web/test_web_element_previous_sibling.py`](web/test_web_element_previous_sibling.py) | [`web/evidence/previous_sibling.md`](web/evidence/previous_sibling.md) | [`sdk/docs/web/previous_sibling.md`](../../sdk/docs/web/previous_sibling.md) |
| `uiautoma.web.WebElement.next_sibling()` | `VERIFIED` | [`web/test_web_element_next_sibling.py`](web/test_web_element_next_sibling.py) | [`web/evidence/next_sibling.md`](web/evidence/next_sibling.md) | [`sdk/docs/web/next_sibling.md`](../../sdk/docs/web/next_sibling.md) |
| `uiautoma.web.WebElement.input()` | `VERIFIED` | [`web/test_web_element_input.py`](web/test_web_element_input.py) | [`web/evidence/input.md`](web/evidence/input.md) | [`sdk/docs/web/input.md`](../../sdk/docs/web/input.md) |
| `uiautoma.web.WebElement.clipboard_input()` | `VERIFIED` | [`web/test_web_element_clipboard_input.py`](web/test_web_element_clipboard_input.py) | [`web/evidence/clipboard_input.md`](web/evidence/clipboard_input.md) | [`sdk/docs/web/clipboard_input.md`](../../sdk/docs/web/clipboard_input.md) |
| `uiautoma.web.WebElement.get_text()` | `VERIFIED` | [`web/test_web_element_get_text.py`](web/test_web_element_get_text.py) | [`web/evidence/get_text.md`](web/evidence/get_text.md) | [`sdk/docs/web/get_text.md`](../../sdk/docs/web/get_text.md) |
| `uiautoma.web.WebElement.get_html()` | `VERIFIED` | [`web/test_web_element_get_html.py`](web/test_web_element_get_html.py) | [`web/evidence/get_html.md`](web/evidence/get_html.md) | [`sdk/docs/web/get_html.md`](../../sdk/docs/web/get_html.md) |
| `uiautoma.web.WebElement.get_value()` | `VERIFIED` | [`web/test_web_element_get_value.py`](web/test_web_element_get_value.py) | [`web/evidence/get_value.md`](web/evidence/get_value.md) | [`sdk/docs/web/get_value.md`](../../sdk/docs/web/get_value.md) |
| `uiautoma.web.WebElement.set_value()` | `VERIFIED` | [`web/test_web_element_set_value.py`](web/test_web_element_set_value.py) | [`web/evidence/set_value.md`](web/evidence/set_value.md) | [`sdk/docs/web/set_value.md`](../../sdk/docs/web/set_value.md) |
| `uiautoma.web.WebElement.check()` | `READY_FOR_LIVE` | [`web/test_web_element_check.py`](web/test_web_element_check.py) | [`web/evidence/check.md`](web/evidence/check.md) | [`sdk/docs/web/check.md`](../../sdk/docs/web/check.md) |
| `uiautoma.web.WebElement.is_checked()` | `READY_FOR_LIVE` | [`web/test_web_element_is_checked.py`](web/test_web_element_is_checked.py) | [`web/evidence/is_checked.md`](web/evidence/is_checked.md) | [`sdk/docs/web/is_checked.md`](../../sdk/docs/web/is_checked.md) |
| `uiautoma.web.WebElement.is_enabled()` | `READY_FOR_LIVE` | [`web/test_web_element_is_enabled.py`](web/test_web_element_is_enabled.py) | [`web/evidence/is_enabled.md`](web/evidence/is_enabled.md) | [`sdk/docs/web/is_enabled.md`](../../sdk/docs/web/is_enabled.md) |
| `uiautoma.web.WebElement.get_attribute()` | `VERIFIED` | [`web/test_web_element_set_attribute_get_attribute.py`](web/test_web_element_set_attribute_get_attribute.py) | [`web/evidence/get_attribute.md`](web/evidence/get_attribute.md) | [`sdk/docs/web/get_attribute.md`](../../sdk/docs/web/get_attribute.md) |
| `uiautoma.web.WebElement.get_all_attributes()` | `VERIFIED` | [`web/test_web_element_get_all_attributes.py`](web/test_web_element_get_all_attributes.py) | [`web/evidence/get_all_attributes.md`](web/evidence/get_all_attributes.md) | [`sdk/docs/web/get_all_attributes.md`](../../sdk/docs/web/get_all_attributes.md) |
| `uiautoma.web.WebElement.set_attribute()` | `READY_FOR_LIVE` | [`web/test_web_element_set_attribute_get_attribute.py`](web/test_web_element_set_attribute_get_attribute.py) | [`web/evidence/set_attribute.md`](web/evidence/set_attribute.md) | [`sdk/docs/web/set_attribute.md`](../../sdk/docs/web/set_attribute.md) |
| `uiautoma.web.WebElement.select()` | `VERIFIED` | [`web/test_web_element_select.py`](web/test_web_element_select.py) | [`web/evidence/select.md`](web/evidence/select.md) | [`sdk/docs/web/select.md`](../../sdk/docs/web/select.md) |
| `uiautoma.web.WebElement.select_by_index()` | `VERIFIED` | [`web/test_web_element_select_by_index.py`](web/test_web_element_select_by_index.py) | [`web/evidence/select_by_index.md`](web/evidence/select_by_index.md) | [`sdk/docs/web/select_by_index.md`](../../sdk/docs/web/select_by_index.md) |
| `uiautoma.web.WebElement.select_multiple()` | `READY_FOR_LIVE` | [`web/test_web_element_select_multiple.py`](web/test_web_element_select_multiple.py) | [`web/evidence/select_multiple.md`](web/evidence/select_multiple.md) | [`sdk/docs/web/select_multiple.md`](../../sdk/docs/web/select_multiple.md) |
| `uiautoma.web.WebElement.select_multiple_by_index()` | `READY_FOR_LIVE` | [`web/test_web_element_select_multiple_by_index.py`](web/test_web_element_select_multiple_by_index.py) | [`web/evidence/select_multiple_by_index.md`](web/evidence/select_multiple_by_index.md) | [`sdk/docs/web/select_multiple_by_index.md`](../../sdk/docs/web/select_multiple_by_index.md) |
| `uiautoma.web.WebElement.get_select_options()` | `READY_FOR_LIVE` | [`web/test_web_element_get_select_options.py`](web/test_web_element_get_select_options.py) | [`web/evidence/get_select_options.md`](web/evidence/get_select_options.md) | [`sdk/docs/web/get_select_options.md`](../../sdk/docs/web/get_select_options.md) |
| `uiautoma.web.WebElement.get_all_select_items()` | `READY_FOR_LIVE` | [`web/test_web_element_get_all_select_items.py`](web/test_web_element_get_all_select_items.py) | [`web/evidence/get_all_select_items.md`](web/evidence/get_all_select_items.md) | [`sdk/docs/web/get_all_select_items.md`](../../sdk/docs/web/get_all_select_items.md) |
| `uiautoma.web.WebElement.get_selected_item()` | `READY_FOR_LIVE` | [`web/test_web_element_get_selected_item.py`](web/test_web_element_get_selected_item.py) | [`web/evidence/get_selected_item.md`](web/evidence/get_selected_item.md) | [`sdk/docs/web/get_selected_item.md`](../../sdk/docs/web/get_selected_item.md) |
| `uiautoma.web.WebElement.get_bounding()` | `VERIFIED` | [`web/test_web_element_get_bounding.py`](web/test_web_element_get_bounding.py) | [`web/evidence/get_bounding.md`](web/evidence/get_bounding.md) | [`sdk/docs/web/get_bounding.md`](../../sdk/docs/web/get_bounding.md) |
| `uiautoma.web.WebElement.screenshot()` | `READY_FOR_LIVE` | [`web/test_web_element_screenshot.py`](web/test_web_element_screenshot.py) | [`web/evidence/screenshot.md`](web/evidence/screenshot.md) | [`sdk/docs/web/screenshot.md`](../../sdk/docs/web/screenshot.md) |
| `uiautoma.web.WebElement.drag_to()` | `READY_FOR_LIVE` | [`web/test_web_element_drag_to.py`](web/test_web_element_drag_to.py) | [`web/evidence/drag_to.md`](web/evidence/drag_to.md) | [`sdk/docs/web/drag_to.md`](../../sdk/docs/web/drag_to.md) |
| `uiautoma.web.WebElement.upload()` | `VERIFIED` | [`web/test_web_element_upload.py`](web/test_web_element_upload.py) | [`web/evidence/upload.md`](web/evidence/upload.md) | [`sdk/docs/web/upload.md`](../../sdk/docs/web/upload.md) |
| `uiautoma.web.WebElement.download()` | `READY_FOR_LIVE` | [`web/test_web_element_download.py`](web/test_web_element_download.py) | [`web/evidence/download.md`](web/evidence/download.md) | [`sdk/docs/web/download.md`](../../sdk/docs/web/download.md) |
| `uiautoma.web.close_all()` | `READY_FOR_LIVE` | [`web/test_web_close_all.py`](web/test_web_close_all.py) | [`web/evidence/close_all.md`](web/evidence/close_all.md) | [`sdk/docs/web/close_all.md`](../../sdk/docs/web/close_all.md) |
| `uiautoma.web.handle_save_dialog()` | `READY_FOR_LIVE` | [`web/test_web_handle_save_dialog.py`](web/test_web_handle_save_dialog.py) | [`web/evidence/handle_save_dialog.md`](web/evidence/handle_save_dialog.md) | [`sdk/docs/web/handle_save_dialog.md`](../../sdk/docs/web/handle_save_dialog.md) |
| `uiautoma.web.handle_upload_dialog()` | `READY_FOR_LIVE` | [`web/test_web_handle_upload_dialog.py`](web/test_web_handle_upload_dialog.py) | [`web/evidence/handle_upload_dialog.md`](web/evidence/handle_upload_dialog.md) | [`sdk/docs/web/handle_upload_dialog.md`](../../sdk/docs/web/handle_upload_dialog.md) |
| `uiautoma.web.set_cookie()` | `READY_FOR_LIVE` | [`web/test_web_set_cookie_get_cookie.py`](web/test_web_set_cookie_get_cookie.py) | [`web/evidence/set_cookie.md`](web/evidence/set_cookie.md) | [`sdk/docs/web/set_cookie.md`](../../sdk/docs/web/set_cookie.md) |
| `uiautoma.web.get_cookie()` | `READY_FOR_LIVE` | [`web/test_web_set_cookie_get_cookie.py`](web/test_web_set_cookie_get_cookie.py) | [`web/evidence/get_cookie.md`](web/evidence/get_cookie.md) | [`sdk/docs/web/get_cookie.md`](../../sdk/docs/web/get_cookie.md) |
| `uiautoma.web.remove_cookie()` | `READY_FOR_LIVE` | [`web/test_web_remove_cookie.py`](web/test_web_remove_cookie.py) | [`web/evidence/remove_cookie.md`](web/evidence/remove_cookie.md) | [`sdk/docs/web/remove_cookie.md`](../../sdk/docs/web/remove_cookie.md) |

`uiautoma.web.WebElement.click()`、`dblclick()`、`hover()`、`focus()` 已于 2026-08-07，
`parent()`、`children()`、`child_at()`、`previous_sibling()`、`next_sibling()`、
`input()`、`clipboard_input()`、`get_text()`、`get_html()`、`get_value()`、
`set_value()`、`get_attribute()` 与 `get_all_attributes()` 已于 2026-08-08，`select()`、
`select_by_index()`、`get_bounding()` 与 `upload()` 已于 2026-08-09，在 Chrome 下完成真实
页面验收与本次资源精确清理，状态为 `VERIFIED`。

其余 API：远端 `main` 的公开合同已通过 `--contract-only`。当前基线不包含本地 Web Stack
安装入口时，旧基线下的真实运行结果只作为历史证据，仍等待当前基线真实复验。

`handle_save_dialog()` 的默认保存场景曾真实通过，但 `wait_complete=True` 已真实复现
`web_download_timeout`；该缺陷修复并完成当前基线复验前不能进入 `VERIFIED`。

`WebElement.check()` 于 2026-08-08 在 Chrome/`form-controls` 完成真实探测：公开签名与
资源清理通过，但 label 目标报 `element_not_checkable`，且对 React/Ant 受控复选框
`check()` 返回成功后真实表单/UI 状态不更新；缺陷修复并复验前不能进入 `VERIFIED`。

`WebElement.set_attribute()` 于 2026-08-08 在 Chrome/`form-controls` 完成真实探测：公开
签名与资源清理通过，但调用抛出 `UnsupportedActionError`（`web.element.set_attribute`
当前版本暂不支持）；实现并与 `get_attribute` 往复验通过前不能进入 `VERIFIED`。

`WebElement.select_multiple()` 与 `select_multiple_by_index()` 于 2026-08-09 在 Chrome /
`form-controls`、元素 `select_html_多选` 上完成真实复验：公开签名、元素绑定与资源清理
通过，但调用均抛出 `UnsupportedActionError`（`web.element.select_multiple` /
`web.element.select_multiple_by_index`）；实现并复验通过前不能进入 `VERIFIED`。

`WebElement.get_select_options()` 于 2026-08-09 在 Chrome/`form-controls`、元素
`select_html` 上完成真实探测：公开签名与资源清理通过，但调用抛出
`UnsupportedActionError`（`web.element.get_select_options` 当前版本暂不支持）；实现并
复验通过前不能进入 `VERIFIED`。

`WebElement.get_all_select_items()` 于 2026-08-09 在 Chrome/`form-controls`、元素
`select_html` 上完成真实探测：公开签名与资源清理通过，但调用抛出
`UnsupportedActionError`（`web.element.get_all_select_items`）；实现并复验通过前不能
进入 `VERIFIED`。跟踪 Issue：https://github.com/uiautoma/desktop/issues/27

`WebElement.get_selected_item()` 于 2026-08-09 在 Chrome/`form-controls`、元素
`select_html` 上完成真实探测：公开签名与资源清理通过，用 `select()` 切换选中后仍抛出
`UnsupportedActionError`（`web.element.get_selected_item`）；实现并复验通过前不能进入
`VERIFIED`。跟踪 Issue：https://github.com/uiautoma/desktop/issues/28

`WebElement.screenshot()` 于 2026-08-09 在 Chrome/`keys-click-test`、元素
`按钮_九宫格` 上完成真实探测：公开签名、PNG 写出与资源清理通过，但裁剪取景相对元素
偏左上（CDP `getBoxModel`→`captureScreenshot` clip 坐标空间）；像素取景修复并复验
通过前不能进入 `VERIFIED`。跟踪 Issue：https://github.com/uiautoma/desktop/issues/20

`WebElement.is_checked()` 于 2026-08-09 在 Chrome/`form-controls`、元素
`checkbox_html_input2` / `checkbox_组件_input` 上完成真实探测：公开签名与资源清理
通过，真实 `click()` 后表单 `hobbies` 含 `"旅行"`，但 `is_checked()` 仍返回 `False`
（只读 HTML attribute，不读 IDL `checked`）；修复并复验通过前不能进入 `VERIFIED`。
跟踪 Issue：https://github.com/uiautoma/desktop/issues/22

`WebElement.is_enabled()` 于 2026-08-09 在 Chrome/`form-controls`、元素 `input元素` /
`input_html_disabled` 上完成真实探测：可用项返回 `True`，禁用项期望 `False` 却因
`disabled` 空串被误判为可用；修复并复验通过前不能进入 `VERIFIED`。
跟踪 Issue：https://github.com/uiautoma/desktop/issues/23

`WebElement.drag_to()` 于 2026-08-09 在 Chrome/`drag-to-test`、元素 `拖拽元素` /
`获取拖拽日志` 上完成真实探测：公开签名与 `delay_after` 通过，但 `left=100/top=50`
后位移仍为 0、日志仅有 `phase=start`（引擎同步派发与 React window 监听时序）；修复并
复验通过前不能进入 `VERIFIED`。
跟踪 Issue：https://github.com/uiautoma/desktop/issues/26

`WebElement.upload()` 于 2026-08-09 在 Chrome/`upload-dialog-test`、元素 `上传文件按钮`
上完成真实验收：CDP 单文件注入后 `get_value()` 文件名匹配，资源清理 `4/4`，状态为
`VERIFIED`。原生对话框路径仍见 `handle_upload_dialog()`。

`WebElement.download()` 于 2026-08-09 在 Chrome/`download-dialog-test`、元素
`下载txt按钮` 上完成真实探测：公开签名与资源清理通过，但 `wait_complete=True` 抛出
`web_download_timeout`（点击后原生另存为无人处理）；修复并复验通过前不能进入
`VERIFIED`。跟踪 Issue：https://github.com/uiautoma/desktop/issues/29

`uiautoma.win32.get()` 于 2026-08-10 在本机已运行窗口上完成真实验收：默认标题 `微信`
与 `Clash Verge` 均可返回带有效句柄的 `Win32Window`（只读探测），状态为 `VERIFIED`。
命令：`uv run --extra dev python -X utf8 tests/SDK/win32/test_win32_get.py`。

`uiautoma.win32.get_by_handle()` 于 2026-08-10 完成真实验收：由 `get(title)` 解析句柄后，
对 `微信` / `Clash Verge` 分别以 int 与 `0x` hex 字符串回取窗口，状态为 `VERIFIED`。
命令：`uv run --extra dev python -X utf8 tests/SDK/win32/test_win32_get_by_handle.py`。

`uiautoma.win32.get_by_selector()` 于 2026-08-10 完成真实验收：打开
`tests/SDK/web/web测试元素库`，对元素 `设置` 以 `str` 与 `package.Selector` 取得
`Clash Verge` 窗口（含有效句柄），清理仅关闭 Package，状态为 `VERIFIED`。
命令：`uv run --extra dev python -X utf8 tests/SDK/win32/test_win32_get_by_selector.py`。

`uiautoma.win32.get_desktop()` 于 2026-08-10 完成真实验收：无 Package 与打开
`web测试元素库` 均返回 `Desktop` 伪窗口；有 Package 时附带 `设置`/`首页`，状态为
`VERIFIED`。命令：`uv run --extra dev python -X utf8 tests/SDK/win32/test_win32_get_desktop.py`。

`uiautoma.win32.exists()` 于 2026-08-10 完成真实验收：存活 `微信` / `Clash Verge`
返回 `True`；受控记事本关闭后返回 `False`；非法入参拒绝，状态为 `VERIFIED`。
命令：`uv run --extra dev python -X utf8 tests/SDK/win32/test_win32_exists.py`。

`uiautoma.win32.minimize_all()` 于 2026-08-10 完成真实验收：样本 `微信` /
`Clash Verge` 调用后均最小化，再调一次（Win+D 切换）恢复，状态为 `VERIFIED`。
命令：`uv run --extra dev python -X utf8 tests/SDK/win32/test_win32_minimize_all.py`。

`uiautoma.win32.mouse_move()` 于 2026-08-10 完成真实探测：公开签名、`screen` /
`position` 落点与鼠标坐标清理通过，但 `relative_to='window'` 抛出
`AttributeError`（`Win32Window` 无 `get_bounding`）；修复并复验通过前不能进入
`VERIFIED`。跟踪 Issue：https://github.com/uiautoma/desktop/issues/30
命令：`uv run --extra dev python -X utf8 tests/SDK/win32/test_win32_mouse_move.py`。

`uiautoma.win32.send_keys()` 于 2026-08-10 在受控记事本上完成真实验收：普通文本与
快捷键 `^a` 全选读回通过，资源清理通过，状态为 `VERIFIED`。
命令：`uv run --extra dev python -X utf8 tests/SDK/win32/test_win32_send_keys.py`。

`uiautoma.win32.mouse_click()` 于 2026-08-10 在 Clash Verge / `web测试元素库` 上完成
真实验收：`首页`、`设置` 左键单击与 `dbclick` 通过；`down`/`up` 按合同被拒绝，状态为
`VERIFIED`。命令：`uv run --extra dev python -X utf8 tests/SDK/win32/test_win32_mouse_click.py`。

`uiautoma.win32.mouse_wheel()` 于 2026-08-10 在 Clash Verge 客户区中心完成真实验收：
`down`/`up` 与非法参数拒绝通过，状态为 `VERIFIED`。
命令：`uv run --extra dev python -X utf8 tests/SDK/win32/test_win32_mouse_wheel.py`。

`uiautoma.win32.get_mouse_position()` 于 2026-08-10 完成 `screen` 默认/显式真实验收。
2026-09-03 新增的 `window` 活动窗口相对坐标已通过自动合同测试，但尚未重新执行真实桌面验收，
当前状态为 `READY_FOR_LIVE`。
命令：`uv run --extra dev python -X utf8 tests/SDK/win32/test_win32_get_mouse_position.py`。

`uiautoma.win32.manual_motion_on()` / `manual_motion_off()` 于 2026-08-11 完成真实验收：
默认与自定义偏好写入、非法参数拒绝、关闭复位通过；开启后 `mouse_move` 慢移、关闭后
瞬移落点正确，状态为 `VERIFIED`。源码另有 `motion_delay` / `min_time` / `max_time`
（部分用户文档未写）。
命令：`uv run --extra dev python -X utf8 tests/SDK/win32/test_win32_manual_motion.py`。

`uiautoma.win32.screenshot.save_screen_to_clipboard()` 于 2026-08-11 完成真实验收：全屏与
区域写入剪贴板后观测到位图格式；非法区域拒绝；清理不清空剪贴板，全屏结果经人工粘贴
确认，状态为 `VERIFIED`。源码另有可选区域参数（部分用户文档未写）。
命令：`uv run --extra dev python -X utf8 tests/SDK/win32/test_win32_save_screen_to_clipboard.py`。

`uiautoma.win32.screenshot.save_window_to_clipboard()` 于 2026-08-11 完成真实验收：样本
`Clash Verge` 在活动窗口默认、`int`/`hex` 句柄、相对窗口区域下写入剪贴板位图；非法
句柄与区域拒绝；清理不清空剪贴板，合同层状态为 `VERIFIED`。人工粘贴确认后发现 GPU/
WebView 窗口客户区常为空色（标题栏在），根因是 `GetWindowDC` 优先且「空白成功」不
触发屏幕 fallback。跟踪 Issue：https://github.com/uiautoma/desktop/issues/32
命令：`uv run --extra dev python -X utf8 tests/SDK/win32/test_win32_save_window_to_clipboard.py`。

`uiautoma.win32.screenshot.save_screen_to_file()` 于 2026-08-11 完成真实验收：全屏 PNG、
JPG 扩展名归一、空 format 按扩展名推断、区域截图与非法区域拒绝通过；产出保留在
`D:\tmp` 并经人工打开确认，状态为 `VERIFIED`。源码返回 `str` 路径且含可选区域参数
（部分用户文档未写）。
命令：`uv run --extra dev python -X utf8 tests/SDK/win32/test_win32_save_screen_to_file.py`。

## 当前 Web API 复测结果（2026-09-14）

| API | 状态 | 测试脚本 | 验收证据 |
|---|---|---|---|
| `uiautoma.web.create()` | `VERIFIED`（5/5） | `web/test_web_create.py` | `web/evidence/create.md` |
| `uiautoma.web.get()` | `VERIFIED`（9/9） | `web/test_web_get.py` | `web/evidence/get.md` |
| `uiautoma.web.get_active()` | `VERIFIED`（9/9） | `web/test_web_get_active.py` | `web/evidence/get_active.md` |
| `uiautoma.web.get_all()` | `VERIFIED`（9/9） | `web/test_web_get_all.py` | `web/evidence/get_all.md` |
| `uiautoma.web.get_cookies()` | `VERIFIED`（12/12） | `web/test_web_get_cookies.py` | `web/evidence/get_cookies.md` |
| `uiautoma.web.get_cookie()` | `VERIFIED`（8/8） | `web/test_web_get_cookie.py` | `web/evidence/get_cookie.md` |
| `uiautoma.web.set_cookie()` | `VERIFIED`（10/10） | `web/test_web_set_cookie.py` | `web/evidence/set_cookie.md` |
| `uiautoma.web.remove_cookie()` | `VERIFIED`（9/9） | `web/test_web_remove_cookie.py` | `web/evidence/remove_cookie.md` |
| `uiautoma.web.clear_cookies()` | `VERIFIED`（10/10） | `web/test_web_clear_cookies.py` | `web/evidence/clear_cookies.md` |
| `uiautoma.web.close_all()` | `VERIFIED`（9/9） | `web/test_web_close_all_form.py` | `web/evidence/close_all_current.md` |
| `uiautoma.web.handle_save_dialog()` | `VERIFIED`（7/7；扩展场景待测） | `web/test_web_handle_save_dialog_current.py` | `web/evidence/handle_save_dialog_current.md` |
| `uiautoma.web.handle_upload_dialog()` | `READY_FOR_LIVE`（3/4；确定按钮识别失败） | `web/test_web_handle_upload_dialog_current.py` | `web/evidence/handle_upload_dialog_current.md` |
| `uiautoma.web.set_user_environment()` | `VERIFIED`（6/6；含预期环境状态） | `web/test_web_set_user_environment_profiles.py` | `web/evidence/set_user_environment.md` |
| `uiautoma.web.WebBrowser.id` | `VERIFIED`（8/8） | `web/test_web_browser_id.py` | `web/evidence/browser_id.md` |

> 说明：本节是当前外部 `sdk测试` 工作区复测覆盖的叠加记录；前面的历史条目保留原始验收上下文。`delete_cookie` 在当前 SDK 中未公开。
