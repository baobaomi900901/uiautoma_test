# 剩余 Web API 实测汇总（2026-10-04）

共处理 29 项：**17 项通过、1 项失败、11 项跳过**。可测项目各运行三轮，跳过项目只做一轮条件确认。

> 后续增量：2026-10-05 已完成[上传对话框](web_handle_upload_dialog_20261005.md)与[自动关闭 DOM 弹窗](auto_handle_popup_20261005.md)真实复验，分别为 3×10/10 PASS 与 3×19/19 PASS。当前原 29 项合并状态为 19 VERIFIED、1 失败、9 SKIPPED。下文保留 2026-10-04 历史批次计数与原始报告。

产品 worktree：`D:\code\desktop`；commit：`cb9332d1a04c09e04df54af958e028b2bc45af9b`；Chrome / 当前 dev Runtime。

范围取自 API 清单中的空白项，并复核索引中未完成真实验收的项目；额外重测了清单空白但索引已有历史验收的属性、坐标、上传等项。既有 `input` 等部分失败记录仍有效，本次没有把它们标成修复；源码不存在的 element_id/raw 不计入剩余 API。

## 结果

| API | 状态 | 每轮用例结果 | 轮数 | 证据与限制 |
|---|---|---|---|---|
| `uiautoma.web.WebElement.name` | VERIFIED | 6/6 PASS + 0 FAIL + 0 KNOWN | 3 | [报告](element_name_20261004.md) |
| `uiautoma.web.WebElement.get_selected_item()` | VERIFIED | 10/12 PASS + 0 FAIL + 2 KNOWN | 3 | [报告](element_get_selected_item_20261004.md) |
| `uiautoma.web.WebElement.set_attribute()` | VERIFIED | 7/7 PASS + 0 FAIL + 0 KNOWN | 3 | [报告](element_set_attribute_20261004.md) |
| `uiautoma.web.WebElement.get_attribute()` | VERIFIED | 8/8 PASS + 0 FAIL + 0 KNOWN | 3 | [报告](element_get_attribute_20261004.md) |
| `uiautoma.web.WebElement.get_all_attributes()` | VERIFIED | 7/7 PASS + 0 FAIL + 0 KNOWN | 3 | [报告](element_get_all_attributes_20261004.md) |
| `uiautoma.web.WebElement.get_bounding()` | SKIPPED | 5/9 PASS + 0 FAIL + 4 KNOWN | 1 | [报告](element_get_bounding_20261004.md)；当前原生 Provider/浏览器窗口环境不可用，跳过此分支 |
| `uiautoma.web.WebElement.get_anchor_position()` | SKIPPED | 5/11 PASS + 0 FAIL + 6 KNOWN | 1 | [报告](element_get_anchor_position_20261004.md)；当前原生 Provider/浏览器窗口环境不可用，跳过此分支 |
| `uiautoma.web.WebElement.get_anchor_viewport_position()` | VERIFIED | 11/11 PASS + 0 FAIL + 0 KNOWN | 3 | [报告](element_get_anchor_viewport_position_20261004.md) |
| `uiautoma.web.WebElement.screenshot()` | VERIFIED | 5/5 PASS + 0 FAIL + 0 KNOWN | 3 | [报告](element_screenshot_20261004.md) |
| `uiautoma.web.WebElement.is_checked()` | VERIFIED | 11/11 PASS + 0 FAIL + 0 KNOWN | 3 | [报告](element_is_checked_20261004.md) |
| `uiautoma.web.WebElement.is_enabled()` | READY_FOR_LIVE | 8/9 PASS + 1 FAIL + 0 KNOWN | 3 | [报告](element_is_enabled_20261004.md)；disabled="false" 被误判为启用；三轮同一失败 |
| `uiautoma.web.WebElement.is_displayed()` | VERIFIED | 7/7 PASS + 0 FAIL + 0 KNOWN | 3 | [报告](element_is_displayed_20261004.md) |
| `uiautoma.web.WebElement.execute_javascript()` | VERIFIED | 10/10 PASS + 0 FAIL + 0 KNOWN | 3 | [报告](element_execute_javascript_20261004.md) |
| `uiautoma.web.WebElement.scroll_to()` | VERIFIED | 9/9 PASS + 0 FAIL + 0 KNOWN | 3 | [报告](element_scroll_to_20261004.md) |
| `uiautoma.web.WebElement.get_scroll()` | VERIFIED | 10/10 PASS + 0 FAIL + 0 KNOWN | 3 | [报告](element_get_scroll_20261004.md) |
| `uiautoma.web.WebElement.drag_to()` | VERIFIED | 6/7 PASS + 0 FAIL + 1 KNOWN | 3 | [报告](element_drag_to_20261004.md)；当前原生 Provider/浏览器窗口环境不可用，跳过此分支；VERIFIED 仅含 simulative=False |
| `uiautoma.web.WebElement.drag_to_by_cdp()` | VERIFIED | 5/5 PASS + 0 FAIL + 0 KNOWN | 3 | [报告](element_drag_to_by_cdp_20261004.md) |
| `uiautoma.web.WebElement.upload()` | VERIFIED | 6/6 PASS + 0 FAIL + 0 KNOWN | 3 | [报告](element_upload_20261004.md) |
| `uiautoma.web.WebElement.download()` | VERIFIED | 5/5 PASS + 0 FAIL + 0 KNOWN | 3 | [报告](element_download_20261004.md) |
| `uiautoma.web.WebElement.highlight()` | SKIPPED | 6/8 PASS + 0 FAIL + 2 KNOWN | 1 | [报告](element_highlight_20261004.md)；当前原生 Provider/浏览器窗口环境不可用，跳过此分支 |
| `uiautoma.web.WebBrowser.go_back()` | VERIFIED | 5/5 PASS + 0 FAIL + 0 KNOWN | 3 | [报告](browser_go_back_20261004.md) |
| `uiautoma.web.handle_upload_dialog()` | SKIPPED | 4/6 PASS + 0 FAIL + 2 KNOWN | 1 | [报告](web_handle_upload_dialog_20261004.md)；当前原生 Provider/浏览器窗口环境不可用，跳过此分支 |
| `uiautoma.web.auto_handle_popup()` | SKIPPED | 1/2 PASS + 0 FAIL + 1 KNOWN | 1 | [报告](web_auto_handle_popup_20261004.md)；2026-10-05 修正：keys-click-test 已有 DOM Modal，尚缺已保存的关闭按钮；旧“只有 JavaScript 原生弹窗”判断撤回 |
| `uiautoma.web.remove_all_auto_handle_popup()` | SKIPPED | 1/2 PASS + 0 FAIL + 1 KNOWN | 1 | [报告](web_remove_all_auto_handle_popup_20261004.md)；缺少可观察自动关闭效果的 DOM 弹窗/关闭按钮，无法证明规则移除后的真实行为 |
| `uiautoma.web.set_user_environment_fingerprint()` | SKIPPED | 1/2 PASS + 0 FAIL + 1 KNOWN | 1 | [报告](web_set_user_environment_fingerprint_20261004.md)；当前源码直接抛 UnsupportedActionError，未实现指纹浏览器环境 |
| `uiautoma.web.WebBrowser.stop_load()` | SKIPPED | 1/2 PASS + 0 FAIL + 1 KNOWN | 1 | [报告](browser_stop_load_20261004.md)；缺少加载持续不完成的现有靶场；完整加载页不能验证中止待处理导航 |
| `uiautoma.web.WebBrowser.extract_table()` | SKIPPED | 1/2 PASS + 0 FAIL + 1 KNOWN | 1 | [报告](browser_extract_table_20261004.md)；当前源码直接抛 UnsupportedActionError，未实现表格提取 |
| `uiautoma.web.WebElement.extract_table()` | SKIPPED | 1/2 PASS + 0 FAIL + 1 KNOWN | 1 | [报告](element_extract_table_20261004.md)；当前源码直接抛 UnsupportedActionError，未实现表格提取 |
| `uiautoma.web.WebElement.get_basetable_value()` | SKIPPED | 1/2 PASS + 0 FAIL + 1 KNOWN | 1 | [报告](element_get_basetable_value_20261004.md)；当前源码直接抛 UnsupportedActionError，未实现基础表格提取 |

## 缺陷

`is_enabled()`：原生输入框存在 `disabled="false"` 时，DOM 的 disabled=True，API 却返回 True；3/3 轮复现。HTML 布尔属性按是否存在决定状态，见 [HTML Standard](https://html.spec.whatwg.org/multipage/common-microsyntaxes.html#boolean-attributes)。[本地 Issue 草稿与复现入口](../../issues/drafts/is_enabled_disabled_false_20261004.md)。没有修改产品源码。

## 跳过与通过范围

- 尚缺库中关闭按钮：auto_handle_popup / remove_all_auto_handle_popup。2026-10-05 核对已发现 keys-click-test 的 DOM Modal；本批次旧原始报告保留，真实自动关闭验收仍未执行。
- 缺少持续加载页面：stop_load。
- 当前源码未实现：fingerprint / 两个 extract_table / get_basetable_value。
- 原生 Provider 不可用：get_bounding / get_anchor_position / highlight / handle_upload_dialog；drag_to 的 simulative=True 分支也跳过。
- 通过只覆盖各报告列出的浏览器、目标、模式和边界；原生 upload、其他 DPI、未列出的参照系等没有宣称通过。

## 清理与复测

全部创建资源的运行 cleanup 均 PASS，标签数 1→1，删除了本次临时库/文件并关闭本次对话框。用户原始元素库和原页面保留。

最终归档核对：[验证结果](artifacts/remaining_web_20261004_validation.json)确认 65 份正式报告、58 次资源清理、32 个脚本的语法、报告链接与逐项索引计数一致。预先存在的临时材料和用户未跟踪的 sdk测试.geany 保留。

在 `D:\code\元素库\sdk测试` 运行全部或指定一个 API：

```powershell
uv run .\web\run_remaining_web_apis.py
uv run .\web\run_remaining_web_apis.py --api element.is_checked
```

当前批次因 is_enabled 缺陷整体退出码为 1；跳过不计成功功能验收。原始 [汇总 JSON](artifacts/remaining_web_20261004_summary.json)、每项三轮/单轮报告、[合同快照](../remaining_web_contracts_20261004.json)均保留。

公开 API 文档需要用户确认后通过 Issue 交接；本次只更新测试侧脚本、证据和索引。

本次提交仅保存在本地。此前远端推送被自动审批拒绝（远端归属及具体内容授权未充分确认），本轮未重试推送。
