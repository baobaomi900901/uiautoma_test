# `uiautoma.web.WebElement.is_enabled()` 验证证据

```yaml
api: "uiautoma.web.WebElement.is_enabled"
lifecycle: "READY_FOR_LIVE"
verification_summary:
  chrome_api_contract_ok: "PASS"
  chrome_enabled_input_true_ok: "PASS"
  chrome_disabled_input_false_ok: "FAIL"
  cleanup: "PASS"
  verified: false
  exit_code: 1
  note: "disabled boolean 属性存在时 getAttribute 为 ''，is_enabled 误判为可用"
source_access:
  user_authorized: true
  authorization_scope:
    - "uiautoma.web.WebElement.is_enabled 的最小 SDK→web.get_attribute 读路径"
source_review:
  status: "reviewed_with_known_defect"
  fingerprint_kind: "Git blob of current working-tree content"
  source_files:
    - path: "sdk/src/uiautoma/web/element.py"
      symbols: ["WebElement.is_enabled", "WebElement.get_attribute"]
      fingerprint: "4b6e99fdafe1c3a18c71761df0b6fe4cc3356f4b"
  verified_contract:
    signature: "is_enabled() -> bool"
    parameter_order: ["self"]
    defaults: {}
    return_annotation: "bool"
    tested_mode: "chrome"
    status_model: ["PASS", "FAIL", "BLOCKED"]
persistent_script:
  path: "tests/SDK/web/test_web_element_is_enabled.py"
  fingerprint_kind: "Git blob of current working-tree content"
  fingerprint: "03cf1d79c88b4a1acd27191275a5208f2bfa175f"
test_assets:
  element_library_manifest: "tests/SDK/web/web测试元素库/elements.json"
  element_library_manifest_fingerprint: "4abe5fb1c234a81c431f9c1e3779dcaa7097d710"
  enabled_element_name: "input元素"
  disabled_element_name: "input_html_disabled"
  disabled_snapshot_path: "tests/SDK/web/web测试元素库/snapshot/localhost_7199_input_20260809_201734_240.json"
  disabled_snapshot_fingerprint: "bfe7ca6cf2fcc436831834bde655aa1c6e75d192"
source_commit_at_doc_time: "2a320f87b87ea8c9f41ca4af9c6064a748d68eda"
known_issue: "https://github.com/uiautoma/desktop/issues/23"
```

## 持久化脚本

脚本：`tests/SDK/web/test_web_element_is_enabled.py`

```powershell
uv run --extra dev python tests/SDK/web/test_web_element_is_enabled.py --mode chrome
uv run --extra dev python tests/SDK/web/test_web_element_is_enabled.py --contract-only
```

## API 角色划分

- 场景准备 API：`web.create()`、`uiautoma.open()`、`page.find()`、页面激活。
- 目标 API：对 `input元素`、`input_html_disabled` 直接调用 `is_enabled()`。
- 清理 API：关闭元素库连接、关闭本次测试页面、删除临时库副本。

## 最小实现链

```text
uiautoma.web.WebElement.is_enabled
  -> RawWebElement.get_attribute("disabled")
  -> web.get_attribute
  -> page_engine getAttribute("disabled")
  -> disabled in (None, "", "false", "False") → True
```

## 覆盖矩阵

| 场景 | 结果 | 验收内容 |
| --- | --- | --- |
| 公开签名 | `PASS` | 无参、`bool` |
| 预检 / 页面 / 库 | `PASS` | form-controls 与两库项 |
| `input元素` → True | `PASS` | |
| `input_html_disabled` → False | `FAIL` | 实际 True；attr `""` |
| 精确清理 | `PASS` | `3/3` |

## 最近一次真实验证

- 日期：2026-08-09
- 模式：`chrome`
- Profile：`Default`
- 总状态：`FAIL`
- 退出码：`1`
- 生命周期提示：`READY_FOR_LIVE`
- 产品源码修改：无

## 明确排除

- Edge、CEF、Auto
- `aria-disabled` / IDL `disabled` 完整矩阵
- 动态写入 `disabled` 后复读

## 跟踪 Issue

https://github.com/uiautoma/desktop/issues/23
