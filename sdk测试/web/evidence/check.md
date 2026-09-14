# `uiautoma.web.WebElement.check()` 验证证据

```yaml
api: "uiautoma.web.WebElement.check"
lifecycle: "READY_FOR_LIVE"
verification_summary:
  chrome_api_contract_ok: "PASS"
  chrome_html_label_check_ok: "FAIL"
  chrome_ant_label_check_ok: "FAIL"
  chrome_html_input_form_state_ok: "FAIL"
  chrome_ant_input_ui_state_ok: "FAIL"
  cleanup: "PASS"
  verified: false
  exit_code: 1
  blocking_defects:
    - "element_not_checkable on label targets"
    - "check() DOM property write does not update React/Ant controlled checkbox state"
source_access:
  user_authorized: true
  authorization_scope:
    - "uiautoma.web.WebElement.check 的最小 SDK、Runtime 与 Page Engine 勾选实现链"
source_review:
  status: "verified"
  fingerprint_kind: "Git blob of current working-tree content"
  source_files:
    - path: "sdk/src/uiautoma/web/element.py"
      symbols: ["WebElement.check", "WebElement._finish"]
      fingerprint: "3c55dadd2bf0009245d099efa8bfe82595b78b1b"
    - path: "sdk/src/uiautoma/_core/client.py"
      symbols: ["WebElement.check"]
      fingerprint: "e8ca31c87da25aa663eb77f60715a28663557e11"
    - path: "automation_pipe_server.py"
      symbols: ["AutomationDispatcher._handle_web_action_check"]
      fingerprint: "3d5054ddcbd79ad6816865c2a9d37f14e0975972"
    - path: "runtime/services/action_service.py"
      symbols: ["ActionService.web_check_element"]
      fingerprint: "e22dabe54069b646992d783cdd0b47a7f8ffd3cd"
    - path: "chrome/engine/engine_packages/page_engine_runtime.js"
      symbols: ["setCheckedState", "setNativeElementProperty"]
      fingerprint: "74f92c170d1d67adae3adae8136eac273d445d82"
  verified_contract:
    signature: "check(mode='check', delay_after=1) -> None"
    parameter_order: ["self", "mode", "delay_after"]
    defaults:
      mode: "check"
      delay_after: 1
    tested_mode: "chrome"
    status_model: ["PASS", "FAIL", "BLOCKED"]
  open_defects:
    - trace_info: "element_not_checkable"
      affected: "label 目标（checkbox_html_input / checkbox_组件_label）"
      product_source_modified: false
    - trace_info: "controlled_checkbox_state_not_updated"
      affected: "React/Ant 受控复选框真实表单或 UI 状态"
      product_source_modified: false
persistent_script:
  path: "tests/SDK/web/test_web_element_check.py"
  fingerprint_kind: "Git blob of current working-tree content"
  fingerprint: "621dc0893cbdd3d4c5eb2a6c340faee88f2295a6"
test_assets:
  element_library_manifest: "tests/SDK/web/web测试元素库/elements.json"
  element_library_manifest_fingerprint: "45299a1c5e4afa2bbfeb55cd24c424cff05dfbba"
  html_label_name: "checkbox_html_input"
  ant_label_name: "checkbox_组件_label"
  ant_input_name: "checkbox_组件_input"
  submit_element_name: "提交_html"
  reset_element_name: "重置_html"
source_commit_at_doc_time: "8a44c023de66eea2a140f7a2fb536a9ff25a7ae8"
```

## 持久化脚本

脚本：`tests/SDK/web/test_web_element_check.py`

```powershell
uv run --extra dev python tests/SDK/web/test_web_element_check.py
```

仅检查公开签名：

```powershell
uv run --extra dev python tests/SDK/web/test_web_element_check.py --contract-only
```

`--mode` 默认即为 `chrome`。脚本会复制元素库到 `.pytest_tmp/<run_id>/` 并清空捕获期
`WebSessionId`；`finally` 中删除该副本。诊断输出到 stderr，stdout 为 JSON 报告。

## API 角色划分

- 场景准备 API：`web.create()`、`uiautoma.open()`、`page.find()`、页面激活，以及
  `重置_html` / `提交_html` 的 `click()`；HTML 路径下通过 `children()` 取 label 内
  input（仅用于逼近可勾选目标，不是公开合同的一部分）。
- 目标 API：直接调用 `WebElement.check(...)`。
- 清理 API：关闭元素库连接、关闭本次测试页面、删除临时库副本。

## 最小实现链

```text
uiautoma.web.WebElement.check
  -> RawWebElement.check
  -> AutomationDispatcher._handle_web_action_check
  -> ActionService.web_check_element
  -> page_engine setCheckedState / setNativeElementProperty
```

## 覆盖矩阵

| 场景 | 结果 | 验收内容 |
| --- | --- | --- |
| 公开签名 | `PASS` | `mode`/`delay_after` 默认值与 `None` 返回注解 |
| 靶场/Runtime/元素库预检 | `PASS` | form-controls 与五库项可用 |
| 页面与库连接 | `PASS` | 绑定成功 |
| HTML label 直接 check | `FAIL` | `element_not_checkable` |
| Ant label 直接 check | `FAIL` | `element_not_checkable` |
| HTML 子 input check + 提交 | `FAIL` | `raw.checked=True` 但 `hobbies is null` |
| Ant input check + class | `FAIL` | `raw.checked=True` 但无 `ant-checkbox-wrapper-checked` |
| 精确清理 | `PASS` | 本次资源 `3/3` |

## 最近一次真实验证

- 日期：2026-08-08
- 模式：`chrome`
- Profile 目录：`Default`
- 总状态：`FAIL`
- 退出码：`1`
- 生命周期提示：`READY_FOR_LIVE`（阻塞 `VERIFIED`）
- 靶场：`http://localhost:7199/form-controls`
- 对照：同目标 `click()` 可更新 HTML 表单 `hobbies=['旅行']`
- 清理结果：`PASS`，本次资源 `3/3`
- 产品源码修改：无（本轮仅记录缺口）

## 明确排除

- Edge、CEF 和 Auto 真实行为。
- `mode=uncheck` / `mode=toggle` 完整矩阵。
- `delay_after=1` 耗时验收。
- 以 `click()` 代替 `check()` 作为目标 API 验收。

## 跟踪 Issue

https://github.com/uiautoma/desktop/issues/12
