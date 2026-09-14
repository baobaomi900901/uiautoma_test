# `uiautoma.web.WebElement.input()` 验证证据

```yaml
api: "uiautoma.web.WebElement.input"
lifecycle: "VERIFIED"
verification_summary:
  chrome_background_basic_ok: "PASS"
  chrome_simulative_basic_ok: "PASS"
  chrome_background_append_ok: "PASS"
  chrome_background_delay_after_ok: "PASS"
  cleanup: "PASS"
  verified: true
  exit_code: 0
source_access:
  user_authorized: true
  authorization_scope:
    - "uiautoma.web.WebElement.input 的最小 SDK、Runtime 与 DOM/键盘输入实现链"
source_review:
  status: "verified"
  fingerprint_kind: "Git blob of current working-tree content"
  source_files:
    - path: "sdk/src/uiautoma/web/element.py"
      symbols: ["WebElement.input", "WebElement._finish"]
      fingerprint: "3c55dadd2bf0009245d099efa8bfe82595b78b1b"
    - path: "sdk/src/uiautoma/_core/client.py"
      symbols: ["WebElement.type_text", "LibrarySession._run_web_action"]
      fingerprint: "e8ca31c87da25aa663eb77f60715a28663557e11"
    - path: "automation_pipe_server.py"
      symbols: ["AutomationDispatcher._handle_web_action_type_text"]
      fingerprint: "3d5054ddcbd79ad6816865c2a9d37f14e0975972"
    - path: "runtime/services/action_service.py"
      symbols: ["ActionService.web_type_text_element", "ActionService._run_web_type_text_with_text_backend_if_needed"]
      fingerprint: "e22dabe54069b646992d783cdd0b47a7f8ffd3cd"
  verified_contract:
    signature: "input(text, *, simulative=True, cdp_input=False, append=False, driver_input=False, contains_hotkey=False, force_ime_ENG=False, force_img_ENG=None, send_key_delay=50, focus_timeout=1000, delay_after=1, click_before_input=True, anchor=None, input_check=False, retry_times=3, check_value='') -> None"
    parameter_order:
      - self
      - text
      - simulative
      - cdp_input
      - append
      - driver_input
      - contains_hotkey
      - force_ime_ENG
      - force_img_ENG
      - send_key_delay
      - focus_timeout
      - delay_after
      - click_before_input
      - anchor
      - input_check
      - retry_times
      - check_value
    defaults:
      simulative: true
      cdp_input: false
      append: false
      driver_input: false
      contains_hotkey: false
      force_ime_ENG: false
      force_img_ENG: null
      send_key_delay: 50
      focus_timeout: 1000
      delay_after: 1
      click_before_input: true
      anchor: null
      input_check: false
      retry_times: 3
      check_value: ""
    text_required: true
    tested_mode: "chrome"
    status_model: ["PASS", "FAIL", "BLOCKED"]
persistent_script:
  path: "tests/SDK/web/test_web_element_input.py"
  fingerprint_kind: "Git blob of current working-tree content"
  fingerprint: "0d9cf642941c0bf39cb0aa13923544f5667112de"
test_assets:
  element_library_manifest: "tests/SDK/web/web测试元素库/elements.json"
  element_library_manifest_fingerprint: "4185c3ca90dfa44632b2e3f833b17ab6455a7cc8"
  input_element_name: "input元素"
  submit_element_name: "提交_html"
  reset_element_name: "重置_html"
source_commit_at_doc_time: "45c1cf47c5f2c8b65e98615f36a7b81b34fee890"
```

## 持久化脚本

脚本：`tests/SDK/web/test_web_element_input.py`

```powershell
uv run --extra dev python tests/SDK/web/test_web_element_input.py
```

仅检查公开签名：

```powershell
uv run --extra dev python tests/SDK/web/test_web_element_input.py --contract-only
```

`--mode` 默认即为 `chrome`。脚本会复制元素库到 `.pytest_tmp/<run_id>/` 并清空捕获期
`WebSessionId`，避免陈旧会话拦截当前页面绑定；`finally` 中删除该副本。

输入步骤日志输出到 stderr，避免污染 stdout 的 JSON 报告。

## API 角色划分

- 场景准备 API：`web.create()`、`uiautoma.open()`、`page.find()`、页面激活，以及
  `重置_html` / `提交_html` 的 `click()`。
- 目标 API：只对 `input元素` 直接调用 `WebElement.input(...)`。
- 清理 API：关闭元素库连接、关闭本次测试页面、删除临时库副本。

## 最小实现链

```text
uiautoma.web.WebElement.input
  -> RawWebElement.type_text
  -> LibrarySession._run_web_action("web.action.type_text")
  -> AutomationDispatcher._handle_web_action_type_text
  -> ActionService.web_type_text_element
  -> ActionService._run_web_type_text_with_text_backend_if_needed
  -> 浏览器插件/引擎或模拟键盘写入输入框
```

## 覆盖矩阵

| 场景 | 结果 | 验收内容 |
| --- | --- | --- |
| 公开签名 | `PASS` | 参数顺序、默认值、`text` 必填、`None` 返回注解 |
| 靶场预检 | `PASS` | `/form-controls` HTTP 200 |
| Runtime 预检 | `PASS` | Runtime 与 Automation Pipe 可响应 |
| 元素库预检 | `PASS` | `input元素` / `提交_html` / `重置_html` 唯一命中 |
| 临时库会话清理 | `PASS` | 清空捕获期 session 字段后副本可用 |
| 页面准备 | `PASS` | 复用 Chrome 会话，唯一 URL 与页面身份正确 |
| 元素库连接 | `PASS` | 三个库项名称绑定正确 |
| 后台基础输入 | `PASS` | 剪贴板 JSON `text == "123"` |
| 模拟人工基础输入 | `PASS` | 剪贴板 JSON `text == "123"` |
| 后台追加输入 | `PASS` | 前缀+后缀拼接为 `123` |
| 后台 `delay_after=1` | `PASS` | 耗时 ≥900ms 且文本正确 |
| 精确清理 | `PASS` | 本次资源 `3/3` |

## 最近一次真实验证

- 日期：2026-08-08
- 模式：`chrome`
- Profile 目录：`Default`
- 总状态：`PASS`
- 退出码：`0`
- 靶场：`http://localhost:7199/form-controls`
- 输入元素：`input元素`
- 验收方式：点击 `提交_html` 后读取剪贴板表单 JSON 的 `text`
- `input_background_basic`：约 `232.4ms`，`text=123`
- `input_simulative_basic`：约 `2415.3ms`，`text=123`
- `input_background_append`：约 `470.7ms`，`text=123`
- `input_background_delay_after`：约 `1041.4ms`，`text=123`
- 清理结果：`PASS`，本次资源 `3/3`
- 产品源码修改：无

## 明确排除

- Edge、CEF 和 Auto 真实行为。
- `contains_hotkey`、`force_ime_ENG`、`anchor`。
- `cdp_input`、`driver_input`、`input_check`。
- 模拟人工路径下的 `append` 与 `delay_after=1`。
- 元素库捕获期 `WebSessionId` 在不清理时仍可直连当前页面（产品侧会话绑定）。
