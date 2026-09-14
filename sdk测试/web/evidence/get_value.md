# `uiautoma.web.WebElement.get_value()` 验证证据

```yaml
api: "uiautoma.web.WebElement.get_value"
lifecycle: "VERIFIED"
verification_summary:
  chrome_get_value_after_input_ok: "PASS"
  cleanup: "PASS"
  verified: true
  exit_code: 0
source_access:
  user_authorized: true
  authorization_scope:
    - "uiautoma.web.WebElement.get_value 的最小 SDK、Runtime 与 DOM value 读取实现链"
source_review:
  status: "verified"
  fingerprint_kind: "Git blob of current working-tree content"
  source_files:
    - path: "sdk/src/uiautoma/web/element.py"
      symbols: ["WebElement.get_value"]
      fingerprint: "3c55dadd2bf0009245d099efa8bfe82595b78b1b"
    - path: "sdk/src/uiautoma/_core/client.py"
      symbols: ["WebElement.get_value"]
      fingerprint: "e8ca31c87da25aa663eb77f60715a28663557e11"
    - path: "automation_pipe_server.py"
      symbols: ["AutomationDispatcher._handle_web_get_value"]
      fingerprint: "3d5054ddcbd79ad6816865c2a9d37f14e0975972"
    - path: "runtime/services/action_service.py"
      symbols: ["ActionService.web_get_value_element"]
      fingerprint: "e22dabe54069b646992d783cdd0b47a7f8ffd3cd"
  verified_contract:
    signature: "get_value() -> str"
    parameter_order: ["self"]
    defaults: {}
    tested_mode: "chrome"
    status_model: ["PASS", "FAIL", "BLOCKED"]
persistent_script:
  path: "tests/SDK/web/test_web_element_get_value.py"
  fingerprint_kind: "Git blob of current working-tree content"
  fingerprint: "da692638ca1c2e60f7dcb186d4813ad6b8bd95e2"
test_assets:
  element_library_manifest: "tests/SDK/web/web测试元素库/elements.json"
  element_library_manifest_fingerprint: "8281c519e8dc529f039a3b58c17219eb57189f47"
  input_element_name: "input元素"
  reset_element_name: "重置_html"
  sample_expected_value: "gv_499b74c7c10b"
source_commit_at_doc_time: "1b2d10fd312576e45b02d5f5d8e0dd223ee7968f"
```

## 持久化脚本

脚本：`tests/SDK/web/test_web_element_get_value.py`

```powershell
uv run --extra dev python tests/SDK/web/test_web_element_get_value.py
```

仅检查公开签名：

```powershell
uv run --extra dev python tests/SDK/web/test_web_element_get_value.py --contract-only
```

`--mode` 默认即为 `chrome`。脚本会复制元素库到 `.pytest_tmp/<run_id>/` 并清空捕获期
`WebSessionId`，避免陈旧会话拦截当前页面绑定；`finally` 中删除该副本。

场景准备的 `input(...)` 与目标 `get_value()` 结果输出到 stderr，避免污染 stdout 的 JSON
报告。

## API 角色划分

- 场景准备 API：`web.create()`、`uiautoma.open()`、`page.find()`、页面激活，以及
  `重置_html` 的 `click()` 与对 `input元素` 的 `input(...)`。
- 目标 API：只对 `input元素` 直接调用无参 `WebElement.get_value()`。
- 清理 API：关闭元素库连接、关闭本次测试页面、删除临时库副本。

## 最小实现链

```text
uiautoma.web.WebElement.get_value
  -> RawWebElement.get_value
  -> AutomationDispatcher._handle_web_get_value
  -> ActionService.web_get_value_element
  -> 浏览器插件/引擎在当前页面 DOM 上读取 value
```

## 覆盖矩阵

| 场景 | 结果 | 验收内容 |
| --- | --- | --- |
| 公开签名 | `PASS` | 仅 `self`、返回注解 `str` |
| 靶场预检 | `PASS` | `/form-controls` HTTP 200 |
| Runtime 预检 | `PASS` | Runtime 与 Automation Pipe 可响应 |
| 元素库预检 | `PASS` | `input元素` / `重置_html` 唯一命中 |
| 临时库会话清理 | `PASS` | 清空捕获期 session 字段后副本可用 |
| 页面准备 | `PASS` | 复用 Chrome 会话，唯一 URL 与页面身份正确 |
| 元素库连接 | `PASS` | 两个库项名称绑定正确 |
| `input` 后 `get_value()` | `PASS` | 返回值与随机写入值完全一致 |
| 精确清理 | `PASS` | 本次资源 `3/3` |

## 最近一次真实验证

- 日期：2026-08-08
- 模式：`chrome`
- Profile 目录：`Default`
- 总状态：`PASS`
- 退出码：`0`
- 靶场：`http://localhost:7199/form-controls`
- 输入元素：`input元素`
- 场景准备：`input(simulative=False)` 写入随机值
- `get_value_after_input`：约 `5.6ms`，`value == expected_value`（示例 `gv_499b74c7c10b`）
- 清理结果：`PASS`，本次资源 `3/3`
- 产品源码修改：无

## 明确排除

- Edge、CEF 和 Auto 真实行为。
- 模拟人工 `input` 后再 `get_value`。
- 空值、只读控件、非输入控件的 `value` 边界。
- 元素库捕获期 `WebSessionId` 在不清理时仍可直连当前页面（产品侧会话绑定）。
