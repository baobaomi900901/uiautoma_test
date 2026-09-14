# `uiautoma.web.handle_save_dialog()` 验证证据

```yaml
api: "uiautoma.web.handle_save_dialog"
lifecycle: "READY_FOR_LIVE"
baseline_revalidation:
  source_commit: "a4598ec3221c8ffc9eb39f0b0beff7f8ca107a43"
  contract_only: "PASS"
  live_status: "BLOCKED"
  blocker: "远端 main 缺少本地 Web Stack 安装入口，无法刷新 Runtime 与插件"
verification_summary:
  default_save_scenario: "PASS"
  wait_complete_true_scenario: "FAIL"
  verified: false
  blocking_defect: "web_download_timeout"
source_access:
  user_authorized: true
  authorization_scope:
    - "uiautoma.web.handle_save_dialog 的最小 SDK、Runtime 和 Chromium 实现链"
source_review:
  status: "verified"
  fingerprint_kind: "Git blob of current working-tree content"
  source_files:
    - path: "sdk/src/uiautoma/web/__init__.py"
      symbols: ["handle_save_dialog", "_wait_save_dialog", "_save_dialog_target_path"]
      fingerprint: "a5e8b8fbcf23059b35ce7f2d9742ccf18039fd38"
    - path: "sdk/src/uiautoma/_core/client.py"
      symbols: ["UIAutomaCoreClient.send_keys", "UIAutomaCoreClient.web_download_prepare", "UIAutomaCoreClient.web_download_wait"]
      fingerprint: "16b3ce68f682e1485cd25c55de5ab2c9a9de6a33"
    - path: "runtime/services/pipe_server.py"
      symbols: ["AutomationDispatcher._handle_input_send_keys", "AutomationDispatcher._handle_web_download_prepare", "AutomationDispatcher._handle_web_download_wait"]
      fingerprint: "3d5054ddcbd79ad6816865c2a9d37f14e0975972"
    - path: "runtime/services/action_service.py"
      symbols: ["ActionService.send_keys", "ActionService.web_download_prepare", "ActionService.web_download_wait"]
      fingerprint: "003039f702f44764c258ab8fb30a9ffca384aded"
    - path: "chrome/engine/plugin_packages/browser_command_package.js"
      symbols: ["wireBrowserCapabilityListeners", "waitDownload", "download_prepare"]
      fingerprint: "f75c8c047d341c97535974c28c9d572d4dd927a1"
  verified_contract:
    signature: "handle_save_dialog(file_folder, dialog_result='ok', mode='cef', *, file_name=None, overwrite=True, wait_complete=False, wait_complete_timeout=300, simulative=False, clipboard_input=True, wait_appear_timeout=20, force_ime_ENG=False, send_key_delay=50, focus_timeout=1000) -> str"
    tested_mode: "chrome"
    passing_options:
      dialog_result: "ok"
      file_name: "unique explicit .txt name"
      overwrite: false
      wait_complete: false
      clipboard_input: true
      simulative: false
      force_ime_ENG: false
    status_model: ["PASS", "FAIL", "BLOCKED"]
  open_defects:
    - trace_info: "web_download_timeout"
      affected_option: "wait_complete=True"
      product_source_modified: false
persistent_script:
  path: "tests/SDK/web/test_web_handle_save_dialog.py"
  fingerprint_kind: "Git blob of current working-tree content"
  fingerprint: "f3488f9640c8e3e2fb2052782df51bbd4ee28830"
```

## 持久化脚本

脚本：`tests/SDK/web/test_web_handle_save_dialog.py`

```powershell
uv run python tests\SDK\web\test_web_handle_save_dialog.py `
  --mode chrome `
  --profile-directory Default `
  --target-url http://localhost:7199/download-dialog-test `
  --element-library "tests\SDK\web\web测试元素库" `
  --element-name "下载txt按钮" `
  --dialog-timeout 20 `
  --download-timeout 30
```

脚本依次预检靶场、Runtime、元素库和已有保存对话框，记录 Chrome 主窗口基线，打开带本次
UUID 的唯一页面，连接元素库并绑定“下载txt按钮”。场景准备通过该元素执行
`simulative=False` DOM 点击；目标断言只直接调用 `web.handle_save_dialog()`。

当前持久化场景使用 `wait_complete=False`，随后通过本地有界轮询确认本次唯一文件存在且
非空。`finally` 逐项处理本次保存对话框、元素库连接、页面和下载目录，并确认没有新增
Google Chrome 主窗口。

## 最小实现链

```text
uiautoma.web.handle_save_dialog
  -> 等待并聚焦原生保存对话框
  -> 计算本次目标路径
  -> UIAutomaCoreClient.send_keys
  -> AutomationDispatcher._handle_input_send_keys
  -> ActionService.send_keys
```

`wait_complete=True` 额外进入以下失败链：

```text
handle_save_dialog
  -> web_download_prepare
  -> Chromium downloadWaits.set(..., itemId=null)
  -> send_keys("{ENTER}")
  -> web_download_wait
  -> waitDownload 未获得 itemId
  -> web_download_timeout
```

真实页面点击在调用 `handle_save_dialog()` 之前已经触发下载。插件
`chrome.downloads.onCreated` 只遍历事件发生时已有的 `downloadWaits`，没有历史事件补查；
这与真实运行中文件存在但下载等待超时的结果一致。

## 覆盖矩阵

| 场景 | 结果 | 验收内容 |
| --- | --- | --- |
| 公开签名 | `PASS` | 参数顺序、默认值和参数种类全部匹配 |
| 靶场预检 | `PASS` | `/download-dialog-test` 返回 HTTP 200 |
| Runtime 预检 | `PASS` | Runtime 与 Automation Pipe 可响应 |
| 元素库预检 | `PASS` | “下载txt按钮”唯一命中，页面 URL 和 XPath 均匹配 |
| 保存对话框隔离 | `PASS` | 运行前没有用户已有保存对话框 |
| Chrome 主窗口基线 | `PASS` | 运行前主窗口数量为 `1` |
| 页面准备 | `PASS` | 复用现有 Chrome 会话，唯一 URL 和页面身份正确 |
| 元素库连接与绑定 | `PASS` | 元素库包含 `6` 个 Web 元素，目标元素名称正确 |
| 下载对话框触发 | `PASS` | DOM 点击返回 `None`，未启用坐标兜底 |
| 默认保存场景 | `PASS` | 返回字符串与目标路径匹配，文件存在且非空 |
| 精确清理 | `PASS` | 本次资源 `5/5` 清理，Chrome 主窗口 `1 -> 1`，新增 `0` |
| `wait_complete=True` | `FAIL` | 文件实际生成，但约 `31.5s` 后返回 `web_download_timeout` |

## 基线切换前最近一次用户验证：默认保存场景

- 日期：2026-08-06
- 模式：`chrome`
- Profile 目录：`Default`
- 总状态：`PASS`
- 退出码：`0`
- 靶场预检：约 `52.6ms`，HTTP 200
- Runtime 预检：约 `2.3ms`
- 元素库预检：约 `0.2ms`，目标元素唯一命中
- 保存对话框预检：约 `0.9ms`，已有对话框 `0`
- Chrome 主窗口基线：`1`
- 页面准备：约 `480.2ms`，复用已有 Chrome 会话
- 元素库连接：约 `11.8ms`，Web 元素 `6`
- 下载按钮点击：约 `242.2ms`
- `handle_save_dialog()`：约 `1458.5ms`
- 文件轮询：`2` 次，目标文件存在且非空
- 清理结果：`PASS`，本次资源 `5/5`
- Chrome 主窗口：`1 -> 1`，新增 `0`

## 产品缺陷复现：`wait_complete=True`

- 日期：2026-08-06
- 模式：`chrome`
- 结果：`FAIL`
- 异常：`ActionError`
- `trace_info`：`web_download_timeout`
- 目标调用耗时：约 `31476.6ms`
- 文件证据：清理前本次下载目录包含 `1` 个条目，文件实际已经生成
- 清理结果：`PASS`，当次资源 `4/4`
- 产品源码修改：未授权，未修改

## 明确排除

- Edge、CEF 和 Auto 真实行为。
- `dialog_result="cancel"`。
- `file_name=None` 时读取对话框默认文件名。
- `overwrite=True` 与同名文件覆盖。
- `wait_complete=True` 的成功行为；当前为已复现缺陷。
- `clipboard_input=False`。
- `simulative=True`。
- `force_ime_ENG=True`。
- 下载中断、网络失败与浏览器策略阻止下载。
- 并发出现的非本次保存对话框。
- Chrome Profile 显示名或账号与 Profile 目录的对应关系。
