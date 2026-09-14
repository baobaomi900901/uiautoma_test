# `uiautoma.web.WebElement.upload()` 验证证据

```yaml
api: "uiautoma.web.WebElement.upload"
lifecycle: "VERIFIED"
verification_summary:
  chrome_api_contract_ok: "PASS"
  chrome_upload_select_single_file_ok: "PASS"
  cleanup: "PASS"
  verified: true
  exit_code: 0
  note: "CDP DOM.setFileInputFiles 注入；非原生文件对话框"
source_access:
  user_authorized: true
  authorization_scope:
    - "uiautoma.web.WebElement.upload 的最小 SDK→web_upload_file_input→CDP setFileInputFiles 路径"
source_review:
  status: "verified"
  fingerprint_kind: "Git blob of current working-tree content"
  source_files:
    - path: "sdk/src/uiautoma/web/element.py"
      symbols: ["WebElement.upload"]
      fingerprint: "3c55dadd2bf0009245d099efa8bfe82595b78b1b"
      note: "ensure_supported(simulative is False)；仅 dialog_timeout 下传为 timeout"
    - path: "sdk/src/uiautoma/_core/client.py"
      symbols: ["WebElement.upload", "Client.web_upload_file_input"]
      fingerprint: "e8ca31c87da25aa663eb77f60715a28663557e11"
    - path: "automation_pipe_server.py"
      symbols: ["AutomationDispatcher._handle_web_upload_file_input"]
      fingerprint: "23a56351fce260eaccdfa8a4465519e0ffd85a73"
    - path: "runtime/services/action_service.py"
      symbols: ["ActionService.web_upload_file_input"]
      fingerprint: "e22dabe54069b646992d783cdd0b47a7f8ffd3cd"
    - path: "chrome/engine/plugin_packages/browser_command_package.js"
      symbols: ["setFileInputFiles", "upload_file_input"]
      fingerprint: "c6878a2a03acb7ba28320ecbc93072bc76cbb61e"
  verified_contract:
    signature: "upload(file_names, *, simulative=False, clipboard_input=True, dialog_timeout=20, force_ime_ENG=False, send_key_delay=50, focus_timeout=1000) -> None"
    parameter_order:
      - "self"
      - "file_names"
      - "simulative"
      - "clipboard_input"
      - "dialog_timeout"
      - "force_ime_ENG"
      - "send_key_delay"
      - "focus_timeout"
    defaults:
      simulative: false
      clipboard_input: true
      dialog_timeout: 20
      force_ime_ENG: false
      send_key_delay: 50
      focus_timeout: 1000
    return_annotation: "None"
    tested_mode: "chrome"
    status_model: ["PASS", "FAIL", "BLOCKED"]
persistent_script:
  path: "tests/SDK/web/test_web_element_upload.py"
  fingerprint_kind: "Git blob of current working-tree content"
  fingerprint: "672451067aa4dbb1e0fcfeb487c11d08b702dd9f"
test_assets:
  element_library_manifest: "tests/SDK/web/web测试元素库/elements.json"
  element_library_manifest_fingerprint: "ab217702c9e9c559302b57f652e5fbf33d714967"
  upload_element_name: "上传文件按钮"
  characteristics: "//input[@id='input-upload-single']"
  sample_selected_value: "C:\\fakepath\\uiautoma_web_element_upload_983ca8b4b61e40e399ec00fab1e79a7f.txt"
source_commit_at_doc_time: "c0168a094231f92114b64b5eed05a087c9286d30"
```

## 持久化脚本

脚本：`tests/SDK/web/test_web_element_upload.py`

```powershell
uv run --extra dev python tests/SDK/web/test_web_element_upload.py --mode chrome
uv run --extra dev python tests/SDK/web/test_web_element_upload.py --contract-only
```

`--mode` 默认即为 `chrome`。脚本会复制元素库到 `.pytest_tmp/<run_id>/` 并清空捕获期
`WebSessionId`，在另一 `.pytest_tmp/<fixture_id>/` 生成唯一上传文本文件；`finally` 中删除
上述副本与夹具。

目标 `upload(...)` 与佐证 `get_value()` 结果输出到 stderr，避免污染 stdout 的 JSON 报告。

## API 角色划分

- 场景准备 API：`web.create()`、`uiautoma.open()`、`page.find()`、页面激活、生成本次唯一文本文件。
- 目标 API：对 `上传文件按钮` 直接调用
  `upload([path], clipboard_input=True, focus_timeout=1000, dialog_timeout=20)`。
- 副作用验收：轮询 `get_value()`，核对非空且文件名与本次夹具一致。
- 清理 API：关闭元素库连接、关闭本次测试页面、删除临时库副本与上传夹具。

## 最小实现链

```text
uiautoma.web.WebElement.upload
  -> ensure_supported(simulative is False)
  -> RawWebElement.upload(file_names, timeout=dialog_timeout)
  -> Client.web_upload_file_input
  -> ActionService.web_upload_file_input
  -> browser command upload_file_input
  -> CDP DOM.setFileInputFiles
```

## 覆盖矩阵

| 场景 | 结果 | 验收内容 |
| --- | --- | --- |
| 公开签名 | `PASS` | keyword-only、默认值、`None` |
| 预检 / 页面 / 库 | `PASS` | upload-dialog-test 与 `上传文件按钮` |
| 单文件 `upload([...])` | `PASS` | 返回 `None`；`get_value` 文件名匹配 |
| 精确清理 | `PASS` | `4/4` |

## 最近一次真实验证

- 日期：2026-08-09
- 模式：`chrome`
- Profile：`Default`
- 总状态：`PASS`
- 退出码：`0`
- 生命周期：`VERIFIED`
- 产品源码修改：无
- 佐证示例：`selected_value=C:\fakepath\uiautoma_web_element_upload_983ca8b4b61e40e399ec00fab1e79a7f.txt`

## 明确排除

- Edge、CEF、Auto
- `simulative=True`（当前显式 unsupported）
- 多文件 / `multiple` input
- 原生文件选择对话框路径输入（见 `handle_upload_dialog`）
- `clipboard_input=False` / 键盘逐字路径输入行为差异
