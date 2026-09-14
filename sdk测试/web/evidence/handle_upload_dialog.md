# `uiautoma.web.handle_upload_dialog()` 验证证据

```yaml
api: "uiautoma.web.handle_upload_dialog"
lifecycle: "READY_FOR_LIVE"
baseline_revalidation:
  source_commit: "a4598ec3221c8ffc9eb39f0b0beff7f8ca107a43"
  contract_only: "PASS"
  live_status: "BLOCKED"
  blocker: "远端 main 缺少本地 Web Stack 安装入口，无法刷新 Runtime 与插件"
verification_summary:
  chrome_single_file_ok: "PASS"
  cleanup: "PASS"
  verified: false
  historical_exit_code: 0
source_access:
  user_authorized: true
  authorization_scope:
    - "uiautoma.web.handle_upload_dialog 的最小 SDK 与 Runtime 实现链"
source_review:
  status: "verified"
  fingerprint_kind: "Git blob of current working-tree content"
  source_files:
    - path: "sdk/src/uiautoma/web/__init__.py"
      symbols: ["handle_upload_dialog", "_wait_upload_dialog", "_upload_dialog_filenames_text"]
      fingerprint: "a5e8b8fbcf23059b35ce7f2d9742ccf18039fd38"
    - path: "sdk/src/uiautoma/_core/client.py"
      symbols: ["UIAutomaCoreClient.send_keys"]
      fingerprint: "16b3ce68f682e1485cd25c55de5ab2c9a9de6a33"
    - path: "runtime/services/pipe_server.py"
      symbols: ["AutomationDispatcher._handle_input_send_keys"]
      fingerprint: "3d5054ddcbd79ad6816865c2a9d37f14e0975972"
    - path: "runtime/services/action_service.py"
      symbols: ["ActionService.send_keys"]
      fingerprint: "003039f702f44764c258ab8fb30a9ffca384aded"
  verified_contract:
    signature: "handle_upload_dialog(filenames, dialog_result='ok', mode='cef', *, simulative=False, clipboard_input=True, wait_appear_timeout=20, force_ime_ENG=False, send_key_delay=50, focus_timeout=1000) -> None"
    tested_mode: "chrome"
    passing_options:
      filenames: "single existing unique .txt path"
      dialog_result: "ok"
      simulative: false
      clipboard_input: true
      wait_appear_timeout: 20
      force_ime_ENG: false
      send_key_delay: 50
      focus_timeout: 1000
    status_model: ["PASS", "FAIL", "BLOCKED"]
persistent_script:
  path: "tests/SDK/web/test_web_handle_upload_dialog.py"
  fingerprint_kind: "Git blob of current working-tree content"
  fingerprint: "1a357a434823627f1bee29d998a8af4747f93479"
test_assets:
  element_library_manifest: "tests/SDK/web/web测试元素库/elements.json"
  element_library_manifest_fingerprint: "1773a727663643cd29d5cef4eb56ff8db59d3cdd"
  element_name: "上传文件按钮"
```

## 持久化脚本

脚本：`tests/SDK/web/test_web_handle_upload_dialog.py`

```powershell
uv run python tests\SDK\web\test_web_handle_upload_dialog.py `
  --mode chrome `
  --profile-directory Default `
  --target-url "http://localhost:7199/upload-dialog-test?" `
  --element-library "tests\SDK\web\web测试元素库" `
  --element-name "上传文件按钮" `
  --dialog-timeout 20 `
  --post-upload-timeout 5
```

省略 `--upload-file` 时，脚本在忽略的 `.pytest_tmp/` 下创建本次 UUID 隔离的唯一文本文件，
并在 `finally` 中精确删除。传入 `--upload-file` 时只使用该文件，不负责删除用户文件。

## API 角色划分

- 场景准备 API：`web.create()`、`uiautoma.open()`、`page.find()` 和
  `element.click(simulative=True)`。
- 场景准备边界：临时激活唯一 Chrome 窗口；必要时通过 Windows
  `AttachThreadInput` 获得真实鼠标点击所需的前台焦点。
- 目标 API：只直接调用一次 `web.handle_upload_dialog()`。
- 目标后置断言：通过上传 input 的实时 `value` 确认文件名，不用其他上传 API 代替证明。
- 清理 API：关闭本次原生窗口、元素库连接和页面，恢复 Chrome placement 与原前台焦点，
  删除本次生成的测试文件。

DOM 合成点击不能作为 `<input type="file">` 的可信用户动作，因此场景准备使用元素库目标的
真实鼠标点击。该点击和 Windows 焦点处理不属于目标 API 行为。

## 最小实现链

```text
uiautoma.web.handle_upload_dialog
  -> _wait_upload_dialog
  -> _find_upload_dialog_window
  -> _upload_dialog_filenames_text
  -> UIAutomaCoreClient.send_keys
  -> AutomationDispatcher._handle_input_send_keys
  -> ActionService.send_keys
```

确认分支依次发送 `Ctrl+A`、带引号的文件路径和 `Enter`。本轮目标返回值为 `None`。

## 覆盖矩阵

| 场景 | 结果 | 验收内容 |
| --- | --- | --- |
| 公开签名 | `PASS` | 参数顺序、默认值、参数种类和 `None` 返回注解匹配 |
| 靶场预检 | `PASS` | `/upload-dialog-test?` 返回 HTTP 200 |
| Runtime 预检 | `PASS` | Runtime 与 Automation Pipe 可响应 |
| 元素库预检 | `PASS` | “上传文件按钮”唯一命中，页面 URL 和 XPath 匹配 |
| 上传对话框隔离 | `PASS` | 运行前没有用户已有上传对话框 |
| 上传文件准备 | `PASS` | 本次唯一 `.txt` 文件存在且非空 |
| 页面准备 | `PASS` | 复用现有 Chrome 会话，唯一 URL 和页面身份正确 |
| 元素库连接 | `PASS` | 元素库包含 `7` 个 Web 元素，目标元素名称正确 |
| 窗口与焦点准备 | `PASS` | 唯一可见 Chrome 窗口为 normal，并通过受控线程连接取得焦点 |
| 上传对话框触发 | `PASS` | 真实鼠标点击返回 `None`，未启用坐标兜底 |
| 目标 API | `PASS` | 返回 `None`，input value 非空且文件名匹配 |
| 精确清理 | `PASS` | 本次资源 `6/6` 清理，Chrome 主窗口 `1 -> 1`，新增 `0` |

## 基线切换前最近一次真实验证

- 日期：2026-08-06
- 模式：`chrome`
- Profile 目录：`Default`
- 总状态：`PASS`
- 退出码：`0`
- 靶场预检：约 `37.1ms`，HTTP 200
- Runtime 预检：约 `2.5ms`
- 元素库预检：约 `0.2ms`，目标元素唯一命中
- 上传对话框预检：约 `1.1ms`，已有对话框 `0`
- Chrome 主窗口基线：`1`
- 页面准备：约 `484.6ms`，复用已有 Chrome 会话
- 元素库连接：约 `11.1ms`，Web 元素 `7`
- 窗口与焦点准备：约 `584.5ms`，`focus_method=attach_thread_input`
- 上传元素点击：约 `1093.5ms`，真实鼠标点击
- `handle_upload_dialog()`：约 `1677.8ms`
- 页面文件名确认：轮询 `2` 次，value 非空且文件名匹配
- 清理结果：`PASS`，本次资源 `6/6`
- Chrome 主窗口：`1 -> 1`，新增 `0`
- Chrome placement：恢复确认 `PASS`
- 原前台焦点：恢复确认 `PASS`
- 产品源码修改：无

## 明确排除

- Edge、CEF 和 Auto 真实行为。
- `dialog_result="cancel"`。
- `filenames` 为多文件列表。
- `clipboard_input=False`。
- `handle_upload_dialog(simulative=True)` 的差异行为。
- `force_ime_ENG=True`。
- 不存在、不可读或被锁定的上传文件。
- Chrome 全屏窗口状态。
- 服务端接收、解析和存储上传文件。
- 并发出现的非本次上传对话框。
- Chrome Profile 显示名或账号与 Profile 目录的对应关系。
