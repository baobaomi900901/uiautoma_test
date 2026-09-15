# `uiautoma.web.handle_upload_dialog()` 初次测试

## 用途

处理浏览器原生文件选择对话框，选择一个或多个文件并确认/取消上传。

## 测试对象

- 靶场：[upload-dialog-test](https://baobaomi900901.github.io/xpath/#/upload-dialog-test)
- 触发元素：`web靶场_上传对话框测试 _原生_上传组件`
- 元素库：`D:\code\元素库\260902_web元素`
- 浏览器模式：默认 Chrome（可用 `--mode edge` 单独复测）

## 脚本

`web/test_web_handle_upload_dialog_current.py`

脚本打开靶场、连接元素库并获取上传按钮，确认用户指定的上传文件存在；点击按钮后调用
`handle_upload_dialog()`，再从文件输入元素/页面状态读回文件名。测试结束关闭 Package、页面和系统弹窗，用户指定文件始终保留。

## 验收场景

| 测试项 | 验收标准 |
|---|---|
| API 合同 | 参数顺序、默认值和位置/关键字规则符合源码 |
| 上传文件准备 | 用户指定文件存在，脚本不会删除 |
| 页面与元素准备 | 上传靶场、元素库和可操作按钮均就绪 |
| 确认上传 | `dialog_result="ok"` 返回 `None`，页面读回用户指定文件名 |
| 取消上传 | `dialog_result="cancel"` 返回 `None` |
| 非法对话框结果 | 非法值被拒绝 |
| 参数边界 | 关键字参数位置传入被 `TypeError` 拒绝 |
| 资源清理 | Package、页面和系统弹窗已清理；用户文件保留 |

## 执行

```powershell
uv run .\web\test_web_handle_upload_dialog_current.py
```

仅检查公开合同：

```powershell
uv run .\web\test_web_handle_upload_dialog_current.py --contract-only
```

调试失败场景、保留网页和系统上传弹窗供人工确认：

```powershell
uv run .\web\test_web_handle_upload_dialog_current.py --preserve-on-failure
```

该选项只在已有失败项时生效；失败时清理项会明确标记为“保留”，避免误以为资源已关闭。

默认上传文件：`C:\Users\moby\Desktop\jianfa260819.lnc`。也可显式指定：

```powershell
uv run .\web\test_web_handle_upload_dialog_current.py --upload-file "C:\Users\moby\Desktop\jianfa260819.lnc"
```

## 当前状态

脚本和文档已建立，等待真实浏览器验收。原有旧脚本仍使用旧的 localhost 靶场和元素名称，
不作为本轮结果依据；运行失败时会保留 `trace_info` 以区分页面、点击、Native Host 或对话框问题。

## 2026-09-14：Chrome 重启后复测

页面和上传按钮准备通过；点击后已进入上传对话框，但 `handle_upload_dialog()` 在确认阶段失败：

```text
ActionError: 无法识别文件对话框的确定按钮
trace=web_dialog_failed
```

结果：3/4 通过，退出码 1；页面和临时上传文件已清理。旧版本测试脚本只关闭网页，
可能遗留系统上传弹窗；脚本现已在清理阶段先关闭可识别的本次上传对话框。该失败与之前的
`browser_host_window_mismatch` 不同，当前定位为 Runtime 对上传对话框“确定/打开”按钮的识别问题。
API 保持 `READY_FOR_LIVE`，暂不标记为 `VERIFIED`。

## 2026-09-14：Chrome 重启后复测

重启 Chrome 后运行完整脚本：页面与上传元素准备通过（约 283ms），但 `upload_ok` 在
上传对话框确认阶段失败：

```text
ActionError: 无法识别文件对话框的确定按钮
trace=web_dialog_failed
```

结果：3/4 通过，退出码 1；Package、页面和临时上传文件已清理。此前的
`browser_host_window_mismatch` 已不再出现，说明 Chrome 重启后窗口绑定问题消失；
当前剩余问题是 Runtime 无法识别原生上传对话框的确认/打开按钮。该场景尚未提交新 Issue，
API 仍保持 `READY_FOR_LIVE`。

最新证据已同步到 Issue #57 的
[复测评论](https://github.com/uiautoma/desktop/issues/57#issuecomment-5657686373)：
上传场景当前失败追踪为 `web_dialog_failed`，与 Issue 原始的
`browser_host_window_mismatch` 区分记录。

本轮真实运行结果：页面与上传元素准备通过，`upload_ok` 调用
`handle_upload_dialog()` 返回 `ActionError`，`trace=browser_host_window_mismatch`，结果为
`3/4` 通过，退出码 `1`；Package、页面和临时上传文件已清理。

该问题已作为保存对话框 Issue 的补充复现提交：
[Issue #57](https://github.com/uiautoma/desktop/issues/57#issuecomment-5654416032)。
在修复前，本 API 保持 `READY_FOR_LIVE`，不能标记为 `VERIFIED`。
