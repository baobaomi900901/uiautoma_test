# SDK 持久化测试状态

生命周期状态：`DRAFT`、`READY_FOR_LIVE`、`VERIFIED`。

> 测一个新 API 时按 [`AGENTS.md`](AGENTS.md) 的 TEST WORKFLOW 走 7 步；
> 判据细则（状态模型、期望值来源、独立确证、抖动治理、脚本与证据骨架、反模式）见
> [`web/web api 实测手册.md`](web/web%20api%20实测手册.md)。

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
| `uiautoma.web.WebElement.get_text()` | `VERIFIED`（8/8） | [`web/test_web_element_get_text_html.py`](web/test_web_element_get_text_html.py) | [`web/evidence/get_text.md`](web/evidence/get_text.md) | [`sdk/docs/web/get_text.md`](../../sdk/docs/web/get_text.md) |
| `uiautoma.web.WebElement.get_html()` | `VERIFIED`（17/17；2026-09-20 真实库元素复验，连续 3 次退出码 0） | [`web/test_web_element_get_html.py`](web/test_web_element_get_html.py) | [`web/evidence/get_html.md`](web/evidence/get_html.md) | [`sdk/docs/web/get_html.md`](../../sdk/docs/web/get_html.md) |
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
| `uiautoma.web.close_all()` | `VERIFIED`（9/9） | [`web/test_web_close_all_form.py`](web/test_web_close_all_form.py) | [`web/evidence/close_all_current.md`](web/evidence/close_all_current.md) | [`sdk/docs/web/close_all.md`](../../sdk/docs/web/close_all.md) |
| `uiautoma.web.handle_save_dialog()` | `VERIFIED`（7/7；2026-09-15复测，扩展场景待测） | [`web/test_web_handle_save_dialog_current.py`](web/test_web_handle_save_dialog_current.py) | [`web/evidence/handle_save_dialog_current.md`](web/evidence/handle_save_dialog_current.md) | [`sdk/docs/web/handle_save_dialog.md`](../../sdk/docs/web/handle_save_dialog.md) |
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

其余 API：远端 `main` 的公开合同已通过 `--contract-only`（2026-09-18 新基线全量冒烟 61/61）。
2026-08 那批元素库脚本的真实运行结果绑在旧基线 `dbe9e015` 上，仍按历史证据对待；
其中读取 `page.raw` / `element.raw` 的 35 个模板脚本在新基线上**无法运行**（`raw` 已被移除），
处置口径待定，详见 `web/evidence/baseline_adaptation.md`「本轮未纳入的范围」。

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
| `uiautoma.web.handle_save_dialog()` | `VERIFIED`（7/7；2026-09-15复测，扩展场景待测） | `web/test_web_handle_save_dialog_current.py` | `web/evidence/handle_save_dialog_current.md` |
| `uiautoma.web.handle_upload_dialog()` | `READY_FOR_LIVE`（3/5；路径已填写但“打开”按钮识别失败） | `web/test_web_handle_upload_dialog_current.py` | `web/evidence/handle_upload_dialog_current.md` |
| `uiautoma.web.set_user_environment()` | `VERIFIED`（6/6；含预期环境状态） | `web/test_web_set_user_environment_profiles.py` | `web/evidence/set_user_environment.md` |
| `uiautoma.web.reset_user_environment()` | `VERIFIED`（7/7） | `web/test_web_reset_user_environment.py` | `web/evidence/reset_user_environment.md` |
| `uiautoma.web.WebBrowser.id` | `已移除`（`44c8e91f` 收敛公开接口）；脚本改为「成员收敛 + 替代方式」契约（8/8，2026-09-18 新基线） | `web/test_web_browser_id.py` | `web/evidence/baseline_adaptation.md` |
| `uiautoma.web.WebElement.find_all()` | `VERIFIED`（30 用例 29/29 + 1 `KNOWN`；2026-09-18 新基线；标准靶场同文档路由语义正确，跨 iframe/open shadow 作用域为不对称边界） | `web/test_web_element_find_all.py` | `web/evidence/element_find_all.md` |
| `uiautoma.web.WebBrowser.get_title()` | `VERIFIED`（7/7） | `web/test_web_browser_get_title.py` | `web/evidence/browser_get_title.md` |
| `uiautoma.web.WebBrowser.get_html()` | `VERIFIED`（8/8） | `web/test_web_browser_get_html_baidu.py` | `web/evidence/browser_get_html_baidu.md` |
| `uiautoma.web.WebBrowser.activate()` | `VERIFIED`（6/6） | `web/test_web_browser_activate.py` | `web/evidence/browser_activate.md` |
| `uiautoma.web.WebBrowser.activateTab()` | `VERIFIED`（6/6；恢复仅尝试） | [web/test_web_browser_activate_tab.py](web/test_web_browser_activate_tab.py) | [web/evidence/browser_activate_tab.md](web/evidence/browser_activate_tab.md) |
| `uiautoma.web.WebBrowser.get_url()` | `VERIFIED`（7/7） | `web/test_web_browser_get_url.py` | `web/evidence/browser_get_url.md` |
| `uiautoma.web.WebBrowser.navigate()` | `VERIFIED`（14/14） | `web/test_web_browser_navigate.py` | `web/evidence/browser_navigate.md` |
| `uiautoma.web.WebElement.get_text()` | `VERIFIED`（35/35 语义矩阵复验；2026-09-15；连续 3 次退出码 0；另有早先 8/8 靶场复测） | `web/test_web_element_get_text.py`（35/35）+ `web/test_web_element_get_text_html.py`（8/8） | `web/evidence/get_text.md` |
| `uiautoma.web.WebBrowser.get_text()` | `VERIFIED`（7/7） | `web/test_web_browser_get_text.py` | `web/evidence/browser_get_text.md` |
| `uiautoma.web.WebBrowser.go_back()` | `READY_FOR_LIVE`（2026-09-15：首次调用稳定失败，缺陷 #58） | `web/test_web_browser_go_back.py` | `web/evidence/go_back.md` |
| `uiautoma.web.WebBrowser.go_forward()` | `VERIFIED`（13/13；2026-09-15；仅预热路径，冷状态被 #58 阻塞） | `web/test_web_browser_go_forward.py` | `web/evidence/go_forward.md` |
| `uiautoma.web.WebBrowser.reload()` | `VERIFIED`（12/12；2026-09-15） | `web/test_web_browser_reload.py` | `web/evidence/reload.md` |
| `uiautoma.web.WebBrowser.is_load_completed()` | `VERIFIED`（9/9；2026-09-15；True/False 两路径均已实际覆盖） | `web/test_web_browser_is_load_completed.py` | `web/evidence/is_load_completed.md` |
| `uiautoma.web.WebBrowser.wait_load_completed()` | `VERIFIED`（12/12；2026-09-15） | `web/test_web_browser_wait_load_completed.py` | `web/evidence/wait_load_completed.md` |
| `uiautoma.web.WebBrowser.close()` | `VERIFIED`（10/10；2026-09-15；含 get_all 复核与 stale_page_reference 复核） | `web/test_web_browser_close.py` | `web/evidence/close.md` |
| `uiautoma.web.WebBrowser.execute_javascript()` | `VERIFIED`（16/16；2026-09-15；含双 world 隔离与 DOM 共享） | `web/test_web_browser_execute_javascript.py` | `web/evidence/execute_javascript.md` |
| `uiautoma.web.WebBrowser.scroll_to()` | `VERIFIED`（16/16；2026-09-15；smooth 仅验证与原生行为一致） | `web/test_web_browser_scroll_to.py` | `web/evidence/scroll_to.md` |
| `uiautoma.web.WebBrowser.get_scroll()` | `VERIFIED`（15/15；2026-09-15） | `web/test_web_browser_get_scroll.py` | `web/evidence/get_scroll.md` |
| `uiautoma.web.WebBrowser.handle_javascript_dialog()` | `VERIFIED`（15/15；2026-09-15；confirm/prompt 语义页面内回读核对） | `web/test_web_browser_handle_javascript_dialog.py` | `web/evidence/handle_javascript_dialog.md` |
| `uiautoma.web.WebBrowser.get_javascript_dialog_text()` | `VERIFIED`（13/13；2026-09-15；含等待出现路径证据） | `web/test_web_browser_get_javascript_dialog_text.py` | `web/evidence/get_javascript_dialog_text.md` |
| `uiautoma.web.WebBrowser.start_monitor_network()` | `VERIFIED`（12/12；2026-09-15；含存储级过滤实证） | `web/test_web_browser_start_monitor_network.py` | `web/evidence/start_monitor_network.md` |
| `uiautoma.web.WebBrowser.get_responses()` | `VERIFIED`（19/19；2026-09-15；含记录结构与过滤语义） | `web/test_web_browser_get_responses.py` | `web/evidence/get_responses.md` |
| `uiautoma.web.WebBrowser.stop_monitor_network()` | `VERIFIED`（13/13；2026-09-15） | `web/test_web_browser_stop_monitor_network.py` | `web/evidence/stop_monitor_network.md` |
| `uiautoma.web.WebBrowser.find()` | `VERIFIED`（22/22；2026-09-15；含清理复核修正） | `web/test_web_browser_find.py` | `web/evidence/find.md` |
| `uiautoma.web.WebElement.find()` | `VERIFIED`（6/6；连续 3 次；人工复测通过） | `web/test_web_element_find.py` | `web/evidence/element_find.md` |
| `uiautoma.web.WebBrowser.find_all()` | `VERIFIED`（20/20；2026-09-15；超时返回空列表、多命中返回全部；含清理复核修正） | `web/test_web_browser_find_all.py` | `web/evidence/find_all.md` |
| `uiautoma.web.WebBrowser.find_by_css()` | `VERIFIED`（22/22；2026-09-15；官方靶场+活 DOM 推导） | `web/test_web_browser_find_by_css.py` | `web/evidence/find_by_css.md` |
| `uiautoma.web.WebElement.find_by_css()` | `VERIFIED`（38/38；用户本轮实测；iframe/open shadow 容器内 CSS 查找） | [web/test_web_element_find_by_css_form.py](web/test_web_element_find_by_css_form.py) | [web/evidence/element_find_by_css.md](web/evidence/element_find_by_css.md) |
| `uiautoma.web.WebElement.find_all_by_css()` | `VERIFIED`（39/39；用户本轮实测；iframe/open shadow 容器内 CSS 全量查找） | [web/test_web_element_find_all_by_css_form.py](web/test_web_element_find_all_by_css_form.py) | [web/evidence/element_find_all_by_css.md](web/evidence/element_find_all_by_css.md) |
| `uiautoma.web.WebElement.find_by_xpath()` | `VERIFIED`（40/40；用户本轮实测；iframe/open shadow 容器内相对 XPath） | [web/test_web_element_find_by_xpath_form.py](web/test_web_element_find_by_xpath_form.py) | [web/evidence/element_find_by_xpath.md](web/evidence/element_find_by_xpath.md) |
| `uiautoma.web.WebElement.find_all_by_xpath()` | `VERIFIED`（41/41；用户本轮实测；iframe/open shadow 容器内 XPath 全量查找） | [web/test_web_element_find_all_by_xpath_form.py](web/test_web_element_find_all_by_xpath_form.py) | [web/evidence/element_find_all_by_xpath.md](web/evidence/element_find_all_by_xpath.md) |
| `uiautoma.web.WebElement.parent()` | `VERIFIED`（23/23；表单场景；含零预算超时边界） | [web/test_web_element_parent_form.py](web/test_web_element_parent_form.py) | [web/evidence/element_parent_form.md](web/evidence/element_parent_form.md) |
| `uiautoma.web.WebElement.children()` | `VERIFIED`（25/25；表单场景；直接子元素；含零预算超时边界） | [web/test_web_element_children_form.py](web/test_web_element_children_form.py) | [web/evidence/element_children_form.md](web/evidence/element_children_form.md) |
| `uiautoma.web.WebElement.child_at()` | `VERIFIED`（40/40；表单场景；含零预算超时边界） | [web/test_web_element_child_at_form.py](web/test_web_element_child_at_form.py) | [web/evidence/element_child_at_form.md](web/evidence/element_child_at_form.md) |
| `uiautoma.web.WebElement.previous_sibling()` | `VERIFIED`（28/28；表单场景；含零预算超时边界） | [web/test_web_element_previous_sibling_form.py](web/test_web_element_previous_sibling_form.py) | [web/evidence/element_previous_sibling_form.md](web/evidence/element_previous_sibling_form.md) |
| `uiautoma.web.WebElement.next_sibling()` | `VERIFIED`（28/28；表单场景；含零预算超时边界） | [web/test_web_element_next_sibling_form.py](web/test_web_element_next_sibling_form.py) | [web/evidence/element_next_sibling_form.md](web/evidence/element_next_sibling_form.md) |
| `uiautoma.web.WebElement.click()` | `VERIFIED`（62/62；含真实 Win 键日志核验；原前台恢复有警告） | [web/test_web_element_click_keys.py](web/test_web_element_click_keys.py) | [web/evidence/element_click_keys.md](web/evidence/element_click_keys.md) |
| `uiautoma.web.WebElement.clipboard_input()` | `VERIFIED`（双模式44/44；非 iframe/iframe；剪贴板 JSON 核对） | [web/test_web_clipboard_input_native_form.py](web/test_web_clipboard_input_native_form.py) | [web/evidence/element_clipboard_input_native_form.md](web/evidence/element_clipboard_input_native_form.md) |
| `uiautoma.web.WebElement.dblclick()` | `VERIFIED`（41/41；真实/DOM 双击；剪贴板日志核验；原前台恢复有警告） | [web/test_web_element_dblclick_keys.py](web/test_web_element_dblclick_keys.py) | [web/evidence/element_dblclick_keys.md](web/evidence/element_dblclick_keys.md) |
| `uiautoma.web.WebElement.focus()` | `VERIFIED`（15/15；focusin/activeElement/剪贴板日志；实测 isTrusted=True） | [web/test_web_element_focus_keys.py](web/test_web_element_focus_keys.py) | [web/evidence/element_focus_keys.md](web/evidence/element_focus_keys.md) |
| `uiautoma.web.WebElement.hover()` | `VERIFIED`（23/23；真实/脚本悬停；锚点与 delay_after 核验） | [web/test_web_element_hover_keys.py](web/test_web_element_hover_keys.py) | [web/evidence/element_hover_keys.md](web/evidence/element_hover_keys.md) |
| `uiautoma.web.WebElement.input()` | `READY_FOR_LIVE`（两模式各18/25；后台 DOM 输入提交状态异常；见 [Issue #65](https://github.com/uiautoma/desktop/issues/65)） | [web/test_web_element_input_native_form.py](web/test_web_element_input_native_form.py) | [web/evidence/element_input_native_form.md](web/evidence/element_input_native_form.md) |
| `uiautoma.web.WebBrowser.find_all_by_css()` | `VERIFIED`（22/22；2026-09-15；官方靶场+活 DOM 推导） | `web/test_web_browser_find_all_by_css.py` | `web/evidence/find_all_by_css.md` |
| `uiautoma.web.WebBrowser.find_by_xpath()` | `VERIFIED`（22/22；2026-09-15；官方靶场+活 DOM 推导） | `web/test_web_browser_find_by_xpath.py` | `web/evidence/find_by_xpath.md` |
| `uiautoma.web.WebBrowser.find_all_by_xpath()` | `VERIFIED`（22/22；2026-09-15；官方靶场+活 DOM 推导） | `web/test_web_browser_find_all_by_xpath.py` | `web/evidence/find_all_by_xpath.md` |
| `uiautoma.web.WebBrowser.is_element_displayed()` | `VERIFIED`（20/20；2026-09-15；活推导分类唯一 52/多命中 10/本页不存在 8） | `web/test_web_browser_is_element_displayed.py` | `web/evidence/is_element_displayed.md` |
| `uiautoma.web.WebBrowser.extract_table()` | `未实现`（已验合同 11/11：必抛 `UnsupportedActionError`，零 Runtime 交互） | `web/test_web_browser_extract_table.py` | `web/evidence/extract_table.md` |
| `uiautoma.web.WebBrowser.screenshot()` | `VERIFIED`（21/21；2026-09-15；产物字节独立解析确证尺寸） | `web/test_web_browser_screenshot.py` | `web/evidence/browser_screenshot.md` |
| `uiautoma.web.WebBrowser.screenshot_to_clipboard()` | `VERIFIED`（23/23；2026-09-15；ctypes 独立读 CF_DIB + 与文件截图三角像素比对） | `web/test_web_browser_screenshot_to_clipboard.py` | `web/evidence/screenshot_to_clipboard.md` |
| `uiautoma.web.WebElement.screenshot_to_clipboard()` | `VERIFIED`（18/18；2026-09-15；ctypes 独立读 CF_DIB + 活矩形裁切偏移扫描验取景，Issue #20 在 dpr=1 未复现） | `web/test_web_element_screenshot_to_clipboard.py` | `web/evidence/element_screenshot_to_clipboard.md` |
| `uiautoma.web.WebBrowser.stop_load()` | `BLOCKED`（10/12 + 2 `BLOCKED` + 1 `KNOWN`，退出码 2；2026-09-18：地址形态探测按边界约定删除，中止「待处理导航」的正向路径需靶场提供「加载永不完成」页面） | `web/test_web_browser_stop_load.py` | `web/evidence/stop_load.md` |
| `uiautoma.web.WebBrowser.wait_appear()` | `VERIFIED`（31/31 + 1 边界；2026-09-15；连续 3 次全绿；canonical 为靶场自计时页 delayed-element.html，测试侧零调度） | `web/test_web_browser_wait_appear.py` | `web/evidence/wait_appear.md` |
| `uiautoma.web.WebBrowser.wait_disappear()` | `VERIFIED`（32/32 无边界；2026-09-15；连续 3 次全绿；含「隐藏≠消失」与 React 销毁节点即判消失） | `web/test_web_browser_wait_disappear.py` | `web/evidence/wait_disappear.md` |
| `uiautoma.web.WebBrowser.http_request()` | `VERIFIED`（41/41；2026-09-18 新基线复跑；地址形态探测已删除，`connect_timeout` 语义改由回显服务 `/delay` 覆盖） | `web/test_web_browser_http_request.py` | `web/evidence/http_request.md` |

> 说明：本节是当前外部 `sdk测试` 工作区复测覆盖的叠加记录；前面的历史条目保留原始验收上下文。`delete_cookie` 在当前 SDK 中未公开（`dbe9e015` 起即如此），脚本已改写为收敛契约（旧名不存在 + `remove_cookie` 签名核对）。
>
> **`WebElement.get_html()` 元素级复验**（2026-09-20，`main@c101caa9`）：17/17 通过，退出码 0，
> 连续 3 次全绿。靶场为用户提供的百度资讯搜索「区块链」结果页，元素为库 `260902_web元素` 的
> `web靶场_测试超链接`（搜索结果第一条标题链接）。期望值来自 HTML 序列化规范与页面侧
> `document.querySelectorAll('a')` 全量枚举（96 个锚点中唯一逐字节相等），不经产品返回值推导；
> 并覆盖 `innerHTML` 子串关系、HTML 与 `get_text()` 通道差异、属性 `&`↔`&amp;` 转义、活推导读写、
> 零参数合同与 `stale_page_reference`。两条实测边界需要知晓：**属性顺序按 DOM 解析顺序序列化**
> （实测 `href → target → class → aria-label`，与元素库捕获顺序不同，不可按捕获顺序断言）；
> 该库元素绑定依赖百度当时的 DOM（必需 `div[index=1]` 与 `a.class+index=0`），改版即失效，
> 脚本按**环境阻塞（退出码 2）**处理，不记产品缺陷。修订说明（旧 2026-08-08 结论的保留与差异）
> 见 [`web/evidence/get_html.md`](web/evidence/get_html.md) 第 5 节。
>
> `WebBrowser.go_back()`（2026-09-15）：首次调用稳定失败，引擎原始
> `failure_reason=Cannot find a next page in history.`，而页面侧 `history.length` 已为 `2`~`3`；
> 先执行一次 `page.execute_javascript(...)` 后即可成功。跟踪 Issue：
> https://github.com/uiautoma/desktop/issues/58 ；复现脚本 `issues/issue_58/test_issue_58_go_back.py`。
>
> `WebBrowser.stop_load()` 验收（2026-09-15）顺带发现并已提单的三个缺陷：
> - [#59](https://github.com/uiautoma/desktop/issues/59) `is_load_completed()` 在 Chrome 错误页上恒为 `False`（`wait_load_completed()` 只能等到超时）
> - [#60](https://github.com/uiautoma/desktop/issues/60) 连续两次 `wait_load_completed()` 超时后页面对象失效（`stale_page_reference`）并泄漏标签（4/4 复现）
> - [#61](https://github.com/uiautoma/desktop/issues/61) 无响应标签无法回收：`close()` / `navigate()` 在同步 JS 死循环页面上全部失败
>
> 详见 `web/evidence/stop_load.md` 与 `web/evidence/is_load_completed.md`。
>
> **`WebBrowser` 覆盖完成**（2026-09-15，`http_request()` 验收后；2026-09-18 在新基线 `c101caa9` 复核）：
> 按 SDK 源码全量对账，`WebBrowser` 的公开成员除**已被移除**的 `id`（`44c8e91f`）外全部有验收结果
> （`go_back` 已测但存在缺陷 #58、`extract_table` 已验合同但功能未实现）。
> 元素级 `WebElement` 仍有未在本工作区复验的方法，见 `web/web api 清单.md`。
>
> **基线切换适配**（2026-09-18）：全部实测证据此前绑在 worktree `dbe9e015` 上；本次以
> `main@c101caa9` 为新基线完成套件适配——机械迁移 21 个脚本、语义改写 6 个、套件内其余 `page.id`
> 引用 9 个、契约漂移 3 个、重写 1 个，并修正 2 处早于本次切换的历史漂移。
> 契约面冒烟 **61/61**；受影响最重的脚本真机复跑全绿（`reload` 12/12、`go_forward` 13/13、
> `navigate` 14/14、`id` 8/8、`get_all` 9/9、`activate` 6/6、`get` 9/9）；`stop_load` 与
> `http_request` 的结果以「测试侧边界裁定」一节为准（地址形态探测删除后分别变为
> 10/12+2 BLOCKED 与 41/41）。差异总账、判据强度变化与三条产品侧观察见
> `web/evidence/baseline_adaptation.md`。
>
> **测试侧边界裁定**（2026-09-18，产品负责人）：**一律不使用非靶场地址形态探测**，全部删除。
> 已删除 4 个脚本里的 6 处自造地址/路径名（不可路由保留地址、本机 discard 端口、保留域名、
> 自造页面文件名），页面材料一律来自标准靶场 `https://baobaomi900901.github.io/xpath/`。
> 删除后的复跑结果：`stop_load` 10/12 + 2 `BLOCKED` + 1 `KNOWN`（退出码 2）、
> `http_request` 41/41、`get_all` 9/9、`get` 9/9、`WebElement.find_all` 30 用例 29/29 + 1 `KNOWN`。
> **待靶场提供（否则无法解除阻塞）**：一个「加载永不完成」的页面/路由（服务端永不响应的子资源），
> 用于验证 `stop_load()` 中止待处理导航与 `create(load_timeout=…)` 超时后的标签状态。
> 产品负责人已确认会补充该页面；到位后即可恢复这两族用例的实测。
>
> **`WebElement.find_all()` 结论修正**（2026-09-18）：标准靶场**同文档**页面上元素级作用域语义
> 正确（含严格子集：整页 1 条 → 作用域内 0 条）；**跨 iframe/open shadow 的已保存路径**作用域内
> 返回空列表（整页 3 条、shadow 内 3 个节点），属不对称边界，记为 `KNOWN`。
> 元素库 64/72 条路径跨 iframe/shadow，故该组合在真实库下不可用——已提
> [#64](https://github.com/uiautoma/desktop/issues/64)，修复后该用例应升级为 PASS。
>
> **`WebBrowser.id` 移除后的判据缺口**（必须知晓）：公开面已无任何标签身份访问器，
> 「同一标签」只能用 `(url, title)` 组合键近似；同 URL 同标题的两个标签**无法区分**。
> 键不变的场景（刷新）可用组合键做等价断言；键必然变化的场景（导航/前进/后退）只能退化为
> 「对象仍可驱动该标签 + 标签数量未增加」，强度弱于原先的 `id` 不变断言。
