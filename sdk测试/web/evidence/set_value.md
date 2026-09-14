# `uiautoma.web.WebElement.set_value()` 验证证据

```yaml
api: "uiautoma.web.WebElement.set_value"
lifecycle: "VERIFIED"
verification_summary:
  chrome_set_value_then_get_value_ok: "PASS"
  cleanup: "PASS"
  verified: true
  exit_code: 0
source_access:
  user_authorized: true
  authorization_scope:
    - "uiautoma.web.WebElement.set_value 的最小 SDK、Runtime 与 DOM value 写入实现链"
source_review:
  status: "verified"
  fingerprint_kind: "Git blob of current working-tree content"
  source_files:
    - path: "sdk/src/uiautoma/web/element.py"
      symbols: ["WebElement.set_value", "WebElement._finish"]
      fingerprint: "3c55dadd2bf0009245d099efa8bfe82595b78b1b"
    - path: "sdk/src/uiautoma/_core/client.py"
      symbols: ["WebElement.type_text"]
      fingerprint: "e8ca31c87da25aa663eb77f60715a28663557e11"
    - path: "automation_pipe_server.py"
      symbols: ["AutomationDispatcher._handle_web_action_type_text"]
      fingerprint: "3d5054ddcbd79ad6816865c2a9d37f14e0975972"
    - path: "runtime/services/action_service.py"
      symbols: ["ActionService.web_type_text_element"]
      fingerprint: "e22dabe54069b646992d783cdd0b47a7f8ffd3cd"
  verified_contract:
    signature: "set_value(value: str) -> None"
    parameter_order: ["self", "value"]
    defaults: {}
    value_required: true
    tested_mode: "chrome"
    status_model: ["PASS", "FAIL", "BLOCKED"]
persistent_script:
  path: "tests/SDK/web/test_web_element_set_value.py"
  fingerprint_kind: "Git blob of current working-tree content"
  fingerprint: "0527b7dd85bc1be1dc5fdf5c17b0a9b02c35d605"
test_assets:
  element_library_manifest: "tests/SDK/web/web测试元素库/elements.json"
  element_library_manifest_fingerprint: "8281c519e8dc529f039a3b58c17219eb57189f47"
  input_element_name: "input元素"
  reset_element_name: "重置_html"
  sample_expected_value: "sv_070fc4ac6d3c"
source_commit_at_doc_time: "25055f002a8a20c8137cc3736f20babbb9424088"
```

## 持久化脚本

脚本：`tests/SDK/web/test_web_element_set_value.py`

```powershell
uv run --extra dev python tests/SDK/web/test_web_element_set_value.py
```

仅检查公开签名：

```powershell
uv run --extra dev python tests/SDK/web/test_web_element_set_value.py --contract-only
```

`--mode` 默认即为 `chrome`。脚本会复制元素库到 `.pytest_tmp/<run_id>/` 并清空捕获期
`WebSessionId`，避免陈旧会话拦截当前页面绑定；`finally` 中删除该副本。

目标 `set_value(...)` 与验收 `get_value()` 输出到 stderr，避免污染 stdout 的 JSON 报告。

## API 角色划分

- 场景准备 API：`web.create()`、`uiautoma.open()`、`page.find()`、页面激活，以及
  `重置_html` 的 `click()`。
- 目标 API：只对 `input元素` 直接调用 `WebElement.set_value(value)`。
- 验收 API：`get_value()`（不作为本轮目标合同）。
- 清理 API：关闭元素库连接、关闭本次测试页面、删除临时库副本。

## 最小实现链

```text
uiautoma.web.WebElement.set_value
  -> RawWebElement.type_text(..., clear=True, focus=True)
  -> AutomationDispatcher._handle_web_action_type_text
  -> ActionService.web_type_text_element
  -> 浏览器插件/引擎写入输入框 value
```

## 覆盖矩阵

| 场景 | 结果 | 验收内容 |
| --- | --- | --- |
| 公开签名 | `PASS` | `self`/`value`、`value` 必填、返回注解 `None` |
| 靶场预检 | `PASS` | `/form-controls` HTTP 200 |
| Runtime 预检 | `PASS` | Runtime 与 Automation Pipe 可响应 |
| 元素库预检 | `PASS` | `input元素` / `重置_html` 唯一命中 |
| 临时库会话清理 | `PASS` | 清空捕获期 session 字段后副本可用 |
| 页面准备 | `PASS` | 复用 Chrome 会话，唯一 URL 与页面身份正确 |
| 元素库连接 | `PASS` | 两个库项名称绑定正确 |
| `set_value` 后 `get_value` | `PASS` | 返回 `None` 且回读值与写入值一致 |
| 精确清理 | `PASS` | 本次资源 `3/3` |

## 最近一次真实验证

- 日期：2026-08-08
- 模式：`chrome`
- Profile 目录：`Default`
- 总状态：`PASS`
- 退出码：`0`
- 靶场：`http://localhost:7199/form-controls`
- 输入元素：`input元素`
- `set_value_then_get_value`：约 `31.2ms`，返回 `None`，
  `get_value() == expected_value`（示例 `sv_070fc4ac6d3c`）
- 清理结果：`PASS`，本次资源 `3/3`
- 产品源码修改：无

## 明确排除

- Edge、CEF 和 Auto 真实行为。
- 模拟人工路径 / `input()` 后再 `set_value`。
- 空值、非输入控件、追加语义。
- 元素库捕获期 `WebSessionId` 在不清理时仍可直连当前页面（产品侧会话绑定）。
