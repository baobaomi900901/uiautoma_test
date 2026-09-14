# `uiautoma.web.WebElement.download()` 验证证据

```yaml
api: "uiautoma.web.WebElement.download"
lifecycle: "READY_FOR_LIVE"
verification_summary:
  chrome_api_contract_ok: "PASS"
  chrome_download_blob_txt_wait_complete_ok: "FAIL"
  cleanup: "PASS"
  verified: false
  exit_code: 1
  note: "点击后原生另存为无人处理 → web_download_timeout"
source_access:
  user_authorized: true
  authorization_scope:
    - "uiautoma.web.WebElement.download 的最小 SDK→download_prepare/click/download_wait 路径"
source_review:
  status: "reviewed_with_known_defect"
  fingerprint_kind: "Git blob of current working-tree content"
  source_files:
    - path: "sdk/src/uiautoma/web/element.py"
      symbols: ["WebElement.download"]
      fingerprint: "3c55dadd2bf0009245d099efa8bfe82595b78b1b"
      note: "ensure_supported(simulative is False)；不调用 handle_save_dialog"
    - path: "sdk/src/uiautoma/_core/client.py"
      symbols: ["WebElement.download", "Client.web_download_prepare", "Client.web_download_wait"]
      fingerprint: "e8ca31c87da25aa663eb77f60715a28663557e11"
    - path: "automation_pipe_server.py"
      symbols: ["AutomationDispatcher._handle_web_download_prepare", "AutomationDispatcher._handle_web_download_wait"]
      fingerprint: "23a56351fce260eaccdfa8a4465519e0ffd85a73"
    - path: "runtime/services/action_service.py"
      symbols: ["ActionService.web_download_prepare", "ActionService.web_download_wait"]
      fingerprint: "e22dabe54069b646992d783cdd0b47a7f8ffd3cd"
    - path: "chrome/engine/plugin_packages/browser_command_package.js"
      symbols: ["download_prepare", "waitDownload"]
      fingerprint: "c6878a2a03acb7ba28320ecbc93072bc76cbb61e"
      note: "output_dir 未用于强制下载目录；仅监听 chrome.downloads"
  verified_contract:
    signature: "download(file_folder, *, file_name=None, overwrite=True, wait_complete=True, wait_complete_timeout=300, simulative=False, clipboard_input=True, dialog_timeout=20, force_ime_ENG=False, send_key_delay=50, focus_timeout=1000) -> str"
    parameter_order:
      - "self"
      - "file_folder"
      - "file_name"
      - "overwrite"
      - "wait_complete"
      - "wait_complete_timeout"
      - "simulative"
      - "clipboard_input"
      - "dialog_timeout"
      - "force_ime_ENG"
      - "send_key_delay"
      - "focus_timeout"
    defaults:
      file_name: null
      overwrite: true
      wait_complete: true
      wait_complete_timeout: 300
      simulative: false
      clipboard_input: true
      dialog_timeout: 20
      force_ime_ENG: false
      send_key_delay: 50
      focus_timeout: 1000
    return_annotation: "str"
    tested_mode: "chrome"
    status_model: ["PASS", "FAIL", "BLOCKED"]
persistent_script:
  path: "tests/SDK/web/test_web_element_download.py"
  fingerprint_kind: "Git blob of current working-tree content"
  fingerprint: "29db6bc487e75f7155790440ed5c8fa3e5a42c72"
test_assets:
  element_library_manifest: "tests/SDK/web/web测试元素库/elements.json"
  element_library_manifest_fingerprint: "ab217702c9e9c559302b57f652e5fbf33d714967"
  download_element_name: "下载txt按钮"
  characteristics: "//button[@id='btn-download-blob-txt']"
source_commit_at_doc_time: "9b47dbe762aa996b45f88e5e6c38d044ac76411f"
known_issue: "https://github.com/uiautoma/desktop/issues/29"
```

## 持久化脚本

脚本：`tests/SDK/web/test_web_element_download.py`

```powershell
uv run --extra dev python tests/SDK/web/test_web_element_download.py --mode chrome
uv run --extra dev python tests/SDK/web/test_web_element_download.py --contract-only
```

真实验证默认 `wait_complete_timeout=30`（合同默认 300）。脚本复制元素库到
`.pytest_tmp/<run_id>/` 并清空捕获期 `WebSessionId`，另建唯一下载目录；`finally`
删除上述副本。

目标 `download(...)` 异常与路径输出到 stderr，避免污染 stdout 的 JSON 报告。

## API 角色划分

- 场景准备 API：`web.create()`、`uiautoma.open()`、`page.find()`、页面激活、生成本次下载目录。
- 目标 API：对 `下载txt按钮` 直接调用
  `download(folder, file_name=..., wait_complete=True, wait_complete_timeout=30, ...)`。
- 副作用验收：返回 `str` 路径，且落盘文件存在、大小 > 0。
- 清理 API：关闭元素库连接、关闭本次测试页面、删除临时库副本与下载目录。

## 最小实现链

```text
uiautoma.web.WebElement.download
  -> ensure_supported(simulative is False)
  -> RawWebElement.download(output_dir, filename, wait_complete_timeout, click_timeout)
       -> web_download_prepare
       -> element.click
       -> web_download_wait  # chrome.downloads.onCreated/onChanged
  # 不调用 web.handle_save_dialog / 不操作原生另存为
```

## 覆盖矩阵

| 场景 | 结果 | 验收内容 |
| --- | --- | --- |
| 公开签名 | `PASS` | keyword-only、默认值、`str` |
| 预检 / 页面 / 库 | `PASS` | download-dialog-test 与 `下载txt按钮` |
| `wait_complete=True` | `FAIL` | `web_download_timeout`；另存为残留 |
| 精确清理 | `PASS` | `4/4`（不含强制关闭用户另存为） |

## 最近一次真实验证

- 日期：2026-08-09
- 模式：`chrome`
- Profile：`Default`
- 总状态：`FAIL`
- 退出码：`1`
- 生命周期提示：`READY_FOR_LIVE`
- 产品源码修改：无
- 现场证据：点击后出现原生「另存为」，默认文件名 `notes.txt`，无人点「保存」

## 明确排除

- Edge、CEF、Auto
- `simulative=True`
- `file_name=None` 默认资源名完整矩阵
- `overwrite=False`
- 主动关闭残留另存为（探测后需人工或另脚本清理）

## 跟踪 Issue

https://github.com/uiautoma/desktop/issues/29

相关：`handle_save_dialog(wait_complete=True)` 同类超时见 #9。
