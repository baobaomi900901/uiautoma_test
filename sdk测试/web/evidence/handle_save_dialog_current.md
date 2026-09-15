# `uiautoma.web.handle_save_dialog()` 初次测试

## 用途

处理浏览器的原生“另存为”对话框，输入文件夹/文件名并确认或取消保存，返回保存路径或空字符串。

## 测试对象

- 靶场：[download-dialog-test](https://baobaomi900901.github.io/xpath/#/download-dialog-test)
- 下载元素：`web靶场_下载对话框测试 _下载txt`
- 元素库：`D:\code\元素库\260902_web元素`
- 浏览器模式：默认 Chrome（可用 `--mode edge` 单独复测）

## 脚本

`web/test_web_handle_save_dialog_current.py`

脚本先通过 `web.create()` 打开靶场、连接元素库并通过元素库名称获取下载元素，
再激活页面并以 `simulative=False` 触发 DOM 点击，避免用户已有 Chrome 会话的
`browser_host_window_mismatch` 物理窗口绑定问题。旧脚本辅助函数依赖不存在的 `WebBrowser.raw`，
不再复用。
元素库名称是查找键，网页运行时 `WebElement.name` 可能是按钮显示文本（本靶场为“下载 demo.txt”），
两者不要求相等；测试只校验运行时元素拥有有效 ID 且可调用点击。
测试文件写入随机临时目录；结束时关闭 Package、页面并删除临时目录。

## 验收场景

| 测试项 | 验收标准 |
|---|---|
| API 合同 | 公开参数顺序、默认值和关键字规则符合源码 |
| 页面与元素准备 | 靶场打开、元素库连接和下载元素名称匹配 |
| 确认保存 | 点击下载元素后调用 `dialog_result="ok"`，返回路径正确且文件存在 |
| 取消保存 | 再次触发后 `dialog_result="cancel"` 返回空字符串 |
| 非法对话框结果 | 非法值在打开对话框前被拒绝 |
| 参数边界 | `file_name` 位置传入被 `TypeError` 拒绝 |
| 资源清理 | Package、网页和临时目录全部清理 |

## 执行

```powershell
uv run .\web\test_web_handle_save_dialog_current.py
```

仅检查公开合同：

```powershell
uv run .\web\test_web_handle_save_dialog_current.py --contract-only
```

## 当前状态

脚本和文档已建立，等待真实浏览器验收。原有旧脚本使用 `localhost:7199`、旧元素名和旧参数名，
不作为本轮结果依据。

本轮真实运行结果：页面与下载元素准备通过，按钮点击阶段通过；`save_ok` 调用
`handle_save_dialog()` 返回 `ActionError`，`trace=browser_host_window_mismatch`，结果为
`3/4` 通过，退出码 `1`。Package、页面和临时下载目录已清理。

已提交产品缺陷：[Issue #57](https://github.com/uiautoma/desktop/issues/57)。在缺陷修复前，
本 API 保持 `READY_FOR_LIVE`，不能标记为 `VERIFIED`。

## 2026-09-14：用户指定 CSS 路径复测

用户已打开靶场，因此复用 `web.get(url=靶场URL, mode="chrome")`，不创建或关闭用户页面，
不连接元素库、不切换 Profile、不改浏览器设置。独立脚本：`web/test_web_handle_save_dialog_css.py`。

按用户指定调用执行（补上保存目录与 `ok` 之间缺失的逗号）：

```python
web_element = web_object.find_by_css("button[id='link-download-txt'] span")
web_element.click()
web.handle_save_dialog(
    r"D:\code\pytest\download", "ok", "chrome",
    file_name="123.txt", wait_appear_timeout=20,
)
```

结果：6/7 通过，退出码 1，总耗时 1268.9ms。

| 阶段 | 结果 |
| --- | --- |
| 输出保护 | 123.txt 运行前不存在，未覆盖既有文件 |
| 连接现有页面 | 通过 |
| CSS 查找 | 通过，运行时名称为“下载 demo.txt” |
| 默认 click() | 通过，返回 None，1121.9ms |
| handle_save_dialog | 失败，ActionError / browser_host_window_mismatch，9.8ms |
| 文件核验 | 未执行（API 已失败）；随后检查 123.txt 未生成 |
| 页面处理 | 用户原页面保留；未发送全局 Esc，也未声称原生对话框已关闭 |

本次 `trace_id`：`7ab1dffad6dc4ebca676ca3870889e20`。
上述结果表明 CSS 查找和默认点击调用均可完成，但保存 API 的窗口匹配错误仍可复现；
不能根据点击返回 None 单独断言保存对话框一定已出现，具体窗口绑定原因仍由 Issue #57 跟踪。

复测命令（先打开靶场，并确保输出目录中没有需保留的同名文件）：

```powershell
uv run .\web\test_web_handle_save_dialog_css.py
```

## 2026-09-14：CSS 场景复测成功

在清理桥接进程冲突并重新连接已打开页面后，按同一 CSS 场景复测通过：

- `find_by_css("button[id='link-download-txt'] span")`：通过
- 默认 `click()`：通过，返回 `None`
- `handle_save_dialog(r"D:\code\pytest\download", "ok", "chrome", file_name="123.txt", wait_appear_timeout=20)`：通过
- 文件读回：通过，返回路径正确，TXT 已落盘（55 字节）
- 用户页面：保留未关闭

结果：**8/8 通过，退出码 0，总耗时 2445.6ms**。

该结果证明指定 CSS 下载场景当前可用；取消保存、覆盖策略、等待完成和非法参数等完整合同场景仍待独立复测，因此 API 总状态继续保持 `READY_FOR_LIVE`。

## 2026-09-14：Chrome 重启后完整复测

重启 Chrome 后运行 `web/test_web_handle_save_dialog_current.py`，结果 **7/7 通过，退出码 0**：
页面与元素准备、确认保存、刷新后取消保存、非法 `dialog_result`、关键字参数规则和临时资源清理全部通过。
本次保存场景耗时约 1918ms，取消场景耗时约 2046ms。

据此，当前脚本覆盖范围内的 `handle_save_dialog()` 初次测试状态更新为 `VERIFIED`；
`wait_complete=True`、覆盖策略等未列入本脚本的扩展场景仍不在本次结论内。

Issue #57 已补充最新复测证据：
[comment-5657686373](https://github.com/uiautoma/desktop/issues/57#issuecomment-5657686373)。
Chrome 重启后窗口匹配错误未再复现；Issue 保持开放，等待维护者确认原始路由冲突是否已根治。
