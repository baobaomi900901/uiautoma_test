# `uiautoma.web.WebElement.is_checked()` 验证证据

```yaml
api: "uiautoma.web.WebElement.is_checked"
lifecycle: "READY_FOR_LIVE"
verification_summary:
  chrome_api_contract_ok: "PASS"
  chrome_html_input2_unchecked_ok: "PASS"
  chrome_html_input2_checked_after_click_ok: "FAIL"
  chrome_html_input2_form_hobbies_旅行_ok: "PASS"
  chrome_ant_input_checked_after_click_ok: "FAIL"
  cleanup: "PASS"
  verified: false
  exit_code: 1
  note: "click 后表单已选中，is_checked 仍 False；只读 HTML attribute"
source_access:
  user_authorized: true
  authorization_scope:
    - "uiautoma.web.WebElement.is_checked 的最小 SDK→web.get_attribute→Page Engine 读路径"
source_review:
  status: "reviewed_with_known_defect"
  fingerprint_kind: "Git blob of current working-tree content"
  source_files:
    - path: "sdk/src/uiautoma/web/element.py"
      symbols: ["WebElement.is_checked", "WebElement.get_attribute"]
      fingerprint: "3c55dadd2bf0009245d099efa8bfe82595b78b1b"
    - path: "chrome/engine/engine_packages/page_engine_runtime.js"
      symbols: ["get_attribute", "setCheckedState"]
      note: "get_attribute 用 getAttribute；check 路径用 IDL element.checked"
  verified_contract:
    signature: "is_checked() -> bool"
    parameter_order: ["self"]
    defaults: {}
    return_annotation: "bool"
    tested_mode: "chrome"
    status_model: ["PASS", "FAIL", "BLOCKED"]
persistent_script:
  path: "tests/SDK/web/test_web_element_is_checked.py"
  fingerprint_kind: "Git blob of current working-tree content"
  fingerprint: "95af6012ae51c20aaa584d1f9df951d2a8f4a286"
test_assets:
  element_library_manifest: "tests/SDK/web/web测试元素库/elements.json"
  element_library_manifest_fingerprint: "a2af9245792c0bcbae6e351330d555af187ab721"
  html_input_name: "checkbox_html_input2"
  ant_input_name: "checkbox_组件_input"
  submit_element_name: "提交_html"
  reset_element_name: "重置_html"
  html_snapshot_path: "tests/SDK/web/web测试元素库/snapshot/localhost_7199_checkbox_html_input2_20260809_181450_273.json"
  html_snapshot_fingerprint: "fb74c686bc2643387ef2e7d11fbc2d854a3b718b"
  form_hobbies_expected: ["旅行"]
source_commit_at_doc_time: "bb852f9ca4b264a858ea7886ab1a5c58b884c73c"
known_issue: "https://github.com/uiautoma/desktop/issues/22"
```

## 持久化脚本

脚本：`tests/SDK/web/test_web_element_is_checked.py`

```powershell
uv run --extra dev python tests/SDK/web/test_web_element_is_checked.py --mode chrome
uv run --extra dev python tests/SDK/web/test_web_element_is_checked.py --contract-only
```

## API 角色划分

- 场景准备 API：`web.create()`、`uiautoma.open()`、`page.find()`、页面激活；用
  `click()` 切换勾选（非目标 API）；`提交_html` / `重置_html`。
- 目标 API：对 `checkbox_html_input2`、`checkbox_组件_input` 直接调用 `is_checked()`。
- 清理 API：关闭元素库连接、关闭本次测试页面、删除临时库副本。

## 最小实现链

```text
uiautoma.web.WebElement.is_checked
  -> RawWebElement.get_attribute("checked")
  -> web.get_attribute
  -> page_engine get_attribute -> element.getAttribute("checked")
  -> 字符串 in {true, checked, 1}
```

## 覆盖矩阵

| 场景 | 结果 | 验收内容 |
| --- | --- | --- |
| 公开签名 | `PASS` | 无参、`bool` 返回注解 |
| 靶场/Runtime/元素库预检 | `PASS` | form-controls 与库项可用 |
| 页面与库连接 | `PASS` | 绑定 HTML/Ant input 与提交/重置 |
| HTML 重置后未选 | `PASS` | `is_checked() is False` |
| HTML click 后选中读法 | `FAIL` | `is_checked()` 仍 False；attr `""` |
| HTML 提交 `hobbies` | `PASS` | 含 `"旅行"` |
| Ant click 后选中读法 | `FAIL` | 同上 |
| 精确清理 | `PASS` | 本次资源 `3/3` |

## 最近一次真实验证

- 日期：2026-08-09
- 模式：`chrome`
- Profile 目录：`Default`
- 总状态：`FAIL`
- 退出码：`1`
- 生命周期提示：`READY_FOR_LIVE`（阻塞 `VERIFIED`）
- 靶场：`http://localhost:7199/form-controls`
- 元素：`checkbox_html_input2`、`checkbox_组件_input`
- 清理结果：`PASS`，本次资源 `3/3`
- 产品源码修改：无（本轮仅记录缺口与文档）

## 明确排除

- Edge、CEF、Auto。
- 以 `check()` 切换选中态（见 Issue #12）。
- radio / 非 checkbox 控件。
- 库项 `checkbox_html_input`（label）直接验收（已改用 `checkbox_html_input2`）。

## 跟踪 Issue

https://github.com/uiautoma/desktop/issues/22
